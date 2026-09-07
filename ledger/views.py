from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .budgets import ensure_month_budgets, month_start
from .forms import ExpenseForm
from .models import Budget, Category, Expense


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
