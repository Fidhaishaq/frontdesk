"""Tests for the SLA calculation engine."""

import pytest
from datetime import datetime, date, timedelta
from app.sla import (
    is_working_day, get_work_start, get_work_end,
    calculate_working_seconds, add_working_seconds,
    calculate_sla_deadlines, WORK_DAY_SECONDS
)


class TestIsWorkingDay:
    def test_monday_is_working_day(self):
        # 2025-01-06 is Monday
        assert is_working_day(date(2025, 1, 6), set()) is True

    def test_friday_is_working_day(self):
        # 2025-01-10 is Friday
        assert is_working_day(date(2025, 1, 10), set()) is True

    def test_saturday_is_not_working_day(self):
        # 2025-01-11 is Saturday
        assert is_working_day(date(2025, 1, 11), set()) is False

    def test_sunday_is_not_working_day(self):
        # 2025-01-12 is Sunday
        assert is_working_day(date(2025, 1, 12), set()) is False

    def test_holiday_is_not_working_day(self):
        holidays = {date(2025, 1, 26)}  # Republic Day (Sunday in 2025, but test the logic)
        # Use a weekday holiday
        holidays = {date(2025, 1, 6)}  # Monday
        assert is_working_day(date(2025, 1, 6), holidays) is False

    def test_non_holiday_weekday(self):
        holidays = {date(2025, 1, 26)}
        assert is_working_day(date(2025, 1, 6), holidays) is True


class TestWorkHours:
    def test_work_start(self):
        d = date(2025, 1, 6)
        ws = get_work_start(d)
        assert ws.hour == 9
        assert ws.minute == 30

    def test_work_end(self):
        d = date(2025, 1, 6)
        we = get_work_end(d)
        assert we.hour == 18
        assert we.minute == 30


class TestCalculateWorkingSeconds:
    def test_same_day_full_working_hours(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        end = datetime(2025, 1, 6, 18, 30)    # Monday 18:30
        result = calculate_working_seconds(start, end, set())
        assert result == WORK_DAY_SECONDS  # 9 hours

    def test_same_day_partial(self):
        start = datetime(2025, 1, 6, 10, 30)  # Monday 10:30
        end = datetime(2025, 1, 6, 12, 30)    # Monday 12:30
        result = calculate_working_seconds(start, end, set())
        assert result == 2 * 3600  # 2 hours

    def test_excludes_weekends(self):
        start = datetime(2025, 1, 10, 17, 30)  # Friday 17:30
        end = datetime(2025, 1, 13, 10, 30)    # Monday 10:30
        result = calculate_working_seconds(start, end, set())
        # Friday: 1 hour (17:30-18:30) + Monday: 1 hour (09:30-10:30)
        assert result == 2 * 3600

    def test_excludes_holidays(self):
        holidays = {date(2025, 1, 7)}  # Tuesday is holiday
        start = datetime(2025, 1, 6, 9, 30)   # Monday 09:30
        end = datetime(2025, 1, 8, 9, 30)      # Wednesday 09:30
        result = calculate_working_seconds(start, end, holidays)
        # Monday: 9 hours, Tuesday: skipped (holiday), Wed: 0 hours (at start)
        assert result == WORK_DAY_SECONDS

    def test_before_work_hours(self):
        start = datetime(2025, 1, 6, 7, 0)   # Monday 07:00
        end = datetime(2025, 1, 6, 10, 30)    # Monday 10:30
        result = calculate_working_seconds(start, end, set())
        # Clamped to 09:30-10:30 = 1 hour
        assert result == 3600

    def test_after_work_hours(self):
        start = datetime(2025, 1, 6, 19, 0)   # Monday 19:00
        end = datetime(2025, 1, 7, 10, 30)     # Tuesday 10:30
        result = calculate_working_seconds(start, end, set())
        # Monday: nothing (after hours), Tuesday: 09:30-10:30 = 1 hour
        assert result == 3600

    def test_end_before_start(self):
        start = datetime(2025, 1, 6, 12, 0)
        end = datetime(2025, 1, 6, 10, 0)
        result = calculate_working_seconds(start, end, set())
        assert result == 0


class TestAddWorkingSeconds:
    def test_same_day(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        result = add_working_seconds(start, 3600, set())  # Add 1 hour
        assert result == datetime(2025, 1, 6, 10, 30)

    def test_across_days(self):
        start = datetime(2025, 1, 6, 17, 30)  # Monday 17:30
        result = add_working_seconds(start, 2 * 3600, set())  # Add 2 hours
        # 1 hour left on Monday + 1 hour on Tuesday
        assert result == datetime(2025, 1, 7, 10, 30)

    def test_across_weekend(self):
        start = datetime(2025, 1, 10, 17, 30)  # Friday 17:30
        result = add_working_seconds(start, 2 * 3600, set())  # Add 2 hours
        # 1 hour left on Friday + skip weekend + 1 hour on Monday
        assert result == datetime(2025, 1, 13, 10, 30)

    def test_full_day(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        result = add_working_seconds(start, WORK_DAY_SECONDS, set())
        assert result == datetime(2025, 1, 6, 18, 30)

    def test_multiple_days(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        result = add_working_seconds(start, 2 * WORK_DAY_SECONDS, set())  # 2 days
        assert result == datetime(2025, 1, 7, 18, 30)  # Tuesday 18:30

    def test_skip_holiday(self):
        holidays = {date(2025, 1, 7)}  # Tuesday
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        result = add_working_seconds(start, 2 * WORK_DAY_SECONDS, holidays)
        # Monday full day + skip Tuesday + Wednesday full day
        assert result == datetime(2025, 1, 8, 18, 30)

    def test_start_on_weekend(self):
        start = datetime(2025, 1, 11, 10, 0)  # Saturday
        result = add_working_seconds(start, 3600, set())
        # Moves to Monday 09:30, then adds 1 hour
        assert result == datetime(2025, 1, 13, 10, 30)


class TestSLADeadlines:
    def test_urgent_deadlines(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        deadlines = calculate_sla_deadlines('urgent', start, set())
        # Response: 2 hours → 11:30
        assert deadlines['response_deadline'] == datetime(2025, 1, 6, 11, 30)
        # Resolution: same day (9 hours) → 18:30
        assert deadlines['resolution_deadline'] == datetime(2025, 1, 6, 18, 30)

    def test_medium_deadlines(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        deadlines = calculate_sla_deadlines('medium', start, set())
        # Response: 4.5 hours → 14:00
        assert deadlines['response_deadline'] == datetime(2025, 1, 6, 14, 0)

    def test_small_deadlines(self):
        start = datetime(2025, 1, 6, 9, 30)  # Monday 09:30
        deadlines = calculate_sla_deadlines('small', start, set())
        # Response: 1 working day (9 hours) → 18:30
        assert deadlines['response_deadline'] == datetime(2025, 1, 6, 18, 30)
