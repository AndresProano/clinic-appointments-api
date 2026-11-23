from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from scheduling.models import Appointment, Availability, Doctor

pytestmark = pytest.mark.django_db


def next_weekday(weekday: int, weeks_ahead: int = 1) -> date:
    """A date with the given weekday at least `weeks_ahead` weeks from today (always future)."""
    today = timezone.localdate()
    return today + timedelta(days=(weekday - today.weekday()) % 7 + 7 * weeks_ahead)


def at(day: date, hour: int, minute: int = 0) -> str:
    local = timezone.make_aware(datetime(day.year, day.month, day.day, hour, minute))
    return local.isoformat()


@pytest.fixture
def monday():
    return next_weekday(0)


@pytest.fixture
def doctor_with_hours(doctor):
    # Mondays 09:00-11:00, 30-minute appointments -> 4 slots
    Availability.objects.create(doctor=doctor, weekday=0, start_time="09:00", end_time="11:00")
    return doctor


def book(client, doctor, start, reason="Check-up"):
    return client.post(
        "/api/appointments/", {"doctor": doctor.id, "start": start, "reason": reason}, format="json"
    )


# --- free slots -------------------------------------------------------------


def test_slots_lists_every_free_slot_of_the_day(client_for, patient, doctor_with_hours, monday):
    response = client_for(patient).get(f"/api/doctors/{doctor_with_hours.id}/slots/?date={monday}")

    assert response.status_code == 200
    starts = [
        timezone.localtime(datetime.fromisoformat(s["start"])).strftime("%H:%M")
        for s in response.json()
    ]
    assert starts == ["09:00", "09:30", "10:00", "10:30"]


def test_day_without_availability_has_no_slots(client_for, patient, doctor_with_hours, monday):
    tuesday = monday + timedelta(days=1)

    response = client_for(patient).get(f"/api/doctors/{doctor_with_hours.id}/slots/?date={tuesday}")

    assert response.json() == []


def test_slots_require_a_valid_date(client_for, patient, doctor_with_hours):
    client = client_for(patient)

    assert client.get(f"/api/doctors/{doctor_with_hours.id}/slots/").status_code == 400
    assert (
        client.get(f"/api/doctors/{doctor_with_hours.id}/slots/?date=31-12-2026").status_code == 400
    )


# --- booking ----------------------------------------------------------------


def test_patient_books_a_free_slot_and_it_disappears(
    client_for, patient, doctor_with_hours, monday
):
    client = client_for(patient)

    response = book(client, doctor_with_hours, at(monday, 9, 30))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "booked"
    assert body["patient"] == patient.id
    assert datetime.fromisoformat(body["end"]) - datetime.fromisoformat(body["start"]) == timedelta(
        minutes=30
    )
    slots = client.get(f"/api/doctors/{doctor_with_hours.id}/slots/?date={monday}").json()
    assert len(slots) == 3


def test_same_slot_cannot_be_booked_twice(
    client_for, patient, make_user, doctor_with_hours, monday
):
    book(client_for(patient), doctor_with_hours, at(monday, 10))
    other = make_user("other")

    response = book(client_for(other), doctor_with_hours, at(monday, 10))

    assert response.status_code == 409
    assert Appointment.objects.count() == 1


@pytest.mark.parametrize(
    ("hour", "minute"),
    [(10, 10), (12, 0), (8, 30)],  # not aligned, after the block, before the block
)
def test_only_real_slots_can_be_booked(
    client_for, patient, doctor_with_hours, monday, hour, minute
):
    response = book(client_for(patient), doctor_with_hours, at(monday, hour, minute))

    assert response.status_code == 400
    assert "start" in response.json()


def test_past_slots_cannot_be_booked(client_for, patient, doctor_with_hours):
    last_monday = next_weekday(0, weeks_ahead=-1)

    response = book(client_for(patient), doctor_with_hours, at(last_monday, 9))

    assert response.status_code == 400


def test_patient_cannot_have_two_appointments_at_the_same_time(
    client_for, patient, make_user, doctor_with_hours, monday
):
    other_doctor = Doctor.objects.create(
        user=make_user("drother", role=User.Role.DOCTOR), specialty="Physiotherapy"
    )
    Availability.objects.create(
        doctor=other_doctor, weekday=0, start_time="09:00", end_time="11:00"
    )
    client = client_for(patient)
    book(client, doctor_with_hours, at(monday, 9))

    response = book(client, other_doctor, at(monday, 9))

    assert response.status_code == 409


def test_doctors_cannot_book(client_for, doctor_with_hours, monday):
    response = book(client_for(doctor_with_hours.user), doctor_with_hours, at(monday, 9))

    assert response.status_code == 403


# --- who sees what ----------------------------------------------------------


def test_each_role_sees_the_right_appointments(
    client_for, patient, make_user, admin_user, doctor_with_hours, monday
):
    other = make_user("other")
    book(client_for(patient), doctor_with_hours, at(monday, 9))
    book(client_for(other), doctor_with_hours, at(monday, 9, 30))

    def count(user):
        return client_for(user).get("/api/appointments/").json()["count"]

    assert count(patient) == 1
    assert count(other) == 1
    assert count(doctor_with_hours.user) == 2
    assert count(admin_user) == 2


def test_agenda_can_be_filtered_by_date(client_for, patient, doctor_with_hours, monday):
    book(client_for(patient), doctor_with_hours, at(monday, 9))
    client = client_for(doctor_with_hours.user)

    assert client.get(f"/api/appointments/?date={monday}").json()["count"] == 1
    assert client.get(f"/api/appointments/?date={monday + timedelta(days=1)}").json()["count"] == 0


# --- cancelling -------------------------------------------------------------


def test_cancelling_frees_the_slot(client_for, patient, doctor_with_hours, monday):
    client = client_for(patient)
    appointment_id = book(client, doctor_with_hours, at(monday, 9)).json()["id"]

    response = client.post(f"/api/appointments/{appointment_id}/cancel/")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert book(client, doctor_with_hours, at(monday, 9)).status_code == 201


def test_cannot_cancel_twice(client_for, patient, doctor_with_hours, monday):
    client = client_for(patient)
    appointment_id = book(client, doctor_with_hours, at(monday, 9)).json()["id"]
    client.post(f"/api/appointments/{appointment_id}/cancel/")

    assert client.post(f"/api/appointments/{appointment_id}/cancel/").status_code == 400


def test_other_patients_cannot_see_or_cancel(
    client_for, patient, make_user, doctor_with_hours, monday
):
    appointment_id = book(client_for(patient), doctor_with_hours, at(monday, 9)).json()["id"]
    stranger = client_for(make_user("stranger"))

    assert stranger.get(f"/api/appointments/{appointment_id}/").status_code == 404
    assert stranger.post(f"/api/appointments/{appointment_id}/cancel/").status_code == 404


def test_doctor_can_cancel_an_appointment_in_their_agenda(
    client_for, patient, doctor_with_hours, monday
):
    appointment_id = book(client_for(patient), doctor_with_hours, at(monday, 9)).json()["id"]

    response = client_for(doctor_with_hours.user).post(
        f"/api/appointments/{appointment_id}/cancel/"
    )

    assert response.status_code == 200
