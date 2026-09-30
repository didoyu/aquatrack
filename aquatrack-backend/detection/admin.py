from django.contrib import admin

from .models import AlertNotification, LeakDetection, MLModelEvaluation

admin.site.register(LeakDetection)
admin.site.register(AlertNotification)
admin.site.register(MLModelEvaluation)
