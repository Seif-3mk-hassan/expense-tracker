from django.urls import path

from . import views

urlpatterns = [
    path("", views.ExpenseListView.as_view(), name="expense-list"),
    path("add/", views.ExpenseCreateView.as_view(), name="expense-add"),
    path("<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="expense-edit"),
    path(
        "<int:pk>/delete/",
        views.ExpenseDeleteView.as_view(),
        name="expense-delete",
    ),
]
