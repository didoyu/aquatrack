"""Export readings as a CSV for Jupyter/ML training (paper section 3.7 attributes + derived features).

    python manage.py export_dataset --household 1 --out dataset.csv
"""
import csv
from collections import deque

from django.core.management.base import BaseCommand

from monitoring.models import WaterReading

COLUMNS = ["timestamp", "flow_rate", "water_volume", "pressure_level", "sampling_interval",
           "rolling_avg_flow_15", "zero_flow_duration_min", "leak_label"]


class Command(BaseCommand):
    help = "Export a household's readings with rolling-average and zero-flow-duration features."

    def add_arguments(self, parser):
        parser.add_argument("--household", type=int, required=True)
        parser.add_argument("--out", default="dataset.csv")
        parser.add_argument("--window", type=int, default=15)

    def handle(self, *args, **o):
        window, zero_run, n = deque(maxlen=o["window"]), 0, 0
        qs = WaterReading.objects.filter(household_id=o["household"]).order_by("timestamp")
        with open(o["out"], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for r in qs.iterator(chunk_size=5000):
                window.append(r.flow_rate)
                zero_run = zero_run + r.sampling_interval / 60 if r.flow_rate <= 0.05 else 0
                w.writerow([r.timestamp.isoformat(), r.flow_rate, r.water_volume, r.pressure_level,
                            r.sampling_interval, round(sum(window) / len(window), 4), round(zero_run, 2),
                            "" if r.leak_label is None else r.leak_label])
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Wrote {n} rows to {o['out']}"))
