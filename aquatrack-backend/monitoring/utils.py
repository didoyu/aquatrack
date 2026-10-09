from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound

from .models import Household


def households_for(user):
    """Superusers see all households; other users see only their own."""
    if user.is_superuser:
        return Household.objects.all()
    return Household.objects.filter(owner=user)


def resolve_household(request):
    """?household=<id> or the user's first household."""
    qs = households_for(request.user)
    hid = request.query_params.get("household")
    if hid:
        return get_object_or_404(qs, pk=hid)
    household = qs.first()
    if household is None:
        raise NotFound("No household found for this account.")
    return household
