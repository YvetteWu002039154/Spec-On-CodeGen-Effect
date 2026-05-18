from __future__ import annotations
from datetime import date

class Book:
    class Cover:
        HARD: str = 'HARD'
        SOFT: str = 'SOFT'

    class Meta:
        ordering: tuple = ()

    def __init__(self, title: str, author: str, cover: str = Cover.HARD, daily_fee: float = 0.0, inventory: int = 0):
        self.title = title
        self.author = author
        self.cover = cover
        self.daily_fee = daily_fee
        self.inventory = inventory


class UserManager:
    use_in_migrations: bool = True

    def create_user(self, email: str, password: str) -> 'User':
        user = User(email=email)
        # In a real system, password handling would be applied here.
        return user

    def create_superuser(self, email: str, password: str) -> 'User':
        user = self.create_user(email, password)
        # Additional superuser flags would be set here if needed.
        return user


class User:
    REQUIRED_FIELDS: list = ['email']
    USERNAME_FIELD: str = 'email'
    username = None

    objects: UserManager = UserManager()

    def __init__(self, email: str, full_name: str = ""):
        self.email = email
        self.full_name = full_name


class Borrowing:
    class Meta:
        constraints: list = []
        ordering: list = []

    def __init__(self, book: Book, user: User, borrow_date: date, expected_return_date: date,
                 actual_return_date: date = None, total_price: float = 0.0):
        self.book = book
        self.user = user
        self.borrow_date = borrow_date
        self.expected_return_date = expected_return_date
        self.actual_return_date = actual_return_date
        self.total_price = total_price

    def validate_borrowing(self, inventory: int):
        """Validate that borrowing is possible given the available inventory."""
        if inventory <= 0:
            raise ValueError("No inventory available for this book.")

    def clean(self):
        """Placeholder for model validation."""
        pass


class Payment:
    class Status:
        PENDING: str = 'PENDING'
        PAID: str = 'PAID'
        EXPIRED: str = 'EXPIRED'

    class Type:
        PAYMENT: str = 'PAYMENT'
        FINE: str = 'FINE'

    def __init__(self, borrowing: Borrowing, money_to_pay: float, session_id: str = "", session_url: str = "",
                 status: str = Status.PENDING, type: str = Type.PAYMENT):
        self.borrowing = borrowing
        self.money_to_pay = money_to_pay
        self.session_id = session_id
        self.session_url = session_url
        self.status = status
        self.type = type