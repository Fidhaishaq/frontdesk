from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash
from datetime import datetime, date
from app import db
from app.models import User, Ticket, AuditLog, Holiday
from app.middleware import get_current_user, role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Base query - agents see only their relevant tickets
    if user.role == 'agent':
        base_q = Ticket.query.filter(
            db.or_(
                Ticket.assigned_agent_id == user.id,
                Ticket.assigned_agent_id.is_(None)
            )
        )
    else:
        base_q = Ticket.query

    total = base_q.count()
    open_tickets = base_q.filter_by(status='open').count()
    in_progress = base_q.filter_by(status='in_progress').count()
    waiting = base_q.filter_by(status='waiting_for_customer').count()
    resolved = base_q.filter_by(status='resolved').count()
    closed = base_q.filter_by(status='closed').count()

    # Count overdue tickets
    active_tickets = base_q.filter(
        Ticket.status.notin_(['closed', 'resolved'])
    ).all()
    overdue_count = 0
    now = datetime.utcnow()
    for t in active_tickets:
        if t.resolution_deadline and now > t.resolution_deadline:
            overdue_count += 1
        elif not t.first_response_at and t.response_deadline and now > t.response_deadline:
            overdue_count += 1

    # Priority distribution
    urgent = base_q.filter_by(priority='urgent').count()
    medium = base_q.filter_by(priority='medium').count()
    small = base_q.filter_by(priority='small').count()

    # Recent tickets
    recent = base_q.order_by(Ticket.created_at.desc()).limit(10).all()

    return jsonify({
        'total_tickets': total,
        'open_tickets': open_tickets,
        'in_progress_tickets': in_progress,
        'waiting_tickets': waiting,
        'resolved_tickets': resolved,
        'closed_tickets': closed,
        'overdue_tickets': overdue_count,
        'tickets_by_priority': {
            'urgent': urgent,
            'medium': medium,
            'small': small
        },
        'recent_tickets': [t.to_dict() for t in recent]
    }), 200


@admin_bp.route('/agents', methods=['GET'])
@jwt_required()
def list_agents():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    agents = User.query.filter_by(role='agent').order_by(User.name).all()

    result = []
    for agent in agents:
        assigned = Ticket.query.filter(
            Ticket.assigned_agent_id == agent.id,
            Ticket.status.notin_(['closed', 'resolved'])
        ).count()
        resolved = Ticket.query.filter(
            Ticket.assigned_agent_id == agent.id,
            Ticket.status.in_(['resolved', 'closed'])
        ).count()

        agent_dict = agent.to_dict()
        agent_dict['assigned_ticket_count'] = assigned
        agent_dict['resolved_ticket_count'] = resolved
        result.append(agent_dict)

    return jsonify({'agents': result}), 200


@admin_bp.route('/agents', methods=['POST'])
@role_required('admin')
def create_agent():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already in use'}), 409

    agent = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role='agent',
        is_active=True
    )
    db.session.add(agent)
    db.session.commit()

    return jsonify({'agent': agent.to_dict(), 'message': 'Agent created'}), 201


@admin_bp.route('/agents/<int:agent_id>', methods=['PATCH'])
@role_required('admin')
def update_agent(agent_id):
    agent = db.session.get(User, agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404

    if agent.role != 'agent':
        return jsonify({'error': 'Can only edit agents'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    if 'name' in data:
        agent.name = data['name'].strip()
    if 'email' in data:
        new_email = data['email'].strip().lower()
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != agent.id:
            return jsonify({'error': 'Email already in use'}), 409
        agent.email = new_email
    if 'is_active' in data:
        agent.is_active = bool(data['is_active'])

    db.session.commit()
    return jsonify({'agent': agent.to_dict()}), 200


@admin_bp.route('/holidays', methods=['GET'])
@jwt_required()
def list_holidays():
    holidays = Holiday.query.order_by(Holiday.date).all()
    return jsonify({'holidays': [h.to_dict() for h in holidays]}), 200


@admin_bp.route('/holidays', methods=['POST'])
@role_required('admin')
def create_holiday():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    date_str = data.get('date', '')
    name = data.get('name', '').strip()

    if not date_str or not name:
        return jsonify({'error': 'Date and name are required'}), 400

    try:
        holiday_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if Holiday.query.filter_by(date=holiday_date).first():
        return jsonify({'error': 'Holiday already exists for this date'}), 409

    holiday = Holiday(date=holiday_date, name=name)
    db.session.add(holiday)
    db.session.commit()

    return jsonify({'holiday': holiday.to_dict()}), 201


@admin_bp.route('/holidays/<int:holiday_id>', methods=['DELETE'])
@role_required('admin')
def delete_holiday(holiday_id):
    holiday = db.session.get(Holiday, holiday_id)
    if not holiday:
        return jsonify({'error': 'Holiday not found'}), 404

    db.session.delete(holiday)
    db.session.commit()
    return jsonify({'message': 'Holiday deleted'}), 200


@admin_bp.route('/audit', methods=['GET'])
@role_required('admin')
def get_audit_logs():
    query = AuditLog.query

    # Optional filters
    ticket_id = request.args.get('ticket_id', '').strip()
    if ticket_id:
        # Allow filtering by ticket_number like INC-0001
        if ticket_id.upper().startswith('INC-'):
            ticket = Ticket.query.filter_by(ticket_number=ticket_id.upper()).first()
            if ticket:
                query = query.filter_by(ticket_id=ticket.id)
            else:
                return jsonify({'audit_logs': []}), 200
        else:
            try:
                query = query.filter_by(ticket_id=int(ticket_id))
            except ValueError:
                pass

    action = request.args.get('action')
    if action and action != 'all':
        query = query.filter_by(action=action)

    logs = query.order_by(AuditLog.created_at.desc()).limit(500).all()

    # Enrich with ticket_number
    result = []
    for log in logs:
        log_dict = log.to_dict()
        ticket = db.session.get(Ticket, log.ticket_id)
        log_dict['ticket_number'] = ticket.ticket_number if ticket else None
        result.append(log_dict)

    return jsonify({'audit_logs': result}), 200
