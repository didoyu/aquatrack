"""Run every few minutes (cron / systemd timer on the Raspberry Pi):

    */5 * * * *  cd /home/pi/aquatrack-backend && .venv/bin/python manage.py run_periodic_tasks

- Marks devices offline when the ESP32 stops reporting (business rule 11) and alerts the homeowner
- Re-evaluates open leak events
- Refreshes today's billing forecast and back-fills last month's actuals
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.services import finalize_previous_month, forecast_month
from detection.models import AlertNotification
from detection.services import create_alert, evaluate_stage, open_event
from monitoring.models import Device, Household, SystemLog


class Command(BaseCommand):
    help = "Connectivity check, leak re-evaluation and billing forecast refresh."

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(minutes=settings.AQUATRACK["DEVICE_OFFLINE_MINUTES"])
        stale = Device.objects.filter(status=Device.Status.ONLINE, last_seen__lt=cutoff).select_related("household")
        went_offline = 0
        for device in stale:
            device.status = Device.Status.OFFLINE
            device.save(update_fields=["status"])
            SystemLog.objects.create(level="warning", source="device", device=device, household=device.household,
                                     message=f"{device.device_name} stopped reporting (last seen {device.last_seen:%Y-%m-%d %H:%M}).")
            create_alert(device.household, None, AlertNotification.AlertType.DEVICE_OFFLINE,
                         AlertNotification.Severity.WARNING,
                         f"{device.device_name} lost connection to the server. Readings are buffered on the "
                         "device and will upload when it reconnects.")
            went_offline += 1

        for household in Household.objects.all():
            event = open_event(household)
            if event:
                evaluate_stage(event)
            forecast_month(household, persist=True)
            finalize_previous_month(household)

        self.stdout.write(self.style.SUCCESS(f"Done. Devices marked offline: {went_offline}"))
