from django.db import models
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rental fee per day")
    fine_per_day = models.DecimalField(max_digits=10, decimal_places=2, help_text="Fine per day if overdue")

    def __str__(self):
        return self.title

class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} borrowed {self.book} on {self.borrow_date}"

    def save(self, *args, **kwargs):
        if not self.expected_return_date:
            self.expected_return_date = self.borrow_date + timedelta(days=7)  # default 7 days
        super().save(*args, **kwargs)

class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    )
    TYPE_CHOICES = (
        ('BORROWING_FEE', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    session_id = models.CharField(max_length=255, blank=True, null=True)  # for external payment integration

    def __str__(self):
        return f"{self.payment_type} - {self.amount} - {self.status}"

