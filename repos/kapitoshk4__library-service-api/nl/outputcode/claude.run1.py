import os
import sys
import json
import uuid
import hashlib
import hmac
import base64
import time
import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# ============================================================
# Configuration
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key-for-library-service")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
FINE_MULTIPLIER = 2  # Fine is 2x the daily fee
DATABASE_FILE = "library.json"


# ============================================================
# Enums
# ============================================================

class CoverType(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"


class PaymentType(str, Enum):
    PAYMENT = "PAYMENT"
    FINE = "FINE"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


# ============================================================
# Database (JSON file-based)
# ============================================================

class Database:
    def __init__(self, filepath: str = DATABASE_FILE):
        self.filepath = filepath
        self._data: Dict[str, Any] = {
            "users": {},
            "books": {},
            "borrowings": {},
            "payments": {},
        }
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {"users": {}, "books": {}, "borrowings": {}, "payments": {}}
        else:
            self._save()

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    def get_collection(self, name: str) -> Dict:
        return self._data.get(name, {})

    def save_item(self, collection: str, item_id: str, item: Dict):
        if collection not in self._data:
            self._data[collection] = {}
        self._data[collection][item_id] = item
        self._save()

    def delete_item(self, collection: str, item_id: str) -> bool:
        if collection in self._data and item_id in self._data[collection]:
            del self._data[collection][item_id]
            self._save()
            return True
        return False

    def get_item(self, collection: str, item_id: str) -> Optional[Dict]:
        return self._data.get(collection, {}).get(item_id)

    def get_all(self, collection: str) -> List[Dict]:
        return list(self._data.get(collection, {}).values())


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
            secret.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        signature_encoded = cls._base64url_encode(signature)
        return f"{signing_input}.{signature_encoded}"

    @classmethod
    def decode(cls, token: str, secret: str) -> Optional[Dict]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_encoded, payload_encoded, signature_encoded = parts
            signing_input = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                secret.encode(), signing_input.encode(), hashlib.sha256
            ).digest()
            expected_encoded = cls._base64url_encode(expected_signature)
            if not hmac.compare_digest(signature_encoded, expected_encoded):
                return None
            payload = json.loads(cls._base64url_decode(payload_encoded))
            if "exp" in payload and payload["exp"] < time.time():
                return None
            return payload
        except Exception:
            return None


# ============================================================
# Password Hashing
# ============================================================

class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        salt = os.urandom(16).hex()
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        try:
            salt, hash_hex = hashed.split(":")
            expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(expected.hex(), hash_hex)
        except Exception:
            return False


# ============================================================
# Models
# ============================================================

@dataclass
class User:
    id: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.USER
    is_active: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "password_hash": self.password_hash,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "is_active": self.is_active,
        }

    def to_public_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        return cls(
            id=data["id"],
            email=data["email"],
            password_hash=data["password_hash"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=data.get("role", UserRole.USER),
            is_active=data.get("is_active", True),
        )


@dataclass
class Book:
    id: str
    title: str
    author: str
    cover: CoverType
    inventory: int
    daily_fee: float  # in USD

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "cover": self.cover,
            "inventory": self.inventory,
            "daily_fee": self.daily_fee,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Book":
        return cls(
            id=data["id"],
            title=data["title"],
            author=data["author"],
            cover=data["cover"],
            inventory=data["inventory"],
            daily_fee=data["daily_fee"],
        )


@dataclass
class Borrowing:
    id: str
    borrow_date: str  # ISO date string
    expected_return_date: str  # ISO date string
    actual_return_date: Optional[str]  # ISO date string or None
    book_id: str
    user_id: str

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "borrow_date": self.borrow_date,
            "expected_return_date": self.expected_return_date,
            "actual_return_date": self.actual_return_date,
            "book_id": self.book_id,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Borrowing":
        return cls(
            id=data["id"],
            borrow_date=data["borrow_date"],
            expected_return_date=data["expected_return_date"],
            actual_return_date=data.get("actual_return_date"),
            book_id=data["book_id"],
            user_id=data["user_id"],
        )

    def is_overdue(self) -> bool:
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        today = datetime.date.today().isoformat()
        return today > self.expected_return_date

    def days_overdue(self) -> int:
        if self.actual_return_date:
            actual = datetime.date.fromisoformat(self.actual_return_date)
            expected = datetime.date.fromisoformat(self.expected_return_date)
            delta = actual - expected
            return max(0, delta.days)
        today = datetime.date.today()
        expected = datetime.date.fromisoformat(self.expected_return_date)
        delta = today - expected
        return max(0, delta.days)

    def days_borrowed(self) -> int:
        borrow = datetime.date.fromisoformat(self.borrow_date)
        end = (
            datetime.date.fromisoformat(self.actual_return_date)
            if self.actual_return_date
            else datetime.date.today()
        )
        return max(1, (end - borrow).days)


@dataclass
class Payment:
    id: str
    status: PaymentStatus
    payment_type: PaymentType
    borrowing_id: str
    session_url: str
    session_id: str
    money_to_pay: float  # in USD

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "status": self.status,
            "payment_type": self.payment_type,
            "borrowing_id": self.borrowing_id,
            "session_url": self.session_url,
            "session_id": self.session_id,
            "money_to_pay": self.money_to_pay,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Payment":
        return cls(
            id=data["id"],
            status=data["status"],
            payment_type=data["payment_type"],
            borrowing_id=data["borrowing_id"],
            session_url=data["session_url"],
            session_id=data["session_id"],
            money_to_pay=data["money_to_pay"],
        )


# ============================================================
# Services
# ============================================================

class UserService:
    @staticmethod
    def create_user(email: str, password: str, first_name: str, last_name: str, role: str = UserRole.USER) -> User:
        users = db.get_collection("users")
        for u in users.values():
            if u["email"] == email:
                raise ValueError("User with this email already exists")
        user_id = str(uuid.uuid4())
        password_hash = PasswordHasher.hash(password)
        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        db.save_item("users", user_id, user.to_dict())
        return user

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        for u in db.get_all("users"):
            if u["email"] == email:
                return User.from_dict(u)
        return None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        data = db.get_item("users", user_id)
        if data:
            return User.from_dict(data)
        return None

    @staticmethod
    def authenticate(email: str, password: str) -> Optional[User]:
        user = UserService.get_user_by_email(email)
        if user and PasswordHasher.verify(password, user.password_hash):
            return user
        return None

    @staticmethod
    def generate_tokens(user: User) -> Dict:
        now = time.time()
        access_payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "iat": now,
            "exp": now + JWT_EXPIRY_HOURS * 3600,
            "type": "access",
        }
        refresh_payload = {
            "sub": user.id,
            "iat": now,
            "exp": now + 7 * 24 * 3600,
            "type": "refresh",
        }
        return {
            "access": JWT.encode(access_payload, SECRET_KEY),
            "refresh": JWT.encode(refresh_payload, SECRET_KEY),
        }

    @staticmethod
    def refresh_token(refresh_token: str) -> Optional[Dict]:
        payload = JWT.decode(refresh_token, SECRET_KEY)
        if not payload or payload.get("type") != "refresh":
            return None
        user = UserService.get_user_by_id(payload["sub"])
        if not user:
            return None
        now = time.time()
        access_payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "iat": now,
            "exp": now + JWT_EXPIRY_HOURS * 3600,
            "type": "access",
        }
        return {"access": JWT.encode(access_payload, SECRET_KEY)}

    @staticmethod
    def update_user(user_id: str, data: Dict) -> Optional[User]:
        user = UserService.get_user_by_id(user_id)
        if not user:
            return None
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "password" in data:
            user.password_hash = PasswordHasher.hash(data["password"])
        db.save_item("users", user_id, user.to_dict())
        return user

    @staticmethod
    def get_all_users() -> List[User]:
        return [User.from_dict(u) for u in db.get_all("users")]


class BookService:
    @staticmethod
    def create_book(title: str, author: str, cover: str, inventory: int, daily_fee: float) -> Book:
        if inventory < 0:
            raise ValueError("Inventory cannot be negative")
        if daily_fee <= 0:
            raise ValueError("Daily fee must be positive")
        if cover not in [c.value for c in CoverType]:
            raise ValueError(f"Cover must be one of {[c.value for c in CoverType]}")
        book_id = str(uuid.uuid4())
        book = Book(
            id=book_id,
            title=title,
            author=author,
            cover=cover,
            inventory=inventory,
            daily_fee=daily_fee,
        )
        db.save_item("books", book_id, book.to_dict())
        return book

    @staticmethod
    def get_book_by_id(book_id: str) -> Optional[Book]:
        data = db.get_item("books", book_id)
        if data:
            return Book.from_dict(data)
        return None

    @staticmethod
    def get_all_books() -> List[Book]:
        return [Book.from_dict(b) for b in db.get_all("books")]

    @staticmethod
    def update_book(book_id: str, data: Dict) -> Optional[Book]:
        book = BookService.get_book_by_id(book_id)
        if not book:
            return None
        if "title" in data:
            book.title = data["title"]
        if "author" in data:
            book.author = data["author"]
        if "cover" in data:
            if data["cover"] not in [c.value for c in CoverType]:
                raise ValueError(f"Cover must be one of {[c.value for c in CoverType]}")
            book.cover = data["cover"]
        if "inventory" in data:
            if data["inventory"] < 0:
                raise ValueError("Inventory cannot be negative")
            book.inventory = data["inventory"]
        if "daily_fee" in data:
            if data["daily_fee"] <= 0:
                raise ValueError("Daily fee must be positive")
            book.daily_fee = data["daily_fee"]
        db.save_item("books", book_id, book.to_dict())
        return book

    @staticmethod
    def delete_book(book_id: str) -> bool:
        return db.delete_item("books", book_id)

    @staticmethod
    def decrement_inventory(book_id: str) -> bool:
        book = BookService.get_book_by_id(book_id)
        if not book or book.inventory <= 0:
            return False
        book.inventory -= 1
        db.save_item("books", book_id, book.to_dict())
        return True

    @staticmethod
    def increment_inventory(book_id: str) -> bool:
        book = BookService.get_book_by_id(book_id)
        if not book:
            return False
        book.inventory += 1
        db.save_item("books", book_id, book.to_dict())
        return True


class BorrowingService:
    @staticmethod
    def create_borrowing(user_id: str, book_id: str, expected_return_date: str) -> Borrowing:
        book = BookService.get_book_by_id(book_id)
        if not book:
            raise ValueError("Book not found")
        if book.inventory <= 0:
            raise ValueError("Book is not available (inventory is 0)")

        today = datetime.date.today().isoformat()
        try:
            exp_date = datetime.date.fromisoformat(expected_return_date)
        except ValueError:
            raise ValueError("Invalid expected_return_date format. Use YYYY-MM-DD")

        if exp_date <= datetime.date.today():
            raise ValueError("Expected return date must be in the future")

        if not BookService.decrement_inventory(book_id):
            raise ValueError("Failed to decrement book inventory")

        borrowing_id = str(uuid.uuid4())
        borrowing = Borrowing(
            id=borrowing_id,
            borrow_date=today,
            expected_return_date=expected_return_date,
            actual_return_date=None,
            book_id=book_id,
            user_id=user_id,
        )
        db.save_item("borrowings", borrowing_id, borrowing.to_dict())

        # Create payment
        days = (exp_date - datetime.date.today()).days
        money_to_pay = round(days * book.daily_fee, 2)
        PaymentService.create_payment(
            borrowing_id=borrowing_id,
            payment_type=PaymentType.PAYMENT,
            money_to_pay=money_to_pay,
        )

        return borrowing

    @staticmethod
    def get_borrowing_by_id(borrowing_id: str) -> Optional[Borrowing]:
        data = db.get_item("borrowings", borrowing_id)
        if data:
            return Borrowing.from_dict(data)
        return None

    @staticmethod
    def get_all_borrowings(
        user_id: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Borrowing]:
        borrowings = [Borrowing.from_dict(b) for b in db.get_all("borrowings")]
        if user_id:
            borrowings = [b for b in borrowings if b.user_id == user_id]
        if is_active is not None:
            if is_active:
                borrowings = [b for b in borrowings if b.actual_return_date is None]
            else:
                borrowings = [b for b in borrowings if b.actual_return_date is not None]
        return borrowings

    @staticmethod
    def return_borrowing(borrowing_id: str, user_id: str, is_admin: bool = False) -> Borrowing:
        borrowing = BorrowingService.get_borrowing_by_id(borrowing_id)
        if not borrowing:
            raise ValueError("Borrowing not found")
        if not is_admin and borrowing.user_id != user_id:
            raise PermissionError("You can only return your own borrowings")
        if borrowing.actual_return_date:
            raise ValueError("Book has already been returned")

        today = datetime.date.today().isoformat()
        borrowing.actual_return_date = today
        db.save_item("borrowings", borrowing_id, borrowing.to_dict())

        BookService.increment_inventory(borrowing.book_id)

        # Check if overdue and create fine payment
        if borrowing.is_overdue():
            book = BookService.get_book_by_id(borrowing.book_id)
            if book:
                overdue_days = borrowing.days_overdue()
                fine_amount = round(overdue_days * book.daily_fee * FINE_MULTIPLIER, 2)
                # Check if fine payment already exists
                existing_payments = PaymentService.get_payments_for_borrowing(borrowing_id)
                fine_exists = any(p.payment_type == PaymentType.FINE for p in existing_payments)
                if not fine_exists:
                    PaymentService.create_payment(
                        borrowing_id=borrowing_id,
                        payment_type=PaymentType.FINE,
                        money_to_pay=fine_amount,
                    )

        return borrowing


class PaymentService:
    @staticmethod
    def create_payment(borrowing_id: str, payment_type: str, money_to_pay: float) -> Payment:
        payment_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        session_url = f"https://checkout.stripe.com/pay/{session_id}"
        payment = Payment(
            id=payment_id,
            status=PaymentStatus.PENDING,
            payment_type=payment_type,
            borrowing_id=borrowing_id,
            session_url=session_url,
            session_id=session_id,
            money_to_pay=money_to_pay,
        )
        db.save_item("payments", payment_id, payment.to_dict())
        return payment

    @staticmethod
    def get_payment_by_id(payment_id: str) -> Optional[Payment]:
        data = db.get_item("payments", payment_id)
        if data:
            return Payment.from_dict(data)
        return None

    @staticmethod
    def get_all_payments(user_id: Optional[str] = None) -> List[Payment]:
        payments = [Payment.from_dict(p) for p in db.get_all("payments")]
        if user_id:
            borrowing_ids = {
                b.id for b in BorrowingService.get_all_borrowings(user_id=user_id)
            }
            payments = [p for p in payments if p.borrowing_id in borrowing_ids]
        return payments

    @staticmethod
    def get_payments_for_borrowing(borrowing_id: str) -> List[Payment]:
        return [
            Payment.from_dict(p)
            for p in db.get_all("payments")
            if p["borrowing_id"] == borrowing_id
        ]

    @staticmethod
    def complete_payment(payment_id: str, session_id: str) -> Optional[Payment]:
        payment = PaymentService.get_payment_by_id(payment_id)
        if not payment:
            return None
        if payment.session_id != session_id:
            return None
        if payment.status == PaymentStatus.PAID:
            return payment
        payment.status = PaymentStatus.PAID
        db.save_item("payments", payment_id, payment.to_dict())
        return payment

    @staticmethod
    def renew_payment_session(payment_id: str, user_id: str) -> Optional[Payment]:
        payment = PaymentService.get_payment_by_id(payment_id)
        if not payment:
            return None
        if payment.status == PaymentStatus.PAID:
            raise ValueError("Payment is already completed")
        # Verify user owns this payment
        borrowing = BorrowingService.get_borrowing_by_id(payment.borrowing_id)
        if not borrowing or borrowing.user_id != user_id:
            raise PermissionError("Access denied")
        new_session_id = str(uuid.uuid4())
        payment.session_id = new_session_id
        payment.session_url = f"https://checkout.stripe.com/pay/{new_session_id}"
        db.save_item("payments", payment_id, payment.to_dict())
        return payment


# ============================================================
# Authentication Middleware
# ============================================================

class AuthMiddleware:
    @staticmethod
    def get_current_user(token: str) -> Optional[User]:
        if not token:
            return None
        if token.startswith("Bearer "):
            token = token[7:]
        payload = JWT.decode(token, SECRET_KEY)
        if not payload or payload.get("type") != "access":
            return None
        user = UserService.get_user_by_id(payload["sub"])
        return user

    @staticmethod
    def require_auth(token: str) -> User:
        user = AuthMiddleware.get_current_user(token)
        if not user:
            raise PermissionError("Authentication required")
        return user

    @staticmethod
    def require_admin(token: str) -> User:
        user = AuthMiddleware.require_auth(token)
        if user.role != UserRole.ADMIN:
            raise PermissionError("Admin access required")
        return user


# ============================================================
# Request/Response helpers
# ============================================================

class Response:
    def __init__(self, data: Any = None, status: int = 200, error: str = None):
        self.data = data
        self.status = status
        self.error = error

    def to_dict(self) -> Dict:
        if self.error:
            return {"error": self.error, "status": self.status}
        return {"data": self.data, "status": self.status}


# ============================================================
# API Handlers
# ============================================================

class AuthAPI:
    @staticmethod
    def register(body: Dict) -> Response:
        required = ["email", "password", "first_name", "last_name"]
        for field in required:
            if field not in body:
                return Response(error=f"Missing field: {field}", status=400)
        try:
            user = UserService.create_user(
                email=body["email"],
                password=body["password"],
                first_name=body["first_name"],
                last_name=body["last_name"],
            )
            return Response(data=user.to_public_dict(), status=201)
        except ValueError as e:
            return Response(error=str(e), status=400)

    @staticmethod
    def login(body: Dict) -> Response:
        email = body.get("email")
        password = body.get("password")
        if not email or not password:
            return Response(error="Email and password required", status=400)
        user = UserService.authenticate(email, password)
        if not user:
            return Response(error="Invalid credentials", status=401)
        tokens = UserService.generate_tokens(user)
        return Response(data=tokens, status=200)

    @staticmethod
    def refresh(body: Dict) -> Response:
        refresh_token = body.get("refresh")
        if not refresh_token:
            return Response(error="Refresh token required", status=400)
        result = UserService.refresh_token(refresh_token)
        if not result:
            return Response(error="Invalid or expired refresh token", status=401)
        return Response(data=result, status=200)

    @staticmethod
    def me(token: str) -> Response:
        try:
            user = AuthMiddleware.require_auth(token)
            return Response(data=user.to_public_dict(), status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def update_me(token: str, body: Dict) -> Response:
        try:
            user = AuthMiddleware.require_auth(token)
            updated = UserService.update_user(user.id, body)
            return Response(data=updated.to_public_dict(), status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)
        except ValueError as e:
            return Response(error=str(e), status=400)


class UserAPI:
    @staticmethod
    def list_users(token: str) -> Response:
        try:
            AuthMiddleware.require_admin(token)
            users = UserService.get_all_users()
            return Response(data=[u.to_public_dict() for u in users], status=200)
        except PermissionError as e:
            return Response(error=str(e), status=403)

    @staticmethod
    def get_user(token: str, user_id: str) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            if current_user.role != UserRole.ADMIN and current_user.id != user_id:
                return Response(error="Access denied", status=403)
            user = UserService.get_user_by_id(user_id)
            if not user:
                return Response(error="User not found", status=404)
            return Response(data=user.to_public_dict(), status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)


class BookAPI:
    @staticmethod
    def list_books(token: Optional[str] = None) -> Response:
        books = BookService.get_all_books()
        return Response(data=[b.to_dict() for b in books], status=200)

    @staticmethod
    def get_book(book_id: str) -> Response:
        book = BookService.get_book_by_id(book_id)
        if not book:
            return Response(error="Book not found", status=404)
        return Response(data=book.to_dict(), status=200)

    @staticmethod
    def create_book(token: str, body: Dict) -> Response:
        try:
            AuthMiddleware.require_admin(token)
            required = ["title", "author", "cover", "inventory", "daily_fee"]
            for f in required:
                if f not in body:
                    return Response(error=f"Missing field: {f}", status=400)
            book = BookService.create_book(
                title=body["title"],
                author=body["author"],
                cover=body["cover"],
                inventory=int(body["inventory"]),
                daily_fee=float(body["daily_fee"]),
            )
            return Response(data=book.to_dict(), status=201)
        except PermissionError as e:
            return Response(error=str(e), status=403)
        except ValueError as e:
            return Response(error=str(e), status=400)

    @staticmethod
    def update_book(token: str, book_id: str, body: Dict) -> Response:
        try:
            AuthMiddleware.require_admin(token)
            book = BookService.update_book(book_id, body)
            if not book:
                return Response(error="Book not found", status=404)
            return Response(data=book.to_dict(), status=200)
        except PermissionError as e:
            return Response(error=str(e), status=403)
        except ValueError as e:
            return Response(error=str(e), status=400)

    @staticmethod
    def delete_book(token: str, book_id: str) -> Response:
        try:
            AuthMiddleware.require_admin(token)
            if not BookService.delete_book(book_id):
                return Response(error="Book not found", status=404)
            return Response(data={"message": "Book deleted"}, status=204)
        except PermissionError as e:
            return Response(error=str(e), status=403)


class BorrowingAPI:
    @staticmethod
    def list_borrowings(token: str, user_id: Optional[str] = None, is_active: Optional[bool] = None) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            if current_user.role == UserRole.ADMIN:
                filter_user_id = user_id
            else:
                filter_user_id = current_user.id
            borrowings = BorrowingService.get_all_borrowings(
                user_id=filter_user_id,
                is_active=is_active,
            )
            result = []
            for b in borrowings:
                d = b.to_dict()
                book = BookService.get_book_by_id(b.book_id)
                d["book"] = book.to_dict() if book else None
                result.append(d)
            return Response(data=result, status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def get_borrowing(token: str, borrowing_id: str) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            borrowing = BorrowingService.get_borrowing_by_id(borrowing_id)
            if not borrowing:
                return Response(error="Borrowing not found", status=404)
            if current_user.role != UserRole.ADMIN and borrowing.user_id != current_user.id:
                return Response(error="Access denied", status=403)
            d = borrowing.to_dict()
            book = BookService.get_book_by_id(borrowing.book_id)
            d["book"] = book.to_dict() if book else None
            return Response(data=d, status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def create_borrowing(token: str, body: Dict) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            required = ["book_id", "expected_return_date"]
            for f in required:
                if f not in body:
                    return Response(error=f"Missing field: {f}", status=400)
            borrowing = BorrowingService.create_borrowing(
                user_id=current_user.id,
                book_id=body["book_id"],
                expected_return_date=body["expected_return_date"],
            )
            d = borrowing.to_dict()
            book = BookService.get_book_by_id(borrowing.book_id)
            d["book"] = book.to_dict() if book else None
            return Response(data=d, status=201)
        except PermissionError as e:
            return Response(error=str(e), status=401)
        except ValueError as e:
            return Response(error=str(e), status=400)

    @staticmethod
    def return_borrowing(token: str, borrowing_id: str) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            is_admin = current_user.role == UserRole.ADMIN
            borrowing = BorrowingService.return_borrowing(
                borrowing_id=borrowing_id,
                user_id=current_user.id,
                is_admin=is_admin,
            )
            d = borrowing.to_dict()
            book = BookService.get_book_by_id(borrowing.book_id)
            d["book"] = book.to_dict() if book else None
            payments = PaymentService.get_payments_for_borrowing(borrowing_id)
            d["payments"] = [p.to_dict() for p in payments]
            return Response(data=d, status=200)
        except PermissionError as e:
            return Response(error=str(e), status=403)
        except ValueError as e:
            return Response(error=str(e), status=400)


class PaymentAPI:
    @staticmethod
    def list_payments(token: str) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            if current_user.role == UserRole.ADMIN:
                payments = PaymentService.get_all_payments()
            else:
                payments = PaymentService.get_all_payments(user_id=current_user.id)
            return Response(data=[p.to_dict() for p in payments], status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def get_payment(token: str, payment_id: str) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            payment = PaymentService.get_payment_by_id(payment_id)
            if not payment:
                return Response(error="Payment not found", status=404)
            borrowing = BorrowingService.get_borrowing_by_id(payment.borrowing_id)
            if current_user.role != UserRole.ADMIN and (
                not borrowing or borrowing.user_id != current_user.id
            ):
                return Response(error="Access denied", status=403)
            return Response(data=payment.to_dict(), status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def payment_success(token: str, payment_id: str, session_id: str) -> Response:
        try:
            AuthMiddleware.require_auth(token)
            payment = PaymentService.complete_payment(payment_id, session_id)
            if not payment:
                return Response(error="Payment not found or session ID mismatch", status=400)
            return Response(data={"message": "Payment successful", "payment": payment.to_dict()}, status=200)
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def payment_cancel(token: str, payment_id: str) -> Response:
        try:
            AuthMiddleware.require_auth(token)
            payment = PaymentService.get_payment_by_id(payment_id)
            if not payment:
                return Response(error="Payment not found", status=404)
            return Response(
                data={
                    "message": "Payment was cancelled. You can retry within 24 hours.",
                    "payment": payment.to_dict(),
                },
                status=200,
            )
        except PermissionError as e:
            return Response(error=str(e), status=401)

    @staticmethod
    def renew_payment_session(token: str, payment_id: str) -> Response:
        try:
            current_user = AuthMiddleware.require_auth(token)
            payment = PaymentService.renew_payment_session(payment_id, current_user.id)
            if not payment:
                return Response(error="Payment not found", status=404)
            return Response(data=payment.to_dict(), status=200)
        except PermissionError as e:
            return Response(error=str(e), status=403)
        except ValueError as e:
            return Response(error=str(e), status=400)


# ============================================================
# Swagger / OpenAPI Documentation
# ============================================================

SWAGGER_SPEC = {
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
                    "id": {"type": "string"},
                    "email": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "role": {"type": "string", "enum": ["ADMIN", "USER"]},
                    "is_active": {"type": "boolean"},
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
                    "daily_fee": {"type": "number"},
                },
            },
            "Borrowing": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "borrow_date": {"type": "string", "format": "date"},
                    "expected_return_date": {"type": "string", "format": "date"},
                    "actual_return_date": {"type": "string", "format": "date", "nullable": True},
                    "book_id": {"type": "string"},
                    "user_id": {"type": "string"},
                },
            },
            "Payment": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string", "enum": ["PENDING", "PAID"]},
                    "payment_type": {"type": "string", "enum": ["PAYMENT", "FINE"]},
                    "borrowing_id": {"type": "string"},
                    "session_url": {"type": "string"},
                    "session_id": {"type": "string"},
                    "money_to_pay": {"type": "number"},
                },
            },
        },
    },
    "paths": {
        "/auth/register/": {
            "post": {
                "tags": ["auth"],
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
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "User created"},
                    "400": {"description": "Bad request"},
                },
            }
        },
        "/auth/token/": {
            "post": {
                "tags": ["auth"],
                "summary": "Obtain JWT token pair",
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
                    "200": {"description": "Token pair returned"},
                    "401": {"description": "Invalid credentials"},
                },
            }
        },
        "/auth/token/refresh/": {
            "post": {
                "tags": ["auth"],
                "summary": "Refresh access token",
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
        "/auth/me/": {
            "get": {
                "tags": ["auth"],
                "summary": "Get current user profile",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "User profile"},
                    "401": {"description": "Unauthorized"},
                },
            },
            "patch": {
                "tags": ["auth"],
                "summary": "Update current user profile",
                "security": [{"BearerAuth": []}],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "first_name": {"type": "string"},
                                    "last_name": {"type": "string"},
                                    "password": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Updated profile"},
                    "401": {"description": "Unauthorized"},
                },
            },
        },
        "/books/": {
            "get": {
                "tags": ["books"],
                "summary": "List all books",
                "responses": {"200": {"description": "List of books"}},
            },
            "post": {
                "tags": ["books"],
                "summary": "Create a book (admin only)",
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
                                    "daily_fee": {"type": "number"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Book created"},
                    "403": {"description": "Admin required"},
                },
            },
        },
        "/books/{id}/": {
            "get": {
                "tags": ["books"],
                "summary": "Get a book by ID",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Book details"},
                    "404": {"description": "Not found"},
                },
            },
            "put": {
                "tags": ["books"],
                "summary": "Update a book (admin only)",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Updated book"},
                    "403": {"description": "Admin required"},
                    "404": {"description": "Not found"},
                },
            },
            "delete": {
                "tags": ["books"],
                "summary": "Delete a book (admin only)",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "204": {"description": "Deleted"},
                    "403": {"description": "Admin required"},
                    "404": {"description": "Not found"},
                },
            },
        },
        "/borrowings/": {
            "get": {
                "tags": ["borrowings"],
                "summary": "List borrowings",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": "Filter by user ID (admin only)",
                    },
                    {
                        "name": "is_active",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "boolean"},
                        "description": "Filter by active status (no actual return date)",
                    },
                ],
                "responses": {
                    "200": {"description": "List of borrowings"},
                    "401": {"description": "Unauthorized"},
                },
            },
            "post": {
                "tags": ["borrowings"],
                "summary": "Create a borrowing",
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
                                    "expected_return_date": {"type": "string", "format": "date"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Borrowing created"},
                    "400": {"description": "Bad request"},
                    "401": {"description": "Unauthorized"},
                },
            },
        },
        "/borrowings/{id}/": {
            "get": {
                "tags": ["borrowings"],
                "summary": "Get a borrowing by ID",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Borrowing details"},
                    "404": {"description": "Not found"},
                },
            }
        },
        "/borrowings/{id}/return/": {
            "post": {
                "tags": ["borrowings"],
                "summary": "Return a borrowed book",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Book returned"},
                    "400": {"description": "Already returned"},
                    "403": {"description": "Access denied"},
                },
            }
        },
        "/payments/": {
            "get": {
                "tags": ["payments"],
                "summary": "List payments",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "List of payments"},
                    "401": {"description": "Unauthorized"},
                },
            }
        },
        "/payments/{id}/": {
            "get": {
                "tags": ["payments"],
                "summary": "Get payment by ID",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Payment details"},
                    "404": {"description": "Not found"},
                },
            }
        },
        "/payments/{id}/success/": {
            "get": {
                "tags": ["payments"],
                "summary": "Handle successful payment",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "session_id", "in": "query", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {
                    "200": {"description": "Payment completed"},
                    "400": {"description": "Invalid session"},
                },
            }
        },
        "/payments/{id}/cancel/": {
            "get": {
                "tags": ["payments"],
                "summary": "Handle cancelled payment",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Payment cancelled info"}},
            }
        },
        "/payments/{id}/renew/": {
            "post": {
                "tags": ["payments"],
                "summary": "Renew payment session",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Session renewed"},
                    "400": {"description": "Already paid"},
                    "403": {"description": "Access denied"},
                },
            }
        },
    },
}


# ============================================================
# Admin Panel
# ============================================================

class AdminPanel:
    @staticmethod
    def get_stats(token: str) -> Response:
        try:
            AuthMiddleware.require_admin(token)
            users = UserService.get_all_users()
            books = BookService.get_all_books()
            borrowings = BorrowingService.get_all_borrowings()
            payments = PaymentService.get_all_payments()

            active_borrowings = [b for b in borrowings if b.actual_return_date is None]
            overdue_borrowings = [b for b in borrowings if b.is_overdue()]
            paid_payments = [p for p in payments if p.status == PaymentStatus.PAID]
            pending_payments = [p for p in payments if p.status == PaymentStatus.PENDING]

            total_revenue = sum(p.money_to_pay for p in paid_payments)

            return Response(
                data={
                    "total_users": len(users),
                    "total_books": len(books),
                    "total_borrowings": len(borrowings),
                    "active_borrowings": len(active_borrowings),
                    "overdue_borrowings": len(overdue_borrowings),
                    "total_payments": len(payments),
                    "paid_payments": len(paid_payments),
                    "pending_payments": len(pending_payments),
                    "total_revenue_usd": round(total_revenue, 2),
                },
                status=200,
            )
        except PermissionError as e:
            return Response(error=str(e), status=403)

    @staticmethod
    def list_all_users(token: str) -> Response:
        return UserAPI.list_users(token)

    @staticmethod
    def list_all_borrowings(token: str) -> Response:
        return BorrowingAPI.list_borrowings(token)

    @staticmethod
    def list_all_payments(token: str) -> Response:
        return PaymentAPI.list_payments(token)


# ============================================================
# Simple HTTP Router
# ============================================================

class Router:
    def __init__(self):
        self.routes: List[Dict] = []

    def add_route(self, method: str, path: str, handler):
        self.routes.append({"method": method, "path": path, "handler": handler})

    def match(self, method: str, path: str):
        for route in self.routes:
            if route["method"] != method:
                continue
            pattern = route["path"]
            params = self._match_path(pattern, path)
            if params is not None:
                return route["handler"], params
        return None, {}

    def _match_path(self, pattern: str, path: str) -> Optional[Dict]:
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return None
        params = {}
        for pp, pathp in zip(pattern_parts, path_parts):
            if pp.startswith("{") and pp.endswith("}"):
                param_name = pp[1:-1]
                params[param_name] = pathp
            elif pp != pathp:
                return None
        return params


# ============================================================
# Application
# ============================================================

class LibraryApp:
    def __init__(self):
        self.router = Router()
        self._setup_routes()

    def _setup_routes(self):
        # Auth routes
        self.router.add_route("POST", "/api/v1/auth/register/", self._register)
        self.router.add_route("POST", "/api/v1/auth/token/", self._login)
        self.router.add_route("POST", "/api/v1/auth/token/refresh/", self._refresh)
        self.router.add_route("GET", "/api/v1/auth/me/", self._me)
        self.router.add_route("PATCH", "/api/v1/auth/me/", self._update_me)

        # User routes
        self.router.add_route("GET", "/api/v1/users/", self._list_users)
        self.router.add_route("GET", "/api/v1/users/{id}/", self._get_user)

        # Book routes
        self.router.add_route("GET", "/api/v1/books/", self._list_books)
        self.router.add_route("POST", "/api/v1/books/", self._create_book)
        self.router.add_route("GET", "/api/v1/books/{id}/", self._get_book)
        self.router.add_route("PUT", "/api/v1/books/{id}/", self._update_book)
        self.router.add_route("PATCH", "/api/v1/books/{id}/", self._update_book)
        self.router.add_route("DELETE", "/api/v1/books/{id}/", self._delete_book)

        # Borrowing routes
        self.router.add_route("GET", "/api/v1/borrowings/", self._list_borrowings)
        self.router.add_route("POST", "/api/v1/borrowings/", self._create_borrowing)
        self.router.add_route("GET", "/api/v1/borrowings/{id}/", self._get_borrowing)
        self.router.add_route("POST", "/api/v1/borrowings/{id}/return/", self._return_borrowing)

        # Payment routes
        self.router.add_route("GET", "/api/v1/payments/", self._list_payments)
        self.router.add_route("GET", "/api/v1/payments/{id}/", self._get_payment)
        self.router.add_route("GET", "/api/v1/payments/{id}/success/", self._payment_success)
        self.router.add_route("GET", "/api/v1/payments/{id}/cancel/", self._payment_cancel)
        self.router.add_route("POST", "/api/v1/payments/{id}/renew/", self._renew_payment)

        # Admin routes
        self.router.add_route("GET", "/admin/", self._admin_stats)
        self.router.add_route("GET", "/admin/users/", self._admin_users)
        self.router.add_route("GET", "/admin/borrowings/", self._admin_borrowings)
        self.router.add_route("GET", "/admin/payments/", self._admin_payments)

        # Swagger docs
        self.router.add_route("GET", "/api/v1/doc/swagger/", self._swagger_docs)

    def handle(self, method: str, path: str, headers: Dict = None, body: Dict = None, query: Dict = None) -> Response:
        headers = headers or {}
        body = body or {}
        query = query or {}
        token = headers.get("Authorization", "")

        handler, params = self.router.match(method, path)
        if handler is None:
            return Response(error="Not found", status=404)

        return handler(token=token, body=body, params=params, query=query)

    # Auth handlers
    def _register(self, token, body, params, query):
        return AuthAPI.register(body)

    def _login(self, token, body, params, query):
        return AuthAPI.login(body)

    def _refresh(self, token, body, params, query):
        return AuthAPI.refresh(body)

    def _me(self, token, body, params, query):
        return AuthAPI.me(token)

    def _update_me(self, token, body, params, query):
        return AuthAPI.update_me(token, body)

    # User handlers
    def _list_users(self, token, body, params, query):
        return UserAPI.list_users(token)

    def _get_user(self, token, body, params, query):
        return UserAPI.get_user(token, params.get("id"))

    # Book handlers
    def _list_books(self, token, body, params, query):
        return BookAPI.list_books(token)

    def _create_book(self, token, body, params, query):
        return BookAPI.create_book(token, body)

    def _get_book(self, token, body, params, query):
        return BookAPI.get_book(params.get("id"))

    def _update_book(self, token, body, params, query):
        return BookAPI.update_book(token, params.get("id"), body)

    def _delete_book(self, token, body, params, query):
        return BookAPI.delete_book(token, params.get("id"))

    # Borrowing handlers
    def _list_borrowings(self, token, body, params, query):
        user_id = query.get("user_id")
        is_active_str = query.get("is_active")
        is_active = None
        if is_active_str is not None:
            is_active = is_active_str.lower() in ("true", "1", "yes")
        return BorrowingAPI.list_borrowings(token, user_id=user_id, is_active=is_active)

    def _create_borrowing(self, token, body, params, query):
        return BorrowingAPI.create_borrowing(token, body)

    def _get_borrowing(self, token, body, params, query):
        return BorrowingAPI.get_borrowing(token, params.get("id"))

    def _return_borrowing(self, token, body, params, query):
        return BorrowingAPI.return_borrowing(token, params.get("id"))

    # Payment handlers
    def _list_payments(self, token, body, params, query):
        return PaymentAPI.list_payments(token)

    def _get_payment(self, token, body, params, query):
        return PaymentAPI.get_payment(token, params.get("id"))

    def _payment_success(self, token, body, params, query):
        session_id = query.get("session_id", "")
        return PaymentAPI.payment_success(token, params.get("id"), session_id)

    def _payment_cancel(self, token, body, params, query):
        return PaymentAPI.payment_cancel(token, params.get("id"))

    def _renew_payment(self, token, body, params, query):
        return PaymentAPI.renew_payment_session(token, params.get("id"))

    # Admin handlers
    def _admin_stats(self, token, body, params, query):
        return AdminPanel.get_stats(token)

    def _admin_users(self, token, body, params, query):
        return AdminPanel.list_all_users(token)

    def _admin_borrowings(self, token, body, params, query):
        return AdminPanel.list_all_borrowings(token)

    def _admin_payments(self, token, body, params, query):
        return AdminPanel.list_all_payments(token)

    def _swagger_docs(self, token, body, params, query):
        return Response(data=SWAGGER_SPEC, status=200)


# ============================================================
# CLI / Demo
# ============================================================

def print_response(label: str, resp: Response):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Status: {resp.status}")
    data = resp.to_dict()
    print(f"  Body: {json.dumps(data, indent=2, default=str)}")


def run_demo():
    app = LibraryApp()

    print("\n" + "="*60)
    print("  LIBRARY SERVICE API - DEMO")
    print("="*60)

    # Register admin
    resp = app.handle("POST", "/api/v1/auth/register/", body={
        "email": "admin@library.com",
        "password": "adminpass123",
        "first_name": "Admin",
        "last_name": "User",
    })
    print_response("Register Admin", resp)
    admin_id = resp.data.get("id") if resp.data else None

    # Manually set admin role
    if admin_id:
        user_data = db.get_item("users", admin_id)
        if user_data:
            user_data["role"] = UserRole.ADMIN
            db.save_item("users", admin_id, user_data)

    # Login as admin
    resp = app.handle("POST", "/api/v1/auth/token/", body={
        "email": "admin@library.com",
        "password": "adminpass123",
    })
    print_response("Admin Login", resp)
    admin_token = f"Bearer {resp.data['access']}" if resp.data else ""

    # Register regular user
    resp = app.handle("POST", "/api/v1/auth/register/", body={
        "email": "user@library.com",
        "password": "userpass123",
        "first_name": "John",
        "last_name": "Doe",
    })
    print_response("Register User", resp)

    # Login as user
    resp = app.handle("POST", "/api/v1/auth/token/", body={
        "email": "user@library.com",
        "password": "userpass123",
    })
    print_response("User Login", resp)
    user_token = f"Bearer {resp.data['access']}" if resp.data else ""

    # Create books (admin)
    resp = app.handle("POST", "/api/v1/books/", headers={"Authorization": admin_token}, body={
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "cover": "HARD",
        "inventory": 5,
        "daily_fee": 1.50,
    })
    print_response("Create Book", resp)
    book_id = resp.data.get("id") if resp.data else None

    resp = app.handle("POST", "/api/v1/books/", headers={"Authorization": admin_token}, body={
        "title": "1984",
        "author": "George Orwell",
        "cover": "SOFT",
        "inventory": 3,
        "daily_fee": 1.00,
    })
    print_response("Create Book 2", resp)

    # List books
    resp = app.handle("GET", "/api/v1/books/")
    print_response("List Books", resp)

    # Get specific book
    if book_id:
        resp = app.handle("GET", f"/api/v1/books/{book_id}/")
        print_response("Get Book", resp)

    # Create borrowing
    future_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    resp = app.handle("POST", "/api/v1/borrowings/", headers={"Authorization": user_token}, body={
        "book_id": book_id,
        "expected_return_date": future_date,
    })
    print_response("Create Borrowing", resp)
    borrowing_id = resp.data.get("id") if resp.data else None

    # List borrowings (user sees only their own)
    resp = app.handle("GET", "/api/v1/borrowings/", headers={"Authorization": user_token})
    print_response("List Borrowings (User)", resp)

    # List borrowings (admin sees all)
    resp = app.handle("GET", "/api/v1/borrowings/", headers={"Authorization": admin_token})
    print_response("List Borrowings (Admin)", resp)

    # Filter active borrowings
    resp = app.handle("GET", "/api/v1/borrowings/", headers={"Authorization": user_token}, query={"is_active": "true"})
    print_response("List Active Borrowings", resp)

    # List payments
    resp = app.handle("GET", "/api/v1/payments/", headers={"Authorization": user_token})
    print_response("List Payments", resp)
    payment_id = None
    if resp.data and len(resp.data) > 0:
        payment_id = resp.data[0].get("id")
        session_id = resp.data[0].get("session_id")

    # Complete payment
    if payment_id and session_id:
        resp = app.handle(
            "GET",
            f"/api/v1/payments/{payment_id}/success/",
            headers={"Authorization": user_token},
            query={"session_id": session_id},
        )
        print_response("Complete Payment", resp)

    # Return borrowing
    if borrowing_id:
        resp = app.handle("POST", f"/api/v1/borrowings/{borrowing_id}/return/", headers={"Authorization": user_token})
        print_response("Return Borrowing", resp)

    # Admin stats
    resp = app.handle("GET", "/admin/", headers={"Authorization": admin_token})
    print_response("Admin Stats", resp)

    # Swagger docs
    resp = app.handle("GET", "/api/v1/doc/swagger/")
    print_response("Swagger Docs (truncated)", Response(
        data={"info": SWAGGER_SPEC["info"], "paths_count": len(SWAGGER_SPEC["paths"])},
        status=200,
    ))

    # Refresh token
    login_resp = app.handle("POST", "/api/v1/auth/token/", body={
        "email": "user@library.com",
        "password": "userpass123",
    })
    if login_resp.data:
        resp = app.handle("POST", "/api/v1/auth/token/refresh/", body={
            "refresh": login_resp.data["refresh"]
        })
        print_response("Refresh Token", resp)

    print("\n" + "="*60)
    print("  DEMO COMPLETE")
    print("="*60)


if __name__ == "__main__":
    run_demo()