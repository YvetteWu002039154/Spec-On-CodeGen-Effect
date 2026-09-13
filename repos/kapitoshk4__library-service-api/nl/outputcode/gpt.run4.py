from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import base64
import hashlib
import hmac
import json
import secrets
import threading


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


def _utcnow() -> datetime:
    return datetime.utcnow()


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(str(value))
    if isinstance(value, float):
        return Decimal(str(value))
    raise ValidationError("Invalid decimal value")


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

    def issue(self, subject: str, claims: Optional[Dict[str, Any]] = None, expires_in_seconds: int = 3600) -> str:
        if not subject:
            raise ValidationError("JWT subject is required")
        if expires_in_seconds <= 0:
            raise ValidationError("expires_in_seconds must be positive")

        header = {"alg": "HS256", "typ": "JWT"}
        now = int(_utcnow().timestamp())
        payload: Dict[str, Any] = {
            "iss": self._issuer,
            "sub": subject,
            "iat": now,
            "exp": now + expires_in_seconds,
        }
        if claims:
            for k, v in claims.items():
                if k in payload:
                    raise ValidationError(f"Claim '{k}' is reserved")
                payload[k] = v

        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify(self, token: str) -> Dict[str, Any]:
        if not token or token.count(".") != 2:
            raise AuthenticationError("Invalid token format")
        header_b64, payload_b64, sig_b64 = token.split(".")
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
    id: int
    username: str
    is_admin: bool


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    total_copies: int
    available_copies: int


@dataclass(frozen=True)
class Borrowing:
    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    expected_return_date: date
    actual_return_date: Optional[date]


@dataclass(frozen=True)
class Payment:
    id: int
    borrowing_id: int
    user_id: int
    amount: Decimal
    kind: str  # "BORROW" or "FINE"
    created_at: datetime


class InMemoryDB:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: Dict[int, Dict[str, Any]] = {}
        self._books: Dict[int, Dict[str, Any]] = {}
        self._borrowings: Dict[int, Dict[str, Any]] = {}
        self._payments: Dict[int, Dict[str, Any]] = {}
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
            if any(u["username"] == username for u in self._users.values()):
                raise ConflictError("Username already exists")
            uid = self._next_user_id()
            self._users[uid] = {"id": uid, "username": username, "password_hash": password_hash, "is_admin": is_admin}
            return User(id=uid, username=username, is_admin=is_admin)

    def get_user_by_username(self, username: str) -> Tuple[User, str]:
        with self._lock:
            for u in self._users.values():
                if u["username"] == username:
                    return User(id=u["id"], username=u["username"], is_admin=u["is_admin"]), u["password_hash"]
        raise NotFoundError("User not found")

    def get_user(self, user_id: int) -> User:
        with self._lock:
            u = self._users.get(user_id)
            if not u:
                raise NotFoundError("User not found")
            return User(id=u["id"], username=u["username"], is_admin=u["is_admin"])

    def create_book(self, title: str, author: str, total_copies: int) -> Book:
        if not title or not author:
            raise ValidationError("Title and author are required")
        if total_copies <= 0:
            raise ValidationError("total_copies must be positive")
        with self._lock:
            bid = self._next_book_id()
            self._books[bid] = {
                "id": bid,
                "title": title,
                "author": author,
                "total_copies": total_copies,
                "available_copies": total_copies,
            }
            return self.get_book(bid)

    def update_book(self, book_id: int, title: Optional[str], author: Optional[str], total_copies: Optional[int]) -> Book:
        with self._lock:
            b = self._books.get(book_id)
            if not b:
                raise NotFoundError("Book not found")
            if title is not None:
                if not title:
                    raise ValidationError("Title cannot be empty")
                b["title"] = title
            if author is not None:
                if not author:
                    raise ValidationError("Author cannot be empty")
                b["author"] = author
            if total_copies is not None:
                if total_copies <= 0:
                    raise ValidationError("total_copies must be positive")
                borrowed_count = b["total_copies"] - b["available_copies"]
                if total_copies < borrowed_count:
                    raise ValidationError("total_copies cannot be less than currently borrowed copies")
                b["total_copies"] = total_copies
                b["available_copies"] = total_copies - borrowed_count
            return self.get_book(book_id)

    def delete_book(self, book_id: int) -> None:
        with self._lock:
            b = self._books.get(book_id)
            if not b:
                raise NotFoundError("Book not found")
            if b["available_copies"] != b["total_copies"]:
                raise ConflictError("Cannot delete book with active borrowings")
            del self._books[book_id]

    def list_books(self, filters: Optional[Dict[str, Any]] = None) -> List[Book]:
        filters = filters or {}
        title = filters.get("title")
        author = filters.get("author")
        available_only = filters.get("available_only")
        with self._lock:
            books = [self._to_book(v) for v in self._books.values()]
        if title is not None:
            books = [b for b in books if title.lower() in b.title.lower()]
        if author is not None:
            books = [b for b in books if author.lower() in b.author.lower()]
        if available_only is True:
            books = [b for b in books if b.available_copies > 0]
        return sorted(books, key=lambda x: x.id)

    def get_book(self, book_id: int) -> Book:
        with self._lock:
            b = self._books.get(book_id)
            if not b:
                raise NotFoundError("Book not found")
            return self._to_book(b)

    def _to_book(self, b: Dict[str, Any]) -> Book:
        return Book(
            id=b["id"],
            title=b["title"],
            author=b["author"],
            total_copies=b["total_copies"],
            available_copies=b["available_copies"],
        )

    def create_borrowing(self, user_id: int, book_id: int, expected_return_date: date) -> Borrowing:
        if expected_return_date <= date.today():
            raise ValidationError("expected_return_date must be in the future")
        with self._lock:
            if user_id not in self._users:
                raise NotFoundError("User not found")
            b = self._books.get(book_id)
            if not b:
                raise NotFoundError("Book not found")
            if b["available_copies"] <= 0:
                raise ConflictError("No available copies")
            b["available_copies"] -= 1
            bor_id = self._next_borrowing_id()
            self._borrowings[bor_id] = {
                "id": bor_id,
                "user_id": user_id,
                "book_id": book_id,
                "borrowed_at": _utcnow(),
                "expected_return_date": expected_return_date,
                "actual_return_date": None,
            }
            return self.get_borrowing(bor_id)

    def return_borrowing(self, borrowing_id: int, actual_return_date: date) -> Borrowing:
        with self._lock:
            br = self._borrowings.get(borrowing_id)
            if not br:
                raise NotFoundError("Borrowing not found")
            if br["actual_return_date"] is not None:
                raise ConflictError("Borrowing already returned")
            if actual_return_date < br["borrowed_at"].date():
                raise ValidationError("actual_return_date cannot be before borrowed date")
            br["actual_return_date"] = actual_return_date
            b = self._books.get(br["book_id"])
            if not b:
                raise NotFoundError("Book not found")
            if b["available_copies"] >= b["total_copies"]:
                raise ConflictError("Book inventory inconsistent")
            b["available_copies"] += 1
            return self.get_borrowing(borrowing_id)

    def get_borrowing(self, borrowing_id: int) -> Borrowing:
        with self._lock:
            br = self._borrowings.get(borrowing_id)
            if not br:
                raise NotFoundError("Borrowing not found")
            return Borrowing(
                id=br["id"],
                user_id=br["user_id"],
                book_id=br["book_id"],
                borrowed_at=br["borrowed_at"],
                expected_return_date=br["expected_return_date"],
                actual_return_date=br["actual_return_date"],
            )

    def list_borrowings(self, filters: Optional[Dict[str, Any]] = None) -> List[Borrowing]:
        filters = filters or {}
        user_id = filters.get("user_id")
        actual_return_date = filters.get("actual_return_date")
        with self._lock:
            borrowings = [self.get_borrowing(v["id"]) for v in self._borrowings.values()]
        if user_id is not None:
            borrowings = [b for b in borrowings if b.user_id == int(user_id)]
        if actual_return_date is not None:
            if isinstance(actual_return_date, str):
                actual_return_date = date.fromisoformat(actual_return_date)
            borrowings = [b for b in borrowings if b.actual_return_date == actual_return_date]
        return sorted(borrowings, key=lambda x: x.id)

    def create_payment(self, borrowing_id: int, user_id: int, amount: Decimal, kind: str) -> Payment:
        if kind not in ("BORROW", "FINE"):
            raise ValidationError("Invalid payment kind")
        amount = _to_decimal(amount)
        if amount <= Decimal("0"):
            raise ValidationError("Payment amount must be positive")
        with self._lock:
            if borrowing_id not in self._borrowings:
                raise NotFoundError("Borrowing not found")
            if user_id not in self._users:
                raise NotFoundError("User not found")
            pid = self._next_payment_id()
            self._payments[pid] = {
                "id": pid,
                "borrowing_id": borrowing_id,
                "user_id": user_id,
                "amount": amount,
                "kind": kind,
                "created_at": _utcnow(),
            }
            return self.get_payment(pid)

    def list_payments(self, filters: Optional[Dict[str, Any]] = None) -> List[Payment]:
        filters = filters or {}
        user_id = filters.get("user_id")
        borrowing_id = filters.get("borrowing_id")
        kind = filters.get("kind")
        with self._lock:
            payments = [self.get_payment(v["id"]) for v in self._payments.values()]
        if user_id is not None:
            payments = [p for p in payments if p.user_id == int(user_id)]
        if borrowing_id is not None:
            payments = [p for p in payments if p.borrowing_id == int(borrowing_id)]
        if kind is not None:
            payments = [p for p in payments if p.kind == kind]
        return sorted(payments, key=lambda x: x.id)

    def get_payment(self, payment_id: int) -> Payment:
        with self._lock:
            p = self._payments.get(payment_id)
            if not p:
                raise NotFoundError("Payment not found")
            return Payment(
                id=p["id"],
                borrowing_id=p["borrowing_id"],
                user_id=p["user_id"],
                amount=p["amount"],
                kind=p["kind"],
                created_at=p["created_at"],
            )


class AuthService:
    def __init__(self, db: InMemoryDB, jwt: JWTService, hasher: PasswordHasher) -> None:
        self._db = db
        self._jwt = jwt
        self._hasher = hasher

    def register(self, username: str, password: str, is_admin: bool = False) -> User:
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")
        password_hash = self._hasher.hash_password(password)
        return self._db.create_user(username=username, password_hash=password_hash, is_admin=is_admin)

    def login(self, username: str, password: str, expires_in_seconds: int = 3600) -> str:
        user, password_hash = self._db.get_user_by_username(username)
        if not self._hasher.verify_password(password, password_hash):
            raise AuthenticationError("Invalid credentials")
        return self._jwt.issue(subject=str(user.id), claims={"is_admin": user.is_admin, "username": user.username}, expires_in_seconds=expires_in_seconds)

    def authenticate(self, token: str) -> User:
        payload = self._jwt.verify(token)
        user_id = int(payload["sub"])
        return self._db.get_user(user_id)


class LibraryService:
    def __init__(
        self,
        db: InMemoryDB,
        borrow_fee: Decimal = Decimal("5.00"),
        fine_per_day: Decimal = Decimal("1.00"),
    ) -> None:
        self._db = db
        self._borrow_fee = _to_decimal(borrow_fee)
        self._fine_per_day = _to_decimal(fine_per_day)
        if self._borrow_fee < Decimal("0") or self._fine_per_day < Decimal("0"):
            raise ValidationError("Fees cannot be negative")

    def create_book(self, actor: User, title: str, author: str, total_copies: int) -> Book:
        self._require_admin(actor)
        return self._db.create_book(title=title, author=author, total_copies=total_copies)

    def update_book(self, actor: User, book_id: int, title: Optional[str] = None, author: Optional[str] = None, total_copies: Optional[int] = None) -> Book:
        self._require_admin(actor)
        return self._db.update_book(book_id=book_id, title=title, author=author, total_copies=total_copies)

    def delete_book(self, actor: User, book_id: int) -> None:
        self._require_admin(actor)
        self._db.delete_book(book_id)

    def list_books(self, actor: User, filters: Optional[Dict[str, Any]] = None) -> List[Book]:
        self._require_authenticated(actor)
        return self._db.list_books(filters=filters)

    def borrow_book(self, actor: User, book_id: int, expected_return_date: date) -> Tuple[Borrowing, Payment]:
        self._require_authenticated(actor)
        borrowing = self._db.create_borrowing(user_id=actor.id, book_id=book_id, expected_return_date=expected_return_date)
        payment = self._db.create_payment(borrowing_id=borrowing.id, user_id=actor.id, amount=self._borrow_fee, kind="BORROW")
        return borrowing, payment

    def return_book(self, actor: User, borrowing_id: int, actual_return_date: date) -> Tuple[Borrowing, Optional[Payment]]:
        self._require_authenticated(actor)
        borrowing = self._db.get_borrowing(borrowing_id)
        if not actor.is_admin and borrowing.user_id != actor.id:
            raise AuthorizationError("Cannot return another user's borrowing")
        updated = self._db.return_borrowing(borrowing_id=borrowing_id, actual_return_date=actual_return_date)
        fine_amount = self._calculate_fine(updated)
        fine_payment: Optional[Payment] = None
        if fine_amount > Decimal("0"):
            fine_payment = self._db.create_payment(borrowing_id=updated.id, user_id=updated.user_id, amount=fine_amount, kind="FINE")
        return updated, fine_payment

    def list_borrowings(self, actor: User, filters: Optional[Dict[str, Any]] = None) -> List[Borrowing]:
        self._require_authenticated(actor)
        filters = dict(filters or {})
        if not actor.is_admin:
            filters["user_id"] = actor.id
        return self._db.list_borrowings(filters=filters)

    def list_payments(self, actor: User, filters: Optional[Dict[str, Any]] = None) -> List[Payment]:
        self._require_authenticated(actor)
        filters = dict(filters or {})
        if not actor.is_admin:
            filters["user_id"] = actor.id
        return self._db.list_payments(filters=filters)

    def _calculate_fine(self, borrowing: Borrowing) -> Decimal:
        if borrowing.actual_return_date is None:
            return Decimal("0")
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        if overdue_days <= 0:
            return Decimal("0")
        return (self._fine_per_day * Decimal(overdue_days)).quantize(Decimal("0.01"))

    @staticmethod
    def _require_authenticated(actor: Optional[User]) -> None:
        if actor is None:
            raise AuthenticationError("Authentication required")

    @staticmethod
    def _require_admin(actor: User) -> None:
        if actor is None:
            raise AuthenticationError("Authentication required")
        if not actor.is_admin:
            raise AuthorizationError("Admin privileges required")


class SwaggerDoc:
    def __init__(self, title: str, version: str, endpoints: List[Dict[str, Any]]) -> None:
        self.title = title
        self.version = version
        self.endpoints = endpoints

    def as_dict(self) -> Dict[str, Any]:
        return {
            "openapi": "3.0.0",
            "info": {"title": self.title, "version": self.version},
            "paths": {e["path"]: e["spec"] for e in self.endpoints},
        }


class LibraryServiceAPI:
    def __init__(self, secret: str) -> None:
        self.db = InMemoryDB()
        self.jwt = JWTService(secret=secret)
        self.hasher = PasswordHasher()
        self.auth = AuthService(db=self.db, jwt=self.jwt, hasher=self.hasher)
        self.library = LibraryService(db=self.db)

    def admin_panel_path(self) -> str:
        return "/admin/"

    def swagger_path(self) -> str:
        return "/api/v1/doc/swagger/"

    def swagger(self) -> Dict[str, Any]:
        endpoints: List[Dict[str, Any]] = [
            {
                "path": "/api/v1/auth/register/",
                "spec": {
                    "post": {
                        "summary": "Register user",
                        "requestBody": {"required": True},
                        "responses": {"200": {"description": "User created"}},
                    }
                },
            },
            {
                "path": "/api/v1/auth/login/",
                "spec": {
                    "post": {
                        "summary": "Login and receive JWT",
                        "requestBody": {"required": True},
                        "responses": {"200": {"description": "JWT token"}},
                    }
                },
            },
            {
                "path": "/api/v1/books/",
                "spec": {
                    "get": {
                        "summary": "List books",
                        "parameters": [
                            {"name": "title", "in": "query", "required": False},
                            {"name": "author", "in": "query", "required": False},
                            {"name": "available_only", "in": "query", "required": False},
                        ],
                        "responses": {"200": {"description": "Books list"}},
                    },
                    "post": {"summary": "Create book (admin)", "responses": {"200": {"description": "Book created"}}},
                },
            },
            {
                "path": "/api/v1/borrowings/",
                "spec": {
                    "get": {
                        "summary": "List borrowings (filterable)",
                        "parameters": [
                            {"name": "user_id", "in": "query", "required": False},
                            {"name": "actual_return_date", "in": "query", "required": False},
                        ],
                        "responses": {"200": {"description": "Borrowings list"}},
                    },
                    "post": {"summary": "Borrow a book", "responses": {"200": {"description": "Borrowing created"}}},
                },
            },
            {
                "path": "/api/v1/borrowings/{id}/return/",
                "spec": {"post": {"summary": "Return a borrowing", "responses": {"200": {"description": "Returned"}}}},
            },
            {
                "path": "/api/v1/payments/",
                "spec": {
                    "get": {
                        "summary": "List payments",
                        "parameters": [
                            {"name": "user_id", "in": "query", "required": False},
                            {"name": "borrowing_id", "in": "query", "required": False},
                            {"name": "kind", "in": "query", "required": False},
                        ],
                        "responses": {"200": {"description": "Payments list"}},
                    }
                },
            },
        ]
        return SwaggerDoc(title="library-service-api", version="1.0.0", endpoints=endpoints).as_dict()

    def _actor_from_token(self, token: str) -> User:
        return self.auth.authenticate(token)

    def register(self, username: str, password: str, is_admin: bool = False) -> Dict[str, Any]:
        user = self.auth.register(username=username, password=password, is_admin=is_admin)
        return {"id": user.id, "username": user.username, "is_admin": user.is_admin}

    def login(self, username: str, password: str, expires_in_seconds: int = 3600) -> Dict[str, Any]:
        token = self.auth.login(username=username, password=password, expires_in_seconds=expires_in_seconds)
        return {"access_token": token, "token_type": "Bearer", "expires_in": expires_in_seconds}

    def create_book(self, token: str, title: str, author: str, total_copies: int) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        book = self.library.create_book(actor=actor, title=title, author=author, total_copies=total_copies)
        return self._book_to_dict(book)

    def update_book(
        self,
        token: str,
        book_id: int,
        title: Optional[str] = None,
        author: Optional[str] = None,
        total_copies: Optional[int] = None,
    ) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        book = self.library.update_book(actor=actor, book_id=book_id, title=title, author=author, total_copies=total_copies)
        return self._book_to_dict(book)

    def delete_book(self, token: str, book_id: int) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        self.library.delete_book(actor=actor, book_id=book_id)
        return {"deleted": True}

    def list_books(self, token: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        books = self.library.list_books(actor=actor, filters=filters)
        return {"results": [self._book_to_dict(b) for b in books]}

    def borrow_book(self, token: str, book_id: int, expected_return_date: str) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        erd = date.fromisoformat(expected_return_date)
        borrowing, payment = self.library.borrow_book(actor=actor, book_id=book_id, expected_return_date=erd)
        return {"borrowing": self._borrowing_to_dict(borrowing), "payment": self._payment_to_dict(payment)}

    def return_borrowing(self, token: str, borrowing_id: int, actual_return_date: str) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        ard = date.fromisoformat(actual_return_date)
        borrowing, fine_payment = self.library.return_book(actor=actor, borrowing_id=borrowing_id, actual_return_date=ard)
        return {
            "borrowing": self._borrowing_to_dict(borrowing),
            "fine_payment": self._payment_to_dict(fine_payment) if fine_payment else None,
        }

    def list_borrowings(self, token: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        borrowings = self.library.list_borrowings(actor=actor, filters=filters)
        return {"results": [self._borrowing_to_dict(b) for b in borrowings]}

    def list_payments(self, token: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        actor = self._actor_from_token(token)
        payments = self.library.list_payments(actor=actor, filters=filters)
        return {"results": [self._payment_to_dict(p) for p in payments]}

    @staticmethod
    def _book_to_dict(book: Book) -> Dict[str, Any]:
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
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


__all__ = [
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "JWTService",
    "PasswordHasher",
    "User",
    "Book",
    "Borrowing",
    "Payment",
    "InMemoryDB",
    "AuthService",
    "LibraryService",
    "SwaggerDoc",
    "LibraryServiceAPI",
]