from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from detection.models import AlertNotification, LeakDetection
from monitoring.models import Device, Household, Sensor
from monitoring.services.ingest import ingest_readings


class TwoStageDetectionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(email="t@example.com", password="x12345678")
        self.household = Household.objects.create(owner=user, name="Test")
        self.device = Device(household=self.household, device_name="esp")
        self.device.generate_key()
        self.device.save()
        Sensor.objects.create(device=self.device, sensor_type="flow")

    def _send(self, start, hours, flow=1.0, flag=False):
        items = [{"timestamp": start + timedelta(minutes=m), "flow_rate": flow, "edge_flag": flag}
                 for m in range(0, hours * 60, 5)]
        return ingest_readings(self.device, items)

    def test_stage_1_then_stage_2(self):
        start = timezone.now() - timedelta(hours=60)
        self._send(start, 25, flag=True)                     # 25 h abnormal -> Stage 1
        leak = LeakDetection.objects.get()
        self.assertEqual(leak.stage, 1)
        self._send(start + timedelta(hours=25), 25, flag=True)  # 50 h -> Stage 2
        leak.refresh_from_db()
        self.assertEqual(leak.stage, 2)
        types = set(AlertNotification.objects.values_list("alert_type", flat=True))
        self.assertTrue({"stage1", "stage2"} <= types)

    def test_short_event_no_stage_alert(self):
        start = timezone.now() - timedelta(hours=10)
        self._send(start, 3, flag=True)
        self.assertEqual(LeakDetection.objects.get().stage, 0)
        self.assertFalse(AlertNotification.objects.filter(alert_type__in=["stage1", "stage2"]).exists())

    def test_duplicate_readings_are_ignored(self):
        start = timezone.now() - timedelta(hours=2)
        first = self._send(start, 1, flow=2.0)
        again = self._send(start, 1, flow=2.0)
        self.assertEqual(first["stored"], again["duplicates"])
        self.assertEqual(again["stored"], 0)
