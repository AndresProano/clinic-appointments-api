import pytest
from rest_framework.test import APIClient

from accounts.models import User
from scheduling.models import Doctor

PASSWORD = "Str0ng-pass-2026"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(username, role=User.Role.PATIENT, **extra):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=PASSWORD,
            role=role,
            **extra,
        )

    return _make


@pytest.fixture
def admin_user(make_user):
    return make_user("admin", role=User.Role.ADMIN)


@pytest.fixture
def patient(make_user):
    return make_user("patient", first_name="Ana", last_name="Vera")


@pytest.fixture
def doctor(make_user):
    user = make_user("drlopez", role=User.Role.DOCTOR, first_name="Luis", last_name="Lopez")
    return Doctor.objects.create(user=user, specialty="Dentistry", appointment_minutes=30)


@pytest.fixture
def client_for(api_client):
    """An API client authenticated as the given user."""

    def _client(user):
        api_client.force_authenticate(user=user)
        return api_client

    return _client
