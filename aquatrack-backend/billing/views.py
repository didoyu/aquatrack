from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.models import ConsumptionSummary
from monitoring.utils import households_for, resolve_household

from .models import BillingForecast
from .serializers import BillingForecastSerializer, RateScheduleSerializer
from .services import calculate_bill, forecast_month, get_active_schedule


class RatesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=RateScheduleSerializer)
    def get(self, request):
        return Response(RateScheduleSerializer(get_active_schedule()).data)


class CalculateView(APIView):
    """Bill calculator: GET /api/billing/calculate/?cubic_meters=27"""

    permission_classes = [AllowAny]

    @extend_schema(parameters=[OpenApiParameter("cubic_meters", float, required=True)])
    def get(self, request):
        try:
            cum = float(request.query_params.get("cubic_meters", ""))
        except ValueError:
            return Response({"detail": "cubic_meters must be a number."}, status=400)
        return Response(calculate_bill(cum))


class CurrentForecastView(APIView):
    """Projected bill for the billing screen (Fig. 18): estimate, monthly usage bars, cost per cu.m."""

    @extend_schema(parameters=[OpenApiParameter("household", int, required=False)])
    def get(self, request):
        household = resolve_household(request)
        forecast = forecast_month(household, persist=True)
        history = (ConsumptionSummary.objects.filter(household=household, period_type="monthly")
                   .order_by("-period_start")[:6])
        forecast["monthly_usage"] = [
            {"month": s.period_start.date().isoformat(), "cubic_meters": round(s.total_consumption / 1000, 3)}
            for s in reversed(list(history))]
        forecast["generated_at"] = timezone.now()
        return Response(forecast)


class ForecastHistoryView(generics.ListAPIView):
    serializer_class = BillingForecastSerializer
    filterset_fields = ["household"]

    def get_queryset(self):
        return BillingForecast.objects.filter(household__in=households_for(self.request.user))
