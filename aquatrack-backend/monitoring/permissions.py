from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Device


class IsMaintenanceOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_maintenance)


class IsMaintenanceOrReadOnly(BasePermission):
    """Any signed-in user can read; only maintenance/admin can create, edit or delete."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_maintenance


class IsDevice(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, Device)
