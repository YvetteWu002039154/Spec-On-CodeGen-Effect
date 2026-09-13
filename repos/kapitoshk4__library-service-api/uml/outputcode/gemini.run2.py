from typing import List, Tuple, Optional, Any
from datetime import date

class UserManager:
    use_in_migrations: bool = True

    def create_user(self, email: str, password: str) -> 'User':
        return User(email=email)

    def create_superuser(self, email: str, password: str) -> 'User':
        return User(email=email)

class User:
    USERNAME_FIELD: str = 'email'
    REQUIRED_FIELDS: list = []
    objects: UserManager = UserManager()

    def __init__(self, email: str, full_name: str = ""):
        self.email: str = email
        self.full_name: str = full_name
        self.username: type(None) = None

class Book:
    class Cover:
        HARD: str = "HARD"
        SOFT: str = "SOFT"

    class Meta:
        ordering: tuple = ()

    def __init__(self, author: str, cover: str, daily_fee: float, inventory: int, title: str):
        self.author: str = author
        self.cover: str = cover
        self.daily_fee: float = daily_fee
        self.inventory: int = inventory
        self.title: str = title

class Borrowing:
    class Meta:
        constraints: list = []
        ordering: list = []

    def __init__(self, book: Book, user: User, borrow_date: date, expected_return_date: date, actual_return_date: Optional[date] = None, total_price: float = 0.0):
        self.book: Book = book
        self.user: User = user
        self.borrow_date: date = borrow_date
        self.expected_return_date: date = expected_return_date
        self.actual_return_date: Optional[date] = actual_return_date
        self.total_price: float = total_price

    def clean(self) -> None:
        pass

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValueError("Inventory must be greater than 0 to borrow a book.")

class Payment:
    class Status:
        EXPIRED: str = "EXPIRED"
        PAID: str = "PAID"
        PENDING: str = "PENDING"

    class Type:
        FINE: str = "FINE"
        PAYMENT: str = "PAYMENT"

    def __init__(self, borrowing: Borrowing, money_to_pay: float, session_id: str, session_url: str, status: str, type: str):
        self.borrowing: Borrowing = borrowing
        self.money_to_pay: float = money_to_pay
        self.session_id: str = session_id
        self.session_url: str = session_url
        self.status: str = status
        self.type: str = type