from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Household


class RolePermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.homeowner = User.objects.create_user(email="home@example.com", password="test-password")
        self.household = Household.objects.create(owner=self.homeowner, name="Home")
        self.other_user = User.objects.create_user(
            email="other@example.com", password="test-password", role="maintenance")
        self.other_household = Household.objects.create(owner=self.other_user, name="Other home")
        self.legacy_admin = User.objects.create_user(
            email="legacy-admin@example.com", password="test-password", role="admin")
        self.legacy_admin_household = Household.objects.create(owner=self.legacy_admin, name="Legacy admin home")
        self.superuser = User.objects.create_superuser(email="admin@example.com", password="test-password")
        self.client = APIClient()

    def test_homeowner_is_limited_to_own_household_and_cannot_administer(self):
        self.client.force_authenticate(self.homeowner)

        response = self.client.get("/api/households/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.household.id])
        self.assertFalse(self.client.get("/api/auth/me/").data["is_superuser"])
        self.assertEqual(self.client.post("/api/households/", {"name": "Another"}).status_code, 403)
        self.assertEqual(self.client.get("/api/logs/").status_code, 403)
        self.assertEqual(self.client.get("/api/ml/evaluations/").status_code, 403)

    def test_non_superuser_role_labels_do_not_grant_admin_access(self):
        for user, household in (
            (self.other_user, self.other_household),
            (self.legacy_admin, self.legacy_admin_household),
        ):
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.get("/api/households/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual([item["id"] for item in response.data["results"]], [household.id])
                self.assertEqual(self.client.get("/api/logs/").status_code, 403)

    def test_superuser_can_access_global_households_and_create_devices(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.get("/api/households/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertTrue(self.client.get("/api/auth/me/").data["is_superuser"])
        device_response = self.client.post(
            "/api/devices/", {"household": self.household.id, "device_name": "ESP32"})
        self.assertEqual(device_response.status_code, 201)
        self.assertTrue(device_response.data["api_key"])

    def test_django_admin_rejects_staff_who_are_not_superusers(self):
        self.other_user.is_staff = True
        self.other_user.save(update_fields=["is_staff"])

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get("/admin/").status_code, 200)


class ESP32IngestTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.homeowner = User.objects.create_user(email="esp@example.com", password="test-password")
        self.household = Household.objects.create(owner=self.homeowner, name="ESP Home")
        self.superuser = User.objects.create_superuser(email="esp-admin@example.com", password="test-password")
        self.client = APIClient()

        self.client.force_authenticate(self.superuser)
        res = self.client.post("/api/devices/", {"household": self.household.id, "device_name": "ESP32-01"})
        self.assertEqual(res.status_code, 201)
        self.device_key = res.data["api_key"]
        self.client.force_authenticate(None)

    def test_heartbeat_ingest_and_live_dashboard_readings(self):
        hb = self.client.post(
            "/api/ingest/heartbeat/",
            {"firmware_version": "1.0.0"},
            format="json",
            HTTP_X_DEVICE_KEY=self.device_key,
        )
        self.assertEqual(hb.status_code, 200)

        ingest = self.client.post(
            "/api/ingest/readings/",
            {"flow_rate": 4.5, "water_volume": 0.375, "sampling_interval": 5, "edge_flag": False},
            format="json",
            HTTP_X_DEVICE_KEY=self.device_key,
        )
        self.assertEqual(ingest.status_code, 201)
        self.assertEqual(ingest.data["stored"], 1)

        self.client.force_authenticate(self.homeowner)
        dash = self.client.get(f"/api/households/{self.household.id}/dashboard/")
        self.assertEqual(dash.status_code, 200)
        self.assertEqual(dash.data["current_flow_rate"], 4.5)
        self.assertEqual(dash.data["today_consumption_liters"], 0.38)
        self.assertEqual(dash.data["devices"][0]["status"], "online")

        readings = self.client.get(f"/api/readings/?household={self.household.id}")
        self.assertEqual(readings.status_code, 200)
        self.assertEqual(readings.data["results"][0]["flow_rate"], 4.5)