from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from monitoring.permissions import IsSuperuser
from monitoring.utils import households_for, resolve_household

from .models import AlertNotification, LeakDetection, MLModelEvaluation
from .serializers import (AlertSerializer, LeakDetectionSerializer, LeakNoteSerializer,
                          MLModelEvaluationSerializer)


class LeakViewSet(viewsets.ReadOnlyModelViewSet):
    """Anomaly Detection screen (Fig. 16) + Stage 1 / Stage 2 warning screens (Fig. 17)."""

    serializer_class = LeakDetectionSerializer
    filterset_fields = ["household", "status", "stage", "category"]
    ordering_fields = ["detected_at", "stage"]

    def get_queryset(self):
        return LeakDetection.objects.filter(household__in=households_for(self.request.user))

    def _transition(self, request, status_value, stamp_field):
        leak = self.get_object()
        note = LeakNoteSerializer(data=request.data)
        note.is_valid(raise_exception=True)
        leak.status = status_value
        setattr(leak, stamp_field, timezone.now())
        if status_value != LeakDetection.Status.INSPECTED and leak.resolved_at is None:
            leak.resolved_at = timezone.now()
        if note.validated_data.get("note"):
            leak.note = note.validated_data["note"]
        leak.save()
        return Response(self.get_serializer(leak).data)

    @extend_schema(request=LeakNoteSerializer)
    @action(detail=True, methods=["post"])
    def inspect(self, request, pk=None):
        """'Mark as inspected' button on the Stage 1 warning screen."""
        return self._transition(request, LeakDetection.Status.INSPECTED, "inspected_at")

    @extend_schema(request=LeakNoteSerializer)
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        return self._transition(request, LeakDetection.Status.RESOLVED, "resolved_at")

    @extend_schema(request=LeakNoteSerializer)
    @action(detail=True, methods=["post"], url_path="false-alarm")
    def false_alarm(self, request, pk=None):
        return self._transition(request, LeakDetection.Status.FALSE_ALARM, "resolved_at")


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    filterset_fields = ["household", "alert_type", "severity", "is_read"]

    def get_queryset(self):
        return AlertNotification.objects.filter(household__in=households_for(self.request.user))

    @extend_schema(request=None, responses=AlertSerializer)
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        alert = self.get_object()
        if not alert.is_read:
            alert.is_read, alert.read_at = True, timezone.now()
            alert.save(update_fields=["is_read", "read_at"])
        return Response(self.get_serializer(alert).data)

    @extend_schema(request=None, responses=dict)
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        household = resolve_household(request)
        n = AlertNotification.objects.filter(household=household, is_read=False).update(
            is_read=True, read_at=timezone.now())
        return Response({"marked_read": n})

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        household = resolve_household(request)
        return Response({"unread": AlertNotification.objects.filter(household=household, is_read=False).count()})


class MLModelEvaluationViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                               viewsets.ReadOnlyModelViewSet):
    """Results of the comparative model study. Maintenance/admin only."""

    serializer_class = MLModelEvaluationSerializer
    permission_classes = [IsSuperuser]
    queryset = MLModelEvaluation.objects.all()
    filterset_fields = ["track", "is_deployed", "model_name"]

    @transaction.atomic
    def _single_deployed(self, instance):
        if instance.is_deployed:
            MLModelEvaluation.objects.filter(track=instance.track).exclude(pk=instance.pk).update(is_deployed=False)

    def perform_create(self, serializer):
        self._single_deployed(serializer.save())

    def perform_update(self, serializer):
        self._single_deployed(serializer.save())

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"])
    def comparison(self, request):
        """Best model per track: forecasting = lowest RMSE, detection = highest F1 (latest run per model)."""
        out = {}
        for track, key, best in (("forecasting", "rmse", min), ("detection", "f1", max)):
            latest = {}
            for e in MLModelEvaluation.objects.filter(track=track).order_by("evaluated_at"):
                latest[e.model_name] = e
            scored = [e for e in latest.values() if key in e.metrics]
            winner = best(scored, key=lambda e: e.metrics[key]) if scored else None
            out[track] = {
                "ranking_metric": key,
                "models": MLModelEvaluationSerializer(list(latest.values()), many=True).data,
                "best": MLModelEvaluationSerializer(winner).data if winner else None,
            }
        return Response(out)
