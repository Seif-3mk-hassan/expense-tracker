from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import DEFAULT_CATEGORIES, Budget, Category, Expense

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


class SeedDemoCommandTests(TestCase):
    def test_seed_matches_prototype_figures_and_is_idempotent(self):
        from django.core.management import call_command

        call_command("seed_demo", user="demo")
        user = User.objects.get(username="demo")
        expenses = Expense.objects.for_user(user)
        self.assertEqual(expenses.count(), 16)
        total = sum(expenses.values_list("amount", flat=True))
        self.assertEqual(total, Decimal("12450.00"))
        call_command("seed_demo", user="demo")
        self.assertEqual(Expense.objects.for_user(user).count(), 16)

    def test_seed_clear_wipes_first(self):
        from django.core.management import call_command

        user = User.objects.create_user("demo2")
        food = Category.objects.for_user(user).get(name="Food")
        Expense.objects.create(owner=user, amount=1, category=food, note="stale")
        call_command("seed_demo", user="demo2", clear=True)
        self.assertFalse(
            Expense.objects.for_user(user).filter(note="stale").exists()
        )


class BudgetModelTests(TestCase):
    def setUp(self):
        from datetime import date

        self.user = User.objects.create_user("budgeter")
        self.food = Category.objects.for_user(self.user).get(name="Food")
        self.september = date(2026, 9, 1)

    def test_ensure_creates_rows_with_default_limits(self):
        from .budgets import ensure_month_budgets

        budgets = ensure_month_budgets(self.user, self.september)
        self.assertEqual(len(budgets), 5)
        food = [b for b in budgets if b.category.name == "Food"][0]
        self.assertEqual(food.limit, Decimal("3000.00"))
        self.assertEqual(food.month, self.september)

    def test_ensure_inherits_previous_month_limit(self):
        from .budgets import ensure_month_budgets
        from datetime import date

        Budget.objects.create(
            owner=self.user,
            category=self.food,
            month=date(2026, 8, 1),
            limit=Decimal("3500"),
        )
        budgets = ensure_month_budgets(self.user, self.september)
        food = [b for b in budgets if b.category.name == "Food"][0]
        self.assertEqual(food.limit, Decimal("3500.00"))

    def test_ensure_is_idempotent(self):
        from .budgets import ensure_month_budgets

        ensure_month_budgets(self.user, self.september)
        ensure_month_budgets(self.user, self.september)
        self.assertEqual(
            Budget.objects.for_user(self.user)
            .filter(month=self.september)
            .count(),
            5,
        )

    def test_used_sums_only_month_and_category(self):
        from datetime import date

        from .budgets import ensure_month_budgets

        fun = Category.objects.for_user(self.user).get(name="Fun")
        Expense.objects.create(
            owner=self.user, amount=100, date=date(2026, 9, 5), category=self.food
        )
        Expense.objects.create(
            owner=self.user, amount=50, date=date(2026, 8, 5), category=self.food
        )
        Expense.objects.create(
            owner=self.user, amount=70, date=date(2026, 9, 5), category=fun
        )
        budgets = ensure_month_budgets(self.user, self.september)
        food = [b for b in budgets if b.category.name == "Food"][0]
        self.assertEqual(food.used, Decimal("100.00"))
        self.assertEqual(food.remaining, Decimal("2900.00"))
        self.assertEqual(food.percent_used, 3)

    def test_warning_at_ninety_percent(self):
        from .budgets import ensure_month_budgets
        from datetime import date

        Expense.objects.create(
            owner=self.user, amount=2860, date=date(2026, 9, 5), category=self.food
        )
        budgets = ensure_month_budgets(self.user, self.september)
        food = [b for b in budgets if b.category.name == "Food"][0]
        self.assertTrue(food.is_warning)
        self.assertEqual(food.percent_used, 95)

    def test_duplicate_budget_rejected(self):
        from django.db import IntegrityError

        Budget.objects.create(
            owner=self.user, category=self.food, month=self.september, limit=100
        )
        with self.assertRaises(IntegrityError):
            Budget.objects.create(
                owner=self.user, category=self.food, month=self.september, limit=200
            )


class BudgetListViewTests(TestCase):
    def setUp(self):
        from datetime import date

        self.user = User.objects.create_user("viewer")
        self.other = User.objects.create_user("other")
        self.today = date.today().replace(day=1)
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("budget-list"))
        self.assertRedirects(response, reverse("login") + "?next=/budgets/")

    def test_view_ensures_month_rows_and_shows_them(self):
        response = self.client.get(reverse("budget-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Budget.objects.for_user(self.user).filter(month=self.today).count(), 5
        )
        self.assertContains(response, "Food")

    def test_only_own_budgets_shown(self):
        from .budgets import ensure_month_budgets

        ensure_month_budgets(self.other, self.today)
        response = self.client.get(reverse("budget-list"))
        budgets = list(response.context["budgets"])
        self.assertTrue(budgets)
        self.assertTrue(all(b.owner == self.user for b in budgets))

    def test_warning_style_on_nearly_spent_budget(self):
        from datetime import date

        food = Category.objects.for_user(self.user).get(name="Food")
        Expense.objects.create(
            owner=self.user, amount=2900, date=date.today(), category=food
        )
        response = self.client.get(reverse("budget-list"))
        self.assertContains(response, 'class="pbar"><i class="warn"')

    def test_seed_creates_september_budgets(self):
        from django.core.management import call_command

        call_command("seed_demo", user="demo")
        demo = User.objects.get(username="demo")
        food_budget = Budget.objects.for_user(demo).get(
            category__name="Food", month__year=2026, month__month=9
        )
        self.assertEqual(food_budget.limit, Decimal("3000.00"))
        self.assertEqual(food_budget.used, Decimal("2615.00"))


class BudgetUpdateTests(TestCase):
    def setUp(self):
        from .budgets import ensure_month_budgets
        from datetime import date

        self.user = User.objects.create_user("editor")
        self.other = User.objects.create_user("other")
        self.today = date.today().replace(day=1)
        ensure_month_budgets(self.user, self.today)
        ensure_month_budgets(self.other, self.today)
        self.budget = Budget.objects.for_user(self.user).get(
            category__name="Food", month=self.today
        )
        self.client.force_login(self.user)

    def test_edit_updates_limit(self):
        response = self.client.post(
            reverse("budget-edit", args=[self.budget.pk]), {"limit": "3500"}
        )
        self.assertRedirects(response, reverse("budget-list"))
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.limit, Decimal("3500.00"))

    def test_negative_limit_rejected(self):
        response = self.client.post(
            reverse("budget-edit", args=[self.budget.pk]), {"limit": "-5"}
        )
        self.assertEqual(response.status_code, 200)
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.limit, Decimal("3000.00"))

    def test_category_and_month_cannot_change(self):
        fun = Category.objects.for_user(self.user).get(name="Fun")
        self.client.post(
            reverse("budget-edit", args=[self.budget.pk]),
            {"limit": "3500", "category": fun.pk, "month": "2026-01-01"},
        )
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.category.name, "Food")
        self.assertEqual(self.budget.month, self.today)

    def test_edit_other_users_budget_returns_404(self):
        other_budget = Budget.objects.for_user(self.other).get(
            category__name="Food", month=self.today
        )
        url = reverse("budget-edit", args=[other_budget.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.post(url, {"limit": "1"}).status_code, 404
        )


class DashboardHeroTests(TestCase):
    def setUp(self):
        from datetime import date

        from .analytics import month_shift

        self.user = User.objects.create_user("dash")
        self.other = User.objects.create_user("stranger")
        self.today = date.today()
        self.food = Category.objects.for_user(self.user).get(name="Food")
        Expense.objects.create(
            owner=self.user, amount=300, date=self.today, category=self.food
        )
        prev = month_shift(self.today, -1).replace(day=5)
        Expense.objects.create(
            owner=self.user, amount=100, date=prev, category=self.food
        )
        other_food = Category.objects.for_user(self.other).get(name="Food")
        Expense.objects.create(
            owner=self.other, amount=9999, date=self.today, category=other_food
        )
        self.client.force_login(self.user)

    def test_hero_math(self):
        hero = self.client.get(reverse("home")).context["hero"]
        self.assertEqual(hero["total"], Decimal("300.00"))
        self.assertEqual(hero["budget"], Decimal("14500.00"))
        self.assertEqual(hero["left"], Decimal("14200.00"))
        self.assertEqual(
            hero["avg"], round(Decimal("300") / self.today.day, 2)
        )
        self.assertEqual(hero["change"], 200)
        self.assertEqual(hero["today"], Decimal("300.00"))

    def test_empty_month_shows_zeros_and_new(self):
        Expense.objects.for_user(self.user).delete()
        hero = self.client.get(reverse("home")).context["hero"]
        self.assertEqual(hero["total"], Decimal("0"))
        self.assertIsNone(hero["change"])
        response = self.client.get(reverse("home"))
        self.assertContains(response, "new")

    def test_month_param_switches_context(self):
        from .analytics import month_shift

        prev = month_shift(self.today, -1)
        hero = self.client.get(
            reverse("home") + f"?month={prev:%Y-%m}"
        ).context["hero"]
        self.assertEqual(hero["total"], Decimal("100.00"))

    def test_dashboard_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("home")).status_code, 302)


class DashboardChartsTests(TestCase):
    def setUp(self):
        from datetime import date, timedelta

        self.user = User.objects.create_user("charts")
        self.today = date.today()
        self.food = Category.objects.for_user(self.user).get(name="Food")
        self.fun = Category.objects.for_user(self.user).get(name="Fun")
        Expense.objects.create(
            owner=self.user, amount=940, date=self.today, category=self.food
        )
        Expense.objects.create(
            owner=self.user,
            amount=310,
            date=self.today - timedelta(days=2),
            category=self.fun,
        )
        self.client.force_login(self.user)

    def test_weekly_marks_peak_and_today(self):
        weekly = self.client.get(reverse("home")).context["weekly"]
        self.assertEqual(len(weekly["days"]), 7)
        peaks = [d for d in weekly["days"] if d["is_peak"]]
        self.assertEqual(len(peaks), 1)
        self.assertEqual(peaks[0]["total"], Decimal("940.00"))
        today_col = [d for d in weekly["days"] if d["is_today"]]
        self.assertEqual(len(today_col), 1)
        self.assertEqual(today_col[0]["px"], 162)
        self.assertContains(self.client.get(reverse("home")), "avg")

    def test_donut_segments_and_style(self):
        donut = self.client.get(reverse("home")).context["donut"]
        self.assertEqual(donut["total"], Decimal("1250.00"))
        self.assertEqual(donut["segments"][0]["name"], "Food")
        self.assertIn("#5EEAD4", donut["style"])
        self.assertIn("conic-gradient", donut["style"])

    def test_empty_month_donut_is_neutral(self):
        Expense.objects.for_user(self.user).delete()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "No spending this month yet.")
        self.assertContains(response, "conic-gradient(#2A3350 0 100%)", html=False)


class DashboardRecentTests(TestCase):
    def setUp(self):
        from datetime import date, timedelta

        self.user = User.objects.create_user("recent")
        self.other = User.objects.create_user("stranger")
        self.food = Category.objects.for_user(self.user).get(name="Food")
        self.today = date.today()
        for back in range(7):
            Expense.objects.create(
                owner=self.user,
                amount=10 + back,
                date=self.today - timedelta(days=back),
                category=self.food,
                note=f"day {back}",
            )
        other_food = Category.objects.for_user(self.other).get(name="Food")
        Expense.objects.create(
            owner=self.other, amount=9999, date=self.today, category=other_food
        )
        self.client.force_login(self.user)

    def test_recent_shows_five_latest_own_only(self):
        recent = list(self.client.get(reverse("home")).context["recent"])
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0].note, "day 0")
        self.assertTrue(all(e.owner == self.user for e in recent))

    def test_view_all_and_manage_links_present(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("expense-list"))
        self.assertContains(response, reverse("budget-list"))

    def test_dashboard_budgets_match_month(self):
        budgets = list(self.client.get(reverse("home")).context["budgets"])
        self.assertEqual(len(budgets), 5)
        self.assertTrue(all(b.owner == self.user for b in budgets))

    def test_modal_param_opens_add_modal(self):
        response = self.client.get(reverse("expense-list") + "?modal=1")
        self.assertContains(response, 'class="ov open"')


class MonthContextTests(TestCase):
    def setUp(self):
        from datetime import date

        from .analytics import month_shift

        self.user = User.objects.create_user("timer")
        self.today = date.today()
        self.prev = month_shift(self.today, -1)
        self.food = Category.objects.for_user(self.user).get(name="Food")
        Expense.objects.create(
            owner=self.user, amount=500, date=self.prev.replace(day=5),
            category=self.food,
        )
        self.client.force_login(self.user)

    def test_topbar_has_search_and_month_picker(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'name="month"')
        self.assertContains(response, self.prev.strftime("%B %Y"))

    def test_budgets_page_honors_month_param(self):
        from .budgets import ensure_month_budgets

        ensure_month_budgets(self.user, self.prev.replace(day=1))
        response = self.client.get(
            reverse("budget-list") + f"?month={self.prev:%Y-%m}"
        )
        self.assertContains(response, self.prev.strftime("%B %Y"))
        budgets = list(response.context["budgets"])
        self.assertTrue(budgets)
        self.assertTrue(
            all(b.month.month == self.prev.month for b in budgets)
        )

    def test_invalid_month_param_falls_back_to_current(self):
        response = self.client.get(reverse("home") + "?month=nope")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["hero"]["month_label"],
            self.today.strftime("%B %Y"),
        )


class InsightsTests(TestCase):
    def setUp(self):
        from datetime import date

        from .analytics import month_shift

        self.user = User.objects.create_user("insight")
        self.other = User.objects.create_user("stranger")
        self.today = date.today()
        self.food = Category.objects.for_user(self.user).get(name="Food")
        Expense.objects.create(
            owner=self.user, amount=2860, date=self.today, category=self.food
        )
        prev = month_shift(self.today, -1).replace(day=5)
        Expense.objects.create(
            owner=self.user, amount=500, date=prev, category=self.food
        )
        other_food = Category.objects.for_user(self.other).get(name="Food")
        Expense.objects.create(
            owner=self.other, amount=7777, date=self.today, category=other_food
        )
        self.client.force_login(self.user)

    def test_history_covers_six_months(self):
        history = self.client.get(reverse("insights")).context["history"]
        self.assertEqual(len(history), 6)
        self.assertEqual(history[-1]["label"], self.today.strftime("%b"))
        current = [h for h in history if h["label"] == self.today.strftime("%b")]
        self.assertEqual(current[0]["total"], Decimal("2860.00"))

    def test_tip_names_worst_strained_category(self):
        response = self.client.get(reverse("insights"))
        tip = response.context["tip"]
        self.assertIsNotNone(tip)
        self.assertEqual(tip.category.name, "Food")
        self.assertContains(response, "Food is at 95%")

    def test_no_tip_when_nothing_strained(self):
        Expense.objects.for_user(self.user).delete()
        response = self.client.get(reverse("insights"))
        self.assertIsNone(response.context["tip"])
        self.assertNotContains(response, "Tip:")

    def test_other_users_data_excluded(self):
        history = self.client.get(reverse("insights")).context["history"]
        total = sum((h["total"] for h in history), Decimal("0"))
        self.assertEqual(total, Decimal("3360.00"))

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("insights")).status_code, 302)


class JsonExportTests(TestCase):
    def setUp(self):
        from datetime import date

        self.user = User.objects.create_user("exporter")
        self.other = User.objects.create_user("stranger")
        food = Category.objects.for_user(self.user).get(name="Food")
        Expense.objects.create(
            owner=self.user, amount=180, date=date(2026, 9, 7),
            category=food, payment="cash", note="Lunch",
        )
        other_food = Category.objects.for_user(self.other).get(name="Food")
        Expense.objects.create(
            owner=self.other, amount=9999, date=date(2026, 9, 7),
            category=other_food, note="Not mine",
        )
        self.client.force_login(self.user)

    def test_export_shape_and_download(self):
        import json

        response = self.client.get(reverse("expense-export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("attachment", response["Content-Disposition"])
        payload = json.loads(response.content)
        self.assertEqual(payload["currency"], "EGP")
        self.assertIn("exported", payload)
        self.assertEqual(len(payload["expenses"]), 1)
        row = payload["expenses"][0]
        self.assertEqual(
            row,
            {
                "description": "Lunch",
                "category": "Food",
                "date": "2026-09-07",
                "payment": "cash",
                "amount": "180.00",
            },
        )

    def test_export_requires_login(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("expense-export")).status_code, 302
        )


class JsonImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("importer")
        self.client.force_login(self.user)

    def _upload(self, content, name="data.json"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        if isinstance(content, str):
            content = content.encode()
        return self.client.post(
            reverse("expense-import"),
            {"file": SimpleUploadedFile(name, content)},
        )

    def test_valid_file_imports(self):
        import json

        payload = {
            "exported": "2026-09-08T00:00:00",
            "currency": "EGP",
            "expenses": [
                {
                    "description": "Lunch",
                    "category": "Food",
                    "date": "2026-09-07",
                    "payment": "cash",
                    "amount": "180.00",
                }
            ],
        }
        response = self._upload(json.dumps(payload))
        self.assertContains(response, "1 imported")
        self.assertEqual(Expense.objects.for_user(self.user).count(), 1)

    def test_malformed_file_imports_nothing(self):
        response = self._upload("{not json")
        self.assertContains(response, "not valid JSON")
        self.assertEqual(Expense.objects.for_user(self.user).count(), 0)

    def test_mixed_rows_report_reasons(self):
        import json

        payload = {
            "expenses": [
                {
                    "description": "Good",
                    "category": "Food",
                    "date": "2026-09-07",
                    "payment": "cash",
                    "amount": "10",
                },
                {
                    "description": "Bad amount",
                    "category": "Food",
                    "date": "2026-09-07",
                    "payment": "cash",
                    "amount": "0",
                },
                {
                    "description": "Bad category",
                    "category": "Nope",
                    "date": "2026-09-07",
                    "payment": "cash",
                    "amount": "5",
                },
                {
                    "description": "Bad date",
                    "category": "Food",
                    "date": "yesterday",
                    "payment": "cash",
                    "amount": "5",
                },
            ]
        }
        response = self._upload(json.dumps(payload))
        self.assertContains(response, "1 imported")
        self.assertContains(response, "3 rejected")
        self.assertContains(response, "Bad amount")
        self.assertContains(response, "Unknown category")
        self.assertContains(response, "Bad date")
        self.assertEqual(Expense.objects.for_user(self.user).count(), 1)

    def test_unknown_shape_imports_nothing(self):
        import json

        response = self._upload(json.dumps([1, 2, 3]))
        self.assertContains(response, "expenses")
        self.assertEqual(Expense.objects.for_user(self.user).count(), 0)

    def test_import_requires_login(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("expense-import")).status_code, 302
        )


class CsvExportTests(TestCase):
    def test_csv_shape_and_scope(self):
        from datetime import date

        user = User.objects.create_user("csver")
        other = User.objects.create_user("stranger")
        food = Category.objects.for_user(user).get(name="Food")
        Expense.objects.create(
            owner=user, amount=180, date=date(2026, 9, 7),
            category=food, payment="cash", note="Lunch, with comma",
        )
        other_food = Category.objects.for_user(other).get(name="Food")
        Expense.objects.create(
            owner=other, amount=9999, date=date(2026, 9, 7), category=other_food
        )
        self.client.force_login(user)
        response = self.client.get(reverse("expense-export-csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        content = response.content.decode()
        self.assertIn("description,category,date,payment,amount", content)
        self.assertIn('"Lunch, with comma",Food,2026-09-07,cash,180.00', content)
        self.assertNotIn("9999", content)

    def test_csv_requires_login(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("expense-export-csv")).status_code, 302
        )


class PreferencesTests(TestCase):
    def setUp(self):
        from datetime import date

        self.user = User.objects.create_user("prefy")
        self.food = Category.objects.for_user(self.user).get(name="Food")
        Expense.objects.create(
            owner=self.user, amount=400, date=date(2026, 9, 12), category=self.food
        )
        self.client.force_login(self.user)

    def test_custom_month_start_moves_spending_between_periods(self):
        from .budgets import month_bounds

        start, end = month_bounds(date(2026, 9, 20), start_day=15)
        self.assertEqual((start.isoformat(), end.isoformat()), ("2026-09-15", "2026-10-14"))
        start, end = month_bounds(date(2026, 9, 10), start_day=15)
        self.assertEqual((start.isoformat(), end.isoformat()), ("2026-08-15", "2026-09-14"))

    def test_settings_update_requeries_dashboard(self):
        url = reverse("home") + "?month=2026-09"
        hero = self.client.get(url).context["hero"]
        self.assertEqual(hero["total"], Decimal("400.00"))
        response = self.client.post(
            reverse("settings"),
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "currency": "USD",
                "month_start_day": "10",
            },
        )
        self.assertRedirects(response, reverse("settings"))
        hero = self.client.get(url).context["hero"]
        self.assertEqual(hero["total"], Decimal("0.00"))
        dashboard = self.client.get(url)
        self.assertContains(dashboard, "USD")

    def test_invalid_month_start_rejected(self):
        response = self.client.post(
            reverse("settings"),
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "currency": "EGP",
                "month_start_day": "31",
            },
        )
        self.assertEqual(response.status_code, 200)
        from accounts.models import get_profile

        self.assertEqual(get_profile(self.user).month_start_day, 1)

    def test_role_not_self_editable(self):
        self.client.post(
            reverse("settings"),
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "currency": "EGP",
                "month_start_day": "1",
                "groups": "admin",
            },
        )
        self.assertFalse(self.user.groups.filter(name="admin").exists())

    def test_settings_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("settings")).status_code, 302)
