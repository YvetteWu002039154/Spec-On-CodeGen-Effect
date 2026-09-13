from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

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


class User(AbstractBaseUser):
    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    objects = UserManager()


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", "Hard"
        SOFT = "SOFT", "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)
    inventory = models.PositiveIntegerField()

    class Meta:
        ordering = ("title",)


class Borrowing(models.Model):
    actual_return_date = models.DateField(null=True, blank=True)
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="borrowings")

    class Meta:
        ordering = ["-borrow_date"]
        constraints = []

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.expected_return_date < self.borrow_date:
            raise ValidationError("Expected return date must be after borrow date.")

    def validate_borrowing(self, inventory: int):
        if inventory <= 0:
            raise ValueError("Book inventory is zero, cannot borrow.")


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
    session_id = models.CharField(max_length=255, blank=True)
    session_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=7, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=7, choices=Type.choices)