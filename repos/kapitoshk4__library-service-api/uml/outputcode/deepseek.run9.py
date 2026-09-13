from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from decimal import Decimal
from typing import Optional


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

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    def __str__(self) -> str:
        return self.email


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = 'HARD', 'Hard'
        SOFT = 'SOFT', 'Soft'

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2)
    inventory = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('title',)

    def __str__(self) -> str:
        return self.title


class Borrowing(models.Model):
    class Meta:
        ordering = ['-borrow_date']
        constraints = []

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField(default=timezone.now)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def clean(self) -> None:
        if self.book_id is not None:
            self.validate_borrowing(self.book.inventory)

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValidationError(f'Book "{self.book.title}" is out of stock.')

    def __str__(self) -> str:
        return f'{self.user.email} borrowed {self.book.title} on {self.borrow_date}'


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        EXPIRED = 'EXPIRED', 'Expired'

    class Type(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        FINE = 'FINE', 'Fine'

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    session_url = models.URLField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=7, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=7, choices=Type.choices, default=Type.PAYMENT)

    def __str__(self) -> str:
        return f'Payment {self.id} - {self.status}'