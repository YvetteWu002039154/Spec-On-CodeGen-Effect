import datetime
from typing import List, Tuple, Optional, Any

class Book:
    class Cover:
        HARD: str = "HARD"
        SOFT: str = "SOFT"

    class Meta:
        ordering: Tuple[str, ...] = ("title",)

    def __init__(self, author: str, cover: str, daily_fee: float, inventory: int, title: str):
        self.author = author
        self.cover = cover
        self.daily_fee = daily_fee
        self.inventory = inventory
        self.title = title


class UserManager:
    use_in_migrations: bool = True

    def create_user(self, email: str, password: str) -> 'User':
        return User(email=email, full_name="", username=None)

    def create_superuser(self, email: str, password: str) -> 'User':
        return self.create_user(email, password)


class User:
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = "email"
    objects: UserManager = UserManager()

    def __init__(self, email: str, full_name: str, username: type(None) = None):
        self.email = email
        self.full_name = full_name
        self.username = username


class Borrowing:
    class Meta:
        constraints: List[Any] = []
        ordering: List[str] = ["-borrow_date"]

    def __init__(
        self,
        book: Book,
        user: User,
        borrow_date: datetime.date,
        expected_return_date: datetime.date,
        total_price: float,
        actual_return_date: Optional[datetime.date] = None
    ):
        self.book = book
        self.user = user
        self.borrow_date = borrow_date
        self.expected_return_date = expected_return_date
        self.total_price = total_price
        self.actual_return_date = actual_return_date

    def clean(self) -> None:
        if self.expected_return_date and self.borrow_date:
            if self.expected_return_date < self.borrow_date:
                raise ValueError("Expected return date cannot be before borrow date.")

    def validate_borrowing(self, inventory: int) -> None:
        if inventory <= 0:
            raise ValueError("Cannot borrow a book with 0 inventory.")


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