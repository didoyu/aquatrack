from rest_framework import serializers

from .models import (ConsumptionSummary, Device, Household, PushToken, Sensor,
                     SystemLog, WaterReading)


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ("id", "owner", "name", "address", "created_at")
        read_only_fields = ("id", "owner", "created_at")


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ("id", "device", "sensor_type", "model_name", "status")


class DeviceSerializer(serializers.ModelSerializer):
    sensors = SensorSerializer(many=True, read_only=True)

    class Meta:
        model = Device
        fields = ("id", "household", "device_name", "status", "last_seen",
                  "firmware_version", "created_at", "sensors")
        read_only_fields = ("id", "last_seen", "firmware_version", "created_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        raw = getattr(instance, "_raw_key", None)
        if raw:  # shown only once, at creation / key regeneration
            data["api_key"] = raw
        return data


class WaterReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterReading
        fields = ("id", "household", "sensor", "timestamp", "flow_rate", "water_volume",
                  "pressure_level", "sampling_interval", "edge_flag", "is_anomalous", "leak_label")


class ConsumptionSummarySerializer(serializers.ModelSerializer):
    total_cubic_meters = serializers.SerializerMethodField()

    class Meta:
        model = ConsumptionSummary
        fields = ("id", "household", "period_type", "period_start", "period_end", "total_consumption",
                  "total_cubic_meters", "average_flow_rate", "peak_flow_rate", "reading_count")

    def get_total_cubic_meters(self, obj):
        return round(obj.total_consumption / 1000.0, 4)


class SystemLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemLog
        fields = ("id", "level", "source", "message", "device", "household", "created_at")


class ReadingIngestSerializer(serializers.Serializer):
    """One sample sent by the ESP32. flow_rate is L/min, pressure PSI, sampling_interval seconds."""

    timestamp = serializers.DateTimeField(required=False)
    flow_rate = serializers.FloatField(min_value=0)
    water_volume = serializers.FloatField(min_value=0, required=False, default=0.0)
    pressure_level = serializers.FloatField(min_value=0, required=False, allow_null=True)
    sampling_interval = serializers.IntegerField(min_value=1, max_value=3600, required=False, default=60)
    edge_flag = serializers.BooleanField(required=False, default=False)
    leak_label = serializers.IntegerField(min_value=0, max_value=1, required=False, allow_null=True)


class HeartbeatSerializer(serializers.Serializer):
    firmware_version = serializers.CharField(required=False, allow_blank=True, max_length=40)


class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = ("id", "token", "platform")
