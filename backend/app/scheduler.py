"""
Background scheduler for automated tasks.
- Auto-close tickets that have been waiting for customer response
  for more than 5 business days.
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.sla import count_working_days_since


def auto_close_stale_tickets(app):
    """Check and auto-close tickets waiting too long for customer response."""
    with app.app_context():
        from app import db
        from app.models import Ticket, AuditLog

        tickets = Ticket.query.filter_by(status='waiting_for_customer').all()
        now = datetime.utcnow()

        for ticket in tickets:
            if not ticket.sla_paused_at:
                continue

            working_days = count_working_days_since(ticket.sla_paused_at)

            if working_days >= 5:
                ticket.status = 'closed'
                ticket.closed_at = now
                ticket.updated_at = now

                # Clear pause
                ticket.sla_paused_at = None

                log = AuditLog(
                    ticket_id=ticket.id,
                    action='ticket_auto_closed',
                    old_value='waiting_for_customer',
                    new_value='closed',
                    user_name='System',
                    created_at=now
                )
                db.session.add(log)

        db.session.commit()


def init_scheduler(app):
    """Initialize and start the background scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=auto_close_stale_tickets,
        args=[app],
        trigger='interval',
        minutes=15,
        id='auto_close_stale',
        replace_existing=True,
        misfire_grace_time=120
    )
    scheduler.start()
    print(" * Background scheduler started (auto-close check every 15 min)")
