"""Demo data for local development: an admin, two doctors with weekday hours and a patient."""

from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from scheduling.models import Availability, Doctor

DEMO_PASSWORD = "demo-pass-2026"  # local demo only

DOCTORS = [
    ("dr.mena", "Sofia", "Mena", "Dentistry", 30),
    ("dr.paz", "Diego", "Paz", "Physiotherapy", 45),
]


class Command(BaseCommand):
    help = "Create demo users, doctors and availability (local development only)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                "admin", "admin@example.com", DEMO_PASSWORD, role=User.Role.ADMIN
            )

        for username, first, last, specialty, minutes in DOCTORS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first,
                    "last_name": last,
                    "role": User.Role.DOCTOR,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            doctor, _ = Doctor.objects.get_or_create(
                user=user, defaults={"specialty": specialty, "appointment_minutes": minutes}
            )
            for weekday in range(5):  # Monday to Friday, 09:00-13:00
                Availability.objects.get_or_create(
                    doctor=doctor, weekday=weekday, start_time=time(9), end_time=time(13)
                )

        if not User.objects.filter(username="patient").exists():
            User.objects.create_user(
                "patient", "patient@example.com", DEMO_PASSWORD, first_name="Ana", last_name="Vera"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready. Users: admin, dr.mena, dr.paz, patient / {DEMO_PASSWORD}"
            )
        )
