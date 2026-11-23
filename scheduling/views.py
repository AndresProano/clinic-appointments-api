from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.permissions import IsAdminOrReadOnly
from scheduling import services
from scheduling.models import Appointment, Availability, Doctor
from scheduling.permissions import CanManageAvailability
from scheduling.serializers import (
    AppointmentSerializer,
    AvailabilitySerializer,
    DoctorSerializer,
    SlotSerializer,
)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This time is already taken."
    default_code = "conflict"


def _parse_date(value, name="date"):
    if not value:
        raise ValidationError({name: "Required, format YYYY-MM-DD."})
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({name: "Use the format YYYY-MM-DD."}) from exc


class DoctorViewSet(viewsets.ModelViewSet):
    """List doctors (filter with `?specialty=`); admins create and edit them."""

    serializer_class = DoctorSerializer
    permission_classes = [IsAdminOrReadOnly]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = Doctor.objects.select_related("user")
        specialty = self.request.query_params.get("specialty")
        if specialty:
            queryset = queryset.filter(specialty__iexact=specialty)
        return queryset

    @extend_schema(
        parameters=[OpenApiParameter("date", str, required=True, description="YYYY-MM-DD")],
        responses=SlotSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None):
        """Free slots of this doctor for one day (past and booked slots are left out)."""
        day = _parse_date(request.query_params.get("date"))
        slots = services.free_slots(self.get_object(), day)
        return Response(SlotSerializer([{"start": s, "end": e} for s, e in slots], many=True).data)


class AvailabilityViewSet(viewsets.ModelViewSet):
    """Weekly working blocks. Filter with `?doctor=<id>`."""

    serializer_class = AvailabilitySerializer
    permission_classes = [CanManageAvailability]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = Availability.objects.select_related("doctor__user")
        doctor = self.request.query_params.get("doctor")
        if doctor:
            queryset = queryset.filter(doctor_id=doctor)
        return queryset


class AppointmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Patients book and see their appointments; doctors see their agenda; admins see all.

    Filters: `?date=YYYY-MM-DD`, `?status=booked|cancelled`.
    """

    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related("doctor__user", "patient")
        if user.is_admin_role:
            pass
        elif user.is_doctor:
            queryset = queryset.filter(doctor__user=user)
        else:
            queryset = queryset.filter(patient=user)

        day = self.request.query_params.get("date")
        if day:
            start, end = services.day_bounds(_parse_date(day))
            queryset = queryset.filter(start__gte=start, start__lt=end)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_patient:
            raise PermissionDenied("Only patients can book appointments.")
        data = serializer.validated_data
        try:
            serializer.instance = services.book(
                doctor=data["doctor"],
                patient=self.request.user,
                start=data["start"],
                reason=data.get("reason", ""),
            )
        except services.BookingConflict as exc:
            raise Conflict(str(exc)) from exc
        except services.BookingError as exc:
            raise ValidationError({"start": str(exc)}) from exc

    @extend_schema(request=None, responses=AppointmentSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a future appointment (its patient, its doctor or an admin). Frees the slot."""
        appointment = self.get_object()  # only visible appointments can be reached
        try:
            services.cancel(appointment)
        except services.BookingError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(self.get_serializer(appointment).data)
