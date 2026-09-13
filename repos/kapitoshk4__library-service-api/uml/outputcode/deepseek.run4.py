from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    use_in_migrations: bool = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: list[str] = ["full_name"]
    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=255)
    objects = UserManager()

class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", _("Hard cover")
        SOFT = "SOFT", _("Soft cover")

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=5, choices=Cover.choices)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)
    inventory = models.PositiveIntegerField()

    class Meta:
        ordering: tuple = ("title",)

    def __str__(self):
        return self.title

class Borrowing(models.Model):
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrowings")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="borrowings")
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints: list = [
            models.CheckConstraint(
                check=models.Q(expected_return_date__gt=models.F("borrow_date")),
                name="expected_after_borrow",
            )
        ]
        ordering: list = ["-borrow_date"]

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValidationError("This book is currently out of stock.")

    def clean(self):
        if self.pk is None:
            self.validate_borrowing(self.book.inventory)
        super().clean()

    def __str__(self):
        return f"{self.book.title} borrowed by {self.user.email}"

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PAID = "PAID", _("Paid")
        EXPIRED = "EXPIRED", _("Expired")

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT", _("Payment")
        FINE = "FINE", _("Fine")

    borrowing = models.ForeignKey(Borrowing, on_delete=models.PROTECT, related_name="payments")
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    session_id = models.CharField(max_length=255)
    session_url = models.URLField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.PAYMENT)

    def __str__(self):
        return f"Payment {self.id} for {self.borrowing}"