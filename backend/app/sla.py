"""
SLA Calculation Engine for Frontdesk.

Business hours: Monday-Friday, 09:30 - 18:30 IST (9 hours per day).
All datetimes are treated as naive IST.

SLA Recalculation Policy:
When a ticket's priority changes, SLA deadlines are recalculated from the
moment of the change, NOT from ticket creation. This prevents instant breach
when escalating (e.g., Small→Urgent after 60 hours would be instantly breached
if calculated from creation).
"""

from datetime import datetime, date, timedelta

# Working hours constants
WORK_START_HOUR = 9
WORK_START_MINUTE = 30
WORK_END_HOUR = 18
WORK_END_MINUTE = 30
WORK_DAY_SECONDS = 9 * 3600  # 32400 seconds (9 hours)

# SLA targets in working seconds
SLA_TARGETS = {
    'urgent': {
        'response': 2 * 3600,       # 2 working hours
        'resolution': 9 * 3600,     # Same working day (9 hours)
    },
    'medium': {
        'response': 4 * 3600 + 1800,  # 4.5 working hours (half day)
        'resolution': 27 * 3600,       # 3 working days (27 hours)
    },
    'small': {
        'response': 9 * 3600,       # 1 working day (9 hours)
        'resolution': 45 * 3600,    # 1 working week / 5 days (45 hours)
    },
}


def get_holidays():
    """Query Holiday table, return set of date objects."""
    try:
        from app.models import Holiday
        holidays = Holiday.query.all()
        return {h.date for h in holidays}
    except Exception:
        return set()


def is_working_day(d, holidays=None):
    """Return True if d is Monday-Friday and not in holidays set."""
    if holidays is None:
        holidays = get_holidays()
    if isinstance(d, datetime):
        d = d.date()
    # Monday=0, Sunday=6
    if d.weekday() >= 5:
        return False
    if d in holidays:
        return False
    return True


def get_work_start(d):
    """Return datetime for 09:30 on given date."""
    if isinstance(d, datetime):
        d = d.date()
    return datetime(d.year, d.month, d.day, WORK_START_HOUR, WORK_START_MINUTE, 0)


def get_work_end(d):
    """Return datetime for 18:30 on given date."""
    if isinstance(d, datetime):
        d = d.date()
    return datetime(d.year, d.month, d.day, WORK_END_HOUR, WORK_END_MINUTE, 0)


def _next_working_day(d, holidays=None):
    """Find the next working day after date d."""
    if holidays is None:
        holidays = get_holidays()
    if isinstance(d, datetime):
        d = d.date()
    d = d + timedelta(days=1)
    while not is_working_day(d, holidays):
        d = d + timedelta(days=1)
    return d


def _prev_working_day(d, holidays=None):
    """Find the previous working day before date d."""
    if holidays is None:
        holidays = get_holidays()
    if isinstance(d, datetime):
        d = d.date()
    d = d - timedelta(days=1)
    while not is_working_day(d, holidays):
        d = d - timedelta(days=1)
    return d


def _clamp_to_work_hours(dt, holidays=None):
    """
    Clamp a datetime to working hours.
    If before work start → return work start of same day (if working day) or next working day.
    If after work end → return work start of next working day.
    If on weekend/holiday → return work start of next working day.
    """
    if holidays is None:
        holidays = get_holidays()

    d = dt.date()
    work_start = get_work_start(d)
    work_end = get_work_end(d)

    if not is_working_day(d, holidays):
        # Move to next working day
        next_wd = _next_working_day(d, holidays)
        return get_work_start(next_wd)

    if dt < work_start:
        return work_start
    elif dt >= work_end:
        next_wd = _next_working_day(d, holidays)
        return get_work_start(next_wd)
    else:
        return dt


def calculate_working_seconds(start, end, holidays=None):
    """
    Calculate the number of working seconds between start and end datetimes.
    Only counts time within Mon-Fri 09:30-18:30, excluding holidays.
    """
    if holidays is None:
        holidays = get_holidays()

    if end <= start:
        return 0

    total_seconds = 0
    current = _clamp_to_work_hours(start, holidays)

    if current >= end:
        return 0

    while current < end:
        d = current.date()
        if not is_working_day(d, holidays):
            current = get_work_start(_next_working_day(d, holidays))
            continue

        work_end_today = get_work_end(d)

        if end <= work_end_today:
            # end is within today's working hours
            total_seconds += int((end - current).total_seconds())
            break
        else:
            # Count remaining work time today, move to next day
            total_seconds += int((work_end_today - current).total_seconds())
            next_wd = _next_working_day(d, holidays)
            current = get_work_start(next_wd)

    return max(0, total_seconds)


def add_working_seconds(start, seconds, holidays=None):
    """
    Add the specified number of working seconds to start datetime.
    Returns the exact datetime when the seconds are exhausted.
    """
    if holidays is None:
        holidays = get_holidays()

    if seconds <= 0:
        return start

    current = _clamp_to_work_hours(start, holidays)
    remaining = seconds

    while remaining > 0:
        d = current.date()
        if not is_working_day(d, holidays):
            current = get_work_start(_next_working_day(d, holidays))
            continue

        work_end_today = get_work_end(d)
        available_today = int((work_end_today - current).total_seconds())

        if available_today <= 0:
            current = get_work_start(_next_working_day(d, holidays))
            continue

        if remaining <= available_today:
            current = current + timedelta(seconds=remaining)
            remaining = 0
        else:
            remaining -= available_today
            next_wd = _next_working_day(d, holidays)
            current = get_work_start(next_wd)

    return current


def calculate_sla_deadlines(priority, from_time, holidays=None):
    """
    Calculate SLA deadlines for a given priority from a given time.
    Returns dict with response_deadline and resolution_deadline.
    """
    if holidays is None:
        holidays = get_holidays()

    targets = SLA_TARGETS.get(priority, SLA_TARGETS['medium'])

    response_deadline = add_working_seconds(from_time, targets['response'], holidays)
    resolution_deadline = add_working_seconds(from_time, targets['resolution'], holidays)

    return {
        'response_deadline': response_deadline,
        'resolution_deadline': resolution_deadline,
    }


def is_ticket_overdue(ticket):
    """
    Check if a ticket's SLA is breached.
    Returns dict with response_overdue and resolution_overdue booleans.
    """
    now = datetime.utcnow()
    result = {
        'response_overdue': False,
        'resolution_overdue': False,
    }

    # Skip check for closed/resolved tickets
    if ticket.status in ('closed', 'resolved'):
        return result

    # Response SLA: only relevant if no first response yet
    if not ticket.first_response_at and ticket.response_deadline:
        if now > ticket.response_deadline:
            result['response_overdue'] = True

    # Resolution SLA
    if ticket.resolution_deadline:
        if now > ticket.resolution_deadline:
            result['resolution_overdue'] = True

    return result


def count_working_days_since(start_dt, holidays=None):
    """Count working days between start_dt and now."""
    if holidays is None:
        holidays = get_holidays()
    now = datetime.utcnow()
    if now <= start_dt:
        return 0

    count = 0
    d = start_dt.date()
    end_d = now.date()

    while d <= end_d:
        if is_working_day(d, holidays):
            count += 1
        d += timedelta(days=1)

    return count
