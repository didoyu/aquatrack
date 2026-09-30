from django.contrib import admin

from .models import BillingForecast, RateSchedule, RateTier


class TierInline(admin.TabularInline):
    model = RateTier
    extra = 0


@admin.register(RateSchedule)
class RateScheduleAdmin(admin.ModelAdmin):
    inlines = [TierInline]
    list_display = ("name", "meter_size", "minimum_charge", "is_active")


admin.site.register(BillingForecast)
