import pytest

from accounts.models import User
from scheduling.models import Doctor
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db

NEW_DOCTOR = {
    "username": "drsoto",
    "email": "soto@example.com",
    "password": PASSWORD,
    "first_name": "Carla",
    "last_name": "Soto",
    "specialty": "Physiotherapy",
    "appointment_minutes": 45,
}


def test_admin_creates_a_doctor_with_its_user_account(client_for, admin_user):
    response = client_for(admin_user).post("/api/doctors/", NEW_DOCTOR, format="json")

    assert response.status_code == 201
    doctor = Doctor.objects.get(user__username="drsoto")
    assert doctor.user.role == User.Role.DOCTOR
    assert doctor.user.check_password(PASSWORD)
    assert "password" not in response.json()


def test_patient_cannot_create_doctors(client_for, patient):
    response = client_for(patient).post("/api/doctors/", NEW_DOCTOR, format="json")

    assert response.status_code == 403


def test_any_signed_in_user_lists_doctors_and_filters_by_specialty(client_for, patient, doctor):
    client = client_for(patient)

    all_doctors = client.get("/api/doctors/").json()["results"]
    dentists = client.get("/api/doctors/?specialty=dentistry").json()["results"]
    others = client.get("/api/doctors/?specialty=cardiology").json()["results"]

    assert [d["last_name"] for d in all_doctors] == ["Lopez"]
    assert len(dentists) == 1
    assert others == []


def test_admin_updates_doctor_names(client_for, admin_user, doctor):
    response = client_for(admin_user).patch(
        f"/api/doctors/{doctor.id}/", {"last_name": "Lopez Ruiz"}, format="json"
    )

    assert response.status_code == 200
    doctor.user.refresh_from_db()
    assert doctor.user.last_name == "Lopez Ruiz"


def test_anonymous_users_cannot_see_doctors(api_client, doctor):
    assert api_client.get("/api/doctors/").status_code == 401
