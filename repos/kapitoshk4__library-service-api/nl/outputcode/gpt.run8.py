from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import base64
import hashlib
import hmac
import json
import secrets
import threading
import uuid


class DomainError(Exception):
    pass


class AuthenticationError(DomainError):
    pass


class AuthorizationError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        try:
            return Decimal(str(value))
        except Exception as e:
            raise ValidationError("Invalid decimal value") from e
    raise ValidationError("Invalid decimal value")


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
            raise ValidationError("ttl_seconds must be positive")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._ttl_seconds = ttl_seconds

    def issue(self, subject: str, claims: Optional[Dict[str, Any]] = None) -> str:
        if not subject:
            raise ValidationError("subject required")
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(_utcnow().timestamp())
        payload: Dict[str, Any] = {
            "iss": self._issuer,
            "sub": subject,
            "iat": now,
            "exp": now + self._ttl_seconds,
        }
        if claims:
            for k, v in claims.items():
                if k in payload:
                    raise ValidationError(f"Reserved claim: {k}")
                payload[k] = v

        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(sig)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify(self, token: str) -> Dict[str, Any]:
        if not token:
            raise AuthenticationError("Missing token")
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        try:
            provided_sig = _b64url_decode(sig_b64)
        except Exception as e:
            raise AuthenticationError("Invalid signature encoding") from e
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise AuthenticationError("Invalid token signature")
        try:
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except Exception as e:
            raise AuthenticationError("Invalid token payload") from e
        if payload.get("iss") != self._issuer:
            raise AuthenticationError("Invalid issuer")
        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise AuthenticationError("Invalid exp")
        if int(_utcnow().timestamp()) >= exp:
            raise AuthenticationError("Token expired")
        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise AuthenticationError("Invalid subject")
        return payload


class PasswordHasher:
    def hash_password(self, password: str) -> str:
        if not isinstance(password, str) or len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(dk)}"

    def verify_password(self, password: str, stored: str) -> bool:
        try:
            algo, salt_b64, dk_b64 = stored.split("$", 2)
            if algo != "pbkdf2_sha256":
                return False
            salt = _b64url_decode(salt_b64)
            expected = _b64url_decode(dk_b64)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False


@dataclass(frozen=True)
class User:
    id: str
    username: str
    password_hash: str
    is_admin: bool


@dataclass(frozen=True)
class Book:
    id: str
    title: str
    author: str
    total_copies: int
    available_copies: int


@dataclass(frozen=True)
class Borrowing:
    id: str
    user_id: str
    book_id: str
    borrowed_at: datetime
    due_at: datetime
    actual_return_at: Optional[datetime]


@dataclass(frozen=True)
class Payment:
    id: str
    borrowing_id: str
    user_id: str
    amount: Decimal
    kind: str  # "BORROW" or "FINE"
    created_at: datetime


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

    def register_user(self, username: str, password: str, is_admin: bool = False) -> User:
        if not isinstance(username, str) or not username.strip():
            raise ValidationError("username required")
        username = username.strip()
        with self._db.lock():
            if username in self._db.users_by_username:
                raise ConflictError("username already exists")
            user_id = str(uuid.uuid4())
            pw_hash = self._hasher.hash_password(password)
            user = User(id=user_id, username=username, password_hash=pw_hash, is_admin=bool(is_admin))
            self._db.users[user_id] = user
            self._db.users_by_username[username] = user_id
            return user

    def login(self, username: str, password: str) -> str:
        if not isinstance(username, str) or not username.strip():
            raise ValidationError("username required")
        username = username.strip()
        with self._db.lock():
            uid = self._db.users_by_username.get(username)
            if not uid:
                raise AuthenticationError("Invalid credentials")
            user = self._db.users[uid]
            if not self._hasher.verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid credentials")
            token = self._jwt.issue(subject=user.id, claims={"username": user.username, "is_admin": user.is_admin})
            return token

    def authenticate(self, token: str) -> User:
        payload = self._jwt.verify(token)
        user_id = payload["sub"]
        with self._db.lock():
            user = self._db.users.get(user_id)
            if not user:
                raise AuthenticationError("User not found")
            return user


class AdminService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def _require_admin(self, actor: User) -> None:
        if not actor.is_admin:
            raise AuthorizationError("Admin privileges required")

    def create_book(self, actor: User, title: str, author: str, total_copies: int) -> Book:
        self._require_admin(actor)
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("title required")
        if not isinstance(author, str) or not author.strip():
            raise ValidationError("author required")
        if not isinstance(total_copies, int) or total_copies <= 0:
            raise ValidationError("total_copies must be positive integer")
        with self._db.lock():
            book_id = str(uuid.uuid4())
            book = Book(
                id=book_id,
                title=title.strip(),
                author=author.strip(),
                total_copies=total_copies,
                available_copies=total_copies,
            )
            self._db.books[book_id] = book
            return book

    def update_book_copies(self, actor: User, book_id: str, total_copies: int) -> Book:
        self._require_admin(actor)
        if not isinstance(total_copies, int) or total_copies <= 0:
            raise ValidationError("total_copies must be positive integer")
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            borrowed = book.total_copies - book.available_copies
            if total_copies < borrowed:
                raise ValidationError("total_copies cannot be less than currently borrowed copies")
            new_available = total_copies - borrowed
            updated = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=total_copies,
                available_copies=new_available,
            )
            self._db.books[book_id] = updated
            return updated

    def list_users(self, actor: User) -> List[User]:
        self._require_admin(actor)
        with self._db.lock():
            return list(self._db.users.values())

    def list_books(self, actor: User) -> List[Book]:
        self._require_admin(actor)
        with self._db.lock():
            return list(self._db.books.values())

    def list_payments(self, actor: User) -> List[Payment]:
        self._require_admin(actor)
        with self._db.lock():
            return list(self._db.payments.values())


class LibraryService:
    def __init__(
        self,
        db: InMemoryDB,
        borrow_fee: Decimal,
        fine_per_day: Decimal,
        borrowing_days: int = 14,
    ) -> None:
        self._db = db
        self._borrow_fee = _to_decimal(borrow_fee)
        self._fine_per_day = _to_decimal(fine_per_day)
        if self._borrow_fee < 0:
            raise ValidationError("borrow_fee must be non-negative")
        if self._fine_per_day < 0:
            raise ValidationError("fine_per_day must be non-negative")
        if not isinstance(borrowing_days, int) or borrowing_days <= 0:
            raise ValidationError("borrowing_days must be positive integer")
        self._borrowing_days = borrowing_days

    def list_books(self) -> List[Book]:
        with self._db.lock():
            return list(self._db.books.values())

    def get_book(self, book_id: str) -> Book:
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            return book

    def borrow_book(self, user: User, book_id: str) -> Tuple[Borrowing, Payment]:
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            if book.available_copies <= 0:
                raise ConflictError("No copies available")

            now = _utcnow()
            due = now + timedelta(days=self._borrowing_days)

            borrowing_id = str(uuid.uuid4())
            borrowing = Borrowing(
                id=borrowing_id,
                user_id=user.id,
                book_id=book.id,
                borrowed_at=now,
                due_at=due,
                actual_return_at=None,
            )
            self._db.borrowings[borrowing_id] = borrowing

            updated_book = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=book.total_copies,
                available_copies=book.available_copies - 1,
            )
            self._db.books[book.id] = updated_book

            payment_id = str(uuid.uuid4())
            payment = Payment(
                id=payment_id,
                borrowing_id=borrowing.id,
                user_id=user.id,
                amount=self._borrow_fee,
                kind="BORROW",
                created_at=now,
            )
            self._db.payments[payment_id] = payment
            return borrowing, payment

    def return_book(self, user: User, borrowing_id: str) -> Tuple[Borrowing, Optional[Payment]]:
        with self._db.lock():
            borrowing = self._db.borrowings.get(borrowing_id)
            if not borrowing:
                raise NotFoundError("Borrowing not found")
            if borrowing.user_id != user.id and not user.is_admin:
                raise AuthorizationError("Not allowed")
            if borrowing.actual_return_at is not None:
                raise ConflictError("Borrowing already returned")

            book = self._db.books.get(borrowing.book_id)
            if not book:
                raise NotFoundError("Book not found")

            now = _utcnow()
            updated_borrowing = Borrowing(
                id=borrowing.id,
                user_id=borrowing.user_id,
                book_id=borrowing.book_id,
                borrowed_at=borrowing.borrowed_at,
                due_at=borrowing.due_at,
                actual_return_at=now,
            )
            self._db.borrowings[borrowing.id] = updated_borrowing

            updated_book = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=book.total_copies,
                available_copies=book.available_copies + 1,
            )
            self._db.books[book.id] = updated_book

            fine_payment: Optional[Payment] = None
            overdue_days = self._calculate_overdue_days(updated_borrowing)
            if overdue_days > 0 and self._fine_per_day > 0:
                amount = (self._fine_per_day * Decimal(overdue_days)).quantize(Decimal("0.01"))
                payment_id = str(uuid.uuid4())
                fine_payment = Payment(
                    id=payment_id,
                    borrowing_id=updated_borrowing.id,
                    user_id=updated_borrowing.user_id,
                    amount=amount,
                    kind="FINE",
                    created_at=now,
                )
                self._db.payments[payment_id] = fine_payment

            return updated_borrowing, fine_payment

    def _calculate_overdue_days(self, borrowing: Borrowing) -> int:
        if borrowing.actual_return_at is None:
            ref = _utcnow()
        else:
            ref = borrowing.actual_return_at
        if ref <= borrowing.due_at:
            return 0
        delta = ref - borrowing.due_at
        days = delta.days
        if delta.seconds > 0 or delta.microseconds > 0:
            days += 1
        return max(0, days)

    def list_borrowings(
        self,
        actor: User,
        actual_return_date: Optional[datetime] = None,
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
            if actual_return_date.tzinfo is None:
                raise ValidationError("actual_return_date must be timezone-aware")
            target_date = actual_return_date.astimezone(timezone.utc).date()
            borrowings = [
                b
                for b in borrowings
                if b.actual_return_at is not None and b.actual_return_at.astimezone(timezone.utc).date() == target_date
            ]

        borrowings.sort(key=lambda b: b.borrowed_at, reverse=True)
        return borrowings

    def list_payments(self, actor: User) -> List[Payment]:
        with self._db.lock():
            payments = list(self._db.payments.values())
        if actor.is_admin:
            payments.sort(key=lambda p: p.created_at, reverse=True)
            return payments
        user_payments = [p for p in payments if p.user_id == actor.id]
        user_payments.sort(key=lambda p: p.created_at, reverse=True)
        return user_payments


class Router:
    def __init__(self) -> None:
        self._routes: Dict[Tuple[str, str], Any] = {}

    def add(self, method: str, path: str, handler: Any) -> None:
        key = (method.upper(), path)
        if key in self._routes:
            raise ConflictError("Route already registered")
        self._routes[key] = handler

    def dispatch(self, method: str, path: str, request: Dict[str, Any]) -> Dict[str, Any]:
        key = (method.upper(), path)
        handler = self._routes.get(key)
        if not handler:
            raise NotFoundError("Endpoint not found")
        return handler(request)


class LibraryServiceAPI:
    def __init__(
        self,
        jwt_secret: str,
        borrow_fee: Decimal = Decimal("2.00"),
        fine_per_day: Decimal = Decimal("1.00"),
        borrowing_days: int = 14,
    ) -> None:
        self.db = InMemoryDB()
        self.jwt = JWTService(secret=jwt_secret)
        self.hasher = PasswordHasher()
        self.auth = AuthService(self.db, self.jwt, self.hasher)
        self.admin = AdminService(self.db)
        self.library = LibraryService(self.db, borrow_fee=borrow_fee, fine_per_day=fine_per_day, borrowing_days=borrowing_days)
        self.router = Router()
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add("GET", "/api/v1/doc/swagger/", self._swagger)
        self.router.add("GET", "/admin/", self._admin_panel)

        self.router.add("POST", "/api/v1/auth/register", self._register)
        self.router.add("POST", "/api/v1/auth/login", self._login)

        self.router.add("GET", "/api/v1/books", self._list_books)
        self.router.add("POST", "/api/v1/books", self._create_book_admin)

        self.router.add("POST", "/api/v1/borrowings", self._borrow_book)
        self.router.add("POST", "/api/v1/borrowings/return", self._return_book)
        self.router.add("GET", "/api/v1/borrowings", self._list_borrowings)

        self.router.add("GET", "/api/v1/payments", self._list_payments)

    def handle(self, method: str, path: str, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if request is None:
            request = {}
        return self.router.dispatch(method, path, request)

    def _get_actor(self, request: Dict[str, Any], required: bool = True) -> Optional[User]:
        token = request.get("token")
        if not token:
            if required:
                raise AuthenticationError("Missing token")
            return None
        return self.auth.authenticate(token)

    def _swagger(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "service": "library-service-api",
            "docs": "/api/v1/doc/swagger/",
            "admin": "/admin/",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/auth/register"},
                {"method": "POST", "path": "/api/v1/auth/login"},
                {"method": "GET", "path": "/api/v1/books"},
                {"method": "POST", "path": "/api/v1/books", "auth": "admin"},
                {"method": "POST", "path": "/api/v1/borrowings", "auth": "jwt"},
                {"method": "POST", "path": "/api/v1/borrowings/return", "auth": "jwt"},
                {
                    "method": "GET",
                    "path": "/api/v1/borrowings",
                    "auth": "jwt",
                    "filters": ["actual_return_date", "user_id (admin only)"],
                },
                {"method": "GET", "path": "/api/v1/payments", "auth": "jwt"},
            ],
        }

    def _admin_panel(self, request: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._get_actor(request, required=True)
        if not actor.is_admin:
            raise AuthorizationError("Admin privileges required")
        return {
            "admin": True,
            "users_count": len(self.db.users),
            "books_count": len(self.db.books),
            "borrowings_count": len(self.db.borrowings),
            "payments_count": len(self.db.payments),
        }

    def _register(self, request: Dict[str, Any]) -> Dict[str, Any]:
        username = request.get("username")
        password = request.get("password")
        is_admin = bool(request.get("is_admin", False))
        user = self.auth.register_user(username=username, password=password, is_admin=is_admin)
        return {"id": user.id, "username": user.username, "is_admin": user.is_admin}

    def _login(self, request: Dict[str, Any]) -> Dict[str, Any]:
        username = request.get("username")
        password = request.get("password")
        token = self.auth.login(username=username, password=password)
        return {"token": token}

    def _list_books(self, request: Dict[str, Any]) -> Dict[str, Any]:
        books = self.library.list_books()
        return {"results": [self._serialize_book(b) for b in books]}

    def _create_book_admin(self, request: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._get_actor(request, required=True)
        book = self.admin.create_book(
            actor=actor,
            title=request.get("title"),
            author=request.get("author"),
            total_copies=request.get("total_copies"),
        )
        return self._serialize_book(book)

    def _borrow_book(self, request: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._get_actor(request, required=True)
        borrowing, payment = self.library.borrow_book(user=actor, book_id=request.get("book_id"))
        return {"borrowing": self._serialize_borrowing(borrowing), "payment": self._serialize_payment(payment)}

    def _return_book(self, request: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._get_actor(request, required=True)
        borrowing_id = request.get("borrowing_id")
        borrowing, fine_payment = self.library.return_book(user=actor, borrowing_id=borrowing_id)
        return {
            "borrowing": self._serialize_borrowing(borrowing),
            "fine_payment": self._serialize_payment(fine_payment) if fine_payment else None,
        }

    def _list_borrowings(self, request: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._get_actor(request, required=True)
        actual_return_date = request.get("actual_return_date")
        if actual_return_date is not None:
            if isinstance(actual_return_date, str):
                try:
                    actual_return_date = datetime.fromisoformat(actual_return_date)
                except Exception as e:
                    raise ValidationError("actual_return_date must be ISO datetime") from e
            if not isinstance(actual_return_date, datetime):
                raise ValidationError("actual_return_date must be datetime or ISO string")
            if actual_return_date.tzinfo is None:
                raise ValidationError("actual_return_date must be timezone-aware")
        user_id = request.get("user_id")
        borrowings = self.library.list_borrowings(actor=actor, actual_return_date=actual_return_date, user_id=user_id)
        return {"results": [self._serialize_borrowing(b) for b in borrowings]}

    def _list_payments(self, request: Dict[str, Any]) -> Dict[str, Any]:
        actor = self._get_actor(request, required=True)
        payments = self.library.list_payments(actor=actor)
        return {"results": [self._serialize_payment(p) for p in payments]}

    def _serialize_book(self, b: Book) -> Dict[str, Any]:
        return {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "total_copies": b.total_copies,
            "available_copies": b.available_copies,
        }

    def _serialize_borrowing(self, b: Borrowing) -> Dict[str, Any]:
        return {
            "id": b.id,
            "user_id": b.user_id,
            "book_id": b.book_id,
            "borrowed_at": b.borrowed_at.isoformat(),
            "due_at": b.due_at.isoformat(),
            "actual_return_at": b.actual_return_at.isoformat() if b.actual_return_at else None,
        }

    def _serialize_payment(self, p: Payment) -> Dict[str, Any]:
        return {
            "id": p.id,
            "borrowing_id": p.borrowing_id,
            "user_id": p.user_id,
            "amount": str(p.amount),
            "kind": p.kind,
            "created_at": p.created_at.isoformat(),
        }


__all__ = [
    "LibraryServiceAPI",
    "DomainError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "User",
    "Book",
    "Borrowing",
    "Payment",
]