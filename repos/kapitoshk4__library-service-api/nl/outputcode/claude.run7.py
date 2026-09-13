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
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
FINE_MULTIPLIER = decimal.Decimal("2.0")  # Fine is 2x daily fee

# ============================================================
# Utilities
# ============================================================

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def generate_jwt(payload: dict) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header).encode())
    payload_encoded = base64url_encode(json.dumps(payload).encode())
    signing_input = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    return f"{signing_input}.{signature_encoded}"


def verify_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_encoded, payload_encoded, signature_encoded = parts
        signing_input = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(
            SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        expected_encoded = base64url_encode(expected_signature)
        if not hmac.compare_digest(signature_encoded, expected_encoded):
            return None
        payload = json.loads(base64url_decode(payload_encoded))
        exp = payload.get("exp")
        if exp and datetime.datetime.utcnow().timestamp() > exp:
            return None
        return payload
    except Exception:
        return None


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


def now_utc() -> datetime.datetime:
    return datetime.datetime.utcnow()


def today() -> datetime.date:
    return datetime.date.today()


# ============================================================
# Database (In-Memory)
# ============================================================

class Database:
    def __init__(self):
        self.users: Dict[int, dict] = {}
        self.books: Dict[int, dict] = {}
        self.borrowings: Dict[int, dict] = {}
        self.payments: Dict[int, dict] = {}
        self._user_counter = 1
        self._book_counter = 1
        self._borrowing_counter = 1
        self._payment_counter = 1
        self._create_admin()

    def _create_admin(self):
        admin = {
            "id": self._user_counter,
            "email": "admin@library.com",
            "password": hash_password("admin123"),
            "first_name": "Admin",
            "last_name": "User",
            "is_staff": True,
            "is_active": True,
            "created_at": now_utc().isoformat(),
        }
        self.users[self._user_counter] = admin
        self._user_counter += 1

    def next_user_id(self) -> int:
        uid = self._user_counter
        self._user_counter += 1
        return uid

    def next_book_id(self) -> int:
        bid = self._book_counter
        self._book_counter += 1
        return bid

    def next_borrowing_id(self) -> int:
        bid = self._borrowing_counter
        self._borrowing_counter += 1
        return bid

    def next_payment_id(self) -> int:
        pid = self._payment_counter
        self._payment_counter += 1
        return pid

    def get_user_by_email(self, email: str) -> Optional[dict]:
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        return self.users.get(user_id)

    def get_book_by_id(self, book_id: int) -> Optional[dict]:
        return self.books.get(book_id)

    def get_borrowing_by_id(self, borrowing_id: int) -> Optional[dict]:
        return self.borrowings.get(borrowing_id)

    def get_payment_by_id(self, payment_id: int) -> Optional[dict]:
        return self.payments.get(payment_id)

    def get_borrowings_for_user(self, user_id: int) -> List[dict]:
        return [b for b in self.borrowings.values() if b["user_id"] == user_id]

    def get_all_borrowings(self) -> List[dict]:
        return list(self.borrowings.values())

    def get_payments_for_user(self, user_id: int) -> List[dict]:
        return [p for p in self.payments.values() if p["user_id"] == user_id]

    def get_all_payments(self) -> List[dict]:
        return list(self.payments.values())


db = Database()


# ============================================================
# Models / Business Logic
# ============================================================

class BookCoverType:
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


class UserModel:
    @staticmethod
    def create(email: str, password: str, first_name: str, last_name: str, is_staff: bool = False) -> dict:
        if db.get_user_by_email(email):
            raise ValueError("User with this email already exists.")
        uid = db.next_user_id()
        user = {
            "id": uid,
            "email": email,
            "password": hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": is_staff,
            "is_active": True,
            "created_at": now_utc().isoformat(),
        }
        db.users[uid] = user
        return user

    @staticmethod
    def update(user_id: int, data: dict) -> Optional[dict]:
        user = db.get_user_by_id(user_id)
        if not user:
            return None
        allowed = ["first_name", "last_name", "email"]
        for key in allowed:
            if key in data:
                user[key] = data[key]
        if "password" in data:
            user["password"] = hash_password(data["password"])
        db.users[user_id] = user
        return user

    @staticmethod
    def serialize(user: dict, include_password: bool = False) -> dict:
        result = {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_staff": user["is_staff"],
            "is_active": user["is_active"],
        }
        return result


class BookModel:
    @staticmethod
    def create(title: str, author: str, cover: str, inventory: int, daily_fee: str) -> dict:
        if cover not in BookCoverType.CHOICES:
            raise ValueError(f"Cover must be one of {BookCoverType.CHOICES}")
        if inventory < 0:
            raise ValueError("Inventory must be non-negative.")
        try:
            fee = decimal.Decimal(daily_fee)
            if fee <= 0:
                raise ValueError("Daily fee must be positive.")
        except decimal.InvalidOperation:
            raise ValueError("Invalid daily fee format.")
        bid = db.next_book_id()
        book = {
            "id": bid,
            "title": title,
            "author": author,
            "cover": cover,
            "inventory": inventory,
            "daily_fee": str(fee),
            "created_at": now_utc().isoformat(),
        }
        db.books[bid] = book
        return book

    @staticmethod
    def update(book_id: int, data: dict) -> Optional[dict]:
        book = db.get_book_by_id(book_id)
        if not book:
            return None
        if "cover" in data and data["cover"] not in BookCoverType.CHOICES:
            raise ValueError(f"Cover must be one of {BookCoverType.CHOICES}")
        if "inventory" in data and data["inventory"] < 0:
            raise ValueError("Inventory must be non-negative.")
        if "daily_fee" in data:
            try:
                fee = decimal.Decimal(data["daily_fee"])
                if fee <= 0:
                    raise ValueError("Daily fee must be positive.")
                data["daily_fee"] = str(fee)
            except decimal.InvalidOperation:
                raise ValueError("Invalid daily fee format.")
        allowed = ["title", "author", "cover", "inventory", "daily_fee"]
        for key in allowed:
            if key in data:
                book[key] = data[key]
        db.books[book_id] = book
        return book

    @staticmethod
    def delete(book_id: int) -> bool:
        if book_id not in db.books:
            return False
        del db.books[book_id]
        return True

    @staticmethod
    def serialize(book: dict) -> dict:
        return {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "cover": book["cover"],
            "inventory": book["inventory"],
            "daily_fee": book["daily_fee"],
        }


class BorrowingModel:
    @staticmethod
    def create(user_id: int, book_id: int, expected_return_date: str) -> dict:
        book = db.get_book_by_id(book_id)
        if not book:
            raise ValueError("Book not found.")
        if book["inventory"] <= 0:
            raise ValueError("Book is not available (inventory is 0).")
        try:
            exp_date = datetime.date.fromisoformat(expected_return_date)
        except ValueError:
            raise ValueError("Invalid expected_return_date format. Use YYYY-MM-DD.")
        if exp_date <= today():
            raise ValueError("Expected return date must be in the future.")

        # Decrease inventory
        book["inventory"] -= 1
        db.books[book_id] = book

        bid = db.next_borrowing_id()
        borrowing = {
            "id": bid,
            "user_id": user_id,
            "book_id": book_id,
            "borrow_date": today().isoformat(),
            "expected_return_date": expected_return_date,
            "actual_return_date": None,
            "created_at": now_utc().isoformat(),
        }
        db.borrowings[bid] = borrowing

        # Create payment
        days = (exp_date - today()).days
        daily_fee = decimal.Decimal(book["daily_fee"])
        amount = daily_fee * days
        PaymentModel.create(
            user_id=user_id,
            borrowing_id=bid,
            payment_type=PaymentType.PAYMENT,
            amount=str(amount),
        )

        return borrowing

    @staticmethod
    def return_book(borrowing_id: int, user_id: int, is_staff: bool) -> dict:
        borrowing = db.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found.")
        if not is_staff and borrowing["user_id"] != user_id:
            raise PermissionError("You do not have permission to return this borrowing.")
        if borrowing["actual_return_date"] is not None:
            raise ValueError("This borrowing has already been returned.")

        actual_return = today()
        borrowing["actual_return_date"] = actual_return.isoformat()
        db.borrowings[borrowing_id] = borrowing

        # Restore inventory
        book = db.get_book_by_id(borrowing["book_id"])
        if book:
            book["inventory"] += 1
            db.books[book["id"]] = book

        # Check for overdue fine
        expected = datetime.date.fromisoformat(borrowing["expected_return_date"])
        if actual_return > expected:
            overdue_days = (actual_return - expected).days
            daily_fee = decimal.Decimal(book["daily_fee"]) if book else decimal.Decimal("0")
            fine_amount = daily_fee * overdue_days * FINE_MULTIPLIER
            PaymentModel.create(
                user_id=borrowing["user_id"],
                borrowing_id=borrowing_id,
                payment_type=PaymentType.FINE,
                amount=str(fine_amount),
            )

        return borrowing

    @staticmethod
    def serialize(borrowing: dict, include_book: bool = True, include_user: bool = False) -> dict:
        result = {
            "id": borrowing["id"],
            "borrow_date": borrowing["borrow_date"],
            "expected_return_date": borrowing["expected_return_date"],
            "actual_return_date": borrowing["actual_return_date"],
            "book_id": borrowing["book_id"],
            "user_id": borrowing["user_id"],
        }
        if include_book:
            book = db.get_book_by_id(borrowing["book_id"])
            if book:
                result["book"] = BookModel.serialize(book)
        if include_user:
            user = db.get_user_by_id(borrowing["user_id"])
            if user:
                result["user"] = UserModel.serialize(user)
        return result


class PaymentModel:
    @staticmethod
    def create(user_id: int, borrowing_id: int, payment_type: str, amount: str) -> dict:
        session_id = str(uuid.uuid4())
        session_url = f"https://checkout.stripe.com/pay/{session_id}"
        pid = db.next_payment_id()
        payment = {
            "id": pid,
            "user_id": user_id,
            "borrowing_id": borrowing_id,
            "status": PaymentStatus.PENDING,
            "type": payment_type,
            "session_url": session_url,
            "session_id": session_id,
            "money_to_pay": amount,
            "created_at": now_utc().isoformat(),
        }
        db.payments[pid] = payment
        return payment

    @staticmethod
    def complete_payment(payment_id: int, user_id: int, is_staff: bool) -> dict:
        payment = db.get_payment_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found.")
        if not is_staff and payment["user_id"] != user_id:
            raise PermissionError("You do not have permission to complete this payment.")
        if payment["status"] == PaymentStatus.PAID:
            raise ValueError("Payment is already completed.")
        payment["status"] = PaymentStatus.PAID
        db.payments[payment_id] = payment
        return payment

    @staticmethod
    def serialize(payment: dict) -> dict:
        return {
            "id": payment["id"],
            "status": payment["status"],
            "type": payment["type"],
            "borrowing_id": payment["borrowing_id"],
            "session_url": payment["session_url"],
            "session_id": payment["session_id"],
            "money_to_pay": payment["money_to_pay"],
            "user_id": payment["user_id"],
        }


# ============================================================
# HTTP Framework (Minimal WSGI)
# ============================================================

class Request:
    def __init__(self, environ: dict):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/")
        self.query_string = environ.get("QUERY_STRING", "")
        self.query_params = self._parse_query(self.query_string)
        self.headers = self._parse_headers(environ)
        self._body = None
        self._json = None
        self.user = None
        self.path_params: Dict[str, str] = {}

    def _parse_query(self, qs: str) -> Dict[str, str]:
        params = {}
        if not qs:
            return params
        for part in qs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
            elif part:
                params[part] = ""
        return params

    def _parse_headers(self, environ: dict) -> Dict[str, str]:
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header_name = key.replace("_", "-").title()
                headers[header_name] = value
        return headers

    def get_body(self) -> bytes:
        if self._body is None:
            try:
                length = int(self.environ.get("CONTENT_LENGTH", 0) or 0)
                self._body = self.environ["wsgi.input"].read(length)
            except Exception:
                self._body = b""
        return self._body

    def get_json(self) -> Optional[dict]:
        if self._json is None:
            body = self.get_body()
            if body:
                try:
                    self._json = json.loads(body.decode("utf-8"))
                except Exception:
                    self._json = {}
            else:
                self._json = {}
        return self._json

    def get_authorization(self) -> Optional[str]:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None


class Response:
    def __init__(self, body: Any, status: int = 200, content_type: str = "application/json"):
        self.status = status
        self.content_type = content_type
        if isinstance(body, (dict, list)):
            self.body = json.dumps(body, default=str).encode("utf-8")
        elif isinstance(body, str):
            self.body = body.encode("utf-8")
        elif isinstance(body, bytes):
            self.body = body
        else:
            self.body = json.dumps(body, default=str).encode("utf-8")

    def get_status_string(self) -> str:
        status_texts = {
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
        return status_texts.get(self.status, f"{self.status} Unknown")

    def get_headers(self) -> List[tuple]:
        return [
            ("Content-Type", self.content_type),
            ("Content-Length", str(len(self.body))),
        ]


def json_response(data: Any, status: int = 200) -> Response:
    return Response(data, status=status)


def error_response(message: str, status: int = 400) -> Response:
    return Response({"error": message}, status=status)


# ============================================================
# Authentication Middleware
# ============================================================

def authenticate(request: Request) -> Optional[dict]:
    token = request.get_authorization()
    if not token:
        return None
    payload = verify_jwt(token)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    user = db.get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        return None
    return user


def require_auth(f):
    @wraps(f)
    def wrapper(request: Request, *args, **kwargs):
        user = authenticate(request)
        if not user:
            return error_response("Authentication required.", 401)
        request.user = user
        return f(request, *args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(request: Request, *args, **kwargs):
        user = authenticate(request)
        if not user:
            return error_response("Authentication required.", 401)
        if not user.get("is_staff"):
            return error_response("Admin access required.", 403)
        request.user = user
        return f(request, *args, **kwargs)
    return wrapper


# ============================================================
# Router
# ============================================================

class Router:
    def __init__(self):
        self.routes: List[tuple] = []

    def add_route(self, method: str, path_pattern: str, handler):
        self.routes.append((method.upper(), path_pattern, handler))

    def match(self, method: str, path: str):
        for route_method, pattern, handler in self.routes:
            if route_method != method and route_method != "*":
                continue
            params = self._match_pattern(pattern, path)
            if params is not None:
                return handler, params
        return None, {}

    def _match_pattern(self, pattern: str, path: str) -> Optional[dict]:
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return None
        params = {}
        for pp, pathp in zip(pattern_parts, path_parts):
            if pp.startswith("<") and pp.endswith(">"):
                param_name = pp[1:-1]
                params[param_name] = pathp
            elif pp != pathp:
                return None
        return params


router = Router()


# ============================================================
# View Handlers
# ============================================================

# --- Auth Views ---

def auth_register(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    if not email or not password:
        return error_response("Email and password are required.", 400)
    if len(password) < 6:
        return error_response("Password must be at least 6 characters.", 400)
    try:
        user = UserModel.create(email, password, first_name, last_name)
        return json_response(UserModel.serialize(user), 201)
    except ValueError as e:
        return error_response(str(e), 409)


def auth_login(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    if not email or not password:
        return error_response("Email and password are required.", 400)
    user = db.get_user_by_email(email)
    if not user or not verify_password(password, user["password"]):
        return error_response("Invalid credentials.", 401)
    if not user.get("is_active"):
        return error_response("Account is inactive.", 401)
    exp = (now_utc() + datetime.timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "is_staff": user["is_staff"],
        "exp": exp,
    }
    token = generate_jwt(payload)
    return json_response({"access": token, "token_type": "Bearer"})


def auth_refresh(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)
    data = request.get_json()
    token = data.get("token", "")
    payload = verify_jwt(token)
    if not payload:
        return error_response("Invalid or expired token.", 401)
    user_id = payload.get("user_id")
    user = db.get_user_by_id(user_id)
    if not user:
        return error_response("User not found.", 401)
    exp = (now_utc() + datetime.timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()
    new_payload = {
        "user_id": user["id"],
        "email": user["email"],
        "is_staff": user["is_staff"],
        "exp": exp,
    }
    new_token = generate_jwt(new_payload)
    return json_response({"access": new_token, "token_type": "Bearer"})


# --- User Views ---

@require_auth
def user_me(request: Request) -> Response:
    if request.method == "GET":
        return json_response(UserModel.serialize(request.user))
    elif request.method in ("PUT", "PATCH"):
        data = request.get_json()
        updated = UserModel.update(request.user["id"], data)
        return json_response(UserModel.serialize(updated))
    return error_response("Method not allowed.", 405)


@require_admin
def user_list(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed.", 405)
    users = [UserModel.serialize(u) for u in db.users.values()]
    return json_response(users)


@require_admin
def user_detail(request: Request) -> Response:
    user_id = int(request.path_params.get("id", 0))
    user = db.get_user_by_id(user_id)
    if not user:
        return error_response("User not found.", 404)
    if request.method == "GET":
        return json_response(UserModel.serialize(user))
    elif request.method in ("PUT", "PATCH"):
        data = request.get_json()
        updated = UserModel.update(user_id, data)
        return json_response(UserModel.serialize(updated))
    elif request.method == "DELETE":
        user["is_active"] = False
        db.users[user_id] = user
        return Response(b"", status=204)
    return error_response("Method not allowed.", 405)


# --- Book Views ---

def book_list(request: Request) -> Response:
    if request.method == "GET":
        books = [BookModel.serialize(b) for b in db.books.values()]
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
        return json_response(books)
    elif request.method == "POST":
        user = authenticate(request)
        if not user or not user.get("is_staff"):
            return error_response("Admin access required.", 403)
        data = request.get_json()
        try:
            book = BookModel.create(
                title=data.get("title", ""),
                author=data.get("author", ""),
                cover=data.get("cover", BookCoverType.SOFT),
                inventory=int(data.get("inventory", 0)),
                daily_fee=str(data.get("daily_fee", "0")),
            )
            return json_response(BookModel.serialize(book), 201)
        except (ValueError, TypeError) as e:
            return error_response(str(e), 400)
    return error_response("Method not allowed.", 405)


def book_detail(request: Request) -> Response:
    book_id = int(request.path_params.get("id", 0))
    book = db.get_book_by_id(book_id)
    if not book:
        return error_response("Book not found.", 404)
    if request.method == "GET":
        return json_response(BookModel.serialize(book))
    user = authenticate(request)
    if not user or not user.get("is_staff"):
        return error_response("Admin access required.", 403)
    if request.method in ("PUT", "PATCH"):
        data = request.get_json()
        if "inventory" in data:
            data["inventory"] = int(data["inventory"])
        try:
            updated = BookModel.update(book_id, data)
            return json_response(BookModel.serialize(updated))
        except ValueError as e:
            return error_response(str(e), 400)
    elif request.method == "DELETE":
        BookModel.delete(book_id)
        return Response(b"", status=204)
    return error_response("Method not allowed.", 405)


# --- Borrowing Views ---

@require_auth
def borrowing_list(request: Request) -> Response:
    if request.method == "GET":
        user = request.user
        if user.get("is_staff"):
            borrowings = db.get_all_borrowings()
            # Filter by user_id if provided
            user_id_filter = request.query_params.get("user_id")
            if user_id_filter:
                try:
                    uid = int(user_id_filter)
                    borrowings = [b for b in borrowings if b["user_id"] == uid]
                except ValueError:
                    pass
        else:
            borrowings = db.get_borrowings_for_user(user["id"])

        # Filter by is_active (actual_return_date is None)
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1", "yes"):
                borrowings = [b for b in borrowings if b["actual_return_date"] is None]
            elif is_active.lower() in ("false", "0", "no"):
                borrowings = [b for b in borrowings if b["actual_return_date"] is not None]

        # Filter by actual_return_date
        actual_return_date = request.query_params.get("actual_return_date")
        if actual_return_date:
            borrowings = [b for b in borrowings if b["actual_return_date"] == actual_return_date]

        result = [BorrowingModel.serialize(b) for b in borrowings]
        return json_response(result)

    elif request.method == "POST":
        data = request.get_json()
        book_id = data.get("book_id")
        expected_return_date = data.get("expected_return_date", "")
        if not book_id:
            return error_response("book_id is required.", 400)
        try:
            borrowing = BorrowingModel.create(
                user_id=request.user["id"],
                book_id=int(book_id),
                expected_return_date=expected_return_date,
            )
            return json_response(BorrowingModel.serialize(borrowing), 201)
        except ValueError as e:
            return error_response(str(e), 400)

    return error_response("Method not allowed.", 405)


@require_auth
def borrowing_detail(request: Request) -> Response:
    borrowing_id = int(request.path_params.get("id", 0))
    borrowing = db.get_borrowing_by_id(borrowing_id)
    if not borrowing:
        return error_response("Borrowing not found.", 404)
    user = request.user
    if not user.get("is_staff") and borrowing["user_id"] != user["id"]:
        return error_response("Permission denied.", 403)
    if request.method == "GET":
        return json_response(BorrowingModel.serialize(borrowing))
    return error_response("Method not allowed.", 405)


@require_auth
def borrowing_return(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)
    borrowing_id = int(request.path_params.get("id", 0))
    try:
        borrowing = BorrowingModel.return_book(
            borrowing_id=borrowing_id,
            user_id=request.user["id"],
            is_staff=request.user.get("is_staff", False),
        )
        return json_response(BorrowingModel.serialize(borrowing))
    except PermissionError as e:
        return error_response(str(e), 403)
    except ValueError as e:
        return error_response(str(e), 400)


# --- Payment Views ---

@require_auth
def payment_list(request: Request) -> Response:
    if request.method != "GET":
        return error_response("Method not allowed.", 405)
    user = request.user
    if user.get("is_staff"):
        payments = db.get_all_payments()
        user_id_filter = request.query_params.get("user_id")
        if user_id_filter:
            try:
                uid = int(user_id_filter)
                payments = [p for p in payments if p["user_id"] == uid]
            except ValueError:
                pass
    else:
        payments = db.get_payments_for_user(user["id"])

    # Filter by status
    status_filter = request.query_params.get("status")
    if status_filter:
        payments = [p for p in payments if p["status"] == status_filter.upper()]

    # Filter by type
    type_filter = request.query_params.get("type")
    if type_filter:
        payments = [p for p in payments if p["type"] == type_filter.upper()]

    result = [PaymentModel.serialize(p) for p in payments]
    return json_response(result)


@require_auth
def payment_detail(request: Request) -> Response:
    payment_id = int(request.path_params.get("id", 0))
    payment = db.get_payment_by_id(payment_id)
    if not payment:
        return error_response("Payment not found.", 404)
    user = request.user
    if not user.get("is_staff") and payment["user_id"] != user["id"]:
        return error_response("Permission denied.", 403)
    if request.method == "GET":
        return json_response(PaymentModel.serialize(payment))
    return error_response("Method not allowed.", 405)


@require_auth
def payment_success(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)
    payment_id = int(request.path_params.get("id", 0))
    try:
        payment = PaymentModel.complete_payment(
            payment_id=payment_id,
            user_id=request.user["id"],
            is_staff=request.user.get("is_staff", False),
        )
        return json_response(PaymentModel.serialize(payment))
    except PermissionError as e:
        return error_response(str(e), 403)
    except ValueError as e:
        return error_response(str(e), 400)


@require_auth
def payment_cancel(request: Request) -> Response:
    if request.method != "POST":
        return error_response("Method not allowed.", 405)
    payment_id = int(request.path_params.get("id", 0))
    payment = db.get_payment_by_id(payment_id)
    if not payment:
        return error_response("Payment not found.", 404)
    user = request.user
    if not user.get("is_staff") and payment["user_id"] != user["id"]:
        return error_response("Permission denied.", 403)
    return json_response({
        "message": "Payment cancelled. You can pay later.",
        "payment": PaymentModel.serialize(payment),
    })


# --- Admin Panel ---

def admin_panel(request: Request) -> Response:
    user = authenticate(request)
    if not user or not user.get("is_staff"):
        return error_response("Admin access required.", 403)
    stats = {
        "total_users": len(db.users),
        "total_books": len(db.books),
        "total_borrowings": len(db.borrowings),
        "total_payments": len(db.payments),
        "active_borrowings": sum(1 for b in db.borrowings.values() if b["actual_return_date"] is None),
        "pending_payments": sum(1 for p in db.payments.values() if p["status"] == PaymentStatus.PENDING),
        "completed_payments": sum(1 for p in db.payments.values() if p["status"] == PaymentStatus.PAID),
    }
    return json_response({"admin_panel": stats})


# --- Swagger Documentation ---

def swagger_doc(request: Request) -> Response:
    doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Service API",
            "version": "1.0.0",
            "description": "API Library service for borrowing books.",
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
                        "email": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "is_staff": {"type": "boolean"},
                    },
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
                    },
                },
                "Borrowing": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "borrow_date": {"type": "string", "format": "date"},
                        "expected_return_date": {"type": "string", "format": "date"},
                        "actual_return_date": {"type": "string", "format": "date", "nullable": True},
                        "book_id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                    },
                },
                "Payment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "status": {"type": "string", "enum": ["PENDING", "PAID"]},
                        "type": {"type": "string", "enum": ["PAYMENT", "FINE"]},
                        "borrowing_id": {"type": "integer"},
                        "session_url": {"type": "string"},
                        "session_id": {"type": "string"},
                        "money_to_pay": {"type": "string"},
                    },
                },
            },
        },
        "security": [{"BearerAuth": []}],
        "paths": {
            "/auth/register/": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Register a new user",
                    "requestBody": {
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
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "User created"}},
                    "security": [],
                }
            },
            "/auth/login/": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Login and get JWT token",
                    "requestBody": {
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
                        }
                    },
                    "responses": {"200": {"description": "JWT token"}},
                    "security": [],
                }
            },
            "/auth/token/refresh/": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Refresh JWT token",
                    "responses": {"200": {"description": "New JWT token"}},
                    "security": [],
                }
            },
            "/users/me/": {
                "get": {
                    "tags": ["users"],
                    "summary": "Get current user profile",
                    "responses": {"200": {"description": "User profile"}},
                },
                "put": {
                    "tags": ["users"],
                    "summary": "Update current user profile",
                    "responses": {"200": {"description": "Updated user"}},
                },
            },
            "/users/": {
                "get": {
                    "tags": ["users"],
                    "summary": "List all users (admin only)",
                    "responses": {"200": {"description": "List of users"}},
                }
            },
            "/books/": {
                "get": {
                    "tags": ["books"],
                    "summary": "List all books",
                    "parameters": [
                        {"name": "title", "in": "query", "schema": {"type": "string"}},
                        {"name": "author", "in": "query", "schema": {"type": "string"}},
                        {"name": "cover", "in": "query", "schema": {"type": "string", "enum": ["HARD", "SOFT"]}},
                    ],
                    "responses": {"200": {"description": "List of books"}},
                    "security": [],
                },
                "post": {
                    "tags": ["books"],
                    "summary": "Create a book (admin only)",
                    "responses": {"201": {"description": "Book created"}},
                },
            },
            "/books/{id}/": {
                "get": {
                    "tags": ["books"],
                    "summary": "Get book details",
                    "responses": {"200": {"description": "Book details"}},
                    "security": [],
                },
                "put": {
                    "tags": ["books"],
                    "summary": "Update book (admin only)",
                    "responses": {"200": {"description": "Updated book"}},
                },
                "delete": {
                    "tags": ["books"],
                    "summary": "Delete book (admin only)",
                    "responses": {"204": {"description": "Book deleted"}},
                },
            },
            "/borrowings/": {
                "get": {
                    "tags": ["borrowings"],
                    "summary": "List borrowings",
                    "parameters": [
                        {"name": "is_active", "in": "query", "schema": {"type": "boolean"}, "description": "Filter by active (not returned) borrowings"},
                        {"name": "actual_return_date", "in": "query", "schema": {"type": "string", "format": "date"}, "description": "Filter by actual return date"},
                        {"name": "user_id", "in": "query", "schema": {"type": "integer"}, "description": "Filter by user (admin only)"},
                    ],
                    "responses": {"200": {"description": "List of borrowings"}},
                },
                "post": {
                    "tags": ["borrowings"],
                    "summary": "Create a borrowing",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["book_id", "expected_return_date"],
                                    "properties": {
                                        "book_id": {"type": "integer"},
                                        "expected_return_date": {"type": "string", "format": "date"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Borrowing created"}},
                },
            },
            "/borrowings/{id}/": {
                "get": {
                    "tags": ["borrowings"],
                    "summary": "Get borrowing details",
                    "responses": {"200": {"description": "Borrowing details"}},
                }
            },
            "/borrowings/{id}/return/": {
                "post": {
                    "tags": ["borrowings"],
                    "summary": "Return a borrowing",
                    "responses": {"200": {"description": "Borrowing returned"}},
                }
            },
            "/payments/": {
                "get": {
                    "tags": ["payments"],
                    "summary": "List payments",
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["PENDING", "PAID"]}},
                        {"name": "type", "in": "query", "schema": {"type": "string", "enum": ["PAYMENT", "FINE"]}},
                        {"name": "user_id", "in": "query", "schema": {"type": "integer"}, "description": "Filter by user (admin only)"},
                    ],
                    "responses": {"200": {"description": "List of payments"}},
                }
            },
            "/payments/{id}/": {
                "get": {
                    "tags": ["payments"],
                    "summary": "Get payment details",
                    "responses": {"200": {"description": "Payment details"}},
                }
            },
            "/payments/{id}/success/": {
                "post": {
                    "tags": ["payments"],
                    "summary": "Complete a payment",
                    "responses": {"200": {"description": "Payment completed"}},
                }
            },
            "/payments/{id}/cancel/": {
                "post": {
                    "tags": ["payments"],
                    "summary": "Cancel a payment session",
                    "responses": {"200": {"description": "Payment cancelled"}},
                }
            },
        },
    }
    return json_response(doc)


def health_check(request: Request) -> Response:
    return json_response({"status": "ok", "service": "Library Service API"})


# ============================================================
# Route Registration
# ============================================================

# Auth
router.add_route("POST", "/api/v1/auth/register/", auth_register)
router.add_route("POST", "/api/v1/auth/login/", auth_login)
router.add_route("POST", "/api/v1/auth/token/refresh/", auth_refresh)

# Users
router.add_route("GET", "/api/v1/users/me/", user_me)
router.add_route("PUT", "/api/v1/users/me/", user_me)
router.add_route("PATCH", "/api/v1/users/me/", user_me)
router.add_route("GET", "/api/v1/users/", user_list)
router.add_route("GET", "/api/v1/users/<id>/", user_detail)
router.add_route("PUT", "/api/v1/users/<id>/", user_detail)
router.add_route("PATCH", "/api/v1/users/<id>/", user_detail)
router.add_route("DELETE", "/api/v1/users/<id>/", user_detail)

# Books
router.add_route("GET", "/api/v1/books/", book_list)
router.add_route("POST", "/api/v1/books/", book_list)
router.add_route("GET", "/api/v1/books/<id>/", book_detail)
router.add_route("PUT", "/api/v1/books/<id>/", book_detail)
router.add_route("PATCH", "/api/v1/books/<id>/", book_detail)
router.add_route("DELETE", "/api/v1/books/<id>/", book_detail)

# Borrowings
router.add_route("GET", "/api/v1/borrowings/", borrowing_list)
router.add_route("POST", "/api/v1/borrowings/", borrowing_list)
router.add_route("GET", "/api/v1/borrowings/<id>/", borrowing_detail)
router.add_route("POST", "/api/v1/borrowings/<id>/return/", borrowing_return)

# Payments
router.add_route("GET", "/api/v1/payments/", payment_list)
router.add_route("GET", "/api/v1/payments/<id>/", payment_detail)
router.add_route("POST", "/api/v1/payments/<id>/success/", payment_success)
router.add_route("POST", "/api/v1/payments/<id>/cancel/", payment_cancel)

# Admin
router.add_route("GET", "/admin/", admin_panel)

# Docs
router.add_route("GET", "/api/v1/doc/swagger/", swagger_doc)

# Health
router.add_route("GET", "/health/", health_check)


# ============================================================
# WSGI Application
# ============================================================

def application(environ: dict, start_response):
    request = Request(environ)
    try:
        handler, params = router.match(request.method, request.path)
        if handler is None:
            # Try OPTIONS for CORS
            if request.method == "OPTIONS":
                response = Response(b"", status=200)
                headers = response.get_headers()
                headers.append(("Access-Control-Allow-Origin", "*"))
                headers.append(("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"))
                headers.append(("Access-Control-Allow-Headers", "Authorization, Content-Type"))
                start_response(response.get_status_string(), headers)
                return [response.body]
            response = error_response("Not found.", 404)
        else:
            request.path_params = params
            response = handler(request)
    except Exception as e:
        response = error_response(f"Internal server error: {str(e)}", 500)

    headers = response.get_headers()
    headers.append(("Access-Control-Allow-Origin", "*"))
    start_response(response.get_status_string(), headers)
    return [response.body]


# ============================================================
# CLI / Server Entry Point
# ============================================================

def run_server(host: str = "0.0.0.0", port: int = 8000):
    from wsgiref.simple_server import make_server, WSGIRequestHandler

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            sys.stdout.write(f"[{self.address_string()}] {format % args}\n")
            sys.stdout.flush()

    print(f"Library Service API running at http://{host}:{port}/")
    print(f"Admin panel: http://{host}:{port}/admin/")
    print(f"Swagger docs: http://{host}:{port}/api/v1/doc/swagger/")
    print(f"Default admin: admin@library.com / admin123")
    print("Press Ctrl+C to stop.")

    with make_server(host, port, application, handler_class=QuietHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def seed_data():
    """Seed some sample data for testing."""
    try:
        # Create sample books
        BookModel.create("The Great Gatsby", "F. Scott Fitzgerald", BookCoverType.SOFT, 5, "1.50")
        BookModel.create("To Kill a Mockingbird", "Harper Lee", BookCoverType.HARD, 3, "2.00")
        BookModel.create("1984", "George Orwell", BookCoverType.SOFT, 7, "1.75")
        BookModel.create("Pride and Prejudice", "Jane Austen", BookCoverType.HARD, 4, "1.25")
        BookModel.create("The Catcher in the Rye", "J.D. Salinger", BookCoverType.SOFT, 2, "1.80")

        # Create sample user
        UserModel.create("user@library.com", "user123", "John", "Doe")
        print("Sample data seeded successfully.")
    except Exception as e:
        print(f"Seeding error: {e}")


# ============================================================
# Tests
# ============================================================

class TestLibraryAPI:
    """Simple test suite for the Library Service API."""

    def __init__(self):
        self.base_url = ""
        self.admin_token = None
        self.user_token = None
        self.test_book_id = None
        self.test_borrowing_id = None
        self.test_payment_id = None
        self.passed = 0
        self.failed = 0

    def make_request(self, method: str, path: str, data: dict = None, token: str = None) -> Response:
        body = json.dumps(data).encode() if data else b""
        environ = {
            "REQUEST_METHOD": method.upper(),
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": __import__("io").BytesIO(body),
        }
        if token:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        request = Request(environ)
        handler, params = router.match(method.upper(), path)
        if handler is None:
            return error_response("Not found.", 404)
        request.path_params = params
        return handler(request)

    def assert_equal(self, name: str, actual, expected):
        if actual == expected:
            print(f"  ✓ {name}")
            self.passed += 1
        else:
            print(f"  ✗ {name}: expected {expected}, got {actual}")
            self.failed += 1

    def assert_status(self, name: str, response: Response, expected_status: int):
        self.assert_equal(name, response.status, expected_status)

    def run_all(self):
        print("\n=== Running Library Service API Tests ===\n")
        self.test_auth()
        self.test_books()
        self.test_borrowings()
        self.test_payments()
        self.test_filtering()
        print(f"\n=== Results: {self.passed} passed, {self.failed} failed ===\n")

    def test_auth(self):
        print("--- Auth Tests ---")

        # Register
        resp = self.make_request("POST", "/api/v1/auth/register/", {
            "email": "testuser@test.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        })
        self.assert_status("Register new user", resp, 201)

        # Register duplicate
        resp = self.make_request("POST", "/api/v1/auth/register/", {
            "email": "testuser@test.com",
            "password": "testpass123",
        })
        self.assert_status("Register duplicate user", resp, 409)

        # Login admin
        resp = self.make_request("POST", "/api/v1/auth/login/", {
            "email": "admin@library.com",
            "password": "admin123",
        })
        self.assert_status("Admin login", resp, 200)
        body = json.loads(resp.body)
        self.admin_token = body.get("access")
        self.assert_equal("Admin token received", bool(self.admin_token), True)

        # Login user
        resp = self.make_request("POST", "/api/v1/auth/login/", {
            "email": "testuser@test.com",
            "password": "testpass123",
        })
        self.assert_status("User login", resp, 200)
        body = json.loads(resp.body)
        self.user_token = body.get("access")

        # Login invalid
        resp = self.make_request("POST", "/api/v1/auth/login/", {
            "email": "wrong@test.com",
            "password": "wrongpass",
        })
        self.assert_status("Invalid login", resp, 401)

        # Get me
        resp = self.make_request("GET", "/api/v1/users/me/", token=self.user_token)
        self.assert_status("Get user profile", resp, 200)

        # Get me without auth
        resp = self.make_request("GET", "/api/v1/users/me/")
        self.assert_status("Get profile without auth", resp, 401)

    def test_books(self):
        print("\n--- Book Tests ---")

        # List books (public)
        resp = self.make_request("GET", "/api/v1/books/")
        self.assert_status("List books (public)", resp, 200)

        # Create book (admin)
        resp = self.make_request("POST", "/api/v1/books/", {
            "title": "Test Book",
            "author": "Test Author",
            "cover": "SOFT",
            "inventory": 5,
            "daily_fee": "1.50",
        }, token=self.admin_token)
        self.assert_status("Create book (admin)", resp, 201)
        body = json.loads(resp.body)
        self.test_book_id = body.get("id")

        # Create book (user - forbidden)
        resp = self.make_request("POST", "/api/v1/books/", {
            "title": "Test Book 2",
            "author": "Author",
            "cover": "HARD",
            "inventory": 3,
            "daily_fee": "2.00",
        }, token=self.user_token)
        self.assert_status("Create book (user - forbidden)", resp, 403)

        # Get book
        resp = self.make_request("GET", f"/api/v1/books/{self.test_book_id}/")
        self.assert_status("Get book detail", resp, 200)

        # Update book
        resp = self.make_request("PUT", f"/api/v1/books/{self.test_book_id}/", {
            "title": "Updated Test Book",
            "author": "Test Author",
            "cover": "HARD",
            "inventory": 10,
            "daily_fee": "2.00",
        }, token=self.admin_token)
        self.assert_status("Update book (admin)", resp, 200)

        # Invalid book
        resp = self.make_request("GET", "/api/v1/books/99999/")
        self.assert_status("Get non-existent book", resp, 404)

    def test_borrowings(self):
        print("\n--- Borrowing Tests ---")

        future_date = (today() + datetime.timedelta(days=7)).isoformat()

        # Create borrowing
        resp = self.make_request("POST", "/api/v1/borrowings/", {
            "book_id": self.test_book_id,
            "expected_return_date": future_date,
        }, token=self.user_token)
        self.assert_status("Create borrowing", resp, 201)
        body = json.loads(resp.body)
        self.test_borrowing_id = body.get("id")

        # Create borrowing with past date
        past_date = (today() - datetime.timedelta(days=1)).isoformat()
        resp = self.make_request("POST", "/api/v1/borrowings/", {
            "book_id": self.test_book_id,
            "expected_return_date": past_date,
        }, token=self.user_token)
        self.assert_status("Create borrowing with past date", resp, 400)

        # List borrowings
        resp = self.make_request("GET", "/api/v1/borrowings/", token=self.user_token)
        self.assert_status("List borrowings", resp, 200)

        # Get borrowing detail
        resp = self.make_request("GET", f"/api/v1/borrowings/{self.test_borrowing_id}/", token=self.user_token)
        self.assert_status("Get borrowing detail", resp, 200)

        # Return borrowing
        resp = self.make_request("POST", f"/api/v1/borrowings/{self.test_borrowing_id}/return/", token=self.user_token)
        self.assert_status("Return borrowing", resp, 200)

        # Return again (should fail)
        resp = self.make_request("POST", f"/api/v1/borrowings/{self.test_borrowing_id}/return/", token=self.user_token)
        self.assert_status("Return already returned borrowing", resp, 400)

    def test_payments(self):
        print("\n--- Payment Tests ---")

        # List payments
        resp = self.make_request("GET", "/api/v1/payments/", token=self.user_token)
        self.assert_status("List payments", resp, 200)
        body = json.loads(resp.body)
        if body:
            self.test_payment_id = body[0]["id"]

            # Get payment detail
            resp = self.make_request("GET", f"/api/v1/payments/{self.test_payment_id}/", token=self.user_token)
            self.assert_status("Get payment detail", resp, 200)

            # Complete payment
            resp = self.make_request("POST", f"/api/v1/payments/{self.test_payment_id}/success/", token=self.user_token)
            self.assert_status("Complete payment", resp, 200)

            # Complete again (should fail)
            resp = self.make_request("POST", f"/api/v1/payments/{self.test_payment_id}/success/", token=self.user_token)
            self.assert_status("Complete already paid payment", resp, 400)

            # Cancel payment
            resp = self.make_request("POST", f"/api/v1/payments/{self.test_payment_id}/cancel/", token=self.user_token)
            self.assert_status("Cancel payment", resp, 200)

    def test_filtering(self):
        print("\n--- Filtering Tests ---")

        # Create a new book for filtering test
        resp = self.make_request("POST", "/api/v1/books/", {
            "title": "Filter Test Book",
            "author": "Filter Author",
            "cover": "HARD",
            "inventory": 3,
            "daily_fee": "1.00",
        }, token=self.admin_token)
        filter_book_id = json.loads(resp.body).get("id")

        # Filter books by title
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/books/",
            "QUERY_STRING": "title=Filter+Test",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": "0",
            "wsgi.input": __import__("io").BytesIO(b""),
        }
        request = Request(environ)
        handler, params = router.match("GET", "/api/v1/books/")
        request.path_params = params
        resp = handler(request)
        self.assert_status("Filter books by title", resp, 200)
        body = json.loads(resp.body)
        self.assert_equal("Filter books result count", len(body) >= 1, True)

        # Filter borrowings by is_active
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/borrowings/",
            "QUERY_STRING": "is_active=false",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": "0",
            "wsgi.input": __import__("io").BytesIO(b""),
            "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
        }
        request = Request(environ)
        handler, params = router.match("GET", "/api/v1/borrowings/")
        request.path_params = params
        resp = handler(request)
        self.assert_status("Filter borrowings by is_active=false", resp, 200)

        # Admin filter borrowings by user_id
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/borrowings/",
            "QUERY_STRING": "user_id=2",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": "0",
            "wsgi.input": __import__("io").BytesIO(b""),
            "HTTP_AUTHORIZATION": f"Bearer {self.admin_token}",
        }
        request = Request(environ)
        handler, params = router.match("GET", "/api/v1/borrowings/")
        request.path_params = params
        resp = handler(request)
        self.assert_status("Admin filter borrowings by user_id", resp, 200)

        # Filter payments by status
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/payments/",
            "QUERY_STRING": "status=PENDING",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": "0",
            "wsgi.input": __import__("io").BytesIO(b""),
            "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
        }
        request = Request(environ)
        handler, params = router.match("GET", "/api/v1/payments/")
        request.path_params = params
        resp = handler(request)
        self.assert_status("Filter payments by status=PENDING", resp, 200)


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    args = sys.argv[1:]

    if "test" in args:
        seed_data()
        tests = TestLibraryAPI()
        tests.run_all()
    elif "seed" in args:
        seed_data()
    else:
        seed_data()
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))
        run_server(host, port)