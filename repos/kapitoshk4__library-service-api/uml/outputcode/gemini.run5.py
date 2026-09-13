import datetime
from typing import Optional, List, Tuple

class UserManager:
    use_in_migrations: bool = True

    def create_user(self, email: str, password: str) -> 'User':
        user = User(email=email, full_name="")
        return user

    def create_superuser(self, email: str, password: str) -> 'User':
        user = User(email=email, full_name="")
        return user

class User:
    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: list = []
    objects: UserManager = UserManager()

    def __init__(self, email: str, full_name: str):
        self.email: str = email
        self.full_name: str = full_name
        self.username: None = None

class Book:
    class Cover:
        HARD: str = "HARD"
        SOFT: str = "SOFT"

    class Meta:
        ordering: tuple = ("title",)

    def __init__(self, title: str, author: str, cover: str, daily_fee: float, inventory: int):
        self.title: str = title
        self.author: str = author
        self.cover: str = cover
        self.daily_fee: float = daily_fee
        self.inventory: int = inventory

class Borrowing:
    class Meta:
        constraints: list = []
        ordering: list = ["-borrow_date"]

    def __init__(
        self,
        book: Book,
        user: User,
        borrow_date: datetime.date,
        expected_return_date: datetime.date,
        actual_return_date: Optional[datetime.date] = None,
        total_price: float = 0.0
    ):
        self.book: Book = book
        self.user: User = user
        self.borrow_date: datetime.date = borrow_date
        self.expected_return_date: datetime.date = expected_return_date
        self.actual_return_date: Optional[datetime.date] = actual_return_date
        self.total_price: float = total_price

    def clean(self) -> None:
        self.validate_borrowing(self.book.inventory)

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValueError("Cannot borrow book: inventory is zero or less.")

class Payment:
    class Status:
        EXPIRED: str = "EXPIRED"
        PAID: str = "PAID"
        PENDING: str = "PENDING"

    class Type:
        FINE: str = "FINE"
        PAYMENT: str = "PAYMENT"

    def __init__(
        self,
        borrowing: Borrowing,
        money_to_pay: float,
        session_id: str,
        session_url: str,
        status: str,
        type: str
    ):
        self.borrowing: Borrowing = borrowing
        self.money_to_pay: float = money_to_pay
        self.session_id: str = session_id
        self.session_url: str = session_url
        self.status: str = status
        self.type: str = type