import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

SECRET_KEY = "library_super_secret_key_for_jwt"
FINE_MULTIPLIER = 2.0

app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    version="1.0.0",
    docs_url="/api/v1/doc/swagger/",
    redoc_url=None
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"

class PaymentType(str, Enum):
    PAYMENT = "PAYMENT"
    FINE = "FINE"

class User(BaseModel):
    id: int
    email: str
    password: str
    is_admin: bool

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
    user_id: int
    amount: float
    status: PaymentStatus
    type: PaymentType

users_db = {
    1: User(id=1, email="admin@library.com", password="adminpassword", is_admin=True),
    2: User(id=2, email="user@library.com", password="userpassword", is_admin=False)
}
books_db = {
    1: Book(id=1, title="The Great Gatsby", author="F. Scott Fitzgerald", inventory=5, daily_fee=1.5),
    2: Book(id=2, title="1984", author="George Orwell", inventory=2, daily_fee=2.0)
}
borrowings_db = {}
payments_db = {}

book_id_counter = 3
borrowing_id_counter = 1
payment_id_counter = 1

def create_jwt(data: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    
    payload = data.copy()
    payload["exp"] = (datetime.utcnow() + timedelta(hours=24)).timestamp()
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{encoded_header}.{encoded_payload}".encode(),
        hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_jwt(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError
        header, payload, signature = parts
        
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(
                SECRET_KEY.encode(),
                f"{header}.{payload}".encode(),
                hashlib.sha256
            ).digest()
        ).decode().rstrip("=")
        
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError
            
        payload_padded = payload + "=" * ((4 - len(payload) % 4) % 4)
        decoded_payload = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
        
        if datetime.utcnow().timestamp() > decoded_payload.get("exp", 0):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
            
        return decoded_payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if user_id is None or int(user_id) not in users_db:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return users_db[int(user_id)]

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    for user in users_db.values():
        if user.email == form_data.username and user.password == form_data.password:
            access_token = create_jwt(data={"sub": str(user.id)})
            return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

@app.get("/admin/")
def admin_panel(current_admin: User = Depends(get_current_admin)):
    return {
        "message": "Welcome to the Admin Panel",
        "admin_email": current_admin.email,
        "total_users": len(users_db),
        "total_books": len(books_db),
        "total_borrowings": len(borrowings_db),
        "total_payments": len(payments_db)
    }

@app.get("/books/", response_model=List[Book])
def get_books(
    title: Optional[str] = None,
    author: Optional[str] = None,
    available_only: Optional[bool] = False
):
    results = list(books_db.values())
    if title:
        results = [b for b in results if title.lower() in b.title.lower()]
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    if available_only:
        results = [b for b in results if b.inventory > 0]
    return results

@app.post("/books/", response_model=Book)
def create_book(book_in: BookCreate, current_admin: User = Depends(get_current_admin)):
    global book_id_counter
    new_book = Book(id=book_id_counter, **book_in.dict())
    books_db[book_id_counter] = new_book
    book_id_counter += 1
    return new_book

@app.get("/borrowings/", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = None,
    actual_return_date: Optional[date] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    results = list(borrowings_db.values())
    
    if not current_user.is_admin:
        results = [b for b in results if b.user_id == current_user.id]
    elif user_id is not None:
        results = [b for b in results if b.user_id == user_id]
        
    if actual_return_date is not None:
        results = [b for b in results if b.actual_return_date == actual_return_date]
        
    if is_active is not None:
        if is_active:
            results = [b for b in results if b.actual_return_date is None]
        else:
            results = [b for b in results if b.actual_return_date is not None]
            
    return results

@app.post("/borrowings/", response_model=Borrowing)
def create_borrowing(borrowing_in: BorrowingCreate, current_user: User = Depends(get_current_user)):
    global borrowing_id_counter, payment_id_counter
    
    book = books_db.get(borrowing_in.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.inventory <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book is currently out of stock")
        
    pending_payments = [p for p in payments_db.values() if p.user_id == current_user.id and p.status == PaymentStatus.PENDING]
    if pending_payments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot borrow new books with pending payments")
        
    book.inventory -= 1
    
    borrow_date = date.today()
    expected_return_date = borrow_date + timedelta(days=borrowing_in.days)
    
    new_borrowing = Borrowing(
        id=borrowing_id_counter,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=borrow_date,
        expected_return_date=expected_return_date
    )
    borrowings_db[borrowing_id_counter] = new_borrowing
    
    payment_amount = borrowing_in.days * book.daily_fee
    new_payment = Payment(
        id=payment_id_counter,
        borrowing_id=new_borrowing.id,
        user_id=current_user.id,
        amount=payment_amount,
        status=PaymentStatus.PENDING,
        type=PaymentType.PAYMENT
    )
    payments_db[payment_id_counter] = new_payment
    
    borrowing_id_counter += 1
    payment_id_counter += 1
    
    return new_borrowing

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    global payment_id_counter
    
    borrowing = borrowings_db.get(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
        
    if borrowing.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to return this borrowing")
        
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrowing has already been returned")
        
    borrowing.actual_return_date = date.today()
    
    book = books_db[borrowing.book_id]
    book.inventory += 1
    
    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_amount = overdue_days * book.daily_fee * FINE_MULTIPLIER
        
        fine_payment = Payment(
            id=payment_id_counter,
            borrowing_id=borrowing.id,
            user_id=borrowing.user_id,
            amount=fine_amount,
            status=PaymentStatus.PENDING,
            type=PaymentType.FINE
        )
        payments_db[payment_id_counter] = fine_payment
        payment_id_counter += 1
        
    return borrowing

@app.get("/payments/", response_model=List[Payment])
def get_payments(
    user_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    type: Optional[PaymentType] = None,
    current_user: User = Depends(get_current_user)
):
    results = list(payments_db.values())
    
    if not current_user.is_admin:
        results = [p for p in results if p.user_id == current_user.id]
    elif user_id is not None:
        results = [p for p in results if p.user_id == user_id]
        
    if status is not None:
        results = [p for p in results if p.status == status]
        
    if type is not None:
        results = [p for p in results if p.type == type]
        
    return results

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        
    if payment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to pay this payment")
        
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment is already paid")
        
    payment.status = PaymentStatus.PAID
    return payment

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)