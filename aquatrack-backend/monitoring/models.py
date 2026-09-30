import hashlib
import secrets

from django.conf import settings
from django.db import models


class Household(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="households")
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Detector state: start of the current uninterrupted non-zero flow run
    flow_run_started_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.owner})"


class Device(models.Model):
    """One ESP32 unit. It authenticates to the API with an X-Device-Key header."""

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        MAINTENANCE = "maintenance", "Maintenance"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="devices")
    device_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFLINE)
    key_hash = models.CharField(max_length=64, unique=True, editable=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    firmware_version = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.device_name

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def generate_key(self) -> str:
        """Create a new API key, store only its hash, and return the raw key (show it once)."""
        raw = secrets.token_urlsafe(32)
        self.key_hash = self.hash_key(raw)
        return raw


class Sensor(models.Model):
    class SensorType(models.TextChoices):
        FLOW = "flow", "Flow (YF-S201)"
        PRESSURE = "pressure", "Pressure (DFRobot Gravity)"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FAULTY = "faulty", "Faulty"
        INACTIVE = "inactive", "Inactive"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sensors")
    sensor_type = models.CharField(max_length=20, choices=SensorType.choices)
    model_name = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["device", "sensor_type"], name="uniq_sensor_per_device")]

    def __str__(self):
        return f"{self.device} / {self.sensor_type}"


class WaterReading(models.Model):
    """One timestamped flow + pressure sample (paper: 1-minute sampling)."""

    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="readings")
    # Denormalised for fast per-household time-series queries
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="readings")
    timestamp = models.DateTimeField()
    flow_rate = models.FloatField(help_text="Liters per minute")
    water_volume = models.FloatField(default=0, help_text="Cumulative liters reported by device")
    pressure_level = models.FloatField(null=True, blank=True, help_text="PSI")
    sampling_interval = models.PositiveIntegerField(default=60, help_text="Seconds covered by this sample")
    edge_flag = models.BooleanField(default=False, help_text="ESP32 preliminary anomaly flag")
    is_anomalous = models.BooleanField(default=False, help_text="Set by the server-side detector")
    leak_label = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Ground truth for ML datasets: 0 normal, 1 leak")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["household", "-timestamp"])]
        constraints = [models.UniqueConstraint(fields=["sensor", "timestamp"], name="uniq_reading_per_sensor_ts")]

    @property
    def liters(self):
        """Volume represented by this sample (L/min x seconds / 60)."""
        return self.flow_rate * self.sampling_interval / 60.0


class ConsumptionSummary(models.Model):
    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="summaries")
    period_type = models.CharField(max_length=10, choices=Period.choices)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    total_consumption = models.FloatField(default=0, help_text="Liters")
    average_flow_rate = models.FloatField(default=0)
    peak_flow_rate = models.FloatField(default=0)
    reading_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start"]
        constraints = [models.UniqueConstraint(fields=["household", "period_type", "period_start"],
                                               name="uniq_summary_period")]


class SystemLog(models.Model):
    """Maintenance personnel monitor these (use-case diagram: 'monitor system logs')."""

    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    source = models.CharField(max_length=40, default="system")
    message = models.TextField()
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs")
    household = models.ForeignKey(Household, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PushToken(models.Model):
    """For the future mobile app (Expo push tokens). The web app uses in-app alerts."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
