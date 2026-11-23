import pytest

from accounts.models import User
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_register_always_creates_a_patient(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "username": "maria",
            "email": "Maria@Example.com",
            "password": PASSWORD,
            "first_name": "Maria",
            "role": "admin",  # ignored on purpose
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(username="maria")
    assert user.role == User.Role.PATIENT
    assert user.email == "maria@example.com"
    assert "password" not in response.json()


def test_register_rejects_duplicate_email_and_weak_password(api_client, patient):
    response = api_client.post(
        "/api/auth/register/",
        {"username": "other", "email": patient.email.upper(), "password": "123"},
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.json()


def test_login_returns_jwt_pair_and_me_shows_the_role(api_client, patient):
    tokens = api_client.post(
        "/api/auth/token/", {"username": "patient", "password": PASSWORD}, format="json"
    ).json()
    assert {"access", "refresh"} <= tokens.keys()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    me = api_client.get("/api/auth/me/")

    assert me.status_code == 200
    assert me.json()["role"] == "patient"


def test_me_requires_authentication(api_client):
    assert api_client.get("/api/auth/me/").status_code == 401
