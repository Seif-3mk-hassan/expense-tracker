from django.urls import path

from . import views

urlpatterns = [
    path("", views.BudgetListView.as_view(), name="budget-list"),
]
