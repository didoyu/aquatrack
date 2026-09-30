"""Generate a labelled synthetic dataset (paper section 3.7: simulation phase, 3 leak scenarios).

    python manage.py simulate_data --days 30
    python manage.py simulate_data --days 5 --leak-hours 60 --detect     # triggers Stage 1 + Stage 2

Creates demo accounts if missing:  demo@aquatrack.local / demo12345  (homeowner)
                                    maint@aquatrack.local / maint12345 (maintenance)
"""
import math
import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Device, Household, Sensor, WaterReading
from monitoring.services.aggregation import rebuild_for_timestamps

User = get_user_model()

# (name, flow L/min added, pressure drop fraction)
SCENARIOS = [("low-flow drip", 0.5, 0.0), ("moderate leak", 3.0, 0.05), ("sustained abnormal flow", 8.0, 0.20)]


def usage_flow(minute_of_day, rng):
    """Household usage: morning, midday, evening peaks; ~zero at night."""
    events = [(6 * 60 + 30, 25, 7), (12 * 60 + 15, 20, 5), (18 * 60 + 30, 35, 8), (20 * 60, 15, 4)]
    for centre, width, rate in events:
        if abs(minute_of_day - centre) <= width and rng.random() < 0.55:
            return rate * rng.uniform(0.5, 1.4)
    return 0.0


class Command(BaseCommand):
    help = "Create demo users/household/device and simulate labelled 1-minute readings."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--leak-hours", type=int, default=12, help="Duration of each of the 3 leak scenarios")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--detect", action="store_true", help="Run the leak detector over the data (creates events/alerts)")

    def handle(self, *args, **o):
        rng = random.Random(o["seed"])
        owner, _ = User.objects.get_or_create(email="demo@aquatrack.local", defaults={
            "first_name": "Demo", "last_name": "Homeowner", "role": "homeowner"})
        if not owner.has_usable_password():
            owner.set_password("demo12345"); owner.save()
        maint, created = User.objects.get_or_create(email="maint@aquatrack.local", defaults={
            "first_name": "Demo", "last_name": "Maintenance", "role": "maintenance"})
        if created:
            maint.set_password("maint12345"); maint.save()

        household, _ = Household.objects.get_or_create(owner=owner, name="Demo Home",
                                                       defaults={"address": "Cagayan de Oro City"})
        device = Device.objects.filter(household=household).first()
        if device is None:
            device = Device(household=household, device_name="ESP32-DEMO", status="online")
            raw = device.generate_key(); device.save()
            Sensor.objects.create(device=device, sensor_type="flow", model_name="YF-S201")
            Sensor.objects.create(device=device, sensor_type="pressure", model_name="DFRobot Gravity")
            self.stdout.write(self.style.WARNING(f"Demo device API key (save it, shown once): {raw}"))
        sensor = device.sensors.get(sensor_type="flow")

        days, leak_minutes = o["days"], o["leak_hours"] * 60
        end = timezone.now().replace(second=0, microsecond=0)
        start = end - timedelta(days=days)
        total = days * 1440

        # place leak scenarios at ~30%, 55%, 80% of the timeline (skipped if the timeline is too short)
        windows = []
        for (name, add, drop), frac in zip(SCENARIOS, (0.30, 0.55, 0.80)):
            s = int(total * frac)
            if s + leak_minutes < total:
                windows.append((s, s + leak_minutes, add, drop))
        self.stdout.write(f"Simulating {total} readings with {len(windows)} leak window(s)...")

        WaterReading.objects.filter(household=household, leak_label__isnull=False).delete()
        household.flow_run_started_at = None
        household.save(update_fields=["flow_run_started_at"])

        volume, batch, all_readings = 0.0, [], []
        for i in range(total):
            ts = start + timedelta(minutes=i)
            local = timezone.localtime(ts)
            flow = usage_flow(local.hour * 60 + local.minute, rng)
            pressure = 38 - (flow * 0.4) + rng.gauss(0, 0.6)
            label = 0
            for ws, we, add, drop in windows:
                if ws <= i < we:
                    flow += add * rng.uniform(0.9, 1.1)
                    pressure *= (1 - drop)
                    label = 1
            volume += flow
            all_readings.append(WaterReading(
                sensor=sensor, household=household, timestamp=ts, flow_rate=round(flow, 3),
                water_volume=round(volume, 2), pressure_level=round(max(pressure, 0), 2),
                sampling_interval=60, leak_label=label))
            if len(all_readings) >= 5000:
                WaterReading.objects.bulk_create(all_readings, ignore_conflicts=True)
                batch.extend(all_readings); all_readings = []
        if all_readings:
            WaterReading.objects.bulk_create(all_readings, ignore_conflicts=True)
            batch.extend(all_readings)

        rebuild_for_timestamps(household, [r.timestamp for r in batch[::60]] + [batch[-1].timestamp])
        device.status, device.last_seen = "online", timezone.now()
        device.save(update_fields=["status", "last_seen"])

        if o["detect"]:
            from detection.services import process_readings
            self.stdout.write("Running detector...")
            stored = list(WaterReading.objects.filter(household=household).order_by("timestamp"))
            for k in range(0, len(stored), 1440):
                process_readings(household.pk, stored[k:k + 1440])
        self.stdout.write(self.style.SUCCESS(
            f"Done: household id={household.pk}. Login demo@aquatrack.local / demo12345"))
