from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import ClassVar, List, Optional, Tuple


class UserManager:
    use_in_migrations: bool = True

    def __init__(self) -> None:
        self._users: List[User] = []

    def create_user(self, email, password):
        if not email:
            raise ValueError("Email is required")
        if not password:
            raise ValueError("Password is required")
        user = User(email=email)
        user.set_password(password)
        self._users.append(user)
        return user

    def create_superuser(self, email, password):
        if not email:
            raise ValueError("Email is required")
        if not password:
            raise ValueError("Password is required")
        user = User(email=email)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        self._users.append(user)
        return user


class User:
    REQUIRED_FIELDS: ClassVar[list] = []
    USERNAME_FIELD: ClassVar[str] = "email"
    username = None
    objects: ClassVar[UserManager]

    def __init__(self, email: str, full_name: str = "") -> None:
        if not email:
            raise ValueError("Email is required")
        self.email = email
        self.full_name = full_name
        self._password: Optional[str] = None
        self.is_superuser: bool = False
        self.is_staff: bool = False

    def set_password(self, password: str) -> None:
        if not password:
            raise ValueError("Password is required")
        self._password = password

    def check_password(self, password: str) -> bool:
        return self._password == password


User.objects = UserManager()


class Book:
    class Cover(str, Enum):
        HARD = "HARD"
        SOFT = "SOFT"

    class Meta:
        ordering: Tuple[str, ...] = ("title",)

    def __init__(
        self,
        title: str,
        author: str,
        cover: Book.Cover | str,
        daily_fee: Decimal | int | float | str,
        inventory: int,
    ) -> None:
        if not title:
            raise ValueError("Title is required")
        if not author:
            raise ValueError("Author is required")
        if isinstance(cover, str):
            try:
                cover = Book.Cover(cover)
            except ValueError as exc:
                raise ValueError("Invalid cover type") from exc
        if inventory < 0:
            raise ValueError("Inventory cannot be negative")
        daily_fee = Decimal(str(daily_fee))
        if daily_fee < Decimal("0"):
            raise ValueError("Daily fee cannot be negative")
        self.title = title
        self.author = author
        self.cover = cover
        self.daily_fee = daily_fee
        self.inventory = inventory


class Borrowing:
    class Meta:
        constraints: list = []
        ordering: list = ["-borrow_date"]

    def __init__(
        self,
        book: Book,
        user: User,
        borrow_date: date,
        expected_return_date: date,
        actual_return_date: Optional[date] = None,
    ) -> None:
        self.book = book
        self.user = user
        self.borrow_date = borrow_date
        self.expected_return_date = expected_return_date
        self.actual_return_date = actual_return_date
        self.clean()

    @property
    def total_price(self) -> Decimal:
        end_date = self.actual_return_date or self.expected_return_date
        days = (end_date - self.borrow_date).days
        if days < 0:
            raise ValueError("Return date cannot be earlier than borrow date")
        return self.book.daily_fee * Decimal(days)

    def validate_borrowing(self, inventory: int):
        if inventory <= 0:
            raise ValueError("Book inventory is not available")

    def clean(self):
        if self.expected_return_date < self.borrow_date:
            raise ValueError("Expected return date cannot be earlier than borrow date")
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValueError("Actual return date cannot be earlier than borrow date")
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
        borrowing: Borrowing,
        money_to_pay: Decimal | int | float | str,
        session_id: str,
        session_url: str,
        status: Payment.Status | str,
        type: Payment.Type | str,
    ) -> None:
        if isinstance(status, str):
            try:
                status = Payment.Status(status)
            except ValueError as exc:
                raise ValueError("Invalid payment status") from exc
        if isinstance(type, str):
            try:
                type = Payment.Type(type)
            except ValueError as exc:
                raise ValueError("Invalid payment type") from exc
        money_to_pay = Decimal(str(money_to_pay))
        if money_to_pay < Decimal("0"):
            raise ValueError("Money to pay cannot be negative")
        self.borrowing = borrowing
        self.money_to_pay = money_to_pay
        self.session_id = session_id
        self.session_url = session_url
        self.status = status
        self.type = type