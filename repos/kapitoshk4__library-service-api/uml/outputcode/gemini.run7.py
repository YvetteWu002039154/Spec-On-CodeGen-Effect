from typing import List, Tuple, Optional, Any
import datetime

class UserManager:
    use_in_migrations: bool = True

    def create_user(self, email: str, password: str) -> 'User':
        return User(email=email, full_name="")

    def create_superuser(self, email: str, password: str) -> 'User':
        return User(email=email, full_name="")

class User:
    REQUIRED_FIELDS: list = []
    USERNAME_FIELD: str = "email"
    objects: UserManager = UserManager()

    def __init__(self, email: str, full_name: str, username: type(None) = None):
        self.email = email
        self.full_name = full_name
        self.username = username

class Book:
    class Cover:
        HARD: str = "HARD"
        SOFT: str = "SOFT"

    class Meta:
        ordering: tuple = ()

    def __init__(self, author: str, cover: str, daily_fee: float, inventory: int, title: str):
        self.author = author
        self.cover = cover
        self.daily_fee = daily_fee
        self.inventory = inventory
        self.title = title

class Borrowing:
    class Meta:
        constraints: list = []
        ordering: list = []

    def __init__(
        self,
        actual_return_date: Optional[datetime.date],
        book: Book,
        borrow_date: datetime.date,
        expected_return_date: datetime.date,
        total_price: float,
        user: User
    ):
        self.actual_return_date = actual_return_date
        self.book = book
        self.borrow_date = borrow_date
        self.expected_return_date = expected_return_date
        self.total_price = total_price
        self.user = user

    def clean(self) -> None:
        self.validate_borrowing(self.book.inventory)

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValueError("Book is currently out of stock.")

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
        self.borrowing = borrowing
        self.money_to_pay = money_to_pay
        self.session_id = session_id
        self.session_url = session_url
        self.status = status
        self.type = type