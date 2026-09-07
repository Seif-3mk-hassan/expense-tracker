from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

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
