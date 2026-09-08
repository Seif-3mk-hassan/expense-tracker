from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .views import SignupView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("settings/", views.settings, name="settings"),
    path("users/", views.user_list, name="user-list"),
    path("users/<int:pk>/toggle/", views.user_toggle, name="user-toggle"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
