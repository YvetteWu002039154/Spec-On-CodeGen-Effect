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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

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
        self._lock = threading.Lock()
        self._init_admin()

    def _init_admin(self):
        admin_id = str(uuid.uuid4())
        self.users[admin_id] = {
            "id": admin_id,
            "email": "admin@library.com",
            "password": self._hash_password("admin123"),
            "first_name": "Admin",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _hash_password(self, password: str) -> str:
        salt = "library_salt_2024"
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

    def create_user(self, email: str, password: str, first_name: str, last_name: str, is_admin: bool = False) -> Dict:
        with self._lock:
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "email": email,
                "password": self._hash_password(password),
                "first_name": first_name,
                "last_name": last_name,
                "is_admin": is_admin,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
            }
            self.users[user_id] = user
            return user

    def get_book_by_id(self, book_id: str) -> Optional[Dict]:
        return self.books.get(book_id)

    def create_book(self, title: str, author: str, cover: str, inventory: int, daily_fee: str) -> Dict:
        with self._lock:
            book_id = str(uuid.uuid4())
            book = {
                "id": book_id,
                "title": title,
                "author": author,
                "cover": cover,
                "inventory": inventory,
                "daily_fee": daily_fee,
                "created_at": datetime.utcnow().isoformat(),
            }
            self.books[book_id] = book
            return book

    def update_book(self, book_id: str, data: Dict) -> Optional[Dict]:
        with self._lock:
            if book_id not in self.books:
                return None
            self.books[book_id].update(data)
            return self.books[book_id]

    def delete_book(self, book_id: str) -> bool:
        with self._lock:
            if book_id in self.books:
                del self.books[book_id]
                return True
            return False

    def list_books(self) -> List[Dict]:
        return list(self.books.values())

    def get_borrowing_by_id(self, borrowing_id: str) -> Optional[Dict]:
        return self.borrowings.get(borrowing_id)

    def create_borrowing(self, user_id: str, book_id: str, expected_return_date: str) -> Dict:
        with self._lock:
            borrowing_id = str(uuid.uuid4())
            borrowing = {
                "id": borrowing_id,
                "user_id": user_id,
                "book_id": book_id,
                "borrow_date": date.today().isoformat(),
                "expected_return_date": expected_return_date,
                "actual_return_date": None,
                "status": "ACTIVE",
                "created_at": datetime.utcnow().isoformat(),
            }
            self.borrowings[borrowing_id] = borrowing
            # Decrease book inventory
            if book_id in self.books:
                self.books[book_id]["inventory"] -= 1
            return borrowing

    def return_borrowing(self, borrowing_id: str) -> Optional[Dict]:
        with self._lock:
            if borrowing_id not in self.borrowings:
                return None
            borrowing = self.borrowings[borrowing_id]
            if borrowing["actual_return_date"] is not None:
                return None  # Already returned
            borrowing["actual_return_date"] = date.today().isoformat()
            borrowing["status"] = "RETURNED"
            # Increase book inventory
            book_id = borrowing["book_id"]
            if book_id in self.books:
                self.books[book_id]["inventory"] += 1
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

    def get_payment_by_id(self, payment_id: str) -> Optional[Dict]:
        return self.payments.get(payment_id)

    def create_payment(self, borrowing_id: str, payment_type: str, money_to_pay: str) -> Dict:
        with self._lock:
            payment_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            payment = {
                "id": payment_id,
                "borrowing_id": borrowing_id,
                "status": "PENDING",
                "type": payment_type,
                "session_url": f"http://localhost:8000/api/v1/payments/session/{session_id}",
                "session_id": session_id,
                "money_to_pay": money_to_pay,
                "created_at": datetime.utcnow().isoformat(),
            }
            self.payments[payment_id] = payment
            return payment

    def complete_payment(self, payment_id: str) -> Optional[Dict]:
        with self._lock:
            if payment_id not in self.payments:
                return None
            self.payments[payment_id]["status"] = "PAID"
            return self.payments[payment_id]

    def cancel_payment(self, payment_id: str) -> Optional[Dict]:
        with self._lock:
            if payment_id not in self.payments:
                return None
            self.payments[payment_id]["status"] = "CANCELLED"
            return self.payments[payment_id]

    def list_payments(self, user_id: Optional[str] = None) -> List[Dict]:
        result = list(self.payments.values())
        if user_id:
            # Filter by borrowings belonging to user
            user_borrowing_ids = {
                b["id"] for b in self.borrowings.values() if b["user_id"] == user_id
            }
            result = [p for p in result if p["borrowing_id"] in user_borrowing_ids]
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
    def verify_token(cls, token: str) -> Optional[Dict]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_encoded, payload_encoded, signature_encoded = parts
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                SECRET_KEY.encode(), message.encode(), hashlib.sha256
            ).digest()
            expected_signature_encoded = cls._base64url_encode(expected_signature)
            if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
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
# Business Logic
# ============================================================

class BorrowingService:
    @staticmethod
    def calculate_payment_amount(borrowing: Dict) -> Decimal:
        book = db.get_book_by_id(borrowing["book_id"])
        if not book:
            return Decimal("0")
        daily_fee = Decimal(book["daily_fee"])
        borrow_date = date.fromisoformat(borrowing["borrow_date"])
        expected_return = date.fromisoformat(borrowing["expected_return_date"])
        days = (expected_return - borrow_date).days
        if days <= 0:
            days = 1
        return daily_fee * days

    @staticmethod
    def calculate_fine_amount(borrowing: Dict) -> Decimal:
        book = db.get_book_by_id(borrowing["book_id"])
        if not book:
            return Decimal("0")
        daily_fee = Decimal(book["daily_fee"])
        expected_return = date.fromisoformat(borrowing["expected_return_date"])
        actual_return = date.today()
        if borrowing["actual_return_date"]:
            actual_return = date.fromisoformat(borrowing["actual_return_date"])
        overdue_days = (actual_return - expected_return).days
        if overdue_days <= 0:
            return Decimal("0")
        return daily_fee * FINE_MULTIPLIER * overdue_days

    @staticmethod
    def is_overdue(borrowing: Dict) -> bool:
        expected_return = date.fromisoformat(borrowing["expected_return_date"])
        check_date = date.today()
        if borrowing["actual_return_date"]:
            check_date = date.fromisoformat(borrowing["actual_return_date"])
        return check_date > expected_return


# ============================================================
# HTTP Request Handler
# ============================================================

class LibraryAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def send_json_response(self, status_code: int, data: Any):
        response_body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body)

    def send_error_response(self, status_code: int, message: str):
        self.send_json_response(status_code, {"error": message})

    def get_request_body(self) -> Optional[Dict]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    def get_current_user(self) -> Optional[Dict]:
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        payload = JWT.verify_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user = db.get_user_by_id(payload["user_id"])
        return user

    def require_auth(self):
        user = self.get_current_user()
        if not user:
            self.send_error_response(401, "Authentication required")
            return None
        return user

    def require_admin(self):
        user = self.require_auth()
        if not user:
            return None
        if not user.get("is_admin"):
            self.send_error_response(403, "Admin access required")
            return None
        return user

    def parse_path(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def do_GET(self):
        path, query_params = self.parse_path()
        self.route_request("GET", path, query_params)

    def do_POST(self):
        path, query_params = self.parse_path()
        self.route_request("POST", path, query_params)

    def do_PUT(self):
        path, query_params = self.parse_path()
        self.route_request("PUT", path, query_params)

    def do_PATCH(self):
        path, query_params = self.parse_path()
        self.route_request("PATCH", path, query_params)

    def do_DELETE(self):
        path, query_params = self.parse_path()
        self.route_request("DELETE", path, query_params)

    def route_request(self, method: str, path: str, query_params: Dict):
        # Normalize path
        path = path.rstrip("/")

        # Auth endpoints
        if path == "/api/v1/auth/register" and method == "POST":
            self.handle_register()
        elif path == "/api/v1/auth/login" and method == "POST":
            self.handle_login()
        elif path == "/api/v1/auth/refresh" and method == "POST":
            self.handle_refresh_token()
        elif path == "/api/v1/auth/me" and method == "GET":
            self.handle_get_me()
        elif path == "/api/v1/auth/me" and method == "PUT":
            self.handle_update_me()

        # Book endpoints
        elif path == "/api/v1/books" and method == "GET":
            self.handle_list_books(query_params)
        elif path == "/api/v1/books" and method == "POST":
            self.handle_create_book()
        elif re.match(r"^/api/v1/books/[^/]+$", path) and method == "GET":
            book_id = path.split("/")[-1]
            self.handle_get_book(book_id)
        elif re.match(r"^/api/v1/books/[^/]+$", path) and method == "PUT":
            book_id = path.split("/")[-1]
            self.handle_update_book(book_id)
        elif re.match(r"^/api/v1/books/[^/]+$", path) and method == "PATCH":
            book_id = path.split("/")[-1]
            self.handle_patch_book(book_id)
        elif re.match(r"^/api/v1/books/[^/]+$", path) and method == "DELETE":
            book_id = path.split("/")[-1]
            self.handle_delete_book(book_id)

        # Borrowing endpoints
        elif path == "/api/v1/borrowings" and method == "GET":
            self.handle_list_borrowings(query_params)
        elif path == "/api/v1/borrowings" and method == "POST":
            self.handle_create_borrowing()
        elif re.match(r"^/api/v1/borrowings/[^/]+$", path) and method == "GET":
            borrowing_id = path.split("/")[-1]
            self.handle_get_borrowing(borrowing_id)
        elif re.match(r"^/api/v1/borrowings/[^/]+/return$", path) and method == "POST":
            parts = path.split("/")
            borrowing_id = parts[-2]
            self.handle_return_borrowing(borrowing_id)

        # Payment endpoints
        elif path == "/api/v1/payments" and method == "GET":
            self.handle_list_payments(query_params)
        elif path == "/api/v1/payments" and method == "POST":
            self.handle_create_payment()
        elif re.match(r"^/api/v1/payments/[^/]+$", path) and method == "GET":
            payment_id = path.split("/")[-1]
            self.handle_get_payment(payment_id)
        elif re.match(r"^/api/v1/payments/[^/]+/success$", path) and method == "GET":
            payment_id = path.split("/")[-2]
            self.handle_payment_success(payment_id)
        elif re.match(r"^/api/v1/payments/[^/]+/cancel$", path) and method == "GET":
            payment_id = path.split("/")[-2]
            self.handle_payment_cancel(payment_id)

        # Admin panel
        elif path == "/admin" and method == "GET":
            self.handle_admin_panel()

        # Documentation
        elif path == "/api/v1/doc/swagger" and method == "GET":
            self.handle_swagger_doc()

        # Health check
        elif path == "/api/v1/health" and method == "GET":
            self.send_json_response(200, {"status": "ok", "service": "library-api"})

        else:
            self.send_error_response(404, f"Endpoint not found: {method} {path}")

    # ============================================================
    # Auth Handlers
    # ============================================================

    def handle_register(self):
        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        email = body.get("email", "").strip()
        password = body.get("password", "")
        first_name = body.get("first_name", "").strip()
        last_name = body.get("last_name", "").strip()

        if not email or not password:
            self.send_error_response(400, "Email and password are required")
            return

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            self.send_error_response(400, "Invalid email format")
            return

        if len(password) < 8:
            self.send_error_response(400, "Password must be at least 8 characters")
            return

        if db.get_user_by_email(email):
            self.send_error_response(400, "User with this email already exists")
            return

        user = db.create_user(email, password, first_name, last_name)
        self.send_json_response(201, self._serialize_user(user))

    def handle_login(self):
        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        email = body.get("email", "").strip()
        password = body.get("password", "")

        if not email or not password:
            self.send_error_response(400, "Email and password are required")
            return

        user = db.get_user_by_email(email)
        if not user or not db.verify_password(password, user["password"]):
            self.send_error_response(401, "Invalid credentials")
            return

        access_token = JWT.create_access_token(user["id"])
        refresh_token = JWT.create_refresh_token(user["id"])

        self.send_json_response(200, {
            "access": access_token,
            "refresh": refresh_token,
            "user": self._serialize_user(user),
        })

    def handle_refresh_token(self):
        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        refresh_token = body.get("refresh", "")
        if not refresh_token:
            self.send_error_response(400, "Refresh token is required")
            return

        payload = JWT.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            self.send_error_response(401, "Invalid or expired refresh token")
            return

        user = db.get_user_by_id(payload["user_id"])
        if not user:
            self.send_error_response(401, "User not found")
            return

        access_token = JWT.create_access_token(user["id"])
        self.send_json_response(200, {"access": access_token})

    def handle_get_me(self):
        user = self.require_auth()
        if not user:
            return
        self.send_json_response(200, self._serialize_user(user))

    def handle_update_me(self):
        user = self.require_auth()
        if not user:
            return

        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        update_data = {}
        if "first_name" in body:
            update_data["first_name"] = body["first_name"].strip()
        if "last_name" in body:
            update_data["last_name"] = body["last_name"].strip()
        if "password" in body:
            new_password = body["password"]
            if len(new_password) < 8:
                self.send_error_response(400, "Password must be at least 8 characters")
                return
            update_data["password"] = db._hash_password(new_password)

        db.users[user["id"]].update(update_data)
        self.send_json_response(200, self._serialize_user(db.users[user["id"]]))

    # ============================================================
    # Book Handlers
    # ============================================================

    def handle_list_books(self, query_params: Dict):
        books = db.list_books()

        # Filtering
        title_filter = query_params.get("title", [None])[0]
        author_filter = query_params.get("author", [None])[0]
        cover_filter = query_params.get("cover", [None])[0]

        if title_filter:
            books = [b for b in books if title_filter.lower() in b["title"].lower()]
        if author_filter:
            books = [b for b in books if author_filter.lower() in b["author"].lower()]
        if cover_filter:
            books = [b for b in books if b["cover"].upper() == cover_filter.upper()]

        self.send_json_response(200, [self._serialize_book(b) for b in books])

    def handle_create_book(self):
        user = self.require_admin()
        if not user:
            return

        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        title = body.get("title", "").strip()
        author = body.get("author", "").strip()
        cover = body.get("cover", "").strip().upper()
        inventory = body.get("inventory")
        daily_fee = body.get("daily_fee")

        if not title:
            self.send_error_response(400, "Title is required")
            return
        if not author:
            self.send_error_response(400, "Author is required")
            return
        if cover not in ["HARD", "SOFT"]:
            self.send_error_response(400, "Cover must be HARD or SOFT")
            return
        if inventory is None or not isinstance(inventory, int) or inventory < 0:
            self.send_error_response(400, "Inventory must be a non-negative integer")
            return
        if daily_fee is None:
            self.send_error_response(400, "Daily fee is required")
            return

        try:
            daily_fee_decimal = Decimal(str(daily_fee))
            if daily_fee_decimal < 0:
                raise ValueError
        except Exception:
            self.send_error_response(400, "Daily fee must be a non-negative number")
            return

        book = db.create_book(title, author, cover, inventory, str(daily_fee_decimal))
        self.send_json_response(201, self._serialize_book(book))

    def handle_get_book(self, book_id: str):
        book = db.get_book_by_id(book_id)
        if not book:
            self.send_error_response(404, "Book not found")
            return
        self.send_json_response(200, self._serialize_book(book))

    def handle_update_book(self, book_id: str):
        user = self.require_admin()
        if not user:
            return

        book = db.get_book_by_id(book_id)
        if not book:
            self.send_error_response(404, "Book not found")
            return

        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        update_data = {}
        if "title" in body:
            update_data["title"] = body["title"].strip()
        if "author" in body:
            update_data["author"] = body["author"].strip()
        if "cover" in body:
            cover = body["cover"].strip().upper()
            if cover not in ["HARD", "SOFT"]:
                self.send_error_response(400, "Cover must be HARD or SOFT")
                return
            update_data["cover"] = cover
        if "inventory" in body:
            inventory = body["inventory"]
            if not isinstance(inventory, int) or inventory < 0:
                self.send_error_response(400, "Inventory must be a non-negative integer")
                return
            update_data["inventory"] = inventory
        if "daily_fee" in body:
            try:
                daily_fee = Decimal(str(body["daily_fee"]))
                if daily_fee < 0:
                    raise ValueError
                update_data["daily_fee"] = str(daily_fee)
            except Exception:
                self.send_error_response(400, "Daily fee must be a non-negative number")
                return

        updated_book = db.update_book(book_id, update_data)
        self.send_json_response(200, self._serialize_book(updated_book))

    def handle_patch_book(self, book_id: str):
        self.handle_update_book(book_id)

    def handle_delete_book(self, book_id: str):
        user = self.require_admin()
        if not user:
            return

        book = db.get_book_by_id(book_id)
        if not book:
            self.send_error_response(404, "Book not found")
            return

        db.delete_book(book_id)
        self.send_json_response(204, {})

    # ============================================================
    # Borrowing Handlers
    # ============================================================

    def handle_list_borrowings(self, query_params: Dict):
        user = self.require_auth()
        if not user:
            return

        # Filtering parameters
        is_active_param = query_params.get("is_active", [None])[0]
        user_id_param = query_params.get("user_id", [None])[0]

        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")

        # Non-admin users can only see their own borrowings
        filter_user_id = user["id"]
        if user.get("is_admin"):
            filter_user_id = user_id_param  # Can filter by any user or None for all

        borrowings = db.list_borrowings(user_id=filter_user_id, is_active=is_active)

        # Additional filtering by actual_return_date
        actual_return_date_param = query_params.get("actual_return_date", [None])[0]
        if actual_return_date_param:
            if actual_return_date_param.lower() == "null":
                borrowings = [b for b in borrowings if b["actual_return_date"] is None]
            else:
                borrowings = [b for b in borrowings if b["actual_return_date"] == actual_return_date_param]

        self.send_json_response(200, [self._serialize_borrowing(b) for b in borrowings])

    def handle_create_borrowing(self):
        user = self.require_auth()
        if not user:
            return

        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        book_id = body.get("book_id", "").strip()
        expected_return_date = body.get("expected_return_date", "").strip()

        if not book_id:
            self.send_error_response(400, "book_id is required")
            return
        if not expected_return_date:
            self.send_error_response(400, "expected_return_date is required")
            return

        # Validate date format
        try:
            return_date = date.fromisoformat(expected_return_date)
            if return_date <= date.today():
                self.send_error_response(400, "expected_return_date must be in the future")
                return
        except ValueError:
            self.send_error_response(400, "expected_return_date must be in YYYY-MM-DD format")
            return

        book = db.get_book_by_id(book_id)
        if not book:
            self.send_error_response(404, "Book not found")
            return

        if book["inventory"] <= 0:
            self.send_error_response(400, "Book is not available (inventory is 0)")
            return

        # Check if user has pending payments
        user_payments = db.list_payments(user_id=user["id"])
        pending_payments = [p for p in user_payments if p["status"] == "PENDING"]
        if pending_payments:
            self.send_error_response(400, "You have pending payments. Please complete them before borrowing.")
            return

        borrowing = db.create_borrowing(user["id"], book_id, expected_return_date)

        # Create payment for the borrowing
        amount = BorrowingService.calculate_payment_amount(borrowing)
        db.create_payment(borrowing["id"], "PAYMENT", str(amount))

        self.send_json_response(201, self._serialize_borrowing(borrowing))

    def handle_get_borrowing(self, borrowing_id: str):
        user = self.require_auth()
        if not user:
            return

        borrowing = db.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            self.send_error_response(404, "Borrowing not found")
            return

        # Non-admin users can only see their own borrowings
        if not user.get("is_admin") and borrowing["user_id"] != user["id"]:
            self.send_error_response(403, "Access denied")
            return

        self.send_json_response(200, self._serialize_borrowing(borrowing))

    def handle_return_borrowing(self, borrowing_id: str):
        user = self.require_auth()
        if not user:
            return

        borrowing = db.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            self.send_error_response(404, "Borrowing not found")
            return

        # Non-admin users can only return their own borrowings
        if not user.get("is_admin") and borrowing["user_id"] != user["id"]:
            self.send_error_response(403, "Access denied")
            return

        if borrowing["actual_return_date"] is not None:
            self.send_error_response(400, "Borrowing has already been returned")
            return

        returned_borrowing = db.return_borrowing(borrowing_id)

        # Check if overdue and create fine payment
        if BorrowingService.is_overdue(returned_borrowing):
            fine_amount = BorrowingService.calculate_fine_amount(returned_borrowing)
            if fine_amount > 0:
                db.create_payment(borrowing_id, "FINE", str(fine_amount))

        self.send_json_response(200, {
            "borrowing": self._serialize_borrowing(returned_borrowing),
            "message": "Book returned successfully",
            "is_overdue": BorrowingService.is_overdue(returned_borrowing),
        })

    # ============================================================
    # Payment Handlers
    # ============================================================

    def handle_list_payments(self, query_params: Dict):
        user = self.require_auth()
        if not user:
            return

        user_id_param = query_params.get("user_id", [None])[0]
        status_filter = query_params.get("status", [None])[0]
        type_filter = query_params.get("type", [None])[0]

        if user.get("is_admin"):
            filter_user_id = user_id_param
        else:
            filter_user_id = user["id"]

        payments = db.list_payments(user_id=filter_user_id)

        if status_filter:
            payments = [p for p in payments if p["status"].upper() == status_filter.upper()]
        if type_filter:
            payments = [p for p in payments if p["type"].upper() == type_filter.upper()]

        self.send_json_response(200, [self._serialize_payment(p) for p in payments])

    def handle_create_payment(self):
        user = self.require_auth()
        if not user:
            return

        body = self.get_request_body()
        if body is None:
            self.send_error_response(400, "Invalid JSON body")
            return

        borrowing_id = body.get("borrowing_id", "").strip()
        payment_type = body.get("type", "PAYMENT").strip().upper()

        if not borrowing_id:
            self.send_error_response(400, "borrowing_id is required")
            return

        if payment_type not in ["PAYMENT", "FINE"]:
            self.send_error_response(400, "type must be PAYMENT or FINE")
            return

        borrowing = db.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            self.send_error_response(404, "Borrowing not found")
            return

        if not user.get("is_admin") and borrowing["user_id"] != user["id"]:
            self.send_error_response(403, "Access denied")
            return

        if payment_type == "PAYMENT":
            amount = BorrowingService.calculate_payment_amount(borrowing)
        else:
            amount = BorrowingService.calculate_fine_amount(borrowing)

        payment = db.create_payment(borrowing_id, payment_type, str(amount))
        self.send_json_response(201, self._serialize_payment(payment))

    def handle_get_payment(self, payment_id: str):
        user = self.require_auth()
        if not user:
            return

        payment = db.get_payment_by_id(payment_id)
        if not payment:
            self.send_error_response(404, "Payment not found")
            return

        # Check access
        if not user.get("is_admin"):
            borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
            if not borrowing or borrowing["user_id"] != user["id"]:
                self.send_error_response(403, "Access denied")
                return

        self.send_json_response(200, self._serialize_payment(payment))

    def handle_payment_success(self, payment_id: str):
        user = self.require_auth()
        if not user:
            return

        payment = db.get_payment_by_id(payment_id)
        if not payment:
            self.send_error_response(404, "Payment not found")
            return

        if not user.get("is_admin"):
            borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
            if not borrowing or borrowing["user_id"] != user["id"]:
                self.send_error_response(403, "Access denied")
                return

        if payment["status"] == "PAID":
            self.send_json_response(200, {
                "message": "Payment already completed",
                "payment": self._serialize_payment(payment),
            })
            return

        completed_payment = db.complete_payment(payment_id)
        self.send_json_response(200, {
            "message": "Payment completed successfully",
            "payment": self._serialize_payment(completed_payment),
        })

    def handle_payment_cancel(self, payment_id: str):
        user = self.require_auth()
        if not user:
            return

        payment = db.get_payment_by_id(payment_id)
        if not payment:
            self.send_error_response(404, "Payment not found")
            return

        if not user.get("is_admin"):
            borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
            if not borrowing or borrowing["user_id"] != user["id"]:
                self.send_error_response(403, "Access denied")
                return

        self.send_json_response(200, {
            "message": "Payment can be completed later. The session is available for 24 hours.",
            "payment": self._serialize_payment(payment),
        })

    # ============================================================
    # Admin Panel Handler
    # ============================================================

    def handle_admin_panel(self):
        user = self.require_admin()
        if not user:
            return

        stats = {
            "total_users": len(db.users),
            "total_books": len(db.books),
            "total_borrowings": len(db.borrowings),
            "active_borrowings": len([b for b in db.borrowings.values() if b["actual_return_date"] is None]),
            "total_payments": len(db.payments),
            "pending_payments": len([p for p in db.payments.values() if p["status"] == "PENDING"]),
            "paid_payments": len([p for p in db.payments.values() if p["status"] == "PAID"]),
            "users": [self._serialize_user(u) for u in db.users.values()],
            "books": [self._serialize_book(b) for b in db.books.values()],
            "borrowings": [self._serialize_borrowing(b) for b in db.borrowings.values()],
            "payments": [self._serialize_payment(p) for p in db.payments.values()],
        }
        self.send_json_response(200, stats)

    # ============================================================
    # Swagger Documentation Handler
    # ============================================================

    def handle_swagger_doc(self):
        swagger_doc = {
            "openapi": "3.0.0",
            "info": {
                "title": "Library Service API",
                "version": "1.0.0",
                "description": "API Library service for borrowing books with JWT authentication",
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
                            "is_admin": {"type": "boolean"},
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
                            "user_id": {"type": "string"},
                            "book_id": {"type": "string"},
                            "borrow_date": {"type": "string", "format": "date"},
                            "expected_return_date": {"type": "string", "format": "date"},
                            "actual_return_date": {"type": "string", "format": "date", "nullable": True},
                            "status": {"type": "string", "enum": ["ACTIVE", "RETURNED"]},
                        },
                    },
                    "Payment": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "borrowing_id": {"type": "string"},
                            "status": {"type": "string", "enum": ["PENDING", "PAID", "CANCELLED"]},
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
                "/api/v1/auth/register": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Register a new user",
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
                                            "first_name": {"type": "string"},
                                            "last_name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {"description": "User created successfully"},
                            "400": {"description": "Validation error"},
                        },
                    }
                },
                "/api/v1/auth/login": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Login and get JWT tokens",
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
                            "200": {"description": "Login successful, returns access and refresh tokens"},
                            "401": {"description": "Invalid credentials"},
                        },
                    }
                },
                "/api/v1/auth/refresh": {
                    "post": {
                        "tags": ["Authentication"],
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
                            "200": {"description": "New access token"},
                            "401": {"description": "Invalid refresh token"},
                        },
                    }
                },
                "/api/v1/auth/me": {
                    "get": {
                        "tags": ["Authentication"],
                        "summary": "Get current user profile",
                        "responses": {
                            "200": {"description": "User profile"},
                            "401": {"description": "Not authenticated"},
                        },
                    },
                    "put": {
                        "tags": ["Authentication"],
                        "summary": "Update current user profile",
                        "responses": {
                            "200": {"description": "Updated user profile"},
                            "401": {"description": "Not authenticated"},
                        },
                    },
                },
                "/api/v1/books": {
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
                            "403": {"description": "Admin access required"},
                        },
                    },
                },
                "/api/v1/books/{id}": {
                    "get": {
                        "tags": ["Books"],
                        "summary": "Get book by ID",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Book details"},
                            "404": {"description": "Book not found"},
                        },
                    },
                    "put": {
                        "tags": ["Books"],
                        "summary": "Update book (Admin only)",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Updated book"},
                            "403": {"description": "Admin access required"},
                            "404": {"description": "Book not found"},
                        },
                    },
                    "delete": {
                        "tags": ["Books"],
                        "summary": "Delete book (Admin only)",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "204": {"description": "Book deleted"},
                            "403": {"description": "Admin access required"},
                            "404": {"description": "Book not found"},
                        },
                    },
                },
                "/api/v1/borrowings": {
                    "get": {
                        "tags": ["Borrowings"],
                        "summary": "List borrowings",
                        "parameters": [
                            {"name": "is_active", "in": "query", "schema": {"type": "boolean"},
                             "description": "Filter by active status (no actual return date)"},
                            {"name": "user_id", "in": "query", "schema": {"type": "string"},
                             "description": "Filter by user ID (Admin only)"},
                            {"name": "actual_return_date", "in": "query", "schema": {"type": "string"},
                             "description": "Filter by actual return date (use 'null' for not returned)"},
                        ],
                        "responses": {"200": {"description": "List of borrowings"}},
                    },
                    "post": {
                        "tags": ["Borrowings"],
                        "summary": "Create a new borrowing",
                        "responses": {
                            "201": {"description": "Borrowing created"},
                            "400": {"description": "Validation error or book not available"},
                        },
                    },
                },
                "/api/v1/borrowings/{id}": {
                    "get": {
                        "tags": ["Borrowings"],
                        "summary": "Get borrowing by ID",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Borrowing details"},
                            "404": {"description": "Borrowing not found"},
                        },
                    }
                },
                "/api/v1/borrowings/{id}/return": {
                    "post": {
                        "tags": ["Borrowings"],
                        "summary": "Return a borrowed book",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Book returned successfully"},
                            "400": {"description": "Already returned"},
                            "404": {"description": "Borrowing not found"},
                        },
                    }
                },
                "/api/v1/payments": {
                    "get": {
                        "tags": ["Payments"],
                        "summary": "List payments",
                        "parameters": [
                            {"name": "user_id", "in": "query", "schema": {"type": "string"},
                             "description": "Filter by user ID (Admin only)"},
                            {"name": "status", "in": "query",
                             "schema": {"type": "string", "enum": ["PENDING", "PAID", "CANCELLED"]}},
                            {"name": "type", "in": "query",
                             "schema": {"type": "string", "enum": ["PAYMENT", "FINE"]}},
                        ],
                        "responses": {"200": {"description": "List of payments"}},
                    },
                    "post": {
                        "tags": ["Payments"],
                        "summary": "Create a payment",
                        "responses": {
                            "201": {"description": "Payment created"},
                            "400": {"description": "Validation error"},
                        },
                    },
                },
                "/api/v1/payments/{id}": {
                    "get": {
                        "tags": ["Payments"],
                        "summary": "Get payment by ID",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Payment details"},
                            "404": {"description": "Payment not found"},
                        },
                    }
                },
                "/api/v1/payments/{id}/success": {
                    "get": {
                        "tags": ["Payments"],
                        "summary": "Complete a payment (success callback)",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Payment completed"},
                            "404": {"description": "Payment not found"},
                        },
                    }
                },
                "/api/v1/payments/{id}/cancel": {
                    "get": {
                        "tags": ["Payments"],
                        "summary": "Cancel a payment (cancel callback)",
                        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Payment cancellation acknowledged"},
                            "404": {"description": "Payment not found"},
                        },
                    }
                },
                "/admin": {
                    "get": {
                        "tags": ["Admin"],
                        "summary": "Admin panel - system statistics (Admin only)",
                        "responses": {
                            "200": {"description": "System statistics and data"},
                            "403": {"description": "Admin access required"},
                        },
                    }
                },
            },
        }
        self.send_json_response(200, swagger_doc)

    # ============================================================
    # Serializers
    # ============================================================

    def _serialize_user(self, user: Dict) -> Dict:
        return {
            "id": user["id"],
            "email": user["email"],
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "is_admin": user.get("is_admin", False),
            "is_active": user.get("is_active", True),
            "created_at": user.get("created_at"),
        }

    def _serialize_book(self, book: Dict) -> Dict:
        return {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "cover": book["cover"],
            "inventory": book["inventory"],
            "daily_fee": book["daily_fee"],
            "created_at": book.get("created_at"),
        }

    def _serialize_borrowing(self, borrowing: Dict) -> Dict:
        book = db.get_book_by_id(borrowing["book_id"])
        user = db.get_user_by_id(borrowing["user_id"])
        payments = db.get_payments_for_borrowing(borrowing["id"])

        return {
            "id": borrowing["id"],
            "user_id": borrowing["user_id"],
            "user_email": user["email"] if user else None,
            "book_id": borrowing["book_id"],
            "book_title": book["title"] if book else None,
            "borrow_date": borrowing["borrow_date"],
            "expected_return_date": borrowing["expected_return_date"],
            "actual_return_date": borrowing["actual_return_date"],
            "status": borrowing["status"],
            "is_overdue": BorrowingService.is_overdue(borrowing),
            "payments": [self._serialize_payment(p) for p in payments],
            "created_at": borrowing.get("created_at"),
        }

    def _serialize_payment(self, payment: Dict) -> Dict:
        borrowing = db.get_borrowing_by_id(payment["borrowing_id"])
        return {
            "id": payment["id"],
            "borrowing_id": payment["borrowing_id"],
            "status": payment["status"],
            "type": payment["type"],
            "session_url": payment["session_url"],
            "session_id": payment["session_id"],
            "money_to_pay": payment["money_to_pay"],
            "created_at": payment.get("created_at"),
        }


# ============================================================
# Server
# ============================================================

class LibraryServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.server = None

    def start(self):
        self.server = HTTPServer((self.host, self.port), LibraryAPIHandler)
        print(f"Library Service API running on http://{self.host}:{self.port}")
        print(f"Admin panel: http://{self.host}:{self.port}/admin")
        print(f"API Documentation: http://{self.host}:{self.port}/api/v1/doc/swagger")
        print(f"Default admin credentials: admin@library.com / admin123")
        print("Press Ctrl+C to stop the server")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
            self.server.server_close()

    def start_background(self):
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        return thread


# ============================================================
# CLI / Demo
# ============================================================

def run_demo():
    """Run a quick demo to verify the API works"""
    import urllib.request
    import time

    server = LibraryServer(port=8001)
    server.server = HTTPServer(("0.0.0.0", 8001), LibraryAPIHandler)
    thread = server.start_background()
    time.sleep(0.5)

    base_url = "http://localhost:8001"

    def api_call(method, path, data=None, token=None):
        url = f"{base_url}{path}"
        body = json.dumps(data).encode() if data else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    print("\n=== Library Service API Demo ===\n")

    # Register user
    status, resp = api_call("POST", "/api/v1/auth/register", {
        "email": "john@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
    })
    print(f"Register user: {status} - {resp.get('email')}")

    # Login as admin
    status, resp = api_call("POST", "/api/v1/auth/login", {
        "email": "admin@library.com",
        "password": "admin123",
    })
    admin_token = resp.get("access")
    print(f"Admin login: {status} - token obtained: {bool(admin_token)}")

    # Login as user
    status, resp = api_call("POST", "/api/v1/auth/login", {
        "email": "john@example.com",
        "password": "password123",
    })
    user_token = resp.get("access")
    print(f"User login: {status} - token obtained: {bool(user_token)}")

    # Create book (admin)
    status, resp = api_call("POST", "/api/v1/books", {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "cover": "HARD",
        "inventory": 5,
        "daily_fee": "1.50",
    }, admin_token)
    book_id = resp.get("id")
    print(f"Create book: {status} - {resp.get('title')}")

    # List books
    status, resp = api_call("GET", "/api/v1/books")
    print(f"List books: {status} - count: {len(resp)}")

    # Create borrowing
    future_date = (date.today() + timedelta(days=7)).isoformat()
    status, resp = api_call("POST", "/api/v1/borrowings", {
        "book_id": book_id,
        "expected_return_date": future_date,
    }, user_token)
    borrowing_id = resp.get("id")
    print(f"Create borrowing: {status} - {resp.get('status')}")

    # List borrowings
    status, resp = api_call("GET", "/api/v1/borrowings", token=user_token)
    print(f"List borrowings: {status} - count: {len(resp)}")

    # List payments
    status, resp = api_call("GET", "/api/v1/payments", token=user_token)
    print(f"List payments: {status} - count: {len(resp)}")
    if resp:
        payment_id = resp[0]["id"]
        # Complete payment
        status, resp = api_call("GET", f"/api/v1/payments/{payment_id}/success", token=user_token)
        print(f"Complete payment: {status} - {resp.get('message')}")

    # Return borrowing
    status, resp = api_call("POST", f"/api/v1/borrowings/{borrowing_id}/return", token=user_token)
    print(f"Return borrowing: {status} - {resp.get('message')}")

    # Admin panel
    status, resp = api_call("GET", "/admin", token=admin_token)
    print(f"Admin panel: {status} - total_users: {resp.get('total_users')}, total_books: {resp.get('total_books')}")

    # Swagger docs
    status, resp = api_call("GET", "/api/v1/doc/swagger")
    print(f"Swagger docs: {status} - paths count: {len(resp.get('paths', {}))}")

    print("\n=== Demo Complete ===")
    server.server.server_close()


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))
        server = LibraryServer(host=host, port=port)
        server.start()