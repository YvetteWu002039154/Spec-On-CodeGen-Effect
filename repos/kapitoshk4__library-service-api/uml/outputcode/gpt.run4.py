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
        cover: Book.Cover,
        daily_fee: Decimal,
        inventory: int,
        title: str,
    ) -> None:
        if not isinstance(author, str) or not author.strip():
            raise ValueError("author must be a non-empty string")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(cover, Book.Cover):
            raise ValueError("cover must be a Book.Cover")
        if not isinstance(daily_fee, Decimal):
            raise TypeError("daily_fee must be a Decimal")
        if daily_fee < Decimal("0"):
            raise ValueError("daily_fee must be >= 0")
        if not isinstance(inventory, int):
            raise TypeError("inventory must be an int")
        if inventory < 0:
            raise ValueError("inventory must be >= 0")

        self.author: str = author
        self.cover: Book.Cover = cover
        self.daily_fee: Decimal = daily_fee
        self.inventory: int = inventory
        self.title: str = title


class UserManager:
    use_in_migrations: bool = True

    def __init__(self) -> None:
        self._users_by_email: Dict[str, User] = {}

    def create_user(self, email: str, password: str) -> "User":
        if not isinstance(email, str) or not email.strip():
            raise ValueError("email must be a non-empty string")
        if not isinstance(password, str) or not password:
            raise ValueError("password must be a non-empty string")
        key = email.strip().lower()
        if key in self._users_by_email:
            raise ValueError("user with this email already exists")
        user = User(email=email.strip(), full_name="", username=None)
        user.set_password(password)
        user.is_superuser = False
        self._users_by_email[key] = user
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email=email, password=password)
        user.is_superuser = True
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
        if not isinstance(email, str) or not email.strip():
            raise ValueError("email must be a non-empty string")
        if not isinstance(full_name, str):
            raise TypeError("full_name must be a string")
        if username is not None:
            raise ValueError("username must be NoneType")

        self.email: str = email.strip()
        self.full_name: str = full_name
        self.username: Optional[None] = None

        self._password: Optional[str] = None
        self.is_superuser: bool = False

    def set_password(self, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError("password must be a non-empty string")
        self._password = password

    def check_password(self, password: str) -> bool:
        return self._password is not None and self._password == password


class Borrowing:
    class Meta:
        constraints: List[Any] = []
        ordering: List[str] = ["-borrow_date"]

    def __init__(
        self,
        *,
        user: User,
        book: Book,
        borrow_date: date,
        expected_return_date: date,
        actual_return_date: Optional[date] = None,
        total_price: Optional[Decimal] = None,
    ) -> None:
        if not isinstance(user, User):
            raise TypeError("user must be a User")
        if not isinstance(book, Book):
            raise TypeError("book must be a Book")
        if not isinstance(borrow_date, date):
            raise TypeError("borrow_date must be a date")
        if not isinstance(expected_return_date, date):
            raise TypeError("expected_return_date must be a date")
        if actual_return_date is not None and not isinstance(actual_return_date, date):
            raise TypeError("actual_return_date must be a date or None")
        if total_price is not None and not isinstance(total_price, Decimal):
            raise TypeError("total_price must be a Decimal or None")

        self.user: User = user
        self.book: Book = book
        self.borrow_date: date = borrow_date
        self.expected_return_date: date = expected_return_date
        self.actual_return_date: Optional[date] = actual_return_date
        self.total_price: Decimal = total_price if total_price is not None else Decimal("0")

        self.clean()

    def validate_borrowing(self, inventory: int) -> None:
        if not isinstance(inventory, int):
            raise TypeError("inventory must be an int")
        if inventory <= 0:
            raise ValueError("book is out of stock")

    def clean(self) -> None:
        self.validate_borrowing(self.book.inventory)
        if self.expected_return_date < self.borrow_date:
            raise ValueError("expected_return_date must be >= borrow_date")
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValueError("actual_return_date must be >= borrow_date")

        days = (self.expected_return_date - self.borrow_date).days
        if days < 0:
            raise ValueError("invalid borrowing period")
        self.total_price = (Decimal(days) * self.book.daily_fee).quantize(Decimal("0.01"))


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
        if not isinstance(borrowing, Borrowing):
            raise TypeError("borrowing must be a Borrowing")
        if not isinstance(money_to_pay, Decimal):
            raise TypeError("money_to_pay must be a Decimal")
        if money_to_pay < Decimal("0"):
            raise ValueError("money_to_pay must be >= 0")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(session_url, str) or not session_url.strip():
            raise ValueError("session_url must be a non-empty string")
        if not isinstance(status, Payment.Status):
            raise ValueError("status must be a Payment.Status")
        if not isinstance(type, Payment.Type):
            raise ValueError("type must be a Payment.Type")

        self.borrowing: Borrowing = borrowing
        self.money_to_pay: Decimal = money_to_pay
        self.session_id: str = session_id
        self.session_url: str = session_url
        self.status: Payment.Status = status
        self.type: Payment.Type = type