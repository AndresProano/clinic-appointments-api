"""Booking rules, kept out of views and serializers so they are easy to read and test."""

from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from scheduling.models import Appointment, Doctor


class BookingError(Exception):
    """The request is not a valid booking (past, not a real slot, wrong state)."""


class BookingConflict(BookingError):
    """The time is already taken by the doctor or by the patient."""


def day_bounds(day: date):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
    return start, start + timedelta(days=1)


def all_slots(doctor: Doctor, day: date) -> list[tuple[datetime, datetime]]:
    """Every slot of `appointment_minutes` inside the doctor's blocks for that weekday."""
    tz = timezone.get_current_timezone()
    step = timedelta(minutes=doctor.appointment_minutes)
    slots = []
    for block in doctor.availabilities.filter(weekday=day.weekday()):
        cursor = timezone.make_aware(datetime.combine(day, block.start_time), tz)
        block_end = timezone.make_aware(datetime.combine(day, block.end_time), tz)
        while cursor + step <= block_end:
            slots.append((cursor, cursor + step))
            cursor += step
    return sorted(slots)


def _overlaps(queryset, start: datetime, end: datetime):
    return queryset.filter(status=Appointment.Status.BOOKED, start__lt=end, end__gt=start)


def free_slots(doctor: Doctor, day: date) -> list[tuple[datetime, datetime]]:
    """Future slots that no booked appointment overlaps."""
    day_start, day_end = day_bounds(day)
    taken = list(
        _overlaps(doctor.appointments.all(), day_start, day_end).values_list("start", "end")
    )
    now = timezone.now()
    return [
        (start, end)
        for start, end in all_slots(doctor, day)
        if start > now and not any(start < t_end and end > t_start for t_start, t_end in taken)
    ]


@transaction.atomic
def book(doctor: Doctor, patient, start: datetime, reason: str = "") -> Appointment:
    # Lock the doctor's row: two requests for the same doctor are handled one after the
    # other, so the overlap check below cannot be beaten by a race (PostgreSQL row lock).
    doctor = Doctor.objects.select_for_update().get(pk=doctor.pk)
    start = timezone.localtime(start)

    if start <= timezone.now():
        raise BookingError("Appointments must be in the future.")

    slots = dict(all_slots(doctor, start.date()))
    if start not in slots:
        raise BookingError("This time is not one of the doctor's slots.")
    end = slots[start]

    if _overlaps(doctor.appointments.all(), start, end).exists():
        raise BookingConflict("This slot is already booked.")
    if _overlaps(Appointment.objects.filter(patient=patient), start, end).exists():
        raise BookingConflict("You already have an appointment at this time.")

    return Appointment.objects.create(
        doctor=doctor, patient=patient, start=start, end=end, reason=reason
    )


def cancel(appointment: Appointment) -> Appointment:
    if appointment.status != Appointment.Status.BOOKED:
        raise BookingError("Only booked appointments can be cancelled.")
    if appointment.start <= timezone.now():
        raise BookingError("Past appointments cannot be cancelled.")
    appointment.status = Appointment.Status.CANCELLED
    appointment.cancelled_at = timezone.now()
    appointment.save(update_fields=["status", "cancelled_at"])
    return appointment
