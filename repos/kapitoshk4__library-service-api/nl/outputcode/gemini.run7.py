import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

SECRET_KEY = "super-secret-library-key"
ALGORITHM = "HS256"

def create_jwt_token(data: dict, expires_delta: timedelta = timedelta(hours=1)) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = data.copy()
    payload_data["exp"] = int((datetime.utcnow() + expires_delta).timestamp())
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(
        hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"

def decode_jwt_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
        
        decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
        if decoded_payload.get("exp", 0) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return decoded_payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

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
    is_admin: bool = False

class Book(BaseModel):
    id: int
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

class Payment(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    status: PaymentStatus
    type: PaymentType

class BookCreate(BaseModel):
    title: str
    author: str
    inventory: int = Field(..., ge=0)
    daily_fee: float = Field(..., gt=0)

class BorrowingCreate(BaseModel):
    book_id: int
    expected_return_date: date

class PaymentResponse(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    status: PaymentStatus
    type: PaymentType

db_users: Dict[int, User] = {
    1: User(id=1, email="admin@library.com", password="adminpassword", is_admin=True),
    2: User(id=2, email="user@library.com", password="userpassword", is_admin=False)
}
db_books: Dict[int, Book] = {
    1: Book(id=1, title="1984", author="George Orwell", inventory=5, daily_fee=1.5),
    2: Book(id=2, title="Brave New World", author="Aldous Huxley", inventory=0, daily_fee=2.0)
}
db_borrowings: Dict[int, Borrowing] = {}
db_payments: Dict[int, Payment] = {}

app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    version="1.0.0",
    docs_url="/api/v1/doc/swagger/"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt_token(token)
    user_id = payload.get("sub")
    if not user_id or int(user_id) not in db_users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return db_users[int(user_id)]

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in db_users.values() if u.email == form_data.username and u.password == form_data.password), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_jwt_token({"sub": str(user.id), "is_admin": user.is_admin})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/admin/", response_class=HTMLResponse)
def admin_panel(current_user: User = Depends(get_admin_user)):
    return """
    <html>
        <head><title>Admin Panel</title></head>
        <body>
            <h1>Welcome to the Library Admin Panel</h1>
            <p>Manage books, users, borrowings, and payments here.</p>
        </body>
    </html>
    """

@app.get("/books", response_model=List[Book])
def get_books(
    author: Optional[str] = Query(None, description="Filter by author"),
    title: Optional[str] = Query(None, description="Filter by title")
):
    result = list(db_books.values())
    if author:
        result = [b for b in result if author.lower() in b.author.lower()]
    if title:
        result = [b for b in result if title.lower() in b.title.lower()]
    return result

@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book_in: BookCreate, current_user: User = Depends(get_admin_user)):
    new_id = max(db_books.keys(), default=0) + 1
    new_book = Book(id=new_id, **book_in.dict())
    db_books[new_id] = new_book
    return new_book

@app.get("/borrowings", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[date] = Query(None, description="Filter by actual return date"),
    is_active: Optional[bool] = Query(None, description="Filter active borrowings"),
    current_user: User = Depends(get_current_user)
):
    result = list(db_borrowings.values())
    
    if not current_user.is_admin:
        result = [b for b in result if b.user_id == current_user.id]
    elif user_id is not None:
        result = [b for b in result if b.user_id == user_id]
        
    if actual_return_date is not None:
        result = [b for b in result if b.actual_return_date == actual_return_date]
        
    if is_active is not None:
        if is_active:
            result = [b for b in result if b.actual_return_date is None]
        else:
            result = [b for b in result if b.actual_return_date is not None]
            
    return result

@app.post("/borrowings", response_model=Borrowing, status_code=status.HTTP_201_CREATED)
def create_borrowing(borrowing_in: BorrowingCreate, current_user: User = Depends(get_current_user)):
    book = db_books.get(borrowing_in.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.inventory <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book is out of stock")
    if borrowing_in.expected_return_date <= date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected return date must be in the future")

    book.inventory -= 1
    
    new_id = max(db_borrowings.keys(), default=0) + 1
    new_borrowing = Borrowing(
        id=new_id,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=date.today(),
        expected_return_date=borrowing_in.expected_return_date
    )
    db_borrowings[new_id] = new_borrowing

    days = (new_borrowing.expected_return_date - new_borrowing.borrow_date).days
    payment_amount = days * book.daily_fee
    
    payment_id = max(db_payments.keys(), default=0) + 1
    new_payment = Payment(
        id=payment_id,
        borrowing_id=new_id,
        amount=payment_amount,
        status=PaymentStatus.PENDING,
        type=PaymentType.PAYMENT
    )
    db_payments[payment_id] = new_payment

    return new_borrowing

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    borrowing = db_borrowings.get(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    if borrowing.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to return this borrowing")
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrowing already returned")

    borrowing.actual_return_date = date.today()
    
    book = db_books[borrowing.book_id]
    book.inventory += 1

    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_multiplier = 2.0
        fine_amount = overdue_days * book.daily_fee * fine_multiplier
        
        payment_id = max(db_payments.keys(), default=0) + 1
        fine_payment = Payment(
            id=payment_id,
            borrowing_id=borrowing.id,
            amount=fine_amount,
            status=PaymentStatus.PENDING,
            type=PaymentType.FINE
        )
        db_payments[payment_id] = fine_payment

    return borrowing

@app.get("/payments", response_model=List[Payment])
def get_payments(
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    type: Optional[PaymentType] = Query(None, description="Filter by payment type"),
    current_user: User = Depends(get_current_user)
):
    result = list(db_payments.values())
    
    if not current_user.is_admin:
        user_borrowing_ids = {b.id for b in db_borrowings.values() if b.user_id == current_user.id}
        result = [p for p in result if p.borrowing_id in user_borrowing_ids]
        
    if status:
        result = [p for p in result if p.status == status]
    if type:
        result = [p for p in result if p.type == type]
        
    return result

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    payment = db_payments.get(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        
    borrowing = db_borrowings.get(payment.borrowing_id)
    if not borrowing or (borrowing.user_id != current_user.id and not current_user.is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to pay this payment")
        
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already completed")

    payment.status = PaymentStatus.PAID
    return payment

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)