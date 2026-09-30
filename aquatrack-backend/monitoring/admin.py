from django.contrib import admin

from .models import (ConsumptionSummary, Device, Household, PushToken, Sensor,
                     SystemLog, WaterReading)

admin.site.register(Household)
admin.site.register(Sensor)
admin.site.register(PushToken)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_name", "household", "status", "last_seen")
    readonly_fields = ("key_hash",)


@admin.register(WaterReading)
class WaterReadingAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "household", "flow_rate", "pressure_level", "is_anomalous", "leak_label")
    list_filter = ("is_anomalous", "leak_label")
    date_hierarchy = "timestamp"


@admin.register(ConsumptionSummary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ("household", "period_type", "period_start", "total_consumption")
    list_filter = ("period_type",)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "source", "message")
    list_filter = ("level", "source")
