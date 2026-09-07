from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SignupTests(TestCase):
    def test_signup_creates_user_in_user_group_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "seif",
                "password1": "Str0ng!passw0rd",
                "password2": "Str0ng!passw0rd",
            },
        )
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(username="seif")
        self.assertTrue(user.groups.filter(name="user").exists())
        self.assertIn("_auth_user_id", self.client.session)


class AuthGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Group.objects.get_or_create(name="user")

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("login") + "?next=/")

    def test_login_with_valid_credentials(self):
        User.objects.create_user("u1", password="Str0ng!passw0rd")
        self.assertTrue(self.client.login(username="u1", password="Str0ng!passw0rd"))
