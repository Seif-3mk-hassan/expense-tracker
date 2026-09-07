from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ledger.models import Category, Expense

# (amount, category, date, payment, note) — totals 12,450 EGP like the prototype.
DEMO_ROWS = [
    (Decimal("180"), "Food", date(2026, 9, 7), "cash", "Lunch Kazlak"),
    (Decimal("95"), "Transport", date(2026, 9, 7), "credit", "Uber to campus"),
    (Decimal("45"), "Food", date(2026, 9, 7), "cash", "Coffee"),
    (Decimal("450"), "Other", date(2026, 9, 6), "transfer", "Internet bill"),
    (Decimal("350"), "Other", date(2026, 9, 6), "transfer", "Phone bill"),
    (Decimal("850"), "Fun", date(2026, 9, 5), "credit", "Steam game"),
    (Decimal("240"), "Other", date(2026, 9, 4), "credit", "Pharmacy"),
    (Decimal("500"), "Fun", date(2026, 9, 4), "credit", "Gym"),
    (Decimal("150"), "Fun", date(2026, 9, 3), "credit", "Netflix"),
    (Decimal("600"), "Transport", date(2026, 9, 3), "credit", "Fuel"),
    (Decimal("1120"), "Food", date(2026, 9, 2), "cash", "Carrefour groceries"),
    (Decimal("620"), "Food", date(2026, 9, 2), "cash", "Takeaway"),
    (Decimal("270"), "Fun", date(2026, 9, 2), "credit", "Cinema"),
    (Decimal("6000"), "Housing", date(2026, 9, 1), "transfer", "Rent September"),
    (Decimal("650"), "Food", date(2026, 9, 1), "cash", "Extra groceries"),
    (Decimal("330"), "Other", date(2026, 9, 1), "cash", "Books"),
]


class Command(BaseCommand):
    help = "Seed one month of realistic EGP demo data (US-07)."

    def add_arguments(self, parser):
        parser.add_argument("--user", default="demo")
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete the user's existing expenses first.",
        )

    def handle(self, *args, user, clear, **options):
        User = get_user_model()
        account, created = User.objects.get_or_create(username=user)
        if created:
            account.set_password("demo1234")
            account.save()
            self.stdout.write(f"Created user '{user}' (password: demo1234).")
        if clear:
            deleted, _ = Expense.objects.for_user(account).delete()
            self.stdout.write(f"Cleared {deleted} existing expenses.")
        categories = {
            name: Category.objects.for_user(account).get(name=name)
            for name in ("Food", "Transport", "Housing", "Fun", "Other")
        }
        made = 0
        for amount, category, day, payment, note in DEMO_ROWS:
            _, was_made = Expense.objects.get_or_create(
                owner=account,
                date=day,
                amount=amount,
                note=note,
                defaults={
                    "category": categories[category],
                    "payment": payment,
                },
            )
            made += was_made
        total = sum(
            Expense.objects.for_user(account).values_list("amount", flat=True)
        )
        self.stdout.write(
            f"Seeded {made} new expenses for '{user}'. Month total: {total} EGP."
        )
