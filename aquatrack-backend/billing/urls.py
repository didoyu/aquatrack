from django.urls import path

from . import views

urlpatterns = [
    path("rates/", views.RatesView.as_view()),
    path("calculate/", views.CalculateView.as_view()),
    path("forecast/", views.CurrentForecastView.as_view()),
    path("forecast/history/", views.ForecastHistoryView.as_view()),
]
