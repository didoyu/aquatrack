from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("leaks", views.LeakViewSet, basename="leak")
router.register("alerts", views.AlertViewSet, basename="alert")
router.register("ml/evaluations", views.MLModelEvaluationViewSet, basename="ml-evaluation")

urlpatterns = [path("", include(router.urls))]
