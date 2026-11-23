from rest_framework.permissions import SAFE_METHODS, BasePermission


class CanManageAvailability(BasePermission):
    """Everyone signed in can read; admins and doctors can write (ownership is checked on save)."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin_role or request.user.is_doctor

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.is_admin_role:
            return True
        return obj.doctor.user_id == request.user.id
