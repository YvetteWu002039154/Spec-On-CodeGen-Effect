#!/usr/bin/env python3
"""
Library Service API - Complete Implementation
JWT authentication, book management, borrowings, and payments
"""

import os
import sys
import uuid
import hashlib
import hmac
import base64
import json
import re
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from functools import wraps

# ============================================================
# Configuration
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "library-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
DAILY_FEE_MULTIPLIER = Decimal("1.5")  # Fine multiplier for overdue books

# In-memory storage (simulating database)
_users_db: Dict[str, Dict] = {}
_books_db: Dict[str, Dict] = {}
_borrowings_db: Dict[str, Dict] = {}
_payments_db: Dict[str, Dict] = {}

# ============================================================
# Utilities
# ============================================================

def generate_id() -> str:
    return str(uuid.uuid4())

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return base64.b64encode(salt + key).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        decoded = base64.b64decode(hashed.encode())
        salt = decoded[:16]
        stored_key = decoded[16:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hmac.compare_digest(key, stored_key)
    except Exception:
        return False

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def create_jwt_token(payload: Dict) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header).encode())
    payload_encoded = base64url_encode(json.dumps(payload).encode())
    signing_input = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    return f"{signing_input}.{signature_encoded}"

def verify_jwt_token(token: str) -> Optional[Dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_encoded, payload_encoded, signature_encoded = parts
        signing_input = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        expected_encoded = base64url_encode(expected_signature)
        if not hmac.compare_digest(signature_encoded, expected_encoded):
            return None
        payload = json.loads(base64url_decode(payload_encoded))
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            return None
        return payload
    except Exception:
        return None

def generate_access_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": (datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)).timestamp(),
        "iat": datetime.utcnow().timestamp(),
    }
    return create_jwt_token(payload)

def generate_refresh_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": (datetime.utcnow() + timedelta(days=7)).timestamp(),
        "iat": datetime.utcnow().timestamp(),
    }
    return create_jwt_token(payload)

# ============================================================
# Models
# ============================================================

class CoverType:
    HARD = "HARD"
    SOFT = "SOFT"
    CHOICES = [HARD, SOFT]

class PaymentStatus:
    PENDING = "PENDING"
    PAID = "PAID"
    CHOICES = [PENDING, PAID]

class PaymentType:
    PAYMENT = "PAYMENT"
    FINE = "FINE"
    CHOICES = [PAYMENT, FINE]

class User:
    def __init__(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        is_admin: bool = False,
        is_active: bool = True,
    ):
        self.id = generate_id()
        self.email = email
        self.password_hash = hash_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = is_admin
        self.is_active = is_active
        self.created_at = datetime.utcnow().isoformat()

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        user = cls.__new__(cls)
        user.id = data["id"]
        user.email = data["email"]
        user.password_hash = data["password_hash"]
        user.first_name = data.get("first_name", "")
        user.last_name = data.get("last_name", "")
        user.is_admin = data.get("is_admin", False)
        user.is_active = data.get("is_active", True)
        user.created_at = data.get("created_at", datetime.utcnow().isoformat())
        return user

    def to_storage_dict(self) -> Dict:
        d = self.to_dict()
        d["password_hash"] = self.password_hash
        return d

class Book:
    def __init__(
        self,
        title: str,
        author: str,
        cover: str,
        inventory: int,
        daily_fee: Decimal,
    ):
        self.id = generate_id()
        self.title = title
        self.author = author
        self.cover = cover
        self.inventory = inventory
        self.daily_fee = daily_fee
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "cover": self.cover,
            "inventory": self.inventory,
            "daily_fee": str(self.daily_fee),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Book":
        book = cls.__new__(cls)
        book.id = data["id"]
        book.title = data["title"]
        book.author = data["author"]
        book.cover = data["cover"]
        book.inventory = data["inventory"]
        book.daily_fee = Decimal(str(data["daily_fee"]))
        book.created_at = data.get("created_at", datetime.utcnow().isoformat())
        return book

class Borrowing:
    def __init__(
        self,
        book_id: str,
        user_id: str,
        expected_return_date: str,
    ):
        self.id = generate_id()
        self.borrow_date = date.today().isoformat()
        self.expected_return_date = expected_return_date
        self.actual_return_date: Optional[str] = None
        self.book_id = book_id
        self.user_id = user_id
        self.created_at = datetime.utcnow().isoformat()

    @property
    def is_active(self) -> bool:
        return self.actual_return_date is None

    @property
    def is_overdue(self) -> bool:
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return date.today().isoformat() > self.expected_return_date

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "borrow_date": self.borrow_date,
            "expected_return_date": self.expected_return_date,
            "actual_return_date": self.actual_return_date,
            "book_id": self.book_id,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "is_overdue": self.is_overdue,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Borrowing":
        borrowing = cls.__new__(cls)
        borrowing.id = data["id"]
        borrowing.borrow_date = data["borrow_date"]
        borrowing.expected_return_date = data["expected_return_date"]
        borrowing.actual_return_date = data.get("actual_return_date")
        borrowing.book_id = data["book_id"]
        borrowing.user_id = data["user_id"]
        borrowing.created_at = data.get("created_at", datetime.utcnow().isoformat())
        return borrowing

class Payment:
    def __init__(
        self,
        borrowing_id: str,
        user_id: str,
        status: str,
        payment_type: str,
        session_url: str,
        session_id: str,
        money_to_pay: Decimal,
    ):
        self.id = generate_id()
        self.borrowing_id = borrowing_id
        self.user_id = user_id
        self.status = status
        self.payment_type = payment_type
        self.session_url = session_url
        self.session_id = session_id
        self.money_to_pay = money_to_pay
        self.created_at = datetime.utcnow().isoformat()
        self.paid_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "borrowing_id": self.borrowing_id,
            "user_id": self.user_id,
            "status": self.status,
            "payment_type": self.payment_type,
            "session_url": self.session_url,
            "session_id": self.session_id,
            "money_to_pay": str(self.money_to_pay),
            "created_at": self.created_at,
            "paid_at": self.paid_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Payment":
        payment = cls.__new__(cls)
        payment.id = data["id"]
        payment.borrowing_id = data["borrowing_id"]
        payment.user_id = data["user_id"]
        payment.status = data["status"]
        payment.payment_type = data["payment_type"]
        payment.session_url = data["session_url"]
        payment.session_id = data["session_id"]
        payment.money_to_pay = Decimal(str(data["money_to_pay"]))
        payment.created_at = data.get("created_at", datetime.utcnow().isoformat())
        payment.paid_at = data.get("paid_at")
        return payment

# ============================================================
# Repositories
# ============================================================

class UserRepository:
    def create(self, email: str, password: str, first_name: str = "", last_name: str = "", is_admin: bool = False) -> User:
        if self.find_by_email(email):
            raise ValueError(f"User with email {email} already exists")
        user = User(email=email, password=password, first_name=first_name, last_name=last_name, is_admin=is_admin)
        _users_db[user.id] = user.to_storage_dict()
        return user

    def find_by_id(self, user_id: str) -> Optional[User]:
        data = _users_db.get(user_id)
        if data:
            return User.from_dict(data)
        return None

    def find_by_email(self, email: str) -> Optional[User]:
        for data in _users_db.values():
            if data["email"] == email:
                return User.from_dict(data)
        return None

    def update(self, user: User) -> User:
        _users_db[user.id] = user.to_storage_dict()
        return user

    def list_all(self) -> List[User]:
        return [User.from_dict(d) for d in _users_db.values()]

class BookRepository:
    def create(self, title: str, author: str, cover: str, inventory: int, daily_fee: Decimal) -> Book:
        if cover not in CoverType.CHOICES:
            raise ValueError(f"Invalid cover type. Must be one of {CoverType.CHOICES}")
        if inventory < 0:
            raise ValueError("Inventory cannot be negative")
        if daily_fee <= 0:
            raise ValueError("Daily fee must be positive")
        book = Book(title=title, author=author, cover=cover, inventory=inventory, daily_fee=daily_fee)
        _books_db[book.id] = book.to_dict()
        return book

    def find_by_id(self, book_id: str) -> Optional[Book]:
        data = _books_db.get(book_id)
        if data:
            return Book.from_dict(data)
        return None

    def update(self, book: Book) -> Book:
        _books_db[book.id] = book.to_dict()
        return book

    def delete(self, book_id: str) -> bool:
        if book_id in _books_db:
            del _books_db[book_id]
            return True
        return False

    def list_all(self) -> List[Book]:
        return [Book.from_dict(d) for d in _books_db.values()]

class BorrowingRepository:
    def create(self, book_id: str, user_id: str, expected_return_date: str) -> Borrowing:
        borrowing = Borrowing(book_id=book_id, user_id=user_id, expected_return_date=expected_return_date)
        _borrowings_db[borrowing.id] = borrowing.to_dict()
        return borrowing

    def find_by_id(self, borrowing_id: str) -> Optional[Borrowing]:
        data = _borrowings_db.get(borrowing_id)
        if data:
            return Borrowing.from_dict(data)
        return None

    def update(self, borrowing: Borrowing) -> Borrowing:
        _borrowings_db[borrowing.id] = borrowing.to_dict()
        return borrowing

    def list_all(self, user_id: Optional[str] = None, is_active: Optional[bool] = None) -> List[Borrowing]:
        borrowings = [Borrowing.from_dict(d) for d in _borrowings_db.values()]
        if user_id:
            borrowings = [b for b in borrowings if b.user_id == user_id]
        if is_active is not None:
            borrowings = [b for b in borrowings if b.is_active == is_active]
        return borrowings

    def filter_by_actual_return_date(self, has_return_date: bool) -> List[Borrowing]:
        borrowings = [Borrowing.from_dict(d) for d in _borrowings_db.values()]
        if has_return_date:
            return [b for b in borrowings if b.actual_return_date is not None]
        else:
            return [b for b in borrowings if b.actual_return_date is None]

class PaymentRepository:
    def create(
        self,
        borrowing_id: str,
        user_id: str,
        status: str,
        payment_type: str,
        session_url: str,
        session_id: str,
        money_to_pay: Decimal,
    ) -> Payment:
        payment = Payment(
            borrowing_id=borrowing_id,
            user_id=user_id,
            status=status,
            payment_type=payment_type,
            session_url=session_url,
            session_id=session_id,
            money_to_pay=money_to_pay,
        )
        _payments_db[payment.id] = payment.to_dict()
        return payment

    def find_by_id(self, payment_id: str) -> Optional[Payment]:
        data = _payments_db.get(payment_id)
        if data:
            return Payment.from_dict(data)
        return None

    def find_by_session_id(self, session_id: str) -> Optional[Payment]:
        for data in _payments_db.values():
            if data["session_id"] == session_id:
                return Payment.from_dict(data)
        return None

    def update(self, payment: Payment) -> Payment:
        _payments_db[payment.id] = payment.to_dict()
        return payment

    def list_all(self, user_id: Optional[str] = None) -> List[Payment]:
        payments = [Payment.from_dict(d) for d in _payments_db.values()]
        if user_id:
            payments = [p for p in payments if p.user_id == user_id]
        return payments

# ============================================================
# Services
# ============================================================

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def register(self, email: str, password: str, first_name: str = "", last_name: str = "") -> Dict:
        if not email or not password:
            raise ValueError("Email and password are required")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email format")
        user = self.user_repo.create(email=email, password=password, first_name=first_name, last_name=last_name)
        return user.to_dict()

    def login(self, email: str, password: str) -> Dict:
        user = self.user_repo.find_by_email(email)
        if not user or not user.check_password(password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("User account is inactive")
        access_token = generate_access_token(user.id)
        refresh_token = generate_refresh_token(user.id)
        return {
            "access": access_token,
            "refresh": refresh_token,
            "user": user.to_dict(),
        }

    def refresh_token(self, refresh_token: str) -> Dict:
        payload = verify_jwt_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid or expired refresh token")
        user_id = payload.get("user_id")
        user = self.user_repo.find_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")
        new_access_token = generate_access_token(user.id)
        return {"access": new_access_token}

    def get_current_user(self, token: str) -> Optional[User]:
        payload = verify_jwt_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id = payload.get("user_id")
        return self.user_repo.find_by_id(user_id)

    def update_user(self, user_id: str, data: Dict) -> Dict:
        user_repo = UserRepository()
        user = user_repo.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "email" in data:
            existing = user_repo.find_by_email(data["email"])
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")
            user.email = data["email"]
        if "password" in data:
            if len(data["password"]) < 8:
                raise ValueError("Password must be at least 8 characters")
            user.password_hash = hash_password(data["password"])
        user_repo.update(user)
        return user.to_dict()

class BookService:
    def __init__(self):
        self.book_repo = BookRepository()

    def create_book(self, title: str, author: str, cover: str, inventory: int, daily_fee: str) -> Dict:
        try:
            fee = Decimal(daily_fee)
        except Exception:
            raise ValueError("Invalid daily fee format")
        book = self.book_repo.create(
            title=title,
            author=author,
            cover=cover,
            inventory=inventory,
            daily_fee=fee,
        )
        return book.to_dict()

    def get_book(self, book_id: str) -> Dict:
        book = self.book_repo.find_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        return book.to_dict()

    def list_books(self) -> List[Dict]:
        return [b.to_dict() for b in self.book_repo.list_all()]

    def update_book(self, book_id: str, data: Dict) -> Dict:
        book = self.book_repo.find_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        if "title" in data:
            book.title = data["title"]
        if "author" in data:
            book.author = data["author"]
        if "cover" in data:
            if data["cover"] not in CoverType.CHOICES:
                raise ValueError(f"Invalid cover type. Must be one of {CoverType.CHOICES}")
            book.cover = data["cover"]
        if "inventory" in data:
            if int(data["inventory"]) < 0:
                raise ValueError("Inventory cannot be negative")
            book.inventory = int(data["inventory"])
        if "daily_fee" in data:
            try:
                fee = Decimal(str(data["daily_fee"]))
                if fee <= 0:
                    raise ValueError("Daily fee must be positive")
                book.daily_fee = fee
            except Exception as e:
                raise ValueError(f"Invalid daily fee: {e}")
        self.book_repo.update(book)
        return book.to_dict()

    def delete_book(self, book_id: str) -> bool:
        book = self.book_repo.find_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        return self.book_repo.delete(book_id)

class BorrowingService:
    def __init__(self):
        self.borrowing_repo = BorrowingRepository()
        self.book_repo = BookRepository()
        self.payment_repo = PaymentRepository()

    def create_borrowing(self, book_id: str, user_id: str, expected_return_date: str) -> Dict:
        book = self.book_repo.find_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        if book.inventory <= 0:
            raise ValueError("Book is not available (inventory is 0)")
        try:
            exp_date = date.fromisoformat(expected_return_date)
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
        if exp_date <= date.today():
            raise ValueError("Expected return date must be in the future")

        # Decrease inventory
        book.inventory -= 1
        self.book_repo.update(book)

        borrowing = self.borrowing_repo.create(
            book_id=book_id,
            user_id=user_id,
            expected_return_date=expected_return_date,
        )

        # Create payment for the borrowing
        days = (exp_date - date.today()).days
        money_to_pay = book.daily_fee * days
        session_id = generate_id()
        session_url = f"https://checkout.stripe.com/pay/{session_id}"

        self.payment_repo.create(
            borrowing_id=borrowing.id,
            user_id=user_id,
            status=PaymentStatus.PENDING,
            payment_type=PaymentType.PAYMENT,
            session_url=session_url,
            session_id=session_id,
            money_to_pay=money_to_pay,
        )

        return borrowing.to_dict()

    def return_borrowing(self, borrowing_id: str, user_id: str, is_admin: bool = False) -> Dict:
        borrowing = self.borrowing_repo.find_by_id(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found")
        if not is_admin and borrowing.user_id != user_id:
            raise ValueError("Permission denied")
        if not borrowing.is_active:
            raise ValueError("Borrowing already returned")

        actual_return = date.today().isoformat()
        borrowing.actual_return_date = actual_return
        self.borrowing_repo.update(borrowing)

        # Restore book inventory
        book = self.book_repo.find_by_id(borrowing.book_id)
        if book:
            book.inventory += 1
            self.book_repo.update(book)

        # Check if overdue and create fine payment
        if borrowing.is_overdue and book:
            expected = date.fromisoformat(borrowing.expected_return_date)
            actual = date.fromisoformat(actual_return)
            overdue_days = (actual - expected).days
            fine_amount = book.daily_fee * DAILY_FEE_MULTIPLIER * overdue_days
            session_id = generate_id()
            session_url = f"https://checkout.stripe.com/pay/{session_id}"
            self.payment_repo.create(
                borrowing_id=borrowing.id,
                user_id=borrowing.user_id,
                status=PaymentStatus.PENDING,
                payment_type=PaymentType.FINE,
                session_url=session_url,
                session_id=session_id,
                money_to_pay=fine_amount,
            )

        return borrowing.to_dict()

    def get_borrowing(self, borrowing_id: str, user_id: str, is_admin: bool = False) -> Dict:
        borrowing = self.borrowing_repo.find_by_id(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found")
        if not is_admin and borrowing.user_id != user_id:
            raise ValueError("Permission denied")
        return borrowing.to_dict()

    def list_borrowings(
        self,
        user_id: str,
        is_admin: bool = False,
        filter_user_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        has_actual_return_date: Optional[bool] = None,
    ) -> List[Dict]:
        if is_admin:
            target_user_id = filter_user_id
        else:
            target_user_id = user_id

        borrowings = self.borrowing_repo.list_all(user_id=target_user_id, is_active=is_active)

        if has_actual_return_date is not None:
            if has_actual_return_date:
                borrowings = [b for b in borrowings if b.actual_return_date is not None]
            else:
                borrowings = [b for b in borrowings if b.actual_return_date is None]

        return [b.to_dict() for b in borrowings]

class PaymentService:
    def __init__(self):
        self.payment_repo = PaymentRepository()
        self.borrowing_repo = BorrowingRepository()

    def list_payments(self, user_id: str, is_admin: bool = False) -> List[Dict]:
        if is_admin:
            payments = self.payment_repo.list_all()
        else:
            payments = self.payment_repo.list_all(user_id=user_id)
        return [p.to_dict() for p in payments]

    def get_payment(self, payment_id: str, user_id: str, is_admin: bool = False) -> Dict:
        payment = self.payment_repo.find_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if not is_admin and payment.user_id != user_id:
            raise ValueError("Permission denied")
        return payment.to_dict()

    def process_payment_success(self, session_id: str, user_id: str, is_admin: bool = False) -> Dict:
        payment = self.payment_repo.find_by_session_id(session_id)
        if not payment:
            raise ValueError("Payment session not found")
        if not is_admin and payment.user_id != user_id:
            raise ValueError("Permission denied")
        if payment.status == PaymentStatus.PAID:
            raise ValueError("Payment already processed")
        payment.status = PaymentStatus.PAID
        payment.paid_at = datetime.utcnow().isoformat()
        self.payment_repo.update(payment)
        return payment.to_dict()

    def process_payment_cancel(self, session_id: str, user_id: str, is_admin: bool = False) -> Dict:
        payment = self.payment_repo.find_by_session_id(session_id)
        if not payment:
            raise ValueError("Payment session not found")
        if not is_admin and payment.user_id != user_id:
            raise ValueError("Permission denied")
        return {
            "message": "Payment cancelled. You can retry the payment later.",
            "payment": payment.to_dict(),
        }

    def renew_payment_session(self, payment_id: str, user_id: str, is_admin: bool = False) -> Dict:
        payment = self.payment_repo.find_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if not is_admin and payment.user_id != user_id:
            raise ValueError("Permission denied")
        if payment.status == PaymentStatus.PAID:
            raise ValueError("Payment already completed")
        new_session_id = generate_id()
        new_session_url = f"https://checkout.stripe.com/pay/{new_session_id}"
        payment.session_id = new_session_id
        payment.session_url = new_session_url
        self.payment_repo.update(payment)
        return payment.to_dict()

# ============================================================
# Request/Response Helpers
# ============================================================

class Response:
    def __init__(self, data: Any, status: int = 200, error: Optional[str] = None):
        self.data = data
        self.status = status
        self.error = error

    def to_dict(self) -> Dict:
        if self.error:
            return {"error": self.error, "status": self.status}
        return {"data": self.data, "status": self.status}

def success_response(data: Any, status: int = 200) -> Response:
    return Response(data=data, status=status)

def error_response(message: str, status: int = 400) -> Response:
    return Response(data=None, status=status, error=message)

# ============================================================
# API Controllers
# ============================================================

class AuthController:
    def __init__(self):
        self.auth_service = AuthService()

    def register(self, request_data: Dict) -> Response:
        try:
            email = request_data.get("email", "")
            password = request_data.get("password", "")
            first_name = request_data.get("first_name", "")
            last_name = request_data.get("last_name", "")
            user = self.auth_service.register(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            return success_response(user, status=201)
        except ValueError as e:
            return error_response(str(e), status=400)

    def login(self, request_data: Dict) -> Response:
        try:
            email = request_data.get("email", "")
            password = request_data.get("password", "")
            tokens = self.auth_service.login(email=email, password=password)
            return success_response(tokens)
        except ValueError as e:
            return error_response(str(e), status=401)

    def refresh(self, request_data: Dict) -> Response:
        try:
            refresh_token = request_data.get("refresh", "")
            tokens = self.auth_service.refresh_token(refresh_token)
            return success_response(tokens)
        except ValueError as e:
            return error_response(str(e), status=401)

    def me(self, token: str) -> Response:
        user = self.auth_service.get_current_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        return success_response(user.to_dict())

    def update_me(self, token: str, request_data: Dict) -> Response:
        user = self.auth_service.get_current_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            updated = self.auth_service.update_user(user.id, request_data)
            return success_response(updated)
        except ValueError as e:
            return error_response(str(e), status=400)

class BookController:
    def __init__(self):
        self.book_service = BookService()
        self.auth_service = AuthService()

    def _get_user(self, token: str) -> Optional[User]:
        return self.auth_service.get_current_user(token)

    def list_books(self, token: Optional[str] = None) -> Response:
        books = self.book_service.list_books()
        return success_response(books)

    def get_book(self, book_id: str, token: Optional[str] = None) -> Response:
        try:
            book = self.book_service.get_book(book_id)
            return success_response(book)
        except ValueError as e:
            return error_response(str(e), status=404)

    def create_book(self, token: str, request_data: Dict) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        if not user.is_admin:
            return error_response("Admin access required", status=403)
        try:
            book = self.book_service.create_book(
                title=request_data.get("title", ""),
                author=request_data.get("author", ""),
                cover=request_data.get("cover", ""),
                inventory=int(request_data.get("inventory", 0)),
                daily_fee=str(request_data.get("daily_fee", "0")),
            )
            return success_response(book, status=201)
        except ValueError as e:
            return error_response(str(e), status=400)

    def update_book(self, token: str, book_id: str, request_data: Dict) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        if not user.is_admin:
            return error_response("Admin access required", status=403)
        try:
            book = self.book_service.update_book(book_id, request_data)
            return success_response(book)
        except ValueError as e:
            return error_response(str(e), status=400)

    def delete_book(self, token: str, book_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        if not user.is_admin:
            return error_response("Admin access required", status=403)
        try:
            self.book_service.delete_book(book_id)
            return success_response({"message": "Book deleted successfully"})
        except ValueError as e:
            return error_response(str(e), status=404)

class BorrowingController:
    def __init__(self):
        self.borrowing_service = BorrowingService()
        self.auth_service = AuthService()

    def _get_user(self, token: str) -> Optional[User]:
        return self.auth_service.get_current_user(token)

    def list_borrowings(self, token: str, filters: Dict = None) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        filters = filters or {}
        filter_user_id = filters.get("user_id") if user.is_admin else None
        is_active_str = filters.get("is_active")
        is_active = None
        if is_active_str is not None:
            is_active = str(is_active_str).lower() in ("true", "1", "yes")
        has_actual_return_str = filters.get("has_actual_return_date")
        has_actual_return = None
        if has_actual_return_str is not None:
            has_actual_return = str(has_actual_return_str).lower() in ("true", "1", "yes")
        borrowings = self.borrowing_service.list_borrowings(
            user_id=user.id,
            is_admin=user.is_admin,
            filter_user_id=filter_user_id,
            is_active=is_active,
            has_actual_return_date=has_actual_return,
        )
        return success_response(borrowings)

    def get_borrowing(self, token: str, borrowing_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            borrowing = self.borrowing_service.get_borrowing(
                borrowing_id=borrowing_id,
                user_id=user.id,
                is_admin=user.is_admin,
            )
            return success_response(borrowing)
        except ValueError as e:
            return error_response(str(e), status=404)

    def create_borrowing(self, token: str, request_data: Dict) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            borrowing = self.borrowing_service.create_borrowing(
                book_id=request_data.get("book_id", ""),
                user_id=user.id,
                expected_return_date=request_data.get("expected_return_date", ""),
            )
            return success_response(borrowing, status=201)
        except ValueError as e:
            return error_response(str(e), status=400)

    def return_borrowing(self, token: str, borrowing_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            borrowing = self.borrowing_service.return_borrowing(
                borrowing_id=borrowing_id,
                user_id=user.id,
                is_admin=user.is_admin,
            )
            return success_response(borrowing)
        except ValueError as e:
            return error_response(str(e), status=400)

class PaymentController:
    def __init__(self):
        self.payment_service = PaymentService()
        self.auth_service = AuthService()

    def _get_user(self, token: str) -> Optional[User]:
        return self.auth_service.get_current_user(token)

    def list_payments(self, token: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        payments = self.payment_service.list_payments(user_id=user.id, is_admin=user.is_admin)
        return success_response(payments)

    def get_payment(self, token: str, payment_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            payment = self.payment_service.get_payment(
                payment_id=payment_id,
                user_id=user.id,
                is_admin=user.is_admin,
            )
            return success_response(payment)
        except ValueError as e:
            return error_response(str(e), status=404)

    def payment_success(self, token: str, session_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            payment = self.payment_service.process_payment_success(
                session_id=session_id,
                user_id=user.id,
                is_admin=user.is_admin,
            )
            return success_response({"message": "Payment successful", "payment": payment})
        except ValueError as e:
            return error_response(str(e), status=400)

    def payment_cancel(self, token: str, session_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            result = self.payment_service.process_payment_cancel(
                session_id=session_id,
                user_id=user.id,
                is_admin=user.is_admin,
            )
            return success_response(result)
        except ValueError as e:
            return error_response(str(e), status=400)

    def renew_payment_session(self, token: str, payment_id: str) -> Response:
        user = self._get_user(token)
        if not user:
            return error_response("Authentication required", status=401)
        try:
            payment = self.payment_service.renew_payment_session(
                payment_id=payment_id,
                user_id=user.id,
                is_admin=user.is_admin,
            )
            return success_response(payment)
        except ValueError as e:
            return error_response(str(e), status=400)

# ============================================================
# Admin Panel
# ============================================================

class AdminPanel:
    """Admin panel available at /admin/"""

    def __init__(self):
        self.user_repo = UserRepository()
        self.book_repo = BookRepository()
        self.borrowing_repo = BorrowingRepository()
        self.payment_repo = PaymentRepository()

    def list_users(self) -> List[Dict]:
        return [u.to_dict() for u in self.user_repo.list_all()]

    def get_user(self, user_id: str) -> Optional[Dict]:
        user = self.user_repo.find_by_id(user_id)
        return user.to_dict() if user else None

    def update_user(self, user_id: str, data: Dict) -> Optional[Dict]:
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return None
        if "is_admin" in data:
            user.is_admin = bool(data["is_admin"])
        if "is_active" in data:
            user.is_active = bool(data["is_active"])
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        self.user_repo.update(user)
        return user.to_dict()

    def list_books(self) -> List[Dict]:
        return [b.to_dict() for b in self.book_repo.list_all()]

    def list_borrowings(self) -> List[Dict]:
        return [b.to_dict() for b in self.borrowing_repo.list_all()]

    def list_payments(self) -> List[Dict]:
        return [p.to_dict() for p in self.payment_repo.list_all()]

    def get_statistics(self) -> Dict:
        users = self.user_repo.list_all()
        books = self.book_repo.list_all()
        borrowings = self.borrowing_repo.list_all()
        payments = self.payment_repo.list_all()
        active_borrowings = [b for b in borrowings if b.is_active]
        overdue_borrowings = [b for b in borrowings if b.is_overdue]
        paid_payments = [p for p in payments if p.status == PaymentStatus.PAID]
        total_revenue = sum(p.money_to_pay for p in paid_payments)
        return {
            "total_users": len(users),
            "total_books": len(books),
            "total_borrowings": len(borrowings),
            "active_borrowings": len(active_borrowings),
            "overdue_borrowings": len(overdue_borrowings),
            "total_payments": len(payments),
            "paid_payments": len(paid_payments),
            "total_revenue": str(total_revenue),
        }

# ============================================================
# API Router (simulating URL routing)
# ============================================================

class APIRouter:
    """
    Simulates the API routing structure:
    - /api/v1/auth/register/
    - /api/v1/auth/login/
    - /api/v1/auth/refresh/
    - /api/v1/auth/me/
    - /api/v1/books/
    - /api/v1/books/{id}/
    - /api/v1/borrowings/
    - /api/v1/borrowings/{id}/
    - /api/v1/borrowings/{id}/return/
    - /api/v1/payments/
    - /api/v1/payments/{id}/
    - /api/v1/payments/success/
    - /api/v1/payments/cancel/
    - /api/v1/payments/{id}/renew/
    - /admin/
    - /api/v1/doc/swagger/
    """

    def __init__(self):
        self.auth_controller = AuthController()
        self.book_controller = BookController()
        self.borrowing_controller = BorrowingController()
        self.payment_controller = PaymentController()
        self.admin_panel = AdminPanel()

    def handle_request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Response:
        data = data or {}
        params = params or {}
        path = path.rstrip("/")

        # Auth endpoints
        if path == "/api/v1/auth/register" and method == "POST":
            return self.auth_controller.register(data)
        elif path == "/api/v1/auth/login" and method == "POST":
            return self.auth_controller.login(data)
        elif path == "/api/v1/auth/refresh" and method == "POST":
            return self.auth_controller.refresh(data)
        elif path == "/api/v1/auth/me" and method == "GET":
            return self.auth_controller.me(token or "")
        elif path == "/api/v1/auth/me" and method in ("PUT", "PATCH"):
            return self.auth_controller.update_me(token or "", data)

        # Book endpoints
        elif path == "/api/v1/books" and method == "GET":
            return self.book_controller.list_books(token)
        elif path == "/api/v1/books" and method == "POST":
            return self.book_controller.create_book(token or "", data)
        elif re.match(r"^/api/v1/books/([^/]+)$", path):
            book_id = re.match(r"^/api/v1/books/([^/]+)$", path).group(1)
            if method == "GET":
                return self.book_controller.get_book(book_id, token)
            elif method in ("PUT", "PATCH"):
                return self.book_controller.update_book(token or "", book_id, data)
            elif method == "DELETE":
                return self.book_controller.delete_book(token or "", book_id)

        # Borrowing endpoints
        elif path == "/api/v1/borrowings" and method == "GET":
            return self.borrowing_controller.list_borrowings(token or "", params)
        elif path == "/api/v1/borrowings" and method == "POST":
            return self.borrowing_controller.create_borrowing(token or "", data)
        elif re.match(r"^/api/v1/borrowings/([^/]+)/return$", path):
            borrowing_id = re.match(r"^/api/v1/borrowings/([^/]+)/return$", path).group(1)
            if method == "POST":
                return self.borrowing_controller.return_borrowing(token or "", borrowing_id)
        elif re.match(r"^/api/v1/borrowings/([^/]+)$", path):
            borrowing_id = re.match(r"^/api/v1/borrowings/([^/]+)$", path).group(1)
            if method == "GET":
                return self.borrowing_controller.get_borrowing(token or "", borrowing_id)

        # Payment endpoints
        elif path == "/api/v1/payments" and method == "GET":
            return self.payment_controller.list_payments(token or "")
        elif re.match(r"^/api/v1/payments/success/([^/]+)$", path):
            session_id = re.match(r"^/api/v1/payments/success/([^/]+)$", path).group(1)
            if method == "GET":
                return self.payment_controller.payment_success(token or "", session_id)
        elif re.match(r"^/api/v1/payments/cancel/([^/]+)$", path):
            session_id = re.match(r"^/api/v1/payments/cancel/([^/]+)$", path).group(1)
            if method == "GET":
                return self.payment_controller.payment_cancel(token or "", session_id)
        elif re.match(r"^/api/v1/payments/([^/]+)/renew$", path):
            payment_id = re.match(r"^/api/v1/payments/([^/]+)/renew$", path).group(1)
            if method == "POST":
                return self.payment_controller.renew_payment_session(token or "", payment_id)
        elif re.match(r"^/api/v1/payments/([^/]+)$", path):
            payment_id = re.match(r"^/api/v1/payments/([^/]+)$", path).group(1)
            if method == "GET":
                return self.payment_controller.get_payment(token or "", payment_id)

        # Admin panel
        elif path == "/admin" and method == "GET":
            return success_response({
                "message": "Admin Panel",
                "statistics": self.admin_panel.get_statistics(),
                "endpoints": [
                    "/admin/users/",
                    "/admin/books/",
                    "/admin/borrowings/",
                    "/admin/payments/",
                ],
            })
        elif path == "/admin/users" and method == "GET":
            return success_response(self.admin_panel.list_users())
        elif path == "/admin/books" and method == "GET":
            return success_response(self.admin_panel.list_books())
        elif path == "/admin/borrowings" and method == "GET":
            return success_response(self.admin_panel.list_borrowings())
        elif path == "/admin/payments" and method == "GET":
            return success_response(self.admin_panel.list_payments())

        # Swagger documentation
        elif path == "/api/v1/doc/swagger" and method == "GET":
            return success_response(self._get_swagger_spec())

        return error_response("Not found", status=404)

    def _get_swagger_spec(self) -> Dict:
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Library Service API",
                "version": "1.0.0",
                "description": "API Library service for borrowing books",
            },
            "paths": {
                "/api/v1/auth/register/": {
                    "post": {
                        "summary": "Register a new user",
                        "tags": ["auth"],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "email": {"type": "string"},
                                            "password": {"type": "string"},
                                            "first_name": {"type": "string"},
                                            "last_name": {"type": "string"},
                                        },
                                        "required": ["email", "password"],
                                    }
                                }
                            }
                        },
                    }
                },
                "/api/v1/auth/login/": {
                    "post": {
                        "summary": "Login and get JWT tokens",
                        "tags": ["auth"],
                    }
                },
                "/api/v1/auth/refresh/": {
                    "post": {
                        "summary": "Refresh access token",
                        "tags": ["auth"],
                    }
                },
                "/api/v1/auth/me/": {
                    "get": {
                        "summary": "Get current user profile",
                        "tags": ["auth"],
                        "security": [{"bearerAuth": []}],
                    },
                    "put": {
                        "summary": "Update current user profile",
                        "tags": ["auth"],
                        "security": [{"bearerAuth": []}],
                    },
                },
                "/api/v1/books/": {
                    "get": {
                        "summary": "List all books",
                        "tags": ["books"],
                    },
                    "post": {
                        "summary": "Create a new book (admin only)",
                        "tags": ["books"],
                        "security": [{"bearerAuth": []}],
                    },
                },
                "/api/v1/books/{id}/": {
                    "get": {"summary": "Get book details", "tags": ["books"]},
                    "put": {"summary": "Update book (admin only)", "tags": ["books"], "security": [{"bearerAuth": []}]},
                    "delete": {"summary": "Delete book (admin only)", "tags": ["books"], "security": [{"bearerAuth": []}]},
                },
                "/api/v1/borrowings/": {
                    "get": {
                        "summary": "List borrowings",
                        "tags": ["borrowings"],
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {
                                "name": "is_active",
                                "in": "query",
                                "description": "Filter by active status",
                                "schema": {"type": "boolean"},
                            },
                            {
                                "name": "user_id",
                                "in": "query",
                                "description": "Filter by user ID (admin only)",
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "has_actual_return_date",
                                "in": "query",
                                "description": "Filter by actual return date presence",
                                "schema": {"type": "boolean"},
                            },
                        ],
                    },
                    "post": {
                        "summary": "Create a new borrowing",
                        "tags": ["borrowings"],
                        "security": [{"bearerAuth": []}],
                    },
                },
                "/api/v1/borrowings/{id}/": {
                    "get": {"summary": "Get borrowing details", "tags": ["borrowings"], "security": [{"bearerAuth": []}]},
                },
                "/api/v1/borrowings/{id}/return/": {
                    "post": {
                        "summary": "Return a borrowing",
                        "tags": ["borrowings"],
                        "security": [{"bearerAuth": []}],
                    }
                },
                "/api/v1/payments/": {
                    "get": {
                        "summary": "List payments",
                        "tags": ["payments"],
                        "security": [{"bearerAuth": []}],
                    }
                },
                "/api/v1/payments/{id}/": {
                    "get": {"summary": "Get payment details", "tags": ["payments"], "security": [{"bearerAuth": []}]},
                },
                "/api/v1/payments/success/{session_id}/": {
                    "get": {
                        "summary": "Handle successful payment",
                        "tags": ["payments"],
                        "security": [{"bearerAuth": []}],
                    }
                },
                "/api/v1/payments/cancel/{session_id}/": {
                    "get": {
                        "summary": "Handle cancelled payment",
                        "tags": ["payments"],
                        "security": [{"bearerAuth": []}],
                    }
                },
                "/api/v1/payments/{id}/renew/": {
                    "post": {
                        "summary": "Renew payment session",
                        "tags": ["payments"],
                        "security": [{"bearerAuth": []}],
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
            },
        }

# ============================================================
# Application Entry Point
# ============================================================

class LibraryServiceApp:
    """Main application class for the Library Service API"""

    def __init__(self):
        self.router = APIRouter()
        self._setup_initial_data()

    def _setup_initial_data(self):
        """Setup initial admin user and sample data"""
        user_repo = UserRepository()
        # Create admin user if not exists
        if not user_repo.find_by_email("admin@library.com"):
            user_repo.create(
                email="admin@library.com",
                password="admin12345",
                first_name="Admin",
                last_name="User",
                is_admin=True,
            )

    def request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        response = self.router.handle_request(
            method=method,
            path=path,
            token=token,
            data=data,
            params=params,
        )
        return response.to_dict()

    def run(self):
        """Run a demonstration of the library service"""
        print("=" * 60)
        print("Library Service API - Demonstration")
        print("=" * 60)

        # Register a user
        print("\n1. Registering a new user...")
        result = self.request("POST", "/api/v1/auth/register", data={
            "email": "user@example.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        })
        print(f"   Status: {result['status']}")
        if result['status'] == 201:
            print(f"   User created: {result['data']['email']}")

        # Login as admin
        print("\n2. Logging in as admin...")
        result = self.request("POST", "/api/v1/auth/login", data={
            "email": "admin@library.com",
            "password": "admin12345",
        })
        print(f"   Status: {result['status']}")
        admin_token = None
        if result['status'] == 200:
            admin_token = result['data']['access']
            print(f"   Admin logged in: {result['data']['user']['email']}")

        # Login as regular user
        print("\n3. Logging in as regular user...")
        result = self.request("POST", "/api/v1/auth/login", data={
            "email": "user@example.com",
            "password": "password123",
        })
        user_token = None
        if result['status'] == 200:
            user_token = result['data']['access']
            print(f"   User logged in: {result['data']['user']['email']}")

        # Create a book (admin)
        print("\n4. Creating a book (admin)...")
        result = self.request("POST", "/api/v1/books", token=admin_token, data={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "cover": CoverType.HARD,
            "inventory": 5,
            "daily_fee": "2.50",
        })
        print(f"   Status: {result['status']}")
        book_id = None
        if result['status'] == 201:
            book_id = result['data']['id']
            print(f"   Book created: {result['data']['title']}")

        # List books
        print("\n5. Listing all books...")
        result = self.request("GET", "/api/v1/books")
        print(f"   Status: {result['status']}")
        if result['status'] == 200:
            print(f"   Total books: {len(result['data'])}")

        # Create a borrowing
        print("\n6. Creating a borrowing...")
        future_date = (date.today() + timedelta(days=14)).isoformat()
        result = self.request("POST", "/api/v1/borrowings", token=user_token, data={
            "book_id": book_id,
            "expected_return_date": future_date,
        })
        print(f"   Status: {result['status']}")
        borrowing_id = None
        if result['status'] == 201:
            borrowing_id = result['data']['id']
            print(f"   Borrowing created: {result['data']['id']}")
            print(f"   Expected return: {result['data']['expected_return_date']}")

        # List borrowings with filters
        print("\n7. Listing active borrowings...")
        result = self.request("GET", "/api/v1/borrowings", token=user_token, params={"is_active": "true"})
        print(f"   Status: {result['status']}")
        if result['status'] == 200:
            print(f"   Active borrowings: {len(result['data'])}")

        # List payments
        print("\n8. Listing payments...")
        result = self.request("GET", "/api/v1/payments", token=user_token)
        print(f"   Status: {result['status']}")
        payment_id = None
        session_id = None
        if result['status'] == 200:
            print(f"   Total payments: {len(result['data'])}")
            if result['data']:
                payment_id = result['data'][0]['id']
                session_id = result['data'][0]['session_id']
                print(f"   Payment amount: ${result['data'][0]['money_to_pay']}")
                print(f"   Payment type: {result['data'][0]['payment_type']}")

        # Process payment success
        if session_id:
            print("\n9. Processing payment success...")
            result = self.request("GET", f"/api/v1/payments/success/{session_id}", token=user_token)
            print(f"   Status: {result['status']}")
            if result['status'] == 200:
                print(f"   Payment status: {result['data']['payment']['status']}")

        # Return borrowing
        if borrowing_id:
            print("\n10. Returning borrowing...")
            result = self.request("POST", f"/api/v1/borrowings/{borrowing_id}/return", token=user_token)
            print(f"    Status: {result['status']}")
            if result['status'] == 200:
                print(f"    Actual return date: {result['data']['actual_return_date']}")

        # Admin statistics
        print("\n11. Admin panel statistics...")
        result = self.request("GET", "/admin", token=admin_token)
        print(f"    Status: {result['status']}")
        if result['status'] == 200:
            stats = result['data']['statistics']
            print(f"    Total users: {stats['total_users']}")
            print(f"    Total books: {stats['total_books']}")
            print(f"    Total borrowings: {stats['total_borrowings']}")
            print(f"    Total revenue: ${stats['total_revenue']}")

        # Swagger docs
        print("\n12. API Documentation at /api/v1/doc/swagger/")
        result = self.request("GET", "/api/v1/doc/swagger")
        print(f"    Status: {result['status']}")
        if result['status'] == 200:
            print(f"    API Title: {result['data']['info']['title']}")
            print(f"    API Version: {result['data']['info']['version']}")
            print(f"    Endpoints documented: {len(result['data']['paths'])}")

        print("\n" + "=" * 60)
        print("Library Service API demonstration complete!")
        print("=" * 60)


if __name__ == "__main__":
    app = LibraryServiceApp()
    app.run()