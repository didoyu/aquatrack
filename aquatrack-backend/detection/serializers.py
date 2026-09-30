from rest_framework import serializers

from .models import AlertNotification, LeakDetection, MLModelEvaluation
from .services import INSPECTION_CHECKLIST


class LeakDetectionSerializer(serializers.ModelSerializer):
    duration_hours = serializers.FloatField(read_only=True)
    classification = serializers.CharField(source="get_category_display", read_only=True)
    recommended_steps = serializers.SerializerMethodField()

    class Meta:
        model = LeakDetection
        fields = ("id", "household", "detected_at", "last_abnormal_at", "resolved_at", "inspected_at",
                  "status", "stage", "category", "classification", "detection_source", "anomaly_score",
                  "avg_flow_rate", "peak_flow_rate", "avg_pressure", "baseline_pressure",
                  "duration_hours", "note", "recommended_steps")
        read_only_fields = fields

    def get_recommended_steps(self, obj):
        if obj.stage >= 2:
            return {"urgency": "critical",
                    "message": "Contact a professional plumber immediately.",
                    "checklist": INSPECTION_CHECKLIST}
        if obj.stage == 1:
            return {"urgency": "warning",
                    "message": "Inspect your plumbing, then mark the issue as inspected.",
                    "checklist": INSPECTION_CHECKLIST}
        return None


class LeakNoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertNotification
        fields = ("id", "household", "leak_detection", "alert_type", "severity", "message",
                  "data", "sent_at", "is_read", "read_at")
        read_only_fields = fields


class MLModelEvaluationSerializer(serializers.ModelSerializer):
    METRIC_KEYS = {
        "forecasting": {"mae", "rmse", "mape", "r2"},
        "detection": {"accuracy", "precision", "recall", "f1"},
    }

    class Meta:
        model = MLModelEvaluation
        fields = ("id", "model_name", "track", "metrics", "train_metrics", "dataset_note",
                  "is_deployed", "evaluated_at")
        read_only_fields = ("id", "evaluated_at")

    def validate(self, attrs):
        allowed = self.METRIC_KEYS[attrs["track"]]
        unknown = set(attrs.get("metrics", {})) - allowed
        if unknown:
            raise serializers.ValidationError(
                {"metrics": f"Unknown metric(s) {sorted(unknown)} for {attrs['track']}. Allowed: {sorted(allowed)}"})
        return attrs
