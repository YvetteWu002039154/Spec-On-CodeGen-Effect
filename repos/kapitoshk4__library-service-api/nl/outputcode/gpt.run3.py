from __future__ import annotations

import base64
import dataclasses
import datetime as _dt
import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.timezone.utc)


def _date_today() -> _dt.date:
    return _utcnow().date()


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise TypeError("Invalid decimal value")


def _money(value: Any) -> Decimal:
    d = _to_decimal(value)
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


class ValidationError(ValueError):
    pass


class AuthenticationError(PermissionError):
    pass


class AuthorizationError(PermissionError):
    pass


class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class JWTService:
    def __init__(self, secret: str, issuer: str = "library-service-api") -> None:
        if not secret or not isinstance(secret, str):
            raise ValidationError("JWT secret must be a non-empty string")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer

    def issue(self, subject: str, is_admin: bool, expires_in_seconds: int = 3600) -> str:
        if not subject:
            raise ValidationError("subject required")
        if expires_in_seconds <= 0:
            raise ValidationError("expires_in_seconds must be positive")

        header = {"alg": "HS256", "typ": "JWT"}
        now = int(_utcnow().timestamp())
        payload = {
            "iss": self._issuer,
            "sub": subject,
            "admin": bool(is_admin),
            "iat": now,
            "exp": now + int(expires_in_seconds),
        }

        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(sig)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify(self, token: str) -> Dict[str, Any]:
        if not token or not isinstance(token, str):
            raise AuthenticationError("Invalid token")

        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        try:
            provided_sig = _b64url_decode(sig_b64)
        except Exception as e:
            raise AuthenticationError("Invalid token signature encoding") from e

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise AuthenticationError("Invalid token signature")

        try:
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except Exception as e:
            raise AuthenticationError("Invalid token payload") from e

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

        admin = payload.get("admin")
        if not isinstance(admin, bool):
            raise AuthenticationError("Invalid token admin claim")

        return payload


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    is_admin: bool = False
    created_at: _dt.datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    total_copies: int
    available_copies: int
    daily_fee: Decimal
    created_at: _dt.datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class Borrowing:
    id: int
    user_id: int
    book_id: int
    borrowed_at: _dt.datetime
    expected_return_date: _dt.date
    actual_return_date: Optional[_dt.date] = None


@dataclass(frozen=True)
class Payment:
    id: int
    borrowing_id: int
    user_id: int
    amount: Decimal
    kind: str  # "BORROW" or "FINE"
    created_at: _dt.datetime = field(default_factory=_utcnow)


class PasswordHasher:
    def hash_password(self, password: str) -> str:
        if not isinstance(password, str) or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return f"pbkdf2_sha256${salt}${digest.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algo, salt, hex_digest = password_hash.split("$", 2)
        except Exception:
            return False
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return hmac.compare_digest(digest.hex(), hex_digest)


class InMemoryDB:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: Dict[int, User] = {}
        self._books: Dict[int, Book] = {}
        self._borrowings: Dict[int, Borrowing] = {}
        self._payments: Dict[int, Payment] = {}
        self._user_seq = 0
        self._book_seq = 0
        self._borrowing_seq = 0
        self._payment_seq = 0

    def _next_user_id(self) -> int:
        self._user_seq += 1
        return self._user_seq

    def _next_book_id(self) -> int:
        self._book_seq += 1
        return self._book_seq

    def _next_borrowing_id(self) -> int:
        self._borrowing_seq += 1
        return self._borrowing_seq

    def _next_payment_id(self) -> int:
        self._payment_seq += 1
        return self._payment_seq

    def create_user(self, username: str, password_hash: str, is_admin: bool) -> User:
        with self._lock:
            if any(u.username == username for u in self._users.values()):
                raise ConflictError("Username already exists")
            uid = self._next_user_id()
            user = User(id=uid, username=username, password_hash=password_hash, is_admin=is_admin)
            self._users[uid] = user
            return user

    def get_user_by_username(self, username: str) -> User:
        with self._lock:
            for u in self._users.values():
                if u.username == username:
                    return u
        raise NotFoundError("User not found")

    def get_user(self, user_id: int) -> User:
        with self._lock:
            u = self._users.get(user_id)
            if not u:
                raise NotFoundError("User not found")
            return u

    def create_book(self, title: str, author: str, total_copies: int, daily_fee: Decimal) -> Book:
        with self._lock:
            bid = self._next_book_id()
            book = Book(
                id=bid,
                title=title,
                author=author,
                total_copies=total_copies,
                available_copies=total_copies,
                daily_fee=_money(daily_fee),
            )
            self._books[bid] = book
            return book

    def update_book(self, book_id: int, *, title: Optional[str] = None, author: Optional[str] = None,
                    total_copies: Optional[int] = None, daily_fee: Optional[Decimal] = None) -> Book:
        with self._lock:
            book = self._books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")

            new_title = book.title if title is None else title
            new_author = book.author if author is None else author
            new_daily_fee = book.daily_fee if daily_fee is None else _money(daily_fee)

            if total_copies is None:
                new_total = book.total_copies
                new_available = book.available_copies
            else:
                if total_copies < 0:
                    raise ValidationError("total_copies must be non-negative")
                borrowed_count = book.total_copies - book.available_copies
                if total_copies < borrowed_count:
                    raise ValidationError("total_copies cannot be less than currently borrowed copies")
                new_total = total_copies
                new_available = total_copies - borrowed_count

            updated = dataclasses.replace(
                book,
                title=new_title,
                author=new_author,
                total_copies=new_total,
                available_copies=new_available,
                daily_fee=new_daily_fee,
            )
            self._books[book_id] = updated
            return updated

    def get_book(self, book_id: int) -> Book:
        with self._lock:
            b = self._books.get(book_id)
            if not b:
                raise NotFoundError("Book not found")
            return b

    def list_books(self) -> List[Book]:
        with self._lock:
            return list(self._books.values())

    def create_borrowing(self, user_id: int, book_id: int, expected_return_date: _dt.date) -> Borrowing:
        with self._lock:
            if user_id not in self._users:
                raise NotFoundError("User not found")
            book = self._books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            if book.available_copies <= 0:
                raise ConflictError("No available copies")

            borrowing_id = self._next_borrowing_id()
            borrowing = Borrowing(
                id=borrowing_id,
                user_id=user_id,
                book_id=book_id,
                borrowed_at=_utcnow(),
                expected_return_date=expected_return_date,
                actual_return_date=None,
            )
            self._borrowings[borrowing_id] = borrowing
            self._books[book_id] = dataclasses.replace(book, available_copies=book.available_copies - 1)
            return borrowing

    def set_borrowing_returned(self, borrowing_id: int, actual_return_date: _dt.date) -> Borrowing:
        with self._lock:
            borrowing = self._borrowings.get(borrowing_id)
            if not borrowing:
                raise NotFoundError("Borrowing not found")
            if borrowing.actual_return_date is not None:
                raise ConflictError("Borrowing already returned")

            updated = dataclasses.replace(borrowing, actual_return_date=actual_return_date)
            self._borrowings[borrowing_id] = updated

            book = self._books.get(borrowing.book_id)
            if not book:
                raise NotFoundError("Book not found")
            self._books[book.id] = dataclasses.replace(book, available_copies=book.available_copies + 1)
            return updated

    def get_borrowing(self, borrowing_id: int) -> Borrowing:
        with self._lock:
            b = self._borrowings.get(borrowing_id)
            if not b:
                raise NotFoundError("Borrowing not found")
            return b

    def list_borrowings(self) -> List[Borrowing]:
        with self._lock:
            return list(self._borrowings.values())

    def create_payment(self, borrowing_id: int, user_id: int, amount: Decimal, kind: str) -> Payment:
        with self._lock:
            if borrowing_id not in self._borrowings:
                raise NotFoundError("Borrowing not found")
            if user_id not in self._users:
                raise NotFoundError("User not found")
            pid = self._next_payment_id()
            payment = Payment(
                id=pid,
                borrowing_id=borrowing_id,
                user_id=user_id,
                amount=_money(amount),
                kind=kind,
                created_at=_utcnow(),
            )
            self._payments[pid] = payment
            return payment

    def list_payments(self) -> List[Payment]:
        with self._lock:
            return list(self._payments.values())

    def list_payments_for_borrowing(self, borrowing_id: int) -> List[Payment]:
        with self._lock:
            return [p for p in self._payments.values() if p.borrowing_id == borrowing_id]


class LibraryService:
    BORROW_PAYMENT_KIND = "BORROW"
    FINE_PAYMENT_KIND = "FINE"

    def __init__(self, db: InMemoryDB, jwt: JWTService, hasher: PasswordHasher) -> None:
        self._db = db
        self._jwt = jwt
        self._hasher = hasher

    def register_user(self, username: str, password: str, is_admin: bool = False) -> User:
        if not isinstance(username, str) or not username.strip():
            raise ValidationError("username required")
        password_hash = self._hasher.hash_password(password)
        return self._db.create_user(username=username.strip(), password_hash=password_hash, is_admin=bool(is_admin))

    def login(self, username: str, password: str, expires_in_seconds: int = 3600) -> str:
        user = self._db.get_user_by_username(username)
        if not self._hasher.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        return self._jwt.issue(subject=str(user.id), is_admin=user.is_admin, expires_in_seconds=expires_in_seconds)

    def authenticate(self, token: str) -> User:
        payload = self._jwt.verify(token)
        user_id = int(payload["sub"])
        return self._db.get_user(user_id)

    def _require_admin(self, user: User) -> None:
        if not user.is_admin:
            raise AuthorizationError("Admin privileges required")

    def admin_create_book(self, admin: User, title: str, author: str, total_copies: int, daily_fee: Any) -> Book:
        self._require_admin(admin)
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("title required")
        if not isinstance(author, str) or not author.strip():
            raise ValidationError("author required")
        if not isinstance(total_copies, int) or total_copies < 0:
            raise ValidationError("total_copies must be a non-negative integer")
        fee = _money(daily_fee)
        if fee < Decimal("0.00"):
            raise ValidationError("daily_fee must be non-negative")
        return self._db.create_book(title=title.strip(), author=author.strip(), total_copies=total_copies, daily_fee=fee)

    def admin_update_book(self, admin: User, book_id: int, *, title: Optional[str] = None, author: Optional[str] = None,
                         total_copies: Optional[int] = None, daily_fee: Optional[Any] = None) -> Book:
        self._require_admin(admin)
        if title is not None and (not isinstance(title, str) or not title.strip()):
            raise ValidationError("title must be non-empty")
        if author is not None and (not isinstance(author, str) or not author.strip()):
            raise ValidationError("author must be non-empty")
        if total_copies is not None and (not isinstance(total_copies, int) or total_copies < 0):
            raise ValidationError("total_copies must be a non-negative integer")
        fee_dec: Optional[Decimal] = None
        if daily_fee is not None:
            fee_dec = _money(daily_fee)
            if fee_dec < Decimal("0.00"):
                raise ValidationError("daily_fee must be non-negative")
        return self._db.update_book(book_id, title=title.strip() if isinstance(title, str) else title,
                                   author=author.strip() if isinstance(author, str) else author,
                                   total_copies=total_copies, daily_fee=fee_dec)

    def list_books(self, user: User) -> List[Book]:
        _ = user
        return self._db.list_books()

    def borrow_book(self, user: User, book_id: int, expected_return_date: _dt.date) -> Borrowing:
        if not isinstance(expected_return_date, _dt.date):
            raise ValidationError("expected_return_date must be a date")
        if expected_return_date < _date_today():
            raise ValidationError("expected_return_date cannot be in the past")
        return self._db.create_borrowing(user_id=user.id, book_id=book_id, expected_return_date=expected_return_date)

    def return_borrowing(self, user: User, borrowing_id: int, actual_return_date: Optional[_dt.date] = None) -> Borrowing:
        borrowing = self._db.get_borrowing(borrowing_id)
        if not (user.is_admin or borrowing.user_id == user.id):
            raise AuthorizationError("Not allowed to return this borrowing")
        if actual_return_date is None:
            actual_return_date = _date_today()
        if not isinstance(actual_return_date, _dt.date):
            raise ValidationError("actual_return_date must be a date")
        if actual_return_date < borrowing.borrowed_at.date():
            raise ValidationError("actual_return_date cannot be before borrowed date")
        return self._db.set_borrowing_returned(borrowing_id, actual_return_date)

    def _borrowing_base_amount(self, borrowing: Borrowing) -> Decimal:
        book = self._db.get_book(borrowing.book_id)
        days = (borrowing.expected_return_date - borrowing.borrowed_at.date()).days
        if days < 1:
            days = 1
        return _money(book.daily_fee * Decimal(days))

    def _borrowing_fine_amount(self, borrowing: Borrowing) -> Decimal:
        if borrowing.actual_return_date is None:
            return Decimal("0.00")
        if borrowing.actual_return_date <= borrowing.expected_return_date:
            return Decimal("0.00")
        book = self._db.get_book(borrowing.book_id)
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        if overdue_days < 0:
            overdue_days = 0
        fine_per_day = _money(book.daily_fee)
        return _money(fine_per_day * Decimal(overdue_days))

    def make_payment_for_borrowing(self, user: User, borrowing_id: int) -> Payment:
        borrowing = self._db.get_borrowing(borrowing_id)
        if not (user.is_admin or borrowing.user_id == user.id):
            raise AuthorizationError("Not allowed to pay for this borrowing")

        existing = self._db.list_payments_for_borrowing(borrowing_id)
        if any(p.kind == self.BORROW_PAYMENT_KIND for p in existing):
            raise ConflictError("Borrowing payment already made")

        amount = self._borrowing_base_amount(borrowing)
        return self._db.create_payment(borrowing_id=borrowing_id, user_id=borrowing.user_id, amount=amount, kind=self.BORROW_PAYMENT_KIND)

    def make_fine_payment(self, user: User, borrowing_id: int) -> Payment:
        borrowing = self._db.get_borrowing(borrowing_id)
        if not (user.is_admin or borrowing.user_id == user.id):
            raise AuthorizationError("Not allowed to pay fine for this borrowing")
        if borrowing.actual_return_date is None:
            raise ConflictError("Cannot pay fine before return")

        existing = self._db.list_payments_for_borrowing(borrowing_id)
        if any(p.kind == self.FINE_PAYMENT_KIND for p in existing):
            raise ConflictError("Fine payment already made")

        fine = self._borrowing_fine_amount(borrowing)
        if fine <= Decimal("0.00"):
            raise ConflictError("No fine due")
        return self._db.create_payment(borrowing_id=borrowing_id, user_id=borrowing.user_id, amount=fine, kind=self.FINE_PAYMENT_KIND)

    def list_borrowings(
        self,
        user: User,
        *,
        actual_return_date: Optional[_dt.date] = None,
        user_id: Optional[int] = None,
    ) -> List[Borrowing]:
        borrowings = self._db.list_borrowings()

        if not user.is_admin:
            borrowings = [b for b in borrowings if b.user_id == user.id]
        else:
            if user_id is not None:
                borrowings = [b for b in borrowings if b.user_id == user_id]

        if actual_return_date is not None:
            if not isinstance(actual_return_date, _dt.date):
                raise ValidationError("actual_return_date must be a date")
            borrowings = [b for b in borrowings if b.actual_return_date == actual_return_date]

        return borrowings

    def list_payments(self, user: User, *, borrowing_id: Optional[int] = None, user_id: Optional[int] = None) -> List[Payment]:
        payments = self._db.list_payments()
        if not user.is_admin:
            payments = [p for p in payments if p.user_id == user.id]
        else:
            if user_id is not None:
                payments = [p for p in payments if p.user_id == user_id]
        if borrowing_id is not None:
            payments = [p for p in payments if p.borrowing_id == borrowing_id]
        return payments


class LibraryServiceAPI:
    ADMIN_PANEL_PATH = "/admin/"
    SWAGGER_DOCS_PATH = "/api/v1/doc/swagger/"

    def __init__(self, service: LibraryService) -> None:
        self._service = service

    def admin_panel(self) -> Dict[str, Any]:
        return {"path": self.ADMIN_PANEL_PATH, "available": True}

    def swagger_docs(self) -> Dict[str, Any]:
        return {"path": self.SWAGGER_DOCS_PATH, "available": True}

    def register(self, username: str, password: str, is_admin: bool = False) -> Dict[str, Any]:
        user = self._service.register_user(username=username, password=password, is_admin=is_admin)
        return {"id": user.id, "username": user.username, "is_admin": user.is_admin, "created_at": user.created_at.isoformat()}

    def login(self, username: str, password: str, expires_in_seconds: int = 3600) -> Dict[str, Any]:
        token = self._service.login(username=username, password=password, expires_in_seconds=expires_in_seconds)
        return {"token": token, "token_type": "Bearer"}

    def _auth(self, token: str) -> User:
        return self._service.authenticate(token)

    def create_book(self, token: str, title: str, author: str, total_copies: int, daily_fee: Any) -> Dict[str, Any]:
        admin = self._auth(token)
        book = self._service.admin_create_book(admin, title=title, author=author, total_copies=total_copies, daily_fee=daily_fee)
        return self._book_to_dict(book)

    def update_book(self, token: str, book_id: int, *, title: Optional[str] = None, author: Optional[str] = None,
                    total_copies: Optional[int] = None, daily_fee: Optional[Any] = None) -> Dict[str, Any]:
        admin = self._auth(token)
        book = self._service.admin_update_book(admin, book_id, title=title, author=author, total_copies=total_copies, daily_fee=daily_fee)
        return self._book_to_dict(book)

    def list_books(self, token: str) -> List[Dict[str, Any]]:
        user = self._auth(token)
        return [self._book_to_dict(b) for b in self._service.list_books(user)]

    def borrow(self, token: str, book_id: int, expected_return_date: _dt.date) -> Dict[str, Any]:
        user = self._auth(token)
        borrowing = self._service.borrow_book(user, book_id=book_id, expected_return_date=expected_return_date)
        return self._borrowing_to_dict(borrowing)

    def return_book(self, token: str, borrowing_id: int, actual_return_date: Optional[_dt.date] = None) -> Dict[str, Any]:
        user = self._auth(token)
        borrowing = self._service.return_borrowing(user, borrowing_id=borrowing_id, actual_return_date=actual_return_date)
        return self._borrowing_to_dict(borrowing)

    def pay_borrowing(self, token: str, borrowing_id: int) -> Dict[str, Any]:
        user = self._auth(token)
        payment = self._service.make_payment_for_borrowing(user, borrowing_id=borrowing_id)
        return self._payment_to_dict(payment)

    def pay_fine(self, token: str, borrowing_id: int) -> Dict[str, Any]:
        user = self._auth(token)
        payment = self._service.make_fine_payment(user, borrowing_id=borrowing_id)
        return self._payment_to_dict(payment)

    def list_borrowings(self, token: str, *, actual_return_date: Optional[_dt.date] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        user = self._auth(token)
        borrowings = self._service.list_borrowings(user, actual_return_date=actual_return_date, user_id=user_id)
        return [self._borrowing_to_dict(b) for b in borrowings]

    def list_payments(self, token: str, *, borrowing_id: Optional[int] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        user = self._auth(token)
        payments = self._service.list_payments(user, borrowing_id=borrowing_id, user_id=user_id)
        return [self._payment_to_dict(p) for p in payments]

    @staticmethod
    def _book_to_dict(book: Book) -> Dict[str, Any]:
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "daily_fee": str(book.daily_fee),
            "created_at": book.created_at.isoformat(),
        }

    @staticmethod
    def _borrowing_to_dict(b: Borrowing) -> Dict[str, Any]:
        return {
            "id": b.id,
            "user_id": b.user_id,
            "book_id": b.book_id,
            "borrowed_at": b.borrowed_at.isoformat(),
            "expected_return_date": b.expected_return_date.isoformat(),
            "actual_return_date": b.actual_return_date.isoformat() if b.actual_return_date else None,
        }

    @staticmethod
    def _payment_to_dict(p: Payment) -> Dict[str, Any]:
        return {
            "id": p.id,
            "borrowing_id": p.borrowing_id,
            "user_id": p.user_id,
            "amount": str(p.amount),
            "kind": p.kind,
            "created_at": p.created_at.isoformat(),
        }


def create_app(secret: str) -> LibraryServiceAPI:
    db = InMemoryDB()
    jwt = JWTService(secret=secret)
    hasher = PasswordHasher()
    service = LibraryService(db=db, jwt=jwt, hasher=hasher)
    return LibraryServiceAPI(service=service)