from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils import timezone


# books/models.py
class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", "Hard"
        SOFT = "SOFT", "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)
    inventory = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


# borrowings/models.py
class Borrowing(models.Model):
    borrow_date = models.DateField(default=timezone.now)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="borrowings")
    total_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["-borrow_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(expected_return_date__gte=models.F("borrow_date")),
                name="expected_return_after_borrow",
            )
        ]

    def clean(self):
        if self.pk is None and self.book_id:
            self.validate_borrowing(self.book.inventory)

    def validate_borrowing(self, inventory: int):
        if inventory <= 0:
            raise ValidationError("No books available for borrowing.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.total_price:
            days = (self.expected_return_date - self.borrow_date).days
            self.total_price = self.book.daily_fee * max(days, 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} borrowed {self.book} on {self.borrow_date}"


# payments/models.py
class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        EXPIRED = "EXPIRED", "Expired"

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        FINE = "FINE", "Fine"

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name="payments")
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    session_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=7, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=7, choices=Type.choices)

    def __str__(self):
        return f"{self.type} - {self.status}"


# users/models.py
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"]:
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.email