from django.db import models

from monitoring.models import Household


class RateSchedule(models.Model):
    """Tiered commodity charge (COWD 2025, 1/2-inch residential). Editable in Django admin so a rate
    change never needs a code change."""

    name = models.CharField(max_length=120)
    meter_size = models.CharField(max_length=20, default="1/2 inch")
    minimum_volume = models.DecimalField(max_digits=8, decimal_places=2, default=10, help_text="cu.m covered by minimum charge")
    minimum_charge = models.DecimalField(max_digits=10, decimal_places=2, default=218.40)
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name


class RateTier(models.Model):
    schedule = models.ForeignKey(RateSchedule, on_delete=models.CASCADE, related_name="tiers")
    lower_bound = models.DecimalField(max_digits=8, decimal_places=2, help_text="cu.m where this tier starts (exclusive)")
    upper_bound = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                      help_text="cu.m where this tier ends; empty = no limit")
    rate_per_cubic_meter = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["lower_bound"]


class BillingForecast(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="forecasts")
    forecast_month = models.DateField(help_text="First day of the billing month")
    generated_on = models.DateField()
    generated_at = models.DateTimeField(auto_now=True)
    consumed_to_date = models.FloatField(default=0, help_text="cu.m used so far this month")
    predicted_consumption = models.FloatField(help_text="cu.m projected for the whole month")
    predicted_bill = models.DecimalField(max_digits=10, decimal_places=2)
    average_flow_rate = models.FloatField(default=0)
    method = models.CharField(max_length=30, default="run_rate")
    # Filled after month end so billing prediction accuracy (paper 3.3.5) can be measured
    actual_consumption = models.FloatField(null=True, blank=True)
    actual_bill = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-forecast_month", "-generated_on"]
        constraints = [models.UniqueConstraint(fields=["household", "forecast_month", "generated_on"],
                                               name="uniq_forecast_per_day")]
