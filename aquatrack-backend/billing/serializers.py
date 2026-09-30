from rest_framework import serializers

from .models import BillingForecast, RateSchedule, RateTier


class RateTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateTier
        fields = ("lower_bound", "upper_bound", "rate_per_cubic_meter")


class RateScheduleSerializer(serializers.ModelSerializer):
    tiers = RateTierSerializer(many=True, read_only=True)

    class Meta:
        model = RateSchedule
        fields = ("id", "name", "meter_size", "minimum_volume", "minimum_charge", "effective_from", "tiers")


class BillingForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingForecast
        fields = ("id", "household", "forecast_month", "generated_on", "consumed_to_date",
                  "predicted_consumption", "predicted_bill", "average_flow_rate", "method",
                  "actual_consumption", "actual_bill")
