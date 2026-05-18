from typing import Optional
from datetime import date

class Book:
    class Cover:
        HARD: str = "HARD"
        SOFT: str = "SOFT"

    class Meta:
        ordering: tuple = ()

    def __init__(self, author: str, cover: str, daily_fee: float, inventory: int, title: str) -> None:
        self.author = author
        self.cover = cover
        self.daily_fee = daily_fee
        self.inventory = inventory
        self.title = title


class User:
    REQUIRED_FIELDS: list = []
    USERNAME_FIELD: str = "email"

    def __init__(self, email: str, full_name: str) -> None:
        self.email = email
        self.full_name = full_name
        self.username: type(None) = None


class UserManager:
    use_in_migrations: bool = True

    def create_user(self, email: str, password: str) -> User:
        return User(email=email, full_name="")

    def create_superuser(self, email: str, password: str) -> User:
        return User(email=email, full_name="")


User.objects = UserManager()


class Borrowing:
    class Meta:
        constraints: list = []
        ordering: list = []

    def __init__(self, book: Book, user: User, borrow_date: date, expected_return_date: date, total_price: float, actual_return_date: Optional[date] = None) -> None:
        self.book = book
        self.user = user
        self.borrow_date = borrow_date
        self.expected_return_date = expected_return_date
        self.total_price = total_price
        self.actual_return_date = actual_return_date

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

    def __init__(self, borrowing: Borrowing, money_to_pay: float, session_id: str, session_url: str, status: str, type: str) -> None:
        self.borrowing = borrowing
        self.money_to_pay = money_to_pay
        self.session_id = session_id
        self.session_url = session_url
        self.status = status
        self.type = type