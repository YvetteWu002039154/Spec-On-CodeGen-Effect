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
import decimal
from typing import Optional, List, Dict, Any
from functools import wraps

# ============================================================
# Configuration
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "library-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_dummy")
FINE_MULTIPLIER = decimal.Decimal("2.0")  # Fine is 2x daily fee

# ============================================================
# Database (In-memory for standalone implementation)
# ============================================================

class Database:
    def __init__(self):
        self.users: Dict[int, Dict] = {}
        self.books: Dict[int, Dict] = {}
        self.borrowings: Dict[int, Dict] = {}
        self.payments: Dict[int, Dict] = {}
        self._user_counter = 1
        self._book_counter = 1
        self._borrowing_counter = 1
        self._payment_counter = 1
        self._create_admin()

    def _create_admin(self):
        admin = {
            "id": self._user_counter,
            "email": "admin@library.com",
            "first_name": "Admin",
            "last_name": "User",
            "password": self._hash_password("admin123"),
            "is_staff": True,
            "is_active": True,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.users[self._user_counter] = admin
        self._user_counter += 1

    def _hash_password(self, password: str) -> str:
        salt = "library_salt"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        return self._hash_password(password) == hashed

    # User operations
    def create_user(self, email: str, password: str, first_name: str, last_name: str, is_staff: bool = False) -> Dict:
        for user in self.users.values():
            if user["email"] == email:
                raise ValueError("User with this email already exists")
        user = {
            "id": self._user_counter,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": self._hash_password(password),
            "is_staff": is_staff,
            "is_active": True,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.users[self._user_counter] = user
        self._user_counter += 1
        return user

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        return self.users.get(user_id)

    def update_user(self, user_id: int, data: Dict) -> Optional[Dict]:
        user = self.users.get(user_id)
        if not user:
            return None
        if "password" in data:
            data["password"] = self._hash_password(data["password"])
        user.update(data)
        return user

    def list_users(self) -> List[Dict]:
        return list(self.users.values())

    # Book operations
    def create_book(self, title: str, author: str, cover: str, inventory: int, daily_fee: str) -> Dict:
        book = {
            "id": self._book_counter,
            "title": title,
            "author": author,
            "cover": cover,
            "inventory": inventory,
            "daily_fee": daily_fee,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.books[self._book_counter] = book
        self._book_counter += 1
        return book

    def get_book(self, book_id: int) -> Optional[Dict]:
        return self.books.get(book_id)

    def update_book(self, book_id: int, data: Dict) -> Optional[Dict]:
        book = self.books.get(book_id)
        if not book:
            return None
        book.update(data)
        return book

    def delete_book(self, book_id: int) -> bool:
        if book_id in self.books:
            del self.books[book_id]
            return True
        return False

    def list_books(self) -> List[Dict]:
        return list(self.books.values())

    # Borrowing operations
    def create_borrowing(self, user_id: int, book_id: int, expected_return_date: str) -> Dict:
        book = self.books.get(book_id)
        if not book:
            raise ValueError("Book not found")
        if book["inventory"] <= 0:
            raise ValueError("Book is not available (inventory is 0)")
        book["inventory"] -= 1
        borrowing = {
            "id": self._borrowing_counter,
            "user_id": user_id,
            "book_id": book_id,
            "borrow_date": datetime.date.today().isoformat(),
            "expected_return_date": expected_return_date,
            "actual_return_date": None,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.borrowings[self._borrowing_counter] = borrowing
        self._borrowing_counter += 1
        return borrowing

    def get_borrowing(self, borrowing_id: int) -> Optional[Dict]:
        return self.borrowings.get(borrowing_id)

    def return_borrowing(self, borrowing_id: int) -> Optional[Dict]:
        borrowing = self.borrowings.get(borrowing_id)
        if not borrowing:
            return None
        if borrowing["actual_return_date"] is not None:
            raise ValueError("Book already returned")
        borrowing["actual_return_date"] = datetime.date.today().isoformat()
        book = self.books.get(borrowing["book_id"])
        if book:
            book["inventory"] += 1
        return borrowing

    def list_borrowings(self, user_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[Dict]:
        result = list(self.borrowings.values())
        if user_id is not None:
            result = [b for b in result if b["user_id"] == user_id]
        if is_active is True:
            result = [b for b in result if b["actual_return_date"] is None]
        elif is_active is False:
            result = [b for b in result if b["actual_return_date"] is not None]
        return result

    # Payment operations
    def create_payment(self, borrowing_id: int, payment_type: str, money_to_pay: str, session_url: str, session_id: str) -> Dict:
        payment = {
            "id": self._payment_counter,
            "borrowing_id": borrowing_id,
            "status": "PENDING",
            "type": payment_type,
            "session_url": session_url,
            "session_id": session_id,
            "money_to_pay": money_to_pay,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.payments[self._payment_counter] = payment
        self._payment_counter += 1
        return payment

    def get_payment(self, payment_id: int) -> Optional[Dict]:
        return self.payments.get(payment_id)

    def get_payment_by_session(self, session_id: str) -> Optional[Dict]:
        for payment in self.payments.values():
            if payment["session_id"] == session_id:
                return payment
        return None

    def update_payment_status(self, payment_id: int, status: str) -> Optional[Dict]:
        payment = self.payments.get(payment_id)
        if not payment:
            return None
        payment["status"] = status
        return payment

    def list_payments(self, user_id: Optional[int] = None) -> List[Dict]:
        result = list(self.payments.values())
        if user_id is not None:
            borrowing_ids = {b["id"] for b in self.borrowings.values() if b["user_id"] == user_id}
            result = [p for p in result if p["borrowing_id"] in borrowing_ids]
        return result


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
    def encode(cls, payload: Dict, secret: str) -> str:
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        header_encoded = cls._base64url_encode(json.dumps(header).encode())
        payload_encoded = cls._base64url_encode(json.dumps(payload).encode())
        signing_input = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            secret.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        signature_encoded = cls._base64url_encode(signature)
        return f"{signing_input}.{signature_encoded}"

    @classmethod
    def decode(cls, token: str, secret: str) -> Dict:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            header_encoded, payload_encoded, signature_encoded = parts
            signing_input = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                secret.encode(),
                signing_input.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = cls._base64url_encode(expected_signature)
            if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
                raise ValueError("Invalid token signature")
            payload = json.loads(cls._base64url_decode(payload_encoded))
            if "exp" in payload:
                if datetime.datetime.utcnow().timestamp() > payload["exp"]:
                    raise ValueError("Token has expired")
            return payload
        except Exception as e:
            raise ValueError(f"Token decode error: {str(e)}")

    @classmethod
    def create_access_token(cls, user_id: int) -> str:
        payload = {
            "user_id": user_id,
            "type": "access",
            "exp": (datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS)).timestamp(),
            "iat": datetime.datetime.utcnow().timestamp(),
        }
        return cls.encode(payload, SECRET_KEY)

    @classmethod
    def create_refresh_token(cls, user_id: int) -> str:
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": (datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp(),
            "iat": datetime.datetime.utcnow().timestamp(),
        }
        return cls.encode(payload, SECRET_KEY)


# ============================================================
# HTTP Framework (Minimal WSGI)
# ============================================================

class Request:
    def __init__(self, environ: Dict):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/")
        self.query_string = environ.get("QUERY_STRING", "")
        self.headers = self._parse_headers(environ)
        self._body = None
        self._json = None
        self.path_params: Dict = {}

    def _parse_headers(self, environ: Dict) -> Dict:
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header_name = key.replace("_", "-").title()
                headers[header_name] = value
        return headers

    @property
    def body(self) -> bytes:
        if self._body is None:
            try:
                length = int(self.environ.get("CONTENT_LENGTH", 0) or 0)
                self._body = self.environ["wsgi.input"].read(length) if length > 0 else b""
            except Exception:
                self._body = b""
        return self._body

    @property
    def json(self) -> Optional[Dict]:
        if self._json is None:
            try:
                self._json = json.loads(self.body.decode("utf-8"))
            except Exception:
                self._json = {}
        return self._json

    @property
    def query_params(self) -> Dict:
        params = {}
        if self.query_string:
            for part in self.query_string.split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    params[key] = value
                else:
                    params[part] = ""
        return params

    def get_auth_token(self) -> Optional[str]:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None


class Response:
    def __init__(self, data: Any = None, status: int = 200, headers: Dict = None):
        self.data = data
        self.status = status
        self.headers = headers or {}

    def to_wsgi(self):
        body = json.dumps(self.data, default=str).encode("utf-8") if self.data is not None else b""
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
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        for key, value in self.headers.items():
            headers.append((key, value))
        return status_text, headers, body


def json_response(data: Any, status: int = 200) -> Response:
    return Response(data=data, status=status)


def error_response(message: str, status: int = 400) -> Response:
    return Response(data={"error": message}, status=status)


# ============================================================
# Authentication Middleware
# ============================================================

def get_current_user(request: Request) -> Optional[Dict]:
    token = request.get_auth_token()
    if not token:
        return None
    try:
        payload = JWT.decode(token, SECRET_KEY)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("user_id")
        return db.get_user_by_id(user_id)
    except Exception:
        return None


def require_auth(f):
    @wraps(f)
    def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        request.user = user
        return f(request, *args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        if not user.get("is_staff"):
            return error_response("Admin access required", 403)
        request.user = user
        return f(request, *args, **kwargs)
    return wrapper


# ============================================================
# Validators
# ============================================================

class Validator:
    @staticmethod
    def validate_email(email: str) -> bool:
        return "@" in email and "." in email.split("@")[-1]

    @staticmethod
    def validate_date(date_str: str) -> bool:
        try:
            datetime.date.fromisoformat(date_str)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_decimal(value: str) -> bool:
        try:
            decimal.Decimal(value)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_cover(cover: str) -> bool:
        return cover in ("HARD", "SOFT")

    @staticmethod
    def validate_payment_type(payment_type: str) -> bool:
        return payment_type in ("PAYMENT", "FINE")

    @staticmethod
    def validate_payment_status(status: str) -> bool:
        return status in ("PENDING", "PAID", "EXPIRED")


# ============================================================
# Business Logic
# ============================================================

class PaymentCalculator:
    @staticmethod
    def calculate_payment(borrowing: Dict) -> decimal.Decimal:
        book = db.get_book(borrowing["book_id"])
        if not book:
            return decimal.Decimal("0")
        daily_fee = decimal.Decimal(book["daily_fee"])
        borrow_date = datetime.date.fromisoformat(borrowing["borrow_date"])
        expected_return = datetime.date.fromisoformat(borrowing["expected_return_date"])
        days = (expected_return - borrow_date).days
        if days <= 0:
            days = 1
        return daily_fee * days

    @staticmethod
    def calculate_fine(borrowing: Dict) -> decimal.Decimal:
        book = db.get_book(borrowing["book_id"])
        if not book:
            return decimal.Decimal("0")
        daily_fee = decimal.Decimal(book["daily_fee"])
        expected_return = datetime.date.fromisoformat(borrowing["expected_return_date"])
        actual_return = datetime.date.today()
        if borrowing.get("actual_return_date"):
            actual_return = datetime.date.fromisoformat(borrowing["actual_return_date"])
        overdue_days = (actual_return - expected_return).days
        if overdue_days <= 0:
            return decimal.Decimal("0")
        return daily_fee * FINE_MULTIPLIER * overdue_days

    @staticmethod
    def is_overdue(borrowing: Dict) -> bool:
        expected_return = datetime.date.fromisoformat(borrowing["expected_return_date"])
        check_date = datetime.date.today()
        if borrowing.get("actual_return_date"):
            check_date = datetime.date.fromisoformat(borrowing["actual_return_date"])
        return check_date > expected_return


class StripeService:
    """Mock Stripe service for payment processing"""

    @staticmethod
    def create_checkout_session(amount: decimal.Decimal, borrowing_id: int, payment_type: str) -> Dict:
        session_id = f"cs_test_{uuid.uuid4().hex}"
        session_url = f"https://checkout.stripe.com/pay/{session_id}"
        return {
            "id": session_id,
            "url": session_url,
            "amount": int(amount * 100),
            "currency": "usd",
            "status": "open",
        }

    @staticmethod
    def retrieve_session(session_id: str) -> Dict:
        return {
            "id": session_id,
            "payment_status": "paid",
            "status": "complete",
        }


# ============================================================
# Serializers
# ============================================================

def serialize_user(user: Dict, include_password: bool = False) -> Dict:
    result = {
        "id": user["id"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "is_staff": user["is_staff"],
        "is_active": user["is_active"],
    }
    return result


def serialize_book(book: Dict) -> Dict:
    return {
        "id": book["id"],
        "title": book["title"],
        "author": book["author"],
        "cover": book["cover"],
        "inventory": book["inventory"],
        "daily_fee": book["daily_fee"],
    }


def serialize_borrowing(borrowing: Dict, include_book: bool = True) -> Dict:
    result = {
        "id": borrowing["id"],
        "user_id": borrowing["user_id"],
        "book_id": borrowing["book_id"],
        "borrow_date": borrowing["borrow_date"],
        "expected_return_date": borrowing["expected_return_date"],
        "actual_return_date": borrowing["actual_return_date"],
    }
    if include_book:
        book = db.get_book(borrowing["book_id"])
        if book:
            result["book"] = serialize_book(book)
    return result


def serialize_payment(payment: Dict, include_borrowing: bool = True) -> Dict:
    result = {
        "id": payment["id"],
        "borrowing_id": payment["borrowing_id"],
        "status": payment["status"],
        "type": payment["type"],
        "session_url": payment["session_url"],
        "session_id": payment["session_id"],
        "money_to_pay": payment["money_to_pay"],
    }
    if include_borrowing:
        borrowing = db.get_borrowing(payment["borrowing_id"])
        if borrowing:
            result["borrowing"] = serialize_borrowing(borrowing, include_book=True)
    return result


# ============================================================
# Route Handlers
# ============================================================

# --- Auth Handlers ---

def handle_register(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    data = request.json
    required = ["email", "password", "first_name", "last_name"]
    for field in required:
        if not data.get(field):
            return error_response(f"Field '{field}' is required", 400)
    if not Validator.validate_email(data["email"]):
        return error_response("Invalid email format", 400)
    if len(data["password"]) < 8:
        return error_response("Password must be at least 8 characters", 400)
    try:
        user = db.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_staff=data.get("is_staff", False),
        )
        return json_response(serialize_user(user), 201)
    except ValueError as e:
        return error_response(str(e), 409)


def handle_login(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return error_response("Email and password are required", 400)
    user = db.get_user_by_email(email)
    if not user or not db.verify_password(password, user["password"]):
        return error_response("Invalid credentials", 401)
    if not user.get("is_active"):
        return error_response("Account is inactive", 401)
    access_token = JWT.create_access_token(user["id"])
    refresh_token = JWT.create_refresh_token(user["id"])
    return json_response({
        "access": access_token,
        "refresh": refresh_token,
        "user": serialize_user(user),
    })


def handle_token_refresh(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    data = request.json
    refresh_token = data.get("refresh")
    if not refresh_token:
        return error_response("Refresh token is required", 400)
    try:
        payload = JWT.decode(refresh_token, SECRET_KEY)
        if payload.get("type") != "refresh":
            return error_response("Invalid token type", 400)
        user_id = payload.get("user_id")
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response("User not found", 404)
        access_token = JWT.create_access_token(user_id)
        return json_response({"access": access_token})
    except ValueError as e:
        return error_response(str(e), 401)


# --- User Handlers ---

@require_auth
def handle_user_me(request: Request) -> Response:
    if request.method == "GET":
        return json_response(serialize_user(request.user))
    elif request.method in ("PUT", "PATCH"):
        data = request.json
        allowed_fields = ["first_name", "last_name", "password"]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        if "password" in update_data and len(update_data["password"]) < 8:
            return error_response("Password must be at least 8 characters", 400)
        updated = db.update_user(request.user["id"], update_data)
        return json_response(serialize_user(updated))
    return error_response("Method not allowed", 405)


@require_admin
def handle_users_list(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    users = db.list_users()
    return json_response([serialize_user(u) for u in users])


@require_admin
def handle_user_detail(request: Request) -> Response:
    user_id = int(request.path_params.get("id", 0))
    user = db.get_user_by_id(user_id)
    if not user:
        return error_response("User not found", 404)
    if request.method == "GET":
        return json_response(serialize_user(user))
    elif request.method in ("PUT", "PATCH"):
        data = request.json
        allowed_fields = ["first_name", "last_name", "is_staff", "is_active"]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        updated = db.update_user(user_id, update_data)
        return json_response(serialize_user(updated))
    return error_response("Method not allowed", 405)


# --- Book Handlers ---

def handle_books_list(request: Request) -> Response:
    if request.method == "GET":
        books = db.list_books()
        # Filtering
        title = request.query_params.get("title")
        author = request.query_params.get("author")
        if title:
            books = [b for b in books if title.lower() in b["title"].lower()]
        if author:
            books = [b for b in books if author.lower() in b["author"].lower()]
        return json_response([serialize_book(b) for b in books])
    elif request.method == "POST":
        user = get_current_user(request)
        if not user or not user.get("is_staff"):
            return error_response("Admin access required", 403)
        data = request.json
        required = ["title", "author", "cover", "inventory", "daily_fee"]
        for field in required:
            if data.get(field) is None:
                return error_response(f"Field '{field}' is required", 400)
        if not Validator.validate_cover(data["cover"]):
            return error_response("Cover must be 'HARD' or 'SOFT'", 400)
        if not isinstance(data["inventory"], int) or data["inventory"] < 0:
            return error_response("Inventory must be a non-negative integer", 400)
        if not Validator.validate_decimal(str(data["daily_fee"])):
            return error_response("Invalid daily_fee format", 400)
        book = db.create_book(
            title=data["title"],
            author=data["author"],
            cover=data["cover"],
            inventory=data["inventory"],
            daily_fee=str(data["daily_fee"]),
        )
        return json_response(serialize_book(book), 201)
    return error_response("Method not allowed", 405)


def handle_book_detail(request: Request) -> Response:
    book_id = int(request.path_params.get("id", 0))
    book = db.get_book(book_id)
    if not book:
        return error_response("Book not found", 404)
    if request.method == "GET":
        return json_response(serialize_book(book))
    user = get_current_user(request)
    if not user or not user.get("is_staff"):
        return error_response("Admin access required", 403)
    if request.method in ("PUT", "PATCH"):
        data = request.json
        allowed = ["title", "author", "cover", "inventory", "daily_fee"]
        update_data = {k: v for k, v in data.items() if k in allowed}
        if "cover" in update_data and not Validator.validate_cover(update_data["cover"]):
            return error_response("Cover must be 'HARD' or 'SOFT'", 400)
        if "inventory" in update_data:
            if not isinstance(update_data["inventory"], int) or update_data["inventory"] < 0:
                return error_response("Inventory must be a non-negative integer", 400)
        if "daily_fee" in update_data:
            update_data["daily_fee"] = str(update_data["daily_fee"])
        updated = db.update_book(book_id, update_data)
        return json_response(serialize_book(updated))
    elif request.method == "DELETE":
        db.delete_book(book_id)
        return Response(status=204)
    return error_response("Method not allowed", 405)


# --- Borrowing Handlers ---

@require_auth
def handle_borrowings_list(request: Request) -> Response:
    if request.method == "GET":
        params = request.query_params
        user_id = None
        is_active = None

        # Admin can filter by user_id, regular users only see their own
        if request.user.get("is_staff"):
            if "user_id" in params:
                try:
                    user_id = int(params["user_id"])
                except ValueError:
                    return error_response("Invalid user_id", 400)
        else:
            user_id = request.user["id"]

        # Filter by is_active (actual_return_date is null)
        if "is_active" in params:
            is_active = params["is_active"].lower() in ("true", "1", "yes")

        borrowings = db.list_borrowings(user_id=user_id, is_active=is_active)
        return json_response([serialize_borrowing(b) for b in borrowings])

    elif request.method == "POST":
        data = request.json
        required = ["book_id", "expected_return_date"]
        for field in required:
            if data.get(field) is None:
                return error_response(f"Field '{field}' is required", 400)
        if not Validator.validate_date(data["expected_return_date"]):
            return error_response("Invalid expected_return_date format (use YYYY-MM-DD)", 400)
        expected_date = datetime.date.fromisoformat(data["expected_return_date"])
        if expected_date <= datetime.date.today():
            return error_response("Expected return date must be in the future", 400)
        try:
            book_id = int(data["book_id"])
        except (ValueError, TypeError):
            return error_response("Invalid book_id", 400)

        # Check for unpaid payments
        existing_borrowings = db.list_borrowings(user_id=request.user["id"])
        for b in existing_borrowings:
            payments = db.list_payments()
            for p in payments:
                if p["borrowing_id"] == b["id"] and p["status"] == "PENDING":
                    return error_response("You have pending payments. Please pay before borrowing.", 400)

        try:
            borrowing = db.create_borrowing(
                user_id=request.user["id"],
                book_id=book_id,
                expected_return_date=data["expected_return_date"],
            )
        except ValueError as e:
            return error_response(str(e), 400)

        # Create payment session
        amount = PaymentCalculator.calculate_payment(borrowing)
        stripe_session = StripeService.create_checkout_session(amount, borrowing["id"], "PAYMENT")
        db.create_payment(
            borrowing_id=borrowing["id"],
            payment_type="PAYMENT",
            money_to_pay=str(amount),
            session_url=stripe_session["url"],
            session_id=stripe_session["id"],
        )
        return json_response(serialize_borrowing(borrowing), 201)

    return error_response("Method not allowed", 405)


@require_auth
def handle_borrowing_detail(request: Request) -> Response:
    borrowing_id = int(request.path_params.get("id", 0))
    borrowing = db.get_borrowing(borrowing_id)
    if not borrowing:
        return error_response("Borrowing not found", 404)

    # Check access
    if not request.user.get("is_staff") and borrowing["user_id"] != request.user["id"]:
        return error_response("Access denied", 403)

    if request.method == "GET":
        return json_response(serialize_borrowing(borrowing))
    return error_response("Method not allowed", 405)


@require_auth
def handle_borrowing_return(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    borrowing_id = int(request.path_params.get("id", 0))
    borrowing = db.get_borrowing(borrowing_id)
    if not borrowing:
        return error_response("Borrowing not found", 404)
    if not request.user.get("is_staff") and borrowing["user_id"] != request.user["id"]:
        return error_response("Access denied", 403)
    try:
        returned = db.return_borrowing(borrowing_id)
    except ValueError as e:
        return error_response(str(e), 400)

    # Check if overdue and create fine payment
    if PaymentCalculator.is_overdue(returned):
        fine_amount = PaymentCalculator.calculate_fine(returned)
        if fine_amount > 0:
            stripe_session = StripeService.create_checkout_session(fine_amount, borrowing_id, "FINE")
            db.create_payment(
                borrowing_id=borrowing_id,
                payment_type="FINE",
                money_to_pay=str(fine_amount),
                session_url=stripe_session["url"],
                session_id=stripe_session["id"],
            )
    return json_response({
        "message": "Book returned successfully",
        "borrowing": serialize_borrowing(returned),
        "is_overdue": PaymentCalculator.is_overdue(returned),
    })


# --- Payment Handlers ---

@require_auth
def handle_payments_list(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    params = request.query_params
    if request.user.get("is_staff"):
        user_id = None
        if "user_id" in params:
            try:
                user_id = int(params["user_id"])
            except ValueError:
                return error_response("Invalid user_id", 400)
        payments = db.list_payments(user_id=user_id)
    else:
        payments = db.list_payments(user_id=request.user["id"])

    # Filter by status
    if "status" in params:
        status = params["status"].upper()
        payments = [p for p in payments if p["status"] == status]

    # Filter by type
    if "type" in params:
        ptype = params["type"].upper()
        payments = [p for p in payments if p["type"] == ptype]

    return json_response([serialize_payment(p) for p in payments])


@require_auth
def handle_payment_detail(request: Request) -> Response:
    payment_id = int(request.path_params.get("id", 0))
    payment = db.get_payment(payment_id)
    if not payment:
        return error_response("Payment not found", 404)

    # Check access
    if not request.user.get("is_staff"):
        borrowing = db.get_borrowing(payment["borrowing_id"])
        if not borrowing or borrowing["user_id"] != request.user["id"]:
            return error_response("Access denied", 403)

    if request.method == "GET":
        return json_response(serialize_payment(payment))
    return error_response("Method not allowed", 405)


def handle_payment_success(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    session_id = request.query_params.get("session_id")
    if not session_id:
        return error_response("session_id is required", 400)
    payment = db.get_payment_by_session(session_id)
    if not payment:
        return error_response("Payment not found", 404)

    # Verify with Stripe (mock)
    stripe_session = StripeService.retrieve_session(session_id)
    if stripe_session.get("payment_status") == "paid":
        updated = db.update_payment_status(payment["id"], "PAID")
        return json_response({
            "message": "Payment successful",
            "payment": serialize_payment(updated),
        })
    return error_response("Payment not completed", 400)


def handle_payment_cancel(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    session_id = request.query_params.get("session_id")
    if not session_id:
        return error_response("session_id is required", 400)
    payment = db.get_payment_by_session(session_id)
    if not payment:
        return error_response("Payment not found", 404)
    return json_response({
        "message": "Payment cancelled. You can retry within 24 hours.",
        "payment": serialize_payment(payment),
    })


# --- Admin Panel ---

def handle_admin(request: Request) -> Response:
    user = get_current_user(request)
    if not user or not user.get("is_staff"):
        return error_response("Admin access required", 403)
    stats = {
        "total_users": len(db.users),
        "total_books": len(db.books),
        "total_borrowings": len(db.borrowings),
        "active_borrowings": len([b for b in db.borrowings.values() if b["actual_return_date"] is None]),
        "total_payments": len(db.payments),
        "paid_payments": len([p for p in db.payments.values() if p["status"] == "PAID"]),
        "pending_payments": len([p for p in db.payments.values() if p["status"] == "PENDING"]),
    }
    return json_response({
        "admin_panel": "/admin/",
        "stats": stats,
        "users": [serialize_user(u) for u in db.list_users()],
        "books": [serialize_book(b) for b in db.list_books()],
        "borrowings": [serialize_borrowing(b) for b in db.list_borrowings()],
        "payments": [serialize_payment(p) for p in db.list_payments()],
    })


# --- Swagger Documentation ---

def handle_swagger(request: Request) -> Response:
    swagger_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Service API",
            "version": "1.0.0",
            "description": "API Library service for borrowing books with JWT authentication",
        },
        "servers": [{"url": "/api/v1"}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "email": {"type": "string", "format": "email"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "is_staff": {"type": "boolean"},
                        "is_active": {"type": "boolean"},
                    }
                },
                "Book": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "cover": {"type": "string", "enum": ["HARD", "SOFT"]},
                        "inventory": {"type": "integer"},
                        "daily_fee": {"type": "string"},
                    }
                },
                "Borrowing": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "book_id": {"type": "integer"},
                        "borrow_date": {"type": "string", "format": "date"},
                        "expected_return_date": {"type": "string", "format": "date"},
                        "actual_return_date": {"type": "string", "format": "date", "nullable": True},
                    }
                },
                "Payment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "borrowing_id": {"type": "integer"},
                        "status": {"type": "string", "enum": ["PENDING", "PAID", "EXPIRED"]},
                        "type": {"type": "string", "enum": ["PAYMENT", "FINE"]},
                        "session_url": {"type": "string"},
                        "session_id": {"type": "string"},
                        "money_to_pay": {"type": "string"},
                    }
                },
            }
        },
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
                                    "required": ["email", "password", "first_name", "last_name"],
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
                    "responses": {
                        "201": {"description": "User created successfully"},
                        "400": {"description": "Validation error"},
                        "409": {"description": "Email already exists"},
                    }
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
                                    "required": ["email", "password"],
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Login successful, returns access and refresh tokens"},
                        "401": {"description": "Invalid credentials"},
                    }
                }
            },
            "/auth/token/refresh/": {
                "post": {
                    "tags": ["Authentication"],
                    "summary": "Refresh access token",
                    "responses": {
                        "200": {"description": "New access token"},
                        "401": {"description": "Invalid refresh token"},
                    }
                }
            },
            "/users/me/": {
                "get": {
                    "tags": ["Users"],
                    "summary": "Get current user profile",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "User profile"},
                        "401": {"description": "Unauthorized"},
                    }
                },
                "put": {
                    "tags": ["Users"],
                    "summary": "Update current user profile",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "Updated user profile"},
                    }
                }
            },
            "/users/": {
                "get": {
                    "tags": ["Users"],
                    "summary": "List all users (admin only)",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "List of users"},
                        "403": {"description": "Admin access required"},
                    }
                }
            },
            "/books/": {
                "get": {
                    "tags": ["Books"],
                    "summary": "List all books",
                    "parameters": [
                        {"name": "title", "in": "query", "schema": {"type": "string"}},
                        {"name": "author", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {"description": "List of books"},
                    }
                },
                "post": {
                    "tags": ["Books"],
                    "summary": "Create a new book (admin only)",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "201": {"description": "Book created"},
                        "403": {"description": "Admin access required"},
                    }
                }
            },
            "/books/{id}/": {
                "get": {
                    "tags": ["Books"],
                    "summary": "Get book details",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Book details"},
                        "404": {"description": "Book not found"},
                    }
                },
                "put": {
                    "tags": ["Books"],
                    "summary": "Update book (admin only)",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "Updated book"},
                    }
                },
                "delete": {
                    "tags": ["Books"],
                    "summary": "Delete book (admin only)",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "204": {"description": "Book deleted"},
                    }
                }
            },
            "/borrowings/": {
                "get": {
                    "tags": ["Borrowings"],
                    "summary": "List borrowings",
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {"name": "is_active", "in": "query", "schema": {"type": "boolean"}, "description": "Filter by active (not returned) borrowings"},
                        {"name": "user_id", "in": "query", "schema": {"type": "integer"}, "description": "Filter by user (admin only)"},
                    ],
                    "responses": {
                        "200": {"description": "List of borrowings"},
                    }
                },
                "post": {
                    "tags": ["Borrowings"],
                    "summary": "Create a new borrowing",
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["book_id", "expected_return_date"],
                                    "properties": {
                                        "book_id": {"type": "integer"},
                                        "expected_return_date": {"type": "string", "format": "date"},
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Borrowing created"},
                        "400": {"description": "Book not available or pending payments"},
                    }
                }
            },
            "/borrowings/{id}/": {
                "get": {
                    "tags": ["Borrowings"],
                    "summary": "Get borrowing details",
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Borrowing details"},
                        "404": {"description": "Borrowing not found"},
                    }
                }
            },
            "/borrowings/{id}/return/": {
                "post": {
                    "tags": ["Borrowings"],
                    "summary": "Return a borrowed book",
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Book returned, fine created if overdue"},
                        "400": {"description": "Already returned"},
                    }
                }
            },
            "/payments/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "List payments",
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["PENDING", "PAID", "EXPIRED"]}},
                        {"name": "type", "in": "query", "schema": {"type": "string", "enum": ["PAYMENT", "FINE"]}},
                        {"name": "user_id", "in": "query", "schema": {"type": "integer"}, "description": "Filter by user (admin only)"},
                    ],
                    "responses": {
                        "200": {"description": "List of payments"},
                    }
                }
            },
            "/payments/{id}/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Get payment details",
                    "security": [{"BearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {
                        "200": {"description": "Payment details"},
                        "404": {"description": "Payment not found"},
                    }
                }
            },
            "/payments/success/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Handle successful payment from Stripe",
                    "parameters": [
                        {"name": "session_id", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {"description": "Payment confirmed"},
                        "400": {"description": "Payment not completed"},
                    }
                }
            },
            "/payments/cancel/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Handle cancelled payment from Stripe",
                    "parameters": [
                        {"name": "session_id", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {"description": "Payment cancellation acknowledged"},
                    }
                }
            },
        }
    }
    return json_response(swagger_doc)


# ============================================================
# Router
# ============================================================

class Router:
    def __init__(self):
        self.routes: List[Dict] = []

    def add_route(self, path: str, handler, methods: List[str] = None):
        self.routes.append({
            "path": path,
            "handler": handler,
            "methods": methods or ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "pattern": self._compile_pattern(path),
        })

    def _compile_pattern(self, path: str):
        import re
        pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path)
        return re.compile(f"^{pattern}/?$")

    def match(self, path: str) -> Optional[Dict]:
        for route in self.routes:
            match = route["pattern"].match(path)
            if match:
                return route, match.groupdict()
        return None, {}

    def dispatch(self, request: Request) -> Response:
        result = self.match(request.path)
        if result[0] is None:
            return error_response("Not found", 404)
        route, path_params = result
        request.path_params = {k: int(v) if v.isdigit() else v for k, v in path_params.items()}
        try:
            return route["handler"](request)
        except Exception as e:
            return error_response(f"Internal server error: {str(e)}", 500)


router = Router()

# Auth routes
router.add_route("/api/v1/auth/register/", handle_register, ["POST"])
router.add_route("/api/v1/auth/login/", handle_login, ["POST"])
router.add_route("/api/v1/auth/token/refresh/", handle_token_refresh, ["POST"])

# User routes
router.add_route("/api/v1/users/me/", handle_user_me, ["GET", "PUT", "PATCH"])
router.add_route("/api/v1/users/", handle_users_list, ["GET"])
router.add_route("/api/v1/users/{id}/", handle_user_detail, ["GET", "PUT", "PATCH"])

# Book routes
router.add_route("/api/v1/books/", handle_books_list, ["GET", "POST"])
router.add_route("/api/v1/books/{id}/", handle_book_detail, ["GET", "PUT", "PATCH", "DELETE"])

# Borrowing routes
router.add_route("/api/v1/borrowings/", handle_borrowings_list, ["GET", "POST"])
router.add_route("/api/v1/borrowings/{id}/", handle_borrowing_detail, ["GET"])
router.add_route("/api/v1/borrowings/{id}/return/", handle_borrowing_return, ["POST"])

# Payment routes
router.add_route("/api/v1/payments/", handle_payments_list, ["GET"])
router.add_route("/api/v1/payments/success/", handle_payment_success, ["GET"])
router.add_route("/api/v1/payments/cancel/", handle_payment_cancel, ["GET"])
router.add_route("/api/v1/payments/{id}/", handle_payment_detail, ["GET"])

# Admin and docs
router.add_route("/admin/", handle_admin, ["GET"])
router.add_route("/api/v1/doc/swagger/", handle_swagger, ["GET"])


# ============================================================
# WSGI Application
# ============================================================

def application(environ: Dict, start_response):
    request = Request(environ)
    response = router.dispatch(request)
    status, headers, body = response.to_wsgi()
    start_response(status, headers)
    return [body]


# ============================================================
# CLI / Test Runner
# ============================================================

class TestClient:
    """Simple test client for the WSGI application"""

    def __init__(self, app):
        self.app = app
        self.token = None

    def _make_environ(self, method: str, path: str, data: Dict = None, token: str = None, query: str = "") -> Dict:
        body = json.dumps(data).encode("utf-8") if data else b""
        environ = {
            "REQUEST_METHOD": method.upper(),
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": __import__("io").BytesIO(body),
            "wsgi.errors": sys.stderr,
        }
        if token:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return environ

    def request(self, method: str, path: str, data: Dict = None, token: str = None, query: str = "") -> Dict:
        environ = self._make_environ(method, path, data, token, query)
        responses = []

        def start_response(status, headers):
            responses.append({"status": status, "headers": headers})

        body_parts = self.app(environ, start_response)
        body = b"".join(body_parts)
        status_code = int(responses[0]["status"].split(" ")[0])
        try:
            response_data = json.loads(body.decode("utf-8"))
        except Exception:
            response_data = {}
        return {"status": status_code, "data": response_data}


def run_tests():
    """Run integration tests"""
    client = TestClient(application)
    print("=" * 60)
    print("Library Service API - Integration Tests")
    print("=" * 60)

    # Test 1: Register user
    print("\n1. Register new user")
    resp = client.request("POST", "/api/v1/auth/register/", {
        "email": "user@test.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
    })
    assert resp["status"] == 201, f"Expected 201, got {resp['status']}: {resp['data']}"
    print(f"   ✓ User registered: {resp['data']['email']}")

    # Test 2: Login
    print("\n2. Login")
    resp = client.request("POST", "/api/v1/auth/login/", {
        "email": "user@test.com",
        "password": "password123",
    })
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    user_token = resp["data"]["access"]
    refresh_token = resp["data"]["refresh"]
    print(f"   ✓ Login successful, token received")

    # Test 3: Admin login
    print("\n3. Admin login")
    resp = client.request("POST", "/api/v1/auth/login/", {
        "email": "admin@library.com",
        "password": "admin123",
    })
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    admin_token = resp["data"]["access"]
    print(f"   ✓ Admin login successful")

    # Test 4: Token refresh
    print("\n4. Token refresh")
    resp = client.request("POST", "/api/v1/auth/token/refresh/", {"refresh": refresh_token})
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Token refreshed")

    # Test 5: Get user profile
    print("\n5. Get user profile")
    resp = client.request("GET", "/api/v1/users/me/", token=user_token)
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Profile: {resp['data']['email']}")

    # Test 6: Create book (admin)
    print("\n6. Create book (admin)")
    resp = client.request("POST", "/api/v1/books/", {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "cover": "HARD",
        "inventory": 5,
        "daily_fee": "1.50",
    }, token=admin_token)
    assert resp["status"] == 201, f"Expected 201, got {resp['status']}: {resp['data']}"
    book_id = resp["data"]["id"]
    print(f"   ✓ Book created: {resp['data']['title']} (ID: {book_id})")

    # Test 7: Create another book
    print("\n7. Create second book")
    resp = client.request("POST", "/api/v1/books/", {
        "title": "1984",
        "author": "George Orwell",
        "cover": "SOFT",
        "inventory": 3,
        "daily_fee": "2.00",
    }, token=admin_token)
    assert resp["status"] == 201, f"Expected 201, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Book created: {resp['data']['title']}")

    # Test 8: List books
    print("\n8. List books")
    resp = client.request("GET", "/api/v1/books/")
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Found {len(resp['data'])} books")

    # Test 9: Filter books by title
    print("\n9. Filter books by title")
    resp = client.request("GET", "/api/v1/books/", query="title=gatsby")
    assert resp["status"] == 200
    print(f"   ✓ Filtered books: {len(resp['data'])} found")

    # Test 10: Get book detail
    print("\n10. Get book detail")
    resp = client.request("GET", f"/api/v1/books/{book_id}/")
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Book: {resp['data']['title']}, inventory: {resp['data']['inventory']}")

    # Test 11: Create borrowing
    print("\n11. Create borrowing")
    future_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    resp = client.request("POST", "/api/v1/borrowings/", {
        "book_id": book_id,
        "expected_return_date": future_date,
    }, token=user_token)
    assert resp["status"] == 201, f"Expected 201, got {resp['status']}: {resp['data']}"
    borrowing_id = resp["data"]["id"]
    print(f"   ✓ Borrowing created (ID: {borrowing_id}), expected return: {future_date}")

    # Test 12: Check book inventory decreased
    print("\n12. Check book inventory decreased")
    resp = client.request("GET", f"/api/v1/books/{book_id}/")
    assert resp["status"] == 200
    assert resp["data"]["inventory"] == 4, f"Expected 4, got {resp['data']['inventory']}"
    print(f"   ✓ Inventory decreased to {resp['data']['inventory']}")

    # Test 13: List borrowings
    print("\n13. List borrowings")
    resp = client.request("GET", "/api/v1/borrowings/", token=user_token)
    assert resp["status"] == 200
    print(f"   ✓ Found {len(resp['data'])} borrowings")

    # Test 14: Filter active borrowings
    print("\n14. Filter active borrowings")
    resp = client.request("GET", "/api/v1/borrowings/", token=user_token, query="is_active=true")
    assert resp["status"] == 200
    print(f"   ✓ Active borrowings: {len(resp['data'])}")

    # Test 15: List payments
    print("\n15. List payments")
    resp = client.request("GET", "/api/v1/payments/", token=user_token)
    assert resp["status"] == 200
    assert len(resp["data"]) > 0, "Expected at least one payment"
    payment_id = resp["data"][0]["id"]
    session_id = resp["data"][0]["session_id"]
    print(f"   ✓ Found {len(resp['data'])} payment(s), status: {resp['data'][0]['status']}")

    # Test 16: Payment success
    print("\n16. Payment success")
    resp = client.request("GET", "/api/v1/payments/success/", query=f"session_id={session_id}")
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Payment status: {resp['data']['payment']['status']}")

    # Test 17: Return book
    print("\n17. Return book")
    resp = client.request("POST", f"/api/v1/borrowings/{borrowing_id}/return/", token=user_token)
    assert resp["status"] == 200, f"Expected 200, got {resp['status']}: {resp['data']}"
    print(f"   ✓ Book returned, overdue: {resp['data']['is_overdue']}")

    # Test 18: Check inventory restored
    print("\n18. Check inventory restored")
    resp = client.request("GET", f"/api/v1/books/{book_id}/")
    assert resp["data"]["inventory"] == 5
    print(f"   ✓ Inventory restored to {resp['data']['inventory']}")

    # Test 19: Create overdue borrowing (simulate)
    print("\n19. Test overdue borrowing")
    past_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    resp = client.request("POST", "/api/v1/borrowings/", {
        "book_id": book_id,
        "expected_return_date": past_date,
    }, token=user_token)
    assert resp["status"] == 201
    overdue_borrowing_id = resp["data"]["id"]
    # Manually set expected return to past
    borrowing = db.borrowings[overdue_borrowing_id]
    borrowing["expected_return_date"] = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    # Return it (should create fine)
    resp = client.request("POST", f"/api/v1/borrowings/{overdue_borrowing_id}/return/", token=user_token)
    assert resp["status"] == 200
    print(f"   ✓ Overdue return, is_overdue: {resp['data']['is_overdue']}")

    # Test 20: Check fine payment created
    print("\n20. Check fine payment")
    resp = client.request("GET", "/api/v1/payments/", token=user_token, query="type=FINE")
    print(f"   ✓ Fine payments: {len(resp['data'])}")

    # Test 21: Admin list all users
    print("\n21. Admin list users")
    resp = client.request("GET", "/api/v1/users/", token=admin_token)
    assert resp["status"] == 200
    print(f"   ✓ Total users: {len(resp['data'])}")

    # Test 22: Admin panel
    print("\n22. Admin panel")
    resp = client.request("GET", "/admin/", token=admin_token)
    assert resp["status"] == 200
    print(f"   ✓ Admin stats: {resp['data']['stats']}")

    # Test 23: Swagger docs
    print("\n23. Swagger documentation")
    resp = client.request("GET", "/api/v1/doc/swagger/")
    assert resp["status"] == 200
    assert "paths" in resp["data"]
    print(f"   ✓ Swagger docs with {len(resp['data']['paths'])} endpoints")

    # Test 24: Payment cancel
    print("\n24. Payment cancel")
    payments = db.list_payments()
    pending = [p for p in payments if p["status"] == "PENDING"]
    if pending:
        resp = client.request("GET", "/api/v1/payments/cancel/", query=f"session_id={pending[0]['session_id']}")
        assert resp["status"] == 200
        print(f"   ✓ Payment cancel acknowledged")
    else:
        print("   - No pending payments to cancel")

    # Test 25: Unauthorized access
    print("\n25. Unauthorized access")
    resp = client.request("GET", "/api/v1/users/me/")
    assert resp["status"] == 401
    print(f"   ✓ Unauthorized access rejected")

    # Test 26: Non-admin book creation rejected
    print("\n26. Non-admin book creation rejected")
    resp = client.request("POST", "/api/v1/books/", {
        "title": "Test",
        "author": "Test",
        "cover": "HARD",
        "inventory": 1,
        "daily_fee": "1.00",
    }, token=user_token)
    assert resp["status"] == 403
    print(f"   ✓ Non-admin book creation rejected")

    # Test 27: Book not found
    print("\n27. Book not found")
    resp = client.request("GET", "/api/v1/books/9999/")
    assert resp["status"] == 404
    print(f"   ✓ 404 for non-existent book")

    # Test 28: Update book
    print("\n28. Update book")
    resp = client.request("PATCH", f"/api/v1/books/{book_id}/", {
        "inventory": 10,
    }, token=admin_token)
    assert resp["status"] == 200
    assert resp["data"]["inventory"] == 10
    print(f"   ✓ Book inventory updated to {resp['data']['inventory']}")

    # Test 29: Delete book
    print("\n29. Delete book")
    resp = client.request("POST", "/api/v1/books/", {
        "title": "To Delete",
        "author": "Author",
        "cover": "SOFT",
        "inventory": 1,
        "daily_fee": "0.50",
    }, token=admin_token)
    delete_id = resp["data"]["id"]
    resp = client.request("DELETE", f"/api/v1/books/{delete_id}/", token=admin_token)
    assert resp["status"] == 204
    print(f"   ✓ Book deleted")

    # Test 30: Filter borrowings by user (admin)
    print("\n30. Filter borrowings by user (admin)")
    resp = client.request("GET", "/api/v1/borrowings/", token=admin_token, query="user_id=2")
    assert resp["status"] == 200
    print(f"   ✓ Borrowings for user 2: {len(resp['data'])}")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the WSGI server"""
    from wsgiref.simple_server import make_server
    print(f"Starting Library Service API on http://{host}:{port}")
    print(f"Admin panel: http://{host}:{port}/admin/")
    print(f"API docs: http://{host}:{port}/api/v1/doc/swagger/")
    print(f"Default admin: admin@library.com / admin123")
    httpd = make_server(host, port, application)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        run_server(port=port)
    else:
        print("Library Service API")
        print("Usage:")
        print("  python solution.py test    - Run integration tests")
        print("  python solution.py server  - Start HTTP server")
        print("  python solution.py server 8080  - Start on custom port")
        print()
        print("Running tests by default...")
        run_tests()