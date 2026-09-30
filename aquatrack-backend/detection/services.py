"""Leak detection engine implementing business rules 4 and 5."""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Max
from django.utils import timezone

from monitoring.models import Household, WaterReading

from .ml_inference import predict_anomaly
from .models import AlertNotification, LeakDetection

# Business rule 5: prioritised physical inspection checklist
INSPECTION_CHECKLIST = [
    {"priority": 1, "item": "Toilet cisterns",
     "how": "Add a few drops of food colouring to the tank. If colour shows in the bowl after 15 minutes without flushing, the flapper is leaking."},
    {"priority": 2, "item": "Visible faucets and under-sink areas",
     "how": "Check every tap, supply hose and P-trap for drips, moisture or corrosion."},
    {"priority": 3, "item": "Outdoor tap connections",
     "how": "Inspect garden taps, hose bibs and outdoor pipe joints for wet soil or pooling water."},
    {"priority": 4, "item": "Meter test",
     "how": "Turn off every fixture and check whether the water meter dial still moves."},
]


def cfg():
    return settings.AQUATRACK


def open_event(household):
    return (LeakDetection.objects.filter(household=household, resolved_at__isnull=True)
            .order_by("-detected_at").first())


def create_alert(household, event, alert_type, severity, message, data=None):
    return AlertNotification.objects.create(
        household=household, leak_detection=event, alert_type=alert_type,
        severity=severity, message=message, data=data or {})


def classify_event(event):
    """Heuristic probable-leak category from the pressure-flow signature (rule 5).
    Active breach: high sustained flow and/or a marked pressure drop. Passive leak: low steady flow."""
    window = WaterReading.objects.filter(
        household=event.household, timestamp__gte=event.detected_at, timestamp__lte=event.last_abnormal_at)
    agg = window.aggregate(avg_flow=Avg("flow_rate"), peak=Max("flow_rate"), avg_p=Avg("pressure_level"))
    baseline = (WaterReading.objects
                .filter(household=event.household, is_anomalous=False,
                        timestamp__gte=event.detected_at - timedelta(days=7), timestamp__lt=event.detected_at,
                        pressure_level__isnull=False, flow_rate__gt=0)
                .aggregate(p=Avg("pressure_level"))["p"])
    event.avg_flow_rate, event.peak_flow_rate = agg["avg_flow"], agg["peak"]
    event.avg_pressure, event.baseline_pressure = agg["avg_p"], baseline

    pressure_drop = 0.0
    if baseline and agg["avg_p"] is not None and baseline > 0:
        pressure_drop = (baseline - agg["avg_p"]) / baseline
    if (agg["avg_flow"] or 0) >= cfg()["ACTIVE_BREACH_FLOW"] or pressure_drop >= cfg()["ACTIVE_BREACH_PRESSURE_DROP"]:
        event.category = LeakDetection.Category.ACTIVE_BREACH
    else:
        event.category = LeakDetection.Category.PASSIVE_LEAK


def alert_payload(event):
    return {
        "detected_at": event.detected_at.isoformat(),
        "duration_hours": event.duration_hours,
        "flow_rate": event.avg_flow_rate,
        "peak_flow_rate": event.peak_flow_rate,
        "pressure": event.avg_pressure,
        "category": event.category,
        "checklist": INSPECTION_CHECKLIST,
    }


def evaluate_stage(event):
    """Escalate stage 0 -> 1 (24 h) -> 2 (48 h) and raise the matching alert (rule 4)."""
    hours = event.duration_hours
    event.anomaly_score = min(1.0, hours / cfg()["STAGE2_HOURS"]) if event.detection_source != "ml" else event.anomaly_score
    new_stage = 2 if hours >= cfg()["STAGE2_HOURS"] else 1 if hours >= cfg()["STAGE1_HOURS"] else 0
    if new_stage > event.stage:
        event.stage = new_stage
        if event.status in (LeakDetection.Status.MONITORING, LeakDetection.Status.INSPECTED):
            event.status = LeakDetection.Status.ACTIVE
        classify_event(event)
        event.save()
        if new_stage == 1:
            create_alert(
                event.household, event, AlertNotification.AlertType.STAGE1, AlertNotification.Severity.WARNING,
                f"Possible leak: abnormal water consumption has continued for {hours:.0f} hours. "
                "Please inspect your plumbing using the checklist.", alert_payload(event))
        else:
            create_alert(
                event.household, event, AlertNotification.AlertType.STAGE2, AlertNotification.Severity.CRITICAL,
                f"Critical: abnormal water consumption has continued for {hours:.0f} hours. "
                "Contact a professional plumber immediately.", alert_payload(event))
    else:
        event.save()


def close_event(event, at, auto=True):
    event.resolved_at = at
    if event.status not in (LeakDetection.Status.FALSE_ALARM,):
        event.status = LeakDetection.Status.RESOLVED
    event.save()
    if event.stage >= 1 and auto:
        create_alert(event.household, event, AlertNotification.AlertType.RESOLVED,
                     AlertNotification.Severity.INFO,
                     f"The abnormal consumption episode ended after {event.duration_hours:.0f} hours.",
                     {"duration_hours": event.duration_hours})


@transaction.atomic
def process_readings(household_id, readings):
    """Run the detector over newly stored readings (any order; sorted here).

    Sets reading.is_anomalous, opens/updates/closes LeakDetection events, and raises alerts.
    Anomaly sources, in priority order: ESP32 edge flag, trained ML model, continuous-flow rule.
    """
    if not readings:
        return
    household = Household.objects.select_for_update().get(pk=household_id)
    c = cfg()
    grace = timedelta(minutes=c["ANOMALY_GRACE_MINUTES"])
    run_start = household.flow_run_started_at
    event = open_event(household)
    changed = []

    for r in sorted(readings, key=lambda x: x.timestamp):
        if r.flow_rate <= c["ZERO_FLOW_THRESHOLD"]:
            run_start = None
        elif run_start is None:
            run_start = r.timestamp
        rule_flag = run_start is not None and (r.timestamp - run_start) >= timedelta(minutes=c["CONTINUOUS_FLOW_MINUTES"])

        ml = predict_anomaly(r)
        ml_flag = bool(ml and ml[0])
        source = "edge" if r.edge_flag else "ml" if ml_flag else "rule" if rule_flag else None
        flagged = source is not None

        if flagged != r.is_anomalous:
            r.is_anomalous = flagged
            changed.append(r)

        if flagged:
            if event is None:
                started = run_start if (source == "rule" and run_start) else r.timestamp
                event = LeakDetection.objects.create(
                    household=household, first_reading=r, detected_at=started,
                    last_abnormal_at=r.timestamp, detection_source=source,
                    anomaly_score=ml[1] if ml_flag else 0.0)
                if source == "edge":
                    create_alert(household, event, AlertNotification.AlertType.EARLY_WARNING,
                                 AlertNotification.Severity.INFO,
                                 "Early warning: the sensor unit noticed unusual water flow. "
                                 "We are monitoring it and will alert you if it persists.",
                                 {"flow_rate": r.flow_rate, "pressure": r.pressure_level})
            elif r.timestamp > event.last_abnormal_at:
                event.last_abnormal_at = r.timestamp
        elif event is not None and r.timestamp - event.last_abnormal_at > grace:
            close_event(event, r.timestamp)
            event = None

    if bulk := [r for r in changed if r.pk]:
        WaterReading.objects.bulk_update(bulk, ["is_anomalous"])
    household.flow_run_started_at = run_start
    household.save(update_fields=["flow_run_started_at"])
    if event is not None:
        evaluate_stage(event)
