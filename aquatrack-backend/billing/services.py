"""Billing prediction (business rule 6): replicate the COWD tiered charge."""
import calendar
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import ExpressionWrapper, F, FloatField, Sum
from django.utils import timezone

from monitoring.models import WaterReading

from .models import BillingForecast, RateSchedule, RateTier

TWO = Decimal("0.01")

# COWD 2025, 1/2-inch residential (paper section 3.2.2, rule 6)
DEFAULT_TIERS = [
    (0, 10, None),          # covered by minimum charge (handled separately)
    (10, 20, "30.55"),
    (20, 30, "31.85"),
    (30, 40, "33.65"),
    (40, None, "36.00"),
]


def ensure_default_schedule():
    schedule = RateSchedule.objects.filter(is_active=True).first()
    if schedule:
        return schedule
    schedule = RateSchedule.objects.create(
        name="COWD 2025 Residential (1/2 inch)", minimum_volume=Decimal("10"),
        minimum_charge=Decimal("218.40"), is_active=True)
    for lower, upper, rate in DEFAULT_TIERS[1:]:
        RateTier.objects.create(schedule=schedule, lower_bound=Decimal(lower),
                                upper_bound=None if upper is None else Decimal(upper),
                                rate_per_cubic_meter=Decimal(rate))
    return schedule


def get_active_schedule():
    return ensure_default_schedule()


def calculate_bill(cubic_meters, schedule=None):
    """Return {'total', 'breakdown', ...} for a monthly consumption in cubic meters.

    <=10 cu.m -> minimum charge; each cu.m above a tier's lower bound is charged at that tier's rate.
    Examples from the paper: 10 -> 218.40, 15 -> 371.15, 27 -> 746.85.
    """
    schedule = schedule or get_active_schedule()
    cum = Decimal(str(max(cubic_meters, 0)))
    total = schedule.minimum_charge
    breakdown = [{"label": f"Minimum charge (first {schedule.minimum_volume:g} cu.m)",
                  "cubic_meters": float(min(cum, schedule.minimum_volume)),
                  "rate": None, "amount": float(schedule.minimum_charge)}]
    for tier in schedule.tiers.all():
        upper = tier.upper_bound if tier.upper_bound is not None else cum
        used = max(Decimal(0), min(cum, upper) - tier.lower_bound)
        if used <= 0:
            continue
        amount = (used * tier.rate_per_cubic_meter)
        total += amount
        label = (f"{tier.lower_bound:g}+ cu.m" if tier.upper_bound is None
                 else f"{tier.lower_bound + 1:g}-{tier.upper_bound:g} cu.m")
        breakdown.append({"label": label, "cubic_meters": float(used),
                          "rate": float(tier.rate_per_cubic_meter),
                          "amount": float(amount.quantize(TWO, ROUND_HALF_UP))})
    total = total.quantize(TWO, ROUND_HALF_UP)
    return {
        "cubic_meters": float(cum),
        "total": total,
        "cost_per_cubic_meter": float((total / cum).quantize(TWO)) if cum > 0 else None,
        "schedule": schedule.name,
        "breakdown": breakdown,
    }


def month_bounds(day):
    start = timezone.make_aware(datetime(day.year, day.month, 1))
    last = calendar.monthrange(day.year, day.month)[1]
    end = start + timedelta(days=last)
    return start, end, last


def liters_between(household, start, end):
    expr = ExpressionWrapper(F("flow_rate") * F("sampling_interval") / 60.0, output_field=FloatField())
    return WaterReading.objects.filter(
        household=household, timestamp__gte=start, timestamp__lt=end
    ).aggregate(total=Sum(expr))["total"] or 0.0


def predict_monthly_with_model(household):
    """Hook for the deployed forecasting model (best of LSTM/GRU/ARIMA). Return cu.m or None."""
    return None


def forecast_month(household, persist=True, now=None):
    """Project this month's consumption and bill.

    Default method ('run_rate'): consumption so far + average daily use of the last 7 days
    x remaining days. Swap in the ML forecast via predict_monthly_with_model()."""
    now = now or timezone.now()
    today = timezone.localdate(now)
    start, end, days_in_month = month_bounds(today)
    consumed_cum = liters_between(household, start, now) / 1000.0

    model_pred = predict_monthly_with_model(household)
    if model_pred is not None:
        method, projected = "ml_model", model_pred
    else:
        method = "run_rate"
        recent_liters = liters_between(household, now - timedelta(days=7), now)
        first_seen = (WaterReading.objects.filter(household=household).order_by("timestamp")
                      .values_list("timestamp", flat=True).first())
        span_days = 7.0
        if first_seen and (now - first_seen) < timedelta(days=7):
            span_days = max((now - first_seen).total_seconds() / 86400.0, 1 / 24)
        daily_cum = (recent_liters / 1000.0) / span_days
        elapsed = (now - start).total_seconds() / 86400.0
        remaining_days = max(days_in_month - elapsed, 0)
        projected = consumed_cum + daily_cum * remaining_days

    bill = calculate_bill(projected)
    avg_flow = (WaterReading.objects.filter(household=household, timestamp__gte=start, timestamp__lt=end)
                .aggregate(a=Sum("flow_rate"))["a"] or 0)
    count = WaterReading.objects.filter(household=household, timestamp__gte=start, timestamp__lt=end).count()
    avg_flow = avg_flow / count if count else 0.0

    result = {
        "forecast_month": start.date().replace(day=1),
        "consumed_to_date": round(consumed_cum, 3),
        "predicted_consumption": round(projected, 3),
        "predicted_bill": bill["total"],
        "average_flow_rate": round(avg_flow, 3),
        "method": method,
        "cost_per_cubic_meter": bill["cost_per_cubic_meter"],
        "breakdown": bill["breakdown"],
        "schedule": bill["schedule"],
    }
    if persist:
        BillingForecast.objects.update_or_create(
            household=household, forecast_month=result["forecast_month"], generated_on=today,
            defaults={"consumed_to_date": result["consumed_to_date"],
                      "predicted_consumption": result["predicted_consumption"],
                      "predicted_bill": result["predicted_bill"],
                      "average_flow_rate": result["average_flow_rate"], "method": method})
    return result


def finalize_previous_month(household, now=None):
    """After month end, store the actual consumption/bill on that month's forecasts (for accuracy metrics)."""
    now = now or timezone.now()
    this_start, _, _ = month_bounds(timezone.localdate(now))
    pending = BillingForecast.objects.filter(household=household, forecast_month__lt=this_start.date(),
                                             actual_bill__isnull=True)
    for month in set(pending.values_list("forecast_month", flat=True)):
        start, end, _ = month_bounds(month)
        actual = liters_between(household, start, end) / 1000.0
        pending.filter(forecast_month=month).update(
            actual_consumption=round(actual, 3), actual_bill=calculate_bill(actual)["total"])
