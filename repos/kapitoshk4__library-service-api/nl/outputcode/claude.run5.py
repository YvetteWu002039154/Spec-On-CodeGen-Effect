#!/usr/bin/env python3
"""
Library Service API - Complete Implementation
JWT authentication, book management, borrowings, and payments
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
DAILY_FEE_MULTIPLIER = Decimal("1.5")  # Fine multiplier for overdue books

# ============================================================
# Database (In-memory for standalone implementation)
# ============================================================

class Database:
    """In-memory database for the library service"""
    
    def __init__(self):
        self.users: Dict[int, Dict] = {}
        self.books: Dict[int, Dict] = {}
        self.borrowings: Dict[int, Dict] = {}
        self.payments: Dict[int, Dict] = {}
        self._user_counter = 1
        self._book_counter = 1
        self._borrowing_counter = 1
        self._payment_counter = 1
        
        # Create default admin user
        self._create_admin()
    
    def _create_admin(self):
        admin = {
            "id": self._user_counter,
            "email": "admin@library.com",
            "password": self._hash_password("admin123"),
            "first_name": "Admin",
            "last_name": "User",
            "is_staff": True,
            "is_active": True,
            "created_at": datetime.datetime.utcnow().isoformat()
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
                raise ValueError(f"User with email {email} already exists")
        
        user = {
            "id": self._user_counter,
            "email": email,
            "password": self._hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": is_staff,
            "is_active": True,
            "created_at": datetime.datetime.utcnow().isoformat()
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
        if user_id not in self.users:
            return None
        if "password" in data:
            data["password"] = self._hash_password(data["password"])
        self.users[user_id].update(data)
        return self.users[user_id]
    
    # Book operations
    def create_book(self, title: str, author: str, cover: str, inventory: int, daily_fee: Decimal) -> Dict:
        book = {
            "id": self._book_counter,
            "title": title,
            "author": author,
            "cover": cover,
            "inventory": inventory,
            "daily_fee": str(daily_fee),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        self.books[self._book_counter] = book
        self._book_counter += 1
        return book
    
    def get_book(self, book_id: int) -> Optional[Dict]:
        return self.books.get(book_id)
    
    def get_all_books(self) -> List[Dict]:
        return list(self.books.values())
    
    def update_book(self, book_id: int, data: Dict) -> Optional[Dict]:
        if book_id not in self.books:
            return None
        self.books[book_id].update(data)
        return self.books[book_id]
    
    def delete_book(self, book_id: int) -> bool:
        if book_id in self.books:
            del self.books[book_id]
            return True
        return False
    
    # Borrowing operations
    def create_borrowing(self, user_id: int, book_id: int, expected_return_date: str) -> Dict:
        borrowing = {
            "id": self._borrowing_counter,
            "user_id": user_id,
            "book_id": book_id,
            "borrow_date": datetime.date.today().isoformat(),
            "expected_return_date": expected_return_date,
            "actual_return_date": None,
            "status": "ACTIVE",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        self.borrowings[self._borrowing_counter] = borrowing
        self._borrowing_counter += 1
        return borrowing
    
    def get_borrowing(self, borrowing_id: int) -> Optional[Dict]:
        return self.borrowings.get(borrowing_id)
    
    def get_all_borrowings(self) -> List[Dict]:
        return list(self.borrowings.values())
    
    def get_user_borrowings(self, user_id: int) -> List[Dict]:
        return [b for b in self.borrowings.values() if b["user_id"] == user_id]
    
    def update_borrowing(self, borrowing_id: int, data: Dict) -> Optional[Dict]:
        if borrowing_id not in self.borrowings:
            return None
        self.borrowings[borrowing_id].update(data)
        return self.borrowings[borrowing_id]
    
    # Payment operations
    def create_payment(self, borrowing_id: int, payment_type: str, money_to_pay: Decimal, session_url: str, session_id: str) -> Dict:
        payment = {
            "id": self._payment_counter,
            "borrowing_id": borrowing_id,
            "status": "PENDING",
            "type": payment_type,
            "session_url": session_url,
            "session_id": session_id,
            "money_to_pay": str(money_to_pay),
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        self.payments[self._payment_counter] = payment
        self._payment_counter += 1
        return payment
    
    def get_payment(self, payment_id: int) -> Optional[Dict]:
        return self.payments.get(payment_id)
    
    def get_all_payments(self) -> List[Dict]:
        return list(self.payments.values())
    
    def get_user_payments(self, user_id: int) -> List[Dict]:
        user_borrowing_ids = {b["id"] for b in self.get_user_borrowings(user_id)}
        return [p for p in self.payments.values() if p["borrowing_id"] in user_borrowing_ids]
    
    def get_borrowing_payments(self, borrowing_id: int) -> List[Dict]:
        return [p for p in self.payments.values() if p["borrowing_id"] == borrowing_id]
    
    def update_payment(self, payment_id: int, data: Dict) -> Optional[Dict]:
        if payment_id not in self.payments:
            return None
        self.payments[payment_id].update(data)
        return self.payments[payment_id]


# Global database instance
db = Database()


# ============================================================
# JWT Implementation
# ============================================================

class JWT:
    """Simple JWT implementation"""
    
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    @classmethod
    def create_token(cls, payload: Dict) -> str:
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        header_encoded = cls._base64url_encode(json.dumps(header).encode())
        payload_encoded = cls._base64url_encode(json.dumps(payload).encode())
        
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_encoded = cls._base64url_encode(signature)
        
        return f"{message}.{signature_encoded}"
    
    @classmethod
    def decode_token(cls, token: str) -> Optional[Dict]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_encoded, payload_encoded, signature_encoded = parts
            message = f"{header_encoded}.{payload_encoded}"
            
            expected_signature = hmac.new(
                SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = cls._base64url_encode(expected_signature)
            
            if not hmac.compare_digest(signature_encoded, expected_signature_encoded):
                return None
            
            payload = json.loads(cls._base64url_decode(payload_encoded))
            
            # Check expiry
            if "exp" in payload:
                exp = datetime.datetime.fromtimestamp(payload["exp"])
                if datetime.datetime.utcnow() > exp:
                    return None
            
            return payload
        except Exception:
            return None
    
    @classmethod
    def create_access_token(cls, user_id: int) -> str:
        exp = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS)
        payload = {
            "user_id": user_id,
            "type": "access",
            "exp": exp.timestamp(),
            "iat": datetime.datetime.utcnow().timestamp()
        }
        return cls.create_token(payload)
    
    @classmethod
    def create_refresh_token(cls, user_id: int) -> str:
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": exp.timestamp(),
            "iat": datetime.datetime.utcnow().timestamp()
        }
        return cls.create_token(payload)


# ============================================================
# Models / Schemas
# ============================================================

class BookCover:
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


class BorrowingStatus:
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    CHOICES = [ACTIVE, RETURNED]


# ============================================================
# Business Logic Services
# ============================================================

class BookService:
    """Service for book management"""
    
    @staticmethod
    def validate_book_data(data: Dict) -> List[str]:
        errors = []
        if not data.get("title"):
            errors.append("Title is required")
        if not data.get("author"):
            errors.append("Author is required")
        if data.get("cover") not in BookCover.CHOICES:
            errors.append(f"Cover must be one of {BookCover.CHOICES}")
        if not isinstance(data.get("inventory"), int) or data.get("inventory", -1) < 0:
            errors.append("Inventory must be a non-negative integer")
        try:
            fee = Decimal(str(data.get("daily_fee", 0)))
            if fee <= 0:
                errors.append("Daily fee must be positive")
        except Exception:
            errors.append("Daily fee must be a valid decimal number")
        return errors
    
    @staticmethod
    def create_book(data: Dict) -> Dict:
        return db.create_book(
            title=data["title"],
            author=data["author"],
            cover=data["cover"],
            inventory=data["inventory"],
            daily_fee=Decimal(str(data["daily_fee"]))
        )
    
    @staticmethod
    def get_book(book_id: int) -> Optional[Dict]:
        return db.get_book(book_id)
    
    @staticmethod
    def get_all_books() -> List[Dict]:
        return db.get_all_books()
    
    @staticmethod
    def update_book(book_id: int, data: Dict) -> Optional[Dict]:
        return db.update_book(book_id, data)
    
    @staticmethod
    def delete_book(book_id: int) -> bool:
        return db.delete_book(book_id)
    
    @staticmethod
    def format_book(book: Dict) -> Dict:
        return {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "cover": book["cover"],
            "inventory": book["inventory"],
            "daily_fee": book["daily_fee"]
        }


class BorrowingService:
    """Service for borrowing management"""
    
    @staticmethod
    def validate_borrowing_data(data: Dict) -> List[str]:
        errors = []
        if not data.get("book_id"):
            errors.append("Book ID is required")
        if not data.get("expected_return_date"):
            errors.append("Expected return date is required")
        else:
            try:
                expected = datetime.date.fromisoformat(data["expected_return_date"])
                if expected <= datetime.date.today():
                    errors.append("Expected return date must be in the future")
            except ValueError:
                errors.append("Expected return date must be in YYYY-MM-DD format")
        return errors
    
    @staticmethod
    def create_borrowing(user_id: int, data: Dict) -> Dict:
        book_id = data["book_id"]
        book = db.get_book(book_id)
        
        if not book:
            raise ValueError(f"Book with id {book_id} not found")
        
        if book["inventory"] <= 0:
            raise ValueError("Book is not available (inventory is 0)")
        
        # Check for pending payments
        user_borrowings = db.get_user_borrowings(user_id)
        for borrowing in user_borrowings:
            if borrowing["status"] == BorrowingStatus.ACTIVE:
                payments = db.get_borrowing_payments(borrowing["id"])
                for payment in payments:
                    if payment["status"] == PaymentStatus.PENDING:
                        raise ValueError("You have pending payments. Please pay them before borrowing.")
        
        # Decrease inventory
        db.update_book(book_id, {"inventory": book["inventory"] - 1})
        
        # Create borrowing
        borrowing = db.create_borrowing(
            user_id=user_id,
            book_id=book_id,
            expected_return_date=data["expected_return_date"]
        )
        
        # Create payment
        borrow_date = datetime.date.fromisoformat(borrowing["borrow_date"])
        expected_return = datetime.date.fromisoformat(borrowing["expected_return_date"])
        days = (expected_return - borrow_date).days
        daily_fee = Decimal(book["daily_fee"])
        money_to_pay = daily_fee * days
        
        session_id = str(uuid.uuid4())
        session_url = f"http://localhost:8000/api/v1/payments/success/?session_id={session_id}"
        
        db.create_payment(
            borrowing_id=borrowing["id"],
            payment_type=PaymentType.PAYMENT,
            money_to_pay=money_to_pay,
            session_url=session_url,
            session_id=session_id
        )
        
        return borrowing
    
    @staticmethod
    def return_book(borrowing_id: int, user_id: int, is_staff: bool) -> Dict:
        borrowing = db.get_borrowing(borrowing_id)
        
        if not borrowing:
            raise ValueError(f"Borrowing with id {borrowing_id} not found")
        
        if not is_staff and borrowing["user_id"] != user_id:
            raise PermissionError("You don't have permission to return this borrowing")
        
        if borrowing["status"] == BorrowingStatus.RETURNED:
            raise ValueError("This book has already been returned")
        
        actual_return_date = datetime.date.today()
        expected_return_date = datetime.date.fromisoformat(borrowing["expected_return_date"])
        
        # Update borrowing
        db.update_borrowing(borrowing_id, {
            "actual_return_date": actual_return_date.isoformat(),
            "status": BorrowingStatus.RETURNED
        })
        
        # Restore book inventory
        book = db.get_book(borrowing["book_id"])
        if book:
            db.update_book(borrowing["book_id"], {"inventory": book["inventory"] + 1})
        
        # Check if overdue and create fine payment
        if actual_return_date > expected_return_date:
            overdue_days = (actual_return_date - expected_return_date).days
            daily_fee = Decimal(book["daily_fee"]) if book else Decimal("0")
            fine_amount = daily_fee * overdue_days * DAILY_FEE_MULTIPLIER
            
            session_id = str(uuid.uuid4())
            session_url = f"http://localhost:8000/api/v1/payments/success/?session_id={session_id}"
            
            db.create_payment(
                borrowing_id=borrowing_id,
                payment_type=PaymentType.FINE,
                money_to_pay=fine_amount,
                session_url=session_url,
                session_id=session_id
            )
        
        return db.get_borrowing(borrowing_id)
    
    @staticmethod
    def get_borrowings(user_id: int, is_staff: bool, filters: Dict = None) -> List[Dict]:
        if is_staff:
            borrowings = db.get_all_borrowings()
            # Filter by user_id if provided
            if filters and filters.get("user_id"):
                try:
                    filter_user_id = int(filters["user_id"])
                    borrowings = [b for b in borrowings if b["user_id"] == filter_user_id]
                except (ValueError, TypeError):
                    pass
        else:
            borrowings = db.get_user_borrowings(user_id)
        
        # Filter by is_active
        if filters and "is_active" in filters:
            is_active = filters["is_active"]
            if isinstance(is_active, str):
                is_active = is_active.lower() in ("true", "1", "yes")
            if is_active:
                borrowings = [b for b in borrowings if b["actual_return_date"] is None]
            else:
                borrowings = [b for b in borrowings if b["actual_return_date"] is not None]
        
        return borrowings
    
    @staticmethod
    def format_borrowing(borrowing: Dict, include_book: bool = True, include_user: bool = False) -> Dict:
        result = {
            "id": borrowing["id"],
            "borrow_date": borrowing["borrow_date"],
            "expected_return_date": borrowing["expected_return_date"],
            "actual_return_date": borrowing["actual_return_date"],
            "status": borrowing["status"],
            "user_id": borrowing["user_id"],
            "book_id": borrowing["book_id"]
        }
        
        if include_book:
            book = db.get_book(borrowing["book_id"])
            if book:
                result["book"] = BookService.format_book(book)
        
        if include_user:
            user = db.get_user_by_id(borrowing["user_id"])
            if user:
                result["user"] = UserService.format_user(user)
        
        return result


class PaymentService:
    """Service for payment management"""
    
    @staticmethod
    def get_payments(user_id: int, is_staff: bool) -> List[Dict]:
        if is_staff:
            return db.get_all_payments()
        return db.get_user_payments(user_id)
    
    @staticmethod
    def process_payment(session_id: str) -> Optional[Dict]:
        for payment in db.get_all_payments():
            if payment["session_id"] == session_id:
                if payment["status"] == PaymentStatus.PENDING:
                    db.update_payment(payment["id"], {"status": PaymentStatus.PAID})
                return db.get_payment(payment["id"])
        return None
    
    @staticmethod
    def format_payment(payment: Dict) -> Dict:
        return {
            "id": payment["id"],
            "status": payment["status"],
            "type": payment["type"],
            "borrowing_id": payment["borrowing_id"],
            "session_url": payment["session_url"],
            "session_id": payment["session_id"],
            "money_to_pay": payment["money_to_pay"]
        }


class UserService:
    """Service for user management"""
    
    @staticmethod
    def register(data: Dict) -> Dict:
        errors = []
        if not data.get("email"):
            errors.append("Email is required")
        if not data.get("password"):
            errors.append("Password is required")
        if not data.get("first_name"):
            errors.append("First name is required")
        if not data.get("last_name"):
            errors.append("Last name is required")
        if len(data.get("password", "")) < 8:
            errors.append("Password must be at least 8 characters")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return db.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_staff=data.get("is_staff", False)
        )
    
    @staticmethod
    def authenticate(email: str, password: str) -> Optional[Dict]:
        user = db.get_user_by_email(email)
        if user and db.verify_password(password, user["password"]):
            return user
        return None
    
    @staticmethod
    def format_user(user: Dict) -> Dict:
        return {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_staff": user["is_staff"]
        }


# ============================================================
# HTTP Framework (Minimal WSGI implementation)
# ============================================================

class Request:
    """HTTP Request object"""
    
    def __init__(self, environ: Dict):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/")
        self.query_string = environ.get("QUERY_STRING", "")
        self._body = None
        self._json = None
        self._headers = {}
        self._parse_headers(environ)
        self._parse_query_params()
    
    def _parse_headers(self, environ: Dict):
        for key, value in environ.items():
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
            for param in self.query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    self.query_params[key] = value
                elif param:
                    self.query_params[param] = ""
    
    def get_header(self, name: str) -> Optional[str]:
        return self._headers.get(name)
    
    def get_body(self) -> bytes:
        if self._body is None:
            try:
                content_length = int(self._headers.get("Content-Length", 0))
                self._body = self.environ.get("wsgi.input", b"").read(content_length)
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
    
    def get_auth_token(self) -> Optional[str]:
        auth_header = self.get_header("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None


class Response:
    """HTTP Response object"""
    
    def __init__(self, data: Any = None, status: int = 200, headers: Dict = None):
        self.data = data
        self.status = status
        self.headers = headers or {}
        self.headers["Content-Type"] = "application/json"
    
    def get_status_string(self) -> str:
        status_messages = {
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
            500: "500 Internal Server Error"
        }
        return status_messages.get(self.status, f"{self.status} Unknown")
    
    def get_body(self) -> bytes:
        if self.data is None:
            return b""
        return json.dumps(self.data).encode("utf-8")
    
    def get_headers(self) -> List[tuple]:
        body = self.get_body()
        headers = list(self.headers.items())
        headers.append(("Content-Length", str(len(body))))
        return headers


def json_response(data: Any, status: int = 200) -> Response:
    return Response(data=data, status=status)


def error_response(message: str, status: int = 400) -> Response:
    return Response(data={"error": message}, status=status)


# ============================================================
# Authentication Middleware
# ============================================================

def get_current_user(request: Request) -> Optional[Dict]:
    """Extract and validate JWT token, return user"""
    token = request.get_auth_token()
    if not token:
        return None
    
    payload = JWT.decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("user_id")
    if not user_id:
        return None
    
    return db.get_user_by_id(user_id)


def require_auth(func):
    """Decorator to require authentication"""
    @wraps(func)
    def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        request.user = user
        return func(request, *args, **kwargs)
    return wrapper


def require_admin(func):
    """Decorator to require admin/staff access"""
    @wraps(func)
    def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        if not user.get("is_staff"):
            return error_response("Admin access required", 403)
        request.user = user
        return func(request, *args, **kwargs)
    return wrapper


# ============================================================
# Route Handlers
# ============================================================

class Router:
    """Simple URL router"""
    
    def __init__(self):
        self.routes: List[tuple] = []
    
    def add_route(self, method: str, path: str, handler):
        self.routes.append((method, path, handler))
    
    def match(self, method: str, path: str):
        for route_method, route_path, handler in self.routes:
            if route_method != method and route_method != "*":
                continue
            
            params = self._match_path(route_path, path)
            if params is not None:
                return handler, params
        
        return None, {}
    
    def _match_path(self, pattern: str, path: str) -> Optional[Dict]:
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        
        if len(pattern_parts) != len(path_parts):
            return None
        
        params = {}
        for pp, pathp in zip(pattern_parts, path_parts):
            if pp.startswith("<") and pp.endswith(">"):
                param_name = pp[1:-1]
                if ":" in param_name:
                    param_type, param_name = param_name.split(":", 1)
                    try:
                        if param_type == "int":
                            params[param_name] = int(pathp)
                        else:
                            params[param_name] = pathp
                    except ValueError:
                        return None
                else:
                    params[param_name] = pathp
            elif pp != pathp:
                return None
        
        return params


router = Router()


# ============================================================
# View Handlers
# ============================================================

# --- Authentication Views ---

def token_obtain_view(request: Request) -> Response:
    """POST /api/v1/auth/token/ - Obtain JWT tokens"""
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return error_response("Email and password are required", 400)
    
    user = UserService.authenticate(email, password)
    if not user:
        return error_response("Invalid credentials", 401)
    
    access_token = JWT.create_access_token(user["id"])
    refresh_token = JWT.create_refresh_token(user["id"])
    
    return json_response({
        "access": access_token,
        "refresh": refresh_token
    })


def token_refresh_view(request: Request) -> Response:
    """POST /api/v1/auth/token/refresh/ - Refresh JWT token"""
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    
    data = request.get_json()
    refresh_token = data.get("refresh")
    
    if not refresh_token:
        return error_response("Refresh token is required", 400)
    
    payload = JWT.decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return error_response("Invalid or expired refresh token", 401)
    
    user_id = payload.get("user_id")
    user = db.get_user_by_id(user_id)
    if not user:
        return error_response("User not found", 404)
    
    access_token = JWT.create_access_token(user_id)
    
    return json_response({"access": access_token})


def token_verify_view(request: Request) -> Response:
    """POST /api/v1/auth/token/verify/ - Verify JWT token"""
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    
    data = request.get_json()
    token = data.get("token")
    
    if not token:
        return error_response("Token is required", 400)
    
    payload = JWT.decode_token(token)
    if not payload:
        return error_response("Token is invalid or expired", 401)
    
    return json_response({"detail": "Token is valid"})


# --- User Views ---

def user_register_view(request: Request) -> Response:
    """POST /api/v1/users/ - Register new user"""
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    
    data = request.get_json()
    
    try:
        user = UserService.register(data)
        return json_response(UserService.format_user(user), 201)
    except ValueError as e:
        return error_response(str(e), 400)


def user_me_view(request: Request) -> Response:
    """GET/PUT/PATCH /api/v1/users/me/ - Get or update current user"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    
    if request.method == "GET":
        return json_response(UserService.format_user(user))
    
    elif request.method in ("PUT", "PATCH"):
        data = request.get_json()
        allowed_fields = ["first_name", "last_name", "password"]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        updated_user = db.update_user(user["id"], update_data)
        if not updated_user:
            return error_response("User not found", 404)
        
        return json_response(UserService.format_user(updated_user))
    
    return error_response("Method not allowed", 405)


def admin_users_list_view(request: Request) -> Response:
    """GET /admin/users/ - Admin: list all users"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    if not user.get("is_staff"):
        return error_response("Admin access required", 403)
    
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    
    users = [UserService.format_user(u) for u in db.users.values()]
    return json_response(users)


# --- Book Views ---

def books_list_view(request: Request) -> Response:
    """GET /api/v1/books/ - List all books, POST /api/v1/books/ - Create book (admin)"""
    if request.method == "GET":
        books = BookService.get_all_books()
        return json_response([BookService.format_book(b) for b in books])
    
    elif request.method == "POST":
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        if not user.get("is_staff"):
            return error_response("Admin access required", 403)
        
        data = request.get_json()
        errors = BookService.validate_book_data(data)
        if errors:
            return error_response("; ".join(errors), 400)
        
        book = BookService.create_book(data)
        return json_response(BookService.format_book(book), 201)
    
    return error_response("Method not allowed", 405)


def book_detail_view(request: Request, book_id: int) -> Response:
    """GET/PUT/PATCH/DELETE /api/v1/books/<id>/"""
    book = BookService.get_book(book_id)
    if not book:
        return error_response(f"Book with id {book_id} not found", 404)
    
    if request.method == "GET":
        return json_response(BookService.format_book(book))
    
    elif request.method in ("PUT", "PATCH"):
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        if not user.get("is_staff"):
            return error_response("Admin access required", 403)
        
        data = request.get_json()
        if request.method == "PUT":
            errors = BookService.validate_book_data(data)
            if errors:
                return error_response("; ".join(errors), 400)
        
        updated_book = BookService.update_book(book_id, data)
        return json_response(BookService.format_book(updated_book))
    
    elif request.method == "DELETE":
        user = get_current_user(request)
        if not user:
            return error_response("Authentication required", 401)
        if not user.get("is_staff"):
            return error_response("Admin access required", 403)
        
        BookService.delete_book(book_id)
        return Response(status=204)
    
    return error_response("Method not allowed", 405)


# --- Borrowing Views ---

def borrowings_list_view(request: Request) -> Response:
    """GET /api/v1/borrowings/ - List borrowings, POST - Create borrowing"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    
    if request.method == "GET":
        filters = {}
        if "is_active" in request.query_params:
            filters["is_active"] = request.query_params["is_active"]
        if "user_id" in request.query_params and user.get("is_staff"):
            filters["user_id"] = request.query_params["user_id"]
        
        borrowings = BorrowingService.get_borrowings(
            user_id=user["id"],
            is_staff=user.get("is_staff", False),
            filters=filters
        )
        
        include_user = user.get("is_staff", False)
        return json_response([
            BorrowingService.format_borrowing(b, include_book=True, include_user=include_user)
            for b in borrowings
        ])
    
    elif request.method == "POST":
        data = request.get_json()
        errors = BorrowingService.validate_borrowing_data(data)
        if errors:
            return error_response("; ".join(errors), 400)
        
        try:
            borrowing = BorrowingService.create_borrowing(user["id"], data)
            return json_response(BorrowingService.format_borrowing(borrowing), 201)
        except ValueError as e:
            return error_response(str(e), 400)
    
    return error_response("Method not allowed", 405)


def borrowing_detail_view(request: Request, borrowing_id: int) -> Response:
    """GET /api/v1/borrowings/<id>/"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    
    borrowing = db.get_borrowing(borrowing_id)
    if not borrowing:
        return error_response(f"Borrowing with id {borrowing_id} not found", 404)
    
    if not user.get("is_staff") and borrowing["user_id"] != user["id"]:
        return error_response("You don't have permission to view this borrowing", 403)
    
    if request.method == "GET":
        include_user = user.get("is_staff", False)
        return json_response(BorrowingService.format_borrowing(borrowing, include_book=True, include_user=include_user))
    
    return error_response("Method not allowed", 405)


def borrowing_return_view(request: Request, borrowing_id: int) -> Response:
    """POST /api/v1/borrowings/<id>/return/"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    
    if request.method != "POST":
        return error_response("Method not allowed", 405)
    
    try:
        borrowing = BorrowingService.return_book(
            borrowing_id=borrowing_id,
            user_id=user["id"],
            is_staff=user.get("is_staff", False)
        )
        return json_response(BorrowingService.format_borrowing(borrowing))
    except ValueError as e:
        return error_response(str(e), 400)
    except PermissionError as e:
        return error_response(str(e), 403)


# --- Payment Views ---

def payments_list_view(request: Request) -> Response:
    """GET /api/v1/payments/ - List payments"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    
    payments = PaymentService.get_payments(
        user_id=user["id"],
        is_staff=user.get("is_staff", False)
    )
    
    return json_response([PaymentService.format_payment(p) for p in payments])


def payment_detail_view(request: Request, payment_id: int) -> Response:
    """GET /api/v1/payments/<id>/"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    
    payment = db.get_payment(payment_id)
    if not payment:
        return error_response(f"Payment with id {payment_id} not found", 404)
    
    # Check ownership
    borrowing = db.get_borrowing(payment["borrowing_id"])
    if not user.get("is_staff") and (not borrowing or borrowing["user_id"] != user["id"]):
        return error_response("You don't have permission to view this payment", 403)
    
    return json_response(PaymentService.format_payment(payment))


def payment_success_view(request: Request) -> Response:
    """GET /api/v1/payments/success/ - Handle successful payment"""
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    
    session_id = request.query_params.get("session_id")
    if not session_id:
        return error_response("Session ID is required", 400)
    
    payment = PaymentService.process_payment(session_id)
    if not payment:
        return error_response("Payment not found or already processed", 404)
    
    return json_response({
        "message": "Payment successful",
        "payment": PaymentService.format_payment(payment)
    })


def payment_cancel_view(request: Request) -> Response:
    """GET /api/v1/payments/cancel/ - Handle cancelled payment"""
    if request.method != "GET":
        return error_response("Method not allowed", 405)
    
    return json_response({
        "message": "Payment was cancelled. You can retry within 24 hours."
    })


# --- Documentation View ---

def swagger_view(request: Request) -> Response:
    """GET /api/v1/doc/swagger/ - API Documentation"""
    swagger_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Service API",
            "version": "1.0.0",
            "description": "API Library service for borrowing books with JWT authentication"
        },
        "servers": [{"url": "http://localhost:8000"}],
        "paths": {
            "/api/v1/auth/token/": {
                "post": {
                    "summary": "Obtain JWT tokens",
                    "tags": ["Authentication"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "JWT tokens"},
                        "401": {"description": "Invalid credentials"}
                    }
                }
            },
            "/api/v1/auth/token/refresh/": {
                "post": {
                    "summary": "Refresh JWT access token",
                    "tags": ["Authentication"],
                    "responses": {"200": {"description": "New access token"}}
                }
            },
            "/api/v1/users/": {
                "post": {
                    "summary": "Register new user",
                    "tags": ["Users"],
                    "responses": {"201": {"description": "User created"}}
                }
            },
            "/api/v1/users/me/": {
                "get": {
                    "summary": "Get current user profile",
                    "tags": ["Users"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "User profile"}}
                },
                "patch": {
                    "summary": "Update current user profile",
                    "tags": ["Users"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Updated user profile"}}
                }
            },
            "/api/v1/books/": {
                "get": {
                    "summary": "List all books",
                    "tags": ["Books"],
                    "responses": {"200": {"description": "List of books"}}
                },
                "post": {
                    "summary": "Create a new book (admin only)",
                    "tags": ["Books"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"201": {"description": "Book created"}}
                }
            },
            "/api/v1/books/{id}/": {
                "get": {
                    "summary": "Get book details",
                    "tags": ["Books"],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Book details"}}
                },
                "put": {
                    "summary": "Update book (admin only)",
                    "tags": ["Books"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Updated book"}}
                },
                "delete": {
                    "summary": "Delete book (admin only)",
                    "tags": ["Books"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"204": {"description": "Book deleted"}}
                }
            },
            "/api/v1/borrowings/": {
                "get": {
                    "summary": "List borrowings",
                    "tags": ["Borrowings"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "is_active",
                            "in": "query",
                            "description": "Filter by active status (true/false)",
                            "schema": {"type": "boolean"}
                        },
                        {
                            "name": "user_id",
                            "in": "query",
                            "description": "Filter by user ID (admin only)",
                            "schema": {"type": "integer"}
                        }
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
            "/api/v1/borrowings/{id}/": {
                "get": {
                    "summary": "Get borrowing details",
                    "tags": ["Borrowings"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Borrowing details"}}
                }
            },
            "/api/v1/borrowings/{id}/return/": {
                "post": {
                    "summary": "Return a borrowed book",
                    "tags": ["Borrowings"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Book returned successfully"}}
                }
            },
            "/api/v1/payments/": {
                "get": {
                    "summary": "List payments",
                    "tags": ["Payments"],
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "List of payments"}}
                }
            },
            "/api/v1/payments/{id}/": {
                "get": {
                    "summary": "Get payment details",
                    "tags": ["Payments"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Payment details"}}
                }
            },
            "/api/v1/payments/success/": {
                "get": {
                    "summary": "Handle successful payment",
                    "tags": ["Payments"],
                    "parameters": [
                        {
                            "name": "session_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {"200": {"description": "Payment processed"}}
                }
            },
            "/api/v1/payments/cancel/": {
                "get": {
                    "summary": "Handle cancelled payment",
                    "tags": ["Payments"],
                    "responses": {"200": {"description": "Payment cancelled"}}
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
    return json_response(swagger_spec)


def admin_panel_view(request: Request) -> Response:
    """GET /admin/ - Admin panel info"""
    user = get_current_user(request)
    if not user:
        return error_response("Authentication required", 401)
    if not user.get("is_staff"):
        return error_response("Admin access required", 403)
    
    return json_response({
        "message": "Library Service Admin Panel",
        "endpoints": {
            "users": "/admin/users/",
            "books": "/api/v1/books/",
            "borrowings": "/api/v1/borrowings/",
            "payments": "/api/v1/payments/"
        },
        "stats": {
            "total_users": len(db.users),
            "total_books": len(db.books),
            "total_borrowings": len(db.borrowings),
            "total_payments": len(db.payments),
            "active_borrowings": len([b for b in db.borrowings.values() if b["status"] == BorrowingStatus.ACTIVE]),
            "pending_payments": len([p for p in db.payments.values() if p["status"] == PaymentStatus.PENDING])
        }
    })


def not_found_view(request: Request) -> Response:
    return error_response(f"Path '{request.path}' not found", 404)


# ============================================================
# Route Registration
# ============================================================

def setup_routes(router: Router):
    # Auth routes
    router.add_route("POST", "/api/v1/auth/token/", token_obtain_view)
    router.add_route("POST", "/api/v1/auth/token/refresh/", token_refresh_view)
    router.add_route("POST", "/api/v1/auth/token/verify/", token_verify_view)
    
    # User routes
    router.add_route("POST", "/api/v1/users/", user_register_view)
    router.add_route("GET", "/api/v1/users/me/", user_me_view)
    router.add_route("PUT", "/api/v1/users/me/", user_me_view)
    router.add_route("PATCH", "/api/v1/users/me/", user_me_view)
    
    # Admin routes
    router.add_route("GET", "/admin/", admin_panel_view)
    router.add_route("GET", "/admin/users/", admin_users_list_view)
    
    # Book routes
    router.add_route("GET", "/api/v1/books/", books_list_view)
    router.add_route("POST", "/api/v1/books/", books_list_view)
    router.add_route("GET", "/api/v1/books/<int:book_id>/", book_detail_view)
    router.add_route("PUT", "/api/v1/books/<int:book_id>/", book_detail_view)
    router.add_route("PATCH", "/api/v1/books/<int:book_id>/", book_detail_view)
    router.add_route("DELETE", "/api/v1/books/<int:book_id>/", book_detail_view)
    
    # Borrowing routes
    router.add_route("GET", "/api/v1/borrowings/", borrowings_list_view)
    router.add_route("POST", "/api/v1/borrowings/", borrowings_list_view)
    router.add_route("GET", "/api/v1/borrowings/<int:borrowing_id>/", borrowing_detail_view)
    router.add_route("POST", "/api/v1/borrowings/<int:borrowing_id>/return/", borrowing_return_view)
    
    # Payment routes
    router.add_route("GET", "/api/v1/payments/", payments_list_view)
    router.add_route("GET", "/api/v1/payments/success/", payment_success_view)
    router.add_route("GET", "/api/v1/payments/cancel/", payment_cancel_view)
    router.add_route("GET", "/api/v1/payments/<int:payment_id>/", payment_detail_view)
    
    # Documentation
    router.add_route("GET", "/api/v1/doc/swagger/", swagger_view)


setup_routes(router)


# ============================================================
# WSGI Application
# ============================================================

class LibraryServiceApp:
    """Main WSGI Application"""
    
    def __init__(self):
        self.router = router
    
    def __call__(self, environ: Dict, start_response):
        request = Request(environ)
        
        try:
            handler, params = self.router.match(request.method, request.path)
            
            if handler is None:
                response = not_found_view(request)
            else:
                response = handler(request, **params)
        
        except Exception as e:
            response = error_response(f"Internal server error: {str(e)}", 500)
        
        status_string = response.get_status_string()
        headers = response.get_headers()
        body = response.get_body()
        
        start_response(status_string, headers)
        return [body]


application = LibraryServiceApp()
app = application  # Alias


# ============================================================
# Development Server
# ============================================================

def run_dev_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the development server"""
    from wsgiref.simple_server import make_server, WSGIRequestHandler
    
    class QuietHandler(WSGIRequestHandler):
        def log_request(self, code='-', size='-'):
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {self.command} {self.path} - {code}")
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           Library Service API - Development Server       ║
╠══════════════════════════════════════════════════════════╣
║  Server running at: http://{host}:{port}                 ║
║  Admin panel:       http://{host}:{port}/admin/          ║
║  API Docs:          http://{host}:{port}/api/v1/doc/swagger/
║                                                          ║
║  Default Admin Credentials:                              ║
║    Email:    admin@library.com                           ║
║    Password: admin123                                    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    server = make_server(host, port, application, handler_class=QuietHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


# ============================================================
# CLI / Demo
# ============================================================

def run_demo():
    """Run a demonstration of the API"""
    import io
    
    def make_request(method: str, path: str, data: Dict = None, token: str = None, query: str = ""):
        """Simulate an HTTP request"""
        body = json.dumps(data).encode() if data else b""
        
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        
        if token:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        
        responses = []
        
        def start_response(status, headers):
            responses.append(status)
        
        result = application(environ, start_response)
        response_body = b"".join(result)
        
        try:
            return responses[0], json.loads(response_body.decode())
        except Exception:
            return responses[0] if responses else "500", {}
    
    print("=" * 60)
    print("Library Service API - Demo")
    print("=" * 60)
    
    # 1. Register a user
    print("\n1. Registering a new user...")
    status, data = make_request("POST", "/api/v1/users/", {
        "email": "john@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe"
    })
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(data, indent=2)}")
    
    # 2. Get admin token
    print("\n2. Getting admin JWT token...")
    status, data = make_request("POST", "/api/v1/auth/token/", {
        "email": "admin@library.com",
        "password": "admin123"
    })
    print(f"   Status: {status}")
    admin_token = data.get("access", "")
    print(f"   Access token obtained: {'Yes' if admin_token else 'No'}")
    
    # 3. Get user token
    print("\n3. Getting user JWT token...")
    status, data = make_request("POST", "/api/v1/auth/token/", {
        "email": "john@example.com",
        "password": "password123"
    })
    print(f"   Status: {status}")
    user_token = data.get("access", "")
    print(f"   Access token obtained: {'Yes' if user_token else 'No'}")
    
    # 4. Create a book (admin)
    print("\n4. Creating a book (admin)...")
    status, data = make_request("POST", "/api/v1/books/", {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "cover": "SOFT",
        "inventory": 5,
        "daily_fee": "2.50"
    }, token=admin_token)
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(data, indent=2)}")
    book_id = data.get("id")
    
    # 5. List books
    print("\n5. Listing all books...")
    status, data = make_request("GET", "/api/v1/books/")
    print(f"   Status: {status}")
    print(f"   Books count: {len(data)}")
    
    # 6. Create a borrowing
    print("\n6. Creating a borrowing...")
    future_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    status, data = make_request("POST", "/api/v1/borrowings/", {
        "book_id": book_id,
        "expected_return_date": future_date
    }, token=user_token)
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(data, indent=2)}")
    borrowing_id = data.get("id")
    
    # 7. List borrowings
    print("\n7. Listing user borrowings...")
    status, data = make_request("GET", "/api/v1/borrowings/", token=user_token)
    print(f"   Status: {status}")
    print(f"   Borrowings count: {len(data)}")
    
    # 8. List payments
    print("\n8. Listing payments...")
    status, data = make_request("GET", "/api/v1/payments/", token=user_token)
    print(f"   Status: {status}")
    print(f"   Payments: {json.dumps(data, indent=2)}")
    
    # 9. Return the book
    print("\n9. Returning the book...")
    status, data = make_request("POST", f"/api/v1/borrowings/{borrowing_id}/return/", token=user_token)
    print(f"   Status: {status}")
    print(f"   Response: {json.dumps(data, indent=2)}")
    
    # 10. Admin panel
    print("\n10. Accessing admin panel...")
    status, data = make_request("GET", "/admin/", token=admin_token)
    print(f"    Status: {status}")
    print(f"    Stats: {json.dumps(data.get('stats', {}), indent=2)}")
    
    # 11. Filter borrowings by is_active
    print("\n11. Filtering borrowings (is_active=false)...")
    status, data = make_request("GET", "/api/v1/borrowings/", token=user_token, query="is_active=false")
    print(f"    Status: {status}")
    print(f"    Returned borrowings count: {len(data)}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "demo":
            run_demo()
        elif command == "runserver":
            host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
            port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
            run_dev_server(host, port)
        else:
            print(f"Unknown command: {command}")
            print("Usage: python solution.py [demo|runserver [host] [port]]")
    else:
        # Default: run demo then start server
        run_demo()
        print("\nStarting development server...")
        run_dev_server()