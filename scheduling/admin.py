from django.contrib import admin

from scheduling.models import Appointment, Availability, Doctor


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("__str__", "specialty", "appointment_minutes")
    search_fields = ("user__first_name", "user__last_name", "specialty")
    inlines = [AvailabilityInline]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("start", "doctor", "patient", "status")
    list_filter = ("status", "doctor")
    date_hierarchy = "start"
