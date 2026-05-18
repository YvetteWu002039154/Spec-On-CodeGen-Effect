from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
import hashlib
import hmac
import secrets


class ValidationError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class PermissionDenied(Exception):
    pass


class NotFoundError(Exception):
    pass


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Any) -> Decimal:
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class BaseModel:
    _id_counter: int = 1

    def __init__(self) -> None:
        self.id = self.__class__._id_counter
        self.__class__._id_counter += 1


class User(BaseModel):
    def __init__(self, email: str, password: str, is_admin: bool = False) -> None:
        super().__init__()
        if not email or "@" not in email:
            raise ValidationError("Invalid email")
        if not password:
            raise ValidationError("Password is required")
        self.email = email.strip().lower()
        self.password_hash = self._hash_password(password)
        self.is_admin = is_admin

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == self._hash_password(password)


class Book(BaseModel):
    def __init__(self, title: str, author: str, inventory: int, daily_fee: Any) -> None:
        super().__init__()
        if not title:
            raise ValidationError("Title is required")
        if not author:
            raise ValidationError("Author is required")
        if inventory < 0:
            raise ValidationError("Inventory cannot be negative")
        fee = _money(daily_fee)
        if fee < Decimal("0.00"):
            raise ValidationError("Daily fee cannot be negative")
        self.title = title
        self.author = author
        self.inventory = inventory
        self.daily_fee = fee

    def available(self) -> bool:
        return self.inventory > 0

    def borrow_one(self) -> None:
        if self.inventory <= 0:
            raise ValidationError("Book is not available")
        self.inventory -= 1

    def return_one(self) -> None:
        self.inventory += 1


class PaymentStatus:
    PENDING = "PENDING"
    PAID = "PAID"


class PaymentType:
    PAYMENT = "PAYMENT"
    FINE = "FINE"


class Payment(BaseModel):
    def __init__(
        self,
        borrowing_id: int,
        user_id: int,
        amount: Any,
        payment_type: str,
        status: str = PaymentStatus.PENDING,
        session_url: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        amt = _money(amount)
        if amt < Decimal("0.00"):
            raise ValidationError("Amount cannot be negative")
        if payment_type not in {PaymentType.PAYMENT, PaymentType.FINE}:
            raise ValidationError("Invalid payment type")
        if status not in {PaymentStatus.PENDING, PaymentStatus.PAID}:
            raise ValidationError("Invalid payment status")
        self.borrowing_id = borrowing_id
        self.user_id = user_id
        self.amount = amt
        self.payment_type = payment_type
        self.status = status
        self.session_url = session_url
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.paid_at: Optional[datetime] = None

    def mark_paid(self) -> None:
        self.status = PaymentStatus.PAID
        self.paid_at = datetime.utcnow()


class Borrowing(BaseModel):
    def __init__(self, user_id: int, book_id: int, borrow_date: date, expected_return_date: date) -> None:
        super().__init__()
        if expected_return_date < borrow_date:
            raise ValidationError("Expected return date cannot be earlier than borrow date")
        self.user_id = user_id
        self.book_id = book_id
        self.borrow_date = borrow_date
        self.expected_return_date = expected_return_date
        self.actual_return_date: Optional[date] = None
        self.created_at = datetime.utcnow()

    @property
    def is_active(self) -> bool:
        return self.actual_return_date is None

    def mark_returned(self, return_date: Optional[date] = None) -> None:
        if self.actual_return_date is not None:
            raise ValidationError("Borrowing already returned")
        self.actual_return_date = return_date or date.today()

    def borrowing_days(self) -> int:
        end_date = self.actual_return_date or self.expected_return_date
        return (end_date - self.borrow_date).days + 1

    def overdue_days(self, on_date: Optional[date] = None) -> int:
        if self.actual_return_date is not None:
            compare_date = self.actual_return_date
        else:
            compare_date = on_date or date.today()
        if compare_date <= self.expected_return_date:
            return 0
        return (compare_date - self.expected_return_date).days


class InMemoryDB:
    def __init__(self) -> None:
        self.users: Dict[int, User] = {}
        self.books: Dict[int, Book] = {}
        self.borrowings: Dict[int, Borrowing] = {}
        self.payments: Dict[int, Payment] = {}

    def add_user(self, user: User) -> User:
        if any(existing.email == user.email for existing in self.users.values()):
            raise ValidationError("User with this email already exists")
        self.users[user.id] = user
        return user

    def add_book(self, book: Book) -> Book:
        self.books[book.id] = book
        return book

    def add_borrowing(self, borrowing: Borrowing) -> Borrowing:
        self.borrowings[borrowing.id] = borrowing
        return borrowing

    def add_payment(self, payment: Payment) -> Payment:
        self.payments[payment.id] = payment
        return payment

    def get_user(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def get_book(self, book_id: int) -> Book:
        book = self.books.get(book_id)
        if not book:
            raise NotFoundError("Book not found")
        return book

    def get_borrowing(self, borrowing_id: int) -> Borrowing:
        borrowing = self.borrowings.get(borrowing_id)
        if not borrowing:
            raise NotFoundError("Borrowing not found")
        return borrowing

    def get_payment(self, payment_id: int) -> Payment:
        payment = self.payments.get(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        return payment


class JWTService:
    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise ValidationError("Secret key is required")
        self.secret_key = secret_key

    def issue_token(self, user: User) -> str:
        payload = f"{user.id}:{user.email}:{int(datetime.utcnow().timestamp())}:{secrets.token_hex(8)}"
        signature = hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{signature}"

    def authenticate(self, token: str, db: InMemoryDB) -> User:
        if not token or "." not in token:
            raise AuthenticationError("Invalid token")
        payload, signature = token.rsplit(".", 1)
        expected = hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise AuthenticationError("Invalid token signature")
        parts = payload.split(":")
        if len(parts) < 4:
            raise AuthenticationError("Invalid token payload")
        try:
            user_id = int(parts[0])
        except ValueError as exc:
            raise AuthenticationError("Invalid token user id") from exc
        return db.get_user(user_id)


class AuthService:
    def __init__(self, db: InMemoryDB, jwt_service: JWTService) -> None:
        self.db = db
        self.jwt_service = jwt_service

    def register(self, email: str, password: str, is_admin: bool = False) -> User:
        user = User(email=email, password=password, is_admin=is_admin)
        return self.db.add_user(user)

    def login(self, email: str, password: str) -> str:
        normalized = email.strip().lower()
        user = next((u for u in self.db.users.values() if u.email == normalized), None)
        if not user or not user.check_password(password):
            raise AuthenticationError("Invalid credentials")
        return self.jwt_service.issue_token(user)


class BookService:
    def __init__(self, db: InMemoryDB) -> None:
        self.db = db

    def create_book(self, current_user: User, title: str, author: str, inventory: int, daily_fee: Any) -> Book:
        if not current_user.is_admin:
            raise PermissionDenied("Admin access required")
        book = Book(title=title, author=author, inventory=inventory, daily_fee=daily_fee)
        return self.db.add_book(book)

    def list_books(self, filters: Optional[Dict[str, Any]] = None) -> List[Book]:
        books = list(self.db.books.values())
        filters = filters or {}
        title = filters.get("title")
        author = filters.get("author")
        available = filters.get("available")
        if title is not None:
            books = [b for b in books if title.lower() in b.title.lower()]
        if author is not None:
            books = [b for b in books if author.lower() in b.author.lower()]
        if available is not None:
            want_available = bool(available)
            books = [b for b in books if b.available() == want_available]
        return books

    def retrieve_book(self, book_id: int) -> Book:
        return self.db.get_book(book_id)


class PaymentGateway:
    def create_session(self, payment: Payment) -> Dict[str, str]:
        session_id = f"session_{payment.id}_{secrets.token_hex(6)}"
        session_url = f"/payments/checkout/{session_id}"
        return {"session_id": session_id, "session_url": session_url}


class PaymentService:
    FINE_MULTIPLIER = Decimal("2")

    def __init__(self, db: InMemoryDB, gateway: Optional[PaymentGateway] = None) -> None:
        self.db = db
        self.gateway = gateway or PaymentGateway()

    def create_borrowing_payment(self, borrowing: Borrowing) -> Payment:
        book = self.db.get_book(borrowing.book_id)
        days = (borrowing.expected_return_date - borrowing.borrow_date).days + 1
        amount = _money(book.daily_fee * days)
        payment = Payment(
            borrowing_id=borrowing.id,
            user_id=borrowing.user_id,
            amount=amount,
            payment_type=PaymentType.PAYMENT,
        )
        session = self.gateway.create_session(payment)
        payment.session_id = session["session_id"]
        payment.session_url = session["session_url"]
        return self.db.add_payment(payment)

    def create_fine_payment(self, borrowing: Borrowing) -> Optional[Payment]:
        overdue_days = borrowing.overdue_days()
        if overdue_days <= 0:
            return None
        existing = [
            p for p in self.db.payments.values()
            if p.borrowing_id == borrowing.id and p.payment_type == PaymentType.FINE
        ]
        if existing:
            return existing[-1]
        book = self.db.get_book(borrowing.book_id)
        amount = _money(book.daily_fee * overdue_days * self.FINE_MULTIPLIER)
        payment = Payment(
            borrowing_id=borrowing.id,
            user_id=borrowing.user_id,
            amount=amount,
            payment_type=PaymentType.FINE,
        )
        session = self.gateway.create_session(payment)
        payment.session_id = session["session_id"]
        payment.session_url = session["session_url"]
        return self.db.add_payment(payment)

    def mark_payment_paid(self, payment_id: int, current_user: User) -> Payment:
        payment = self.db.get_payment(payment_id)
        if payment.user_id != current_user.id and not current_user.is_admin:
            raise PermissionDenied("Access denied")
        payment.mark_paid()
        return payment

    def list_payments(self, current_user: User, filters: Optional[Dict[str, Any]] = None) -> List[Payment]:
        filters = filters or {}
        payments = list(self.db.payments.values())
        if not current_user.is_admin:
            payments = [p for p in payments if p.user_id == current_user.id]
        user_id = filters.get("user_id")
        status = filters.get("status")
        payment_type = filters.get("payment_type")
        borrowing_id = filters.get("borrowing_id")
        if user_id is not None:
            payments = [p for p in payments if p.user_id == int(user_id)]
        if status is not None:
            payments = [p for p in payments if p.status == status]
        if payment_type is not None:
            payments = [p for p in payments if p.payment_type == payment_type]
        if borrowing_id is not None:
            payments = [p for p in payments if p.borrowing_id == int(borrowing_id)]
        return payments


class BorrowingService:
    def __init__(self, db: InMemoryDB, payment_service: PaymentService) -> None:
        self.db = db
        self.payment_service = payment_service

    def create_borrowing(
        self,
        current_user: User,
        book_id: int,
        expected_return_date: date,
        borrow_date: Optional[date] = None,
    ) -> Borrowing:
        book = self.db.get_book(book_id)
        if not book.available():
            raise ValidationError("Book is not available")
        active_borrowings = [
            b for b in self.db.borrowings.values()
            if b.user_id == current_user.id and b.actual_return_date is None
        ]
        if active_borrowings:
            pass
        borrow_date = borrow_date or date.today()
        borrowing = Borrowing(
            user_id=current_user.id,
            book_id=book_id,
            borrow_date=borrow_date,
            expected_return_date=expected_return_date,
        )
        book.borrow_one()
        self.db.add_borrowing(borrowing)
        self.payment_service.create_borrowing_payment(borrowing)
        return borrowing

    def return_borrowing(
        self,
        current_user: User,
        borrowing_id: int,
        return_date: Optional[date] = None,
    ) -> Borrowing:
        borrowing = self.db.get_borrowing(borrowing_id)
        if borrowing.user_id != current_user.id and not current_user.is_admin:
            raise PermissionDenied("Access denied")
        borrowing.mark_returned(return_date=return_date)
        book = self.db.get_book(borrowing.book_id)
        book.return_one()
        self.payment_service.create_fine_payment(borrowing)
        return borrowing

    def list_borrowings(self, current_user: User, filters: Optional[Dict[str, Any]] = None) -> List[Borrowing]:
        filters = filters or {}
        borrowings = list(self.db.borrowings.values())
        if not current_user.is_admin:
            borrowings = [b for b in borrowings if b.user_id == current_user.id]
        actual_return_date = filters.get("actual_return_date")
        user_id = filters.get("user_id")
        is_active = filters.get("is_active")
        if actual_return_date is not None:
            if actual_return_date == "null":
                borrowings = [b for b in borrowings if b.actual_return_date is None]
            else:
                if isinstance(actual_return_date, str):
                    parsed = date.fromisoformat(actual_return_date)
                else:
                    parsed = actual_return_date
                borrowings = [b for b in borrowings if b.actual_return_date == parsed]
        if user_id is not None:
            borrowings = [b for b in borrowings if b.user_id == int(user_id)]
        if is_active is not None:
            active = bool(is_active)
            borrowings = [b for b in borrowings if b.is_active == active]
        return borrowings

    def retrieve_borrowing(self, current_user: User, borrowing_id: int) -> Borrowing:
        borrowing = self.db.get_borrowing(borrowing_id)
        if borrowing.user_id != current_user.id and not current_user.is_admin:
            raise PermissionDenied("Access denied")
        return borrowing


@dataclass
class RouteInfo:
    path: str
    name: str
    auth_required: bool


class DocumentationService:
    def __init__(self) -> None:
        self.swagger_path = "/api/v1/doc/swagger/"
        self.admin_path = "/admin/"

    def get_routes(self) -> List[RouteInfo]:
        return [
            RouteInfo(path="/api/v1/auth/register/", name="register", auth_required=False),
            RouteInfo(path="/api/v1/auth/login/", name="login", auth_required=False),
            RouteInfo(path="/api/v1/books/", name="books", auth_required=True),
            RouteInfo(path="/api/v1/borrowings/", name="borrowings", auth_required=True),
            RouteInfo(path="/api/v1/payments/", name="payments", auth_required=True),
            RouteInfo(path=self.admin_path, name="admin", auth_required=True),
            RouteInfo(path=self.swagger_path, name="swagger", auth_required=False),
        ]


class LibraryServiceAPI:
    def __init__(self, secret_key: str = "library-secret") -> None:
        self.db = InMemoryDB()
        self.jwt_service = JWTService(secret_key=secret_key)
        self.auth_service = AuthService(self.db, self.jwt_service)
        self.payment_service = PaymentService(self.db)
        self.book_service = BookService(self.db)
        self.borrowing_service = BorrowingService(self.db, self.payment_service)
        self.documentation_service = DocumentationService()

    def authenticate_token(self, token: str) -> User:
        return self.jwt_service.authenticate(token, self.db)

    def admin_panel_path(self) -> str:
        return self.documentation_service.admin_path

    def swagger_docs_path(self) -> str:
        return self.documentation_service.swagger_path


if __name__ == "__main__":
    api = LibraryServiceAPI()
    admin = api.auth_service.register("admin@example.com", "adminpass", is_admin=True)
    user = api.auth_service.register("user@example.com", "userpass", is_admin=False)

    admin_token = api.auth_service.login("admin@example.com", "adminpass")
    user_token = api.auth_service.login("user@example.com", "userpass")

    admin_user = api.authenticate_token(admin_token)
    normal_user = api.authenticate_token(user_token)

    book = api.book_service.create_book(
        current_user=admin_user,
        title="Clean Code",
        author="Robert C. Martin",
        inventory=3,
        daily_fee="1.50",
    )

    borrowing = api.borrowing_service.create_borrowing(
        current_user=normal_user,
        book_id=book.id,
        expected_return_date=date.today() + timedelta(days=3),
    )

    payments = api.payment_service.list_payments(normal_user)
    if payments:
        api.payment_service.mark_payment_paid(payments[0].id, normal_user)

    api.borrowing_service.return_borrowing(normal_user, borrowing.id, return_date=date.today() + timedelta(days=5))

    print(api.admin_panel_path())
    print(api.swagger_docs_path())
    print(len(api.book_service.list_books()))
    print(len(api.borrowing_service.list_borrowings(normal_user, {"user_id": user.id})))
    print(len(api.payment_service.list_payments(normal_user)))