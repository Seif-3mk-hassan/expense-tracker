from django.urls import path

from . import views

urlpatterns = [
    path("", views.InsightsView.as_view(), name="insights"),
]
