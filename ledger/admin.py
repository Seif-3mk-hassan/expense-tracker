from django.contrib import admin

from .models import Budget, Category, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("owner", "name", "active")
    list_filter = ("active",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("owner", "amount", "date", "category", "payment")
    list_filter = ("payment", "date")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("owner", "category", "month", "limit")
    list_filter = ("month",)
