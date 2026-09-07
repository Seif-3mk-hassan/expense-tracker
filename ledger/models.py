from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import OwnedModel

DEFAULT_CATEGORIES = [
    ("Food", "\U0001F354", "#5EEAD4"),
    ("Transport", "\U0001F695", "#A78BFA"),
    ("Housing", "\U0001F3E0", "#FBBF24"),
    ("Fun", "\U0001F3AE", "#D4F65A"),
    ("Other", "\U0001F6D2", "#8B93A7"),
]


class Category(OwnedModel):
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=8, default="\U0001F6D2")
    color = models.CharField(max_length=7, default="#8B93A7")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_category_per_owner"
            )
        ]

    def __str__(self):
        return f"{self.icon} {self.name}"


class Expense(OwnedModel):
    CASH = "cash"
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    PAYMENT_CHOICES = [
        (CASH, "Cash"),
        (CREDIT, "Credit card"),
        (DEBIT, "Debit card"),
        (TRANSFER, "Bank transfer"),
    ]

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=200, blank=True)
    payment = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=CASH)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="expenses"
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.amount} on {self.date} ({self.category.name})"
