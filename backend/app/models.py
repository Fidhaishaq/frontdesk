from datetime import datetime
from app import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')  # 'admin' or 'agent'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='medium')  # urgent, medium, small
    status = db.Column(db.String(30), nullable=False, default='open')
    # Statuses: open, in_progress, waiting_for_customer, resolved, closed

    assigned_agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    response_deadline = db.Column(db.DateTime, nullable=True)
    resolution_deadline = db.Column(db.DateTime, nullable=True)

    # SLA pause tracking
    sla_paused_at = db.Column(db.DateTime, nullable=True)
    total_paused_seconds = db.Column(db.Integer, default=0)

    # Timestamps
    first_response_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_agent = db.relationship('User', foreign_keys=[assigned_agent_id], lazy='joined')
    messages = db.relationship('TicketMessage', backref='ticket', lazy='dynamic',
                               order_by='TicketMessage.created_at')
    audit_logs = db.relationship('AuditLog', backref='ticket', lazy='dynamic',
                                 order_by='AuditLog.created_at.desc()')

    @staticmethod
    def generate_ticket_number():
        max_ticket = db.session.query(db.func.max(Ticket.id)).scalar()
        next_id = (max_ticket or 0) + 1
        return f'INC-{next_id:04d}'

    def to_dict(self):
        from app.sla import is_ticket_overdue
        overdue_info = is_ticket_overdue(self)

        sla_status = 'on_time'
        if self.status in ('resolved', 'closed'):
            sla_status = 'done'
        elif overdue_info.get('response_overdue') or overdue_info.get('resolution_overdue'):
            sla_status = 'overdue'

        return {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'subject': self.subject,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'assigned_agent_id': self.assigned_agent_id,
            'assigned_agent_name': self.assigned_agent.name if self.assigned_agent else None,
            'response_deadline': self.response_deadline.isoformat() if self.response_deadline else None,
            'resolution_deadline': self.resolution_deadline.isoformat() if self.resolution_deadline else None,
            'sla_paused_at': self.sla_paused_at.isoformat() if self.sla_paused_at else None,
            'total_paused_seconds': self.total_paused_seconds,
            'first_response_at': self.first_response_at.isoformat() if self.first_response_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_response_overdue': overdue_info.get('response_overdue', False),
            'is_resolution_overdue': overdue_info.get('resolution_overdue', False),
            'sla_status': sla_status
        }


class TicketMessage(db.Model):
    __tablename__ = 'ticket_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    sender_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'sender_name': self.sender_name,
            'content': self.content,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.String(500), nullable=True)
    new_value = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'action': self.action,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SlaPauseRecord(db.Model):
    __tablename__ = 'sla_pause_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    paused_at = db.Column(db.DateTime, nullable=False)
    resumed_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)

    ticket = db.relationship('Ticket', foreign_keys=[ticket_id])

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'resumed_at': self.resumed_at.isoformat() if self.resumed_at else None,
            'duration_seconds': self.duration_seconds
        }
