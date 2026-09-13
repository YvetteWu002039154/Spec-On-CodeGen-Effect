import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

SECRET_KEY = "super-secret-library-key"

def create_jwt(data: dict, secret: str) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"

def decode_jwt(token: str, secret: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected_sig):
            return None
        padded_payload = payload + "=" * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded_payload).decode())
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
    expected_return_date: date

class Payment(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    status: PaymentStatus
    type: PaymentType

users_db: List[User] = [
    User(id=1, email="admin@library.com", password_hash="admin", is_admin=True),
    User(id=2, email="user@library.com", password_hash="user", is_admin=False)
]
books_db: List[Book] = [
    Book(id=1, title="1984", author="George Orwell", inventory=5, daily_fee=1.5),
    Book(id=2, title="Brave New World", author="Aldous Huxley", inventory=2, daily_fee=2.0)
]
borrowings_db: List[Borrowing] = []
payments_db: List[Payment] = []

app = FastAPI(
    title="Library Service API",
    docs_url="/api/v1/doc/swagger/",
    openapi_url="/api/v1/openapi.json"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt(token, SECRET_KEY)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = next((u for u in users_db if u.email == payload["sub"]), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in users_db if u.email == form_data.username and u.password_hash == form_data.password), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_jwt({"sub": user.email, "exp": (datetime.utcnow() + timedelta(hours=2)).timestamp()}, SECRET_KEY)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/admin/")
def admin_panel(current_user: User = Depends(get_current_admin_user)):
    return {
        "message": "Welcome to the Admin Panel",
        "total_users": len(users_db),
        "total_books": len(books_db),
        "total_borrowings": len(borrowings_db),
        "total_payments": len(payments_db)
    }

@app.get("/books/", response_model=List[Book])
def get_books(
    title: Optional[str] = Query(None, description="Filter by book title"),
    author: Optional[str] = Query(None, description="Filter by book author")
):
    result = books_db
    if title:
        result = [b for b in result if title.lower() in b.title.lower()]
    if author:
        result = [b for b in result if author.lower() in b.author.lower()]
    return result

@app.post("/books/", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book_in: BookCreate, current_user: User = Depends(get_current_admin_user)):
    new_id = max([b.id for b in books_db], default=0) + 1
    new_book = Book(id=new_id, **book_in.dict())
    books_db.append(new_book)
    return new_book

@app.get("/borrowings/", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[date] = Query(None, description="Filter by actual return date"),
    current_user: User = Depends(get_current_user)
):
    result = borrowings_db
    if not current_user.is_admin:
        result = [b for b in result if b.user_id == current_user.id]
    elif user_id is not None:
        result = [b for b in result if b.user_id == user_id]
        
    if actual_return_date is not None:
        result = [b for b in result if b.actual_return_date == actual_return_date]
        
    return result

@app.post("/borrowings/", response_model=Borrowing, status_code=status.HTTP_201_CREATED)
def create_borrowing(borrowing_in: BorrowingCreate, current_user: User = Depends(get_current_user)):
    book = next((b for b in books_db if b.id == borrowing_in.book_id), None)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.inventory <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book is out of stock")
    
    today = date.today()
    if borrowing_in.expected_return_date <= today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected return date must be in the future")

    book.inventory -= 1

    new_borrowing_id = max([b.id for b in borrowings_db], default=0) + 1
    new_borrowing = Borrowing(
        id=new_borrowing_id,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=today,
        expected_return_date=borrowing_in.expected_return_date,
        actual_return_date=None
    )
    borrowings_db.append(new_borrowing)

    days_borrowed = (new_borrowing.expected_return_date - today).days
    payment_amount = days_borrowed * book.daily_fee

    new_payment_id = max([p.id for p in payments_db], default=0) + 1
    new_payment = Payment(
        id=new_payment_id,
        borrowing_id=new_borrowing.id,
        amount=payment_amount,
        status=PaymentStatus.PENDING,
        type=PaymentType.PAYMENT
    )
    payments_db.append(new_payment)

    return new_borrowing

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    borrowing = next((b for b in borrowings_db if b.id == borrowing_id), None)
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    if not current_user.is_admin and borrowing.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to return this borrowing")
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrowing already returned")

    pending_payments = [p for p in payments_db if p.borrowing_id == borrowing.id and p.status == PaymentStatus.PENDING]
    if pending_payments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot return book with pending payments")

    today = date.today()
    borrowing.actual_return_date = today

    book = next((b for b in books_db if b.id == borrowing.book_id), None)
    if book:
        book.inventory += 1

    if today > borrowing.expected_return_date:
        overdue_days = (today - borrowing.expected_return_date).days
        fine_multiplier = 2.0
        fine_amount = overdue_days * (book.daily_fee if book else 2.0) * fine_multiplier
        
        new_payment_id = max([p.id for p in payments_db], default=0) + 1
        fine_payment = Payment(
            id=new_payment_id,
            borrowing_id=borrowing.id,
            amount=fine_amount,
            status=PaymentStatus.PENDING,
            type=PaymentType.FINE
        )
        payments_db.append(fine_payment)

    return borrowing

@app.get("/payments/", response_model=List[Payment])
def get_payments(
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    type: Optional[PaymentType] = Query(None, description="Filter by payment type"),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_admin:
        user_borrowing_ids = [b.id for b in borrowings_db]
    else:
        user_borrowing_ids = [b.id for b in borrowings_db if b.user_id == current_user.id]

    result = [p for p in payments_db if p.borrowing_id in user_borrowing_ids]

    if status:
        result = [p for p in result if p.status == status]
    if type:
        result = [p for p in result if p.type == type]

    return result

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    payment = next((p for p in payments_db if p.id == payment_id), None)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    borrowing = next((b for b in borrowings_db if b.id == payment.borrowing_id), None)
    if not current_user.is_admin and (not borrowing or borrowing.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to pay this payment")
        
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already paid")

    payment.status = PaymentStatus.PAID
    return payment

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)