#!/usr/bin/env python3
"""
Library Service API - Complete Implementation
JWT authentication, book management, borrowings, payments, and fines
"""

import os
import sys
import json
import uuid
import hashlib
import hmac
import base64
import time
import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from functools import wraps

# Try to use Flask if available, otherwise implement a minimal HTTP server
try:
    from flask import Flask, request, jsonify, g
    from flask.views import MethodView
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# ============================================================
# DATA MODELS
# ============================================================

class Database:
    """In-memory database for the library service"""
    
    def __init__(self):
        self.users: Dict[str, Dict] = {}
        self.books: Dict[str, Dict] = {}
        self.borrowings: Dict[str, Dict] = {}
        self.payments: Dict[str, Dict] = {}
        self._init_admin()
        self._init_sample_data()
    
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
            "created_at": datetime.datetime.utcnow().isoformat()
        }
    
    def _init_sample_data(self):
        # Sample books
        books_data = [
            {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "cover": "HARD", "inventory": 5, "daily_fee": "1.50"},
            {"title": "To Kill a Mockingbird", "author": "Harper Lee", "cover": "SOFT", "inventory": 3, "daily_fee": "1.00"},
            {"title": "1984", "author": "George Orwell", "cover": "HARD", "inventory": 7, "daily_fee": "2.00"},
            {"title": "Pride and Prejudice", "author": "Jane Austen", "cover": "SOFT", "inventory": 4, "daily_fee": "0.75"},
        ]
        for book_data in books_data:
            book_id = str(uuid.uuid4())
            self.books[book_id] = {
                "id": book_id,
                "title": book_data["title"],
                "author": book_data["author"],
                "cover": book_data["cover"],
                "inventory": book_data["inventory"],
                "daily_fee": book_data["daily_fee"],
                "created_at": datetime.datetime.utcnow().isoformat()
            }
    
    def _hash_password(self, password: str) -> str:
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return base64.b64encode(salt + key).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            decoded = base64.b64decode(hashed.encode('utf-8'))
            salt = decoded[:32]
            stored_key = decoded[32:]
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return hmac.compare_digest(key, stored_key)
        except Exception:
            return False
    
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


# Global database instance
db = Database()


# ============================================================
# JWT IMPLEMENTATION
# ============================================================

class JWT:
    SECRET_KEY = os.environ.get("SECRET_KEY", "library-service-secret-key-2024")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    @classmethod
    def _base64url_encode(cls, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    @classmethod
    def _base64url_decode(cls, data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data.encode('utf-8'))
    
    @classmethod
    def create_token(cls, payload: Dict, expire_minutes: int = None, expire_days: int = None) -> str:
        header = {"alg": cls.ALGORITHM, "typ": "JWT"}
        
        now = datetime.datetime.utcnow()
        if expire_minutes:
            exp = now + datetime.timedelta(minutes=expire_minutes)
        elif expire_days:
            exp = now + datetime.timedelta(days=expire_days)
        else:
            exp = now + datetime.timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload_copy = payload.copy()
        payload_copy["exp"] = int(exp.timestamp())
        payload_copy["iat"] = int(now.timestamp())
        
        header_encoded = cls._base64url_encode(json.dumps(header).encode())
        payload_encoded = cls._base64url_encode(json.dumps(payload_copy).encode())
        
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            cls.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_encoded = cls._base64url_encode(signature)
        
        return f"{message}.{signature_encoded}"
    
    @classmethod
    def create_access_token(cls, user_id: str) -> str:
        return cls.create_token(
            {"user_id": user_id, "type": "access"},
            expire_minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        return cls.create_token(
            {"user_id": user_id, "type": "refresh"},
            expire_days=cls.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    @classmethod
    def decode_token(cls, token: str) -> Optional[Dict]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                cls.SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = cls._base64url_encode(expected_signature)
            
            if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
                return None
            
            payload = json.loads(cls._base64url_decode(payload_encoded))
            
            if payload.get("exp", 0) < int(time.time()):
                return None
            
            return payload
        except Exception:
            return None


# ============================================================
# VALIDATORS
# ============================================================

class ValidationError(Exception):
    def __init__(self, errors: Dict):
        self.errors = errors
        super().__init__(str(errors))


class BookValidator:
    VALID_COVERS = ["HARD", "SOFT"]
    
    @classmethod
    def validate_create(cls, data: Dict) -> Dict:
        errors = {}
        
        if not data.get("title"):
            errors["title"] = "Title is required"
        elif len(data["title"]) > 255:
            errors["title"] = "Title must be 255 characters or less"
        
        if not data.get("author"):
            errors["author"] = "Author is required"
        elif len(data["author"]) > 255:
            errors["author"] = "Author must be 255 characters or less"
        
        if not data.get("cover"):
            errors["cover"] = "Cover type is required"
        elif data["cover"] not in cls.VALID_COVERS:
            errors["cover"] = f"Cover must be one of: {', '.join(cls.VALID_COVERS)}"
        
        if data.get("inventory") is None:
            errors["inventory"] = "Inventory is required"
        else:
            try:
                inventory = int(data["inventory"])
                if inventory < 0:
                    errors["inventory"] = "Inventory must be non-negative"
            except (ValueError, TypeError):
                errors["inventory"] = "Inventory must be an integer"
        
        if not data.get("daily_fee"):
            errors["daily_fee"] = "Daily fee is required"
        else:
            try:
                fee = Decimal(str(data["daily_fee"]))
                if fee <= 0:
                    errors["daily_fee"] = "Daily fee must be positive"
            except Exception:
                errors["daily_fee"] = "Daily fee must be a valid decimal number"
        
        if errors:
            raise ValidationError(errors)
        
        return {
            "title": data["title"].strip(),
            "author": data["author"].strip(),
            "cover": data["cover"],
            "inventory": int(data["inventory"]),
            "daily_fee": str(Decimal(str(data["daily_fee"])))
        }
    
    @classmethod
    def validate_update(cls, data: Dict) -> Dict:
        cleaned = {}
        errors = {}
        
        if "title" in data:
            if not data["title"]:
                errors["title"] = "Title cannot be empty"
            elif len(data["title"]) > 255:
                errors["title"] = "Title must be 255 characters or less"
            else:
                cleaned["title"] = data["title"].strip()
        
        if "author" in data:
            if not data["author"]:
                errors["author"] = "Author cannot be empty"
            elif len(data["author"]) > 255:
                errors["author"] = "Author must be 255 characters or less"
            else:
                cleaned["author"] = data["author"].strip()
        
        if "cover" in data:
            if data["cover"] not in cls.VALID_COVERS:
                errors["cover"] = f"Cover must be one of: {', '.join(cls.VALID_COVERS)}"
            else:
                cleaned["cover"] = data["cover"]
        
        if "inventory" in data:
            try:
                inventory = int(data["inventory"])
                if inventory < 0:
                    errors["inventory"] = "Inventory must be non-negative"
                else:
                    cleaned["inventory"] = inventory
            except (ValueError, TypeError):
                errors["inventory"] = "Inventory must be an integer"
        
        if "daily_fee" in data:
            try:
                fee = Decimal(str(data["daily_fee"]))
                if fee <= 0:
                    errors["daily_fee"] = "Daily fee must be positive"
                else:
                    cleaned["daily_fee"] = str(fee)
            except Exception:
                errors["daily_fee"] = "Daily fee must be a valid decimal number"
        
        if errors:
            raise ValidationError(errors)
        
        return cleaned


class BorrowingValidator:
    @classmethod
    def validate_create(cls, data: Dict) -> Dict:
        errors = {}
        
        if not data.get("book_id"):
            errors["book_id"] = "Book ID is required"
        
        if not data.get("expected_return_date"):
            errors["expected_return_date"] = "Expected return date is required"
        else:
            try:
                expected_date = datetime.date.fromisoformat(data["expected_return_date"])
                if expected_date <= datetime.date.today():
                    errors["expected_return_date"] = "Expected return date must be in the future"
            except ValueError:
                errors["expected_return_date"] = "Invalid date format. Use YYYY-MM-DD"
        
        if errors:
            raise ValidationError(errors)
        
        return {
            "book_id": data["book_id"],
            "expected_return_date": data["expected_return_date"]
        }


class UserValidator:
    @classmethod
    def validate_register(cls, data: Dict) -> Dict:
        errors = {}
        
        if not data.get("email"):
            errors["email"] = "Email is required"
        elif "@" not in data["email"]:
            errors["email"] = "Invalid email format"
        elif len(data["email"]) > 255:
            errors["email"] = "Email must be 255 characters or less"
        
        if not data.get("password"):
            errors["password"] = "Password is required"
        elif len(data["password"]) < 8:
            errors["password"] = "Password must be at least 8 characters"
        
        if not data.get("first_name"):
            errors["first_name"] = "First name is required"
        
        if not data.get("last_name"):
            errors["last_name"] = "Last name is required"
        
        if errors:
            raise ValidationError(errors)
        
        return {
            "email": data["email"].lower().strip(),
            "password": data["password"],
            "first_name": data["first_name"].strip(),
            "last_name": data["last_name"].strip()
        }
    
    @classmethod
    def validate_update(cls, data: Dict) -> Dict:
        cleaned = {}
        errors = {}
        
        if "email" in data:
            if not data["email"]:
                errors["email"] = "Email cannot be empty"
            elif "@" not in data["email"]:
                errors["email"] = "Invalid email format"
            else:
                cleaned["email"] = data["email"].lower().strip()
        
        if "first_name" in data:
            if not data["first_name"]:
                errors["first_name"] = "First name cannot be empty"
            else:
                cleaned["first_name"] = data["first_name"].strip()
        
        if "last_name" in data:
            if not data["last_name"]:
                errors["last_name"] = "Last name cannot be empty"
            else:
                cleaned["last_name"] = data["last_name"].strip()
        
        if "password" in data:
            if len(data["password"]) < 8:
                errors["password"] = "Password must be at least 8 characters"
            else:
                cleaned["password"] = data["password"]
        
        if errors:
            raise ValidationError(errors)
        
        return cleaned


# ============================================================
# SERVICES
# ============================================================

class PaymentService:
    FINE_MULTIPLIER = Decimal("2.0")
    
    @classmethod
    def calculate_borrowing_amount(cls, borrowing: Dict) -> Decimal:
        book = db.get_book_by_id(borrowing["book_id"])
        if not book:
            return Decimal("0")
        
        borrow_date = datetime.date.fromisoformat(borrowing["borrow_date"])
        expected_date = datetime.date.fromisoformat(borrowing["expected_return_date"])
        days = (expected_date - borrow_date).days
        if days <= 0:
            days = 1
        
        daily_fee = Decimal(book["daily_fee"])
        return daily_fee * days
    
    @classmethod
    def calculate_fine_amount(cls, borrowing: Dict) -> Decimal:
        if not borrowing.get("actual_return_date"):
            return Decimal("0")
        
        book = db.get_book_by_id(borrowing["book_id"])
        if not book:
            return Decimal("0")
        
        expected_date = datetime.date.fromisoformat(borrowing["expected_return_date"])
        actual_date = datetime.date.fromisoformat(borrowing["actual_return_date"])
        
        if actual_date <= expected_date:
            return Decimal("0")
        
        overdue_days = (actual_date - expected_date).days
        daily_fee = Decimal(book["daily_fee"])
        return daily_fee * overdue_days * cls.FINE_MULTIPLIER
    
    @classmethod
    def create_payment(cls, borrowing_id: str, payment_type: str = "PAYMENT") -> Dict:
        borrowing = db.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found")
        
        if payment_type == "PAYMENT":
            amount = cls.calculate_borrowing_amount(borrowing)
        elif payment_type == "FINE":
            amount = cls.calculate_fine_amount(borrowing)
        else:
            raise ValueError("Invalid payment type")
        
        payment_id = str(uuid.uuid4())
        session_url = f"https://checkout.stripe.com/pay/cs_test_{payment_id}"
        session_id = f"cs_test_{payment_id}"
        
        payment = {
            "id": payment_id,
            "status": "PENDING",
            "type": payment_type,
            "borrowing_id": borrowing_id,
            "session_url": session_url,
            "session_id": session_id,
            "money_to_pay": str(amount),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        db.payments[payment_id] = payment
        return payment
    
    @classmethod
    def complete_payment(cls, payment_id: str) -> Dict:
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        if payment["status"] == "PAID":
            raise ValueError("Payment already completed")
        
        payment["status"] = "PAID"
        payment["paid_at"] = datetime.datetime.utcnow().isoformat()
        db.payments[payment_id] = payment
        return payment


class BorrowingService:
    @classmethod
    def create_borrowing(cls, user_id: str, book_id: str, expected_return_date: str) -> Dict:
        book = db.get_book_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        
        if book["inventory"] <= 0:
            raise ValueError("Book is not available (inventory is 0)")
        
        # Check for unpaid payments
        for payment in db.payments.values():
            borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
            if borrowing and borrowing["user_id"] == user_id and payment["status"] == "PENDING":
                raise ValueError("You have pending payments. Please complete them before borrowing.")
        
        borrowing_id = str(uuid.uuid4())
        borrowing = {
            "id": borrowing_id,
            "user_id": user_id,
            "book_id": book_id,
            "borrow_date": datetime.date.today().isoformat(),
            "expected_return_date": expected_return_date,
            "actual_return_date": None,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        # Decrease inventory
        book["inventory"] -= 1
        db.books[book_id] = book
        db.borrowings[borrowing_id] = borrowing
        
        # Create payment
        PaymentService.create_payment(borrowing_id, "PAYMENT")
        
        return borrowing
    
    @classmethod
    def return_book(cls, borrowing_id: str, user_id: str) -> Dict:
        borrowing = db.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found")
        
        if borrowing["user_id"] != user_id:
            raise ValueError("You can only return your own borrowings")
        
        if borrowing["actual_return_date"]:
            raise ValueError("Book already returned")
        
        borrowing["actual_return_date"] = datetime.date.today().isoformat()
        db.borrowings[borrowing_id] = borrowing
        
        # Increase inventory
        book = db.get_book_by_id(borrowing["book_id"])
        if book:
            book["inventory"] += 1
            db.books[borrowing["book_id"]] = book
        
        # Check if fine is needed
        expected_date = datetime.date.fromisoformat(borrowing["expected_return_date"])
        actual_date = datetime.date.fromisoformat(borrowing["actual_return_date"])
        
        fine_payment = None
        if actual_date > expected_date:
            fine_payment = PaymentService.create_payment(borrowing_id, "FINE")
        
        return {"borrowing": borrowing, "fine_payment": fine_payment}


# ============================================================
# SERIALIZERS
# ============================================================

class Serializer:
    @staticmethod
    def serialize_user(user: Dict, include_sensitive: bool = False) -> Dict:
        result = {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_staff": user["is_staff"],
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        }
        return result
    
    @staticmethod
    def serialize_book(book: Dict) -> Dict:
        return {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "cover": book["cover"],
            "inventory": book["inventory"],
            "daily_fee": book["daily_fee"],
            "created_at": book["created_at"]
        }
    
    @staticmethod
    def serialize_borrowing(borrowing: Dict, include_book: bool = True, include_user: bool = False) -> Dict:
        result = {
            "id": borrowing["id"],
            "borrow_date": borrowing["borrow_date"],
            "expected_return_date": borrowing["expected_return_date"],
            "actual_return_date": borrowing["actual_return_date"],
            "created_at": borrowing["created_at"]
        }
        
        if include_book:
            book = db.get_book_by_id(borrowing["book_id"])
            result["book"] = Serializer.serialize_book(book) if book else None
        else:
            result["book_id"] = borrowing["book_id"]
        
        if include_user:
            user = db.get_user_by_id(borrowing["user_id"])
            result["user"] = Serializer.serialize_user(user) if user else None
        else:
            result["user_id"] = borrowing["user_id"]
        
        return result
    
    @staticmethod
    def serialize_payment(payment: Dict, include_borrowing: bool = True) -> Dict:
        result = {
            "id": payment["id"],
            "status": payment["status"],
            "type": payment["type"],
            "session_url": payment["session_url"],
            "session_id": payment["session_id"],
            "money_to_pay": payment["money_to_pay"],
            "created_at": payment["created_at"]
        }
        
        if include_borrowing:
            borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
            result["borrowing"] = Serializer.serialize_borrowing(borrowing) if borrowing else None
        else:
            result["borrowing_id"] = payment["borrowing_id"]
        
        return result


# ============================================================
# RESPONSE HELPERS
# ============================================================

def success_response(data: Any, status_code: int = 200) -> tuple:
    return jsonify(data), status_code


def error_response(message: str, status_code: int = 400, errors: Dict = None) -> tuple:
    response = {"error": message}
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code


def paginate(items: List, page: int = 1, page_size: int = 10) -> Dict:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "results": items[start:end]
    }


# ============================================================
# AUTHENTICATION MIDDLEWARE
# ============================================================

def get_current_user() -> Optional[Dict]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    payload = JWT.decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    user = db.get_user_by_id(payload.get("user_id", ""))
    if not user or not user["is_active"]:
        return None
    
    return user


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error_response("Authentication required", 401)
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error_response("Authentication required", 401)
        if not user["is_staff"]:
            return error_response("Admin access required", 403)
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


# ============================================================
# FLASK APPLICATION
# ============================================================

if FLASK_AVAILABLE:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = JWT.SECRET_KEY
    
    # ============================================================
    # SWAGGER DOCUMENTATION
    # ============================================================
    
    SWAGGER_SPEC = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Service API",
            "version": "1.0.0",
            "description": "API Library service for borrowing books with JWT authentication"
        },
        "servers": [{"url": "/api/v1"}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            },
            "schemas": {
                "Book": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "cover": {"type": "string", "enum": ["HARD", "SOFT"]},
                        "inventory": {"type": "integer"},
                        "daily_fee": {"type": "string"},
                        "created_at": {"type": "string"}
                    }
                },
                "Borrowing": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "borrow_date": {"type": "string"},
                        "expected_return_date": {"type": "string"},
                        "actual_return_date": {"type": "string", "nullable": True},
                        "book": {"$ref": "#/components/schemas/Book"},
                        "user_id": {"type": "string"}
                    }
                },
                "Payment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "status": {"type": "string", "enum": ["PENDING", "PAID"]},
                        "type": {"type": "string", "enum": ["PAYMENT", "FINE"]},
                        "session_url": {"type": "string"},
                        "session_id": {"type": "string"},
                        "money_to_pay": {"type": "string"},
                        "borrowing": {"$ref": "#/components/schemas/Borrowing"}
                    }
                },
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "is_staff": {"type": "boolean"}
                    }
                }
            }
        },
        "paths": {
            "/books/": {
                "get": {
                    "summary": "List all books",
                    "tags": ["Books"],
                    "parameters": [
                        {"name": "title", "in": "query", "schema": {"type": "string"}},
                        {"name": "author", "in": "query", "schema": {"type": "string"}},
                        {"name": "cover", "in": "query", "schema": {"type": "string", "enum": ["HARD", "SOFT"]}},
                        {"name": "available", "in": "query", "schema": {"type": "boolean"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "page_size", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "List of books"}}
                },
                "post": {
                    "summary": "Create a book (Admin only)",
                    "tags": ["Books"],
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "author", "cover", "inventory", "daily_fee"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "author": {"type": "string"},
                                        "cover": {"type": "string", "enum": ["HARD", "SOFT"]},
                                        "inventory": {"type": "integer"},
                                        "daily_fee": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Book created"}}
                }
            },
            "/books/{id}/": {
                "get": {
                    "summary": "Get book details",
                    "tags": ["Books"],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Book details"}}
                },
                "put": {
                    "summary": "Update book (Admin only)",
                    "tags": ["Books"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Book updated"}}
                },
                "patch": {
                    "summary": "Partial update book (Admin only)",
                    "tags": ["Books"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Book updated"}}
                },
                "delete": {
                    "summary": "Delete book (Admin only)",
                    "tags": ["Books"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"204": {"description": "Book deleted"}}
                }
            },
            "/borrowings/": {
                "get": {
                    "summary": "List borrowings",
                    "tags": ["Borrowings"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {"name": "is_active", "in": "query", "schema": {"type": "boolean"}, "description": "Filter by actual return date (true=not returned, false=returned)"},
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Filter by user ID (Admin only)"},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "page_size", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "List of borrowings"}}
                },
                "post": {
                    "summary": "Create a borrowing",
                    "tags": ["Borrowings"],
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["book_id", "expected_return_date"],
                                    "properties": {
                                        "book_id": {"type": "string"},
                                        "expected_return_date": {"type": "string", "format": "date"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Borrowing created"}}
                }
            },
            "/borrowings/{id}/": {
                "get": {
                    "summary": "Get borrowing details",
                    "tags": ["Borrowings"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Borrowing details"}}
                }
            },
            "/borrowings/{id}/return/": {
                "post": {
                    "summary": "Return a book",
                    "tags": ["Borrowings"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Book returned"}}
                }
            },
            "/payments/": {
                "get": {
                    "summary": "List payments",
                    "tags": ["Payments"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["PENDING", "PAID"]}},
                        {"name": "type", "in": "query", "schema": {"type": "string", "enum": ["PAYMENT", "FINE"]}},
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Filter by user ID (Admin only)"},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "page_size", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "List of payments"}}
                }
            },
            "/payments/{id}/": {
                "get": {
                    "summary": "Get payment details",
                    "tags": ["Payments"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Payment details"}}
                }
            },
            "/payments/{id}/success/": {
                "get": {
                    "summary": "Payment success callback",
                    "tags": ["Payments"],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Payment completed"}}
                }
            },
            "/payments/{id}/cancel/": {
                "get": {
                    "summary": "Payment cancel callback",
                    "tags": ["Payments"],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Payment cancelled"}}
                }
            },
            "/users/register/": {
                "post": {
                    "summary": "Register a new user",
                    "tags": ["Users"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["email", "password", "first_name", "last_name"],
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                        "first_name": {"type": "string"},
                                        "last_name": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "User registered"}}
                }
            },
            "/users/me/": {
                "get": {
                    "summary": "Get current user profile",
                    "tags": ["Users"],
                    "security": [{"BearerAuth": []}],
                    "responses": {"200": {"description": "User profile"}}
                },
                "put": {
                    "summary": "Update current user profile",
                    "tags": ["Users"],
                    "security": [{"BearerAuth": []}],
                    "responses": {"200": {"description": "Profile updated"}}
                },
                "patch": {
                    "summary": "Partial update current user profile",
                    "tags": ["Users"],
                    "security": [{"BearerAuth": []}],
                    "responses": {"200": {"description": "Profile updated"}}
                }
            },
            "/users/token/": {
                "post": {
                    "summary": "Obtain JWT token pair",
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
                                        "password": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Token pair"}}
                }
            },
            "/users/token/refresh/": {
                "post": {
                    "summary": "Refresh JWT access token",
                    "tags": ["Authentication"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["refresh"],
                                    "properties": {
                                        "refresh": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "New access token"}}
                }
            }
        }
    }
    
    # ============================================================
    # ROUTES - DOCUMENTATION
    # ============================================================
    
    @app.route("/api/v1/doc/swagger/")
    def swagger_ui():
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Library Service API - Swagger UI</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" >
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"> </script>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"> </script>
<script>
window.onload = function() {
    const ui = SwaggerUIBundle({
        url: "/api/v1/doc/swagger.json",
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout"
    })
    window.ui = ui
}
</script>
</body>
</html>"""
        from flask import Response
        return Response(html, mimetype='text/html')
    
    @app.route("/api/v1/doc/swagger.json")
    def swagger_spec():
        return jsonify(SWAGGER_SPEC)
    
    # ============================================================
    # ROUTES - ADMIN
    # ============================================================
    
    @app.route("/admin/")
    def admin_panel():
        user = get_current_user()
        if not user or not user["is_staff"]:
            return jsonify({"error": "Admin access required. Please provide admin Bearer token."}), 403
        
        stats = {
            "total_users": len(db.users),
            "total_books": len(db.books),
            "total_borrowings": len(db.borrowings),
            "total_payments": len(db.payments),
            "active_borrowings": sum(1 for b in db.borrowings.values() if not b["actual_return_date"]),
            "pending_payments": sum(1 for p in db.payments.values() if p["status"] == "PENDING"),
            "users": [Serializer.serialize_user(u) for u in db.users.values()],
            "books": [Serializer.serialize_book(b) for b in db.books.values()],
            "borrowings": [Serializer.serialize_borrowing(b, include_user=True) for b in db.borrowings.values()],
            "payments": [Serializer.serialize_payment(p) for p in db.payments.values()]
        }
        return jsonify(stats)
    
    # ============================================================
    # ROUTES - AUTHENTICATION
    # ============================================================
    
    @app.route("/api/v1/users/token/", methods=["POST"])
    def obtain_token():
        data = request.get_json() or {}
        email = data.get("email", "").lower().strip()
        password = data.get("password", "")
        
        if not email or not password:
            return error_response("Email and password are required", 400)
        
        user = db.get_user_by_email(email)
        if not user or not db.verify_password(password, user["password"]):
            return error_response("Invalid credentials", 401)
        
        if not user["is_active"]:
            return error_response("Account is disabled", 401)
        
        access_token = JWT.create_access_token(user["id"])
        refresh_token = JWT.create_refresh_token(user["id"])
        
        return success_response({
            "access": access_token,
            "refresh": refresh_token,
            "user": Serializer.serialize_user(user)
        })
    
    @app.route("/api/v1/users/token/refresh/", methods=["POST"])
    def refresh_token():
        data = request.get_json() or {}
        refresh = data.get("refresh", "")
        
        if not refresh:
            return error_response("Refresh token is required", 400)
        
        payload = JWT.decode_token(refresh)
        if not payload or payload.get("type") != "refresh":
            return error_response("Invalid or expired refresh token", 401)
        
        user = db.get_user_by_id(payload.get("user_id", ""))
        if not user or not user["is_active"]:
            return error_response("User not found or inactive", 401)
        
        access_token = JWT.create_access_token(user["id"])
        return success_response({"access": access_token})
    
    # ============================================================
    # ROUTES - USERS
    # ============================================================
    
    @app.route("/api/v1/users/register/", methods=["POST"])
    def register_user():
        data = request.get_json() or {}
        
        try:
            cleaned = UserValidator.validate_register(data)
        except ValidationError as e:
            return error_response("Validation failed", 400, e.errors)
        
        if db.get_user_by_email(cleaned["email"]):
            return error_response("User with this email already exists", 400)
        
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": cleaned["email"],
            "password": db._hash_password(cleaned["password"]),
            "first_name": cleaned["first_name"],
            "last_name": cleaned["last_name"],
            "is_staff": False,
            "is_active": True,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        db.users[user_id] = user
        
        return success_response(Serializer.serialize_user(user), 201)
    
    @app.route("/api/v1/users/me/", methods=["GET", "PUT", "PATCH"])
    @require_auth
    def user_profile():
        user = g.current_user
        
        if request.method == "GET":
            return success_response(Serializer.serialize_user(user))
        
        data = request.get_json() or {}
        
        try:
            if request.method == "PUT":
                # Full update - require all fields
                cleaned = UserValidator.validate_update(data)
            else:
                # Partial update
                cleaned = UserValidator.validate_update(data)
        except ValidationError as e:
            return error_response("Validation failed", 400, e.errors)
        
        if "email" in cleaned and cleaned["email"] != user["email"]:
            existing = db.get_user_by_email(cleaned["email"])
            if existing:
                return error_response("User with this email already exists", 400)
        
        if "password" in cleaned:
            cleaned["password"] = db._hash_password(cleaned["password"])
        
        user.update(cleaned)
        db.users[user["id"]] = user
        
        return success_response(Serializer.serialize_user(user))
    
    @app.route("/api/v1/users/", methods=["GET"])
    @require_admin
    def list_users():
        users = list(db.users.values())
        
        # Filtering
        email_filter = request.args.get("email", "")
        if email_filter:
            users = [u for u in users if email_filter.lower() in u["email"].lower()]
        
        is_staff_filter = request.args.get("is_staff")
        if is_staff_filter is not None:
            is_staff = is_staff_filter.lower() == "true"
            users = [u for u in users if u["is_staff"] == is_staff]
        
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        
        serialized = [Serializer.serialize_user(u) for u in users]
        return success_response(paginate(serialized, page, page_size))
    
    @app.route("/api/v1/users/<user_id>/", methods=["GET", "PUT", "PATCH", "DELETE"])
    @require_admin
    def user_detail(user_id: str):
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", 404)
        
        if request.method == "GET":
            return success_response(Serializer.serialize_user(user))
        
        if request.method == "DELETE":
            del db.users[user_id]
            return jsonify({}), 204
        
        data = request.get_json() or {}
        try:
            cleaned = UserValidator.validate_update(data)
        except ValidationError as e:
            return error_response("Validation failed", 400, e.errors)
        
        if "password" in cleaned:
            cleaned["password"] = db._hash_password(cleaned["password"])
        
        user.update(cleaned)
        db.users[user_id] = user
        return success_response(Serializer.serialize_user(user))
    
    # ============================================================
    # ROUTES - BOOKS
    # ============================================================
    
    @app.route("/api/v1/books/", methods=["GET"])
    def list_books():
        books = list(db.books.values())
        
        # Filtering
        title_filter = request.args.get("title", "")
        if title_filter:
            books = [b for b in books if title_filter.lower() in b["title"].lower()]
        
        author_filter = request.args.get("author", "")
        if author_filter:
            books = [b for b in books if author_filter.lower() in b["author"].lower()]
        
        cover_filter = request.args.get("cover", "")
        if cover_filter:
            books = [b for b in books if b["cover"] == cover_filter.upper()]
        
        available_filter = request.args.get("available")
        if available_filter is not None:
            if available_filter.lower() == "true":
                books = [b for b in books if b["inventory"] > 0]
            elif available_filter.lower() == "false":
                books = [b for b in books if b["inventory"] == 0]
        
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        
        serialized = [Serializer.serialize_book(b) for b in books]
        return success_response(paginate(serialized, page, page_size))
    
    @app.route("/api/v1/books/", methods=["POST"])
    @require_admin
    def create_book():
        data = request.get_json() or {}
        
        try:
            cleaned = BookValidator.validate_create(data)
        except ValidationError as e:
            return error_response("Validation failed", 400, e.errors)
        
        book_id = str(uuid.uuid4())
        book = {
            "id": book_id,
            "title": cleaned["title"],
            "author": cleaned["author"],
            "cover": cleaned["cover"],
            "inventory": cleaned["inventory"],
            "daily_fee": cleaned["daily_fee"],
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        db.books[book_id] = book
        
        return success_response(Serializer.serialize_book(book), 201)
    
    @app.route("/api/v1/books/<book_id>/", methods=["GET"])
    def get_book(book_id: str):
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found", 404)
        return success_response(Serializer.serialize_book(book))
    
    @app.route("/api/v1/books/<book_id>/", methods=["PUT", "PATCH"])
    @require_admin
    def update_book(book_id: str):
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found", 404)
        
        data = request.get_json() or {}
        
        try:
            if request.method == "PUT":
                cleaned = BookValidator.validate_create(data)
            else:
                cleaned = BookValidator.validate_update(data)
        except ValidationError as e:
            return error_response("Validation failed", 400, e.errors)
        
        book.update(cleaned)
        db.books[book_id] = book
        
        return success_response(Serializer.serialize_book(book))
    
    @app.route("/api/v1/books/<book_id>/", methods=["DELETE"])
    @require_admin
    def delete_book(book_id: str):
        book = db.get_book_by_id(book_id)
        if not book:
            return error_response("Book not found", 404)
        
        # Check if book has active borrowings
        active_borrowings = [
            b for b in db.borrowings.values()
            if b["book_id"] == book_id and not b["actual_return_date"]
        ]
        if active_borrowings:
            return error_response("Cannot delete book with active borrowings", 400)
        
        del db.books[book_id]
        return jsonify({}), 204
    
    # ============================================================
    # ROUTES - BORROWINGS
    # ============================================================
    
    @app.route("/api/v1/borrowings/", methods=["GET"])
    @require_auth
    def list_borrowings():
        user = g.current_user
        borrowings = list(db.borrowings.values())
        
        # Non-admin users can only see their own borrowings
        if not user["is_staff"]:
            borrowings = [b for b in borrowings if b["user_id"] == user["id"]]
        else:
            # Admin can filter by user_id
            user_id_filter = request.args.get("user_id", "")
            if user_id_filter:
                borrowings = [b for b in borrowings if b["user_id"] == user_id_filter]
        
        # Filter by is_active (actual_return_date)
        is_active_filter = request.args.get("is_active")
        if is_active_filter is not None:
            if is_active_filter.lower() == "true":
                # Active = not returned (actual_return_date is None)
                borrowings = [b for b in borrowings if not b["actual_return_date"]]
            elif is_active_filter.lower() == "false":
                # Inactive = returned
                borrowings = [b for b in borrowings if b["actual_return_date"]]
        
        # Filter by book
        book_id_filter = request.args.get("book_id", "")
        if book_id_filter:
            borrowings = [b for b in borrowings if b["book_id"] == book_id_filter]
        
        # Filter by borrow_date
        borrow_date_filter = request.args.get("borrow_date", "")
        if borrow_date_filter:
            borrowings = [b for b in borrowings if b["borrow_date"] == borrow_date_filter]
        
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        
        include_user = user["is_staff"]
        serialized = [Serializer.serialize_borrowing(b, include_user=include_user) for b in borrowings]
        return success_response(paginate(serialized, page, page_size))
    
    @app.route("/api/v1/borrowings/", methods=["POST"])
    @require_auth
    def create_borrowing():
        user = g.current_user
        data = request.get_json() or {}
        
        try:
            cleaned = BorrowingValidator.validate_create(data)
        except ValidationError as e:
            return error_response("Validation failed", 400, e.errors)
        
        try:
            borrowing = BorrowingService.create_borrowing(
                user["id"],
                cleaned["book_id"],
                cleaned["expected_return_date"]
            )
        except ValueError as e:
            return error_response(str(e), 400)
        
        # Get the created payment
        payment = None
        for p in db.payments.values():
            if p["borrowing_id"] == borrowing["id"] and p["type"] == "PAYMENT":
                payment = p
                break
        
        response_data = Serializer.serialize_borrowing(borrowing)
        if payment:
            response_data["payment"] = Serializer.serialize_payment(payment, include_borrowing=False)
        
        return success_response(response_data, 201)
    
    @app.route("/api/v1/borrowings/<borrowing_id>/", methods=["GET"])
    @require_auth
    def get_borrowing(borrowing_id: str):
        user = g.current_user
        borrowing = db.get_borrowing_by_id(borrowing_id)
        
        if not borrowing:
            return error_response("Borrowing not found", 404)
        
        if not user["is_staff"] and borrowing["user_id"] != user["id"]:
            return error_response("Access denied", 403)
        
        return success_response(Serializer.serialize_borrowing(borrowing, include_user=user["is_staff"]))
    
    @app.route("/api/v1/borrowings/<borrowing_id>/return/", methods=["POST"])
    @require_auth
    def return_borrowing(borrowing_id: str):
        user = g.current_user
        borrowing = db.get_borrowing_by_id(borrowing_id)
        
        if not borrowing:
            return error_response("Borrowing not found", 404)
        
        if not user["is_staff"] and borrowing["user_id"] != user["id"]:
            return error_response("Access denied", 403)
        
        try:
            result = BorrowingService.return_book(borrowing_id, borrowing["user_id"])
        except ValueError as e:
            return error_response(str(e), 400)
        
        response_data = {
            "borrowing": Serializer.serialize_borrowing(result["borrowing"]),
            "message": "Book returned successfully"
        }
        
        if result["fine_payment"]:
            response_data["fine_payment"] = Serializer.serialize_payment(result["fine_payment"], include_borrowing=False)
            response_data["message"] = "Book returned with overdue fine. Please pay the fine."
        
        return success_response(response_data)
    
    # ============================================================
    # ROUTES - PAYMENTS
    # ============================================================
    
    @app.route("/api/v1/payments/", methods=["GET"])
    @require_auth
    def list_payments():
        user = g.current_user
        payments = list(db.payments.values())
        
        # Non-admin users can only see their own payments
        if not user["is_staff"]:
            user_borrowing_ids = {b["id"] for b in db.borrowings.values() if b["user_id"] == user["id"]}
            payments = [p for p in payments if p["borrowing_id"] in user_borrowing_ids]
        else:
            # Admin can filter by user_id
            user_id_filter = request.args.get("user_id", "")
            if user_id_filter:
                user_borrowing_ids = {b["id"] for b in db.borrowings.values() if b["user_id"] == user_id_filter}
                payments = [p for p in payments if p["borrowing_id"] in user_borrowing_ids]
        
        # Filter by status
        status_filter = request.args.get("status", "")
        if status_filter:
            payments = [p for p in payments if p["status"] == status_filter.upper()]
        
        # Filter by type
        type_filter = request.args.get("type", "")
        if type_filter:
            payments = [p for p in payments if p["type"] == type_filter.upper()]
        
        # Filter by borrowing_id
        borrowing_id_filter = request.args.get("borrowing_id", "")
        if borrowing_id_filter:
            payments = [p for p in payments if p["borrowing_id"] == borrowing_id_filter]
        
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        
        serialized = [Serializer.serialize_payment(p) for p in payments]
        return success_response(paginate(serialized, page, page_size))
    
    @app.route("/api/v1/payments/<payment_id>/", methods=["GET"])
    @require_auth
    def get_payment(payment_id: str):
        user = g.current_user
        payment = db.get_payment_by_id(payment_id)
        
        if not payment:
            return error_response("Payment not found", 404)
        
        # Check access
        if not user["is_staff"]:
            borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
            if not borrowing or borrowing["user_id"] != user["id"]:
                return error_response("Access denied", 403)
        
        return success_response(Serializer.serialize_payment(payment))
    
    @app.route("/api/v1/payments/<payment_id>/success/", methods=["GET"])
    def payment_success(payment_id: str):
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            return error_response("Payment not found", 404)
        
        try:
            completed_payment = PaymentService.complete_payment(payment_id)
            return success_response({
                "message": "Payment completed successfully",
                "payment": Serializer.serialize_payment(completed_payment)
            })
        except ValueError as e:
            return error_response(str(e), 400)
    
    @app.route("/api/v1/payments/<payment_id>/cancel/", methods=["GET"])
    def payment_cancel(payment_id: str):
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            return error_response("Payment not found", 404)
        
        return success_response({
            "message": "Payment was cancelled. You can pay later but please note the session is available for 24 hours.",
            "payment": Serializer.serialize_payment(payment)
        })
    
    # ============================================================
    # ERROR HANDLERS
    # ============================================================
    
    @app.errorhandler(404)
    def not_found(e):
        return error_response("Resource not found", 404)
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response("Method not allowed", 405)
    
    @app.errorhandler(500)
    def internal_error(e):
        return error_response("Internal server error", 500)
    
    # ============================================================
    # ROOT ENDPOINT
    # ============================================================
    
    @app.route("/")
    def root():
        return jsonify({
            "message": "Library Service API",
            "version": "1.0.0",
            "endpoints": {
                "documentation": "/api/v1/doc/swagger/",
                "admin": "/admin/",
                "authentication": {
                    "obtain_token": "/api/v1/users/token/",
                    "refresh_token": "/api/v1/users/token/refresh/"
                },
                "users": {
                    "register": "/api/v1/users/register/",
                    "profile": "/api/v1/users/me/",
                    "list": "/api/v1/users/"
                },
                "books": "/api/v1/books/",
                "borrowings": "/api/v1/borrowings/",
                "payments": "/api/v1/payments/"
            }
        })
    
    @app.route("/api/v1/")
    def api_root():
        return jsonify({
            "message": "Library Service API v1",
            "documentation": "/api/v1/doc/swagger/"
        })


# ============================================================
# LIBRARY SERVICE CORE CLASSES (Framework-independent)
# ============================================================

class Book:
    """Represents a book in the library"""
    
    COVER_HARD = "HARD"
    COVER_SOFT = "SOFT"
    COVER_CHOICES = [COVER_HARD, COVER_SOFT]
    
    def __init__(
        self,
        title: str,
        author: str,
        cover: str,
        inventory: int,
        daily_fee: Decimal,
        book_id: str = None
    ):
        self.id = book_id or str(uuid.uuid4())
        self.title = title
        self.author = author
        self.cover = cover
        self.inventory = inventory
        self.daily_fee = Decimal(str(daily_fee))
        self.created_at = datetime.datetime.utcnow()
        self._validate()
    
    def _validate(self):
        if not self.title:
            raise ValueError("Title is required")
        if not self.author:
            raise ValueError("Author is required")
        if self.cover not in self.COVER_CHOICES:
            raise ValueError(f"Cover must be one of: {', '.join(self.COVER_CHOICES)}")
        if self.inventory < 0:
            raise ValueError("Inventory must be non-negative")
        if self.daily_fee <= 0:
            raise ValueError("Daily fee must be positive")
    
    def is_available(self) -> bool:
        return self.inventory > 0
    
    def decrease_inventory(self):
        if self.inventory <= 0:
            raise ValueError("Book is not available")
        self.inventory -= 1
    
    def increase_inventory(self):
        self.inventory += 1
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "cover": self.cover,
            "inventory": self.inventory,
            "daily_fee": str(self.daily_fee),
            "created_at": self.created_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f"Book(id={self.id}, title={self.title}, author={self.author})"


class User:
    """Represents a user in the library system"""
    
    def __init__(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        is_staff: bool = False,
        user_id: str = None
    ):
        self.id = user_id or str(uuid.uuid4())
        self.email = email.lower().strip()
        self.password_hash = self._hash_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_staff = is_staff
        self.is_active = True
        self.created_at = datetime.datetime.utcnow()
        self._validate()
    
    def _validate(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email is required")
        if not self.first_name:
            raise ValueError("First name is required")
        if not self.last_name:
            raise ValueError("Last name is required")
    
    def _hash_password(self, password: str) -> str:
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return base64.b64encode(salt + key).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        try:
            decoded = base64.b64decode(self.password_hash.encode('utf-8'))
            salt = decoded[:32]
            stored_key = decoded[32:]
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return hmac.compare_digest(key, stored_key)
        except Exception:
            return False
    
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_staff": self.is_staff,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email})"


class Borrowing:
    """Represents a book borrowing"""
    
    def __init__(
        self,
        user_id: str,
        book_id: str,
        expected_return_date: datetime.date,
        borrowing_id: str = None
    ):
        self.id = borrowing_id or str(uuid.uuid4())
        self.user_id = user_id
        self.book_id = book_id
        self.borrow_date = datetime.date.today()
        self.expected_return_date = expected_return_date
        self.actual_return_date: Optional[datetime.date] = None
        self.created_at = datetime.datetime.utcnow()
        self._validate()
    
    def _validate(self):
        if not self.user_id:
            raise ValueError("User ID is required")
        if not self.book_id:
            raise ValueError("Book ID is required")
        if self.expected_return_date <= self.borrow_date:
            raise ValueError("Expected return date must be in the future")
    
    def is_active(self) -> bool:
        return self.actual_return_date is None
    
    def is_overdue(self) -> bool:
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return datetime.date.today() > self.expected_return_date
    
    def return_book(self):
        if self.actual_return_date:
            raise ValueError("Book already returned")
        self.actual_return_date = datetime.date.today()
    
    def get_overdue_days(self) -> int:
        if not self.actual_return_date:
            return max(0, (datetime.date.today() - self.expected_return_date).days)
        return max(0, (self.actual_return_date - self.expected_return_date).days)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "book_id": self.book_id,
            "borrow_date": self.borrow_date.isoformat(),
            "expected_return_date": self.expected_return_date.isoformat(),
            "actual_return_date": self.actual_return_date.isoformat() if self.actual_return_date else None,
            "created_at": self.created_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f"Borrowing(id={self.id}, user_id={self.user_id}, book_id={self.book_id})"


class Payment:
    """Represents a payment for a borrowing"""
    
    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_CHOICES = [STATUS_PENDING, STATUS_PAID]
    
    TYPE_PAYMENT = "PAYMENT"
    TYPE_FINE = "FINE"
    TYPE_CHOICES = [TYPE_PAYMENT, TYPE_FINE]
    
    FINE_MULTIPLIER = Decimal("2.0")
    
    def __init__(
        self,
        borrowing_id: str,
        money_to_pay: Decimal,
        payment_type: str = TYPE_PAYMENT,
        payment_id: str = None
    ):
        self.id = payment_id or str(uuid.uuid4())
        self.status = self.STATUS_PENDING
        self.type = payment_type
        self.borrowing_id = borrowing_id
        self.money_to_pay = Decimal(str(money_to_pay))
        self.session_id = f"cs_test_{self.id}"
        self.session_url = f"https://checkout.stripe.com/pay/{self.session_id}"
        self.created_at = datetime.datetime.utcnow()
        self.paid_at: Optional[datetime.datetime] = None
        self._validate()
    
    def _validate(self):
        if not self.borrowing_id:
            raise ValueError("Borrowing ID is required")
        if self.money_to_pay < 0:
            raise ValueError("Amount must be non-negative")
        if self.type not in self.TYPE_CHOICES:
            raise ValueError(f"Type must be one of: {', '.join(self.TYPE_CHOICES)}")
    
    def complete(self):
        if self.status == self.STATUS_PAID:
            raise ValueError("Payment already completed")
        self.status = self.STATUS_PAID
        self.paid_at = datetime.datetime.utcnow()
    
    def is_paid(self) -> bool:
        return self.status == self.STATUS_PAID
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "status": self.status,
            "type": self.type,
            "borrowing_id": self.borrowing_id,
            "session_url": self.session_url,
            "session_id": self.session_id,
            "money_to_pay": str(self.money_to_pay),
            "created_at": self.created_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None
        }
    
    def __repr__(self) -> str:
        return f"Payment(id={self.id}, type={self.type}, status={self.status}, amount={self.money_to_pay})"


class LibraryService:
    """Main service class for the library system"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.books: Dict[str, Book] = {}
        self.borrowings: Dict[str, Borrowing] = {}
        self.payments: Dict[str, Payment] = {}
    
    def register_user(self, email: str, password: str, first_name: str, last_name: str) -> User:
        if any(u.email == email.lower() for u in self.users.values()):
            raise ValueError("User with this email already exists")
        
        user = User(email, password, first_name, last_name)
        self.users[user.id] = user
        return user
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = next((u for u in self.users.values() if u.email == email.lower()), None)
        if user and user.verify_password(password) and user.is_active:
            return user
        return None
    
    def add_book(self, title: str, author: str, cover: str, inventory: int, daily_fee: Decimal) -> Book:
        book = Book(title, author, cover, inventory, daily_fee)
        self.books[book.id] = book
        return book
    
    def get_book(self, book_id: str) -> Optional[Book]:
        return self.books.get(book_id)
    
    def list_books(
        self,
        title: str = None,
        author: str = None,
        cover: str = None,
        available_only: bool = False
    ) -> List[Book]:
        books = list(self.books.values())
        
        if title:
            books = [b for b in books if title.lower() in b.title.lower()]
        if author:
            books = [b for b in books if author.lower() in b.author.lower()]
        if cover:
            books = [b for b in books if b.cover == cover.upper()]
        if available_only:
            books = [b for b in books if b.is_available()]
        
        return books
    
    def borrow_book(self, user_id: str, book_id: str, expected_return_date: datetime.date) -> tuple:
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        book = self.books.get(book_id)
        if not book:
            raise ValueError("Book not found")
        
        if not book.is_available():
            raise ValueError("Book is not available")
        
        # Check for pending payments
        user_borrowing_ids = {b.id for b in self.borrowings.values() if b.user_id == user_id}
        pending_payments = [
            p for p in self.payments.values()
            if p.borrowing_id in user_borrowing_ids and not p.is_paid()
        ]
        if pending_payments:
            raise ValueError("You have pending payments. Please complete them before borrowing.")
        
        borrowing = Borrowing(user_id, book_id, expected_return_date)
        book.decrease_inventory()
        self.borrowings[borrowing.id] = borrowing
        
        # Calculate payment amount
        days = (expected_return_date - borrowing.borrow_date).days
        if days <= 0:
            days = 1
        amount = book.daily_fee * days
        
        payment = Payment(borrowing.id, amount, Payment.TYPE_PAYMENT)
        self.payments[payment.id] = payment
        
        return borrowing, payment
    
    def return_book(self, borrowing_id: str, user_id: str) -> tuple:
        borrowing = self.borrowings.get(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found")
        
        if borrowing.user_id != user_id:
            raise ValueError("Access denied")
        
        borrowing.return_book()
        
        book = self.books.get(borrowing.book_id)
        if book:
            book.increase_inventory()
        
        fine_payment = None
        if borrowing.is_overdue():
            overdue_days = borrowing.get_overdue_days()
            if book:
                fine_amount = book.daily_fee * overdue_days * Payment.FINE_MULTIPLIER
                fine_payment = Payment(borrowing.id, fine_amount, Payment.TYPE_FINE)
                self.payments[fine_payment.id] = fine_payment
        
        return borrowing, fine_payment
    
    def get_user_borrowings(
        self,
        user_id: str,
        is_active: bool = None
    ) -> List[Borrowing]:
        borrowings = [b for b in self.borrowings.values() if b.user_id == user_id]
        
        if is_active is True:
            borrowings = [b for b in borrowings if b.is_active()]
        elif is_active is False:
            borrowings = [b for b in borrowings if not b.is_active()]
        
        return borrowings
    
    def get_all_borrowings(
        self,
        user_id: str = None,
        is_active: bool = None
    ) -> List[Borrowing]:
        borrowings = list(self.borrowings.values())
        
        if user_id:
            borrowings = [b for b in borrowings if b.user_id == user_id]
        
        if is_active is True:
            borrowings = [b for b in borrowings if b.is_active()]
        elif is_active is False:
            borrowings = [b for b in borrowings if not b.is_active()]
        
        return borrowings
    
    def get_user_payments(
        self,
        user_id: str,
        status: str = None,
        payment_type: str = None
    ) -> List[Payment]:
        user_borrowing_ids = {b.id for b in self.borrowings.values() if b.user_id == user_id}
        payments = [p for p in self.payments.values() if p.borrowing_id in user_borrowing_ids]
        
        if status:
            payments = [p for p in payments if p.status == status.upper()]
        if payment_type:
            payments = [p for p in payments if p.type == payment_type.upper()]
        
        return payments
    
    def complete_payment(self, payment_id: str) -> Payment:
        payment = self.payments.get(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        payment.complete()
        return payment


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def create_app():
    """Application factory"""
    if FLASK_AVAILABLE:
        return app
    else:
        raise RuntimeError("Flask is not installed. Please install it with: pip install flask")


def run_demo():
    """Run a demonstration of the library service"""
    print("=" * 60)
    print("Library Service API - Demo")
    print("=" * 60)
    
    service = LibraryService()
    
    # Register users
    print("\n1. Registering users...")
    user1 = service.register_user("john@example.com", "password123", "John", "Doe")
    user2 = service.register_user("jane@example.com", "password456", "Jane", "Smith")
    print(f"   Registered: {user1}")
    print(f"   Registered: {user2}")
    
    # Add books
    print("\n2. Adding books...")
    book1 = service.add_book("The Great Gatsby", "F. Scott Fitzgerald", "HARD", 3, Decimal("1.50"))
    book2 = service.add_book("1984", "George Orwell", "SOFT", 2, Decimal("2.00"))
    print(f"   Added: {book1}")
    print(f"   Added: {book2}")
    
    # Borrow a book
    print("\n3. Borrowing a book...")
    expected_return = datetime.date.today() + datetime.timedelta(days=7)
    borrowing, payment = service.borrow_book(user1.id, book1.id, expected_return)
    print(f"   Borrowing: {borrowing}")
    print(f"   Payment: {payment}")
    print(f"   Amount to pay: ${payment.money_to_pay}")
    
    # Complete payment
    print("\n4. Completing payment...")
    payment.complete()
    print(f"   Payment status: {payment.status}")
    
    # Return book (simulate overdue)
    print("\n5. Returning book (simulating overdue)...")
    borrowing.expected_return_date = datetime.date.today() - datetime.timedelta(days=2)
    returned_borrowing, fine_payment = service.return_book(borrowing.id, user1.id)
    print(f"   Returned: {returned_borrowing}")
    if fine_payment:
        print(f"   Fine payment: {fine_payment}")
        print(f"   Fine amount: ${fine_payment.money_to_pay}")
    
    # JWT Demo
    print("\n6. JWT Token Demo...")
    access_token = JWT.create_access_token(user1.id)
    refresh_token = JWT.create_refresh_token(user1.id)
    print(f"   Access token created: {access_token[:50]}...")
    
    decoded = JWT.decode_token(access_token)
    print(f"   Decoded payload: user_id={decoded['user_id']}, type={decoded['type']}")
    
    # List books with filtering
    print("\n7. Filtering books...")
    available_books = service.list_books(available_only=True)
    print(f"   Available books: {len(available_books)}")
    
    hard_cover_books = service.list_books(cover="HARD")
    print(f"   Hard cover books: {len(hard_cover_books)}")
    
    # List borrowings with filtering
    print("\n8. Filtering borrowings...")
    active_borrowings = service.get_all_borrowings(is_active=True)
    print(f"   Active borrowings: {len(active_borrowings)}")
    
    returned_borrowings = service.get_all_borrowings(is_active=False)
    print(f"   Returned borrowings: {len(returned_borrowings)}")
    
    user1_borrowings = service.get_all_borrowings(user_id=user1.id)
    print(f"   User1 borrowings: {len(user1_borrowings)}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    
    if FLASK_AVAILABLE:
        print("\nTo start the Flask server, run:")
        print("  python solution.py server")
        print("\nAPI Endpoints:")
        print("  GET  /                              - API info")
        print("  GET  /admin/                        - Admin panel")
        print("  GET  /api/v1/doc/swagger/           - Swagger UI")
        print("  POST /api/v1/users/register/        - Register user")
        print("  POST /api/v1/users/token/           - Get JWT token")
        print("  POST /api/v1/users/token/refresh/   - Refresh token")
        print("  GET  /api/v1/users/me/              - User profile")
        print("  GET  /api/v1/books/                 - List books")
        print("  POST /api/v1/books/                 - Create book (admin)")
        print("  GET  /api/v1/borrowings/            - List borrowings")
        print("  POST /api/v1/borrowings/            - Create borrowing")
        print("  POST /api/v1/borrowings/{id}/return/ - Return book")
        print("  GET  /api/v1/payments/              - List payments")
        print("  GET  /api/v1/payments/{id}/success/ - Payment success")
        print("  GET  /api/v1/payments/{id}/cancel/  - Payment cancel")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        if FLASK_AVAILABLE:
            print("Starting Library Service API server...")
            print("Admin credentials: admin@library.com / admin123")
            print("Documentation: http://localhost:5000/api/v1/doc/swagger/")
            print("Admin panel: http://localhost:5000/admin/")
            app.run(debug=True, host="0.0.0.0", port=5000)
        else:
            print("Flask is not installed. Please install it with: pip install flask")
            sys.exit(1)
    else:
        run_demo()