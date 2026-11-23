from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer):
    """Public sign-up. Always creates a patient: the role is never taken from the request."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name", "phone")
        extra_kwargs = {"email": {"required": True}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        validate_password(
            attrs["password"], user=User(**{k: v for k, v in attrs.items() if k != "password"})
        )
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(role=User.Role.PATIENT, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "phone", "role")
        read_only_fields = fields
