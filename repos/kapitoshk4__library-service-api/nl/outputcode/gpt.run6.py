from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _to_decimal(value: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _json_dumps(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _json_loads(data: Union[str, bytes]) -> Any:
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    if not data:
        return None
    return json.loads(data)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


class APIError(Exception):
    def __init__(self, status: int, message: str, code: str = "error"):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code

    def to_response(self) -> "Response":
        return Response(
            status=self.status,
            headers={"Content-Type": "application/json"},
            body=_json_dumps({"code": self.code, "message": self.message}),
        )


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    headers: Dict[str, str]
    query: Dict[str, List[str]]
    body: bytes

    @staticmethod
    def from_environ(environ: Dict[str, Any]) -> "Request":
        method = environ.get("REQUEST_METHOD", "GET").upper()
        raw_path = environ.get("PATH_INFO", "/")
        query_string = environ.get("QUERY_STRING", "")
        query = parse_qs(query_string, keep_blank_values=True)
        headers: Dict[str, str] = {}
        for k, v in environ.items():
            if k.startswith("HTTP_"):
                name = k[5:].replace("_", "-").title()
                headers[name] = v
        if "CONTENT_TYPE" in environ:
            headers["Content-Type"] = environ["CONTENT_TYPE"]
        if "CONTENT_LENGTH" in environ:
            headers["Content-Length"] = environ["CONTENT_LENGTH"]
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            length = 0
        body = b""
        if length > 0:
            body = environ["wsgi.input"].read(length)  # type: ignore[index]
        return Request(method=method, path=raw_path, headers=headers, query=query, body=body)


@dataclass(frozen=True)
class Response:
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def to_wsgi(self) -> Tuple[str, List[Tuple[str, str]], List[bytes]]:
        status_text = {
            200: "200 OK",
            201: "201 Created",
            204: "204 No Content",
            400: "400 Bad Request",
            401: "401 Unauthorized",
            403: "403 Forbidden",
            404: "404 Not Found",
            405: "405 Method Not Allowed",
            409: "409 Conflict",
            422: "422 Unprocessable Entity",
            500: "500 Internal Server Error",
        }.get(self.status, f"{self.status} Unknown")
        headers = dict(self.headers)
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        headers.setdefault("Cache-Control", "no-store")
        if self.body is not None:
            headers["Content-Length"] = str(len(self.body))
        return status_text, list(headers.items()), [self.body or b""]


class JWTService:
    def __init__(self, secret: str, issuer: str = "library-service-api", ttl_seconds: int = 3600):
        if not secret:
            raise ValueError("JWT secret must be non-empty")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._ttl_seconds = int(ttl_seconds)

    def issue(self, subject: str, claims: Dict[str, Any]) -> str:
        now = int(_utcnow().timestamp())
        payload = {
            "iss": self._issuer,
            "sub": subject,
            "iat": now,
            "exp": now + self._ttl_seconds,
        }
        payload.update(claims or {})
        header = {"alg": "HS256", "typ": "JWT"}
        signing_input = f"{_b64url_encode(_json_dumps(header))}.{_b64url_encode(_json_dumps(payload))}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return signing_input.decode("ascii") + "." + _b64url_encode(sig)

    def verify(self, token: str) -> Dict[str, Any]:
        if not token or token.count(".") != 2:
            raise APIError(401, "Invalid token", "invalid_token")
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        try:
            provided = _b64url_decode(sig_b64)
        except Exception:
            raise APIError(401, "Invalid token signature", "invalid_token")
        if not hmac.compare_digest(expected, provided):
            raise APIError(401, "Invalid token signature", "invalid_token")
        try:
            payload = _json_loads(_b64url_decode(payload_b64))
        except Exception:
            raise APIError(401, "Invalid token payload", "invalid_token")
        if not isinstance(payload, dict):
            raise APIError(401, "Invalid token payload", "invalid_token")
        now = int(_utcnow().timestamp())
        exp = payload.get("exp")
        if exp is None or not isinstance(exp, int):
            raise APIError(401, "Invalid token expiration", "invalid_token")
        if now >= exp:
            raise APIError(401, "Token expired", "token_expired")
        iss = payload.get("iss")
        if iss != self._issuer:
            raise APIError(401, "Invalid token issuer", "invalid_token")
        return payload


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    is_admin: bool = False
    created_at: datetime = field(default_factory=_utcnow)

    def verify_password(self, password: str) -> bool:
        return hmac.compare_digest(self.password_hash, User.hash_password(password))

    @staticmethod
    def hash_password(password: str) -> str:
        if password is None:
            password = ""
        salt = "library-service-api"
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


@dataclass
class Book:
    id: int
    title: str
    author: str
    total_copies: int
    available_copies: int
    daily_fee: Decimal
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.total_copies < 0:
            raise ValueError("total_copies must be >= 0")
        if self.available_copies < 0:
            raise ValueError("available_copies must be >= 0")
        if self.available_copies > self.total_copies:
            raise ValueError("available_copies must be <= total_copies")
        if self.daily_fee < Decimal("0"):
            raise ValueError("daily_fee must be >= 0")


@dataclass
class Borrowing:
    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    expected_return_at: datetime
    actual_return_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)

    def is_returned(self) -> bool:
        return self.actual_return_at is not None

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        now = now or _utcnow()
        if self.actual_return_at is not None:
            return self.actual_return_at > self.expected_return_at
        return now > self.expected_return_at


@dataclass
class Payment:
    id: int
    borrowing_id: int
    user_id: int
    amount: Decimal
    kind: str  # "BORROW" or "FINE"
    status: str  # "PENDING" or "PAID"
    created_at: datetime = field(default_factory=_utcnow)
    paid_at: Optional[datetime] = None

    def mark_paid(self) -> None:
        if self.status == "PAID":
            return
        self.status = "PAID"
        self.paid_at = _utcnow()


class InMemoryDB:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: Dict[int, User] = {}
        self._books: Dict[int, Book] = {}
        self._borrowings: Dict[int, Borrowing] = {}
        self._payments: Dict[int, Payment] = {}
        self._seq = {"users": 0, "books": 0, "borrowings": 0, "payments": 0}

    def _next_id(self, table: str) -> int:
        self._seq[table] += 1
        return self._seq[table]

    def create_user(self, username: str, password: str, is_admin: bool = False) -> User:
        username = (username or "").strip()
        if not username:
            raise APIError(422, "username is required", "validation_error")
        if any(u.username == username for u in self._users.values()):
            raise APIError(409, "username already exists", "conflict")
        if password is None or len(password) < 4:
            raise APIError(422, "password must be at least 4 characters", "validation_error")
        with self._lock:
            uid = self._next_id("users")
            user = User(id=uid, username=username, password_hash=User.hash_password(password), is_admin=is_admin)
            self._users[uid] = user
            return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def list_users(self) -> List[User]:
        return list(self._users.values())

    def create_book(self, title: str, author: str, total_copies: int, daily_fee: Decimal) -> Book:
        title = (title or "").strip()
        author = (author or "").strip()
        if not title:
            raise APIError(422, "title is required", "validation_error")
        if not author:
            raise APIError(422, "author is required", "validation_error")
        if total_copies is None or int(total_copies) < 0:
            raise APIError(422, "total_copies must be >= 0", "validation_error")
        daily_fee = daily_fee if daily_fee is not None else Decimal("0")
        if daily_fee < Decimal("0"):
            raise APIError(422, "daily_fee must be >= 0", "validation_error")
        with self._lock:
            bid = self._next_id("books")
            book = Book(
                id=bid,
                title=title,
                author=author,
                total_copies=int(total_copies),
                available_copies=int(total_copies),
                daily_fee=daily_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            )
            self._books[bid] = book
            return book

    def get_book(self, book_id: int) -> Optional[Book]:
        return self._books.get(book_id)

    def list_books(self) -> List[Book]:
        return list(self._books.values())

    def update_book(self, book_id: int, fields: Dict[str, Any]) -> Book:
        with self._lock:
            book = self._books.get(book_id)
            if not book:
                raise APIError(404, "book not found", "not_found")
            title = fields.get("title", book.title)
            author = fields.get("author", book.author)
            total_copies = fields.get("total_copies", book.total_copies)
            daily_fee = fields.get("daily_fee", book.daily_fee)
            title = (title or "").strip()
            author = (author or "").strip()
            if not title:
                raise APIError(422, "title is required", "validation_error")
            if not author:
                raise APIError(422, "author is required", "validation_error")
            total_copies = int(total_copies)
            if total_copies < 0:
                raise APIError(422, "total_copies must be >= 0", "validation_error")
            daily_fee = Decimal(str(daily_fee))
            if daily_fee < Decimal("0"):
                raise APIError(422, "daily_fee must be >= 0", "validation_error")
            borrowed_count = book.total_copies - book.available_copies
            if total_copies < borrowed_count:
                raise APIError(409, "total_copies cannot be less than borrowed copies", "conflict")
            book.total_copies = total_copies
            book.available_copies = total_copies - borrowed_count
            book.title = title
            book.author = author
            book.daily_fee = daily_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return book

    def create_borrowing(self, user_id: int, book_id: int, days: int) -> Borrowing:
        if days is None or int(days) <= 0:
            raise APIError(422, "days must be > 0", "validation_error")
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                raise APIError(404, "user not found", "not_found")
            book = self._books.get(book_id)
            if not book:
                raise APIError(404, "book not found", "not_found")
            if book.available_copies <= 0:
                raise APIError(409, "no available copies", "conflict")
            borrowed_at = _utcnow()
            expected_return_at = borrowed_at + timedelta(days=int(days))
            bid = self._next_id("borrowings")
            borrowing = Borrowing(
                id=bid,
                user_id=user_id,
                book_id=book_id,
                borrowed_at=borrowed_at,
                expected_return_at=expected_return_at,
            )
            self._borrowings[bid] = borrowing
            book.available_copies -= 1
            return borrowing

    def get_borrowing(self, borrowing_id: int) -> Optional[Borrowing]:
        return self._borrowings.get(borrowing_id)

    def list_borrowings(self) -> List[Borrowing]:
        return list(self._borrowings.values())

    def return_borrowing(self, borrowing_id: int) -> Borrowing:
        with self._lock:
            borrowing = self._borrowings.get(borrowing_id)
            if not borrowing:
                raise APIError(404, "borrowing not found", "not_found")
            if borrowing.actual_return_at is not None:
                raise APIError(409, "borrowing already returned", "conflict")
            borrowing.actual_return_at = _utcnow()
            book = self._books.get(borrowing.book_id)
            if book:
                book.available_copies += 1
                if book.available_copies > book.total_copies:
                    book.available_copies = book.total_copies
            return borrowing

    def create_payment(self, borrowing_id: int, user_id: int, amount: Decimal, kind: str) -> Payment:
        if kind not in {"BORROW", "FINE"}:
            raise APIError(422, "invalid payment kind", "validation_error")
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount <= Decimal("0"):
            raise APIError(422, "amount must be > 0", "validation_error")
        with self._lock:
            borrowing = self._borrowings.get(borrowing_id)
            if not borrowing:
                raise APIError(404, "borrowing not found", "not_found")
            if borrowing.user_id != user_id:
                raise APIError(403, "forbidden", "forbidden")
            pid = self._next_id("payments")
            payment = Payment(
                id=pid,
                borrowing_id=borrowing_id,
                user_id=user_id,
                amount=amount,
                kind=kind,
                status="PENDING",
            )
            self._payments[pid] = payment
            return payment

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def list_payments(self) -> List[Payment]:
        return list(self._payments.values())

    def mark_payment_paid(self, payment_id: int, user_id: int, is_admin: bool) -> Payment:
        with self._lock:
            payment = self._payments.get(payment_id)
            if not payment:
                raise APIError(404, "payment not found", "not_found")
            if not is_admin and payment.user_id != user_id:
                raise APIError(403, "forbidden", "forbidden")
            payment.mark_paid()
            return payment

    def find_payments_for_borrowing(self, borrowing_id: int) -> List[Payment]:
        return [p for p in self._payments.values() if p.borrowing_id == borrowing_id]


class LibraryService:
    def __init__(self, db: InMemoryDB, fine_multiplier: Decimal = Decimal("2.0")) -> None:
        self._db = db
        self._fine_multiplier = Decimal(str(fine_multiplier))

    def compute_borrow_fee(self, borrowing: Borrowing) -> Decimal:
        book = self._db.get_book(borrowing.book_id)
        if not book:
            raise APIError(404, "book not found", "not_found")
        days = max(1, int((borrowing.expected_return_at - borrowing.borrowed_at).total_seconds() // 86400))
        return (book.daily_fee * Decimal(days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def compute_fine(self, borrowing: Borrowing) -> Decimal:
        book = self._db.get_book(borrowing.book_id)
        if not book:
            raise APIError(404, "book not found", "not_found")
        if borrowing.actual_return_at is None:
            raise APIError(409, "borrowing not returned yet", "conflict")
        overdue_seconds = (borrowing.actual_return_at - borrowing.expected_return_at).total_seconds()
        if overdue_seconds <= 0:
            return Decimal("0.00")
        overdue_days = int((overdue_seconds + 86399) // 86400)
        fine = book.daily_fee * Decimal(overdue_days) * self._fine_multiplier
        return fine.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def ensure_borrow_payment(self, borrowing: Borrowing, user_id: int) -> Payment:
        existing = [p for p in self._db.find_payments_for_borrowing(borrowing.id) if p.kind == "BORROW"]
        if existing:
            return existing[0]
        amount = self.compute_borrow_fee(borrowing)
        return self._db.create_payment(borrowing.id, user_id, amount, "BORROW")

    def ensure_fine_payment(self, borrowing: Borrowing, user_id: int) -> Optional[Payment]:
        if borrowing.actual_return_at is None:
            raise APIError(409, "borrowing not returned yet", "conflict")
        fine_amount = self.compute_fine(borrowing)
        if fine_amount <= Decimal("0"):
            return None
        existing = [p for p in self._db.find_payments_for_borrowing(borrowing.id) if p.kind == "FINE"]
        if existing:
            return existing[0]
        return self._db.create_payment(borrowing.id, user_id, fine_amount, "FINE")


class Router:
    def __init__(self) -> None:
        self._routes: Dict[Tuple[str, str], Any] = {}

    def add(self, method: str, path: str, handler: Any) -> None:
        self._routes[(method.upper(), path)] = handler

    def match(self, method: str, path: str) -> Any:
        key = (method.upper(), path)
        if key in self._routes:
            return self._routes[key], {}
        for (m, p), h in self._routes.items():
            if m != method.upper():
                continue
            if "{" not in p:
                continue
            parts_p = p.strip("/").split("/")
            parts_a = path.strip("/").split("/")
            if len(parts_p) != len(parts_a):
                continue
            params: Dict[str, str] = {}
            ok = True
            for pp, pa in zip(parts_p, parts_a):
                if pp.startswith("{") and pp.endswith("}"):
                    params[pp[1:-1]] = pa
                elif pp != pa:
                    ok = False
                    break
            if ok:
                return h, params
        raise APIError(404, "not found", "not_found")


class App:
    def __init__(self) -> None:
        secret = os.environ.get("JWT_SECRET", "dev-secret")
        self._jwt = JWTService(secret=secret)
        self._db = InMemoryDB()
        self._service = LibraryService(self._db)
        self._router = Router()
        self._register_routes()
        self._ensure_default_admin()

    def _ensure_default_admin(self) -> None:
        if not self._db.get_user_by_username("admin"):
            self._db.create_user("admin", "admin", is_admin=True)

    def _register_routes(self) -> None:
        # Auth
        self._router.add("POST", "/api/v1/auth/register/", self._auth_register)
        self._router.add("POST", "/api/v1/auth/login/", self._auth_login)

        # Books
        self._router.add("GET", "/api/v1/books/", self._books_list)
        self._router.add("POST", "/api/v1/books/", self._books_create)
        self._router.add("GET", "/api/v1/books/{id}/", self._books_get)
        self._router.add("PATCH", "/api/v1/books/{id}/", self._books_patch)

        # Borrowings
        self._router.add("GET", "/api/v1/borrowings/", self._borrowings_list)
        self._router.add("POST", "/api/v1/borrowings/", self._borrowings_create)
        self._router.add("GET", "/api/v1/borrowings/{id}/", self._borrowings_get)
        self._router.add("POST", "/api/v1/borrowings/{id}/return/", self._borrowings_return)

        # Payments
        self._router.add("GET", "/api/v1/payments/", self._payments_list)
        self._router.add("POST", "/api/v1/payments/", self._payments_create)
        self._router.add("POST", "/api/v1/payments/{id}/pay/", self._payments_pay)

        # Admin + Docs placeholders
        self._router.add("GET", "/admin/", self._admin)
        self._router.add("GET", "/api/v1/doc/swagger/", self._swagger)

    def __call__(self, environ: Dict[str, Any], start_response: Any) -> List[bytes]:
        try:
            req = Request.from_environ(environ)
            resp = self._handle(req)
        except APIError as e:
            resp = e.to_response()
        except Exception:
            resp = Response(
                status=500,
                headers={"Content-Type": "application/json"},
                body=_json_dumps({"code": "server_error", "message": "Internal server error"}),
            )
        status, headers, body_iter = resp.to_wsgi()
        start_response(status, headers)
        return body_iter

    def _handle(self, req: Request) -> Response:
        if not req.path.endswith("/"):
            req = Request(method=req.method, path=req.path + "/", headers=req.headers, query=req.query, body=req.body)
        handler, params = self._router.match(req.method, req.path)
        return handler(req, params)

    def _parse_json_body(self, req: Request) -> Dict[str, Any]:
        ct = (req.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if req.body and ct not in {"application/json", ""}:
            raise APIError(400, "Unsupported Content-Type", "bad_request")
        data = _json_loads(req.body or b"{}")
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise APIError(400, "JSON body must be an object", "bad_request")
        return data

    def _auth_user(self, req: Request) -> Tuple[User, Dict[str, Any]]:
        auth = req.headers.get("Authorization") or req.headers.get("authorization") or ""
        if not auth.startswith("Bearer "):
            raise APIError(401, "Authentication required", "unauthorized")
        token = auth[len("Bearer ") :].strip()
        payload = self._jwt.verify(token)
        sub = payload.get("sub")
        if not sub:
            raise APIError(401, "Invalid token subject", "invalid_token")
        uid = _to_int(sub)
        if uid is None:
            raise APIError(401, "Invalid token subject", "invalid_token")
        user = self._db.get_user(uid)
        if not user:
            raise APIError(401, "User not found", "unauthorized")
        return user, payload

    def _require_admin(self, user: User) -> None:
        if not user.is_admin:
            raise APIError(403, "Admin required", "forbidden")

    def _serialize_user(self, u: User) -> Dict[str, Any]:
        return {"id": u.id, "username": u.username, "is_admin": u.is_admin, "created_at": u.created_at.isoformat()}

    def _serialize_book(self, b: Book) -> Dict[str, Any]:
        return {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "total_copies": b.total_copies,
            "available_copies": b.available_copies,
            "daily_fee": str(b.daily_fee),
            "created_at": b.created_at.isoformat(),
        }

    def _serialize_borrowing(self, br: Borrowing) -> Dict[str, Any]:
        return {
            "id": br.id,
            "user_id": br.user_id,
            "book_id": br.book_id,
            "borrowed_at": br.borrowed_at.isoformat(),
            "expected_return_at": br.expected_return_at.isoformat(),
            "actual_return_at": br.actual_return_at.isoformat() if br.actual_return_at else None,
            "created_at": br.created_at.isoformat(),
        }

    def _serialize_payment(self, p: Payment) -> Dict[str, Any]:
        return {
            "id": p.id,
            "borrowing_id": p.borrowing_id,
            "user_id": p.user_id,
            "amount": str(p.amount),
            "kind": p.kind,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        }

    # Auth endpoints
    def _auth_register(self, req: Request, params: Dict[str, str]) -> Response:
        data = self._parse_json_body(req)
        username = data.get("username")
        password = data.get("password")
        user = self._db.create_user(str(username or ""), str(password or ""), is_admin=False)
        token = self._jwt.issue(str(user.id), {"is_admin": user.is_admin, "username": user.username})
        return Response(
            status=201,
            headers={"Content-Type": "application/json"},
            body=_json_dumps({"user": self._serialize_user(user), "token": token}),
        )

    def _auth_login(self, req: Request, params: Dict[str, str]) -> Response:
        data = self._parse_json_body(req)
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        user = self._db.get_user_by_username(username)
        if not user or not user.verify_password(str(password)):
            raise APIError(401, "Invalid credentials", "unauthorized")
        token = self._jwt.issue(str(user.id), {"is_admin": user.is_admin, "username": user.username})
        return Response(
            status=200,
            headers={"Content-Type": "application/json"},
            body=_json_dumps({"user": self._serialize_user(user), "token": token}),
        )

    # Books endpoints
    def _books_list(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        _ = user
        books = self._db.list_books()
        q = {k: (v[0] if v else "") for k, v in req.query.items()}
        title = (q.get("title") or "").strip().lower()
        author = (q.get("author") or "").strip().lower()
        available = _to_bool(q.get("available"))
        if title:
            books = [b for b in books if title in b.title.lower()]
        if author:
            books = [b for b in books if author in b.author.lower()]
        if available is True:
            books = [b for b in books if b.available_copies > 0]
        if available is False:
            books = [b for b in books if b.available_copies <= 0]
        return Response(body=_json_dumps({"results": [self._serialize_book(b) for b in books]}))

    def _books_create(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        self._require_admin(user)
        data = self._parse_json_body(req)
        title = data.get("title")
        author = data.get("author")
        total_copies = _to_int(data.get("total_copies"))
        daily_fee = _to_decimal(data.get("daily_fee"), Decimal("0"))
        if total_copies is None:
            raise APIError(422, "total_copies is required", "validation_error")
        if daily_fee is None:
            raise APIError(422, "daily_fee is required", "validation_error")
        book = self._db.create_book(str(title or ""), str(author or ""), total_copies, daily_fee)
        return Response(status=201, body=_json_dumps(self._serialize_book(book)))

    def _books_get(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        _ = user
        book_id = _to_int(params.get("id"))
        if book_id is None:
            raise APIError(404, "book not found", "not_found")
        book = self._db.get_book(book_id)
        if not book:
            raise APIError(404, "book not found", "not_found")
        return Response(body=_json_dumps(self._serialize_book(book)))

    def _books_patch(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        self._require_admin(user)
        book_id = _to_int(params.get("id"))
        if book_id is None:
            raise APIError(404, "book not found", "not_found")
        data = self._parse_json_body(req)
        fields: Dict[str, Any] = {}
        for k in ("title", "author", "total_copies", "daily_fee"):
            if k in data:
                fields[k] = data[k]
        book = self._db.update_book(book_id, fields)
        return Response(body=_json_dumps(self._serialize_book(book)))

    # Borrowings endpoints (with filtering by actual_return_date and users)
    def _borrowings_list(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        borrowings = self._db.list_borrowings()
        q = {k: (v[0] if v else "") for k, v in req.query.items()}

        user_filter = _to_int(q.get("user"))
        actual_returned = _to_bool(q.get("actual_returned"))
        actual_return_date = (q.get("actual_return_date") or "").strip()

        if not user.is_admin:
            borrowings = [b for b in borrowings if b.user_id == user.id]
        else:
            if user_filter is not None:
                borrowings = [b for b in borrowings if b.user_id == user_filter]

        if actual_returned is True:
            borrowings = [b for b in borrowings if b.actual_return_at is not None]
        if actual_returned is False:
            borrowings = [b for b in borrowings if b.actual_return_at is None]

        if actual_return_date:
            try:
                d = datetime.fromisoformat(actual_return_date).date()
            except Exception:
                raise APIError(422, "actual_return_date must be ISO format date or datetime", "validation_error")
            borrowings = [
                b for b in borrowings if b.actual_return_at is not None and b.actual_return_at.date() == d
            ]

        return Response(body=_json_dumps({"results": [self._serialize_borrowing(b) for b in borrowings]}))

    def _borrowings_create(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        data = self._parse_json_body(req)
        book_id = _to_int(data.get("book_id"))
        days = _to_int(data.get("days"))
        if book_id is None:
            raise APIError(422, "book_id is required", "validation_error")
        if days is None:
            raise APIError(422, "days is required", "validation_error")
        borrowing = self._db.create_borrowing(user.id, book_id, days)
        borrow_payment = self._service.ensure_borrow_payment(borrowing, user.id)
        return Response(
            status=201,
            body=_json_dumps({"borrowing": self._serialize_borrowing(borrowing), "payment": self._serialize_payment(borrow_payment)}),
        )

    def _borrowings_get(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        borrowing_id = _to_int(params.get("id"))
        if borrowing_id is None:
            raise APIError(404, "borrowing not found", "not_found")
        borrowing = self._db.get_borrowing(borrowing_id)
        if not borrowing:
            raise APIError(404, "borrowing not found", "not_found")
        if not user.is_admin and borrowing.user_id != user.id:
            raise APIError(403, "forbidden", "forbidden")
        payments = self._db.find_payments_for_borrowing(borrowing.id)
        return Response(
            body=_json_dumps(
                {"borrowing": self._serialize_borrowing(borrowing), "payments": [self._serialize_payment(p) for p in payments]}
            )
        )

    def _borrowings_return(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        borrowing_id = _to_int(params.get("id"))
        if borrowing_id is None:
            raise APIError(404, "borrowing not found", "not_found")
        borrowing = self._db.get_borrowing(borrowing_id)
        if not borrowing:
            raise APIError(404, "borrowing not found", "not_found")
        if not user.is_admin and borrowing.user_id != user.id:
            raise APIError(403, "forbidden", "forbidden")
        borrowing = self._db.return_borrowing(borrowing_id)
        fine_payment = self._service.ensure_fine_payment(borrowing, borrowing.user_id)
        payload: Dict[str, Any] = {"borrowing": self._serialize_borrowing(borrowing)}
        if fine_payment is not None:
            payload["fine_payment"] = self._serialize_payment(fine_payment)
        return Response(body=_json_dumps(payload))

    # Payments endpoints
    def _payments_list(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        payments = self._db.list_payments()
        q = {k: (v[0] if v else "") for k, v in req.query.items()}
        borrowing_filter = _to_int(q.get("borrowing"))
        status_filter = (q.get("status") or "").strip().upper()
        kind_filter = (q.get("kind") or "").strip().upper()

        if not user.is_admin:
            payments = [p for p in payments if p.user_id == user.id]
        if borrowing_filter is not None:
            payments = [p for p in payments if p.borrowing_id == borrowing_filter]
        if status_filter in {"PENDING", "PAID"}:
            payments = [p for p in payments if p.status == status_filter]
        if kind_filter in {"BORROW", "FINE"}:
            payments = [p for p in payments if p.kind == kind_filter]

        return Response(body=_json_dumps({"results": [self._serialize_payment(p) for p in payments]}))

    def _payments_create(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        data = self._parse_json_body(req)
        borrowing_id = _to_int(data.get("borrowing_id"))
        kind = (data.get("kind") or "").strip().upper()
        if borrowing_id is None:
            raise APIError(422, "borrowing_id is required", "validation_error")
        borrowing = self._db.get_borrowing(borrowing_id)
        if not borrowing:
            raise APIError(404, "borrowing not found", "not_found")
        if not user.is_admin and borrowing.user_id != user.id:
            raise APIError(403, "forbidden", "forbidden")

        if kind == "BORROW":
            payment = self._service.ensure_borrow_payment(borrowing, borrowing.user_id)
        elif kind == "FINE":
            if borrowing.actual_return_at is None:
                raise APIError(409, "borrowing not returned yet", "conflict")
            payment = self._service.ensure_fine_payment(borrowing, borrowing.user_id)
            if payment is None:
                raise APIError(409, "no fine due", "conflict")
        else:
            raise APIError(422, "kind must be BORROW or FINE", "validation_error")

        return Response(status=201, body=_json_dumps(self._serialize_payment(payment)))

    def _payments_pay(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        payment_id = _to_int(params.get("id"))
        if payment_id is None:
            raise APIError(404, "payment not found", "not_found")
        payment = self._db.mark_payment_paid(payment_id, user.id, user.is_admin)
        return Response(body=_json_dumps(self._serialize_payment(payment)))

    # Admin + Swagger endpoints
    def _admin(self, req: Request, params: Dict[str, str]) -> Response:
        user, _ = self._auth_user(req)
        self._require_admin(user)
        users = [self._serialize_user(u) for u in self._db.list_users()]
        books = [self._serialize_book(b) for b in self._db.list_books()]
        borrowings = [self._serialize_borrowing(b) for b in self._db.list_borrowings()]
        payments = [self._serialize_payment(p) for p in self._db.list_payments()]
        return Response(
            headers={"Content-Type": "application/json"},
            body=_json_dumps({"users": users, "books": books, "borrowings": borrowings, "payments": payments}),
        )

    def _swagger(self, req: Request, params: Dict[str, str]) -> Response:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "library-service-api", "version": "1.0.0"},
            "paths": {
                "/api/v1/auth/register/": {"post": {"summary": "Register", "security": []}},
                "/api/v1/auth/login/": {"post": {"summary": "Login", "security": []}},
                "/api/v1/books/": {
                    "get": {
                        "summary": "List books",
                        "parameters": [
                            {"name": "title", "in": "query", "schema": {"type": "string"}},
                            {"name": "author", "in": "query", "schema": {"type": "string"}},
                            {"name": "available", "in": "query", "schema": {"type": "boolean"}},
                        ],
                    },
                    "post": {"summary": "Create book (admin)"},
                },
                "/api/v1/books/{id}/": {"get": {"summary": "Get book"}, "patch": {"summary": "Update book (admin)"}},
                "/api/v1/borrowings/": {
                    "get": {
                        "summary": "List borrowings",
                        "parameters": [
                            {"name": "actual_return_date", "in": "query", "schema": {"type": "string"}},
                            {"name": "actual_returned", "in": "query", "schema": {"type": "boolean"}},
                            {"name": "user", "in": "query", "schema": {"type": "integer"}, "description": "Admin only"},
                        ],
                    },
                    "post": {"summary": "Create borrowing"},
                },
                "/api/v1/borrowings/{id}/": {"get": {"summary": "Get borrowing"}},
                "/api/v1/borrowings/{id}/return/": {"post": {"summary": "Return borrowing"}},
                "/api/v1/payments/": {
                    "get": {
                        "summary": "List payments",
                        "parameters": [
                            {"name": "borrowing", "in": "query", "schema": {"type": "integer"}},
                            {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["PENDING", "PAID"]}},
                            {"name": "kind", "in": "query", "schema": {"type": "string", "enum": ["BORROW", "FINE"]}},
                        ],
                    },
                    "post": {"summary": "Create payment for borrowing (BORROW/FINE)"},
                },
                "/api/v1/payments/{id}/pay/": {"post": {"summary": "Mark payment paid"}},
                "/admin/": {"get": {"summary": "Admin panel (JSON)"}},
                "/api/v1/doc/swagger/": {"get": {"summary": "Swagger spec (JSON)"}},
            },
            "components": {
                "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}
            },
            "security": [{"bearerAuth": []}],
        }
        return Response(headers={"Content-Type": "application/json"}, body=_json_dumps(spec))


app = App()


def main() -> None:
    from wsgiref.simple_server import make_server

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    with make_server(host, port, app) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()