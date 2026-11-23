# Clinic Appointments API

REST API to book medical appointments: roles (admin, doctor, patient), doctor availability, free slots and conflict-free booking.

Built with **Django REST Framework** and **PostgreSQL**, tested with **pytest** and checked on every pull request by **GitHub Actions**.

> Work in progress: the project is being built in small pull requests. See the [pull requests](../../pulls?q=is%3Apr) for the history.

## Stack
Python 3.12 · Django 5.2 · Django REST Framework · PostgreSQL 16 · drf-spectacular (OpenAPI) · pytest · Ruff · Docker Compose · GitHub Actions

## Run with Docker
```bash
cp .env.example .env
docker compose up --build
```
- Health check: http://localhost:8000/api/health/
- API docs (Swagger): http://localhost:8000/api/docs/

## Run tests locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                           # SQLite by default; set DATABASE_URL to use PostgreSQL
ruff check . && ruff format --check .
```

## License
MIT
