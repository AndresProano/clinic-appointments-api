from rest_framework import generics
from rest_framework.permissions import AllowAny

from accounts.serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Create a patient account."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class MeView(generics.RetrieveAPIView):
    """The authenticated user, with their role."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
