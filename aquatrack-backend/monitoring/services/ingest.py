"""Store readings from the ESP32 and run the detector (business rules 1, 9, 11)."""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from detection.models import AlertNotification
from detection.services import create_alert, process_readings
from monitoring.models import Device, Sensor, SystemLog, WaterReading

from .aggregation import rebuild_for_timestamps


def get_flow_sensor(device):
    sensor = device.sensors.filter(sensor_type=Sensor.SensorType.FLOW).first()
    if sensor is None:
        sensor = Sensor.objects.create(device=device, sensor_type=Sensor.SensorType.FLOW, model_name="YF-S201")
    return sensor


def touch_device(device, firmware_version=None):
    """Mark device online (and log/alert if it was offline: rule 11 reconnection)."""
    was_offline = device.status == Device.Status.OFFLINE
    device.last_seen = timezone.now()
    fields = ["last_seen"]
    if was_offline:
        device.status = Device.Status.ONLINE
        fields.append("status")
        SystemLog.objects.create(level="info", source="device", device=device, household=device.household,
                                 message=f"{device.device_name} is back online.")
        create_alert(device.household, None, AlertNotification.AlertType.DEVICE_ONLINE,
                     AlertNotification.Severity.INFO, f"{device.device_name} reconnected to the server.")
    if firmware_version and firmware_version != device.firmware_version:
        device.firmware_version = firmware_version
        fields.append("firmware_version")
    device.save(update_fields=fields)


@transaction.atomic
def ingest_readings(device, items):
    """items: list of validated dicts. Idempotent: duplicate (sensor, timestamp) pairs are skipped,
    so the ESP32 can safely re-send its flash buffer after reconnecting."""
    cfg = settings.AQUATRACK
    now = timezone.now()
    latest_allowed = now + timedelta(minutes=cfg["MAX_FUTURE_MINUTES"])
    sensor = get_flow_sensor(device)
    household = device.household

    cleaned, rejected = {}, 0
    for item in items:
        ts = item.get("timestamp") or now
        if ts > latest_allowed:
            rejected += 1
            continue
        cleaned[ts] = item  # de-duplicates inside the batch

    existing = set(WaterReading.objects.filter(sensor=sensor, timestamp__in=list(cleaned)).values_list(
        "timestamp", flat=True))
    new_objs = [
        WaterReading(
            sensor=sensor, household=household, timestamp=ts,
            flow_rate=i["flow_rate"], water_volume=i.get("water_volume", 0.0),
            pressure_level=i.get("pressure_level"), sampling_interval=i.get("sampling_interval", 60),
            edge_flag=i.get("edge_flag", False), leak_label=i.get("leak_label"))
        for ts, i in cleaned.items() if ts not in existing
    ]
    WaterReading.objects.bulk_create(new_objs)
    process_readings(household.pk, new_objs)
    rebuild_for_timestamps(household, [o.timestamp for o in new_objs])
    touch_device(device)
    return {"received": len(items), "stored": len(new_objs),
            "duplicates": len(existing), "rejected": rejected}
