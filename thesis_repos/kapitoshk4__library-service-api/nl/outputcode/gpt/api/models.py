# Models
# =========================
from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from decimal import Decimal
from datetime import date, datetime, timedelta


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["title", "author"]

    def clean(self) -> None:
        if self.daily_fee < 0:
            raise ValidationError({"daily_fee": "Daily fee must be non-negative."})

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"


class Borrowing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrowings")
    borrow_date = models.DateField(default=date.today)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-borrow_date", "-id"]

    def clean(self) -> None:
        if self.expected_return_date is None:
            raise ValidationError({"expected_return_date": "Expected return date is required."})
        if self.expected_return_date < self.borrow_date:
            raise ValidationError({"expected_return_date": "Expected return date cannot be before borrow date."})
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValidationError({"actual_return_date": "Actual return date cannot be before borrow date."})

    @property
    def is_returned(self) -> bool:
        return self.actual_return_date is not None

    def __str__(self) -> str:
        return f"Borrowing #{self.pk} - {self.user} - {self.book}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    class Type(models.TextChoices):
        BORROWING = "BORROWING", "Borrowing"
        FINE = "FINE", "Fine"

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name="payments")
    payment_type = models.CharField(max_length=16, choices=Type.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self) -> None:
        if self.amount < 0:
            raise ValidationError({"amount": "Amount must be non-negative."})

    def mark_paid(self) -> None:
        if self.status == self.Status.PAID:
            return
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])

    def __str__(self) -> str:
        return f"Payment #{self.pk} ({self.payment_type}) - {self.status} - {self.amount}"
