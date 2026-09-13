#!/usr/bin/env python3
"""
Library Service API - Complete Implementation
"""

import os
import sys
import json
import uuid
import hashlib
import hmac
import base64
import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from functools import wraps

# ============================================================
# Configuration
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "library-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
FINE_MULTIPLIER = Decimal("2.0")  # Fine is 2x the daily fee

# ============================================================
# JWT Implementation
# ============================================================

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt_token(payload: dict) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header).encode())
    payload_encoded = base64url_encode(json.dumps(payload).encode())
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        SECRET_KEY.encode(), message.encode(), hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    return f"{message}.{signature_encoded}"


def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_encoded, payload_encoded, signature_encoded = parts
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(), message.encode(), hashlib.sha256
        ).digest()
        expected_signature_encoded = base64url_encode(expected_signature)
        if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
            return None
        payload = json.loads(base64url_decode(payload_encoded))
        exp = payload.get("exp")
        if exp and datetime.datetime.utcnow().timestamp() > exp:
            return None
        return payload
    except Exception:
        return None


def generate_tokens(user_id: int, is_admin: bool) -> dict:
    now = datetime.datetime.utcnow()
    access_payload = {
        "user_id": user_id,
        "is_admin": is_admin,
        "exp": (now + datetime.timedelta(hours=JWT_EXPIRY_HOURS)).timestamp(),
        "iat": now.timestamp(),
        "type": "access",
    }
    refresh_payload = {
        "user_id": user_id,
        "is_admin": is_admin,
        "exp": (now + datetime.timedelta(days=7)).timestamp(),
        "iat": now.timestamp(),
        "type": "refresh",
    }
    return {
        "access": create_jwt_token(access_payload),
        "refresh": create_jwt_token(refresh_payload),
    }


# ============================================================
# Models
# ============================================================

class User:
    _id_counter = 1
    _users: Dict[int, "User"] = {}
    _email_index: Dict[str, int] = {}

    def __init__(self, email: str, password: str, first_name: str = "", last_name: str = "", is_admin: bool = False):
        self.id = User._id_counter
        User._id_counter += 1
        self.email = email
        self.password_hash = self._hash_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = is_admin
        self.is_active = True
        self.created_at = datetime.datetime.utcnow()
        User._users[self.id] = self
        User._email_index[email] = self.id

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = "library_salt_2024"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == self._hash_password(password)

    @classmethod
    def get_by_id(cls, user_id: int) -> Optional["User"]:
        return cls._users.get(user_id)

    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        user_id = cls._email_index.get(email)
        if user_id:
            return cls._users.get(user_id)
        return None

    @classmethod
    def get_all(cls) -> List["User"]:
        return list(cls._users.values())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
        }

    def update(self, **kwargs):
        if "email" in kwargs:
            if kwargs["email"] != self.email:
                del User._email_index[self.email]
                self.email = kwargs["email"]
                User._email_index[self.email] = self.id
        if "first_name" in kwargs:
            self.first_name = kwargs["first_name"]
        if "last_name" in kwargs:
            self.last_name = kwargs["last_name"]
        if "password" in kwargs:
            self.password_hash = self._hash_password(kwargs["password"])
        if "is_admin" in kwargs:
            self.is_admin = kwargs["is_admin"]


class Book:
    _id_counter = 1
    _books: Dict[int, "Book"] = {}

    COVER_CHOICES = ["HARD", "SOFT"]

    def __init__(self, title: str, author: str, cover: str, inventory: int, daily_fee: Decimal):
        if cover not in self.COVER_CHOICES:
            raise ValueError(f"Cover must be one of {self.COVER_CHOICES}")
        if inventory < 0:
            raise ValueError("Inventory cannot be negative")
        if daily_fee <= 0:
            raise ValueError("Daily fee must be positive")

        self.id = Book._id_counter
        Book._id_counter += 1
        self.title = title
        self.author = author
        self.cover = cover
        self.inventory = inventory
        self.daily_fee = Decimal(str(daily_fee))
        self.created_at = datetime.datetime.utcnow()
        Book._books[self.id] = self

    @classmethod
    def get_by_id(cls, book_id: int) -> Optional["Book"]:
        return cls._books.get(book_id)

    @classmethod
    def get_all(cls) -> List["Book"]:
        return list(cls._books.values())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "cover": self.cover,
            "inventory": self.inventory,
            "daily_fee": str(self.daily_fee),
        }

    def update(self, **kwargs):
        if "title" in kwargs:
            self.title = kwargs["title"]
        if "author" in kwargs:
            self.author = kwargs["author"]
        if "cover" in kwargs:
            if kwargs["cover"] not in self.COVER_CHOICES:
                raise ValueError(f"Cover must be one of {self.COVER_CHOICES}")
            self.cover = kwargs["cover"]
        if "inventory" in kwargs:
            if kwargs["inventory"] < 0:
                raise ValueError("Inventory cannot be negative")
            self.inventory = kwargs["inventory"]
        if "daily_fee" in kwargs:
            if Decimal(str(kwargs["daily_fee"])) <= 0:
                raise ValueError("Daily fee must be positive")
            self.daily_fee = Decimal(str(kwargs["daily_fee"]))

    def is_available(self) -> bool:
        return self.inventory > 0

    def borrow(self):
        if self.inventory <= 0:
            raise ValueError("Book is not available")
        self.inventory -= 1

    def return_book(self):
        self.inventory += 1


class Borrowing:
    _id_counter = 1
    _borrowings: Dict[int, "Borrowing"] = {}

    def __init__(self, user_id: int, book_id: int, expected_return_date: datetime.date):
        book = Book.get_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        if not book.is_available():
            raise ValueError("Book is not available for borrowing")
        user = User.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        self.id = Borrowing._id_counter
        Borrowing._id_counter += 1
        self.user_id = user_id
        self.book_id = book_id
        self.borrow_date = datetime.date.today()
        self.expected_return_date = expected_return_date
        self.actual_return_date: Optional[datetime.date] = None
        self.created_at = datetime.datetime.utcnow()

        book.borrow()
        Borrowing._borrowings[self.id] = self

    @classmethod
    def get_by_id(cls, borrowing_id: int) -> Optional["Borrowing"]:
        return cls._borrowings.get(borrowing_id)

    @classmethod
    def get_all(cls) -> List["Borrowing"]:
        return list(cls._borrowings.values())

    @classmethod
    def get_by_user(cls, user_id: int) -> List["Borrowing"]:
        return [b for b in cls._borrowings.values() if b.user_id == user_id]

    @classmethod
    def filter(cls, user_id: Optional[int] = None, is_active: Optional[bool] = None) -> List["Borrowing"]:
        result = list(cls._borrowings.values())
        if user_id is not None:
            result = [b for b in result if b.user_id == user_id]
        if is_active is not None:
            if is_active:
                result = [b for b in result if b.actual_return_date is None]
            else:
                result = [b for b in result if b.actual_return_date is not None]
        return result

    def is_active(self) -> bool:
        return self.actual_return_date is None

    def is_overdue(self) -> bool:
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return datetime.date.today() > self.expected_return_date

    def return_book(self) -> Optional["Payment"]:
        if self.actual_return_date:
            raise ValueError("Book already returned")
        self.actual_return_date = datetime.date.today()
        book = Book.get_by_id(self.book_id)
        if book:
            book.return_book()

        if self.is_overdue():
            return self._create_fine_payment()
        return None

    def calculate_borrowing_fee(self) -> Decimal:
        book = Book.get_by_id(self.book_id)
        if not book:
            return Decimal("0")
        end_date = self.actual_return_date or datetime.date.today()
        days = (end_date - self.borrow_date).days
        if days <= 0:
            days = 1
        return book.daily_fee * days

    def calculate_fine(self) -> Decimal:
        if not self.is_overdue():
            return Decimal("0")
        book = Book.get_by_id(self.book_id)
        if not book:
            return Decimal("0")
        end_date = self.actual_return_date or datetime.date.today()
        overdue_days = (end_date - self.expected_return_date).days
        if overdue_days <= 0:
            return Decimal("0")
        return book.daily_fee * overdue_days * FINE_MULTIPLIER

    def _create_fine_payment(self) -> "Payment":
        fine_amount = self.calculate_fine()
        payment = Payment(
            borrowing_id=self.id,
            payment_type="FINE",
            money_to_pay=fine_amount,
        )
        return payment

    def to_dict(self) -> dict:
        book = Book.get_by_id(self.book_id)
        user = User.get_by_id(self.user_id)
        return {
            "id": self.id,
            "borrow_date": self.borrow_date.isoformat(),
            "expected_return_date": self.expected_return_date.isoformat(),
            "actual_return_date": self.actual_return_date.isoformat() if self.actual_return_date else None,
            "book": book.to_dict() if book else None,
            "user": user.to_dict() if user else None,
            "is_active": self.is_active(),
            "is_overdue": self.is_overdue(),
        }


class Payment:
    _id_counter = 1
    _payments: Dict[int, "Payment"] = {}

    STATUS_CHOICES = ["PENDING", "PAID"]
    TYPE_CHOICES = ["PAYMENT", "FINE"]

    def __init__(self, borrowing_id: int, payment_type: str, money_to_pay: Decimal):
        if payment_type not in self.TYPE_CHOICES:
            raise ValueError(f"Payment type must be one of {self.TYPE_CHOICES}")

        self.id = Payment._id_counter
        Payment._id_counter += 1
        self.borrowing_id = borrowing_id
        self.status = "PENDING"
        self.payment_type = payment_type
        self.session_url = f"https://checkout.stripe.com/pay/session_{uuid.uuid4().hex}"
        self.session_id = f"session_{uuid.uuid4().hex}"
        self.money_to_pay = Decimal(str(money_to_pay))
        self.created_at = datetime.datetime.utcnow()
        Payment._payments[self.id] = self

    @classmethod
    def get_by_id(cls, payment_id: int) -> Optional["Payment"]:
        return cls._payments.get(payment_id)

    @classmethod
    def get_all(cls) -> List["Payment"]:
        return list(cls._payments.values())

    @classmethod
    def get_by_borrowing(cls, borrowing_id: int) -> List["Payment"]:
        return [p for p in cls._payments.values() if p.borrowing_id == borrowing_id]

    @classmethod
    def get_by_user(cls, user_id: int) -> List["Payment"]:
        result = []
        for payment in cls._payments.values():
            borrowing = Borrowing.get_by_id(payment.borrowing_id)
            if borrowing and borrowing.user_id == user_id:
                result.append(payment)
        return result

    def mark_as_paid(self):
        self.status = "PAID"

    def to_dict(self) -> dict:
        borrowing = Borrowing.get_by_id(self.borrowing_id)
        return {
            "id": self.id,
            "status": self.status,
            "type": self.payment_type,
            "borrowing_id": self.borrowing_id,
            "borrowing": borrowing.to_dict() if borrowing else None,
            "session_url": self.session_url,
            "session_id": self.session_id,
            "money_to_pay": str(self.money_to_pay),
        }


# ============================================================
# Response Helpers
# ============================================================

class Response:
    def __init__(self, data: Any, status: int = 200):
        self.data = data
        self.status = status

    def to_dict(self) -> dict:
        return {"status": self.status, "data": self.data}


def success_response(data: Any, status: int = 200) -> dict:
    return {"success": True, "data": data, "status": status}


def error_response(message: str, status: int = 400) -> dict:
    return {"success": False, "error": message, "status": status}


def paginate(items: list, page: int = 1, page_size: int = 10) -> dict:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "count": total,
        "next": page + 1 if end < total else None,
        "previous": page - 1 if page > 1 else None,
        "results": items[start:end],
    }


# ============================================================
# Validators
# ============================================================

class ValidationError(Exception):
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]


def validate_date(date_str: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        raise ValidationError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def validate_required(data: dict, fields: List[str]):
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == ""]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


# ============================================================
# Authentication Service
# ============================================================

class AuthService:
    @staticmethod
    def register(email: str, password: str, first_name: str = "", last_name: str = "", is_admin: bool = False) -> dict:
        if not validate_email(email):
            raise ValidationError("Invalid email format", "email")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters", "password")
        if User.get_by_email(email):
            raise ValidationError("User with this email already exists", "email")

        user = User(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
        )
        return user.to_dict()

    @staticmethod
    def login(email: str, password: str) -> dict:
        user = User.get_by_email(email)
        if not user or not user.check_password(password):
            raise ValidationError("Invalid email or password")
        if not user.is_active:
            raise ValidationError("User account is disabled")
        tokens = generate_tokens(user.id, user.is_admin)
        return tokens

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        payload = verify_jwt_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValidationError("Invalid or expired refresh token")
        user = User.get_by_id(payload["user_id"])
        if not user or not user.is_active:
            raise ValidationError("User not found or inactive")
        tokens = generate_tokens(user.id, user.is_admin)
        return {"access": tokens["access"]}

    @staticmethod
    def get_current_user(token: str) -> Optional[User]:
        payload = verify_jwt_token(token)
        if not payload or payload.get("type") != "access":
            return None
        return User.get_by_id(payload["user_id"])


# ============================================================
# Book Service
# ============================================================

class BookService:
    @staticmethod
    def create_book(title: str, author: str, cover: str, inventory: int, daily_fee: str) -> dict:
        validate_required(
            {"title": title, "author": author, "cover": cover, "inventory": inventory, "daily_fee": daily_fee},
            ["title", "author", "cover", "inventory", "daily_fee"]
        )
        try:
            book = Book(
                title=title,
                author=author,
                cover=cover,
                inventory=int(inventory),
                daily_fee=Decimal(str(daily_fee)),
            )
            return book.to_dict()
        except (ValueError, Exception) as e:
            raise ValidationError(str(e))

    @staticmethod
    def get_book(book_id: int) -> dict:
        book = Book.get_by_id(book_id)
        if not book:
            raise ValidationError("Book not found", "book_id")
        return book.to_dict()

    @staticmethod
    def list_books(title: Optional[str] = None, author: Optional[str] = None) -> List[dict]:
        books = Book.get_all()
        if title:
            books = [b for b in books if title.lower() in b.title.lower()]
        if author:
            books = [b for b in books if author.lower() in b.author.lower()]
        return [b.to_dict() for b in books]

    @staticmethod
    def update_book(book_id: int, **kwargs) -> dict:
        book = Book.get_by_id(book_id)
        if not book:
            raise ValidationError("Book not found", "book_id")
        try:
            book.update(**kwargs)
            return book.to_dict()
        except ValueError as e:
            raise ValidationError(str(e))

    @staticmethod
    def delete_book(book_id: int) -> bool:
        book = Book.get_by_id(book_id)
        if not book:
            raise ValidationError("Book not found", "book_id")
        del Book._books[book_id]
        return True


# ============================================================
# Borrowing Service
# ============================================================

class BorrowingService:
    @staticmethod
    def create_borrowing(user_id: int, book_id: int, expected_return_date: str) -> dict:
        validate_required(
            {"book_id": book_id, "expected_return_date": expected_return_date},
            ["book_id", "expected_return_date"]
        )
        exp_date = validate_date(expected_return_date)
        if exp_date <= datetime.date.today():
            raise ValidationError("Expected return date must be in the future", "expected_return_date")

        try:
            borrowing = Borrowing(
                user_id=user_id,
                book_id=book_id,
                expected_return_date=exp_date,
            )
            payment = Payment(
                borrowing_id=borrowing.id,
                payment_type="PAYMENT",
                money_to_pay=borrowing.calculate_borrowing_fee(),
            )
            result = borrowing.to_dict()
            result["payment"] = payment.to_dict()
            return result
        except ValueError as e:
            raise ValidationError(str(e))

    @staticmethod
    def get_borrowing(borrowing_id: int, user_id: int, is_admin: bool) -> dict:
        borrowing = Borrowing.get_by_id(borrowing_id)
        if not borrowing:
            raise ValidationError("Borrowing not found")
        if not is_admin and borrowing.user_id != user_id:
            raise ValidationError("Permission denied")
        return borrowing.to_dict()

    @staticmethod
    def list_borrowings(
        user_id: int,
        is_admin: bool,
        filter_user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> List[dict]:
        if is_admin:
            borrowings = Borrowing.filter(user_id=filter_user_id, is_active=is_active)
        else:
            borrowings = Borrowing.filter(user_id=user_id, is_active=is_active)
        return [b.to_dict() for b in borrowings]

    @staticmethod
    def return_borrowing(borrowing_id: int, user_id: int, is_admin: bool) -> dict:
        borrowing = Borrowing.get_by_id(borrowing_id)
        if not borrowing:
            raise ValidationError("Borrowing not found")
        if not is_admin and borrowing.user_id != user_id:
            raise ValidationError("Permission denied")
        if not borrowing.is_active():
            raise ValidationError("Book already returned")

        try:
            fine_payment = borrowing.return_book()
            result = borrowing.to_dict()
            if fine_payment:
                result["fine_payment"] = fine_payment.to_dict()
            return result
        except ValueError as e:
            raise ValidationError(str(e))


# ============================================================
# Payment Service
# ============================================================

class PaymentService:
    @staticmethod
    def list_payments(user_id: int, is_admin: bool) -> List[dict]:
        if is_admin:
            payments = Payment.get_all()
        else:
            payments = Payment.get_by_user(user_id)
        return [p.to_dict() for p in payments]

    @staticmethod
    def get_payment(payment_id: int, user_id: int, is_admin: bool) -> dict:
        payment = Payment.get_by_id(payment_id)
        if not payment:
            raise ValidationError("Payment not found")
        if not is_admin:
            borrowing = Borrowing.get_by_id(payment.borrowing_id)
            if not borrowing or borrowing.user_id != user_id:
                raise ValidationError("Permission denied")
        return payment.to_dict()

    @staticmethod
    def process_payment(payment_id: int, user_id: int, is_admin: bool) -> dict:
        payment = Payment.get_by_id(payment_id)
        if not payment:
            raise ValidationError("Payment not found")
        if not is_admin:
            borrowing = Borrowing.get_by_id(payment.borrowing_id)
            if not borrowing or borrowing.user_id != user_id:
                raise ValidationError("Permission denied")
        if payment.status == "PAID":
            raise ValidationError("Payment already processed")
        payment.mark_as_paid()
        return payment.to_dict()

    @staticmethod
    def payment_success(session_id: str, user_id: int, is_admin: bool) -> dict:
        payment = None
        for p in Payment.get_all():
            if p.session_id == session_id:
                payment = p
                break
        if not payment:
            raise ValidationError("Payment session not found")
        if not is_admin:
            borrowing = Borrowing.get_by_id(payment.borrowing_id)
            if not borrowing or borrowing.user_id != user_id:
                raise ValidationError("Permission denied")
        payment.mark_as_paid()
        return payment.to_dict()

    @staticmethod
    def payment_cancel(session_id: str) -> dict:
        payment = None
        for p in Payment.get_all():
            if p.session_id == session_id:
                payment = p
                break
        if not payment:
            raise ValidationError("Payment session not found")
        return {
            "message": "Payment was cancelled. You can retry the payment.",
            "payment": payment.to_dict(),
        }


# ============================================================
# User Service
# ============================================================

class UserService:
    @staticmethod
    def get_user(user_id: int, requesting_user_id: int, is_admin: bool) -> dict:
        if not is_admin and user_id != requesting_user_id:
            raise ValidationError("Permission denied")
        user = User.get_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        return user.to_dict()

    @staticmethod
    def list_users(is_admin: bool) -> List[dict]:
        if not is_admin:
            raise ValidationError("Permission denied")
        return [u.to_dict() for u in User.get_all()]

    @staticmethod
    def update_user(user_id: int, requesting_user_id: int, is_admin: bool, **kwargs) -> dict:
        if not is_admin and user_id != requesting_user_id:
            raise ValidationError("Permission denied")
        user = User.get_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        if "email" in kwargs and kwargs["email"] != user.email:
            if User.get_by_email(kwargs["email"]):
                raise ValidationError("Email already in use", "email")
            if not validate_email(kwargs["email"]):
                raise ValidationError("Invalid email format", "email")
        if "password" in kwargs and len(kwargs["password"]) < 8:
            raise ValidationError("Password must be at least 8 characters", "password")
        user.update(**kwargs)
        return user.to_dict()

    @staticmethod
    def get_me(user_id: int) -> dict:
        user = User.get_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        return user.to_dict()


# ============================================================
# Admin Panel
# ============================================================

class AdminPanel:
    """Simple admin panel for managing all resources"""

    @staticmethod
    def get_stats() -> dict:
        return {
            "total_users": len(User.get_all()),
            "total_books": len(Book.get_all()),
            "total_borrowings": len(Borrowing.get_all()),
            "active_borrowings": len([b for b in Borrowing.get_all() if b.is_active()]),
            "overdue_borrowings": len([b for b in Borrowing.get_all() if b.is_overdue()]),
            "total_payments": len(Payment.get_all()),
            "pending_payments": len([p for p in Payment.get_all() if p.status == "PENDING"]),
            "paid_payments": len([p for p in Payment.get_all() if p.status == "PAID"]),
        }

    @staticmethod
    def list_all_users() -> List[dict]:
        return [u.to_dict() for u in User.get_all()]

    @staticmethod
    def list_all_books() -> List[dict]:
        return [b.to_dict() for b in Book.get_all()]

    @staticmethod
    def list_all_borrowings(
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> List[dict]:
        borrowings = Borrowing.filter(user_id=user_id, is_active=is_active)
        return [b.to_dict() for b in borrowings]

    @staticmethod
    def list_all_payments() -> List[dict]:
        return [p.to_dict() for p in Payment.get_all()]

    @staticmethod
    def create_admin_user(email: str, password: str, first_name: str = "", last_name: str = "") -> dict:
        return AuthService.register(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_admin=True,
        )


# ============================================================
# API Router (Simulated REST API)
# ============================================================

class APIRouter:
    """Simulates a REST API router with JWT authentication"""

    def __init__(self):
        self.routes: Dict[str, Dict[str, Any]] = {}
        self._setup_routes()

    def _setup_routes(self):
        self.routes = {
            "POST /api/v1/auth/register/": self._register,
            "POST /api/v1/auth/login/": self._login,
            "POST /api/v1/auth/token/refresh/": self._refresh_token,
            "GET /api/v1/auth/me/": self._get_me,
            "PUT /api/v1/auth/me/": self._update_me,
            "GET /api/v1/books/": self._list_books,
            "POST /api/v1/books/": self._create_book,
            "GET /api/v1/books/{id}/": self._get_book,
            "PUT /api/v1/books/{id}/": self._update_book,
            "PATCH /api/v1/books/{id}/": self._update_book,
            "DELETE /api/v1/books/{id}/": self._delete_book,
            "GET /api/v1/borrowings/": self._list_borrowings,
            "POST /api/v1/borrowings/": self._create_borrowing,
            "GET /api/v1/borrowings/{id}/": self._get_borrowing,
            "POST /api/v1/borrowings/{id}/return/": self._return_borrowing,
            "GET /api/v1/payments/": self._list_payments,
            "GET /api/v1/payments/{id}/": self._get_payment,
            "POST /api/v1/payments/{id}/pay/": self._process_payment,
            "GET /api/v1/payments/success/": self._payment_success,
            "GET /api/v1/payments/cancel/": self._payment_cancel,
            "GET /admin/": self._admin_panel,
            "GET /admin/stats/": self._admin_stats,
            "GET /api/v1/doc/swagger/": self._swagger_docs,
            "GET /api/v1/users/": self._list_users,
            "GET /api/v1/users/{id}/": self._get_user,
            "PUT /api/v1/users/{id}/": self._update_user,
        }

    def _get_current_user(self, headers: dict) -> Optional[User]:
        auth_header = headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        return AuthService.get_current_user(token)

    def _require_auth(self, headers: dict) -> User:
        user = self._get_current_user(headers)
        if not user:
            raise ValidationError("Authentication required")
        return user

    def _require_admin(self, headers: dict) -> User:
        user = self._require_auth(headers)
        if not user.is_admin:
            raise ValidationError("Admin access required")
        return user

    def handle(self, method: str, path: str, data: dict = None, headers: dict = None, params: dict = None) -> dict:
        if data is None:
            data = {}
        if headers is None:
            headers = {}
        if params is None:
            params = {}

        path_id = None
        normalized_path = path
        parts = path.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            path_id = int(parts[-1])
            parts[-1] = "{id}"
            normalized_path = "/".join(parts) + "/"

        route_key = f"{method} {normalized_path}"
        handler = self.routes.get(route_key)

        if not handler:
            return error_response(f"Route not found: {method} {path}", 404)

        try:
            return handler(data=data, headers=headers, params=params, path_id=path_id)
        except ValidationError as e:
            return error_response(e.message, 400)
        except Exception as e:
            return error_response(f"Internal server error: {str(e)}", 500)

    def _register(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        validate_required(data, ["email", "password"])
        result = AuthService.register(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            is_admin=data.get("is_admin", False),
        )
        return success_response(result, 201)

    def _login(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        validate_required(data, ["email", "password"])
        tokens = AuthService.login(data["email"], data["password"])
        return success_response(tokens)

    def _refresh_token(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        validate_required(data, ["refresh"])
        result = AuthService.refresh_token(data["refresh"])
        return success_response(result)

    def _get_me(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        return success_response(UserService.get_me(user.id))

    def _update_me(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = UserService.update_user(user.id, user.id, user.is_admin, **data)
        return success_response(result)

    def _list_books(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        books = BookService.list_books(
            title=params.get("title"),
            author=params.get("author"),
        )
        return success_response(paginate(books, int(params.get("page", 1))))

    def _create_book(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        self._require_admin(headers)
        validate_required(data, ["title", "author", "cover", "inventory", "daily_fee"])
        result = BookService.create_book(
            title=data["title"],
            author=data["author"],
            cover=data["cover"],
            inventory=data["inventory"],
            daily_fee=data["daily_fee"],
        )
        return success_response(result, 201)

    def _get_book(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        result = BookService.get_book(path_id)
        return success_response(result)

    def _update_book(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        self._require_admin(headers)
        result = BookService.update_book(path_id, **data)
        return success_response(result)

    def _delete_book(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        self._require_admin(headers)
        BookService.delete_book(path_id)
        return success_response({"message": "Book deleted successfully"}, 204)

    def _list_borrowings(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        filter_user_id = None
        if "user_id" in params and user.is_admin:
            filter_user_id = int(params["user_id"])
        is_active = None
        if "is_active" in params:
            is_active = params["is_active"].lower() == "true"
        borrowings = BorrowingService.list_borrowings(
            user_id=user.id,
            is_admin=user.is_admin,
            filter_user_id=filter_user_id,
            is_active=is_active,
        )
        return success_response(paginate(borrowings, int(params.get("page", 1))))

    def _create_borrowing(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        validate_required(data, ["book_id", "expected_return_date"])
        result = BorrowingService.create_borrowing(
            user_id=user.id,
            book_id=data["book_id"],
            expected_return_date=data["expected_return_date"],
        )
        return success_response(result, 201)

    def _get_borrowing(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = BorrowingService.get_borrowing(path_id, user.id, user.is_admin)
        return success_response(result)

    def _return_borrowing(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = BorrowingService.return_borrowing(path_id, user.id, user.is_admin)
        return success_response(result)

    def _list_payments(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        payments = PaymentService.list_payments(user.id, user.is_admin)
        return success_response(paginate(payments, int(params.get("page", 1))))

    def _get_payment(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = PaymentService.get_payment(path_id, user.id, user.is_admin)
        return success_response(result)

    def _process_payment(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = PaymentService.process_payment(path_id, user.id, user.is_admin)
        return success_response(result)

    def _payment_success(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        session_id = params.get("session_id")
        if not session_id:
            raise ValidationError("session_id parameter is required")
        result = PaymentService.payment_success(session_id, user.id, user.is_admin)
        return success_response(result)

    def _payment_cancel(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        session_id = params.get("session_id")
        if not session_id:
            raise ValidationError("session_id parameter is required")
        result = PaymentService.payment_cancel(session_id)
        return success_response(result)

    def _admin_panel(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        self._require_admin(headers)
        stats = AdminPanel.get_stats()
        return success_response({
            "message": "Welcome to Library Admin Panel",
            "stats": stats,
            "endpoints": [
                "/admin/stats/",
                "/api/v1/books/",
                "/api/v1/borrowings/",
                "/api/v1/payments/",
                "/api/v1/users/",
            ]
        })

    def _admin_stats(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        self._require_admin(headers)
        return success_response(AdminPanel.get_stats())

    def _swagger_docs(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        swagger_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Library Service API",
                "version": "1.0.0",
                "description": "API for managing library borrowings, books, and payments",
            },
            "servers": [{"url": "/api/v1"}],
            "paths": {
                "/auth/register/": {
                    "post": {
                        "summary": "Register a new user",
                        "tags": ["Authentication"],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["email", "password"],
                                        "properties": {
                                            "email": {"type": "string"},
                                            "password": {"type": "string"},
                                            "first_name": {"type": "string"},
                                            "last_name": {"type": "string"},
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "User created successfully"}}
                    }
                },
                "/auth/login/": {
                    "post": {
                        "summary": "Login and get JWT tokens",
                        "tags": ["Authentication"],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["email", "password"],
                                        "properties": {
                                            "email": {"type": "string"},
                                            "password": {"type": "string"},
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "JWT tokens returned"}}
                    }
                },
                "/books/": {
                    "get": {
                        "summary": "List all books",
                        "tags": ["Books"],
                        "parameters": [
                            {"name": "title", "in": "query", "schema": {"type": "string"}},
                            {"name": "author", "in": "query", "schema": {"type": "string"}},
                            {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        ],
                        "responses": {"200": {"description": "List of books"}}
                    },
                    "post": {
                        "summary": "Create a new book (Admin only)",
                        "tags": ["Books"],
                        "security": [{"bearerAuth": []}],
                        "responses": {"201": {"description": "Book created"}}
                    }
                },
                "/borrowings/": {
                    "get": {
                        "summary": "List borrowings",
                        "tags": ["Borrowings"],
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "is_active", "in": "query", "schema": {"type": "boolean"},
                             "description": "Filter by active status (actual_return_date is null)"},
                            {"name": "user_id", "in": "query", "schema": {"type": "integer"},
                             "description": "Filter by user ID (Admin only)"},
                        ],
                        "responses": {"200": {"description": "List of borrowings"}}
                    },
                    "post": {
                        "summary": "Create a new borrowing",
                        "tags": ["Borrowings"],
                        "security": [{"bearerAuth": []}],
                        "responses": {"201": {"description": "Borrowing created"}}
                    }
                },
                "/borrowings/{id}/return/": {
                    "post": {
                        "summary": "Return a borrowed book",
                        "tags": ["Borrowings"],
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                        ],
                        "responses": {"200": {"description": "Book returned, fine payment created if overdue"}}
                    }
                },
                "/payments/": {
                    "get": {
                        "summary": "List payments",
                        "tags": ["Payments"],
                        "security": [{"bearerAuth": []}],
                        "responses": {"200": {"description": "List of payments"}}
                    }
                },
                "/payments/success/": {
                    "get": {
                        "summary": "Handle successful payment",
                        "tags": ["Payments"],
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "session_id", "in": "query", "required": True, "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "Payment marked as paid"}}
                    }
                },
                "/payments/cancel/": {
                    "get": {
                        "summary": "Handle cancelled payment",
                        "tags": ["Payments"],
                        "parameters": [
                            {"name": "session_id", "in": "query", "required": True, "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "Payment cancellation acknowledged"}}
                    }
                },
            },
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                }
            }
        }
        return success_response(swagger_spec)

    def _list_users(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        users = UserService.list_users(user.is_admin)
        return success_response(paginate(users, int(params.get("page", 1))))

    def _get_user(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = UserService.get_user(path_id, user.id, user.is_admin)
        return success_response(result)

    def _update_user(self, data: dict, headers: dict, params: dict, path_id: Optional[int]) -> dict:
        user = self._require_auth(headers)
        result = UserService.update_user(path_id, user.id, user.is_admin, **data)
        return success_response(result)


# ============================================================
# Application Entry Point
# ============================================================

class LibraryServiceApp:
    """Main application class"""

    def __init__(self):
        self.router = APIRouter()
        self._initialize_data()

    def _initialize_data(self):
        """Initialize with sample data"""
        try:
            admin = AuthService.register(
                email="admin@library.com",
                password="admin1234",
                first_name="Admin",
                last_name="User",
                is_admin=True,
            )
        except ValidationError:
            pass

        try:
            BookService.create_book(
                title="The Great Gatsby",
                author="F. Scott Fitzgerald",
                cover="HARD",
                inventory=5,
                daily_fee="1.50",
            )
            BookService.create_book(
                title="To Kill a Mockingbird",
                author="Harper Lee",
                cover="SOFT",
                inventory=3,
                daily_fee="1.00",
            )
            BookService.create_book(
                title="1984",
                author="George Orwell",
                cover="HARD",
                inventory=7,
                daily_fee="2.00",
            )
        except ValidationError:
            pass

    def request(self, method: str, path: str, data: dict = None, headers: dict = None, params: dict = None) -> dict:
        return self.router.handle(method, path, data, headers, params)

    def get_auth_header(self, email: str, password: str) -> dict:
        response = self.request("POST", "/api/v1/auth/login/", {"email": email, "password": password})
        if response.get("success"):
            token = response["data"]["access"]
            return {"Authorization": f"Bearer {token}"}
        return {}


def main():
    """Demonstrate the Library Service API"""
    app = LibraryServiceApp()

    print("=" * 60)
    print("Library Service API - Demo")
    print("=" * 60)

    print("\n1. Register a new user")
    response = app.request("POST", "/api/v1/auth/register/", {
        "email": "user@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
    })
    print(f"   Status: {response['status']}")
    print(f"   User: {response['data']['email']}")

    print("\n2. Login")
    response = app.request("POST", "/api/v1/auth/login/", {
        "email": "user@example.com",
        "password": "password123",
    })
    user_token = response["data"]["access"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    print(f"   Status: {response['status']}")
    print(f"   Token received: {user_token[:50]}...")

    print("\n3. List Books")
    response = app.request("GET", "/api/v1/books/")
    print(f"   Status: {response['status']}")
    print(f"   Total books: {response['data']['count']}")
    for book in response["data"]["results"]:
        print(f"   - {book['title']} by {book['author']} (${book['daily_fee']}/day, {book['inventory']} available)")

    print("\n4. Create a Borrowing")
    future_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    response = app.request("POST", "/api/v1/borrowings/", {
        "book_id": 1,
        "expected_return_date": future_date,
    }, user_headers)
    print(f"   Status: {response['status']}")
    if response.get("success"):
        borrowing_id = response["data"]["id"]
        payment_id = response["data"]["payment"]["id"]
        print(f"   Borrowing ID: {borrowing_id}")
        print(f"   Payment ID: {payment_id}")
        print(f"   Amount to pay: ${response['data']['payment']['money_to_pay']}")

    print("\n5. List Borrowings (active only)")
    response = app.request("GET", "/api/v1/borrowings/", headers=user_headers, params={"is_active": "true"})
    print(f"   Status: {response['status']}")
    print(f"   Active borrowings: {response['data']['count']}")

    print("\n6. Process Payment")
    response = app.request("POST", f"/api/v1/payments/{payment_id}/pay/", headers=user_headers)
    print(f"   Status: {response['status']}")
    if response.get("success"):
        print(f"   Payment status: {response['data']['status']}")

    print("\n7. Return Book")
    response = app.request("POST", f"/api/v1/borrowings/{borrowing_id}/return/", headers=user_headers)
    print(f"   Status: {response['status']}")
    if response.get("success"):
        print(f"   Return date: {response['data']['actual_return_date']}")
        if "fine_payment" in response["data"]:
            print(f"   Fine payment: ${response['data']['fine_payment']['money_to_pay']}")

    print("\n8. Admin Login and Stats")
    admin_headers = app.get_auth_header("admin@library.com", "admin1234")
    response = app.request("GET", "/admin/stats/", headers=admin_headers)
    print(f"   Status: {response['status']}")
    if response.get("success"):
        stats = response["data"]
        print(f"   Total users: {stats['total_users']}")
        print(f"   Total books: {stats['total_books']}")
        print(f"   Total borrowings: {stats['total_borrowings']}")
        print(f"   Total payments: {stats['total_payments']}")

    print("\n9. Admin - List All Borrowings with User Filter")
    response = app.request("GET", "/api/v1/borrowings/", headers=admin_headers, params={"user_id": "2"})
    print(f"   Status: {response['status']}")
    print(f"   Borrowings for user 2: {response['data']['count']}")

    print("\n10. Swagger Documentation")
    response = app.request("GET", "/api/v1/doc/swagger/")
    print(f"    Status: {response['status']}")
    if response.get("success"):
        print(f"    API Title: {response['data']['info']['title']}")
        print(f"    API Version: {response['data']['info']['version']}")
        print(f"    Endpoints documented: {len(response['data']['paths'])}")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()