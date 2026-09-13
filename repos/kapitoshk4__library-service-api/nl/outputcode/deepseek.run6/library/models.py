from django.db import models
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2, help_text="Daily borrowing fee in dollars")
    fine_per_day = models.DecimalField(max_digits=6, decimal_places=2, help_text="Overdue fine per day in dollars")

    def __str__(self):
        return self.title

    def is_available(self):
        """Check if no active borrowing exists (actual_return_date is null)"""
        active_borrowings = self.borrowings.filter(actual_return_date__isnull=True)
        return not active_borrowings.exists()

class Borrowing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-borrow_date']

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.borrow_date})"

    def save(self, *args, **kwargs):
        # Automatically set expected return date if not provided (e.g., 30 days)
        if not self.expected_return_date:
            self.expected_return_date = self.borrow_date + timedelta(days=30)
        super().save(*args, **kwargs)

    def return_book(self):
        """Set actual return date and deactivate borrowing"""
        if self.actual_return_date is not None:
            raise ValueError("Book already returned")
        self.actual_return_date = date.today()
        self.is_active = False
        self.save()

    @property
    def is_overdue(self):
        """Check if book is still active and past expected return date"""
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return date.today() > self.expected_return_date

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('BORROWING', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    )

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_type} - {self.amount} ({self.status})"

