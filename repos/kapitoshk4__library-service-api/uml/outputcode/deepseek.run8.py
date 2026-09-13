from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import Optional


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = 'HARD', 'Hard'
        SOFT = 'SOFT', 'Soft'

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)
    inventory = models.PositiveIntegerField()

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: Optional[str] = None, **extra_fields) -> 'User':
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: Optional[str] = None, **extra_fields) -> 'User':
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    def __str__(self):
        return self.email


class Borrowing(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ['-borrow_date']
        constraints = [
            models.CheckConstraint(
                check=models.Q(expected_return_date__gte=models.F('borrow_date')),
                name='expected_return_after_borrow'
            )
        ]

    def clean(self) -> None:
        if self.actual_return_date and self.actual_return_date < self.borrow_date:
            raise ValidationError('Actual return date cannot be earlier than borrow date.')

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValidationError('Book is out of stock.')

    def save(self, *args, **kwargs) -> None:
        if not self.pk:
            self.validate_borrowing(self.book.inventory)
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.book.title}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        EXPIRED = 'EXPIRED', 'Expired'

    class Type(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        FINE = 'FINE', 'Fine'

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    session_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=8, choices=Type.choices, default=Type.PAYMENT)

    def __str__(self):
        return f"{self.type} - {self.status}"