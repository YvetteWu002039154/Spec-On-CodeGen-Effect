# File: api/models.py
from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import date

class Book(models.Model):
    COVER_CHOICES = (
        ('HARD', 'Hardcover'),
        ('SOFT', 'Softcover'),
    )
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=COVER_CHOICES, default='SOFT')
    inventory = models.PositiveIntegerField(default=1)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    fine_per_day = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.title} ({self.author})"

    def available_copies(self):
        active_borrowings = self.borrowings.filter(actual_return_date__isnull=True).count()
        return self.inventory - active_borrowings

class Borrowing(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-borrow_date']

    def __str__(self):
        return f"{self.book.title} borrowed by {self.user.username} on {self.borrow_date}"

    @property
    def is_active(self):
        return self.actual_return_date is None

    @property
    def is_overdue(self):
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return date.today() > self.expected_return_date

    def overdue_days(self):
        if self.actual_return_date:
            return (self.actual_return_date - self.expected_return_date).days
        if self.is_overdue:
            return (date.today() - self.expected_return_date).days
        return 0

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('BORROWING_FEE', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    )
    borrowing = models.ForeignKey(
        Borrowing,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=15, choices=PAYMENT_TYPE_CHOICES)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.payment_type} payment for borrowing #{self.borrowing.id} - {self.status}"
