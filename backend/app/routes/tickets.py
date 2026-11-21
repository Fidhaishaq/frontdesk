from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from app import db
from app.models import Ticket, TicketMessage, AuditLog, SlaPauseRecord, User
from app.middleware import get_current_user, role_required
from app.sla import calculate_sla_deadlines, get_holidays

tickets_bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')


def create_audit_log(ticket_id, action, old_value=None, new_value=None, user=None):
    """Helper to create an audit log entry."""
    log = AuditLog(
        ticket_id=ticket_id,
        action=action,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        user_id=user.id if user else None,
        user_name=user.name if user else 'System',
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    return log


@tickets_bp.route('', methods=['GET'])
@jwt_required()
def list_tickets():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    query = Ticket.query

    # Role-based filtering
    if user.role == 'agent':
        # Agents see their assigned tickets + unassigned open tickets
        query = query.filter(
            db.or_(
                Ticket.assigned_agent_id == user.id,
                Ticket.assigned_agent_id.is_(None)
            )
        )

    # Apply filters
    status = request.args.get('status')
    if status and status != 'all':
        query = query.filter(Ticket.status == status)

    priority = request.args.get('priority')
    if priority and priority != 'all':
        query = query.filter(Ticket.priority == priority)

    agent_id = request.args.get('agent_id')
    if agent_id and agent_id != 'all':
        if agent_id == 'unassigned':
            query = query.filter(Ticket.assigned_agent_id.is_(None))
        else:
            try:
                query = query.filter(Ticket.assigned_agent_id == int(agent_id))
            except ValueError:
                pass

    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Ticket.ticket_number.ilike(search_pattern),
                Ticket.subject.ilike(search_pattern),
                Ticket.customer_name.ilike(search_pattern),
                Ticket.customer_email.ilike(search_pattern)
            )
        )

    # Sort by created_at descending
    query = query.order_by(Ticket.created_at.desc())
    tickets = query.all()

    # Overdue filter (applied post-query since it's computed)
    overdue = request.args.get('overdue')
    if overdue == 'true':
        tickets = [t for t in tickets if t.to_dict().get('sla_status') == 'overdue']

    return jsonify({'tickets': [t.to_dict() for t in tickets]}), 200


@tickets_bp.route('', methods=['POST'])
@jwt_required()
def create_ticket():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    required = ['customer_name', 'customer_email', 'subject', 'description', 'priority']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'error': f'{field} is required'}), 400

    priority = data['priority'].lower()
    if priority not in ('urgent', 'medium', 'small'):
        return jsonify({'error': 'Priority must be urgent, medium, or small'}), 400

    # Generate ticket number
    ticket_number = Ticket.generate_ticket_number()

    # Calculate SLA deadlines
    now = datetime.utcnow()
    holidays = get_holidays()
    deadlines = calculate_sla_deadlines(priority, now, holidays)

    ticket = Ticket(
        ticket_number=ticket_number,
        customer_name=data['customer_name'].strip(),
        customer_email=data['customer_email'].strip().lower(),
        subject=data['subject'].strip(),
        description=data['description'].strip(),
        priority=priority,
        status='open',
        response_deadline=deadlines['response_deadline'],
        resolution_deadline=deadlines['resolution_deadline'],
        created_at=now,
        updated_at=now
    )
    db.session.add(ticket)
    db.session.flush()  # Get the ID

    # Audit log
    create_audit_log(ticket.id, 'ticket_created',
                     new_value=f'{ticket_number} - {data["subject"][:100]}',
                     user=user)

    db.session.commit()
    return jsonify({'ticket': ticket.to_dict()}), 201


@tickets_bp.route('/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    # Get messages (all for staff, filter internal for others if needed)
    messages = TicketMessage.query.filter_by(ticket_id=ticket_id)\
        .order_by(TicketMessage.created_at.asc()).all()

    # In this system, only admin/agent roles exist, so they all see internal notes.
    # If we had a customer role, we'd filter here:
    # if user.role == 'customer':
    #     messages = [m for m in messages if not m.is_internal]

    # Get audit logs
    audit_logs = AuditLog.query.filter_by(ticket_id=ticket_id)\
        .order_by(AuditLog.created_at.asc()).all()

    result = ticket.to_dict()
    return jsonify({
        'ticket': result,
        'messages': [m.to_dict() for m in messages],
        'audit_logs': [a.to_dict() for a in audit_logs]
    }), 200


@tickets_bp.route('/<int:ticket_id>/claim', methods=['POST'])
@jwt_required()
def claim_ticket(ticket_id):
    """
    Atomic ticket claiming with database-level concurrency control.
    Prevents two agents from claiming the same unassigned ticket.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role not in ('agent', 'admin'):
        return jsonify({'error': 'Only agents can claim tickets'}), 403

    try:
        # Atomic check-and-update: query for unassigned ticket
        # SQLite uses serialized transactions by default which prevents races
        ticket = Ticket.query.filter_by(
            id=ticket_id,
            assigned_agent_id=None
        ).first()

        if not ticket:
            # Check if ticket exists at all
            existing = db.session.get(Ticket, ticket_id)
            if not existing:
                return jsonify({'error': 'Ticket not found'}), 404
            return jsonify({'error': 'This ticket has already been claimed by another agent'}), 409

        if ticket.status == 'closed':
            return jsonify({'error': 'Cannot claim a closed ticket'}), 400

        old_status = ticket.status
        ticket.assigned_agent_id = user.id
        ticket.status = 'in_progress'
        ticket.updated_at = datetime.utcnow()

        # Audit logs
        create_audit_log(ticket.id, 'ticket_claimed',
                         new_value=user.name, user=user)
        if old_status != 'in_progress':
            create_audit_log(ticket.id, 'status_changed',
                             old_value=old_status, new_value='in_progress',
                             user=user)

        db.session.commit()
        return jsonify({'ticket': ticket.to_dict(), 'message': 'Ticket claimed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to claim ticket. It may have been claimed by another agent.'}), 409


@tickets_bp.route('/<int:ticket_id>', methods=['PATCH'])
@jwt_required()
def update_ticket(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    now = datetime.utcnow()
    holidays = get_holidays()

    # Handle priority change
    if 'priority' in data:
        new_priority = data['priority'].lower()
        if new_priority not in ('urgent', 'medium', 'small'):
            return jsonify({'error': 'Invalid priority'}), 400

        if new_priority != ticket.priority:
            old_priority = ticket.priority
            old_response = ticket.response_deadline
            old_resolution = ticket.resolution_deadline

            # Recalculate SLA from NOW with new priority
            deadlines = calculate_sla_deadlines(new_priority, now, holidays)
            ticket.priority = new_priority
            ticket.response_deadline = deadlines['response_deadline']
            ticket.resolution_deadline = deadlines['resolution_deadline']

            create_audit_log(
                ticket.id, 'priority_changed',
                old_value=f'{old_priority} (resp: {old_response}, res: {old_resolution})',
                new_value=f'{new_priority} (resp: {deadlines["response_deadline"]}, res: {deadlines["resolution_deadline"]})',
                user=user
            )

    # Handle status change
    if 'status' in data:
        new_status = data['status'].lower()
        valid_statuses = ['open', 'in_progress', 'waiting_for_customer', 'resolved', 'closed']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400

        if new_status != ticket.status:
            old_status = ticket.status

            # Pause SLA when going to waiting_for_customer
            if new_status == 'waiting_for_customer' and old_status != 'waiting_for_customer':
                ticket.sla_paused_at = now
                pause_record = SlaPauseRecord(
                    ticket_id=ticket.id,
                    paused_at=now
                )
                db.session.add(pause_record)

            # Resume SLA when leaving waiting_for_customer
            if old_status == 'waiting_for_customer' and new_status != 'waiting_for_customer':
                if ticket.sla_paused_at:
                    pause_duration = int((now - ticket.sla_paused_at).total_seconds())
                    ticket.total_paused_seconds = (ticket.total_paused_seconds or 0) + pause_duration

                    # Update the latest pause record
                    pause_record = SlaPauseRecord.query.filter_by(
                        ticket_id=ticket.id,
                        resumed_at=None
                    ).first()
                    if pause_record:
                        pause_record.resumed_at = now
                        pause_record.duration_seconds = pause_duration

                    # Extend deadlines by pause duration
                    if ticket.response_deadline:
                        ticket.response_deadline += timedelta(seconds=pause_duration)
                    if ticket.resolution_deadline:
                        ticket.resolution_deadline += timedelta(seconds=pause_duration)

                    ticket.sla_paused_at = None

            # Set resolved/closed timestamps
            if new_status == 'resolved':
                ticket.resolved_at = now
            elif new_status == 'closed':
                ticket.closed_at = now

            # Clear resolved/closed if reopening
            if new_status == 'open' and old_status in ('resolved', 'closed'):
                ticket.resolved_at = None
                ticket.closed_at = None

            ticket.status = new_status
            create_audit_log(ticket.id, 'status_changed',
                             old_value=old_status, new_value=new_status,
                             user=user)

    # Handle agent assignment
    if 'assigned_agent_id' in data:
        new_agent_id = data['assigned_agent_id']
        if new_agent_id is not None:
            new_agent_id = int(new_agent_id) if new_agent_id else None

        old_agent_name = ticket.assigned_agent.name if ticket.assigned_agent else 'Unassigned'

        if new_agent_id:
            new_agent = db.session.get(User, new_agent_id)
            if not new_agent:
                return jsonify({'error': 'Agent not found'}), 404
            new_agent_name = new_agent.name
        else:
            new_agent_name = 'Unassigned'

        if new_agent_id != ticket.assigned_agent_id:
            ticket.assigned_agent_id = new_agent_id
            create_audit_log(ticket.id, 'ticket_assigned',
                             old_value=old_agent_name,
                             new_value=new_agent_name,
                             user=user)

    ticket.updated_at = now
    db.session.commit()
    return jsonify({'ticket': ticket.to_dict()}), 200


@tickets_bp.route('/<int:ticket_id>/messages', methods=['POST'])
@jwt_required()
def add_message(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Message content is required'}), 400

    is_internal = data.get('is_internal', False)
    now = datetime.utcnow()

    message = TicketMessage(
        ticket_id=ticket_id,
        user_id=user.id,
        sender_name=user.name,
        content=content,
        is_internal=is_internal,
        created_at=now
    )
    db.session.add(message)

    # Track first response (non-internal agent reply)
    if not is_internal and not ticket.first_response_at and user.role in ('agent', 'admin'):
        ticket.first_response_at = now

    # If ticket was waiting and customer replies, resume SLA
    # (In this system agents simulate customer replies too)
    if ticket.status == 'waiting_for_customer' and not is_internal:
        if ticket.sla_paused_at:
            pause_duration = int((now - ticket.sla_paused_at).total_seconds())
            ticket.total_paused_seconds = (ticket.total_paused_seconds or 0) + pause_duration

            pause_record = SlaPauseRecord.query.filter_by(
                ticket_id=ticket_id,
                resumed_at=None
            ).first()
            if pause_record:
                pause_record.resumed_at = now
                pause_record.duration_seconds = pause_duration

            if ticket.response_deadline:
                ticket.response_deadline += timedelta(seconds=pause_duration)
            if ticket.resolution_deadline:
                ticket.resolution_deadline += timedelta(seconds=pause_duration)

            ticket.sla_paused_at = None

        ticket.status = 'in_progress'
        create_audit_log(ticket_id, 'status_changed',
                         old_value='waiting_for_customer',
                         new_value='in_progress', user=user)

    # Audit log
    if is_internal:
        create_audit_log(ticket_id, 'internal_note_added',
                         new_value=f'Note by {user.name}', user=user)
    else:
        create_audit_log(ticket_id, 'customer_reply_sent',
                         new_value=f'Reply by {user.name}', user=user)

    ticket.updated_at = now
    db.session.commit()
    return jsonify({'message': message.to_dict()}), 201


@tickets_bp.route('/<int:ticket_id>/reopen', methods=['POST'])
@jwt_required()
def reopen_ticket(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    if ticket.status not in ('resolved', 'closed'):
        return jsonify({'error': 'Only resolved or closed tickets can be reopened'}), 400

    # Check 7-day reopen window
    reference_time = ticket.closed_at or ticket.resolved_at
    if reference_time:
        days_since = (datetime.utcnow() - reference_time).days
        if days_since > 7:
            return jsonify({
                'error': f'Reopen window has expired ({days_since} days ago). Please create a new ticket.'
            }), 400

    now = datetime.utcnow()
    old_status = ticket.status
    ticket.status = 'open'
    ticket.resolved_at = None
    ticket.closed_at = None
    ticket.updated_at = now

    create_audit_log(ticket.id, 'ticket_reopened',
                     old_value=old_status, new_value='open',
                     user=user)

    db.session.commit()
    return jsonify({'ticket': ticket.to_dict(), 'message': 'Ticket reopened'}), 200
