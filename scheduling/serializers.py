from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from accounts.models import User
from scheduling.models import Availability, Doctor


class DoctorSerializer(serializers.ModelSerializer):
    """Read: public doctor card. Write (admins): creates the doctor's user account too."""

    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email", write_only=True)
    username = serializers.CharField(source="user.username", write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = Doctor
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
            "password",
            "specialty",
            "appointment_minutes",
            "bio",
        )

    def validate(self, attrs):
        if self.instance is None:  # creating: the account fields are required
            user_data = attrs.get("user", {})
            missing = [f for f in ("username", "email") if not user_data.get(f)]
            if missing or "password" not in attrs:
                raise serializers.ValidationError(
                    {f: "This field is required." for f in [*missing, "password"]}
                )
            if User.objects.filter(username=user_data["username"]).exists():
                raise serializers.ValidationError({"username": "This username is taken."})
            validate_password(attrs["password"])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")
        password = validated_data.pop("password")
        user = User.objects.create_user(role=User.Role.DOCTOR, password=password, **user_data)
        return Doctor.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("password", None)  # passwords are not changed through this endpoint
        user_data = validated_data.pop("user", {})
        for field in ("first_name", "last_name"):
            if field in user_data:
                setattr(instance.user, field, user_data[field])
        instance.user.save(update_fields=["first_name", "last_name"])
        return super().update(instance, validated_data)


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ("id", "doctor", "weekday", "start_time", "end_time")

    def validate(self, attrs):
        doctor = attrs.get("doctor", getattr(self.instance, "doctor", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))

        if end <= start:
            raise serializers.ValidationError({"end_time": "Must be later than start_time."})

        request = self.context["request"]
        if not request.user.is_admin_role and doctor.user_id != request.user.id:
            raise PermissionDenied("Doctors can only manage their own availability.")

        overlapping = Availability.objects.filter(
            doctor=doctor, weekday=weekday, start_time__lt=end, end_time__gt=start
        )
        if self.instance:
            overlapping = overlapping.exclude(pk=self.instance.pk)
        if overlapping.exists():
            raise serializers.ValidationError("This block overlaps another availability block.")
        return attrs
