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
# Database (In-Memory)
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
            "created_at": datetime.datetime.utcnow().isoformat(),
        }

    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return base64.b64encode(salt + key).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            decoded = base64.b64decode(hashed.encode())
            salt = decoded[:16]
            stored_key = decoded[16:]
            key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
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

    def create_user(self, email: str, password: str, first_name: str, last_name: str, is_staff: bool = False) -> Dict:
        if self.get_user_by_email(email):
            raise ValueError("User with this email already exists")
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "password": self._hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": is_staff,
            "is_active": True,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.users[user_id] = user
        return user

    def get_book_by_id(self, book_id: str) -> Optional[Dict]:
        return self.books.get(book_id)

    def create_book(self, title: str, author: str, cover: str, inventory: int, daily_fee: str) -> Dict:
        book_id = str(uuid.uuid4())
        book = {
            "id": book_id,
            "title": title,
            "author": author,
            "cover": cover,
            "inventory": inventory,
            "daily_fee": daily_fee,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.books[book_id] = book
        return book

    def update_book(self, book_id: str, data: Dict) -> Optional[Dict]:
        book = self.books.get(book_id)
        if not book:
            return None
        book.update(data)
        return book

    def delete_book(self, book_id: str) -> bool:
        if book_id in self.books:
            del self.books[book_id]
            return True
        return False

    def list_books(self) -> List[Dict]:
        return list(self.books.values())

    def get_borrowing_by_id(self, borrowing_id: str) -> Optional[Dict]:
        return self.borrowings.get(borrowing_id)

    def create_borrowing(self, user_id: str, book_id: str, expected_return_date: str) -> Dict:
        borrowing_id = str(uuid.uuid4())
        borrowing = {
            "id": borrowing_id,
            "user_id": user_id,
            "book_id": book_id,
            "borrow_date": datetime.date.today().isoformat(),
            "expected_return_date": expected_return_date,
            "actual_return_date": None,
            "status": "ACTIVE",
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.borrowings[borrowing_id] = borrowing
        return borrowing

    def list_borrowings(self, user_id: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict]:
        result = list(self.borrowings.values())
        if user_id:
            result = [b for b in result if b["user_id"] == user_id]
        if is_active is not None:
            if is_active:
                result = [b for b in result if b["actual_return_date"] is None]
            else:
                result = [b for b in result if b["actual_return_date"] is not None]
        return result

    def return_borrowing(self, borrowing_id: str) -> Optional[Dict]:
        borrowing = self.borrowings.get(borrowing_id)
        if not borrowing:
            return None
        borrowing["actual_return_date"] = datetime.date.today().isoformat()
        borrowing["status"] = "RETURNED"
        return borrowing

    def get_payment_by_id(self, payment_id: str) -> Optional[Dict]:
        return self.payments.get(payment_id)

    def create_payment(self, borrowing_id: str, payment_type: str, money_to_pay: str, session_url: str, session_id: str) -> Dict:
        payment_id = str(uuid.uuid4())
        payment = {
            "id": payment_id,
            "borrowing_id": borrowing_id,
            "status": "PENDING",
            "type": payment_type,
            "session_url": session_url,
            "session_id": session_id,
            "money_to_pay": money_to_pay,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self.payments[payment_id] = payment
        return payment

    def update_payment_status(self, payment_id: str, status: str) -> Optional[Dict]:
        payment = self.payments.get(payment_id)
        if not payment:
            return None
        payment["status"] = status
        return payment

    def list_payments(self, borrowing_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
        result = list(self.payments.values())
        if borrowing_id:
            result = [p for p in result if p["borrowing_id"] == borrowing_id]
        if user_id:
            borrowing_ids = {b["id"] for b in self.borrowings.values() if b["user_id"] == user_id}
            result = [p for p in result if p["borrowing_id"] in borrowing_ids]
        return result

    def get_payments_for_borrowing(self, borrowing_id: str) -> List[Dict]:
        return [p for p in self.payments.values() if p["borrowing_id"] == borrowing_id]


db = Database()

# ============================================================
# JWT Implementation
# ============================================================

class JWT:
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    @classmethod
    def encode(cls, payload: Dict) -> str:
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        header_encoded = cls._base64url_encode(json.dumps(header).encode())
        payload_encoded = cls._base64url_encode(json.dumps(payload).encode())
        signing_input = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        signature_encoded = cls._base64url_encode(signature)
        return f"{signing_input}.{signature_encoded}"

    @classmethod
    def decode(cls, token: str) -> Dict:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            header_encoded, payload_encoded, signature_encoded = parts
            signing_input = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                SECRET_KEY.encode(),
                signing_input.encode(),
                hashlib.sha256
            ).digest()
            actual_signature = cls._base64url_decode(signature_encoded)
            if not hmac.compare_digest(expected_signature, actual_signature):
                raise ValueError("Invalid token signature")
            payload = json.loads(cls._base64url_decode(payload_encoded))
            if "exp" in payload:
                if datetime.datetime.utcnow().timestamp() > payload["exp"]:
                    raise ValueError("Token has expired")
            return payload
        except Exception as e:
            raise ValueError(f"Token decode error: {str(e)}")


def create_tokens(user_id: str) -> Dict[str, str]:
    now = datetime.datetime.utcnow()
    access_payload = {
        "user_id": user_id,
        "type": "access",
        "exp": (now + datetime.timedelta(hours=JWT_EXPIRY_HOURS)).timestamp(),
        "iat": now.timestamp(),
    }
    refresh_payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": (now + datetime.timedelta(days=7)).timestamp(),
        "iat": now.timestamp(),
    }
    return {
        "access": JWT.encode(access_payload),
        "refresh": JWT.encode(refresh_payload),
    }


# ============================================================
# HTTP Framework (Minimal WSGI)
# ============================================================

class Request:
    def __init__(self, environ: Dict):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/")
        self.query_string = environ.get("QUERY_STRING", "")
        self._body = None
        self._json = None
        self._headers = {}
        self._parse_headers()
        self._parse_query_params()

    def _parse_headers(self):
        for key, value in self.environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                self._headers[header_name] = value
            elif key == "CONTENT_TYPE":
                self._headers["Content-Type"] = value
            elif key == "CONTENT_LENGTH":
                self._headers["Content-Length"] = value

    def _parse_query_params(self):
        self.query_params = {}
        if self.query_string:
            for part in self.query_string.split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    self.query_params[key] = value
                elif part:
                    self.query_params[part] = ""

    def get_header(self, name: str) -> Optional[str]:
        return self._headers.get(name)

    def get_body(self) -> bytes:
        if self._body is None:
            try:
                length = int(self.environ.get("CONTENT_LENGTH", 0) or 0)
                self._body = self.environ["wsgi.input"].read(length) if length > 0 else b""
            except Exception:
                self._body = b""
        return self._body

    def get_json(self) -> Optional[Dict]:
        if self._json is None:
            try:
                body = self.get_body()
                if body:
                    self._json = json.loads(body.decode("utf-8"))
            except Exception:
                self._json = {}
        return self._json or {}


class Response:
    def __init__(self, data: Any = None, status: int = 200, headers: Optional[Dict] = None):
        self.status = status
        self.headers = headers or {}
        self.data = data

    def to_wsgi(self, start_response):
        status_map = {
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
        }
        status_str = status_map.get(self.status, f"{self.status} Unknown")
        response_headers = [("Content-Type", "application/json")]
        for key, value in self.headers.items():
            response_headers.append((key, value))
        if self.status == 204:
            start_response(status_str, response_headers)
            return [b""]
        body = json.dumps(self.data, default=str).encode("utf-8")
        response_headers.append(("Content-Length", str(len(body))))
        start_response(status_str, response_headers)
        return [body]


def json_response(data: Any, status: int = 200) -> Response:
    return Response(data=data, status=status)


def error_response(message: str, status: int = 400) -> Response:
    return Response(data={"error": message}, status=status)


# ============================================================
# Authentication Middleware
# ============================================================

def get_current_user(request: Request) -> Optional[Dict]:
    auth_header = request.get_header("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = JWT.decode(token)
        if payload.get("type") != "access":
            return None
        user = db.get_user_by_id(payload["user_id"])
        return user
    except Exception:
        return None


def require_auth(f):
    @wraps(f)
    def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication credentials were not provided.", 401)
        request.user = user
        return f(request, *args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication credentials were not provided.", 401)
        if not user.get("is_staff"):
            return error_response("You do not have permission to perform this action.", 403)
        request.user = user
        return f(request, *args, **kwargs)
    return wrapper


# ============================================================
# Serializers / Validators
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


def serialize_borrowing(borrowing: Dict, include_book: bool = True, include_user: bool = False) -> Dict:
    result = {
        "id": borrowing["id"],
        "borrow_date": borrowing["borrow_date"],
        "expected_return_date": borrowing["expected_return_date"],
        "actual_return_date": borrowing["actual_return_date"],
        "status": borrowing["status"],
        "user_id": borrowing["user_id"],
        "book_id": borrowing["book_id"],
    }
    if include_book:
        book = db.get_book_by_id(borrowing["book_id"])
        if book:
            result["book"] = serialize_book(book)
    if include_user:
        user = db.get_user_by_id(borrowing["user_id"])
        if user:
            result["user"] = serialize_user(user)
    return result


def serialize_payment(payment: Dict) -> Dict:
    return {
        "id": payment["id"],
        "borrowing_id": payment["borrowing_id"],
        "status": payment["status"],
        "type": payment["type"],
        "session_url": payment["session_url"],
        "session_id": payment["session_id"],
        "money_to_pay": payment["money_to_pay"],
    }


def validate_book_data(data: Dict, partial: bool = False) -> tuple:
    errors = {}
    cover_choices = ["HARD", "SOFT"]

    if not partial or "title" in data:
        if not data.get("title"):
            errors["title"] = "This field is required."
        elif len(data["title"]) > 255:
            errors["title"] = "Title must be 255 characters or less."

    if not partial or "author" in data:
        if not data.get("author"):
            errors["author"] = "This field is required."
        elif len(data["author"]) > 255:
            errors["author"] = "Author must be 255 characters or less."

    if not partial or "cover" in data:
        if not data.get("cover"):
            errors["cover"] = "This field is required."
        elif data["cover"] not in cover_choices:
            errors["cover"] = f"Cover must be one of: {', '.join(cover_choices)}."

    if not partial or "inventory" in data:
        if "inventory" not in data or data["inventory"] is None:
            if not partial:
                errors["inventory"] = "This field is required."
        else:
            try:
                inv = int(data["inventory"])
                if inv < 0:
                    errors["inventory"] = "Inventory must be a non-negative integer."
            except (ValueError, TypeError):
                errors["inventory"] = "Inventory must be an integer."

    if not partial or "daily_fee" in data:
        if not data.get("daily_fee"):
            if not partial:
                errors["daily_fee"] = "This field is required."
        else:
            try:
                fee = Decimal(str(data["daily_fee"]))
                if fee <= 0:
                    errors["daily_fee"] = "Daily fee must be a positive number."
            except Exception:
                errors["daily_fee"] = "Daily fee must be a valid decimal number."

    return len(errors) == 0, errors


def validate_borrowing_data(data: Dict) -> tuple:
    errors = {}

    if not data.get("book_id"):
        errors["book_id"] = "This field is required."

    if not data.get("expected_return_date"):
        errors["expected_return_date"] = "This field is required."
    else:
        try:
            expected = datetime.date.fromisoformat(data["expected_return_date"])
            if expected <= datetime.date.today():
                errors["expected_return_date"] = "Expected return date must be in the future."
        except ValueError:
            errors["expected_return_date"] = "Invalid date format. Use YYYY-MM-DD."

    return len(errors) == 0, errors


# ============================================================
# Business Logic
# ============================================================

def calculate_borrowing_fee(borrowing: Dict) -> Decimal:
    book = db.get_book_by_id(borrowing["book_id"])
    if not book:
        return Decimal("0")

    daily_fee = Decimal(str(book["daily_fee"]))
    borrow_date = datetime.date.fromisoformat(borrowing["borrow_date"])
    expected_return = datetime.date.fromisoformat(borrowing["expected_return_date"])

    days = (expected_return - borrow_date).days
    if days <= 0:
        days = 1

    return daily_fee * days


def calculate_fine(borrowing: Dict) -> Decimal:
    book = db.get_book_by_id(borrowing["book_id"])
    if not book:
        return Decimal("0")

    daily_fee = Decimal(str(book["daily_fee"]))
    expected_return = datetime.date.fromisoformat(borrowing["expected_return_date"])
    actual_return = datetime.date.today()

    if actual_return <= expected_return:
        return Decimal("0")

    overdue_days = (actual_return - expected_return).days
    return daily_fee * FINE_MULTIPLIER * overdue_days


def create_payment_session(borrowing_id: str, amount: Decimal, payment_type: str) -> Dict:
    session_id = str(uuid.uuid4())
    session_url = f"http://localhost:8000/api/v1/payments/session/{session_id}/"
    payment = db.create_payment(
        borrowing_id=borrowing_id,
        payment_type=payment_type,
        money_to_pay=str(amount),
        session_url=session_url,
        session_id=session_id,
    )
    return payment


# ============================================================
# Route Handlers
# ============================================================

# --- Auth Handlers ---

def handle_register(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)

    data = request.get_json()
    errors = {}

    if not data.get("email"):
        errors["email"] = "This field is required."
    if not data.get("password"):
        errors["password"] = "This field is required."
    elif len(data["password"]) < 8:
        errors["password"] = "Password must be at least 8 characters."
    if not data.get("first_name"):
        errors["first_name"] = "This field is required."
    if not data.get("last_name"):
        errors["last_name"] = "This field is required."

    if errors:
        return json_response(errors, 400)

    try:
        user = db.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        return json_response(serialize_user(user), 201)
    except ValueError as e:
        return error_response(str(e), 409)


def handle_token_obtain(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return json_response({"error": "Email and password are required."}, 400)

    user = db.get_user_by_email(email)
    if not user or not db.verify_password(password, user["password"]):
        return json_response({"error": "Invalid credentials."}, 401)

    if not user.get("is_active"):
        return json_response({"error": "User account is disabled."}, 401)

    tokens = create_tokens(user["id"])
    return json_response(tokens, 200)


def handle_token_refresh(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)

    data = request.get_json()
    refresh_token = data.get("refresh")

    if not refresh_token:
        return json_response({"error": "Refresh token is required."}, 400)

    try:
        payload = JWT.decode(refresh_token)
        if payload.get("type") != "refresh":
            return json_response({"error": "Invalid token type."}, 401)

        user = db.get_user_by_id(payload["user_id"])
        if not user:
            return json_response({"error": "User not found."}, 401)

        tokens = create_tokens(user["id"])
        return json_response({"access": tokens["access"]}, 200)
    except ValueError as e:
        return json_response({"error": str(e)}, 401)


@require_auth
def handle_user_me(request: Request) -> Response:
    if request.method == "GET":
        return json_response(serialize_user(request.user), 200)
    elif request.method in ("PUT", "PATCH"):
        data = request.get_json()
        user = request.user
        partial = request.method == "PATCH"

        if "first_name" in data:
            user["first_name"] = data["first_name"]
        if "last_name" in data:
            user["last_name"] = data["last_name"]
        if "password" in data:
            if len(data["password"]) < 8:
                return json_response({"password": "Password must be at least 8 characters."}, 400)
            user["password"] = db._hash_password(data["password"])

        return json_response(serialize_user(user), 200)
    else:
        return error_response("Method not allowed.", 405)


# --- Book Handlers ---

def handle_books_list(request: Request) -> Response:
    if request.method == "GET":
        books = db.list_books()
        # Filtering
        title = request.query_params.get("title")
        author = request.query_params.get("author")
        cover = request.query_params.get("cover")

        if title:
            books = [b for b in books if title.lower() in b["title"].lower()]
        if author:
            books = [b for b in books if author.lower() in b["author"].lower()]
        if cover:
            books = [b for b in books if b["cover"] == cover.upper()]

        return json_response([serialize_book(b) for b in books], 200)

    elif request.method == "POST":
        user = get_current_user(request)
        if not user:
            return error_response("Authentication credentials were not provided.", 401)
        if not user.get("is_staff"):
            return error_response("You do not have permission to perform this action.", 403)

        data = request.get_json()
        valid, errors = validate_book_data(data)
        if not valid:
            return json_response(errors, 400)

        book = db.create_book(
            title=data["title"],
            author=data["author"],
            cover=data["cover"],
            inventory=int(data["inventory"]),
            daily_fee=str(Decimal(str(data["daily_fee"]))),
        )
        return json_response(serialize_book(book), 201)
    else:
        return error_response("Method not allowed.", 405)


def handle_book_detail(request: Request, book_id: str) -> Response:
    book = db.get_book_by_id(book_id)
    if not book:
        return error_response("Book not found.", 404)

    if request.method == "GET":
        return json_response(serialize_book(book), 200)

    elif request.method in ("PUT", "PATCH"):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication credentials were not provided.", 401)
        if not user.get("is_staff"):
            return error_response("You do not have permission to perform this action.", 403)

        data = request.get_json()
        partial = request.method == "PATCH"
        valid, errors = validate_book_data(data, partial=partial)
        if not valid:
            return json_response(errors, 400)

        update_data = {}
        if "title" in data:
            update_data["title"] = data["title"]
        if "author" in data:
            update_data["author"] = data["author"]
        if "cover" in data:
            update_data["cover"] = data["cover"]
        if "inventory" in data:
            update_data["inventory"] = int(data["inventory"])
        if "daily_fee" in data:
            update_data["daily_fee"] = str(Decimal(str(data["daily_fee"])))

        updated = db.update_book(book_id, update_data)
        return json_response(serialize_book(updated), 200)

    elif request.method == "DELETE":
        user = get_current_user(request)
        if not user:
            return error_response("Authentication credentials were not provided.", 401)
        if not user.get("is_staff"):
            return error_response("You do not have permission to perform this action.", 403)

        db.delete_book(book_id)
        return Response(status=204)
    else:
        return error_response("Method not allowed.", 405)


# --- Borrowing Handlers ---

@require_auth
def handle_borrowings_list(request: Request) -> Response:
    if request.method == "GET":
        user = request.user
        is_staff = user.get("is_staff", False)

        # Filtering params
        is_active_param = request.query_params.get("is_active")
        user_id_param = request.query_params.get("user_id")

        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")

        if is_staff:
            filter_user_id = user_id_param if user_id_param else None
        else:
            filter_user_id = user["id"]

        borrowings = db.list_borrowings(user_id=filter_user_id, is_active=is_active)

        # Additional filter: actual_return_date
        actual_return_date = request.query_params.get("actual_return_date")
        if actual_return_date:
            if actual_return_date.lower() == "null" or actual_return_date == "":
                borrowings = [b for b in borrowings if b["actual_return_date"] is None]
            else:
                borrowings = [b for b in borrowings if b["actual_return_date"] == actual_return_date]

        return json_response([serialize_borrowing(b) for b in borrowings], 200)

    elif request.method == "POST":
        data = request.get_json()
        valid, errors = validate_borrowing_data(data)
        if not valid:
            return json_response(errors, 400)

        book = db.get_book_by_id(data["book_id"])
        if not book:
            return error_response("Book not found.", 404)

        if book["inventory"] <= 0:
            return error_response("Book is not available (inventory is 0).", 400)

        # Check for pending payments
        user_borrowings = db.list_borrowings(user_id=request.user["id"], is_active=True)
        for b in user_borrowings:
            payments = db.get_payments_for_borrowing(b["id"])
            pending = [p for p in payments if p["status"] == "PENDING"]
            if pending:
                return error_response("You have pending payments. Please complete them before borrowing.", 400)

        # Decrease inventory
        book["inventory"] -= 1

        borrowing = db.create_borrowing(
            user_id=request.user["id"],
            book_id=data["book_id"],
            expected_return_date=data["expected_return_date"],
        )

        # Create payment session
        fee = calculate_borrowing_fee(borrowing)
        payment = create_payment_session(borrowing["id"], fee, "PAYMENT")

        result = serialize_borrowing(borrowing)
        result["payment"] = serialize_payment(payment)

        return json_response(result, 201)
    else:
        return error_response("Method not allowed.", 405)


@require_auth
def handle_borrowing_detail(request: Request, borrowing_id: str) -> Response:
    borrowing = db.get_borrowing_by_id(borrowing_id)
    if not borrowing:
        return error_response("Borrowing not found.", 404)

    user = request.user
    if not user.get("is_staff") and borrowing["user_id"] != user["id"]:
        return error_response("You do not have permission to view this borrowing.", 403)

    if request.method == "GET":
        return json_response(serialize_borrowing(borrowing, include_user=user.get("is_staff", False)), 200)
    else:
        return error_response("Method not allowed.", 405)


@require_auth
def handle_borrowing_return(request: Request, borrowing_id: str) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)

    borrowing = db.get_borrowing_by_id(borrowing_id)
    if not borrowing:
        return error_response("Borrowing not found.", 404)

    user = request.user
    if not user.get("is_staff") and borrowing["user_id"] != user["id"]:
        return error_response("You do not have permission to return this borrowing.", 403)

    if borrowing["actual_return_date"] is not None:
        return error_response("This borrowing has already been returned.", 400)

    # Check if payment was made
    payments = db.get_payments_for_borrowing(borrowing_id)
    paid_payments = [p for p in payments if p["status"] == "PAID" and p["type"] == "PAYMENT"]
    if not paid_payments:
        return error_response("Payment must be completed before returning the book.", 400)

    # Return the borrowing
    updated_borrowing = db.return_borrowing(borrowing_id)

    # Increase inventory
    book = db.get_book_by_id(borrowing["book_id"])
    if book:
        book["inventory"] += 1

    result = serialize_borrowing(updated_borrowing)

    # Check for fine
    fine_amount = calculate_fine(updated_borrowing)
    if fine_amount > 0:
        fine_payment = create_payment_session(borrowing_id, fine_amount, "FINE")
        result["fine_payment"] = serialize_payment(fine_payment)
        result["message"] = f"Book returned late. Fine of ${fine_amount} has been created."
    else:
        result["message"] = "Book returned successfully."

    return json_response(result, 200)


# --- Payment Handlers ---

@require_auth
def handle_payments_list(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed.", 405)

    user = request.user
    is_staff = user.get("is_staff", False)

    borrowing_id = request.query_params.get("borrowing_id")
    status_filter = request.query_params.get("status")
    payment_type = request.query_params.get("type")

    if is_staff:
        user_id_filter = request.query_params.get("user_id")
        payments = db.list_payments(borrowing_id=borrowing_id, user_id=user_id_filter)
    else:
        payments = db.list_payments(borrowing_id=borrowing_id, user_id=user["id"])

    if status_filter:
        payments = [p for p in payments if p["status"] == status_filter.upper()]
    if payment_type:
        payments = [p for p in payments if p["type"] == payment_type.upper()]

    return json_response([serialize_payment(p) for p in payments], 200)


@require_auth
def handle_payment_detail(request: Request, payment_id: str) -> Response:
    payment = db.get_payment_by_id(payment_id)
    if not payment:
        return error_response("Payment not found.", 404)

    user = request.user
    if not user.get("is_staff"):
        borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
        if not borrowing or borrowing["user_id"] != user["id"]:
            return error_response("You do not have permission to view this payment.", 403)

    if request.method == "GET":
        return json_response(serialize_payment(payment), 200)
    else:
        return error_response("Method not allowed.", 405)


@require_auth
def handle_payment_success(request: Request, payment_id: str) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)

    payment = db.get_payment_by_id(payment_id)
    if not payment:
        return error_response("Payment not found.", 404)

    user = request.user
    if not user.get("is_staff"):
        borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
        if not borrowing or borrowing["user_id"] != user["id"]:
            return error_response("You do not have permission to complete this payment.", 403)

    if payment["status"] == "PAID":
        return error_response("Payment has already been completed.", 400)

    if payment["status"] == "EXPIRED":
        return error_response("Payment session has expired.", 400)

    updated = db.update_payment_status(payment["id"], "PAID")
    return json_response({
        "message": "Payment completed successfully.",
        "payment": serialize_payment(updated),
    }, 200)


@require_auth
def handle_payment_cancel(request: Request, payment_id: str) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)

    payment = db.get_payment_by_id(payment_id)
    if not payment:
        return error_response("Payment not found.", 404)

    user = request.user
    if not user.get("is_staff"):
        borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
        if not borrowing or borrowing["user_id"] != user["id"]:
            return error_response("You do not have permission to cancel this payment.", 403)

    if payment["status"] in ("PAID", "EXPIRED"):
        return error_response(f"Cannot cancel a {payment['status'].lower()} payment.", 400)

    updated = db.update_payment_status(payment["id"], "EXPIRED")
    return json_response({
        "message": "Payment session cancelled. You can pay later.",
        "payment": serialize_payment(updated),
    }, 200)


# --- Admin Panel ---

def handle_admin(request: Request) -> Response:
    user = get_current_user(request)
    if not user or not user.get("is_staff"):
        return error_response("Admin access required.", 403)

    if request.method == "GET":
        stats = {
            "total_users": len(db.users),
            "total_books": len(db.books),
            "total_borrowings": len(db.borrowings),
            "active_borrowings": len([b for b in db.borrowings.values() if b["actual_return_date"] is None]),
            "total_payments": len(db.payments),
            "paid_payments": len([p for p in db.payments.values() if p["status"] == "PAID"]),
            "pending_payments": len([p for p in db.payments.values() if p["status"] == "PENDING"]),
            "users": [serialize_user(u) for u in db.users.values()],
            "books": [serialize_book(b) for b in db.books.values()],
            "borrowings": [serialize_borrowing(b, include_user=True) for b in db.borrowings.values()],
            "payments": [serialize_payment(p) for p in db.payments.values()],
        }
        return json_response(stats, 200)
    else:
        return error_response("Method not allowed.", 405)


# --- Swagger Documentation ---

def handle_swagger(request: Request) -> Response:
    swagger_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Service API",
            "version": "1.0.0",
            "description": "API Library service for borrowing books with JWT authentication.",
        },
        "servers": [{"url": "http://localhost:8000", "description": "Local server"}],
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
                        "id": {"type": "string"},
                        "email": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "is_staff": {"type": "boolean"},
                    },
                },
                "Book": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "cover": {"type": "string", "enum": ["HARD", "SOFT"]},
                        "inventory": {"type": "integer"},
                        "daily_fee": {"type": "string"},
                    },
                },
                "Borrowing": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "borrow_date": {"type": "string", "format": "date"},
                        "expected_return_date": {"type": "string", "format": "date"},
                        "actual_return_date": {"type": "string", "format": "date", "nullable": True},
                        "status": {"type": "string", "enum": ["ACTIVE", "RETURNED"]},
                        "book_id": {"type": "string"},
                        "user_id": {"type": "string"},
                    },
                },
                "Payment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "borrowing_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["PENDING", "PAID", "EXPIRED"]},
                        "type": {"type": "string", "enum": ["PAYMENT", "FINE"]},
                        "session_url": {"type": "string"},
                        "session_id": {"type": "string"},
                        "money_to_pay": {"type": "string"},
                    },
                },
            },
        },
        "security": [{"BearerAuth": []}],
        "paths": {
            "/api/v1/users/register/": {
                "post": {
                    "tags": ["Users"],
                    "summary": "Register a new user",
                    "security": [],
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
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "User created"},
                        "400": {"description": "Validation error"},
                        "409": {"description": "User already exists"},
                    },
                }
            },
            "/api/v1/users/token/": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Obtain JWT tokens",
                    "security": [],
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
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Tokens obtained"},
                        "401": {"description": "Invalid credentials"},
                    },
                }
            },
            "/api/v1/users/token/refresh/": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Refresh access token",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["refresh"],
                                    "properties": {"refresh": {"type": "string"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Access token refreshed"},
                        "401": {"description": "Invalid refresh token"},
                    },
                }
            },
            "/api/v1/users/me/": {
                "get": {
                    "tags": ["Users"],
                    "summary": "Get current user profile",
                    "responses": {
                        "200": {"description": "User profile"},
                        "401": {"description": "Unauthorized"},
                    },
                },
                "put": {
                    "tags": ["Users"],
                    "summary": "Update current user profile",
                    "responses": {
                        "200": {"description": "User updated"},
                        "401": {"description": "Unauthorized"},
                    },
                },
                "patch": {
                    "tags": ["Users"],
                    "summary": "Partially update current user profile",
                    "responses": {
                        "200": {"description": "User updated"},
                        "401": {"description": "Unauthorized"},
                    },
                },
            },
            "/api/v1/books/": {
                "get": {
                    "tags": ["Books"],
                    "summary": "List all books",
                    "security": [],
                    "parameters": [
                        {"name": "title", "in": "query", "schema": {"type": "string"}},
                        {"name": "author", "in": "query", "schema": {"type": "string"}},
                        {"name": "cover", "in": "query", "schema": {"type": "string", "enum": ["HARD", "SOFT"]}},
                    ],
                    "responses": {"200": {"description": "List of books"}},
                },
                "post": {
                    "tags": ["Books"],
                    "summary": "Create a new book (Admin only)",
                    "responses": {
                        "201": {"description": "Book created"},
                        "400": {"description": "Validation error"},
                        "403": {"description": "Forbidden"},
                    },
                },
            },
            "/api/v1/books/{id}/": {
                "get": {
                    "tags": ["Books"],
                    "summary": "Get book details",
                    "security": [],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Book details"},
                        "404": {"description": "Not found"},
                    },
                },
                "put": {
                    "tags": ["Books"],
                    "summary": "Update book (Admin only)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Book updated"},
                        "403": {"description": "Forbidden"},
                        "404": {"description": "Not found"},
                    },
                },
                "patch": {
                    "tags": ["Books"],
                    "summary": "Partially update book (Admin only)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Book updated"},
                        "403": {"description": "Forbidden"},
                        "404": {"description": "Not found"},
                    },
                },
                "delete": {
                    "tags": ["Books"],
                    "summary": "Delete book (Admin only)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "204": {"description": "Book deleted"},
                        "403": {"description": "Forbidden"},
                        "404": {"description": "Not found"},
                    },
                },
            },
            "/api/v1/borrowings/": {
                "get": {
                    "tags": ["Borrowings"],
                    "summary": "List borrowings",
                    "parameters": [
                        {"name": "is_active", "in": "query", "schema": {"type": "boolean"}, "description": "Filter by active status"},
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Filter by user (Admin only)"},
                        {"name": "actual_return_date", "in": "query", "schema": {"type": "string"}, "description": "Filter by actual return date (use 'null' for unreturned)"},
                    ],
                    "responses": {
                        "200": {"description": "List of borrowings"},
                        "401": {"description": "Unauthorized"},
                    },
                },
                "post": {
                    "tags": ["Borrowings"],
                    "summary": "Create a new borrowing",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["book_id", "expected_return_date"],
                                    "properties": {
                                        "book_id": {"type": "string"},
                                        "expected_return_date": {"type": "string", "format": "date"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Borrowing created"},
                        "400": {"description": "Validation error or book unavailable"},
                        "401": {"description": "Unauthorized"},
                    },
                },
            },
            "/api/v1/borrowings/{id}/": {
                "get": {
                    "tags": ["Borrowings"],
                    "summary": "Get borrowing details",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Borrowing details"},
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/api/v1/borrowings/{id}/return/": {
                "post": {
                    "tags": ["Borrowings"],
                    "summary": "Return a borrowed book",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Book returned"},
                        "400": {"description": "Already returned or payment pending"},
                        "401": {"description": "Unauthorized"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/api/v1/payments/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "List payments",
                    "parameters": [
                        {"name": "borrowing_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["PENDING", "PAID", "EXPIRED"]}},
                        {"name": "type", "in": "query", "schema": {"type": "string", "enum": ["PAYMENT", "FINE"]}},
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Admin only"},
                    ],
                    "responses": {
                        "200": {"description": "List of payments"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/api/v1/payments/{id}/": {
                "get": {
                    "tags": ["Payments"],
                    "summary": "Get payment details",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Payment details"},
                        "401": {"description": "Unauthorized"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/api/v1/payments/{id}/success/": {
                "post": {
                    "tags": ["Payments"],
                    "summary": "Complete a payment",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Payment completed"},
                        "400": {"description": "Payment already completed or expired"},
                        "401": {"description": "Unauthorized"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/api/v1/payments/{id}/cancel/": {
                "post": {
                    "tags": ["Payments"],
                    "summary": "Cancel a payment",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Payment cancelled"},
                        "400": {"description": "Cannot cancel"},
                        "401": {"description": "Unauthorized"},
                        "404": {"description": "Not found"},
                    },
                }
            },
        },
    }
    return json_response(swagger_doc, 200)


# ============================================================
# Router
# ============================================================

import re


class Router:
    def __init__(self):
        self.routes: List[tuple] = []

    def add_route(self, pattern: str, handler, methods: Optional[List[str]] = None):
        regex = re.compile("^" + pattern + "$")
        self.routes.append((regex, handler, methods or ["GET", "POST", "PUT", "PATCH", "DELETE"]))

    def match(self, path: str, method: str) -> tuple:
        for regex, handler, methods in self.routes:
            match = regex.match(path)
            if match:
                return handler, match.groupdict()
        return None, {}


router = Router()

# Register routes
router.add_route(r"/api/v1/users/register/", handle_register)
router.add_route(r"/api/v1/users/token/", handle_token_obtain)
router.add_route(r"/api/v1/users/token/refresh/", handle_token_refresh)
router.add_route(r"/api/v1/users/me/", handle_user_me)
router.add_route(r"/api/v1/books/", handle_books_list)
router.add_route(r"/api/v1/books/(?P<book_id>[^/]+)/", handle_book_detail)
router.add_route(r"/api/v1/borrowings/", handle_borrowings_list)
router.add_route(r"/api/v1/borrowings/(?P<borrowing_id>[^/]+)/", handle_borrowing_detail)
router.add_route(r"/api/v1/borrowings/(?P<borrowing_id>[^/]+)/return/", handle_borrowing_return)
router.add_route(r"/api/v1/payments/", handle_payments_list)
router.add_route(r"/api/v1/payments/(?P<payment_id>[^/]+)/", handle_payment_detail)
router.add_route(r"/api/v1/payments/(?P<payment_id>[^/]+)/success/", handle_payment_success)
router.add_route(r"/api/v1/payments/(?P<payment_id>[^/]+)/cancel/", handle_payment_cancel)
router.add_route(r"/admin/", handle_admin)
router.add_route(r"/api/v1/doc/swagger/", handle_swagger)


# ============================================================
# WSGI Application
# ============================================================

def application(environ: Dict, start_response) -> List[bytes]:
    request = Request(environ)

    # Fix path for borrowing return route (needs to be matched before detail)
    path = request.path

    # Try to match borrowing return first
    return_match = re.match(r"^/api/v1/borrowings/([^/]+)/return/$", path)
    if return_match:
        borrowing_id = return_match.group(1)
        response = handle_borrowing_return(request, borrowing_id=borrowing_id)
        return response.to_wsgi(start_response)

    # Try to match payment success/cancel first
    success_match = re.match(r"^/api/v1/payments/([^/]+)/success/$", path)
    if success_match:
        payment_id = success_match.group(1)
        response = handle_payment_success(request, payment_id=payment_id)
        return response.to_wsgi(start_response)

    cancel_match = re.match(r"^/api/v1/payments/([^/]+)/cancel/$", path)
    if cancel_match:
        payment_id = cancel_match.group(1)
        response = handle_payment_cancel(request, payment_id=payment_id)
        return response.to_wsgi(start_response)

    handler, kwargs = router.match(path, request.method)

    if handler is None:
        response = error_response("Not found.", 404)
        return response.to_wsgi(start_response)

    try:
        response = handler(request, **kwargs)
    except Exception as e:
        response = error_response(f"Internal server error: {str(e)}", 500)

    return response.to_wsgi(start_response)


# ============================================================
# CLI / Server
# ============================================================

def run_server(host: str = "0.0.0.0", port: int = 8000):
    from wsgiref.simple_server import make_server, WSGIRequestHandler

    class SilentHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            print(f"[{self.address_string()}] {format % args}")

    print(f"Library Service API running at http://{host}:{port}")
    print(f"Admin panel: http://{host}:{port}/admin/")
    print(f"Swagger docs: http://{host}:{port}/api/v1/doc/swagger/")
    print(f"Default admin credentials: admin@library.com / admin123")
    print("Press Ctrl+C to stop.")

    with make_server(host, port, application, handler_class=SilentHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


# ============================================================
# Tests
# ============================================================

class TestLibraryAPI:
    def __init__(self):
        global db
        db = Database()
        self.passed = 0
        self.failed = 0

    def _make_request(self, method: str, path: str, data: Optional[Dict] = None,
                      token: Optional[str] = None, query_params: Optional[Dict] = None) -> Response:
        body = json.dumps(data).encode() if data else b""
        qs = "&".join(f"{k}={v}" for k, v in (query_params or {}).items())

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": qs,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": __import__("io").BytesIO(body),
        }
        if token:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        request = Request(environ)
        if token:
            request.user = None

        # Route manually
        path_info = path

        return_match = re.match(r"^/api/v1/borrowings/([^/]+)/return/$", path_info)
        if return_match:
            return handle_borrowing_return(request, borrowing_id=return_match.group(1))

        success_match = re.match(r"^/api/v1/payments/([^/]+)/success/$", path_info)
        if success_match:
            return handle_payment_success(request, payment_id=success_match.group(1))

        cancel_match = re.match(r"^/api/v1/payments/([^/]+)/cancel/$", path_info)
        if cancel_match:
            return handle_payment_cancel(request, payment_id=cancel_match.group(1))

        handler, kwargs = router.match(path_info, method)
        if handler is None:
            return error_response("Not found.", 404)

        return handler(request, **kwargs)

    def assert_equal(self, actual, expected, test_name: str):
        if actual == expected:
            print(f"  ✓ {test_name}")
            self.passed += 1
        else:
            print(f"  ✗ {test_name}: expected {expected}, got {actual}")
            self.failed += 1

    def run_all(self):
        print("\n=== Running Library API Tests ===\n")

        self.test_user_registration()
        self.test_authentication()
        self.test_books_crud()
        self.test_borrowings()
        self.test_payments()
        self.test_filtering()
        self.test_admin()
        self.test_swagger()

        print(f"\n=== Results: {self.passed} passed, {self.failed} failed ===\n")

    def test_user_registration(self):
        print("--- User Registration Tests ---")

        # Register new user
        resp = self._make_request("POST", "/api/v1/users/register/", {
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        })
        self.assert_equal(resp.status, 201, "Register new user")
        self.assert_equal(resp.data["email"], "test@example.com", "User email correct")

        # Duplicate registration
        resp = self._make_request("POST", "/api/v1/users/register/", {
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        })
        self.assert_equal(resp.status, 409, "Duplicate registration rejected")

        # Missing fields
        resp = self._make_request("POST", "/api/v1/users/register/", {
            "email": "test2@example.com",
        })
        self.assert_equal(resp.status, 400, "Missing fields rejected")

    def test_authentication(self):
        print("\n--- Authentication Tests ---")

        # Get token
        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        self.assert_equal(resp.status, 200, "Token obtained")
        self.assert_equal("access" in resp.data, True, "Access token present")
        self.assert_equal("refresh" in resp.data, True, "Refresh token present")

        access_token = resp.data["access"]
        refresh_token = resp.data["refresh"]

        # Refresh token
        resp = self._make_request("POST", "/api/v1/users/token/refresh/", {
            "refresh": refresh_token,
        })
        self.assert_equal(resp.status, 200, "Token refreshed")

        # Get user profile
        resp = self._make_request("GET", "/api/v1/users/me/", token=access_token)
        self.assert_equal(resp.status, 200, "Get user profile")
        self.assert_equal(resp.data["email"], "admin@library.com", "Profile email correct")

        # Invalid credentials
        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "wrongpassword",
        })
        self.assert_equal(resp.status, 401, "Invalid credentials rejected")

        # Unauthorized access
        resp = self._make_request("GET", "/api/v1/users/me/")
        self.assert_equal(resp.status, 401, "Unauthorized access rejected")

    def test_books_crud(self):
        print("\n--- Books CRUD Tests ---")

        # Get admin token
        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        admin_token = resp.data["access"]

        # Get user token
        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "test@example.com",
            "password": "testpass123",
        })
        user_token = resp.data["access"]

        # List books (empty)
        resp = self._make_request("GET", "/api/v1/books/")
        self.assert_equal(resp.status, 200, "List books")
        self.assert_equal(len(resp.data), 0, "Empty book list")

        # Create book (admin)
        resp = self._make_request("POST", "/api/v1/books/", {
            "title": "Python Programming",
            "author": "Guido van Rossum",
            "cover": "HARD",
            "inventory": 5,
            "daily_fee": "1.50",
        }, token=admin_token)
        self.assert_equal(resp.status, 201, "Create book (admin)")
        book_id = resp.data["id"]

        # Create book (non-admin) - should fail
        resp = self._make_request("POST", "/api/v1/books/", {
            "title": "Test Book",
            "author": "Test Author",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": "2.00",
        }, token=user_token)
        self.assert_equal(resp.status, 403, "Create book (non-admin) rejected")

        # Get book
        resp = self._make_request("GET", f"/api/v1/books/{book_id}/")
        self.assert_equal(resp.status, 200, "Get book")
        self.assert_equal(resp.data["title"], "Python Programming", "Book title correct")

        # Update book
        resp = self._make_request("PATCH", f"/api/v1/books/{book_id}/", {
            "inventory": 10,
        }, token=admin_token)
        self.assert_equal(resp.status, 200, "Update book")
        self.assert_equal(resp.data["inventory"], 10, "Inventory updated")

        # Invalid cover
        resp = self._make_request("POST", "/api/v1/books/", {
            "title": "Test",
            "author": "Author",
            "cover": "INVALID",
            "inventory": 1,
            "daily_fee": "1.00",
        }, token=admin_token)
        self.assert_equal(resp.status, 400, "Invalid cover rejected")

        # Delete book
        resp = self._make_request("DELETE", f"/api/v1/books/{book_id}/", token=admin_token)
        self.assert_equal(resp.status, 204, "Delete book")

        # Get deleted book
        resp = self._make_request("GET", f"/api/v1/books/{book_id}/")
        self.assert_equal(resp.status, 404, "Deleted book not found")

    def test_borrowings(self):
        print("\n--- Borrowing Tests ---")

        # Setup
        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        admin_token = resp.data["access"]

        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "test@example.com",
            "password": "testpass123",
        })
        user_token = resp.data["access"]

        # Create a book
        resp = self._make_request("POST", "/api/v1/books/", {
            "title": "Clean Code",
            "author": "Robert Martin",
            "cover": "SOFT",
            "inventory": 2,
            "daily_fee": "2.00",
        }, token=admin_token)
        book_id = resp.data["id"]

        # Create borrowing
        future_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        resp = self._make_request("POST", "/api/v1/borrowings/", {
            "book_id": book_id,
            "expected_return_date": future_date,
        }, token=user_token)
        self.assert_equal(resp.status, 201, "Create borrowing")
        borrowing_id = resp.data["id"]
        payment_id = resp.data["payment"]["id"]

        # Check inventory decreased
        resp = self._make_request("GET", f"/api/v1/books/{book_id}/")
        self.assert_equal(resp.data["inventory"], 1, "Inventory decreased after borrowing")

        # Get borrowing
        resp = self._make_request("GET", f"/api/v1/borrowings/{borrowing_id}/", token=user_token)
        self.assert_equal(resp.status, 200, "Get borrowing")

        # Try to return without payment
        resp = self._make_request("POST", f"/api/v1/borrowings/{borrowing_id}/return/", token=user_token)
        self.assert_equal(resp.status, 400, "Return without payment rejected")

        # Complete payment
        resp = self._make_request("POST", f"/api/v1/payments/{payment_id}/success/", token=user_token)
        self.assert_equal(resp.status, 200, "Payment completed")

        # Return book
        resp = self._make_request("POST", f"/api/v1/borrowings/{borrowing_id}/return/", token=user_token)
        self.assert_equal(resp.status, 200, "Return book")

        # Check inventory increased
        resp = self._make_request("GET", f"/api/v1/books/{book_id}/")
        self.assert_equal(resp.data["inventory"], 2, "Inventory increased after return")

        # Try to return again
        resp = self._make_request("POST", f"/api/v1/borrowings/{borrowing_id}/return/", token=user_token)
        self.assert_equal(resp.status, 400, "Double return rejected")

        # Past date borrowing
        past_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        resp = self._make_request("POST", "/api/v1/borrowings/", {
            "book_id": book_id,
            "expected_return_date": past_date,
        }, token=user_token)
        self.assert_equal(resp.status, 400, "Past date borrowing rejected")

    def test_payments(self):
        print("\n--- Payment Tests ---")

        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        admin_token = resp.data["access"]

        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "test@example.com",
            "password": "testpass123",
        })
        user_token = resp.data["access"]

        # Create book and borrowing
        resp = self._make_request("POST", "/api/v1/books/", {
            "title": "Design Patterns",
            "author": "Gang of Four",
            "cover": "HARD",
            "inventory": 3,
            "daily_fee": "3.00",
        }, token=admin_token)
        book_id = resp.data["id"]

        future_date = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
        resp = self._make_request("POST", "/api/v1/borrowings/", {
            "book_id": book_id,
            "expected_return_date": future_date,
        }, token=user_token)
        payment_id = resp.data["payment"]["id"]

        # List payments
        resp = self._make_request("GET", "/api/v1/payments/", token=user_token)
        self.assert_equal(resp.status, 200, "List payments")
        self.assert_equal(len(resp.data) > 0, True, "Payments list not empty")

        # Get payment
        resp = self._make_request("GET", f"/api/v1/payments/{payment_id}/", token=user_token)
        self.assert_equal(resp.status, 200, "Get payment")
        self.assert_equal(resp.data["status"], "PENDING", "Payment status is PENDING")
        self.assert_equal(resp.data["type"], "PAYMENT", "Payment type is PAYMENT")

        # Cancel payment
        resp = self._make_request("POST", f"/api/v1/payments/{payment_id}/cancel/", token=user_token)
        self.assert_equal(resp.status, 200, "Cancel payment")

        # Try to complete cancelled payment
        resp = self._make_request("POST", f"/api/v1/payments/{payment_id}/success/", token=user_token)
        self.assert_equal(resp.status, 400, "Complete cancelled payment rejected")

    def test_filtering(self):
        print("\n--- Filtering Tests ---")

        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        admin_token = resp.data["access"]

        # Filter books by title
        resp = self._make_request("GET", "/api/v1/books/", query_params={"title": "Clean"})
        self.assert_equal(resp.status, 200, "Filter books by title")

        # Filter borrowings by is_active
        resp = self._make_request("GET", "/api/v1/borrowings/", token=admin_token,
                                  query_params={"is_active": "true"})
        self.assert_equal(resp.status, 200, "Filter borrowings by is_active")

        # Filter borrowings by actual_return_date=null
        resp = self._make_request("GET", "/api/v1/borrowings/", token=admin_token,
                                  query_params={"actual_return_date": "null"})
        self.assert_equal(resp.status, 200, "Filter borrowings by actual_return_date=null")

        # Filter payments by status
        resp = self._make_request("GET", "/api/v1/payments/", token=admin_token,
                                  query_params={"status": "PENDING"})
        self.assert_equal(resp.status, 200, "Filter payments by status")

    def test_admin(self):
        print("\n--- Admin Tests ---")

        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        admin_token = resp.data["access"]

        resp = self._make_request("POST", "/api/v1/users/token/", {
            "email": "test@example.com",
            "password": "testpass123",
        })
        user_token = resp.data["access"]

        # Admin panel access
        resp = self._make_request("GET", "/admin/", token=admin_token)
        self.assert_equal(resp.status, 200, "Admin panel accessible")
        self.assert_equal("total_users" in resp.data, True, "Admin stats present")

        # Non-admin access to admin panel
        resp = self._make_request("GET", "/admin/", token=user_token)
        self.assert_equal(resp.status, 403, "Non-admin access to admin panel rejected")

    def test_swagger(self):
        print("\n--- Swagger Tests ---")

        resp = self._make_request("GET", "/api/v1/doc/swagger/")
        self.assert_equal(resp.status, 200, "Swagger docs accessible")
        self.assert_equal("openapi" in resp.data, True, "OpenAPI spec present")
        self.assert_equal("paths" in resp.data, True, "Paths present in spec")


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        tests = TestLibraryAPI()
        tests.run_all()
    elif len(sys.argv) > 1 and sys.argv[1] == "runserver":
        host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
        run_server(host, port)
    else:
        print("Library Service API")
        print("Usage:")
        print("  python solution.py runserver [host] [port]  - Start the server")
        print("  python solution.py test                      - Run tests")
        print("")
        print("Default: Starting server on port 8000...")
        run_server()