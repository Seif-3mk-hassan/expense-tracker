from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .analytics import (
    budget_total,
    category_sums,
    daily_average,
    donut_style,
    last_6_months,
    last_n_days,
    month_shift,
    month_total,
    pct_change,
)
from .budgets import ensure_month_budgets, month_bounds, month_start
from .forms import ExpenseForm, ImportForm
from .importing import validate_import_rows
from .models import Budget, Category, Expense


def parse_month_param(params):
    """YYYY-MM from ?month=, else None (defaults to the current month)."""
    from datetime import date

    raw = params.get("month", "").strip()
    try:
        year, month = raw.split("-")
        return date(int(year), int(month), 1)
    except (ValueError, AttributeError):
        return None


@login_required
def home(request):
    return render(request, "home.html")


class OwnerScopedMixin(LoginRequiredMixin):
    """Every expense view only ever sees the request user's rows (US-03/US-05)."""

    def get_queryset(self):
        return Expense.objects.for_user(self.request.user)


def filter_expenses(user, params):
    """Shared search + category filtering over one user's expenses (US-06)."""
    expenses = Expense.objects.for_user(user)
    query = params.get("q", "").strip()
    if query:
        expenses = expenses.filter(
            Q(note__icontains=query) | Q(category__name__icontains=query)
        )
    category_id = params.get("category", "").strip()
    if category_id.isdigit():
        expenses = expenses.filter(category__pk=int(category_id))
    return expenses, query, category_id


def expense_list_context(user, params, form=None, show_modal=False):
    """Shared context for the expenses page, including summary and density."""
    expenses, query, category_id = filter_expenses(user, params)
    total = expenses.aggregate(total=Sum("amount"))["total"] or 0
    count = expenses.count()
    return {
        "expenses": expenses,
        "form": form or ExpenseForm(user=user),
        "show_modal": show_modal,
        "q": query,
        "selected_category": category_id,
        "categories": Category.objects.for_user(user).filter(active=True),
        "is_filtered": bool(query or category_id),
        "summary": {"count": count, "total": total},
        "density": "roomy" if count <= 10 else "standard",
    }


class ExpenseListView(OwnerScopedMixin, ListView):
    template_name = "ledger/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        expenses, _, _ = filter_expenses(self.request.user, self.request.GET)
        return expenses

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(expense_list_context(self.request.user, self.request.GET))
        context["show_modal"] = self.request.GET.get("modal") == "1"
        return context


class ExpenseCreateView(OwnerScopedMixin, CreateView):
    form_class = ExpenseForm
    template_name = "ledger/expense_form.html"
    success_url = reverse_lazy("expense-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.POST.get("from_modal"):
            context = expense_list_context(
                self.request.user, self.request.GET, form=form, show_modal=True
            )
            return render(
                self.request,
                "ledger/expense_list.html",
                context,
                status=400,
            )
        return super().form_invalid(form)


class ExpenseUpdateView(OwnerScopedMixin, UpdateView):
    form_class = ExpenseForm
    template_name = "ledger/expense_form.html"
    success_url = reverse_lazy("expense-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ExpenseDeleteView(OwnerScopedMixin, DeleteView):
    template_name = "ledger/expense_confirm_delete.html"
    success_url = reverse_lazy("expense-list")


class BudgetListView(LoginRequiredMixin, ListView):
    """Monthly budget cards; also ensures the month's rows exist (US-09)."""

    template_name = "ledger/budget_list.html"
    context_object_name = "budgets"

    def get_month(self):
        from accounts.models import get_profile

        start_day = get_profile(self.request.user).month_start_day
        return month_start(
            parse_month_param(self.request.GET) or timezone.now().date(), start_day
        ), start_day

    def get_queryset(self):
        from accounts.models import get_profile

        month, start_day = self.get_month()
        ensure_month_budgets(self.request.user, month, start_day)
        return (
            Budget.objects.for_user(self.request.user)
            .filter(month=month)
            .select_related("category")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, _ = self.get_month()
        context["month_label"] = month.strftime("%B %Y")
        return context


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    """Change a category's limit. Only ``limit`` is editable by design (US-10)."""

    model = Budget
    fields = ["limit"]
    template_name = "ledger/budget_form.html"
    success_url = reverse_lazy("budget-list")

    def get_queryset(self):
        return Budget.objects.for_user(self.request.user)


class InsightsView(LoginRequiredMixin, TemplateView):
    """Six-month trends plus budget pressure and one auto tip (US-15)."""

    template_name = "ledger/insights.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import get_profile

        today = timezone.now().date()
        ref = parse_month_param(self.request.GET) or today
        start_day = get_profile(self.request.user).month_start_day
        history = last_6_months(self.request.user, ref, start_day)
        peak = max([h["total"] for h in history] or [0])
        for entry in history:
            entry["pct"] = (
                round(float(entry["total"] / peak) * 100) if peak else 0
            )
        start, _ = month_bounds(ref, start_day)
        ensure_month_budgets(self.request.user, start, start_day)
        budgets = list(
            Budget.objects.for_user(self.request.user)
            .filter(month=start)
            .select_related("category")
            .order_by("-limit")
        )
        strained = [b for b in budgets if b.is_warning]
        tip = max(strained, key=lambda b: b.percent_used) if strained else None
        context.update(
            {
                "history": history,
                "budgets": budgets,
                "tip": tip,
                "month_label": ref.strftime("%B %Y"),
            }
        )
        return context


class JsonExportView(LoginRequiredMixin, View):
    """Download all own expenses in the prototyped JSON shape (US-16)."""

    def get(self, request):
        rows = (
            Expense.objects.for_user(request.user)
            .select_related("category")
            .order_by("date", "id")
        )
        payload = {
            "exported": timezone.now().isoformat(),
            "currency": "EGP",
            "expenses": [
                {
                    "description": e.note,
                    "category": e.category.name,
                    "date": e.date.isoformat(),
                    "payment": e.payment,
                    "amount": str(e.amount),
                }
                for e in rows
            ],
        }
        response = JsonResponse(payload, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = (
            "attachment; filename=expenses-export.json"
        )
        return response


class CsvExportView(LoginRequiredMixin, View):
    """Same dataset as CSV for spreadsheets (US-18)."""

    def get(self, request):
        import csv

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            "attachment; filename=expenses-export.csv"
        )
        writer = csv.writer(response)
        writer.writerow(["description", "category", "date", "payment", "amount"])
        for e in (
            Expense.objects.for_user(request.user)
            .select_related("category")
            .order_by("date", "id")
        ):
            writer.writerow(
                [e.note, e.category.name, e.date.isoformat(), e.payment, e.amount]
            )
        return response


class JsonImportView(LoginRequiredMixin, FormView):
    """Upload a JSON export; report imported vs rejected rows (US-17)."""

    form_class = ImportForm
    template_name = "ledger/import.html"

    def form_valid(self, form):
        import json

        raw = form.cleaned_data["file"].read()
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            form.add_error(None, "That file is not valid JSON. Nothing imported.")
            return self.form_invalid(form)
        records = data.get("expenses") if isinstance(data, dict) else None
        if not isinstance(records, list):
            form.add_error(
                None, 'Want an object with an "expenses" list. Nothing imported.'
            )
            return self.form_invalid(form)
        clean, rejected = validate_import_rows(self.request.user, records)
        with transaction.atomic():
            Expense.objects.bulk_create(clean)
        return render(
            self.request,
            "ledger/import_report.html",
            {
                "imported": len(clean),
                "rejected": rejected,
            },
        )


class DashboardView(LoginRequiredMixin, TemplateView):
    """Landing page: KPI hero now (US-11), charts and tables follow in S4."""

    template_name = "home.html"

    def _start_day(self):
        from accounts.models import get_profile

        return get_profile(self.request.user).month_start_day

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ref = parse_month_param(self.request.GET) or today
        start_day = self._start_day()
        start, _ = month_bounds(ref, start_day)
        ensure_month_budgets(self.request.user, start, start_day)
        total = month_total(self.request.user, ref, start_day)
        budget = budget_total(self.request.user, ref, start_day)
        previous = month_total(
            self.request.user, month_shift(ref, -1, start_day), start_day
        )
        today_total = (
            Expense.objects.for_user(self.request.user)
            .filter(date=today)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )
        context["hero"] = {
            "total": total,
            "budget": budget,
            "left": budget - total,
            "avg": daily_average(total, ref, today, start_day),
            "change": pct_change(total, previous),
            "today": today_total,
            "pct": min(100, round(float(total / budget) * 100)) if budget else 0,
            "month_label": ref.strftime("%B %Y"),
        }
        context["ref_month"] = ref.strftime("%Y-%m")
        context["recent"] = Expense.objects.for_user(self.request.user)[:5]
        context["budgets"] = (
            Budget.objects.for_user(self.request.user)
            .filter(month=start)
            .select_related("category")
        )
        context.update(self._weekly_context(today))
        context.update(self._donut_context(ref, start_day))
        return context

    PLOT_PX = 162
    LABEL_PX = 24

    def _weekly_context(self, today):
        days = last_n_days(self.request.user, today)
        peak = max([d["total"] for d in days] or [0])
        for day in days:
            day["px"] = (
                round(float(day["total"] / peak) * self.PLOT_PX) if peak else 0
            )
            day["is_today"] = day["date"] == today
            day["is_peak"] = peak > 0 and day["total"] == peak
        average = round(sum(d["total"] for d in days) / len(days), 2)
        avg_px = round(float(average / peak) * self.PLOT_PX) if peak else 0
        return {
            "weekly": {
                "days": days,
                "avg": average,
                "avg_bottom_px": self.LABEL_PX + avg_px,
            }
        }

    def _donut_context(self, ref, start_day=1):
        segments = category_sums(self.request.user, ref, start_day)
        total = sum(s["total"] for s in segments)
        for seg in segments:
            seg["pct"] = round(float(seg["total"] / total) * 100) if total else 0
        return {
            "donut": {
                "style": donut_style(segments, total),
                "segments": segments,
                "total": total,
            }
        }
