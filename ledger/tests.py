from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import DEFAULT_CATEGORIES, Category, Expense

User = get_user_model()


class CategoryModelTests(TestCase):
    def test_new_user_gets_five_default_categories(self):
        user = User.objects.create_user("newbie")
        names = list(
            Category.objects.for_user(user).values_list("name", flat=True)
        )
        self.assertEqual(names, sorted(n for n, _i, _c in DEFAULT_CATEGORIES))

    def test_duplicate_name_same_owner_rejected(self):
        user = User.objects.create_user("u1")
        food = Category.objects.for_user(user).get(name="Food")
        with self.assertRaises(IntegrityError):
            Category.objects.create(owner=user, name=food.name)

    def test_same_name_different_owner_allowed(self):
        alice = User.objects.create_user("alice")
        bob = User.objects.create_user("bob")
        Category.objects.create(owner=alice, name="Pets")
        Category.objects.create(owner=bob, name="Pets")
        self.assertTrue(
            Category.objects.for_user(alice).filter(name="Pets").exists()
        )
        self.assertTrue(
            Category.objects.for_user(bob).filter(name="Pets").exists()
        )


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("spender")
        self.food = Category.objects.for_user(self.user).get(name="Food")

    def test_ordering_newest_first(self):
        Expense.objects.create(
            owner=self.user, amount=10, date=date(2026, 9, 1), category=self.food
        )
        Expense.objects.create(
            owner=self.user, amount=20, date=date(2026, 9, 7), category=self.food
        )
        amounts = list(
            Expense.objects.for_user(self.user).values_list("amount", flat=True)
        )
        self.assertEqual(amounts, [Decimal("20.00"), Decimal("10.00")])

    def test_amount_must_be_positive(self):
        expense = Expense(owner=self.user, amount=0, category=self.food)
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_category_protected_while_referenced(self):
        Expense.objects.create(owner=self.user, amount=5, category=self.food)
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.food.delete()


class ExpenseCrudTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice")
        self.bob = User.objects.create_user("bob")
        self.alice_food = Category.objects.for_user(self.alice).get(name="Food")
        self.bob_food = Category.objects.for_user(self.bob).get(name="Food")
        self.client.force_login(self.alice)

    def test_create_sets_owner_and_redirects(self):
        response = self.client.post(
            reverse("expense-add"),
            {
                "amount": "180",
                "category": self.alice_food.pk,
                "date": "2026-09-07",
                "payment": "cash",
                "note": "Lunch",
            },
        )
        self.assertRedirects(response, reverse("expense-list"))
        expense = Expense.objects.get(note="Lunch")
        self.assertEqual(expense.owner, self.alice)

    def test_create_rejects_other_users_category(self):
        response = self.client.post(
            reverse("expense-add"),
            {
                "amount": "50",
                "category": self.bob_food.pk,
                "date": "2026-09-07",
                "payment": "cash",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_create_rejects_zero_amount(self):
        response = self.client.post(
            reverse("expense-add"),
            {
                "amount": "0",
                "category": self.alice_food.pk,
                "date": "2026-09-07",
                "payment": "cash",
                "from_modal": "1",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context["show_modal"])

    def test_list_shows_only_own_expenses(self):
        Expense.objects.create(owner=self.alice, amount=10, category=self.alice_food)
        Expense.objects.create(owner=self.bob, amount=99, category=self.bob_food)
        response = self.client.get(reverse("expense-list"))
        self.assertContains(response, "10.00")
        self.assertNotContains(response, "99.00")

    def test_edit_other_users_expense_returns_404(self):
        other = Expense.objects.create(
            owner=self.bob, amount=99, category=self.bob_food
        )
        self.assertEqual(
            self.client.get(reverse("expense-edit", args=[other.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("expense-edit", args=[other.pk]),
                {
                    "amount": "1",
                    "category": self.alice_food.pk,
                    "date": "2026-09-07",
                    "payment": "cash",
                },
            ).status_code,
            404,
        )

    def test_delete_other_users_expense_returns_404(self):
        other = Expense.objects.create(
            owner=self.bob, amount=99, category=self.bob_food
        )
        self.assertEqual(
            self.client.get(
                reverse("expense-delete", args=[other.pk])
            ).status_code,
            404,
        )
        self.assertTrue(Expense.objects.filter(pk=other.pk).exists())

    def test_delete_own_expense_confirms_then_deletes(self):
        mine = Expense.objects.create(
            owner=self.alice, amount=10, category=self.alice_food
        )
        self.assertEqual(
            self.client.get(
                reverse("expense-delete", args=[mine.pk])
            ).status_code,
            200,
        )
        response = self.client.post(reverse("expense-delete", args=[mine.pk]))
        self.assertRedirects(response, reverse("expense-list"))
        self.assertFalse(Expense.objects.filter(pk=mine.pk).exists())


class ExpenseFilterTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice")
        self.bob = User.objects.create_user("bob")
        self.food = Category.objects.for_user(self.alice).get(name="Food")
        self.fun = Category.objects.for_user(self.alice).get(name="Fun")
        Expense.objects.create(
            owner=self.alice, amount=180, category=self.food, note="Lunch Kazlak"
        )
        Expense.objects.create(
            owner=self.alice, amount=850, category=self.fun, note="Steam game"
        )
        Expense.objects.create(
            owner=self.bob,
            amount=999,
            category=Category.objects.for_user(self.bob).get(name="Food"),
            note="Lunch elsewhere",
        )
        self.client.force_login(self.alice)

    def test_search_matches_note(self):
        response = self.client.get(reverse("expense-list") + "?q=kazlak")
        self.assertContains(response, "180.00")
        self.assertNotContains(response, "850.00")

    def test_search_matches_category_name(self):
        response = self.client.get(reverse("expense-list") + "?q=fun")
        self.assertContains(response, "850.00")
        self.assertNotContains(response, "180.00")

    def test_category_filter(self):
        response = self.client.get(
            reverse("expense-list") + f"?category={self.fun.pk}"
        )
        self.assertContains(response, "850.00")
        self.assertNotContains(response, "180.00")

    def test_search_never_leaks_other_users_rows(self):
        response = self.client.get(reverse("expense-list") + "?q=lunch")
        self.assertContains(response, "180.00")
        self.assertNotContains(response, "999.00")

    def test_forged_other_user_category_shows_empty_state(self):
        other_cat = Category.objects.for_user(self.bob).get(name="Fun")
        response = self.client.get(
            reverse("expense-list") + f"?category={other_cat.pk}"
        )
        self.assertContains(response, "No expenses match your filters.")

    def test_unfiltered_empty_state(self):
        Expense.objects.for_user(self.alice).delete()
        response = self.client.get(reverse("expense-list"))
        self.assertContains(response, "No expenses yet")
