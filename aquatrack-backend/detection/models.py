from django.db import models

from monitoring.models import Household, WaterReading


class LeakDetection(models.Model):
    """One anomaly *event* (a continuous abnormal-consumption episode).

    stage 0 = monitoring (< 24 h), 1 = Stage 1 warning (>= 24 h), 2 = Stage 2 escalated (>= 48 h).
    """

    class Status(models.TextChoices):
        MONITORING = "monitoring", "Monitoring"
        ACTIVE = "active", "Active"
        INSPECTED = "inspected", "Inspected by homeowner"
        RESOLVED = "resolved", "Resolved"
        FALSE_ALARM = "false_alarm", "False alarm"

    class Category(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PASSIVE_LEAK = "passive_leak", "Passive leak"
        ACTIVE_BREACH = "active_breach", "Active breach"

    class Source(models.TextChoices):
        EDGE = "edge", "ESP32 edge flag"
        RULE = "rule", "Continuous-flow rule"
        ML = "ml", "ML model"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="leaks")
    first_reading = models.ForeignKey(WaterReading, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="+")
    detected_at = models.DateTimeField()
    last_abnormal_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    inspected_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MONITORING)
    stage = models.PositiveSmallIntegerField(default=0)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.UNKNOWN)
    detection_source = models.CharField(max_length=10, choices=Source.choices, default=Source.RULE)
    anomaly_score = models.FloatField(default=0, help_text="0-1 severity (duration/48h, or ML score)")
    avg_flow_rate = models.FloatField(null=True, blank=True)
    peak_flow_rate = models.FloatField(null=True, blank=True)
    avg_pressure = models.FloatField(null=True, blank=True)
    baseline_pressure = models.FloatField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [models.Index(fields=["household", "-detected_at"])]

    @property
    def is_open(self):
        return self.resolved_at is None

    @property
    def duration_hours(self):
        return round((self.last_abnormal_at - self.detected_at).total_seconds() / 3600, 2)


class AlertNotification(models.Model):
    class AlertType(models.TextChoices):
        EARLY_WARNING = "early_warning", "Early warning (edge)"
        STAGE1 = "stage1", "Stage 1 warning"
        STAGE2 = "stage2", "Stage 2 critical"
        RESOLVED = "resolved", "Leak event ended"
        DEVICE_OFFLINE = "device_offline", "Device offline"
        DEVICE_ONLINE = "device_online", "Device back online"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="alerts")
    leak_detection = models.ForeignKey(LeakDetection, null=True, blank=True, on_delete=models.CASCADE,
                                       related_name="alerts")
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [models.Index(fields=["household", "is_read"])]


class MLModelEvaluation(models.Model):
    """Stores results of the paper's comparative study (LSTM, GRU, ARIMA, RF, Autoencoder,
    Isolation Forest, One-Class SVM) so the web app can display and pick the best model."""

    class Track(models.TextChoices):
        FORECASTING = "forecasting", "Consumption forecasting"
        DETECTION = "detection", "Anomaly / leak detection"

    model_name = models.CharField(max_length=60)
    track = models.CharField(max_length=20, choices=Track.choices)
    # forecasting: mae, rmse, mape, r2      detection: accuracy, precision, recall, f1
    metrics = models.JSONField(default=dict)
    train_metrics = models.JSONField(default=dict, blank=True, help_text="Side-by-side train scores (overfitting check)")
    dataset_note = models.CharField(max_length=255, blank=True)
    is_deployed = models.BooleanField(default=False)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-evaluated_at"]
