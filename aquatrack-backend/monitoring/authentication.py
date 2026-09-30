from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Device


class DeviceKeyAuthentication(BaseAuthentication):
    """ESP32 authenticates with header  X-Device-Key: <key>.  request.auth is the Device."""

    keyword = "X-Device-Key"

    def authenticate(self, request):
        raw = request.headers.get(self.keyword)
        if not raw:
            return None
        try:
            device = Device.objects.select_related("household").get(key_hash=Device.hash_key(raw))
        except Device.DoesNotExist:
            raise AuthenticationFailed("Invalid device key.")
        return (AnonymousUser(), device)

    def authenticate_header(self, request):
        return self.keyword
