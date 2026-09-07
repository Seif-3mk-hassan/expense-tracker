from django.urls import path

from . import views

urlpatterns = [
    path("", views.BudgetListView.as_view(), name="budget-list"),
    path("<int:pk>/edit/", views.BudgetUpdateView.as_view(), name="budget-edit"),
]
