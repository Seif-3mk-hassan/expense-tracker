"""Budget month math and rollover (US-08).

Calendar months for now. US-19 (S6 preferences) will honor the user's
custom month-start day by extending ``month_bounds``.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

DEFAULT_LIMITS = {
    "Food": Decimal("3000"),
    "Transport": Decimal("2000"),
    "Fun": Decimal("1500"),
    "Housing": Decimal("7000"),
    "Other": Decimal("1000"),
}
FALLBACK_LIMIT = Decimal("1000")


def month_start(any_day, start_day=1):
    """First date of the budgeting period containing ``any_day``."""
    if start_day <= 1:
        return date(any_day.year, any_day.month, 1)
    if any_day.day >= start_day:
        return date(any_day.year, any_day.month, start_day)
    prev = any_day.replace(day=1) - timedelta(days=1)
    return date(prev.year, prev.month, start_day)


def month_bounds(any_day, start_day=1):
    """(first_date, last_date) of the budgeting period containing ``any_day``."""
    start = month_start(any_day, start_day)
    if start_day <= 1:
        last = calendar.monthrange(start.year, start.month)[1]
        return start, date(start.year, start.month, last)
    bumped = start.month + 1
    next_start = date(
        start.year + (bumped - 1) // 12, (bumped - 1) % 12 + 1, start_day
    )
    return start, next_start - timedelta(days=1)


def ensure_month_budgets(user, any_day, start_day=1):
    """Guarantee one Budget row per active category for the period.

    New periods inherit each category's most recent limit; categories with
    no history fall back to DEFAULT_LIMITS. Idempotent.
    """
    from .models import Budget, Category

    start, _ = month_bounds(any_day, start_day)
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
