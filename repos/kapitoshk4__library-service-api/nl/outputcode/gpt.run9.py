from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import base64
import hashlib
import hmac
import json
import secrets
import threading
import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise TypeError("Invalid decimal value")


def _money(value: Any) -> Decimal:
    d = _to_decimal(value)
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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


class PaymentError(DomainError):
    pass


class JWTService:
    def __init__(self, secret: str, issuer: str = "library-service-api", ttl_seconds: int = 3600) -> None:
        if not secret:
            raise ValidationError("JWT secret is required")
        if ttl_seconds <= 0:
            raise ValidationError("ttl_seconds must be positive")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        pad = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode((data + pad).encode("ascii"))

    def _sign(self, signing_input: bytes) -> str:
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return self._b64url_encode(sig)

    def issue(self, subject: str, is_admin: bool) -> str:
        if not subject:
            raise ValidationError("subject is required")
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(_utcnow().timestamp())
        payload = {
            "iss": self._issuer,
            "sub": subject,
            "iat": now,
            "exp": now + self._ttl_seconds,
            "admin": bool(is_admin),
            "jti": uuid.uuid4().hex,
        }
        header_b64 = self._b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = self._b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature_b64 = self._sign(signing_input)
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def verify(self, token: str) -> Dict[str, Any]:
        if not token:
            raise AuthenticationError("Missing token")
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = self._sign(signing_input)
        if not hmac.compare_digest(expected_sig, sig_b64):
            raise AuthenticationError("Invalid token signature")
        try:
            payload = json.loads(self._b64url_decode(payload_b64).decode("utf-8"))
        except Exception as e:
            raise AuthenticationError("Invalid token payload") from e
        if payload.get("iss") != self._issuer:
            raise AuthenticationError("Invalid token issuer")
        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise AuthenticationError("Invalid token exp")
        if int(_utcnow().timestamp()) >= exp:
            raise AuthenticationError("Token expired")
        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise AuthenticationError("Invalid token subject")
        if "admin" not in payload:
            raise AuthenticationError("Invalid token admin claim")
        return payload


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
    status: str  # "PENDING" or "PAID"
    created_at: datetime
    paid_at: Optional[datetime]


class PasswordHasher:
    def __init__(self, pepper: str = "") -> None:
        self._pepper = pepper.encode("utf-8")

    def hash(self, password: str) -> str:
        if not isinstance(password, str) or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8") + self._pepper, salt, 200_000)
        return f"pbkdf2_sha256${base64.b64encode(salt).decode('ascii')}${base64.b64encode(dk).decode('ascii')}"

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            algo, salt_b64, dk_b64 = password_hash.split("$", 2)
            if algo != "pbkdf2_sha256":
                return False
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(dk_b64.encode("ascii"))
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8") + self._pepper, salt, 200_000)
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False


class InMemoryDB:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.users: Dict[str, User] = {}
        self.books: Dict[str, Book] = {}
        self.borrowings: Dict[str, Borrowing] = {}
        self.payments: Dict[str, Payment] = {}
        self._username_index: Dict[str, str] = {}

    def _new_id(self) -> str:
        return uuid.uuid4().hex

    def create_user(self, username: str, password_hash: str, is_admin: bool) -> User:
        with self._lock:
            if username in self._username_index:
                raise ConflictError("Username already exists")
            uid = self._new_id()
            user = User(id=uid, username=username, password_hash=password_hash, is_admin=is_admin)
            self.users[uid] = user
            self._username_index[username] = uid
            return user

    def get_user_by_username(self, username: str) -> User:
        with self._lock:
            uid = self._username_index.get(username)
            if not uid:
                raise NotFoundError("User not found")
            return self.users[uid]

    def get_user(self, user_id: str) -> User:
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                raise NotFoundError("User not found")
            return user

    def create_book(self, title: str, author: str, total_copies: int) -> Book:
        if not title or not author:
            raise ValidationError("Title and author are required")
        if total_copies <= 0:
            raise ValidationError("total_copies must be positive")
        with self._lock:
            bid = self._new_id()
            book = Book(id=bid, title=title, author=author, total_copies=total_copies, available_copies=total_copies)
            self.books[bid] = book
            return book

    def get_book(self, book_id: str) -> Book:
        with self._lock:
            book = self.books.get(book_id)
            if not book:
                raise NotFoundError("Book not found")
            return book

    def update_book(self, book: Book) -> None:
        with self._lock:
            if book.id not in self.books:
                raise NotFoundError("Book not found")
            self.books[book.id] = book

    def create_borrowing(self, user_id: str, book_id: str, borrowed_at: datetime, due_at: datetime) -> Borrowing:
        with self._lock:
            if user_id not in self.users:
                raise NotFoundError("User not found")
            if book_id not in self.books:
                raise NotFoundError("Book not found")
            bor_id = self._new_id()
            borrowing = Borrowing(
                id=bor_id,
                user_id=user_id,
                book_id=book_id,
                borrowed_at=borrowed_at,
                due_at=due_at,
                actual_return_at=None,
            )
            self.borrowings[bor_id] = borrowing
            return borrowing

    def get_borrowing(self, borrowing_id: str) -> Borrowing:
        with self._lock:
            b = self.borrowings.get(borrowing_id)
            if not b:
                raise NotFoundError("Borrowing not found")
            return b

    def update_borrowing(self, borrowing: Borrowing) -> None:
        with self._lock:
            if borrowing.id not in self.borrowings:
                raise NotFoundError("Borrowing not found")
            self.borrowings[borrowing.id] = borrowing

    def list_borrowings(self) -> List[Borrowing]:
        with self._lock:
            return list(self.borrowings.values())

    def create_payment(self, borrowing_id: str, user_id: str, amount: Decimal, kind: str) -> Payment:
        if kind not in ("BORROW", "FINE"):
            raise ValidationError("Invalid payment kind")
        amount = _money(amount)
        if amount <= Decimal("0.00"):
            raise ValidationError("Payment amount must be positive")
        with self._lock:
            if borrowing_id not in self.borrowings:
                raise NotFoundError("Borrowing not found")
            if user_id not in self.users:
                raise NotFoundError("User not found")
            pid = self._new_id()
            p = Payment(
                id=pid,
                borrowing_id=borrowing_id,
                user_id=user_id,
                amount=amount,
                kind=kind,
                status="PENDING",
                created_at=_utcnow(),
                paid_at=None,
            )
            self.payments[pid] = p
            return p

    def get_payment(self, payment_id: str) -> Payment:
        with self._lock:
            p = self.payments.get(payment_id)
            if not p:
                raise NotFoundError("Payment not found")
            return p

    def update_payment(self, payment: Payment) -> None:
        with self._lock:
            if payment.id not in self.payments:
                raise NotFoundError("Payment not found")
            self.payments[payment.id] = payment

    def list_payments(self) -> List[Payment]:
        with self._lock:
            return list(self.payments.values())


class LibraryService:
    def __init__(
        self,
        db: InMemoryDB,
        jwt: JWTService,
        hasher: PasswordHasher,
        borrow_fee: Decimal = Decimal("2.00"),
        fine_per_day: Decimal = Decimal("1.00"),
        default_borrow_days: int = 14,
    ) -> None:
        if default_borrow_days <= 0:
            raise ValidationError("default_borrow_days must be positive")
        self._db = db
        self._jwt = jwt
        self._hasher = hasher
        self._borrow_fee = _money(borrow_fee)
        self._fine_per_day = _money(fine_per_day)
        self._default_borrow_days = default_borrow_days

    def register(self, username: str, password: str, is_admin: bool = False) -> User:
        if not username or not isinstance(username, str):
            raise ValidationError("username is required")
        password_hash = self._hasher.hash(password)
        return self._db.create_user(username=username, password_hash=password_hash, is_admin=is_admin)

    def login(self, username: str, password: str) -> str:
        user = self._db.get_user_by_username(username)
        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        return self._jwt.issue(subject=user.id, is_admin=user.is_admin)

    def _auth(self, token: str) -> User:
        payload = self._jwt.verify(token)
        return self._db.get_user(payload["sub"])

    def _require_admin(self, user: User) -> None:
        if not user.is_admin:
            raise AuthorizationError("Admin privileges required")

    def admin_panel_path(self) -> str:
        return "/admin/"

    def swagger_docs_path(self) -> str:
        return "/api/v1/doc/swagger/"

    def create_book(self, token: str, title: str, author: str, total_copies: int) -> Book:
        user = self._auth(token)
        self._require_admin(user)
        return self._db.create_book(title=title, author=author, total_copies=total_copies)

    def list_books(self, token: str) -> List[Book]:
        self._auth(token)
        return list(self._db.books.values())

    def borrow_book(self, token: str, book_id: str, borrow_days: Optional[int] = None) -> Tuple[Borrowing, Payment]:
        user = self._auth(token)
        if borrow_days is None:
            borrow_days = self._default_borrow_days
        if borrow_days <= 0:
            raise ValidationError("borrow_days must be positive")

        with self._db._lock:
            book = self._db.get_book(book_id)
            if book.available_copies <= 0:
                raise ConflictError("No available copies")
            book = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=book.total_copies,
                available_copies=book.available_copies - 1,
            )
            self._db.update_book(book)

            borrowed_at = _utcnow()
            due_at = borrowed_at + timedelta(days=borrow_days)
            borrowing = self._db.create_borrowing(user_id=user.id, book_id=book_id, borrowed_at=borrowed_at, due_at=due_at)

            payment = self._db.create_payment(
                borrowing_id=borrowing.id,
                user_id=user.id,
                amount=self._borrow_fee,
                kind="BORROW",
            )
            return borrowing, payment

    def return_book(self, token: str, borrowing_id: str) -> Tuple[Borrowing, Optional[Payment]]:
        user = self._auth(token)
        with self._db._lock:
            borrowing = self._db.get_borrowing(borrowing_id)
            if borrowing.user_id != user.id and not user.is_admin:
                raise AuthorizationError("Not allowed to return this borrowing")
            if borrowing.actual_return_at is not None:
                raise ConflictError("Borrowing already returned")

            returned_at = _utcnow()
            borrowing = Borrowing(
                id=borrowing.id,
                user_id=borrowing.user_id,
                book_id=borrowing.book_id,
                borrowed_at=borrowing.borrowed_at,
                due_at=borrowing.due_at,
                actual_return_at=returned_at,
            )
            self._db.update_borrowing(borrowing)

            book = self._db.get_book(borrowing.book_id)
            if book.available_copies >= book.total_copies:
                raise ConflictError("Book inventory inconsistency")
            book = Book(
                id=book.id,
                title=book.title,
                author=book.author,
                total_copies=book.total_copies,
                available_copies=book.available_copies + 1,
            )
            self._db.update_book(book)

            fine_payment: Optional[Payment] = None
            if returned_at > borrowing.due_at:
                overdue_days = (returned_at.date() - borrowing.due_at.date()).days
                if overdue_days > 0:
                    fine_amount = _money(self._fine_per_day * Decimal(overdue_days))
                    fine_payment = self._db.create_payment(
                        borrowing_id=borrowing.id,
                        user_id=borrowing.user_id,
                        amount=fine_amount,
                        kind="FINE",
                    )
            return borrowing, fine_payment

    def list_borrowings(
        self,
        token: str,
        actual_return_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> List[Borrowing]:
        user = self._auth(token)
        borrowings = self._db.list_borrowings()

        if not user.is_admin:
            borrowings = [b for b in borrowings if b.user_id == user.id]

        if user_id is not None:
            if not user.is_admin and user_id != user.id:
                raise AuthorizationError("Not allowed to filter by other users")
            borrowings = [b for b in borrowings if b.user_id == user_id]

        if actual_return_date is not None:
            target_date = actual_return_date.date()
            borrowings = [
                b for b in borrowings if b.actual_return_at is not None and b.actual_return_at.date() == target_date
            ]

        borrowings.sort(key=lambda b: b.borrowed_at, reverse=True)
        return borrowings

    def list_payments(self, token: str, user_id: Optional[str] = None, borrowing_id: Optional[str] = None) -> List[Payment]:
        user = self._auth(token)
        payments = self._db.list_payments()

        if not user.is_admin:
            payments = [p for p in payments if p.user_id == user.id]

        if user_id is not None:
            if not user.is_admin and user_id != user.id:
                raise AuthorizationError("Not allowed to filter by other users")
            payments = [p for p in payments if p.user_id == user_id]

        if borrowing_id is not None:
            payments = [p for p in payments if p.borrowing_id == borrowing_id]

        payments.sort(key=lambda p: p.created_at, reverse=True)
        return payments

    def pay(self, token: str, payment_id: str) -> Payment:
        user = self._auth(token)
        with self._db._lock:
            payment = self._db.get_payment(payment_id)
            if payment.user_id != user.id and not user.is_admin:
                raise AuthorizationError("Not allowed to pay this payment")
            if payment.status == "PAID":
                raise ConflictError("Payment already paid")
            payment = Payment(
                id=payment.id,
                borrowing_id=payment.borrowing_id,
                user_id=payment.user_id,
                amount=payment.amount,
                kind=payment.kind,
                status="PAID",
                created_at=payment.created_at,
                paid_at=_utcnow(),
            )
            self._db.update_payment(payment)
            return payment


class Router:
    def __init__(self, service: LibraryService) -> None:
        self._svc = service

    def handle(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, body: Optional[Dict[str, Any]] = None,
               query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = headers or {}
        body = body or {}
        query = query or {}

        def token_from_headers() -> str:
            auth = headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return auth[len("Bearer "):].strip()
            return ""

        try:
            if method == "GET" and path == "/admin/":
                return {"status": 200, "data": {"path": self._svc.admin_panel_path()}}
            if method == "GET" and path == "/api/v1/doc/swagger/":
                return {"status": 200, "data": {"path": self._svc.swagger_docs_path()}}

            if method == "POST" and path == "/api/v1/auth/register":
                user = self._svc.register(
                    username=str(body.get("username", "")),
                    password=str(body.get("password", "")),
                    is_admin=bool(body.get("is_admin", False)),
                )
                return {"status": 201, "data": {"id": user.id, "username": user.username, "is_admin": user.is_admin}}

            if method == "POST" and path == "/api/v1/auth/login":
                token = self._svc.login(username=str(body.get("username", "")), password=str(body.get("password", "")))
                return {"status": 200, "data": {"access_token": token, "token_type": "Bearer"}}

            if method == "POST" and path == "/api/v1/books":
                book = self._svc.create_book(
                    token=token_from_headers(),
                    title=str(body.get("title", "")),
                    author=str(body.get("author", "")),
                    total_copies=int(body.get("total_copies", 0)),
                )
                return {"status": 201, "data": book.__dict__}

            if method == "GET" and path == "/api/v1/books":
                books = self._svc.list_books(token=token_from_headers())
                return {"status": 200, "data": [b.__dict__ for b in books]}

            if method == "POST" and path == "/api/v1/borrowings":
                borrowing, payment = self._svc.borrow_book(
                    token=token_from_headers(),
                    book_id=str(body.get("book_id", "")),
                    borrow_days=int(body["borrow_days"]) if "borrow_days" in body and body["borrow_days"] is not None else None,
                )
                return {
                    "status": 201,
                    "data": {
                        "borrowing": {
                            **borrowing.__dict__,
                            "borrowed_at": borrowing.borrowed_at.isoformat(),
                            "due_at": borrowing.due_at.isoformat(),
                            "actual_return_at": borrowing.actual_return_at.isoformat() if borrowing.actual_return_at else None,
                        },
                        "payment": {
                            **payment.__dict__,
                            "amount": str(payment.amount),
                            "created_at": payment.created_at.isoformat(),
                            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                        },
                    },
                }

            if method == "POST" and path.startswith("/api/v1/borrowings/") and path.endswith("/return"):
                borrowing_id = path.split("/")[4]
                borrowing, fine_payment = self._svc.return_book(token=token_from_headers(), borrowing_id=borrowing_id)
                data: Dict[str, Any] = {
                    "borrowing": {
                        **borrowing.__dict__,
                        "borrowed_at": borrowing.borrowed_at.isoformat(),
                        "due_at": borrowing.due_at.isoformat(),
                        "actual_return_at": borrowing.actual_return_at.isoformat() if borrowing.actual_return_at else None,
                    },
                    "fine_payment": None,
                }
                if fine_payment is not None:
                    data["fine_payment"] = {
                        **fine_payment.__dict__,
                        "amount": str(fine_payment.amount),
                        "created_at": fine_payment.created_at.isoformat(),
                        "paid_at": fine_payment.paid_at.isoformat() if fine_payment.paid_at else None,
                    }
                return {"status": 200, "data": data}

            if method == "GET" and path == "/api/v1/borrowings":
                actual_return_date = query.get("actual_return_date")
                parsed_date: Optional[datetime] = None
                if actual_return_date:
                    if isinstance(actual_return_date, datetime):
                        parsed_date = actual_return_date
                    else:
                        parsed_date = datetime.fromisoformat(str(actual_return_date))
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                uid = query.get("user_id")
                borrowings = self._svc.list_borrowings(
                    token=token_from_headers(),
                    actual_return_date=parsed_date,
                    user_id=str(uid) if uid is not None and str(uid) != "" else None,
                )
                return {
                    "status": 200,
                    "data": [
                        {
                            **b.__dict__,
                            "borrowed_at": b.borrowed_at.isoformat(),
                            "due_at": b.due_at.isoformat(),
                            "actual_return_at": b.actual_return_at.isoformat() if b.actual_return_at else None,
                        }
                        for b in borrowings
                    ],
                }

            if method == "GET" and path == "/api/v1/payments":
                uid = query.get("user_id")
                bid = query.get("borrowing_id")
                payments = self._svc.list_payments(
                    token=token_from_headers(),
                    user_id=str(uid) if uid is not None and str(uid) != "" else None,
                    borrowing_id=str(bid) if bid is not None and str(bid) != "" else None,
                )
                return {
                    "status": 200,
                    "data": [
                        {
                            **p.__dict__,
                            "amount": str(p.amount),
                            "created_at": p.created_at.isoformat(),
                            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                        }
                        for p in payments
                    ],
                }

            if method == "POST" and path.startswith("/api/v1/payments/") and path.endswith("/pay"):
                payment_id = path.split("/")[4]
                p = self._svc.pay(token=token_from_headers(), payment_id=payment_id)
                return {
                    "status": 200,
                    "data": {
                        **p.__dict__,
                        "amount": str(p.amount),
                        "created_at": p.created_at.isoformat(),
                        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                    },
                }

            raise NotFoundError("Endpoint not found")
        except DomainError as e:
            status = 400
            if isinstance(e, AuthenticationError):
                status = 401
            elif isinstance(e, AuthorizationError):
                status = 403
            elif isinstance(e, NotFoundError):
                status = 404
            elif isinstance(e, ConflictError):
                status = 409
            elif isinstance(e, PaymentError):
                status = 402
            return {"status": status, "error": {"type": e.__class__.__name__, "message": str(e)}}


def create_app(secret: str) -> Router:
    db = InMemoryDB()
    jwt = JWTService(secret=secret)
    hasher = PasswordHasher()
    svc = LibraryService(db=db, jwt=jwt, hasher=hasher)
    return Router(svc)