"""Dashboard and insights math over scoped querysets (US-11 and later)."""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from .budgets import month_bounds, month_start
from .models import Budget, Expense


def month_expenses(user, ref):
    start, end = month_bounds(ref)
    return Expense.objects.for_user(user).filter(date__gte=start, date__lte=end)


def month_total(user, ref):
    return (
        month_expenses(user, ref).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )


def budget_total(user, ref):
    start, _ = month_bounds(ref)
    return (
        Budget.objects.for_user(user)
        .filter(month=start)
        .aggregate(total=Sum("limit"))["total"]
        or Decimal("0")
    )


def days_elapsed(ref, today):
    if (ref.year, ref.month) == (today.year, today.month):
        return today.day
    return calendar.monthrange(ref.year, ref.month)[1]


def daily_average(total, ref, today):
    elapsed = days_elapsed(ref, today)
    if elapsed <= 0:
        return Decimal("0")
    return round(total / elapsed, 2)


def month_shift(ref, delta):
    month = ref.month - 1 + delta
    return date(ref.year + month // 12, month % 12 + 1, 1)


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


def category_sums(user, ref):
    """Per-category month totals, richest first: [{name, color, icon, total}]."""
    rows = (
        month_expenses(user, ref)
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


def last_6_months(user, ref):
    """Oldest-first (label, total) for the 6 months ending with ref's month."""
    out = []
    for delta in range(-5, 1):
        first = month_shift(ref, delta)
        total = month_total(user, first)
        out.append({"label": first.strftime("%b"), "total": total})
    return out
