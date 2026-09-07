from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ExpenseForm
from .models import Expense


@login_required
def home(request):
    return render(request, "home.html")


class OwnerScopedMixin(LoginRequiredMixin):
    """Every expense view only ever sees the request user's rows (US-03/US-05)."""

    def get_queryset(self):
        return Expense.objects.for_user(self.request.user)


class ExpenseListView(OwnerScopedMixin, ListView):
    template_name = "ledger/expense_list.html"
    context_object_name = "expenses"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ExpenseForm(user=self.request.user)
        context["show_modal"] = False
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
            expenses = Expense.objects.for_user(self.request.user)
            return render(
                self.request,
                "ledger/expense_list.html",
                {"expenses": expenses, "form": form, "show_modal": True},
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
