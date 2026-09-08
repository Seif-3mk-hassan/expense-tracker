from django.contrib import admin
from django.urls import include, path

from ledger.views import DashboardView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("expenses/", include("ledger.urls")),
    path("budgets/", include("ledger.budgets_urls")),
    path("insights/", include("ledger.insights_urls")),
    path("", DashboardView.as_view(), name="home"),
]
