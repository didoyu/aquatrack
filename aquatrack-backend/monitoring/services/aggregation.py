"""Business rule 2: daily / weekly / monthly consumption summaries."""
from datetime import datetime, timedelta

from django.db.models import Avg, ExpressionWrapper, F, FloatField, Max, Sum
from django.utils import timezone

from monitoring.models import ConsumptionSummary, WaterReading


def period_bounds(period_type, day):
    """Return aware (start, end) for the period containing local date `day`."""
    if period_type == "daily":
        first, nxt = day, day + timedelta(days=1)
    elif period_type == "weekly":  # ISO week, Monday start
        first = day - timedelta(days=day.weekday())
        nxt = first + timedelta(days=7)
    else:  # monthly
        first = day.replace(day=1)
        nxt = (first.replace(year=first.year + 1, month=1) if first.month == 12
               else first.replace(month=first.month + 1))
    make = lambda d: timezone.make_aware(datetime(d.year, d.month, d.day))
    return make(first), make(nxt)


def rebuild_summary(household, period_type, day):
    start, end = period_bounds(period_type, day)
    liters = ExpressionWrapper(F("flow_rate") * F("sampling_interval") / 60.0, output_field=FloatField())
    agg = WaterReading.objects.filter(household=household, timestamp__gte=start, timestamp__lt=end).aggregate(
        total=Sum(liters), avg=Avg("flow_rate"), peak=Max("flow_rate"))
    count = WaterReading.objects.filter(household=household, timestamp__gte=start, timestamp__lt=end).count()
    obj, _ = ConsumptionSummary.objects.update_or_create(
        household=household, period_type=period_type, period_start=start,
        defaults={"period_end": end, "total_consumption": agg["total"] or 0.0,
                  "average_flow_rate": agg["avg"] or 0.0, "peak_flow_rate": agg["peak"] or 0.0,
                  "reading_count": count})
    return obj


def rebuild_for_timestamps(household, timestamps):
    """Rebuild every summary touched by a set of reading timestamps."""
    days = {timezone.localdate(ts) for ts in timestamps}
    seen = set()
    for day in days:
        for period in ("daily", "weekly", "monthly"):
            start, _ = period_bounds(period, day)
            if (period, start) in seen:
                continue
            seen.add((period, start))
            rebuild_summary(household, period, day)
