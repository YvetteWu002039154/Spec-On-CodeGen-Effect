#!/usr/bin/env python3
"""
Library Service API - Complete Implementation
JWT authentication, book borrowing, payments, and fine management
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
JWT_EXPIRY_HOURS = 24
FINE_MULTIPLIER = Decimal("2.0")  # Fine is 2x daily fee per overdue day

# ============================================================
# In-Memory Database
# ============================================================

class Database:
    def __init__(self):
        self.users: Dict[str, Dict] = {}
        self.books: Dict[str, Dict] = {}
        self.borrowings: Dict[str, Dict] = {}
        self.payments: Dict[str, Dict] = {}
        self._init_admin()

    def _init_admin(self):
        admin_id = str(uuid.uuid4())
        self.users[admin_id] = {
            "id": admin_id,
            "email": "admin@library.com",
            "password": self._hash_password("admin123"),
            "first_name": "Admin",
            "last_name": "User",
            "is_staff": True,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _hash_password(self, password: str) -> str:
        salt = "library_salt"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        return self._hash_password(password) == hashed

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        return self.users.get(user_id)

    def get_book_by_id(self, book_id: str) -> Optional[Dict]:
        return self.books.get(book_id)

    def get_borrowing_by_id(self, borrowing_id: str) -> Optional[Dict]:
        return self.borrowings.get(borrowing_id)

    def get_payment_by_id(self, payment_id: str) -> Optional[Dict]:
        return self.payments.get(payment_id)


db = Database()


# ============================================================
# JWT Implementation
# ============================================================

class JWT:
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    @classmethod
    def create_token(cls, payload: Dict) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_encoded = cls._base64url_encode(json.dumps(header).encode())
        payload_encoded = cls._base64url_encode(json.dumps(payload).encode())
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            SECRET_KEY.encode(), message.encode(), hashlib.sha256
        ).digest()
        signature_encoded = cls._base64url_encode(signature)
        return f"{message}.{signature_encoded}"

    @classmethod
    def decode_token(cls, token: str) -> Optional[Dict]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_encoded, payload_encoded, signature_encoded = parts
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                SECRET_KEY.encode(), message.encode(), hashlib.sha256
            ).digest()
            expected_encoded = cls._base64url_encode(expected_signature)
            if not hmac.compare_digest(signature_encoded, expected_encoded):
                return None
            payload = json.loads(cls._base64url_decode(payload_encoded))
            if "exp" in payload:
                if datetime.utcnow().timestamp() > payload["exp"]:
                    return None
            return payload
        except Exception:
            return None

    @classmethod
    def create_access_token(cls, user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "type": "access",
            "exp": (datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
        }
        return cls.create_token(payload)

    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": (datetime.utcnow() + timedelta(days=7)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
        }
        return cls.create_token(payload)


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


class Book:
    def __init__(
        self,
        title: str,
        author: str,
        cover: str,
        inventory: int,
        daily_fee: Decimal,
    ):
        self.id = str(uuid.uuid4())
        self.title = title
        self.author = author
        self.cover = cover
        self.inventory = inventory
        self.daily_fee = Decimal(str(daily_fee))
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
        book.created_at = data["created_at"]
        return book


class User:
    def __init__(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        is_staff: bool = False,
    ):
        self.id = str(uuid.uuid4())
        self.email = email
        self.password = self._hash_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_staff = is_staff
        self.is_active = True
        self.created_at = datetime.utcnow().isoformat()

    def _hash_password(self, password: str) -> str:
        salt = "library_salt"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_staff": self.is_staff,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class Borrowing:
    def __init__(
        self,
        book_id: str,
        user_id: str,
        expected_return_date: str,
    ):
        self.id = str(uuid.uuid4())
        self.borrow_date = date.today().isoformat()
        self.expected_return_date = expected_return_date
        self.actual_return_date: Optional[str] = None
        self.book_id = book_id
        self.user_id = user_id
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self, include_book: bool = True, include_user: bool = False) -> Dict:
        data = {
            "id": self.id,
            "borrow_date": self.borrow_date,
            "expected_return_date": self.expected_return_date,
            "actual_return_date": self.actual_return_date,
            "book_id": self.book_id,
            "user_id": self.user_id,
            "is_active": self.actual_return_date is None,
            "created_at": self.created_at,
        }
        if include_book:
            book_data = db.get_book_by_id(self.book_id)
            if book_data:
                data["book"] = book_data
        if include_user:
            user_data = db.get_user_by_id(self.user_id)
            if user_data:
                safe_user = {k: v for k, v in user_data.items() if k != "password"}
                data["user"] = safe_user
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Borrowing":
        borrowing = cls.__new__(cls)
        borrowing.id = data["id"]
        borrowing.borrow_date = data["borrow_date"]
        borrowing.expected_return_date = data["expected_return_date"]
        borrowing.actual_return_date = data.get("actual_return_date")
        borrowing.book_id = data["book_id"]
        borrowing.user_id = data["user_id"]
        borrowing.created_at = data["created_at"]
        return borrowing

    def calculate_days_borrowed(self) -> int:
        borrow = date.fromisoformat(self.borrow_date)
        end = date.today() if not self.actual_return_date else date.fromisoformat(self.actual_return_date)
        return max(1, (end - borrow).days)

    def calculate_overdue_days(self) -> int:
        expected = date.fromisoformat(self.expected_return_date)
        end = date.today() if not self.actual_return_date else date.fromisoformat(self.actual_return_date)
        overdue = (end - expected).days
        return max(0, overdue)

    def is_overdue(self) -> bool:
        return self.calculate_overdue_days() > 0


class Payment:
    def __init__(
        self,
        borrowing_id: str,
        user_id: str,
        payment_type: str,
        money_to_pay: Decimal,
    ):
        self.id = str(uuid.uuid4())
        self.status = PaymentStatus.PENDING
        self.type = payment_type
        self.borrowing_id = borrowing_id
        self.user_id = user_id
        self.session_url = f"https://checkout.stripe.com/pay/session_{uuid.uuid4().hex}"
        self.session_id = f"cs_{uuid.uuid4().hex}"
        self.money_to_pay = Decimal(str(money_to_pay))
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "status": self.status,
            "type": self.type,
            "borrowing_id": self.borrowing_id,
            "user_id": self.user_id,
            "session_url": self.session_url,
            "session_id": self.session_id,
            "money_to_pay": str(self.money_to_pay),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Payment":
        payment = cls.__new__(cls)
        payment.id = data["id"]
        payment.status = data["status"]
        payment.type = data["type"]
        payment.borrowing_id = data["borrowing_id"]
        payment.user_id = data["user_id"]
        payment.session_url = data["session_url"]
        payment.session_id = data["session_id"]
        payment.money_to_pay = Decimal(str(data["money_to_pay"]))
        payment.created_at = data["created_at"]
        return payment


# ============================================================
# Validators
# ============================================================

class ValidationError(Exception):
    def __init__(self, errors: Dict):
        self.errors = errors
        super().__init__(str(errors))


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_date_format(date_str: str) -> bool:
    try:
        date.fromisoformat(date_str)
        return True
    except (ValueError, TypeError):
        return False


def validate_book_data(data: Dict, partial: bool = False) -> Dict:
    errors = {}
    if not partial or "title" in data:
        if not data.get("title"):
            errors["title"] = "Title is required."
        elif len(data["title"]) > 255:
            errors["title"] = "Title must be at most 255 characters."

    if not partial or "author" in data:
        if not data.get("author"):
            errors["author"] = "Author is required."
        elif len(data["author"]) > 255:
            errors["author"] = "Author must be at most 255 characters."

    if not partial or "cover" in data:
        if not data.get("cover"):
            errors["cover"] = "Cover is required."
        elif data["cover"] not in CoverType.CHOICES:
            errors["cover"] = f"Cover must be one of {CoverType.CHOICES}."

    if not partial or "inventory" in data:
        if "inventory" not in data and not partial:
            errors["inventory"] = "Inventory is required."
        elif "inventory" in data:
            try:
                inv = int(data["inventory"])
                if inv < 0:
                    errors["inventory"] = "Inventory must be non-negative."
            except (ValueError, TypeError):
                errors["inventory"] = "Inventory must be an integer."

    if not partial or "daily_fee" in data:
        if "daily_fee" not in data and not partial:
            errors["daily_fee"] = "Daily fee is required."
        elif "daily_fee" in data:
            try:
                fee = Decimal(str(data["daily_fee"]))
                if fee <= 0:
                    errors["daily_fee"] = "Daily fee must be positive."
            except Exception:
                errors["daily_fee"] = "Daily fee must be a valid decimal number."

    if errors:
        raise ValidationError(errors)
    return data


def validate_user_registration(data: Dict) -> Dict:
    errors = {}
    if not data.get("email"):
        errors["email"] = "Email is required."
    elif not validate_email(data["email"]):
        errors["email"] = "Enter a valid email address."
    elif db.get_user_by_email(data["email"]):
        errors["email"] = "A user with this email already exists."

    if not data.get("password"):
        errors["password"] = "Password is required."
    elif len(data["password"]) < 8:
        errors["password"] = "Password must be at least 8 characters."

    if errors:
        raise ValidationError(errors)
    return data


def validate_borrowing_data(data: Dict) -> Dict:
    errors = {}
    if not data.get("book_id"):
        errors["book_id"] = "Book ID is required."

    if not data.get("expected_return_date"):
        errors["expected_return_date"] = "Expected return date is required."
    elif not validate_date_format(data["expected_return_date"]):
        errors["expected_return_date"] = "Invalid date format. Use YYYY-MM-DD."
    else:
        expected = date.fromisoformat(data["expected_return_date"])
        if expected <= date.today():
            errors["expected_return_date"] = "Expected return date must be in the future."

    if errors:
        raise ValidationError(errors)
    return data


# ============================================================
# Response Helpers
# ============================================================

class Response:
    def __init__(self, data: Any, status: int = 200, headers: Dict = None):
        self.data = data
        self.status = status
        self.headers = headers or {}

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "data": self.data,
            "headers": self.headers,
        }


def success_response(data: Any, status: int = 200) -> Dict:
    return {"success": True, "data": data, "status": status}


def error_response(message: Any, status: int = 400) -> Dict:
    return {"success": False, "error": message, "status": status}


def paginate(items: List, page: int = 1, page_size: int = 10) -> Dict:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "count": total,
        "next": f"?page={page + 1}" if end < total else None,
        "previous": f"?page={page - 1}" if page > 1 else None,
        "results": items[start:end],
    }


# ============================================================
# Authentication Service
# ============================================================

class AuthService:
    @staticmethod
    def register(data: Dict) -> Dict:
        validate_user_registration(data)
        user = User(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )
        db.users[user.id] = {
            "id": user.id,
            "email": user.email,
            "password": user.password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": False,
            "is_active": True,
            "created_at": user.created_at,
        }
        return success_response(user.to_dict(), 201)

    @staticmethod
    def login(email: str, password: str) -> Dict:
        user = db.get_user_by_email(email)
        if not user or not db.verify_password(password, user["password"]):
            return error_response("Invalid email or password.", 401)
        if not user["is_active"]:
            return error_response("Account is disabled.", 401)
        access_token = JWT.create_access_token(user["id"])
        refresh_token = JWT.create_refresh_token(user["id"])
        return success_response(
            {
                "access": access_token,
                "refresh": refresh_token,
                "user": {k: v for k, v in user.items() if k != "password"},
            }
        )

    @staticmethod
    def refresh_token(refresh_token: str) -> Dict:
        payload = JWT.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return error_response("Invalid or expired refresh token.", 401)
        user = db.get_user_by_id(payload["user_id"])
        if not user:
            return error_response("User not found.", 401)
        access_token = JWT.create_access_token(user["id"])
        return success_response({"access": access_token})

    @staticmethod
    def get_current_user(token: str) -> Optional[Dict]:
        payload = JWT.decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        return db.get_user_by_id(payload["user_id"])

    @staticmethod
    def update_profile(user_id: str, data: Dict) -> Dict:
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response("User not found.", 404)
        if "first_name" in data:
            user["first_name"] = data["first_name"]
        if "last_name" in data:
            user["last_name"] = data["last_name"]
        if "password" in data:
            if len(data["password"]) < 8:
                return error_response({"password": "Password must be at least 8 characters."}, 400)
            salt = "library_salt"
            user["password"] = hashlib.sha256(f"{salt}{data['password']}".encode()).hexdigest()
        db.users[user_id] = user
        return success_response({k: v for k, v in user.items() if k != "password"})


# ============================================================
# Book Service
# ============================================================

class BookService:
    @staticmethod
    def list_books(filters: Dict = None) -> Dict:
        books = list(db.books.values())
        if filters:
            if filters.get("title"):
                books = [b for b in books if filters["title"].lower() in b["title"].lower()]
            if filters.get("author"):
                books = [b for b in books if filters["author"].lower() in b["author"].lower()]
            if filters.get("cover"):
                books = [b for b in books if b["cover"] == filters["cover"]]
            if filters.get("available") == "true":
                books = [b for b in books if b["inventory"] > 0]
        page = int(filters.get("page", 1)) if filters else 1
        return success_response(paginate(books, page))

    @staticmethod
    def get_book(book_id: str) -> Dict:
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found.", 404)
        return success_response(book)

    @staticmethod
    def create_book(data: Dict) -> Dict:
        validate_book_data(data)
        book = Book(
            title=data["title"],
            author=data["author"],
            cover=data["cover"],
            inventory=int(data["inventory"]),
            daily_fee=Decimal(str(data["daily_fee"])),
        )
        db.books[book.id] = book.to_dict()
        return success_response(book.to_dict(), 201)

    @staticmethod
    def update_book(book_id: str, data: Dict, partial: bool = False) -> Dict:
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found.", 404)
        validate_book_data(data, partial=partial)
        if "title" in data:
            book["title"] = data["title"]
        if "author" in data:
            book["author"] = data["author"]
        if "cover" in data:
            book["cover"] = data["cover"]
        if "inventory" in data:
            book["inventory"] = int(data["inventory"])
        if "daily_fee" in data:
            book["daily_fee"] = str(Decimal(str(data["daily_fee"])))
        db.books[book_id] = book
        return success_response(book)

    @staticmethod
    def delete_book(book_id: str) -> Dict:
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found.", 404)
        active_borrowings = [
            b for b in db.borrowings.values()
            if b["book_id"] == book_id and b.get("actual_return_date") is None
        ]
        if active_borrowings:
            return error_response("Cannot delete book with active borrowings.", 400)
        del db.books[book_id]
        return success_response(None, 204)


# ============================================================
# Borrowing Service
# ============================================================

class BorrowingService:
    @staticmethod
    def list_borrowings(user: Dict, filters: Dict = None) -> Dict:
        borrowings = list(db.borrowings.values())
        if not user["is_staff"]:
            borrowings = [b for b in borrowings if b["user_id"] == user["id"]]
        if filters:
            if filters.get("is_active") == "true":
                borrowings = [b for b in borrowings if b.get("actual_return_date") is None]
            elif filters.get("is_active") == "false":
                borrowings = [b for b in borrowings if b.get("actual_return_date") is not None]
            if filters.get("user_id") and user["is_staff"]:
                borrowings = [b for b in borrowings if b["user_id"] == filters["user_id"]]
            if filters.get("actual_return_date"):
                borrowings = [
                    b for b in borrowings
                    if b.get("actual_return_date") == filters["actual_return_date"]
                ]
        result = []
        for b_data in borrowings:
            borrowing = Borrowing.from_dict(b_data)
            result.append(borrowing.to_dict(include_book=True, include_user=user["is_staff"]))
        page = int(filters.get("page", 1)) if filters else 1
        return success_response(paginate(result, page))

    @staticmethod
    def get_borrowing(borrowing_id: str, user: Dict) -> Dict:
        borrowing_data = db.get_borrowing_by_id(borrowing_id)
        if not borrowing_data:
            return error_response("Borrowing not found.", 404)
        if not user["is_staff"] and borrowing_data["user_id"] != user["id"]:
            return error_response("Permission denied.", 403)
        borrowing = Borrowing.from_dict(borrowing_data)
        return success_response(borrowing.to_dict(include_book=True, include_user=user["is_staff"]))

    @staticmethod
    def create_borrowing(data: Dict, user: Dict) -> Dict:
        validate_borrowing_data(data)
        book = db.get_book_by_id(data["book_id"])
        if not book:
            return error_response("Book not found.", 404)
        if book["inventory"] <= 0:
            return error_response("Book is not available (inventory is 0).", 400)
        pending_payments = [
            p for p in db.payments.values()
            if p["user_id"] == user["id"] and p["status"] == PaymentStatus.PENDING
        ]
        if pending_payments:
            return error_response(
                "You have pending payments. Please complete them before borrowing.", 400
            )
        borrowing = Borrowing(
            book_id=data["book_id"],
            user_id=user["id"],
            expected_return_date=data["expected_return_date"],
        )
        book["inventory"] -= 1
        db.books[book["id"]] = book
        borrowing_dict = {
            "id": borrowing.id,
            "borrow_date": borrowing.borrow_date,
            "expected_return_date": borrowing.expected_return_date,
            "actual_return_date": borrowing.actual_return_date,
            "book_id": borrowing.book_id,
            "user_id": borrowing.user_id,
            "created_at": borrowing.created_at,
        }
        db.borrowings[borrowing.id] = borrowing_dict
        days = (date.fromisoformat(borrowing.expected_return_date) - date.fromisoformat(borrowing.borrow_date)).days
        money_to_pay = Decimal(str(book["daily_fee"])) * max(1, days)
        payment = Payment(
            borrowing_id=borrowing.id,
            user_id=user["id"],
            payment_type=PaymentType.PAYMENT,
            money_to_pay=money_to_pay,
        )
        db.payments[payment.id] = payment.to_dict()
        result = borrowing.to_dict(include_book=True)
        result["payment"] = payment.to_dict()
        return success_response(result, 201)

    @staticmethod
    def return_borrowing(borrowing_id: str, user: Dict) -> Dict:
        borrowing_data = db.get_borrowing_by_id(borrowing_id)
        if not borrowing_data:
            return error_response("Borrowing not found.", 404)
        if not user["is_staff"] and borrowing_data["user_id"] != user["id"]:
            return error_response("Permission denied.", 403)
        if borrowing_data.get("actual_return_date"):
            return error_response("Book has already been returned.", 400)
        borrowing = Borrowing.from_dict(borrowing_data)
        borrowing.actual_return_date = date.today().isoformat()
        borrowing_data["actual_return_date"] = borrowing.actual_return_date
        db.borrowings[borrowing_id] = borrowing_data
        book = db.get_book_by_id(borrowing.book_id)
        if book:
            book["inventory"] += 1
            db.books[book["id"]] = book
        fine_payment = None
        if borrowing.is_overdue():
            overdue_days = borrowing.calculate_overdue_days()
            daily_fee = Decimal(str(book["daily_fee"])) if book else Decimal("0")
            fine_amount = daily_fee * FINE_MULTIPLIER * overdue_days
            fine = Payment(
                borrowing_id=borrowing_id,
                user_id=borrowing.user_id,
                payment_type=PaymentType.FINE,
                money_to_pay=fine_amount,
            )
            db.payments[fine.id] = fine.to_dict()
            fine_payment = fine.to_dict()
        result = borrowing.to_dict(include_book=True)
        result["overdue_days"] = borrowing.calculate_overdue_days()
        if fine_payment:
            result["fine_payment"] = fine_payment
        return success_response(result)


# ============================================================
# Payment Service
# ============================================================

class PaymentService:
    @staticmethod
    def list_payments(user: Dict, filters: Dict = None) -> Dict:
        payments = list(db.payments.values())
        if not user["is_staff"]:
            payments = [p for p in payments if p["user_id"] == user["id"]]
        if filters:
            if filters.get("status"):
                payments = [p for p in payments if p["status"] == filters["status"]]
            if filters.get("type"):
                payments = [p for p in payments if p["type"] == filters["type"]]
            if filters.get("user_id") and user["is_staff"]:
                payments = [p for p in payments if p["user_id"] == filters["user_id"]]
            if filters.get("borrowing_id"):
                payments = [p for p in payments if p["borrowing_id"] == filters["borrowing_id"]]
        page = int(filters.get("page", 1)) if filters else 1
        return success_response(paginate(payments, page))

    @staticmethod
    def get_payment(payment_id: str, user: Dict) -> Dict:
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            return error_response("Payment not found.", 404)
        if not user["is_staff"] and payment["user_id"] != user["id"]:
            return error_response("Permission denied.", 403)
        return success_response(payment)

    @staticmethod
    def process_payment(payment_id: str, user: Dict) -> Dict:
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            return error_response("Payment not found.", 404)
        if not user["is_staff"] and payment["user_id"] != user["id"]:
            return error_response("Permission denied.", 403)
        if payment["status"] == PaymentStatus.PAID:
            return error_response("Payment has already been processed.", 400)
        payment["status"] = PaymentStatus.PAID
        db.payments[payment_id] = payment
        return success_response(
            {
                "message": "Payment processed successfully.",
                "payment": payment,
            }
        )

    @staticmethod
    def cancel_payment(payment_id: str, user: Dict) -> Dict:
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            return error_response("Payment not found.", 404)
        if not user["is_staff"] and payment["user_id"] != user["id"]:
            return error_response("Permission denied.", 403)
        if payment["status"] == PaymentStatus.PAID:
            return error_response("Cannot cancel a completed payment.", 400)
        return success_response(
            {
                "message": "Payment can be completed later. Session URL: " + payment["session_url"],
                "payment": payment,
            }
        )

    @staticmethod
    def stripe_success(session_id: str, user: Dict) -> Dict:
        payment = None
        for p in db.payments.values():
            if p["session_id"] == session_id:
                payment = p
                break
        if not payment:
            return error_response("Payment session not found.", 404)
        if not user["is_staff"] and payment["user_id"] != user["id"]:
            return error_response("Permission denied.", 403)
        payment["status"] = PaymentStatus.PAID
        db.payments[payment["id"]] = payment
        return success_response(
            {
                "message": "Payment successful!",
                "payment": payment,
            }
        )

    @staticmethod
    def stripe_cancel(session_id: str, user: Dict) -> Dict:
        payment = None
        for p in db.payments.values():
            if p["session_id"] == session_id:
                payment = p
                break
        if not payment:
            return error_response("Payment session not found.", 404)
        return success_response(
            {
                "message": "Payment was cancelled. You can complete it within 24 hours.",
                "session_url": payment["session_url"],
                "payment": payment,
            }
        )


# ============================================================
# Admin Service
# ============================================================

class AdminService:
    @staticmethod
    def list_users(admin: Dict, filters: Dict = None) -> Dict:
        if not admin["is_staff"]:
            return error_response("Admin access required.", 403)
        users = [
            {k: v for k, v in u.items() if k != "password"}
            for u in db.users.values()
        ]
        if filters:
            if filters.get("email"):
                users = [u for u in users if filters["email"].lower() in u["email"].lower()]
            if filters.get("is_staff") == "true":
                users = [u for u in users if u["is_staff"]]
            elif filters.get("is_staff") == "false":
                users = [u for u in users if not u["is_staff"]]
        page = int(filters.get("page", 1)) if filters else 1
        return success_response(paginate(users, page))

    @staticmethod
    def get_user(admin: Dict, user_id: str) -> Dict:
        if not admin["is_staff"]:
            return error_response("Admin access required.", 403)
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response("User not found.", 404)
        return success_response({k: v for k, v in user.items() if k != "password"})

    @staticmethod
    def update_user(admin: Dict, user_id: str, data: Dict) -> Dict:
        if not admin["is_staff"]:
            return error_response("Admin access required.", 403)
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response("User not found.", 404)
        if "is_staff" in data:
            user["is_staff"] = bool(data["is_staff"])
        if "is_active" in data:
            user["is_active"] = bool(data["is_active"])
        if "first_name" in data:
            user["first_name"] = data["first_name"]
        if "last_name" in data:
            user["last_name"] = data["last_name"]
        db.users[user_id] = user
        return success_response({k: v for k, v in user.items() if k != "password"})

    @staticmethod
    def delete_user(admin: Dict, user_id: str) -> Dict:
        if not admin["is_staff"]:
            return error_response("Admin access required.", 403)
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response("User not found.", 404)
        if user["is_staff"]:
            return error_response("Cannot delete admin users.", 400)
        del db.users[user_id]
        return success_response(None, 204)

    @staticmethod
    def dashboard(admin: Dict) -> Dict:
        if not admin["is_staff"]:
            return error_response("Admin access required.", 403)
        total_books = len(db.books)
        total_users = len(db.users)
        total_borrowings = len(db.borrowings)
        active_borrowings = sum(
            1 for b in db.borrowings.values() if b.get("actual_return_date") is None
        )
        overdue_borrowings = 0
        for b_data in db.borrowings.values():
            if b_data.get("actual_return_date") is None:
                borrowing = Borrowing.from_dict(b_data)
                if borrowing.is_overdue():
                    overdue_borrowings += 1
        total_revenue = sum(
            Decimal(str(p["money_to_pay"]))
            for p in db.payments.values()
            if p["status"] == PaymentStatus.PAID
        )
        pending_payments = sum(
            1 for p in db.payments.values() if p["status"] == PaymentStatus.PENDING
        )
        return success_response(
            {
                "total_books": total_books,
                "total_users": total_users,
                "total_borrowings": total_borrowings,
                "active_borrowings": active_borrowings,
                "overdue_borrowings": overdue_borrowings,
                "total_revenue": str(total_revenue),
                "pending_payments": pending_payments,
            }
        )


# ============================================================
# API Router / Request Handler
# ============================================================

class APIRouter:
    def __init__(self):
        self.routes: List[Dict] = []

    def add_route(self, method: str, path: str, handler, auth_required: bool = True, admin_required: bool = False):
        self.routes.append(
            {
                "method": method.upper(),
                "path": path,
                "handler": handler,
                "auth_required": auth_required,
                "admin_required": admin_required,
            }
        )

    def match_path(self, pattern: str, path: str) -> Optional[Dict]:
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return None
        params = {}
        for pp, p in zip(pattern_parts, path_parts):
            if pp.startswith("{") and pp.endswith("}"):
                params[pp[1:-1]] = p
            elif pp != p:
                return None
        return params

    def handle_request(
        self,
        method: str,
        path: str,
        data: Dict = None,
        headers: Dict = None,
        query_params: Dict = None,
    ) -> Dict:
        headers = headers or {}
        data = data or {}
        query_params = query_params or {}
        current_user = None
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            current_user = AuthService.get_current_user(token)
        for route in self.routes:
            if route["method"] != method.upper():
                continue
            params = self.match_path(route["path"], path)
            if params is None:
                continue
            if route["auth_required"] and not current_user:
                return error_response("Authentication required.", 401)
            if route["admin_required"] and (not current_user or not current_user.get("is_staff")):
                return error_response("Admin access required.", 403)
            try:
                return route["handler"](
                    data=data,
                    params=params,
                    query_params=query_params,
                    current_user=current_user,
                )
            except ValidationError as e:
                return error_response(e.errors, 400)
            except Exception as e:
                return error_response(f"Internal server error: {str(e)}", 500)
        return error_response("Not found.", 404)


# ============================================================
# API Handlers
# ============================================================

def handle_register(data, params, query_params, current_user):
    return AuthService.register(data)


def handle_login(data, params, query_params, current_user):
    email = data.get("email", "")
    password = data.get("password", "")
    return AuthService.login(email, password)


def handle_token_refresh(data, params, query_params, current_user):
    refresh = data.get("refresh", "")
    return AuthService.refresh_token(refresh)


def handle_me_get(data, params, query_params, current_user):
    return success_response({k: v for k, v in current_user.items() if k != "password"})


def handle_me_update(data, params, query_params, current_user):
    return AuthService.update_profile(current_user["id"], data)


def handle_books_list(data, params, query_params, current_user):
    return BookService.list_books(query_params)


def handle_books_create(data, params, query_params, current_user):
    if not current_user["is_staff"]:
        return error_response("Admin access required.", 403)
    return BookService.create_book(data)


def handle_book_detail(data, params, query_params, current_user):
    return BookService.get_book(params["book_id"])


def handle_book_update(data, params, query_params, current_user):
    if not current_user["is_staff"]:
        return error_response("Admin access required.", 403)
    return BookService.update_book(params["book_id"], data)


def handle_book_partial_update(data, params, query_params, current_user):
    if not current_user["is_staff"]:
        return error_response("Admin access required.", 403)
    return BookService.update_book(params["book_id"], data, partial=True)


def handle_book_delete(data, params, query_params, current_user):
    if not current_user["is_staff"]:
        return error_response("Admin access required.", 403)
    return BookService.delete_book(params["book_id"])


def handle_borrowings_list(data, params, query_params, current_user):
    return BorrowingService.list_borrowings(current_user, query_params)


def handle_borrowings_create(data, params, query_params, current_user):
    return BorrowingService.create_borrowing(data, current_user)


def handle_borrowing_detail(data, params, query_params, current_user):
    return BorrowingService.get_borrowing(params["borrowing_id"], current_user)


def handle_borrowing_return(data, params, query_params, current_user):
    return BorrowingService.return_borrowing(params["borrowing_id"], current_user)


def handle_payments_list(data, params, query_params, current_user):
    return PaymentService.list_payments(current_user, query_params)


def handle_payment_detail(data, params, query_params, current_user):
    return PaymentService.get_payment(params["payment_id"], current_user)


def handle_payment_process(data, params, query_params, current_user):
    return PaymentService.process_payment(params["payment_id"], current_user)


def handle_payment_cancel(data, params, query_params, current_user):
    return PaymentService.cancel_payment(params["payment_id"], current_user)


def handle_stripe_success(data, params, query_params, current_user):
    session_id = query_params.get("session_id", "")
    return PaymentService.stripe_success(session_id, current_user)


def handle_stripe_cancel(data, params, query_params, current_user):
    session_id = query_params.get("session_id", "")
    return PaymentService.stripe_cancel(session_id, current_user)


def handle_admin_users_list(data, params, query_params, current_user):
    return AdminService.list_users(current_user, query_params)


def handle_admin_user_detail(data, params, query_params, current_user):
    return AdminService.get_user(current_user, params["user_id"])


def handle_admin_user_update(data, params, query_params, current_user):
    return AdminService.update_user(current_user, params["user_id"], data)


def handle_admin_user_delete(data, params, query_params, current_user):
    return AdminService.delete_user(current_user, params["user_id"])


def handle_admin_dashboard(data, params, query_params, current_user):
    return AdminService.dashboard(current_user)


def handle_swagger_docs(data, params, query_params, current_user):
    swagger_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Service API",
            "version": "1.0.0",
            "description": "API for library book borrowing service with JWT authentication",
        },
        "servers": [{"url": "/api/v1"}],
        "paths": {
            "/auth/register/": {
                "post": {
                    "tags": ["Authentication"],
                    "summary": "Register a new user",
                    "requestBody": {
                        "required": True,
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
                        },
                    },
                    "responses": {"201": {"description": "User created"}},
                }
            },
            "/auth/login/": {
                "post": {
                    "tags": ["Authentication"],
                    "summary": "Login and get JWT tokens",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                    },
                                    "required": ["email", "password"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "JWT tokens"}},
                }
            },
            "/books/": {
                "get": {
                    "tags": ["Books"],
                    "summary": "List all books",
                    "parameters": [
                        {"name": "title", "in": "query", "schema": {"type": "string"}},
                        {"name": "author", "in": "query", "schema": {"type": "string"}},
                        {"name": "cover", "in": "query", "schema": {"type": "string", "enum": ["HARD", "SOFT"]}},
                        {"name": "available", "in": "query", "schema": {"type": "string", "enum": ["true", "false"]}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "List of books"}},
                },
                "post": {
                    "tags": ["Books"],
                    "summary": "Create a new book (Admin only)",
                    "security": [{"bearerAuth": []}],
                    "responses": {"201": {"description": "Book created"}},
                },
            },
            "/books/{book_id}/": {
                "get": {
                    "tags": ["Books"],
                    "summary": "Get book details",
                    "parameters": [{"name": "book_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Book details"}},
                },
                "put": {
                    "tags": ["Books"],
                    "summary": "Update book (Admin only)",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Book updated"}},
                },
                "patch": {
                    "tags": ["Books"],
                    "summary": "Partial update book (Admin only)",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Book updated"}},
                },
                "delete": {
                    "tags": ["Books"],
                    "summary": "Delete book (Admin only)",
                    "security": [{"bearerAuth": []}],
                    "responses": {"204": {"description": "Book deleted"}},
                },
            },
            "/borrowings/": {
                "get": {
                    "tags": ["Borrowings"],
                    "summary": "List borrowings",
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {"name": "is_active", "in": "query", "schema": {"type": "string", "enum": ["true", "false"]}},
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Admin only"},
                        {"name": "actual_return_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "List of borrowings"}},
                },
                "post": {
                    "tags": ["Borrowings"],
                    "summary": "Create a borrowing",
                    "security": [{"bearerAuth": []}],
                    "responses": {"201": {"description": "Borrowing created"}},
                },
            },
            "/borrowings/{borrowing_id}/": {
                "get": {
                    "tags": ["Borrowings"],
                    "summary": "Get borrowing details",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Borrowing details"}},
                }
            },
            "/borrowings/{borrowing_id}/return/": {
                "post": {
                    "tags": ["Borrowings"],
                    "summary": "Return a borrowed book",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Book returned"}},
                }
            },
            "/payments/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "List payments",
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["PENDING", "PAID"]}},
                        {"name": "type", "in": "query", "schema": {"type": "string", "enum": ["PAYMENT", "FINE"]}},
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Admin only"},
                        {"name": "borrowing_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "List of payments"}},
                }
            },
            "/payments/{payment_id}/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Get payment details",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Payment details"}},
                }
            },
            "/payments/{payment_id}/pay/": {
                "post": {
                    "tags": ["Payments"],
                    "summary": "Process a payment",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Payment processed"}},
                }
            },
            "/payments/success/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Stripe payment success callback",
                    "security": [{"bearerAuth": []}],
                    "parameters": [{"name": "session_id", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Payment successful"}},
                }
            },
            "/payments/cancel/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Stripe payment cancel callback",
                    "security": [{"bearerAuth": []}],
                    "parameters": [{"name": "session_id", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Payment cancelled"}},
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
    return success_response(swagger_spec)


# ============================================================
# Application Setup
# ============================================================

def create_app() -> APIRouter:
    router = APIRouter()

    # Auth endpoints
    router.add_route("POST", "/api/v1/auth/register/", handle_register, auth_required=False)
    router.add_route("POST", "/api/v1/auth/login/", handle_login, auth_required=False)
    router.add_route("POST", "/api/v1/auth/token/refresh/", handle_token_refresh, auth_required=False)
    router.add_route("GET", "/api/v1/auth/me/", handle_me_get, auth_required=True)
    router.add_route("PUT", "/api/v1/auth/me/", handle_me_update, auth_required=True)
    router.add_route("PATCH", "/api/v1/auth/me/", handle_me_update, auth_required=True)

    # Book endpoints
    router.add_route("GET", "/api/v1/books/", handle_books_list, auth_required=False)
    router.add_route("POST", "/api/v1/books/", handle_books_create, auth_required=True)
    router.add_route("GET", "/api/v1/books/{book_id}/", handle_book_detail, auth_required=False)
    router.add_route("PUT", "/api/v1/books/{book_id}/", handle_book_update, auth_required=True)
    router.add_route("PATCH", "/api/v1/books/{book_id}/", handle_book_partial_update, auth_required=True)
    router.add_route("DELETE", "/api/v1/books/{book_id}/", handle_book_delete, auth_required=True)

    # Borrowing endpoints
    router.add_route("GET", "/api/v1/borrowings/", handle_borrowings_list, auth_required=True)
    router.add_route("POST", "/api/v1/borrowings/", handle_borrowings_create, auth_required=True)
    router.add_route("GET", "/api/v1/borrowings/{borrowing_id}/", handle_borrowing_detail, auth_required=True)
    router.add_route("POST", "/api/v1/borrowings/{borrowing_id}/return/", handle_borrowing_return, auth_required=True)

    # Payment endpoints
    router.add_route("GET", "/api/v1/payments/", handle_payments_list, auth_required=True)
    router.add_route("GET", "/api/v1/payments/success/", handle_stripe_success, auth_required=True)
    router.add_route("GET", "/api/v1/payments/cancel/", handle_stripe_cancel, auth_required=True)
    router.add_route("GET", "/api/v1/payments/{payment_id}/", handle_payment_detail, auth_required=True)
    router.add_route("POST", "/api/v1/payments/{payment_id}/pay/", handle_payment_process, auth_required=True)
    router.add_route("POST", "/api/v1/payments/{payment_id}/cancel/", handle_payment_cancel, auth_required=True)

    # Admin endpoints
    router.add_route("GET", "/admin/", handle_admin_dashboard, auth_required=True, admin_required=True)
    router.add_route("GET", "/admin/users/", handle_admin_users_list, auth_required=True, admin_required=True)
    router.add_route("GET", "/admin/users/{user_id}/", handle_admin_user_detail, auth_required=True, admin_required=True)
    router.add_route("PUT", "/admin/users/{user_id}/", handle_admin_user_update, auth_required=True, admin_required=True)
    router.add_route("PATCH", "/admin/users/{user_id}/", handle_admin_user_update, auth_required=True, admin_required=True)
    router.add_route("DELETE", "/admin/users/{user_id}/", handle_admin_user_delete, auth_required=True, admin_required=True)

    # Documentation
    router.add_route("GET", "/api/v1/doc/swagger/", handle_swagger_docs, auth_required=False)

    return router


# ============================================================
# CLI / Demo Runner
# ============================================================

def run_demo():
    print("=" * 60)
    print("Library Service API - Demo")
    print("=" * 60)

    app = create_app()

    print("\n1. Register a new user")
    result = app.handle_request(
        "POST",
        "/api/v1/auth/register/",
        data={
            "email": "john@example.com",
            "password": "securepass123",
            "first_name": "John",
            "last_name": "Doe",
        },
    )
    print(f"   Status: {result['status']}")
    print(f"   User: {result.get('data', {}).get('email', 'N/A')}")

    print("\n2. Login as admin")
    result = app.handle_request(
        "POST",
        "/api/v1/auth/login/",
        data={"email": "admin@library.com", "password": "admin123"},
    )
    print(f"   Status: {result['status']}")
    admin_token = result.get("data", {}).get("access", "")
    print(f"   Token: {admin_token[:50]}...")

    print("\n3. Create a book (Admin)")
    result = app.handle_request(
        "POST",
        "/api/v1/books/",
        data={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "cover": "HARD",
            "inventory": 5,
            "daily_fee": "1.50",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print(f"   Status: {result['status']}")
    book_id = result.get("data", {}).get("id", "")
    print(f"   Book ID: {book_id}")
    print(f"   Title: {result.get('data', {}).get('title', 'N/A')}")

    print("\n4. List books (public)")
    result = app.handle_request("GET", "/api/v1/books/")
    print(f"   Status: {result['status']}")
    print(f"   Total books: {result.get('data', {}).get('count', 0)}")

    print("\n5. Login as regular user")
    result = app.handle_request(
        "POST",
        "/api/v1/auth/login/",
        data={"email": "john@example.com", "password": "securepass123"},
    )
    user_token = result.get("data", {}).get("access", "")
    print(f"   Status: {result['status']}")
    print(f"   Token obtained: {bool(user_token)}")

    print("\n6. Create a borrowing")
    future_date = (date.today() + timedelta(days=7)).isoformat()
    result = app.handle_request(
        "POST",
        "/api/v1/borrowings/",
        data={"book_id": book_id, "expected_return_date": future_date},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print(f"   Status: {result['status']}")
    borrowing_id = result.get("data", {}).get("id", "")
    payment_id = result.get("data", {}).get("payment", {}).get("id", "")
    print(f"   Borrowing ID: {borrowing_id}")
    print(f"   Payment ID: {payment_id}")
    print(f"   Money to pay: {result.get('data', {}).get('payment', {}).get('money_to_pay', 'N/A')}")

    print("\n7. List borrowings (user sees own)")
    result = app.handle_request(
        "GET",
        "/api/v1/borrowings/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print(f"   Status: {result['status']}")
    print(f"   Total borrowings: {result.get('data', {}).get('count', 0)}")

    print("\n8. Filter borrowings by is_active=true")
    result = app.handle_request(
        "GET",
        "/api/v1/borrowings/",
        headers={"Authorization": f"Bearer {user_token}"},
        query_params={"is_active": "true"},
    )
    print(f"   Status: {result['status']}")
    print(f"   Active borrowings: {result.get('data', {}).get('count', 0)}")

    print("\n9. Process payment")
    result = app.handle_request(
        "POST",
        f"/api/v1/payments/{payment_id}/pay/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print(f"   Status: {result['status']}")
    print(f"   Payment status: {result.get('data', {}).get('payment', {}).get('status', 'N/A')}")

    print("\n10. Return the book")
    result = app.handle_request(
        "POST",
        f"/api/v1/borrowings/{borrowing_id}/return/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print(f"    Status: {result['status']}")
    print(f"    Actual return date: {result.get('data', {}).get('actual_return_date', 'N/A')}")
    print(f"    Overdue days: {result.get('data', {}).get('overdue_days', 0)}")

    print("\n11. List payments")
    result = app.handle_request(
        "GET",
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print(f"    Status: {result['status']}")
    print(f"    Total payments: {result.get('data', {}).get('count', 0)}")

    print("\n12. Admin dashboard")
    result = app.handle_request(
        "GET",
        "/admin/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print(f"    Status: {result['status']}")
    dashboard = result.get("data", {})
    print(f"    Total books: {dashboard.get('total_books', 0)}")
    print(f"    Total users: {dashboard.get('total_users', 0)}")
    print(f"    Total borrowings: {dashboard.get('total_borrowings', 0)}")
    print(f"    Total revenue: ${dashboard.get('total_revenue', '0')}")

    print("\n13. Filter borrowings by actual_return_date (admin)")
    today = date.today().isoformat()
    result = app.handle_request(
        "GET",
        "/api/v1/borrowings/",
        headers={"Authorization": f"Bearer {admin_token}"},
        query_params={"actual_return_date": today},
    )
    print(f"    Status: {result['status']}")
    print(f"    Borrowings returned today: {result.get('data', {}).get('count', 0)}")

    print("\n14. Filter borrowings by user_id (admin)")
    user_data = db.get_user_by_email("john@example.com")
    result = app.handle_request(
        "GET",
        "/api/v1/borrowings/",
        headers={"Authorization": f"Bearer {admin_token}"},
        query_params={"user_id": user_data["id"]},
    )
    print(f"    Status: {result['status']}")
    print(f"    John's borrowings: {result.get('data', {}).get('count', 0)}")

    print("\n15. Swagger documentation")
    result = app.handle_request("GET", "/api/v1/doc/swagger/")
    print(f"    Status: {result['status']}")
    print(f"    API Title: {result.get('data', {}).get('info', {}).get('title', 'N/A')}")
    print(f"    Endpoints: {len(result.get('data', {}).get('paths', {}))}")

    print("\n16. Test token refresh")
    login_result = app.handle_request(
        "POST",
        "/api/v1/auth/login/",
        data={"email": "john@example.com", "password": "securepass123"},
    )
    refresh_token = login_result.get("data", {}).get("refresh", "")
    result = app.handle_request(
        "POST",
        "/api/v1/auth/token/refresh/",
        data={"refresh": refresh_token},
    )
    print(f"    Status: {result['status']}")
    print(f"    New access token obtained: {bool(result.get('data', {}).get('access', ''))}")

    print("\n17. Admin list users")
    result = app.handle_request(
        "GET",
        "/admin/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print(f"    Status: {result['status']}")
    print(f"    Total users: {result.get('data', {}).get('count', 0)}")

    print("\n18. Test unauthorized access")
    result = app.handle_request("GET", "/api/v1/borrowings/")
    print(f"    Status: {result['status']}")
    print(f"    Error: {result.get('error', 'N/A')}")

    print("\n19. Test non-admin creating book")
    result = app.handle_request(
        "POST",
        "/api/v1/books/",
        data={
            "title": "Unauthorized Book",
            "author": "Test",
            "cover": "SOFT",
            "inventory": 1,
            "daily_fee": "1.00",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print(f"    Status: {result['status']}")
    print(f"    Error: {result.get('error', 'N/A')}")

    print("\n20. Test validation error")
    result = app.handle_request(
        "POST",
        "/api/v1/books/",
        data={"title": "", "cover": "INVALID"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print(f"    Status: {result['status']}")
    print(f"    Validation errors: {list(result.get('error', {}).keys())}")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)

    return app


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    app = run_demo()