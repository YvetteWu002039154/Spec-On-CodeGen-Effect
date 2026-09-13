from __future__ import annotations

import base64
import dataclasses
import datetime as _dt
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, PositiveInt, condecimal, constr


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.timezone.utc)


def _to_date(dt: _dt.datetime) -> _dt.date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.date()


def _quantize_money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class JWTError(Exception):
    pass


class SimpleJWT:
    def __init__(self, secret: str, issuer: str = "library-service-api", ttl_seconds: int = 3600) -> None:
        if not secret:
            raise ValueError("secret must be non-empty")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._ttl_seconds = int(ttl_seconds)

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        pad = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode((data + pad).encode("ascii"))

    def encode(self, subject: str, claims: Dict[str, Any]) -> str:
        now = int(_utcnow().timestamp())
        payload = {
            "iss": self._issuer,
            "sub": subject,
            "iat": now,
            "exp": now + self._ttl_seconds,
            **claims,
        }
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self._b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_b64 = self._b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = self._b64url_encode(sig)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def decode(self, token: str) -> Dict[str, Any]:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError as e:
            raise JWTError("invalid token format") from e

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        actual_sig = self._b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise JWTError("invalid signature")

        payload = json.loads(self._b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("iss") != self._issuer:
            raise JWTError("invalid issuer")
        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise JWTError("invalid exp")
        if int(_utcnow().timestamp()) >= exp:
            raise JWTError("token expired")
        return payload


def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return base64.b64encode(dk).decode("ascii")


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password, salt), password_hash)


@dataclass(frozen=True)
class User:
    id: int
    username: str
    is_admin: bool
    password_salt: str
    password_hash: str


@dataclass
class Book:
    id: int
    title: str
    author: str
    total_copies: int
    available_copies: int

    def borrow_one(self) -> None:
        if self.available_copies <= 0:
            raise ValueError("no copies available")
        self.available_copies -= 1

    def return_one(self) -> None:
        if self.available_copies >= self.total_copies:
            raise ValueError("all copies already returned")
        self.available_copies += 1


@dataclass
class Borrowing:
    id: int
    user_id: int
    book_id: int
    borrowed_at: _dt.datetime
    due_date: _dt.date
    actual_return_date: Optional[_dt.date] = None

    def is_returned(self) -> bool:
        return self.actual_return_date is not None

    def mark_returned(self, return_date: _dt.date) -> None:
        if self.actual_return_date is not None:
            raise ValueError("already returned")
        self.actual_return_date = return_date

    def overdue_days(self, as_of: Optional[_dt.date] = None) -> int:
        if as_of is None:
            as_of = _to_date(_utcnow())
        end_date = self.actual_return_date or as_of
        if end_date <= self.due_date:
            return 0
        return (end_date - self.due_date).days


class PaymentStatus:
    PENDING = "PENDING"
    PAID = "PAID"


class PaymentType:
    BORROWING = "BORROWING"
    FINE = "FINE"


@dataclass
class Payment:
    id: int
    borrowing_id: int
    user_id: int
    amount: Decimal
    currency: str
    payment_type: str
    status: str
    created_at: _dt.datetime
    paid_at: Optional[_dt.datetime] = None

    def mark_paid(self) -> None:
        if self.status == PaymentStatus.PAID:
            raise ValueError("already paid")
        self.status = PaymentStatus.PAID
        self.paid_at = _utcnow()


class InMemoryDB:
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}
        self._books: Dict[int, Book] = {}
        self._borrowings: Dict[int, Borrowing] = {}
        self._payments: Dict[int, Payment] = {}

        self._user_id = 0
        self._book_id = 0
        self._borrowing_id = 0
        self._payment_id = 0

    def create_user(self, username: str, password: str, is_admin: bool) -> User:
        if any(u.username == username for u in self._users.values()):
            raise ValueError("username already exists")
        self._user_id += 1
        salt = secrets.token_hex(16)
        ph = _hash_password(password, salt)
        user = User(id=self._user_id, username=username, is_admin=is_admin, password_salt=salt, password_hash=ph)
        self._users[user.id] = user
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def create_book(self, title: str, author: str, total_copies: int) -> Book:
        if total_copies <= 0:
            raise ValueError("total_copies must be positive")
        self._book_id += 1
        book = Book(id=self._book_id, title=title, author=author, total_copies=total_copies, available_copies=total_copies)
        self._books[book.id] = book
        return book

    def list_books(self) -> List[Book]:
        return list(self._books.values())

    def get_book(self, book_id: int) -> Optional[Book]:
        return self._books.get(book_id)

    def update_book(self, book_id: int, title: Optional[str], author: Optional[str], total_copies: Optional[int]) -> Book:
        book = self._books.get(book_id)
        if not book:
            raise KeyError("book not found")
        if title is not None:
            book.title = title
        if author is not None:
            book.author = author
        if total_copies is not None:
            if total_copies <= 0:
                raise ValueError("total_copies must be positive")
            borrowed_out = book.total_copies - book.available_copies
            if total_copies < borrowed_out:
                raise ValueError("total_copies cannot be less than borrowed copies")
            book.total_copies = total_copies
            book.available_copies = total_copies - borrowed_out
        return book

    def delete_book(self, book_id: int) -> None:
        if book_id not in self._books:
            raise KeyError("book not found")
        del self._books[book_id]

    def create_borrowing(self, user_id: int, book_id: int, days: int) -> Borrowing:
        if days <= 0:
            raise ValueError("days must be positive")
        book = self._books.get(book_id)
        if not book:
            raise KeyError("book not found")
        book.borrow_one()
        self._borrowing_id += 1
        borrowed_at = _utcnow()
        due_date = _to_date(borrowed_at) + _dt.timedelta(days=days)
        borrowing = Borrowing(
            id=self._borrowing_id,
            user_id=user_id,
            book_id=book_id,
            borrowed_at=borrowed_at,
            due_date=due_date,
        )
        self._borrowings[borrowing.id] = borrowing
        return borrowing

    def get_borrowing(self, borrowing_id: int) -> Optional[Borrowing]:
        return self._borrowings.get(borrowing_id)

    def list_borrowings(self) -> List[Borrowing]:
        return list(self._borrowings.values())

    def return_borrowing(self, borrowing_id: int, return_date: _dt.date) -> Borrowing:
        borrowing = self._borrowings.get(borrowing_id)
        if not borrowing:
            raise KeyError("borrowing not found")
        if borrowing.actual_return_date is not None:
            raise ValueError("already returned")
        book = self._books.get(borrowing.book_id)
        if not book:
            raise KeyError("book not found")
        borrowing.mark_returned(return_date)
        book.return_one()
        return borrowing

    def create_payment(self, borrowing_id: int, user_id: int, amount: Decimal, currency: str, payment_type: str) -> Payment:
        if amount <= 0:
            raise ValueError("amount must be positive")
        if payment_type not in (PaymentType.BORROWING, PaymentType.FINE):
            raise ValueError("invalid payment_type")
        self._payment_id += 1
        payment = Payment(
            id=self._payment_id,
            borrowing_id=borrowing_id,
            user_id=user_id,
            amount=_quantize_money(amount),
            currency=currency,
            payment_type=payment_type,
            status=PaymentStatus.PENDING,
            created_at=_utcnow(),
        )
        self._payments[payment.id] = payment
        return payment

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def list_payments(self) -> List[Payment]:
        return list(self._payments.values())

    def find_payments_for_borrowing(self, borrowing_id: int) -> List[Payment]:
        return [p for p in self._payments.values() if p.borrowing_id == borrowing_id]

    def find_pending_payment(self, borrowing_id: int, payment_type: str) -> Optional[Payment]:
        for p in self._payments.values():
            if p.borrowing_id == borrowing_id and p.payment_type == payment_type and p.status == PaymentStatus.PENDING:
                return p
        return None


class LibraryService:
    def __init__(
        self,
        db: InMemoryDB,
        borrowing_fee: Decimal = Decimal("2.00"),
        fine_per_overdue_day: Decimal = Decimal("1.00"),
        currency: str = "USD",
        default_borrow_days: int = 14,
    ) -> None:
        self._db = db
        self._borrowing_fee = _quantize_money(Decimal(borrowing_fee))
        self._fine_per_overdue_day = _quantize_money(Decimal(fine_per_overdue_day))
        self._currency = currency
        self._default_borrow_days = int(default_borrow_days)

    @property
    def currency(self) -> str:
        return self._currency

    def create_borrowing(self, user_id: int, book_id: int, days: Optional[int] = None) -> Tuple[Borrowing, Payment]:
        if days is None:
            days = self._default_borrow_days
        borrowing = self._db.create_borrowing(user_id=user_id, book_id=book_id, days=days)
        payment = self._db.create_payment(
            borrowing_id=borrowing.id,
            user_id=user_id,
            amount=self._borrowing_fee,
            currency=self._currency,
            payment_type=PaymentType.BORROWING,
        )
        return borrowing, payment

    def return_borrowing(self, borrowing_id: int, return_date: Optional[_dt.date] = None) -> Tuple[Borrowing, Optional[Payment]]:
        if return_date is None:
            return_date = _to_date(_utcnow())
        borrowing = self._db.get_borrowing(borrowing_id)
        if not borrowing:
            raise KeyError("borrowing not found")
        borrowing = self._db.return_borrowing(borrowing_id, return_date=return_date)
        overdue = borrowing.overdue_days()
        if overdue <= 0:
            return borrowing, None
        existing = self._db.find_pending_payment(borrowing_id=borrowing.id, payment_type=PaymentType.FINE)
        if existing:
            return borrowing, existing
        fine_amount = _quantize_money(self._fine_per_overdue_day * Decimal(overdue))
        fine_payment = self._db.create_payment(
            borrowing_id=borrowing.id,
            user_id=borrowing.user_id,
            amount=fine_amount,
            currency=self._currency,
            payment_type=PaymentType.FINE,
        )
        return borrowing, fine_payment

    def pay(self, payment_id: int, user_id: int, is_admin: bool) -> Payment:
        payment = self._db.get_payment(payment_id)
        if not payment:
            raise KeyError("payment not found")
        if not is_admin and payment.user_id != user_id:
            raise PermissionError("forbidden")
        payment.mark_paid()
        return payment

    def list_borrowings_filtered(
        self,
        actual_return_date: Optional[_dt.date],
        user_id: Optional[int],
        requester_user_id: int,
        requester_is_admin: bool,
    ) -> List[Borrowing]:
        items = self._db.list_borrowings()
        if not requester_is_admin:
            items = [b for b in items if b.user_id == requester_user_id]
        if actual_return_date is not None:
            items = [b for b in items if b.actual_return_date == actual_return_date]
        if user_id is not None:
            items = [b for b in items if b.user_id == user_id]
        items.sort(key=lambda b: b.id)
        return items


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: constr(min_length=1)
    password: constr(min_length=1)


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool


class BookCreate(BaseModel):
    title: constr(min_length=1)
    author: constr(min_length=1)
    total_copies: PositiveInt


class BookUpdate(BaseModel):
    title: Optional[constr(min_length=1)] = None
    author: Optional[constr(min_length=1)] = None
    total_copies: Optional[PositiveInt] = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    total_copies: int
    available_copies: int


class BorrowingCreate(BaseModel):
    book_id: PositiveInt
    days: Optional[PositiveInt] = None


class BorrowingOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrowed_at: _dt.datetime
    due_date: _dt.date
    actual_return_date: Optional[_dt.date] = None


class ReturnRequest(BaseModel):
    return_date: Optional[_dt.date] = None


class PaymentOut(BaseModel):
    id: int
    borrowing_id: int
    user_id: int
    amount: condecimal(gt=0, max_digits=12, decimal_places=2)
    currency: str
    payment_type: str
    status: str
    created_at: _dt.datetime
    paid_at: Optional[_dt.datetime] = None


class BorrowingWithPaymentOut(BaseModel):
    borrowing: BorrowingOut
    payment: PaymentOut


class ReturnResultOut(BaseModel):
    borrowing: BorrowingOut
    fine_payment: Optional[PaymentOut] = None


def _user_to_out(u: User) -> UserOut:
    return UserOut(id=u.id, username=u.username, is_admin=u.is_admin)


def _book_to_out(b: Book) -> BookOut:
    return BookOut(id=b.id, title=b.title, author=b.author, total_copies=b.total_copies, available_copies=b.available_copies)


def _borrowing_to_out(b: Borrowing) -> BorrowingOut:
    return BorrowingOut(
        id=b.id,
        user_id=b.user_id,
        book_id=b.book_id,
        borrowed_at=b.borrowed_at,
        due_date=b.due_date,
        actual_return_date=b.actual_return_date,
    )


def _payment_to_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        borrowing_id=p.borrowing_id,
        user_id=p.user_id,
        amount=p.amount,
        currency=p.currency,
        payment_type=p.payment_type,
        status=p.status,
        created_at=p.created_at,
        paid_at=p.paid_at,
    )


class AppContext:
    def __init__(self) -> None:
        self.db = InMemoryDB()
        self.jwt = SimpleJWT(secret=secrets.token_urlsafe(32))
        self.service = LibraryService(self.db)

        admin = self.db.create_user("admin", "admin", is_admin=True)
        user = self.db.create_user("user", "user", is_admin=False)

        self.db.create_book("The Hobbit", "J.R.R. Tolkien", 3)
        self.db.create_book("1984", "George Orwell", 2)
        self.db.create_book("Pride and Prejudice", "Jane Austen", 1)

        self._bootstrap_users = (admin, user)


ctx = AppContext()
app = FastAPI(
    title="library-service-api",
    version="1.0.0",
    docs_url="/api/v1/doc/swagger/",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: int
    username: str
    is_admin: bool


def get_current_principal(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AuthPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = ctx.jwt.decode(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    uid = payload.get("uid")
    is_admin = payload.get("adm")
    if not isinstance(uid, int) or not isinstance(is_admin, bool):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = ctx.db.get_user(uid)
    if not user or user.username != sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return AuthPrincipal(user_id=user.id, username=user.username, is_admin=user.is_admin)


def require_admin(p: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
    if not p.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return p


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    user = ctx.db.get_user_by_username(req.username)
    if not user or not _verify_password(req.password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = ctx.jwt.encode(subject=user.username, claims={"uid": user.id, "adm": user.is_admin})
    return TokenResponse(access_token=token)


@app.get("/api/v1/me", response_model=UserOut)
def me(p: AuthPrincipal = Depends(get_current_principal)) -> UserOut:
    user = ctx.db.get_user(p.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _user_to_out(user)


@app.get("/api/v1/books", response_model=List[BookOut])
def list_books(
    title: Optional[str] = Query(default=None),
    author: Optional[str] = Query(default=None),
    available: Optional[bool] = Query(default=None),
    p: AuthPrincipal = Depends(get_current_principal),
) -> List[BookOut]:
    books = ctx.db.list_books()
    if title is not None:
        t = title.strip().lower()
        books = [b for b in books if t in b.title.lower()]
    if author is not None:
        a = author.strip().lower()
        books = [b for b in books if a in b.author.lower()]
    if available is not None:
        if available:
            books = [b for b in books if b.available_copies > 0]
        else:
            books = [b for b in books if b.available_copies == 0]
    books.sort(key=lambda b: b.id)
    return [_book_to_out(b) for b in books]


@app.post("/api/v1/books", response_model=BookOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_book(req: BookCreate) -> BookOut:
    try:
        book = ctx.db.create_book(req.title, req.author, int(req.total_copies))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _book_to_out(book)


@app.patch("/api/v1/books/{book_id}", response_model=BookOut, dependencies=[Depends(require_admin)])
def update_book(book_id: int, req: BookUpdate) -> BookOut:
    try:
        book = ctx.db.update_book(book_id, req.title, req.author, int(req.total_copies) if req.total_copies is not None else None)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _book_to_out(book)


@app.delete("/api/v1/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_book(book_id: int) -> Response:
    try:
        ctx.db.delete_book(book_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/v1/borrowings", response_model=BorrowingWithPaymentOut, status_code=status.HTTP_201_CREATED)
def create_borrowing(req: BorrowingCreate, p: AuthPrincipal = Depends(get_current_principal)) -> BorrowingWithPaymentOut:
    try:
        borrowing, payment = ctx.service.create_borrowing(user_id=p.user_id, book_id=int(req.book_id), days=int(req.days) if req.days is not None else None)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return BorrowingWithPaymentOut(borrowing=_borrowing_to_out(borrowing), payment=_payment_to_out(payment))


@app.get("/api/v1/borrowings", response_model=List[BorrowingOut])
def list_borrowings(
    actual_return_date: Optional[_dt.date] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    p: AuthPrincipal = Depends(get_current_principal),
) -> List[BorrowingOut]:
    borrowings = ctx.service.list_borrowings_filtered(
        actual_return_date=actual_return_date,
        user_id=user_id,
        requester_user_id=p.user_id,
        requester_is_admin=p.is_admin,
    )
    return [_borrowing_to_out(b) for b in borrowings]


@app.post("/api/v1/borrowings/{borrowing_id}/return", response_model=ReturnResultOut)
def return_borrowing(borrowing_id: int, req: ReturnRequest, p: AuthPrincipal = Depends(get_current_principal)) -> ReturnResultOut:
    borrowing = ctx.db.get_borrowing(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    if not p.is_admin and borrowing.user_id != p.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        b, fine = ctx.service.return_borrowing(borrowing_id=borrowing_id, return_date=req.return_date)
    except KeyError as e:
        msg = str(e)
        if "book" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ReturnResultOut(borrowing=_borrowing_to_out(b), fine_payment=_payment_to_out(fine) if fine else None)


@app.get("/api/v1/payments", response_model=List[PaymentOut])
def list_payments(
    borrowing_id: Optional[int] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    payment_type: Optional[str] = Query(default=None),
    p: AuthPrincipal = Depends(get_current_principal),
) -> List[PaymentOut]:
    payments = ctx.db.list_payments()
    if not p.is_admin:
        payments = [pay for pay in payments if pay.user_id == p.user_id]
    if borrowing_id is not None:
        payments = [pay for pay in payments if pay.borrowing_id == borrowing_id]
    if user_id is not None:
        payments = [pay for pay in payments if pay.user_id == user_id]
    if status_filter is not None:
        payments = [pay for pay in payments if pay.status == status_filter]
    if payment_type is not None:
        payments = [pay for pay in payments if pay.payment_type == payment_type]
    payments.sort(key=lambda x: x.id)
    return [_payment_to_out(pay) for pay in payments]


@app.post("/api/v1/payments/{payment_id}/pay", response_model=PaymentOut)
def pay(payment_id: int, p: AuthPrincipal = Depends(get_current_principal)) -> PaymentOut:
    try:
        payment = ctx.service.pay(payment_id=payment_id, user_id=p.user_id, is_admin=p.is_admin)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _payment_to_out(payment)


@app.get("/admin/", include_in_schema=False)
def admin_panel(p: AuthPrincipal = Depends(require_admin)) -> Dict[str, Any]:
    users = [_user_to_out(u).model_dump() for u in ctx.db._users.values()]
    books = [_book_to_out(b).model_dump() for b in ctx.db.list_books()]
    borrowings = [_borrowing_to_out(b).model_dump() for b in ctx.db.list_borrowings()]
    payments = [_payment_to_out(pay).model_dump() for pay in ctx.db.list_payments()]
    return {"users": users, "books": books, "borrowings": borrowings, "payments": payments}