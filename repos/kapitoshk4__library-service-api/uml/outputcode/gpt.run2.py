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
        ordering: ClassVar[Tuple[str, ...]] = ("title",)

    def __init__(
        self,
        *,
        author: str,
        cover: Book.Cover,
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
        if not email or not isinstance(email, str):
            raise ValueError("email is required")
        if password is None or not isinstance(password, str) or password == "":
            raise ValueError("password is required")
        normalized = email.strip().lower()
        if normalized in self._users_by_email:
            raise ValueError("user with this email already exists")
        user = User(email=normalized, full_name="", username=None)
        user._set_password(password)
        self._users_by_email[normalized] = user
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        return user


class User:
    REQUIRED_FIELDS: ClassVar[List[str]] = ["full_name"]
    USERNAME_FIELD: ClassVar[str] = "email"
    objects: ClassVar[UserManager] = UserManager()

    def __init__(
        self,
        *,
        email: str,
        full_name: str,
        username: Optional[None] = None,
    ) -> None:
        if not email or not isinstance(email, str):
            raise ValueError("email is required")
        self.email: str = email.strip().lower()
        self.full_name: str = full_name
        self.username: Optional[None] = username
        self.is_superuser: bool = False
        self.is_staff: bool = False
        self._password: Optional[str] = None

    def _set_password(self, password: str) -> None:
        if password is None or not isinstance(password, str) or password == "":
            raise ValueError("password is required")
        self._password = password

    def check_password(self, password: str) -> bool:
        return self._password == password


class Borrowing:
    class Meta:
        constraints: ClassVar[List[Any]] = []
        ordering: ClassVar[List[str]] = ["-borrow_date"]

    def __init__(
        self,
        *,
        actual_return_date: Optional[date] = None,
        book: Book,
        borrow_date: date,
        expected_return_date: date,
        total_price: Decimal = Decimal("0"),
        user: User,
    ) -> None:
        self.actual_return_date: Optional[date] = actual_return_date
        self.book: Book = book
        self.borrow_date: date = borrow_date
        self.expected_return_date: date = expected_return_date
        self.total_price: Decimal = self._validate_total_price(total_price)
        self.user: User = user

    @staticmethod
    def _validate_total_price(value: Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        if value < Decimal("0"):
            raise ValueError("total_price must be non-negative")
        return value

    def validate_borrowing(self, inventory: int) -> None:
        if not isinstance(inventory, int):
            raise TypeError("inventory must be an int")
        if inventory <= 0:
            raise ValueError("book is out of stock")
        if self.expected_return_date < self.borrow_date:
            raise ValueError("expected_return_date cannot be earlier than borrow_date")
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValueError("actual_return_date cannot be earlier than borrow_date")

    def clean(self) -> None:
        self.validate_borrowing(self.book.inventory)


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
        status: Payment.Status,
        type: Payment.Type,
    ) -> None:
        self.borrowing: Borrowing = borrowing
        self.money_to_pay: Decimal = self._validate_money_to_pay(money_to_pay)
        self.session_id: str = self._validate_non_empty_str(session_id, "session_id")
        self.session_url: str = self._validate_non_empty_str(session_url, "session_url")
        self.status: Payment.Status = status
        self.type: Payment.Type = type

    @staticmethod
    def _validate_non_empty_str(value: str, field_name: str) -> str:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f"{field_name} must be a non-empty string")
        return value

    @staticmethod
    def _validate_money_to_pay(value: Decimal) -> Decimal:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        if value < Decimal("0"):
            raise ValueError("money_to_pay must be non-negative")
        return value