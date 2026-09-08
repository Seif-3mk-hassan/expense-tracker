from django.urls import path

from . import views

urlpatterns = [
    path("", views.InsightsView.as_view(), name="insights"),
    path("export.json", views.JsonExportView.as_view(), name="expense-export"),
    path("export.csv", views.CsvExportView.as_view(), name="expense-export-csv"),
    path("import/", views.JsonImportView.as_view(), name="expense-import"),
]
