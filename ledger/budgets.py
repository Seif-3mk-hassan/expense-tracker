"""Budget month math and rollover (US-08).

Calendar months for now. US-19 (S6 preferences) will honor the user's
custom month-start day by extending ``month_bounds``.
"""

import calendar
from datetime import date
from decimal import Decimal

DEFAULT_LIMITS = {
    "Food": Decimal("3000"),
    "Transport": Decimal("2000"),
    "Fun": Decimal("1500"),
    "Housing": Decimal("7000"),
    "Other": Decimal("1000"),
}
FALLBACK_LIMIT = Decimal("1000")


def month_start(day):
    return date(day.year, day.month, 1)


def month_bounds(any_day):
    """(first_date, last_date) of the calendar month containing ``any_day``."""
    start = month_start(any_day)
    last = calendar.monthrange(start.year, start.month)[1]
    return start, date(start.year, start.month, last)


def ensure_month_budgets(user, any_day):
    """Guarantee one Budget row per active category for the month.

    New months inherit each category's most recent limit; categories with
    no history fall back to DEFAULT_LIMITS. Idempotent.
    """
    from .models import Budget, Category

    start, _ = month_bounds(any_day)
    budgets = []
    for category in Category.objects.for_user(user).filter(active=True):
        previous = (
            Budget.objects.for_user(user)
            .filter(category=category, month__lt=start)
            .order_by("-month")
            .first()
        )
        if previous is not None:
            limit = previous.limit
        else:
            limit = DEFAULT_LIMITS.get(category.name, FALLBACK_LIMIT)
        budget, _ = Budget.objects.get_or_create(
            owner=user,
            category=category,
            month=start,
            defaults={"limit": limit},
        )
        budgets.append(budget)
    return budgets
