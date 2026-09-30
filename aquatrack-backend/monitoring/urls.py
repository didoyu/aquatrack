from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("households", views.HouseholdViewSet, basename="household")
router.register("devices", views.DeviceViewSet, basename="device")
router.register("sensors", views.SensorViewSet, basename="sensor")
router.register("readings", views.ReadingViewSet, basename="reading")
router.register("summaries", views.SummaryViewSet, basename="summary")
router.register("logs", views.SystemLogViewSet, basename="log")

urlpatterns = [
    path("", include(router.urls)),
    path("push-tokens/", views.PushTokenView.as_view()),
    path("ingest/readings/", views.IngestReadingsView.as_view()),
    path("ingest/heartbeat/", views.HeartbeatView.as_view()),
]
