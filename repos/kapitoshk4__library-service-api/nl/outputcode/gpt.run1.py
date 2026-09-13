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
    raise ValidationError("Invalid decimal value type")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


class JWTService:
    def __init__(self, secret: str, issuer: str = "library-service-api") -> None:
        if not secret:
            raise ValidationError("JWT secret is required")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer

    def issue_token(self, user_id: str, is_admin: bool, expires_in_seconds: int = 3600) -> str:
        if not user_id:
            raise ValidationError("user_id is required")
        if expires_in_seconds <= 0:
            raise ValidationError("expires_in_seconds must be positive")

        header = {"alg": "HS256", "typ": "JWT"}
        now = int(_utcnow().timestamp())
        payload = {
            "iss": self._issuer,
            "sub": user_id,
            "adm": bool(is_admin),
            "iat": now,
            "exp": now + int(expires_in_seconds),
            "jti": str(uuid.uuid4()),
        }

        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(sig)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        if not token:
            raise AuthenticationError("Missing token")
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format")

        header_b64, payload_b64, sig_b64 = parts
        try:
            signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
            expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
            provided_sig = _b64url_decode(sig_b64)
            if not hmac.compare_digest(expected_sig, provided_sig):
                raise AuthenticationError("Invalid token signature")

            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError("Invalid token") from e

        if payload.get("iss") != self._issuer:
            raise AuthenticationError("Invalid token issuer")

        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise AuthenticationError("Invalid token expiration")
        if int(_utcnow().timestamp()) >= exp:
            raise AuthenticationError("Token expired")

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise AuthenticationError("Invalid token subject")

        return payload


class PasswordHasher:
    def hash_password(self, password: str) -> str:
        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(dk)}"

    def verify_password(self, password: str, stored: str) -> bool:
        try:
            algo, salt_b64, dk_b64 = stored.split("$", 2)
            if algo != "pbkdf2_sha256":
                return False
            salt = _b64url_decode(salt_b64)
            expected = _b64url_decode(dk_b64)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
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

    def register(self, username: str, password: str, is_admin: bool = False) -> User:
        username = (username or "").strip()
        if not username:
            raise ValidationError("Username is required")

        with self._db.lock():
            if username in self._db.users_by_username:
                raise ConflictError("Username already exists")
            user_id = str(uuid.uuid4())
            pw_hash = self._hasher.hash_password(password)
            user = User(id=user_id, username=username, password_hash=pw_hash, is_admin=bool(is_admin))
            self._db.users[user_id] = user
            self._db.users_by_username[username] = user_id
            return user

    def login(self, username: str, password: str, expires_in_seconds: int = 3600) -> str:
        username = (username or "").strip()
        if not username or not password:
            raise ValidationError("Username and password are required")

        with self._db.lock():
            user_id = self._db.users_by_username.get(username)
            if not user_id:
                raise AuthenticationError("Invalid credentials")
            user = self._db.users[user_id]
            if not self._hasher.verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid credentials")
            return self._jwt.issue_token(user_id=user.id, is_admin=user.is_admin, expires_in_seconds=expires_in_seconds)

    def authenticate(self, token: str) -> User:
        payload = self._jwt.verify_token(token)
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
        title = (title or "").strip()
        author = (author or "").strip()
        if not title:
            raise ValidationError("Title is required")
        if not author:
            raise ValidationError("Author is required")
        if not isinstance(total_copies, int) or total_copies <= 0:
            raise ValidationError("total_copies must be a positive integer")

        with self._db.lock():
            book_id = str(uuid.uuid4())
            book = Book(
                id=book_id,
                title=title,
                author=author,
                total_copies=total_copies,
                available_copies=total_copies,
            )
            self._db.books[book_id] = book
            return book

    def update_book_copies(self, actor: User, book_id: str, total_copies: int) -> Book:
        self._require_admin(actor)
        if not isinstance(total_copies, int) or total_copies <= 0:
            raise ValidationError("total_copies must be a positive integer")

        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")

            borrowed_count = book.total_copies - book.available_copies
            if total_copies < borrowed_count:
                raise ValidationError("total_copies cannot be less than currently borrowed copies")

            available = total_copies - borrowed_count
            updated = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=total_copies,
                available_copies=available,
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


class LibraryService:
    def __init__(
        self,
        db: InMemoryDB,
        borrow_fee: Decimal = Decimal("5.00"),
        fine_per_day: Decimal = Decimal("1.00"),
        default_borrow_days: int = 14,
    ) -> None:
        self._db = db
        self._borrow_fee = _to_decimal(borrow_fee)
        self._fine_per_day = _to_decimal(fine_per_day)
        if self._borrow_fee < 0 or self._fine_per_day < 0:
            raise ValidationError("Fees must be non-negative")
        if not isinstance(default_borrow_days, int) or default_borrow_days <= 0:
            raise ValidationError("default_borrow_days must be a positive integer")
        self._default_borrow_days = default_borrow_days

    def list_books(self) -> List[Book]:
        with self._db.lock():
            return list(self._db.books.values())

    def get_book(self, book_id: str) -> Book:
        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            return book

    def borrow_book(self, actor: User, book_id: str, borrow_days: Optional[int] = None) -> Tuple[Borrowing, Payment]:
        if borrow_days is None:
            borrow_days = self._default_borrow_days
        if not isinstance(borrow_days, int) or borrow_days <= 0:
            raise ValidationError("borrow_days must be a positive integer")

        with self._db.lock():
            book = self._db.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            if book.available_copies <= 0:
                raise ConflictError("No available copies")

            now = _utcnow()
            due = now + timedelta(days=borrow_days)

            borrowing_id = str(uuid.uuid4())
            borrowing = Borrowing(
                id=borrowing_id,
                user_id=actor.id,
                book_id=book.id,
                borrowed_at=now,
                due_at=due,
                actual_return_at=None,
            )

            payment_id = str(uuid.uuid4())
            payment = Payment(
                id=payment_id,
                borrowing_id=borrowing.id,
                user_id=actor.id,
                amount=self._borrow_fee,
                kind="BORROW",
                created_at=now,
            )

            updated_book = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=book.total_copies,
                available_copies=book.available_copies - 1,
            )

            self._db.borrowings[borrowing_id] = borrowing
            self._db.payments[payment_id] = payment
            self._db.books[book.id] = updated_book

            return borrowing, payment

    def return_book(self, actor: User, borrowing_id: str) -> Tuple[Borrowing, Optional[Payment]]:
        with self._db.lock():
            borrowing = self._db.borrowings.get(borrowing_id)
            if not borrowing:
                raise NotFoundError("Borrowing not found")
            if borrowing.user_id != actor.id and not actor.is_admin:
                raise AuthorizationError("Not allowed to return this borrowing")
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

            updated_book = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=book.total_copies,
                available_copies=book.available_copies + 1,
            )

            fine_payment: Optional[Payment] = None
            overdue_days = self._calculate_overdue_days(updated_borrowing.due_at, now)
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

            self._db.borrowings[borrowing_id] = updated_borrowing
            self._db.books[book.id] = updated_book

            return updated_borrowing, fine_payment

    def list_borrowings(
        self,
        actor: User,
        actual_returned: Optional[bool] = None,
        user_id: Optional[str] = None,
    ) -> List[Borrowing]:
        with self._db.lock():
            borrowings = list(self._db.borrowings.values())

            if not actor.is_admin:
                borrowings = [b for b in borrowings if b.user_id == actor.id]
            else:
                if user_id is not None:
                    borrowings = [b for b in borrowings if b.user_id == user_id]

            if actual_returned is True:
                borrowings = [b for b in borrowings if b.actual_return_at is not None]
            elif actual_returned is False:
                borrowings = [b for b in borrowings if b.actual_return_at is None]

            borrowings.sort(key=lambda b: b.borrowed_at, reverse=True)
            return borrowings

    def list_payments(self, actor: User, user_id: Optional[str] = None) -> List[Payment]:
        with self._db.lock():
            payments = list(self._db.payments.values())
            if actor.is_admin:
                if user_id is not None:
                    payments = [p for p in payments if p.user_id == user_id]
            else:
                payments = [p for p in payments if p.user_id == actor.id]
            payments.sort(key=lambda p: p.created_at, reverse=True)
            return payments

    @staticmethod
    def _calculate_overdue_days(due_at: datetime, returned_at: datetime) -> int:
        if returned_at <= due_at:
            return 0
        delta = returned_at - due_at
        days = delta.days
        if delta.seconds > 0 or delta.microseconds > 0:
            days += 1
        return max(0, days)


class Router:
    def __init__(self) -> None:
        self._routes: Dict[Tuple[str, str], Any] = {}

    def add(self, method: str, path: str, handler: Any) -> None:
        key = (method.upper(), path)
        if key in self._routes:
            raise ConflictError("Route already registered")
        self._routes[key] = handler

    def dispatch(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, body: Any = None, query: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        headers = headers or {}
        query = query or {}
        key = (method.upper(), path)
        handler = self._routes.get(key)
        if not handler:
            raise NotFoundError("Endpoint not found")
        return handler(headers=headers, body=body, query=query)


class LibraryServiceAPI:
    def __init__(self, jwt_secret: str) -> None:
        self.db = InMemoryDB()
        self.jwt = JWTService(secret=jwt_secret)
        self.hasher = PasswordHasher()
        self.auth = AuthService(self.db, self.jwt, self.hasher)
        self.admin = AdminService(self.db)
        self.library = LibraryService(self.db)
        self.router = Router()
        self._register_routes()

    @property
    def admin_panel_path(self) -> str:
        return "/admin/"

    @property
    def swagger_docs_path(self) -> str:
        return "/api/v1/doc/swagger/"

    def _register_routes(self) -> None:
        self.router.add("POST", "/api/v1/auth/register", self._ep_register)
        self.router.add("POST", "/api/v1/auth/login", self._ep_login)

        self.router.add("GET", "/api/v1/books", self._ep_list_books)
        self.router.add("POST", "/api/v1/admin/books", self._ep_admin_create_book)

        self.router.add("POST", "/api/v1/borrowings", self._ep_borrow_book)
        self.router.add("POST", "/api/v1/borrowings/return", self._ep_return_book)
        self.router.add("GET", "/api/v1/borrowings", self._ep_list_borrowings)

        self.router.add("GET", "/api/v1/payments", self._ep_list_payments)

    def _get_actor(self, headers: Dict[str, str]) -> User:
        auth = headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise AuthenticationError("Missing Bearer token")
        token = auth[len("Bearer ") :].strip()
        return self.auth.authenticate(token)

    @staticmethod
    def _serialize_user(user: User) -> Dict[str, Any]:
        return {"id": user.id, "username": user.username, "is_admin": user.is_admin}

    @staticmethod
    def _serialize_book(book: Book) -> Dict[str, Any]:
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
        }

    @staticmethod
    def _serialize_borrowing(b: Borrowing) -> Dict[str, Any]:
        return {
            "id": b.id,
            "user_id": b.user_id,
            "book_id": b.book_id,
            "borrowed_at": b.borrowed_at.isoformat(),
            "due_at": b.due_at.isoformat(),
            "actual_return_at": b.actual_return_at.isoformat() if b.actual_return_at else None,
        }

    @staticmethod
    def _serialize_payment(p: Payment) -> Dict[str, Any]:
        return {
            "id": p.id,
            "borrowing_id": p.borrowing_id,
            "user_id": p.user_id,
            "amount": str(p.amount),
            "kind": p.kind,
            "created_at": p.created_at.isoformat(),
        }

    def _ep_register(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        if not isinstance(body, dict):
            raise ValidationError("Invalid body")
        user = self.auth.register(
            username=str(body.get("username", "")).strip(),
            password=str(body.get("password", "")),
            is_admin=bool(body.get("is_admin", False)),
        )
        return {"user": self._serialize_user(user)}

    def _ep_login(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        if not isinstance(body, dict):
            raise ValidationError("Invalid body")
        token = self.auth.login(
            username=str(body.get("username", "")).strip(),
            password=str(body.get("password", "")),
            expires_in_seconds=int(body.get("expires_in_seconds", 3600)),
        )
        return {"access_token": token, "token_type": "Bearer"}

    def _ep_list_books(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        books = self.library.list_books()
        return {"results": [self._serialize_book(b) for b in books]}

    def _ep_admin_create_book(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        actor = self._get_actor(headers)
        if not isinstance(body, dict):
            raise ValidationError("Invalid body")
        book = self.admin.create_book(
            actor=actor,
            title=str(body.get("title", "")).strip(),
            author=str(body.get("author", "")).strip(),
            total_copies=int(body.get("total_copies", 0)),
        )
        return {"book": self._serialize_book(book)}

    def _ep_borrow_book(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        actor = self._get_actor(headers)
        if not isinstance(body, dict):
            raise ValidationError("Invalid body")
        borrowing, payment = self.library.borrow_book(
            actor=actor,
            book_id=str(body.get("book_id", "")).strip(),
            borrow_days=int(body.get("borrow_days", self.library._default_borrow_days)),
        )
        return {"borrowing": self._serialize_borrowing(borrowing), "payment": self._serialize_payment(payment)}

    def _ep_return_book(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        actor = self._get_actor(headers)
        if not isinstance(body, dict):
            raise ValidationError("Invalid body")
        borrowing_id = str(body.get("borrowing_id", "")).strip()
        borrowing, fine_payment = self.library.return_book(actor=actor, borrowing_id=borrowing_id)
        resp: Dict[str, Any] = {"borrowing": self._serialize_borrowing(borrowing)}
        if fine_payment is not None:
            resp["fine_payment"] = self._serialize_payment(fine_payment)
        return resp

    def _ep_list_borrowings(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        actor = self._get_actor(headers)
        actual_returned_raw = query.get("actual_returned")
        actual_returned: Optional[bool]
        if actual_returned_raw is None or actual_returned_raw == "":
            actual_returned = None
        else:
            v = actual_returned_raw.strip().lower()
            if v in ("true", "1", "yes"):
                actual_returned = True
            elif v in ("false", "0", "no"):
                actual_returned = False
            else:
                raise ValidationError("Invalid actual_returned filter")

        user_id = query.get("user_id")
        if user_id is not None:
            user_id = user_id.strip() or None

        borrowings = self.library.list_borrowings(actor=actor, actual_returned=actual_returned, user_id=user_id)
        return {"results": [self._serialize_borrowing(b) for b in borrowings]}

    def _ep_list_payments(self, headers: Dict[str, str], body: Any, query: Dict[str, str]) -> Dict[str, Any]:
        actor = self._get_actor(headers)
        user_id = query.get("user_id")
        if user_id is not None:
            user_id = user_id.strip() or None
        payments = self.library.list_payments(actor=actor, user_id=user_id)
        return {"results": [self._serialize_payment(p) for p in payments]}


def create_app(jwt_secret: str) -> LibraryServiceAPI:
    return LibraryServiceAPI(jwt_secret=jwt_secret)