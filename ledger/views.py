from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .analytics import (
    budget_total,
    category_sums,
    daily_average,
    donut_style,
    last_n_days,
    month_shift,
    month_total,
    pct_change,
)
from .budgets import ensure_month_budgets, month_bounds, month_start
from .forms import ExpenseForm
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


class ExpenseListView(OwnerScopedMixin, ListView):
    template_name = "ledger/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        expenses, _, _ = filter_expenses(self.request.user, self.request.GET)
        return expenses

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _, query, category_id = filter_expenses(self.request.user, self.request.GET)
        context.update(
            {
                "form": ExpenseForm(user=self.request.user),
                "show_modal": False,
                "q": query,
                "selected_category": category_id,
                "categories": Category.objects.for_user(self.request.user).filter(
                    active=True
                ),
                "is_filtered": bool(query or category_id),
            }
        )
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
            expenses, query, category_id = filter_expenses(
                self.request.user, self.request.GET
            )
            return render(
                self.request,
                "ledger/expense_list.html",
                {
                    "expenses": expenses,
                    "form": form,
                    "show_modal": True,
                    "q": query,
                    "selected_category": category_id,
                    "categories": Category.objects.for_user(self.request.user).filter(
                        active=True
                    ),
                    "is_filtered": bool(query or category_id),
                },
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

    def get_queryset(self):
        month = month_start(timezone.now().date())
        ensure_month_budgets(self.request.user, month)
        return (
            Budget.objects.for_user(self.request.user)
            .filter(month=month)
            .select_related("category")
        )


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    """Change a category's limit. Only ``limit`` is editable by design (US-10)."""

    model = Budget
    fields = ["limit"]
    template_name = "ledger/budget_form.html"
    success_url = reverse_lazy("budget-list")

    def get_queryset(self):
        return Budget.objects.for_user(self.request.user)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Landing page: KPI hero now (US-11), charts and tables follow in S4."""

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ref = parse_month_param(self.request.GET) or today
        start, _ = month_bounds(ref)
        ensure_month_budgets(self.request.user, start)
        total = month_total(self.request.user, ref)
        budget = budget_total(self.request.user, ref)
        previous = month_total(self.request.user, month_shift(ref, -1))
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
            "avg": daily_average(total, ref, today),
            "change": pct_change(total, previous),
            "today": today_total,
            "pct": min(100, round(float(total / budget) * 100)) if budget else 0,
            "month_label": ref.strftime("%B %Y"),
        }
        context["ref_month"] = ref.strftime("%Y-%m")
        context.update(self._weekly_context(today))
        context.update(self._donut_context(ref))
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

    def _donut_context(self, ref):
        segments = category_sums(self.request.user, ref)
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
