import django_filters
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import DeviceKeyAuthentication
from .models import (ConsumptionSummary, Device, Household, PushToken, Sensor,
                     SystemLog, WaterReading)
from .permissions import IsDevice, IsMaintenanceOrAdmin, IsMaintenanceOrReadOnly
from .serializers import (ConsumptionSummarySerializer, DeviceSerializer, HeartbeatSerializer,
                          HouseholdSerializer, PushTokenSerializer, ReadingIngestSerializer,
                          SensorSerializer, SystemLogSerializer, WaterReadingSerializer)
from .services.dashboard import build_dashboard
from .services.ingest import ingest_readings, touch_device
from .utils import households_for
from django.conf import settings


# --------------------------------------------------------------- households
class HouseholdViewSet(viewsets.ModelViewSet):
    serializer_class = HouseholdSerializer

    def get_queryset(self):
        return households_for(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        return Response(build_dashboard(self.get_object()))

    @extend_schema(parameters=[OpenApiParameter("period", str, enum=["daily", "weekly", "monthly"]),
                               OpenApiParameter("limit", int)],
                   responses=ConsumptionSummarySerializer(many=True))
    @action(detail=True, methods=["get"])
    def usage(self, request, pk=None):
        """Usage History screen (Fig. 15): bar-chart data, oldest first."""
        household = self.get_object()
        period = request.query_params.get("period", "daily")
        if period not in ("daily", "weekly", "monthly"):
            return Response({"detail": "period must be daily, weekly or monthly."}, status=400)
        default_limit = {"daily": 7, "weekly": 8, "monthly": 12}[period]
        try:
            limit = min(int(request.query_params.get("limit", default_limit)), 366)
        except ValueError:
            limit = default_limit
        rows = (ConsumptionSummary.objects.filter(household=household, period_type=period)
                .order_by("-period_start")[:limit])
        return Response(ConsumptionSummarySerializer(list(reversed(list(rows))), many=True).data)


# --------------------------------------------------------------- devices & sensors
class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsMaintenanceOrReadOnly]
    filterset_fields = ["household", "status"]

    def get_queryset(self):
        return (Device.objects.filter(household__in=households_for(self.request.user))
                .prefetch_related("sensors"))

    def perform_create(self, serializer):
        device = Device(**serializer.validated_data)
        device._raw_key = device.generate_key()
        device.save()
        Sensor.objects.create(device=device, sensor_type=Sensor.SensorType.FLOW, model_name="YF-S201")
        Sensor.objects.create(device=device, sensor_type=Sensor.SensorType.PRESSURE,
                              model_name="DFRobot Gravity analog pressure")
        SystemLog.objects.create(level="info", source="admin", device=device, household=device.household,
                                 message=f"Device '{device.device_name}' registered by {self.request.user.email}.")
        serializer.instance = device

    @extend_schema(request=None, responses=DeviceSerializer)
    @action(detail=True, methods=["post"], url_path="regenerate-key")
    def regenerate_key(self, request, pk=None):
        """Issue a new API key (old one stops working). The raw key is returned once."""
        device = self.get_object()
        device._raw_key = device.generate_key()
        device.save(update_fields=["key_hash"])
        SystemLog.objects.create(level="warning", source="admin", device=device, household=device.household,
                                 message=f"API key regenerated for '{device.device_name}'.")
        return Response(self.get_serializer(device).data)


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    permission_classes = [IsMaintenanceOrReadOnly]
    filterset_fields = ["device", "sensor_type", "status"]

    def get_queryset(self):
        return Sensor.objects.filter(device__household__in=households_for(self.request.user))


# --------------------------------------------------------------- readings, summaries, logs
class ReadingFilter(django_filters.FilterSet):
    start = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gte")
    end = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = WaterReading
        fields = ["household", "is_anomalous", "leak_label", "start", "end"]


class ReadingViewSet(viewsets.ReadOnlyModelViewSet):
    """Detailed log of individual readings with timestamps (Usage History screen)."""

    serializer_class = WaterReadingSerializer
    filterset_class = ReadingFilter
    ordering_fields = ["timestamp", "flow_rate"]

    def get_queryset(self):
        return WaterReading.objects.filter(household__in=households_for(self.request.user))

    @extend_schema(parameters=[OpenApiParameter("household", int)], responses=WaterReadingSerializer)
    @action(detail=False, methods=["get"])
    def latest(self, request):
        qs = self.filter_queryset(self.get_queryset()).order_by("-timestamp")
        obj = qs.first()
        return Response(WaterReadingSerializer(obj).data if obj else None)


class SummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsumptionSummarySerializer
    filterset_fields = ["household", "period_type"]

    def get_queryset(self):
        return ConsumptionSummary.objects.filter(household__in=households_for(self.request.user))


class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SystemLogSerializer
    permission_classes = [IsMaintenanceOrAdmin]
    queryset = SystemLog.objects.all()
    filterset_fields = ["level", "source", "device", "household"]


class PushTokenView(APIView):
    @extend_schema(request=PushTokenSerializer, responses=PushTokenSerializer)
    def post(self, request):
        s = PushTokenSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj, _ = PushToken.objects.update_or_create(
            token=s.validated_data["token"],
            defaults={"user": request.user, "platform": s.validated_data.get("platform", "")})
        return Response(PushTokenSerializer(obj).data, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------- ESP32 ingest
class IngestReadingsView(APIView):
    """POST one reading, a JSON list, or {"readings": [...]} (buffered upload after reconnect)."""

    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [IsDevice]

    @extend_schema(request=ReadingIngestSerializer(many=True), responses=dict)
    def post(self, request):
        data = request.data
        if isinstance(data, dict) and "readings" in data:
            data = data["readings"]
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            return Response({"detail": "Send a reading object or a non-empty list."}, status=400)
        if len(data) > settings.AQUATRACK["MAX_BATCH_SIZE"]:
            return Response({"detail": f"Max {settings.AQUATRACK['MAX_BATCH_SIZE']} readings per request."}, status=413)
        serializer = ReadingIngestSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        result = ingest_readings(request.auth, serializer.validated_data)
        return Response(result, status=status.HTTP_201_CREATED)


class HeartbeatView(APIView):
    """ESP32 pings this; response includes server time (useful if the ESP32 has no RTC)."""

    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [IsDevice]

    @extend_schema(request=HeartbeatSerializer, responses=dict)
    def post(self, request):
        s = HeartbeatSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        touch_device(request.auth, s.validated_data.get("firmware_version"))
        return Response({"server_time": timezone.now(), "device": request.auth.device_name})
