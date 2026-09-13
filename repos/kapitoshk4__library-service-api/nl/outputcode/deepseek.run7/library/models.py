from django.db import models
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    borrowing_fee = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)

    def __str__(self):
        return self.title

    def is_available(self):
        return self.available_copies > 0


class Borrowing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-borrow_date']

    def save(self, *args, **kwargs):
        if not self.pk and not self.expected_return_date:
            self.expected_return_date = self.borrow_date + timedelta(days=settings.LOAN_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return timezone.now() > self.expected_return_date


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        BORROWING_FEE = 'borrowing_fee', 'Borrowing Fee'
        FINE = 'fine', 'Fine'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    def __str__(self):
        return f"{self.payment_type} - {self.amount} - {self.status}"

