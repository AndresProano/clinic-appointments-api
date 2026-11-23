from rest_framework import viewsets

from accounts.permissions import IsAdminOrReadOnly
from scheduling.models import Availability, Doctor
from scheduling.permissions import CanManageAvailability
from scheduling.serializers import AvailabilitySerializer, DoctorSerializer


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
