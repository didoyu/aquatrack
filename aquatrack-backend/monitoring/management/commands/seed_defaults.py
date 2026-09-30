from django.core.management.base import BaseCommand

from billing.services import ensure_default_schedule


class Command(BaseCommand):
    help = "Create the default COWD rate schedule if none exists."

    def handle(self, *args, **opts):
        schedule = ensure_default_schedule()
        self.stdout.write(self.style.SUCCESS(f"Rate schedule ready: {schedule.name}"))
