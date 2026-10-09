from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Device


class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsSuperuserOrReadOnly(BasePermission):
    """Any signed-in user can read; only superusers can create, edit or delete."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_superuser


class IsDevice(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, Device)
