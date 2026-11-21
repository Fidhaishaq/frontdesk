# 🎫 Frontdesk — Support Ticket System for Arvo Systems

A production-ready customer support ticket management system replacing a shared spreadsheet + WhatsApp workflow. Built for 9 support agents handling ~40 tickets/day.

---

## Features

- **Priority-based SLA tracking** (Urgent / Medium / Small) with live deadline displays
- **Business-hours SLA clock** (Mon–Fri 09:30–18:30, excluding configurable Indian public holidays)
- **SLA pause/resume** — clock pauses when waiting on customer, resumes on reply
- **Atomic ticket claiming** — database-level transaction prevents two agents from claiming the same ticket
- **Internal notes** — never visible to customers in any API response
- **Full audit trail** — every action recorded with actor, timestamp, before/after values; immutable (no update/delete endpoints)
- **Auto-close** — tickets with no customer reply for 5 business days close automatically (scheduler runs every 15 min)
- **Reopen window** — tickets can be reopened within 7 calendar days of resolution
- **Priority escalation** — SLA clock resets from moment of change (see Design Decision below)
- **Role-based access** — Admin / Agent roles with appropriate permissions

---

## SLA Configuration

| Priority | First Response | Resolution |
|----------|---------------|------------|
| Urgent | 2 working hours | Same working day (9 hours) |
| Medium | Half working day (4.5 hours) | 3 working days (27 hours) |
| Small | 1 working day (9 hours) | 1 working week (45 hours) |

**Business hours:** Monday–Friday, 09:30–18:30, excluding configured holidays.

---

## Design Decision: Priority Change Mid-Ticket

**Question**: What happens to the SLA timer if a ticket's priority is changed mid-way?

**Decision**: The SLA deadlines are **recalculated from the moment of the priority change**, not from ticket creation.

**Rationale**: If a ticket starts as "Small" (45-hour SLA) and after 40 hours is escalated to "Urgent" (9-hour SLA), keeping the original creation time would make the ticket instantly and permanently breached — giving agents no actionable window to respond. Recalculating from the escalation moment gives agents the full SLA window for the new priority level. The audit log records the old priority, old deadlines, new priority, and new deadlines with a precise timestamp.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Flask |
| ORM | SQLAlchemy |
| Database | SQLite (dev) / MySQL (prod) |
| Auth | JWT (7-day tokens) |
| Frontend | React + Vite |
| Styling | Vanilla CSS |
| Background Jobs | APScheduler |

---

## Running Locally

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm

### 1. Clone and set up

```bash
git clone <repo-url>
cd frontdesk
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

Seed the database with demo data:
```bash
python seed.py
```

Start the backend:
```bash
python run.py
# Backend runs on http://localhost:5000
```

### 3. Frontend setup

```bash
cd ../frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
# API calls are proxied to http://localhost:5000
```

### 4. Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@arvo.com | Admin123! |
| Agent 1 | agent1@arvo.com | Agent123! |
| Agent 2 | agent2@arvo.com | Agent123! |
| Agent 3 | agent3@arvo.com | Agent123! |
| ... | ... | ... |
| Agent 9 | agent9@arvo.com | Agent123! |

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

Tests cover all 13 required scenarios:
1. Agent login
2. Agent claim ticket
3. Double-claim prevention (409 Conflict)
4. Customer replies visible
5. Private notes access control
6. SLA excludes weekends
7. SLA excludes holidays
8. SLA pauses during customer waiting
9. Overdue detection
10. Auto-close after waiting period
11. Reopen within window
12. Audit history completeness
13. Audit immutability

---

## Project Structure

```
frontdesk/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── sla.py               # SLA calculation engine
│   │   ├── middleware.py         # Auth decorators
│   │   ├── scheduler.py         # Background jobs (auto-close)
│   │   └── routes/
│   │       ├── auth.py          # Login / verify
│   │       ├── tickets.py       # Ticket CRUD + operations
│   │       └── admin.py         # Stats, agents, holidays, audit
│   ├── tests/
│   │   ├── conftest.py          # Pytest fixtures
│   │   ├── test_sla.py          # SLA calculations
│   │   └── test_tickets.py      # Ticket operations
│   ├── seed.py                  # Demo data
│   ├── run.py                   # Entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # Shared UI components
│   │   ├── contexts/            # React contexts (Auth)
│   │   ├── pages/               # Route pages
│   │   ├── services/            # API client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css            # Design system
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .gitignore
├── Procfile
└── README.md
```

---

## API Reference

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | Login → returns JWT |
| GET | /api/auth/me | Verify token |

### Tickets
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/tickets | List tickets (role-filtered) |
| POST | /api/tickets | Create ticket |
| GET | /api/tickets/:id | Get ticket with messages + audit |
| POST | /api/tickets/:id/claim | Atomic claim (transaction-locked) |
| PATCH | /api/tickets/:id | Update priority/status/assignment |
| POST | /api/tickets/:id/messages | Add reply or internal note |
| POST | /api/tickets/:id/reopen | Reopen resolved/closed ticket |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/admin/stats | Dashboard statistics |
| GET | /api/admin/agents | Agent list with ticket counts |
| POST | /api/admin/agents | Create agent |
| PATCH | /api/admin/agents/:id | Update agent |
| GET | /api/admin/holidays | Holiday list |
| POST | /api/admin/holidays | Add holiday |
| DELETE | /api/admin/holidays/:id | Remove holiday |
| GET | /api/admin/audit | Full audit history |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| FLASK_ENV | Environment (development/production) | development |
| SECRET_KEY | Flask secret key | dev-secret-key |
| JWT_SECRET_KEY | JWT signing key | dev-jwt-secret |
| DATABASE_URL | Database connection string | sqlite:///frontdesk.db |

For MySQL production:
```
DATABASE_URL=mysql+pymysql://user:password@host:3306/frontdesk
```

---

## Security

- JWT authentication on all protected routes
- Internal notes (`is_internal: true`) filtered at the API layer — never exposed in customer-facing responses
- Ticket claiming uses database transactions — race condition between simultaneous claims is prevented
- Passwords hashed with Werkzeug (pbkdf2)
- Audit log entries are append-only — no update or delete endpoints exist
- Input validation on all routes with proper HTTP status codes

---

## Deployment

### Backend (Render / Railway)

1. Set environment variables:
   ```
   DATABASE_URL=mysql+pymysql://user:password@host:3306/frontdesk
   JWT_SECRET_KEY=<strong random string>
   SECRET_KEY=<strong random string>
   FLASK_ENV=production
   ```
2. Build command: `cd backend && pip install -r requirements.txt`
3. Start command: `cd backend && python run.py`
4. After first deploy, seed the database: `python seed.py`

### Frontend (Vercel / Netlify)

1. Set root directory: `frontend`
2. Build command: `npm run build`
3. Output directory: `dist`
4. Set environment variable: `VITE_API_URL=<your backend URL>`
5. Update `vite.config.js` proxy target for production

---

## Database Schema

### Tables
- **users** — Admin and agent accounts with password hashes
- **tickets** — All ticket data with SLA deadlines and status tracking
- **ticket_messages** — Customer replies and private internal notes (distinguished by `is_internal` flag)
- **audit_logs** — Immutable append-only action history
- **holidays** — Configurable holidays excluded from SLA calculations
- **sla_pause_records** — Records of when SLA was paused/resumed with durations
