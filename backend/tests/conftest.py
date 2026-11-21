import pytest
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Ticket, Holiday
from datetime import date


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key-that-is-long-enough-for-hs256-validation',
        'SECRET_KEY': 'test-secret-key-that-is-long-enough-for-flask',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    with app.app_context():
        db.create_all()

        # Create test admin
        admin = User(
            name='Test Admin',
            email='admin@test.com',
            password_hash=generate_password_hash('Admin123!'),
            role='admin',
            is_active=True
        )
        db.session.add(admin)

        # Create test agent
        agent = User(
            name='Test Agent',
            email='agent@test.com',
            password_hash=generate_password_hash('Agent123!'),
            role='agent',
            is_active=True
        )
        db.session.add(agent)

        # Create second agent for double-claim test
        agent2 = User(
            name='Test Agent 2',
            email='agent2@test.com',
            password_hash=generate_password_hash('Agent123!'),
            role='agent',
            is_active=True
        )
        db.session.add(agent2)

        # Add test holidays
        db.session.add(Holiday(date=date(2025, 1, 26), name='Republic Day'))
        db.session.add(Holiday(date=date(2025, 8, 15), name='Independence Day'))

        db.session.commit()

        yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def admin_headers(client):
    """Login as admin and return auth headers."""
    response = client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'Admin123!'
    })
    token = response.get_json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture
def agent_headers(client):
    """Login as agent and return auth headers."""
    response = client.post('/api/auth/login', json={
        'email': 'agent@test.com',
        'password': 'Agent123!'
    })
    token = response.get_json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture
def agent2_headers(client):
    """Login as second agent and return auth headers."""
    response = client.post('/api/auth/login', json={
        'email': 'agent2@test.com',
        'password': 'Agent123!'
    })
    token = response.get_json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture
def sample_ticket(client, admin_headers):
    """Create a sample ticket and return its data."""
    response = client.post('/api/tickets', json={
        'customer_name': 'Test Customer',
        'customer_email': 'customer@test.com',
        'subject': 'Test Issue',
        'description': 'This is a test ticket description',
        'priority': 'medium'
    }, headers=admin_headers)
    return response.get_json()['ticket']
