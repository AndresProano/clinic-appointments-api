# Clinic Appointments API

[![CI](https://github.com/AndresProano/clinic-appointments-api/actions/workflows/ci.yml/badge.svg)](https://github.com/AndresProano/clinic-appointments-api/actions/workflows/ci.yml)

REST API to book medical appointments. Patients see a doctor's free slots and book one; doctors manage their weekly hours and see their agenda; admins manage doctors. The API never allows two bookings in the same slot.

Built with **Django REST Framework** and **PostgreSQL**, tested with **pytest** (34 tests) and checked on every pull request by **GitHub Actions** against a real PostgreSQL database.

## Features
- **Roles:** admin, doctor and patient on a custom user model. Public sign-up always creates a patient; the role is never read from the request.
- **JWT auth:** access and refresh tokens (SimpleJWT).
- **Doctors:** admins create a doctor and its account in one transaction; anyone signed in can list them by specialty.
- **Weekly availability:** blocks like "Monday 09:00–13:00"; overlapping blocks are rejected.
- **Free slots:** `GET /api/doctors/{id}/slots/?date=YYYY-MM-DD` splits the doctor's blocks into slots of their appointment length and hides past and booked ones.
- **Conflict-free booking:** a booking must match a real future slot; the doctor and the patient cannot be double-booked (`409 Conflict`).
- **Agenda by role:** patients see their own appointments, doctors see their agenda, admins see everything (filters `?date=` and `?status=`).
- **Cancellation:** the patient, the doctor or an admin can cancel a future appointment, which frees the slot.
- **OpenAPI docs** at `/api/docs/`.

## Endpoints
| Method | Path | Who |
|---|---|---|
| POST | `/api/auth/register/` | anyone (creates a patient) |
| POST | `/api/auth/token/` · `/api/auth/token/refresh/` | anyone |
| GET | `/api/auth/me/` | signed in |
| GET · POST · PATCH · DELETE | `/api/doctors/` | read: signed in · write: admin |
| GET | `/api/doctors/{id}/slots/?date=YYYY-MM-DD` | signed in |
| GET · POST · PATCH · DELETE | `/api/availability/` | read: signed in · write: the doctor or an admin |
| GET · POST | `/api/appointments/` | list: by role · book: patient |
| POST | `/api/appointments/{id}/cancel/` | its patient, its doctor or an admin |
| GET | `/api/health/` | public |

## Design decisions
- **No double booking under concurrency.** Booking runs in a transaction that locks the doctor's row (`SELECT ... FOR UPDATE`), so two simultaneous requests for the same doctor are processed one after the other and the overlap check cannot be raced.
- **Rules in a service layer.** Slot generation, booking and cancellation live in `scheduling/services.py`, separate from views and serializers, so they are easy to read and test.
- **Database constraints too.** `CHECK` constraints make sure every availability block and appointment ends after it starts.
- **Custom user from the first migration,** so roles never require swapping the user model later.
- **Real database in CI.** Tests run against PostgreSQL 16 in GitHub Actions; locally they fall back to SQLite for speed.
- **Time zone aware.** Slots are generated in `America/Guayaquil` and stored in UTC.

## Run with Docker
```bash
cp .env.example .env
docker compose up --build
docker compose exec api python manage.py seed_demo   # demo users and doctors
```
- API docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/
- Demo users: `admin`, `dr.mena`, `dr.paz`, `patient` — password `demo-pass-2026` (local only)

## Try it
```bash
# log in as the demo patient
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "patient", "password": "demo-pass-2026"}' | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

# free slots of doctor 1 on a weekday
curl -s -H "Authorization: Bearer $TOKEN" "localhost:8000/api/doctors/1/slots/?date=2026-12-07"

# book one of them
curl -s -X POST localhost:8000/api/appointments/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"doctor": 1, "start": "2026-12-07T09:30:00-05:00", "reason": "Check-up"}'
```

## Run tests locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                           # SQLite by default; set DATABASE_URL to use PostgreSQL
ruff check . && ruff format --check .
```

## Stack
Python 3.12 · Django 5.2 · Django REST Framework · SimpleJWT · PostgreSQL 16 · drf-spectacular · pytest · Ruff · Docker Compose · GitHub Actions

## License
MIT
