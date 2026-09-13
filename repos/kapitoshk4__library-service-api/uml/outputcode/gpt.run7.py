from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple


class ValidationError(ValueError):
    pass


@dataclass
class Book:
    author: str
    cover: str
    daily_fee: Decimal
    inventory: int
    title: str

    class Cover(str, Enum):
        HARD = "HARD"
        SOFT = "SOFT"

    class Meta:
        ordering: Tuple[str, ...] = ("title",)

    def __post_init__(self) -> None:
        if not isinstance(self.author, str) or not self.author.strip():
            raise ValidationError("author must be a non-empty string")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValidationError("title must be a non-empty string")

        if isinstance(self.cover, Book.Cover):
            self.cover = self.cover.value
        if self.cover not in (Book.Cover.HARD.value, Book.Cover.SOFT.value):
            raise ValidationError("cover must be either HARD or SOFT")

        try:
            self.daily_fee = Decimal(self.daily_fee)
        except Exception as e:
            raise ValidationError("daily_fee must be a valid decimal") from e
        if self.daily_fee < Decimal("0"):
            raise ValidationError("daily_fee must be non-negative")

        if not isinstance(self.inventory, int):
            raise ValidationError("inventory must be an integer")
        if self.inventory < 0:
            raise ValidationError("inventory must be non-negative")


class UserManager:
    use_in_migrations: bool = True

    def __init__(self) -> None:
        self._users_by_email: Dict[str, User] = {}

    def create_user(self, email: str, password: str) -> "User":
        if not isinstance(email, str) or not email.strip():
            raise ValidationError("email must be a non-empty string")
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty string")

        normalized = email.strip().lower()
        if normalized in self._users_by_email:
            raise ValidationError("a user with this email already exists")

        user = User(email=normalized, full_name="", username=None)
        user.set_password(password)
        user.is_superuser = False
        user.is_staff = False
        self._users_by_email[normalized] = user
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email=email, password=password)
        user.is_superuser = True
        user.is_staff = True
        return user


@dataclass
class User:
    email: str
    full_name: str
    username: None = None

    REQUIRED_FIELDS: ClassVar[List[str]] = ["full_name"]
    USERNAME_FIELD: ClassVar[str] = "email"
    objects: ClassVar[UserManager] = UserManager()

    _password: str = ""
    is_superuser: bool = False
    is_staff: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email.strip():
            raise ValidationError("email must be a non-empty string")
        self.email = self.email.strip().lower()
        if not isinstance(self.full_name, str):
            raise ValidationError("full_name must be a string")

    def set_password(self, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty string")
        self._password = password

    def check_password(self, password: str) -> bool:
        return self._password == password


@dataclass
class Borrowing:
    actual_return_date: Optional[date]
    book: Book
    borrow_date: date
    expected_return_date: date
    total_price: Decimal
    user: User

    class Meta:
        constraints: List[Any] = []
        ordering: List[str] = ["-borrow_date"]

    def __post_init__(self) -> None:
        self.clean()

    def validate_borrowing(self, inventory: int) -> None:
        if not isinstance(inventory, int):
            raise ValidationError("inventory must be an integer")
        if inventory <= 0:
            raise ValidationError("book is out of stock")

    def clean(self) -> None:
        if not isinstance(self.book, Book):
            raise ValidationError("book must be a Book instance")
        if not isinstance(self.user, User):
            raise ValidationError("user must be a User instance")
        if not isinstance(self.borrow_date, date):
            raise ValidationError("borrow_date must be a date")
        if not isinstance(self.expected_return_date, date):
            raise ValidationError("expected_return_date must be a date")
        if self.actual_return_date is not None and not isinstance(self.actual_return_date, date):
            raise ValidationError("actual_return_date must be a date or None")

        if self.expected_return_date < self.borrow_date:
            raise ValidationError("expected_return_date cannot be before borrow_date")
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValidationError("actual_return_date cannot be before borrow_date")

        self.validate_borrowing(self.book.inventory)

        try:
            self.total_price = Decimal(self.total_price)
        except Exception as e:
            raise ValidationError("total_price must be a valid decimal") from e
        if self.total_price < Decimal("0"):
            raise ValidationError("total_price must be non-negative")


@dataclass
class Payment:
    borrowing: Borrowing
    money_to_pay: Decimal
    session_id: str
    session_url: str
    status: str
    type: str

    class Status(str, Enum):
        EXPIRED = "EXPIRED"
        PAID = "PAID"
        PENDING = "PENDING"

    class Type(str, Enum):
        FINE = "FINE"
        PAYMENT = "PAYMENT"

    def __post_init__(self) -> None:
        if not isinstance(self.borrowing, Borrowing):
            raise ValidationError("borrowing must be a Borrowing instance")

        try:
            self.money_to_pay = Decimal(self.money_to_pay)
        except Exception as e:
            raise ValidationError("money_to_pay must be a valid decimal") from e
        if self.money_to_pay < Decimal("0"):
            raise ValidationError("money_to_pay must be non-negative")

        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValidationError("session_id must be a non-empty string")
        if not isinstance(self.session_url, str) or not self.session_url.strip():
            raise ValidationError("session_url must be a non-empty string")

        if isinstance(self.status, Payment.Status):
            self.status = self.status.value
        if self.status not in (Payment.Status.EXPIRED.value, Payment.Status.PAID.value, Payment.Status.PENDING.value):
            raise ValidationError("status must be one of: PENDING, PAID, EXPIRED")

        if isinstance(self.type, Payment.Type):
            self.type = self.type.value
        if self.type not in (Payment.Type.FINE.value, Payment.Type.PAYMENT.value):
            raise ValidationError("type must be one of: PAYMENT, FINE")