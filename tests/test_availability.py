import pytest

from accounts.models import User
from scheduling.models import Availability, Doctor

pytestmark = pytest.mark.django_db

MONDAY_MORNING = {"weekday": 0, "start_time": "09:00", "end_time": "13:00"}


def test_doctor_adds_own_availability(client_for, doctor):
    response = client_for(doctor.user).post(
        "/api/availability/", {"doctor": doctor.id, **MONDAY_MORNING}, format="json"
    )

    assert response.status_code == 201
    assert Availability.objects.filter(doctor=doctor).count() == 1


def test_doctor_cannot_manage_another_doctors_availability(client_for, doctor, make_user):
    other_user = make_user("drother", role=User.Role.DOCTOR)
    other = Doctor.objects.create(user=other_user, specialty="Dentistry")

    response = client_for(doctor.user).post(
        "/api/availability/", {"doctor": other.id, **MONDAY_MORNING}, format="json"
    )

    assert response.status_code == 403


def test_patient_cannot_create_availability(client_for, patient, doctor):
    response = client_for(patient).post(
        "/api/availability/", {"doctor": doctor.id, **MONDAY_MORNING}, format="json"
    )

    assert response.status_code == 403


def test_overlapping_blocks_are_rejected(client_for, doctor):
    client = client_for(doctor.user)
    client.post("/api/availability/", {"doctor": doctor.id, **MONDAY_MORNING}, format="json")

    response = client.post(
        "/api/availability/",
        {"doctor": doctor.id, "weekday": 0, "start_time": "12:00", "end_time": "15:00"},
        format="json",
    )

    assert response.status_code == 400


def test_end_must_be_after_start(client_for, admin_user, doctor):
    response = client_for(admin_user).post(
        "/api/availability/",
        {"doctor": doctor.id, "weekday": 2, "start_time": "14:00", "end_time": "10:00"},
        format="json",
    )

    assert response.status_code == 400
    assert "end_time" in response.json()


def test_availability_can_be_filtered_by_doctor(client_for, patient, doctor):
    Availability.objects.create(doctor=doctor, weekday=0, start_time="09:00", end_time="13:00")

    rows = client_for(patient).get(f"/api/availability/?doctor={doctor.id}").json()["results"]

    assert len(rows) == 1
    assert rows[0]["start_time"] == "09:00:00"
