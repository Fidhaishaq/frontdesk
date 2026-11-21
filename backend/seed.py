"""
Seed script to populate the database with demo data.
Run with: python seed.py
"""

import os
import sys

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Ticket, TicketMessage, AuditLog, Holiday
from app.sla import calculate_sla_deadlines, get_holidays


def seed():
    app = create_app()
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()

        print("Seeding database...")

        # ============ Users ============
        admin = User(
            name='Admin User',
            email='admin@arvo.com',
            password_hash=generate_password_hash('Admin123!'),
            role='admin',
            is_active=True
        )
        db.session.add(admin)

        agent_names = [
            ('Rahul Sharma', 'agent1@arvo.com'),
            ('Priya Patel', 'agent2@arvo.com'),
            ('Amit Kumar', 'agent3@arvo.com'),
            ('Sneha Reddy', 'agent4@arvo.com'),
            ('Vikram Singh', 'agent5@arvo.com'),
            ('Ananya Gupta', 'agent6@arvo.com'),
            ('Rohan Joshi', 'agent7@arvo.com'),
            ('Kavitha Nair', 'agent8@arvo.com'),
            ('Arjun Menon', 'agent9@arvo.com'),
        ]

        agents = []
        for name, email in agent_names:
            agent = User(
                name=name,
                email=email,
                password_hash=generate_password_hash('Agent123!'),
                role='agent',
                is_active=True
            )
            db.session.add(agent)
            agents.append(agent)

        db.session.flush()
        print(f"  Created 1 admin + {len(agents)} agents")

        # ============ Holidays ============
        holidays_data = [
            (date(2025, 1, 26), 'Republic Day'),
            (date(2025, 3, 14), 'Holi'),
            (date(2025, 4, 14), 'Ambedkar Jayanti'),
            (date(2025, 5, 1), 'May Day'),
            (date(2025, 8, 15), 'Independence Day'),
            (date(2025, 10, 2), 'Gandhi Jayanti'),
            (date(2025, 10, 20), 'Diwali'),
            (date(2025, 10, 21), 'Diwali (Day 2)'),
            (date(2025, 12, 25), 'Christmas'),
            (date(2026, 1, 26), 'Republic Day'),
            (date(2026, 3, 3), 'Holi'),
            (date(2026, 8, 15), 'Independence Day'),
            (date(2026, 10, 2), 'Gandhi Jayanti'),
            (date(2026, 11, 9), 'Diwali'),
            (date(2026, 12, 25), 'Christmas'),
        ]

        for h_date, h_name in holidays_data:
            db.session.add(Holiday(date=h_date, name=h_name))

        db.session.flush()
        print(f"  Created {len(holidays_data)} holidays")

        holiday_set = {h[0] for h in holidays_data}

        # ============ Tickets ============
        now = datetime.utcnow()

        ticket_data = [
            {
                'customer_name': 'Rajesh Krishnan',
                'customer_email': 'rajesh@example.com',
                'subject': 'Unable to login to dashboard',
                'description': 'I am getting "Invalid credentials" error even though I reset my password yesterday. I tried clearing cookies and using incognito mode but the issue persists.',
                'priority': 'urgent',
                'status': 'in_progress',
                'agent_idx': 0,
                'hours_ago': 4,
            },
            {
                'customer_name': 'Meera Sundaram',
                'customer_email': 'meera@example.com',
                'subject': 'Export feature not generating PDF',
                'description': 'When I click "Export to PDF" on the reports page, nothing happens. The button seems to click but no download starts. Using Chrome 120 on Windows 11.',
                'priority': 'medium',
                'status': 'waiting_for_customer',
                'agent_idx': 1,
                'hours_ago': 28,
            },
            {
                'customer_name': 'Sunil Kapoor',
                'customer_email': 'sunil.k@example.com',
                'subject': 'API rate limit exceeded constantly',
                'description': 'Our integration is hitting the rate limit even though we are well within the documented limits. We are making about 100 requests per minute but the limit should be 500.',
                'priority': 'urgent',
                'status': 'open',
                'agent_idx': None,
                'hours_ago': 1,
            },
            {
                'customer_name': 'Divya Nair',
                'customer_email': 'divya@example.com',
                'subject': 'Need to update billing information',
                'description': 'Please update our billing address and GST number. I have attached the updated details in the form below.',
                'priority': 'small',
                'status': 'resolved',
                'agent_idx': 2,
                'hours_ago': 72,
            },
            {
                'customer_name': 'Arun Prakash',
                'customer_email': 'arun.p@example.com',
                'subject': 'Dashboard charts showing incorrect data',
                'description': 'The monthly revenue chart is showing data from last year instead of this year. This is affecting our board presentation tomorrow.',
                'priority': 'urgent',
                'status': 'in_progress',
                'agent_idx': 3,
                'hours_ago': 6,
            },
            {
                'customer_name': 'Lakshmi Venkatesh',
                'customer_email': 'lakshmi.v@example.com',
                'subject': 'Feature request: bulk user import',
                'description': 'We need the ability to import users via CSV file. Currently we have to add each user manually which is very time consuming for our 200+ team.',
                'priority': 'small',
                'status': 'open',
                'agent_idx': None,
                'hours_ago': 48,
            },
            {
                'customer_name': 'Karthik Rajan',
                'customer_email': 'karthik@example.com',
                'subject': 'Two-factor authentication not sending OTP',
                'description': 'After enabling 2FA, I am not receiving the OTP on my registered mobile number. I have checked my SMS settings and there are no blocks.',
                'priority': 'medium',
                'status': 'in_progress',
                'agent_idx': 4,
                'hours_ago': 12,
            },
            {
                'customer_name': 'Pooja Sharma',
                'customer_email': 'pooja.s@example.com',
                'subject': 'Account deletion request',
                'description': 'Please delete my account and all associated data as per our data retention policy. My user ID is USR-4521.',
                'priority': 'medium',
                'status': 'in_progress',
                'agent_idx': 5,
                'hours_ago': 20,
            },
            {
                'customer_name': 'Nikhil Jain',
                'customer_email': 'nikhil.j@example.com',
                'subject': 'Integration webhook failures',
                'description': 'Our webhook endpoint is receiving 500 errors from your system since yesterday. The endpoint URL is correct and responding to health checks.',
                'priority': 'urgent',
                'status': 'open',
                'agent_idx': None,
                'hours_ago': 2,
            },
            {
                'customer_name': 'Swathi Pillai',
                'customer_email': 'swathi@example.com',
                'subject': 'Permission error on team settings',
                'description': 'I am a team admin but getting "Forbidden" when trying to change team settings. This was working fine until last week.',
                'priority': 'medium',
                'status': 'open',
                'agent_idx': None,
                'hours_ago': 8,
            },
            {
                'customer_name': 'Ravi Teja',
                'customer_email': 'ravi.t@example.com',
                'subject': 'Slow page load times on analytics',
                'description': 'The analytics page takes over 30 seconds to load. All other pages are fine. This started about a week ago.',
                'priority': 'small',
                'status': 'in_progress',
                'agent_idx': 6,
                'hours_ago': 36,
            },
            {
                'customer_name': 'Anjali Deshmukh',
                'customer_email': 'anjali.d@example.com',
                'subject': 'Mobile app crashes on launch',
                'description': 'The Android app crashes immediately after the splash screen. I have tried reinstalling. Phone is Samsung Galaxy S23 running Android 14.',
                'priority': 'urgent',
                'status': 'resolved',
                'agent_idx': 7,
                'hours_ago': 50,
            },
            {
                'customer_name': 'Pranav Kulkarni',
                'customer_email': 'pranav.k@example.com',
                'subject': 'SSO configuration help needed',
                'description': 'We want to set up SAML SSO with our Okta instance. Can you provide documentation or help with the configuration?',
                'priority': 'small',
                'status': 'waiting_for_customer',
                'agent_idx': 8,
                'hours_ago': 96,
            },
            {
                'customer_name': 'Deepa Murthy',
                'customer_email': 'deepa.m@example.com',
                'subject': 'Invoice discrepancy for November',
                'description': 'Our November invoice shows charges for 50 users but we only have 35 active users. Please review and correct.',
                'priority': 'medium',
                'status': 'closed',
                'agent_idx': 0,
                'hours_ago': 168,
            },
            {
                'customer_name': 'Harish Iyer',
                'customer_email': 'harish.i@example.com',
                'subject': 'Custom domain SSL certificate expired',
                'description': 'Our custom domain portal.ourcompany.com is showing SSL certificate errors. The certificate seems to have expired.',
                'priority': 'urgent',
                'status': 'in_progress',
                'agent_idx': 1,
                'hours_ago': 3,
            },
        ]

        for i, td in enumerate(ticket_data):
            created_at = now - timedelta(hours=td['hours_ago'])
            ticket_number = f'INC-{i + 1:04d}'

            deadlines = calculate_sla_deadlines(td['priority'], created_at, holiday_set)

            agent_id = None
            if td['agent_idx'] is not None:
                agent_id = agents[td['agent_idx']].id

            ticket = Ticket(
                ticket_number=ticket_number,
                customer_name=td['customer_name'],
                customer_email=td['customer_email'],
                subject=td['subject'],
                description=td['description'],
                priority=td['priority'],
                status=td['status'],
                assigned_agent_id=agent_id,
                response_deadline=deadlines['response_deadline'],
                resolution_deadline=deadlines['resolution_deadline'],
                created_at=created_at,
                updated_at=now - timedelta(hours=max(0, td['hours_ago'] - 1)),
            )

            if td['status'] == 'resolved':
                ticket.resolved_at = now - timedelta(hours=max(0, td['hours_ago'] - 10))
                ticket.first_response_at = created_at + timedelta(hours=1)
            elif td['status'] == 'closed':
                ticket.closed_at = now - timedelta(hours=max(0, td['hours_ago'] - 20))
                ticket.resolved_at = now - timedelta(hours=max(0, td['hours_ago'] - 15))
                ticket.first_response_at = created_at + timedelta(hours=1)
            elif td['status'] == 'waiting_for_customer':
                ticket.sla_paused_at = now - timedelta(hours=max(0, td['hours_ago'] // 2))
                ticket.first_response_at = created_at + timedelta(hours=1)
            elif td['status'] == 'in_progress' and agent_id:
                ticket.first_response_at = created_at + timedelta(hours=1)

            db.session.add(ticket)
            db.session.flush()

            # Create audit log for ticket creation
            db.session.add(AuditLog(
                ticket_id=ticket.id,
                action='ticket_created',
                new_value=f'{ticket_number} - {td["subject"][:80]}',
                user_id=admin.id,
                user_name='Admin User',
                created_at=created_at
            ))

            # Add sample messages
            if td['status'] != 'open':
                # Initial customer message
                db.session.add(TicketMessage(
                    ticket_id=ticket.id,
                    user_id=None,
                    sender_name=td['customer_name'],
                    content=td['description'],
                    is_internal=False,
                    created_at=created_at
                ))

                if agent_id:
                    agent_name = agents[td['agent_idx']].name

                    # Agent response
                    db.session.add(TicketMessage(
                        ticket_id=ticket.id,
                        user_id=agent_id,
                        sender_name=agent_name,
                        content=f"Hi {td['customer_name'].split()[0]}, thank you for reaching out. I'm looking into this issue now and will update you shortly.",
                        is_internal=False,
                        created_at=created_at + timedelta(hours=1)
                    ))

                    # Audit for claim
                    db.session.add(AuditLog(
                        ticket_id=ticket.id,
                        action='ticket_claimed',
                        new_value=agent_name,
                        user_id=agent_id,
                        user_name=agent_name,
                        created_at=created_at + timedelta(minutes=30)
                    ))

                    # Add an internal note for some tickets
                    if i % 3 == 0:
                        db.session.add(TicketMessage(
                            ticket_id=ticket.id,
                            user_id=agent_id,
                            sender_name=agent_name,
                            content=f"Internal: Checked the logs, this seems related to the recent deployment. Escalating to engineering team.",
                            is_internal=True,
                            created_at=created_at + timedelta(hours=2)
                        ))
                        db.session.add(AuditLog(
                            ticket_id=ticket.id,
                            action='internal_note_added',
                            new_value=f'Note by {agent_name}',
                            user_id=agent_id,
                            user_name=agent_name,
                            created_at=created_at + timedelta(hours=2)
                        ))

        db.session.commit()
        print(f"  Created {len(ticket_data)} tickets with messages and audit logs")
        print("\nSeeding complete!")
        print("\n--- Demo Credentials ---")
        print("Admin:   admin@arvo.com / Admin123!")
        print("Agent 1: agent1@arvo.com / Agent123!")
        print("Agent 2: agent2@arvo.com / Agent123!")
        print("  ... through agent9@arvo.com")


if __name__ == '__main__':
    seed()
