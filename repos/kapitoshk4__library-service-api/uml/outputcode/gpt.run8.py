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

    class Cover:
        HARD: ClassVar[str] = "HARD"
        SOFT: ClassVar[str] = "SOFT"

    class Meta:
        ordering: ClassVar[Tuple[str, ...]] = ("title",)

    def __post_init__(self) -> None:
        if not isinstance(self.author, str) or not self.author.strip():
            raise ValidationError("author must be a non-empty string")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValidationError("title must be a non-empty string")
        if self.cover not in (self.Cover.HARD, self.Cover.SOFT):
            raise ValidationError("cover must be one of Book.Cover.HARD or Book.Cover.SOFT")
        if not isinstance(self.daily_fee, Decimal):
            raise ValidationError("daily_fee must be a Decimal")
        if self.daily_fee < Decimal("0"):
            raise ValidationError("daily_fee must be >= 0")
        if not isinstance(self.inventory, int):
            raise ValidationError("inventory must be an int")
        if self.inventory < 0:
            raise ValidationError("inventory must be >= 0")


class UserManager:
    use_in_migrations: bool = True

    def __init__(self) -> None:
        self._users_by_email: Dict[str, User] = {}

    def create_user(self, email: str, password: str) -> "User":
        if not isinstance(email, str) or not email.strip():
            raise ValidationError("email must be a non-empty string")
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty string")
        key = email.strip().lower()
        if key in self._users_by_email:
            raise ValidationError("user with this email already exists")
        user = User(email=email.strip(), full_name="", username=None)
        user._set_password(password)
        self._users_by_email[key] = user
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email=email, password=password)
        user.is_superuser = True
        user.is_staff = True
        return user


@dataclass
class User:
    REQUIRED_FIELDS: ClassVar[List[str]] = ["full_name"]
    USERNAME_FIELD: ClassVar[str] = "email"
    objects: ClassVar[UserManager] = UserManager()

    email: str
    full_name: str
    username: None = None

    is_superuser: bool = False
    is_staff: bool = False
    _password_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email.strip():
            raise ValidationError("email must be a non-empty string")
        self.email = self.email.strip()
        if not isinstance(self.full_name, str):
            raise ValidationError("full_name must be a string")
        if self.username is not None:
            raise ValidationError("username must be None")

    def _set_password(self, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValidationError("password must be a non-empty string")
        self._password_hash = f"hashed:{password}"

    def check_password(self, password: str) -> bool:
        if not isinstance(password, str):
            return False
        return self._password_hash == f"hashed:{password}"


@dataclass
class Borrowing:
    actual_return_date: Optional[date]
    book: Book
    borrow_date: date
    expected_return_date: date
    total_price: Decimal
    user: User

    class Meta:
        constraints: ClassVar[List[Any]] = []
        ordering: ClassVar[List[str]] = ["-borrow_date"]

    def __post_init__(self) -> None:
        self.clean()

    def validate_borrowing(self, inventory: int) -> None:
        if not isinstance(inventory, int):
            raise ValidationError("inventory must be an int")
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
            raise ValidationError("expected_return_date must be >= borrow_date")
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValidationError("actual_return_date must be >= borrow_date")

        self.validate_borrowing(self.book.inventory)

        if not isinstance(self.total_price, Decimal):
            raise ValidationError("total_price must be a Decimal")
        if self.total_price < Decimal("0"):
            raise ValidationError("total_price must be >= 0")


@dataclass
class Payment:
    borrowing: Borrowing
    money_to_pay: Decimal
    session_id: str
    session_url: str
    status: str
    type: str

    class Status:
        EXPIRED: ClassVar[str] = "EXPIRED"
        PAID: ClassVar[str] = "PAID"
        PENDING: ClassVar[str] = "PENDING"

    class Type:
        FINE: ClassVar[str] = "FINE"
        PAYMENT: ClassVar[str] = "PAYMENT"

    def __post_init__(self) -> None:
        if not isinstance(self.borrowing, Borrowing):
            raise ValidationError("borrowing must be a Borrowing instance")
        if not isinstance(self.money_to_pay, Decimal):
            raise ValidationError("money_to_pay must be a Decimal")
        if self.money_to_pay < Decimal("0"):
            raise ValidationError("money_to_pay must be >= 0")
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValidationError("session_id must be a non-empty string")
        if not isinstance(self.session_url, str) or not self.session_url.strip():
            raise ValidationError("session_url must be a non-empty string")
        if self.status not in (self.Status.EXPIRED, self.Status.PAID, self.Status.PENDING):
            raise ValidationError("status must be one of Payment.Status values")
        if self.type not in (self.Type.FINE, self.Type.PAYMENT):
            raise ValidationError("type must be one of Payment.Type values")