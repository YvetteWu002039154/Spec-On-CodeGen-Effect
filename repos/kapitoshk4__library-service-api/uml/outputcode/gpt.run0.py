from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple


class Book:
    class Cover(str, Enum):
        HARD = "HARD"
        SOFT = "SOFT"

    class Meta:
        ordering: Tuple[str, ...] = ("title",)

    def __init__(
        self,
        *,
        author: str,
        cover: "Book.Cover",
        daily_fee: Decimal,
        inventory: int,
        title: str,
    ) -> None:
        self.author: str = author
        self.cover: Book.Cover = cover
        self.daily_fee: Decimal = self._validate_daily_fee(daily_fee)
        self.inventory: int = self._validate_inventory(inventory)
        self.title: str = title

    @staticmethod
    def _validate_daily_fee(value: Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        if value < Decimal("0"):
            raise ValueError("daily_fee must be non-negative")
        return value

    @staticmethod
    def _validate_inventory(value: int) -> int:
        if not isinstance(value, int):
            raise TypeError("inventory must be an int")
        if value < 0:
            raise ValueError("inventory must be non-negative")
        return value


class UserManager:
    use_in_migrations: bool = True

    def __init__(self) -> None:
        self._users_by_email: Dict[str, User] = {}

    def create_user(self, email: str, password: str) -> "User":
        if not isinstance(email, str) or not email.strip():
            raise ValueError("email is required")
        if not isinstance(password, str) or not password:
            raise ValueError("password is required")
        normalized_email = email.strip().lower()
        if normalized_email in self._users_by_email:
            raise ValueError("user with this email already exists")
        user = User(email=normalized_email, full_name="", username=None)
        user.set_password(password)
        user.is_superuser = False
        self._users_by_email[normalized_email] = user
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email, password)
        user.is_superuser = True
        return user


class User:
    REQUIRED_FIELDS: List[str] = ["full_name"]
    USERNAME_FIELD: str = "email"
    objects: ClassVar[UserManager] = UserManager()

    def __init__(self, *, email: str, full_name: str, username: Optional[None] = None) -> None:
        if not isinstance(email, str) or not email.strip():
            raise ValueError("email is required")
        self.email: str = email.strip().lower()
        self.full_name: str = full_name
        self.username: Optional[None] = username
        self._password: Optional[str] = None
        self.is_superuser: bool = False

    def set_password(self, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError("password is required")
        self._password = password

    def check_password(self, password: str) -> bool:
        return self._password is not None and self._password == password


class Borrowing:
    class Meta:
        ordering: List[str] = ["-borrow_date"]
        constraints: List[Any] = []

    def __init__(
        self,
        *,
        actual_return_date: Optional[date],
        book: Book,
        borrow_date: date,
        expected_return_date: date,
        total_price: Decimal,
        user: User,
    ) -> None:
        self.actual_return_date: Optional[date] = actual_return_date
        self.book: Book = book
        self.borrow_date: date = borrow_date
        self.expected_return_date: date = expected_return_date
        self.total_price: Decimal = self._coerce_decimal(total_price)
        self.user: User = user
        self.clean()

    @staticmethod
    def _coerce_decimal(value: Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value

    def validate_borrowing(self, inventory: int) -> None:
        if not isinstance(inventory, int):
            raise TypeError("inventory must be an int")
        if inventory <= 0:
            raise ValueError("book is out of stock")

    def clean(self) -> None:
        if not isinstance(self.book, Book):
            raise TypeError("book must be a Book instance")
        if not isinstance(self.user, User):
            raise TypeError("user must be a User instance")
        if not isinstance(self.borrow_date, date):
            raise TypeError("borrow_date must be a date")
        if not isinstance(self.expected_return_date, date):
            raise TypeError("expected_return_date must be a date")
        if self.actual_return_date is not None and not isinstance(self.actual_return_date, date):
            raise TypeError("actual_return_date must be a date or None")

        if self.expected_return_date < self.borrow_date:
            raise ValueError("expected_return_date cannot be earlier than borrow_date")
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValueError("actual_return_date cannot be earlier than borrow_date")

        self.validate_borrowing(self.book.inventory)

        if self.total_price < Decimal("0"):
            raise ValueError("total_price must be non-negative")


class Payment:
    class Status(str, Enum):
        EXPIRED = "EXPIRED"
        PAID = "PAID"
        PENDING = "PENDING"

    class Type(str, Enum):
        FINE = "FINE"
        PAYMENT = "PAYMENT"

    def __init__(
        self,
        *,
        borrowing: Borrowing,
        money_to_pay: Decimal,
        session_id: str,
        session_url: str,
        status: "Payment.Status",
        type: "Payment.Type",
    ) -> None:
        if not isinstance(borrowing, Borrowing):
            raise TypeError("borrowing must be a Borrowing instance")
        self.borrowing: Borrowing = borrowing
        self.money_to_pay: Decimal = self._validate_money_to_pay(money_to_pay)
        self.session_id: str = self._validate_non_empty_str(session_id, "session_id")
        self.session_url: str = self._validate_non_empty_str(session_url, "session_url")
        if not isinstance(status, Payment.Status):
            raise TypeError("status must be a Payment.Status")
        if not isinstance(type, Payment.Type):
            raise TypeError("type must be a Payment.Type")
        self.status: Payment.Status = status
        self.type: Payment.Type = type

    @staticmethod
    def _validate_non_empty_str(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        return value

    @staticmethod
    def _validate_money_to_pay(value: Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        if value < Decimal("0"):
            raise ValueError("money_to_pay must be non-negative")
        return value