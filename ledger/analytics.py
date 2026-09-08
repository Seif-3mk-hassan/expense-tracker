"""Dashboard and insights math over scoped querysets (US-11 and later)."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum

from .budgets import month_bounds, month_start
from .models import Budget, Expense


def month_expenses(user, ref, start_day=1):
    start, end = month_bounds(ref, start_day)
    return Expense.objects.for_user(user).filter(date__gte=start, date__lte=end)


def month_total(user, ref, start_day=1):
    return (
        month_expenses(user, ref, start_day).aggregate(total=Sum("amount"))[
            "total"
        ]
        or Decimal("0")
    )


def budget_total(user, ref, start_day=1):
    start, _ = month_bounds(ref, start_day)
    return (
        Budget.objects.for_user(user)
        .filter(month=start)
        .aggregate(total=Sum("limit"))["total"]
        or Decimal("0")
    )


def days_elapsed(ref, today, start_day=1):
    start, end = month_bounds(ref, start_day)
    if today < start or today > end:
        return (end - start).days + 1
    return (today - start).days + 1


def daily_average(total, ref, today, start_day=1):
    elapsed = days_elapsed(ref, today, start_day)
    if elapsed <= 0:
        return Decimal("0")
    return round(total / elapsed, 2)


def month_shift(ref, delta, start_day=1):
    """First date of the period ``delta`` steps from ref's period."""
    start, end = month_bounds(ref, start_day)
    if delta >= 0:
        current = start
        for _ in range(delta):
            _, period_end = month_bounds(current, start_day)
            current = period_end + timedelta(days=1)
        return current
    current = start
    for _ in range(-delta):
        previous_end = current - timedelta(days=1)
        current, _ = month_bounds(previous_end, start_day)
    return current


def pct_change(current, previous):
    if previous == 0:
        return None
    return round(float((current - previous) / previous) * 100)


def last_n_days(user, today, n=7):
    """Oldest-first (date, weekday label, total) for the n days ending today."""
    days = []
    for back in range(n - 1, -1, -1):
        day = today - timedelta(days=back)
        total = (
            Expense.objects.for_user(user)
            .filter(date=day)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        days.append({"date": day, "label": day.strftime("%a"), "total": total})
    return days


def category_sums(user, ref, start_day=1):
    """Per-category month totals, richest first: [{name, color, icon, total}]."""
    rows = (
        month_expenses(user, ref, start_day)
        .values("category__name", "category__color", "category__icon")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [
        {
            "name": r["category__name"],
            "color": r["category__color"],
            "icon": r["category__icon"],
            "total": r["total"],
        }
        for r in rows
    ]


def donut_style(segments, total):
    """CSS conic-gradient for the category donut (US-12)."""
    if not total:
        return "conic-gradient(#2A3350 0 100%)"
    parts, running = [], Decimal("0")
    for seg in segments:
        start_pct = running / total * 100
        running += seg["total"]
        end_pct = running / total * 100
        parts.append(f"{seg['color']} {start_pct:.1f}% {end_pct:.1f}%")
    return "conic-gradient(" + ", ".join(parts) + ")"


def last_6_months(user, ref, start_day=1):
    """Oldest-first (label, total) for the 6 periods ending with ref's period."""
    out = []
    for delta in range(-5, 1):
        first = month_shift(ref, delta, start_day)
        total = month_total(user, first, start_day)
        out.append({"label": first.strftime("%b"), "total": total})
    return out
