import json
import base64
import hmac
import hashlib
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

SECRET_KEY = "library_super_secret_key"
ALGORITHM = "HS256"

def create_jwt_token(data: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = data.copy()
    payload_data["exp"] = (datetime.utcnow() + timedelta(hours=24)).timestamp()
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(
        hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"

def decode_jwt_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected_sig):
            return None
        padded_payload = payload + "=" * (4 - len(payload) % 4)
        decoded_payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode())
        if decoded_payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        return decoded_payload
    except Exception:
        return None

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"

class PaymentType(str, Enum):
    PAYMENT = "PAYMENT"
    FINE = "FINE"

class User(BaseModel):
    id: int
    email: str
    password_hash: str
    is_admin: bool

class UserCreate(BaseModel):
    email: str
    password: str
    is_admin: bool = False

class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool

class Book(BaseModel):
    id: int
    title: str
    author: str
    inventory: int
    daily_fee: float

class BookCreate(BaseModel):
    title: str
    author: str
    inventory: int
    daily_fee: float

class Borrowing(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrow_date: date
    expected_return_date: date
    actual_return_date: Optional[date] = None

class BorrowingCreate(BaseModel):
    book_id: int
    days: int

class Payment(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    status: PaymentStatus
    type: PaymentType

users_db: Dict[int, User] = {
    1: User(id=1, email="admin@library.com", password_hash="admin", is_admin=True),
    2: User(id=2, email="user@library.com", password_hash="user", is_admin=False)
}
books_db: Dict[int, Book] = {
    1: Book(id=1, title="1984", author="George Orwell", inventory=5, daily_fee=1.5),
    2: Book(id=2, title="Brave New World", author="Aldous Huxley", inventory=2, daily_fee=1.2)
}
borrowings_db: Dict[int, Borrowing] = {}
payments_db: Dict[int, Payment] = {}

app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    docs_url="/api/v1/doc/swagger/"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = users_db.get(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in users_db.values() if u.email == form_data.username and u.password_hash == form_data.password), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_jwt_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/admin/", response_class=HTMLResponse)
def admin_panel():
    return """
    <html>
        <head><title>Admin Panel</title></head>
        <body>
            <h1>Library Admin Panel</h1>
            <p>Welcome to the Library Service Admin Panel. Use the API endpoints to manage books, users, borrowings, and payments.</p>
            <a href="/api/v1/doc/swagger/">Go to Swagger Documentation</a>
        </body>
    </html>
    """

@app.post("/books/", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book_in: BookCreate, admin: User = Depends(get_admin_user)):
    new_id = max(books_db.keys(), default=0) + 1
    book = Book(id=new_id, **book_in.dict())
    books_db[new_id] = book
    return book

@app.get("/books/", response_model=List[Book])
def get_books(
    author: Optional[str] = Query(None, description="Filter by author"),
    title: Optional[str] = Query(None, description="Filter by title")
):
    results = list(books_db.values())
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    if title:
        results = [b for b in results if title.lower() in b.title.lower()]
    return results

@app.post("/borrowings/", response_model=Borrowing, status_code=status.HTTP_201_CREATED)
def create_borrowing(borrow_in: BorrowingCreate, current_user: User = Depends(get_current_user)):
    book = books_db.get(borrow_in.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.inventory <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book out of stock")

    book.inventory -= 1
    borrowing_id = max(borrowings_db.keys(), default=0) + 1
    borrow_date = date.today()
    expected_return_date = borrow_date + timedelta(days=borrow_in.days)

    borrowing = Borrowing(
        id=borrowing_id,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=borrow_date,
        expected_return_date=expected_return_date
    )
    borrowings_db[borrowing_id] = borrowing

    payment_id = max(payments_db.keys(), default=0) + 1
    payment = Payment(
        id=payment_id,
        borrowing_id=borrowing_id,
        amount=book.daily_fee * borrow_in.days,
        status=PaymentStatus.PENDING,
        type=PaymentType.PAYMENT
    )
    payments_db[payment_id] = payment

    return borrowing

@app.get("/borrowings/", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[date] = Query(None, description="Filter by actual return date"),
    current_user: User = Depends(get_current_user)
):
    results = list(borrowings_db.values())
    
    if not current_user.is_admin:
        results = [b for b in results if b.user_id == current_user.id]
    elif user_id is not None:
        results = [b for b in results if b.user_id == user_id]

    if actual_return_date is not None:
        results = [b for b in results if b.actual_return_date == actual_return_date]

    return results

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    borrowing = borrowings_db.get(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    if borrowing.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to return this borrowing")
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrowing already returned")

    borrowing.actual_return_date = date.today()
    book = books_db[borrowing.book_id]
    book.inventory += 1

    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_multiplier = 2.0
        fine_amount = overdue_days * book.daily_fee * fine_multiplier
        
        payment_id = max(payments_db.keys(), default=0) + 1
        fine_payment = Payment(
            id=payment_id,
            borrowing_id=borrowing_id,
            amount=fine_amount,
            status=PaymentStatus.PENDING,
            type=PaymentType.FINE
        )
        payments_db[payment_id] = fine_payment

    return borrowing

@app.get("/payments/", response_model=List[Payment])
def get_payments(
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    type: Optional[PaymentType] = Query(None, description="Filter by payment type"),
    current_user: User = Depends(get_current_user)
):
    results = list(payments_db.values())
    
    if not current_user.is_admin:
        user_borrowing_ids = {b.id for b in borrowings_db.values() if b.user_id == current_user.id}
        results = [p for p in results if p.borrowing_id in user_borrowing_ids]

    if status:
        results = [p for p in results if p.status == status]
    if type:
        results = [p for p in results if p.type == type]

    return results

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    borrowing = borrowings_db.get(payment.borrowing_id)
    if not borrowing or (borrowing.user_id != current_user.id and not current_user.is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to pay this payment")
        
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already completed")

    payment.status = PaymentStatus.PAID
    return payment