from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    def __str__(self):
        return self.email


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", "Hard"
        SOFT = "SOFT", "Soft"

    class Meta:
        ordering = ("title",)

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.title} by {self.author}"


class Borrowing(models.Model):
    class Meta:
        ordering = ["-borrow_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(expected_return_date__gt=models.F("borrow_date")),
                name="expected_return_date_after_borrow_date",
            )
        ]

    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="borrowings")

    @property
    def total_price(self):
        if self.actual_return_date:
            days = (self.actual_return_date - self.borrow_date).days
        else:
            days = (self.expected_return_date - self.borrow_date).days
        return days * self.book.daily_fee

    @staticmethod
    def validate_borrowing(inventory: int):
        if inventory <= 0:
            raise ValidationError(
                {"inventory": "Book inventory must be greater than 0 to borrow."}
            )

    def clean(self):
        self.validate_borrowing(self.book.inventory)
        if self.expected_return_date and self.borrow_date:
            if self.expected_return_date <= self.borrow_date:
                raise ValidationError(
                    {
                        "expected_return_date": "Expected return date must be after borrow date."
                    }
                )
        if self.actual_return_date and self.borrow_date:
            if self.actual_return_date < self.borrow_date:
                raise ValidationError(
                    {
                        "actual_return_date": "Actual return date cannot be before borrow date."
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Borrowing of {self.book.title} by {self.user.email}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        EXPIRED = "EXPIRED", "Expired"

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        FINE = "FINE", "Fine"

    borrowing = models.ForeignKey(
        Borrowing, on_delete=models.CASCADE, related_name="payments"
    )
    session_url = models.URLField(max_length=500, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.PAYMENT
    )

    def __str__(self):
        return f"Payment {self.type} - {self.status} for borrowing {self.borrowing_id}"