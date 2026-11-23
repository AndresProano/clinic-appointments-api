from django.contrib import admin

from scheduling.models import Availability, Doctor


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("__str__", "specialty", "appointment_minutes")
    search_fields = ("user__first_name", "user__last_name", "specialty")
    inlines = [AvailabilityInline]
