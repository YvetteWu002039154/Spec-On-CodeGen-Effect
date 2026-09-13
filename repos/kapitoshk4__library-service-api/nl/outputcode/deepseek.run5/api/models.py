from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

class Book(models.Model):
    COVER_CHOICES = [
        ('HARD', 'Hard'),
        ('SOFT', 'Soft'),
    ]
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=COVER_CHOICES)
    inventory = models.PositiveIntegerField(default=1)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.title

class Borrowing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.is_active = self.actual_return_date is None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class Payment(models.Model):
    PENDING = 'PENDING'
    PAID = 'PAID'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
    ]
    RENTAL = 'RENTAL'
    FINE = 'FINE'
    TYPE_CHOICES = [
        (RENTAL, 'Rental Payment'),
        (FINE, 'Fine Payment'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.payment_type})"

