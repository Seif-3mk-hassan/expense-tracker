from django.contrib import admin
from django.urls import include, path

from core.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("expenses/", include("ledger.urls")),
    path("budgets/", include("ledger.budgets_urls")),
    path("", home, name="home"),
]
