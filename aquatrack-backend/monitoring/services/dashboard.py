"""Data for the Dashboard screen (Fig. 14): flow rate, daily consumption, max daily, avg hourly."""
from datetime import datetime, timedelta

from django.db.models import ExpressionWrapper, F, FloatField, Max, Sum
from django.utils import timezone

from detection.models import AlertNotification, LeakDetection
from detection.services import open_event
from monitoring.models import ConsumptionSummary, WaterReading


def build_dashboard(household):
    from billing.services import forecast_month  # local import avoids a circular dependency

    now = timezone.now()
    today = timezone.localdate(now)
    day_start = timezone.make_aware(datetime(today.year, today.month, today.day))
    month_start = day_start.replace(day=1)

    latest = WaterReading.objects.filter(household=household).order_by("-timestamp").first()
    liters = ExpressionWrapper(F("flow_rate") * F("sampling_interval") / 60.0, output_field=FloatField())
    today_liters = (WaterReading.objects.filter(household=household, timestamp__gte=day_start)
                    .aggregate(t=Sum(liters))["t"] or 0.0)
    max_daily = (ConsumptionSummary.objects.filter(household=household, period_type="daily",
                                                   period_start__gte=month_start)
                 .aggregate(m=Max("total_consumption"))["m"] or 0.0)
    max_daily = max(max_daily, today_liters)
    hours_elapsed = max((now - day_start).total_seconds() / 3600.0, 1 / 60)

    event = open_event(household)
    devices = [{"id": d.id, "name": d.device_name, "status": d.status, "last_seen": d.last_seen}
               for d in household.devices.all()]
    projection = forecast_month(household, persist=False)

    return {
        "household": {"id": household.id, "name": household.name},
        "current_flow_rate": latest.flow_rate if latest else None,
        "current_pressure": latest.pressure_level if latest else None,
        "last_reading_at": latest.timestamp if latest else None,
        "today_consumption_liters": round(today_liters, 2),
        "max_daily_consumption_liters": round(max_daily, 2),
        "average_hourly_usage_liters": round(today_liters / hours_elapsed, 2),
        "devices": devices,
        "active_leak": None if event is None else {
            "id": event.id, "stage": event.stage, "status": event.status,
            "detected_at": event.detected_at, "duration_hours": event.duration_hours,
            "category": event.category},
        "unread_alerts": AlertNotification.objects.filter(household=household, is_read=False).count(),
        "projected_bill": projection["predicted_bill"],
        "projected_consumption_cubic_meters": projection["predicted_consumption"],
    }
