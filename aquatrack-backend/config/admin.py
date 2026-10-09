from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class SuperuserAdminSite(AdminSite):
    def has_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)


class SuperuserAdminConfig(AdminConfig):
    default_site = "config.admin.SuperuserAdminSite"