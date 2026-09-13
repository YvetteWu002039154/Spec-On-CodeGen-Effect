from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import secrets
import threading
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple


class ValidationError(ValueError):
    pass


class AuthenticationError(PermissionError):
    pass


class AuthorizationError(PermissionError):
    pass


class NotFoundError(LookupError):
    pass


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _to_date(value: Any) -> dt.date:
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    raise ValidationError("Invalid date value")


def _to_datetime(value: Any) -> dt.datetime:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = dt.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    raise ValidationError("Invalid datetime value")


def _money(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        v = value
    elif isinstance(value, (int, float, str)):
        v = Decimal(str(value))
    else:
        raise ValidationError("Invalid money value")
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


class JWTService:
    def __init__(self, secret: str, issuer: str = "library-service-api", ttl_seconds: int = 3600) -> None:
        if not secret:
            raise ValidationError("JWT secret required")
        if ttl_seconds <= 0:
            raise ValidationError("TTL must be positive")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._ttl_seconds = ttl_seconds

    def issue(self, user_id: str, is_admin: bool) -> str:
        now = int(_utcnow().timestamp())
        payload = {
            "iss": self._issuer,
            "sub": user_id,
            "adm": bool(is_admin),
            "iat": now,
            "exp": now + self._ttl_seconds,
            "jti": str(uuid.uuid4()),
        }
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(sig)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify(self, token: str) -> Dict[str, Any]:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError as e:
            raise AuthenticationError("Invalid token format") from e

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise AuthenticationError("Invalid token signature")

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("iss") != self._issuer:
            raise AuthenticationError("Invalid token issuer")
        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise AuthenticationError("Invalid token expiry")
        if int(_utcnow().timestamp()) >= exp:
            raise AuthenticationError("Token expired")
        if "sub" not in payload:
            raise AuthenticationError("Invalid token subject")
        return payload


@dataclass(frozen=True)
class User:
    id: str
    username: str
    password_hash: str
    is_admin: bool = False
    created_at: dt.datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class Book:
    id: str
    title: str
    author: str
    total_copies: int
    available_copies: int
    created_at: dt.datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.total_copies < 0:
            raise ValidationError("total_copies must be non-negative")
        if self.available_copies < 0:
            raise ValidationError("available_copies must be non-negative")
        if self.available_copies > self.total_copies:
            raise ValidationError("available_copies cannot exceed total_copies")


@dataclass(frozen=True)
class Borrowing:
    id: str
    user_id: str
    book_id: str
    borrowed_at: dt.datetime
    due_date: dt.date
    actual_return_date: Optional[dt.date] = None
    created_at: dt.datetime = field(default_factory=_utcnow)

    @property
    def is_returned(self) -> bool:
        return self.actual_return_date is not None

    def overdue_days(self, on_date: Optional[dt.date] = None) -> int:
        if on_date is None:
            on_date = _utcnow().date()
        end_date = self.actual_return_date or on_date
        if end_date <= self.due_date:
            return 0
        return (end_date - self.due_date).days


@dataclass(frozen=True)
class Payment:
    id: str
    borrowing_id: str
    user_id: str
    amount: Decimal
    kind: str  # "BORROW" or "FINE"
    created_at: dt.datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0.00"):
            raise ValidationError("Payment amount must be positive")
        if self.kind not in ("BORROW", "FINE"):
            raise ValidationError("Invalid payment kind")


class PasswordHasher:
    def __init__(self, pepper: str = "") -> None:
        self._pepper = pepper.encode("utf-8")

    def hash(self, password: str) -> str:
        if not password:
            raise ValidationError("Password required")
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8") + self._pepper, salt, 120_000)
        return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(dk)}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            algo, salt_b64, dk_b64 = stored.split("$", 2)
        except ValueError:
            return False
        if algo != "pbkdf2_sha256":
            return False
        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(dk_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8") + self._pepper, salt, 120_000)
        return hmac.compare_digest(dk, expected)


class InMemoryDB:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.users: Dict[str, User] = {}
        self.users_by_username: Dict[str, str] = {}
        self.books: Dict[str, Book] = {}
        self.borrowings: Dict[str, Borrowing] = {}
        self.payments: Dict[str, Payment] = {}

    def lock(self) -> threading.RLock:
        return self._lock


class AuthService:
    def __init__(self, db: InMemoryDB, jwt: JWTService, hasher: PasswordHasher) -> None:
        self._db = db
        self._jwt = jwt
        self._hasher = hasher

    def register(self, username: str, password: str, is_admin: bool = False) -> User:
        username = (username or "").strip()
        if not username:
            raise ValidationError("Username required")
        with self._db.lock():
            if username in self._db.users_by_username:
                raise ValidationError("Username already exists")
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                username=username,
                password_hash=self._hasher.hash(password),
                is_admin=bool(is_admin),
            )
            self._db.users[user_id] = user
            self._db.users_by_username[username] = user_id
            return user

    def login(self, username: str, password: str) -> str:
        username = (username or "").strip()
        with self._db.lock():
            user_id = self._db.users_by_username.get(username)
            if not user_id:
                raise AuthenticationError("Invalid credentials")
            user = self._db.users[user_id]
            if not self._hasher.verify(password, user.password_hash):
                raise AuthenticationError("Invalid credentials")
            return self._jwt.issue(user.id, user.is_admin)

    def authenticate(self, token: str) -> User:
        payload = self._jwt.verify(token)
        user_id = payload["sub"]
        with self._db.lock():
            user = self._db.users.get(user_id)
            if not user:
                raise AuthenticationError("User not found")
            return user


class LibraryService:
    def __init__(
        self,
        db: InMemoryDB,
        borrow_fee: Decimal = Decimal("1.00"),
        fine_per_overdue_day: Decimal = Decimal("0.50"),
        default_borrow_days: int = 14,
    ) -> None:
        self._db = db
        self._borrow_fee = _money(borrow_fee)
        self._fine_per_overdue_day = _money(fine_per_overdue_day)
        if default_borrow_days <= 0:
            raise ValidationError("default_borrow_days must be positive")
        self._default_borrow_days = default_borrow_days

    def _require_admin(self, user: User) -> None:
        if not user.is_admin:
            raise AuthorizationError("Admin privileges required")

    def create_book(self, actor: User, title: str, author: str, total_copies: int) -> Book:
        self._require_admin(actor)
        title = (title or "").strip()
        author = (author or "").strip()
        if not title:
            raise ValidationError("Title required")
        if not author:
            raise ValidationError("Author required")
        if total_copies < 0:
            raise ValidationError("total_copies must be non-negative")
        with self._db.lock():
            book_id = str(uuid.uuid4())
            book = Book(
                id=book_id,
                title=title,
                author=author,
                total_copies=int(total_copies),
                available_copies=int(total_copies),
            )
            self._db.books[book_id] = book
            return book

    def update_book_copies(self, actor: User, book_id: str, total_copies: int) -> Book:
        self._require_admin(actor)
        if total_copies < 0:
            raise ValidationError("total_copies must be non-negative")
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            borrowed_count = book.total_copies - book.available_copies
            if total_copies < borrowed_count:
                raise ValidationError("total_copies cannot be less than currently borrowed copies")
            new_available = total_copies - borrowed_count
            updated = dataclasses.replace(book, total_copies=int(total_copies), available_copies=int(new_available))
            self._db.books[book_id] = updated
            return updated

    def list_books(self) -> List[Book]:
        with self._db.lock():
            return list(self._db.books.values())

    def get_book(self, book_id: str) -> Book:
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            return book

    def borrow_book(self, actor: User, book_id: str, due_date: Optional[Any] = None) -> Tuple[Borrowing, Payment]:
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            if book.available_copies <= 0:
                raise ValidationError("No available copies")

            borrowed_at = _utcnow()
            if due_date is None:
                due = (borrowed_at + dt.timedelta(days=self._default_borrow_days)).date()
            else:
                due = _to_date(due_date)
            if due < borrowed_at.date():
                raise ValidationError("due_date cannot be in the past")

            borrowing_id = str(uuid.uuid4())
            borrowing = Borrowing(
                id=borrowing_id,
                user_id=actor.id,
                book_id=book_id,
                borrowed_at=borrowed_at,
                due_date=due,
                actual_return_date=None,
            )
            self._db.borrowings[borrowing_id] = borrowing

            updated_book = dataclasses.replace(book, available_copies=book.available_copies - 1)
            self._db.books[book_id] = updated_book

            payment_id = str(uuid.uuid4())
            payment = Payment(
                id=payment_id,
                borrowing_id=borrowing_id,
                user_id=actor.id,
                amount=self._borrow_fee,
                kind="BORROW",
            )
            self._db.payments[payment_id] = payment
            return borrowing, payment

    def return_book(self, actor: User, borrowing_id: str, actual_return_date: Optional[Any] = None) -> Tuple[Borrowing, Optional[Payment]]:
        with self._db.lock():
            borrowing = self._db.borrowings.get(borrowing_id)
            if not borrowing:
                raise NotFoundError("Borrowing not found")
            if borrowing.user_id != actor.id and not actor.is_admin:
                raise AuthorizationError("Not allowed to return this borrowing")
            if borrowing.actual_return_date is not None:
                raise ValidationError("Borrowing already returned")

            ret_date = _to_date(actual_return_date) if actual_return_date is not None else _utcnow().date()
            if ret_date < borrowing.borrowed_at.date():
                raise ValidationError("actual_return_date cannot be before borrowed_at")

            updated_borrowing = dataclasses.replace(borrowing, actual_return_date=ret_date)
            self._db.borrowings[borrowing_id] = updated_borrowing

            book = self._db.books.get(borrowing.book_id)
            if not book:
                raise NotFoundError("Book not found")
            if book.available_copies >= book.total_copies:
                raise ValidationError("Book inventory inconsistency")
            self._db.books[book.id] = dataclasses.replace(book, available_copies=book.available_copies + 1)

            overdue_days = updated_borrowing.overdue_days()
            if overdue_days <= 0:
                return updated_borrowing, None

            fine_amount = _money(self._fine_per_overdue_day * Decimal(overdue_days))
            payment_id = str(uuid.uuid4())
            fine_payment = Payment(
                id=payment_id,
                borrowing_id=borrowing_id,
                user_id=updated_borrowing.user_id,
                amount=fine_amount,
                kind="FINE",
            )
            self._db.payments[payment_id] = fine_payment
            return updated_borrowing, fine_payment

    def list_borrowings(
        self,
        actor: User,
        actual_return_date: Optional[Any] = None,
        user_id: Optional[str] = None,
    ) -> List[Borrowing]:
        with self._db.lock():
            borrowings = list(self._db.borrowings.values())

            if not actor.is_admin:
                borrowings = [b for b in borrowings if b.user_id == actor.id]
            else:
                if user_id is not None:
                    borrowings = [b for b in borrowings if b.user_id == user_id]

            if actual_return_date is not None:
                ard = _to_date(actual_return_date)
                borrowings = [b for b in borrowings if b.actual_return_date == ard]

            borrowings.sort(key=lambda b: (b.borrowed_at, b.id))
            return borrowings

    def get_borrowing(self, actor: User, borrowing_id: str) -> Borrowing:
        with self._db.lock():
            borrowing = self._db.borrowings.get(borrowing_id)
            if not borrowing:
                raise NotFoundError("Borrowing not found")
            if borrowing.user_id != actor.id and not actor.is_admin:
                raise AuthorizationError("Not allowed to view this borrowing")
            return borrowing

    def list_payments(self, actor: User, user_id: Optional[str] = None, borrowing_id: Optional[str] = None) -> List[Payment]:
        with self._db.lock():
            payments = list(self._db.payments.values())
            if not actor.is_admin:
                payments = [p for p in payments if p.user_id == actor.id]
            else:
                if user_id is not None:
                    payments = [p for p in payments if p.user_id == user_id]
            if borrowing_id is not None:
                payments = [p for p in payments if p.borrowing_id == borrowing_id]
            payments.sort(key=lambda p: (p.created_at, p.id))
            return payments


class AdminPanel:
    def __init__(self, library: LibraryService) -> None:
        self._library = library

    @property
    def path(self) -> str:
        return "/admin/"

    def create_book(self, actor: User, title: str, author: str, total_copies: int) -> Book:
        return self._library.create_book(actor, title, author, total_copies)

    def update_book_copies(self, actor: User, book_id: str, total_copies: int) -> Book:
        return self._library.update_book_copies(actor, book_id, total_copies)


class SwaggerDocs:
    @property
    def path(self) -> str:
        return "/api/v1/doc/swagger/"

    def endpoints(self) -> List[Dict[str, Any]]:
        return [
            {"method": "POST", "path": "/api/v1/auth/register", "filters": []},
            {"method": "POST", "path": "/api/v1/auth/login", "filters": []},
            {"method": "GET", "path": "/api/v1/books", "filters": []},
            {"method": "POST", "path": "/api/v1/books", "filters": []},
            {"method": "PATCH", "path": "/api/v1/books/{book_id}/copies", "filters": []},
            {"method": "POST", "path": "/api/v1/borrowings", "filters": []},
            {"method": "POST", "path": "/api/v1/borrowings/{borrowing_id}/return", "filters": []},
            {"method": "GET", "path": "/api/v1/borrowings", "filters": ["actual_return_date", "users"]},
            {"method": "GET", "path": "/api/v1/payments", "filters": ["user_id", "borrowing_id"]},
        ]


class LibraryServiceAPI:
    def __init__(
        self,
        jwt_secret: str,
        jwt_ttl_seconds: int = 3600,
        borrow_fee: Decimal = Decimal("1.00"),
        fine_per_overdue_day: Decimal = Decimal("0.50"),
        default_borrow_days: int = 14,
        password_pepper: str = "",
    ) -> None:
        self.db = InMemoryDB()
        self.jwt = JWTService(secret=jwt_secret, ttl_seconds=jwt_ttl_seconds)
        self.hasher = PasswordHasher(pepper=password_pepper)
        self.auth = AuthService(self.db, self.jwt, self.hasher)
        self.library = LibraryService(
            self.db,
            borrow_fee=borrow_fee,
            fine_per_overdue_day=fine_per_overdue_day,
            default_borrow_days=default_borrow_days,
        )
        self.admin = AdminPanel(self.library)
        self.docs = SwaggerDocs()

    def swagger_path(self) -> str:
        return self.docs.path

    def admin_path(self) -> str:
        return self.admin.path

    def authenticate(self, token: str) -> User:
        return self.auth.authenticate(token)

    def register(self, username: str, password: str, is_admin: bool = False) -> User:
        return self.auth.register(username, password, is_admin=is_admin)

    def login(self, username: str, password: str) -> str:
        return self.auth.login(username, password)

    def create_book(self, token: str, title: str, author: str, total_copies: int) -> Book:
        actor = self.authenticate(token)
        return self.library.create_book(actor, title, author, total_copies)

    def list_books(self, token: str) -> List[Book]:
        _ = self.authenticate(token)
        return self.library.list_books()

    def borrow_book(self, token: str, book_id: str, due_date: Optional[Any] = None) -> Tuple[Borrowing, Payment]:
        actor = self.authenticate(token)
        return self.library.borrow_book(actor, book_id, due_date=due_date)

    def return_book(self, token: str, borrowing_id: str, actual_return_date: Optional[Any] = None) -> Tuple[Borrowing, Optional[Payment]]:
        actor = self.authenticate(token)
        return self.library.return_book(actor, borrowing_id, actual_return_date=actual_return_date)

    def list_borrowings(
        self,
        token: str,
        actual_return_date: Optional[Any] = None,
        users: Optional[str] = None,
    ) -> List[Borrowing]:
        actor = self.authenticate(token)
        return self.library.list_borrowings(actor, actual_return_date=actual_return_date, user_id=users)

    def list_payments(self, token: str, user_id: Optional[str] = None, borrowing_id: Optional[str] = None) -> List[Payment]:
        actor = self.authenticate(token)
        return self.library.list_payments(actor, user_id=user_id, borrowing_id=borrowing_id)