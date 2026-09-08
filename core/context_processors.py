from datetime import date

from ledger.analytics import month_shift


def month_options(request):
    """Last 6 months for the topbar picker plus the currently active value."""
    today = date.today()
    return {
        "month_options": [month_shift(today, delta) for delta in range(0, -6, -1)],
        "active_month": request.GET.get("month", ""),
    }


def currency(request):
    """Display currency from the user's profile (US-19)."""
    if request.user.is_authenticated:
        from accounts.models import get_profile

        return {"currency": get_profile(request.user).currency}
    return {"currency": "EGP"}
