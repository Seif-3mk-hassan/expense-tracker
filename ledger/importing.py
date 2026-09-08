"""Row-level validation for JSON imports (US-17).

Every row is explicitly accepted or rejected with a reason; the caller
decides what to persist. Nothing here touches the database.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from .models import Expense


def validate_import_rows(user, records):
    """Returns (clean_expenses, rejected) for a list of raw record dicts."""
    from .models import Category

    categories = {
        c.name: c for c in Category.objects.for_user(user).filter(active=True)
    }
    valid_payments = dict(Expense.PAYMENT_CHOICES)
    clean, rejected = [], []
    for index, raw in enumerate(records, start=1):
        if not isinstance(raw, dict):
            rejected.append((index, "Row is not an object."))
            continue
        reason = None
        category = categories.get(raw.get("category"))
        if category is None:
            reason = f"Unknown category: {raw.get('category')!r}."
        try:
            day = date.fromisoformat(str(raw.get("date", "")))
        except ValueError:
            reason = f"Bad date (want YYYY-MM-DD): {raw.get('date')!r}."
        payment = raw.get("payment")
        if payment not in valid_payments:
            reason = f"Bad payment method: {payment!r}."
        try:
            amount = Decimal(str(raw.get("amount")))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            reason = f"Bad amount (want a number above 0): {raw.get('amount')!r}."
        note = raw.get("description", "") or ""
        if not isinstance(note, str) or len(note) > 200:
            reason = "Bad description (want text up to 200 chars)."
        if reason is not None:
            rejected.append((index, reason))
            continue
        clean.append(
            Expense(
                owner=user,
                amount=amount,
                date=day,
                payment=payment,
                note=note,
                category=category,
            )
        )
    return clean, rejected
