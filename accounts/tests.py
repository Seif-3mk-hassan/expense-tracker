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


class UserManagementTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("boss", password="Str0ng!passw0rd")
        self.staff.is_staff = True
        self.staff.save()
        self.member = User.objects.create_user("member", password="Str0ng!passw0rd")

    def test_non_staff_gets_404(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("user-list")).status_code, 404)
        self.assertEqual(
            self.client.post(
                reverse("user-toggle", args=[self.member.pk])
            ).status_code,
            404,
        )

    def test_anonymous_redirected_to_login(self):
        self.assertEqual(self.client.get(reverse("user-list")).status_code, 302)

    def test_staff_sees_roster_without_spending_data(self):
        from ledger.models import Category, Expense

        food = Category.objects.for_user(self.member).get(name="Food")
        Expense.objects.create(owner=self.member, amount=9999, category=food)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("user-list"))
        self.assertContains(response, "member")
        self.assertNotContains(response, "9999")

    def test_toggle_deactivates_and_blocks_login(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("user-toggle", args=[self.member.pk]))
        self.assertRedirects(response, reverse("user-list"))
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertFalse(
            self.client.login(username="member", password="Str0ng!passw0rd")
        )

    def test_cannot_deactivate_self(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("user-toggle", args=[self.staff.pk]), follow=True
        )
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)
        self.assertContains(response, "cannot deactivate")

    def test_cannot_deactivate_superuser(self):
        admin = User.objects.create_superuser(
            "root", password="Str0ng!passw0rd", email="r@x.com"
        )
        self.client.force_login(self.staff)
        self.client.post(reverse("user-toggle", args=[admin.pk]))
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)
