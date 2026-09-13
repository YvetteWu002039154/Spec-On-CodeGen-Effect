import base64
import hmac
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

SECRET_KEY = "super-secret-library-key"
ALGORITHM = "HS256"

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(payload: str) -> bytes:
    padding = '=' * (4 - (len(payload) % 4))
    return base64.urlsafe_b64decode(payload + padding)

def create_jwt(payload: dict, secret: str) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    encoded_header = base64url_encode(json.dumps(header).encode())
    encoded_payload = base64url_encode(json.dumps(payload).encode())
    signature_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(secret.encode(), signature_input, hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_jwt(token: str, secret: str) -> dict:
    try:
        header, payload, signature = token.split('.')
        signature_input = f"{header}.{payload}".encode()
        expected_signature = hmac.new(secret.encode(), signature_input, hashlib.sha256).digest()
        if not hmac.compare_digest(base64url_encode(expected_signature), signature):
            raise ValueError("Invalid signature")
        return json.loads(base64url_decode(payload).decode())
    except Exception:
        raise ValueError("Invalid token")

class User(BaseModel):
    id: int
    email: str
    is_admin: bool

class UserInDB(User):
    hashed_password: str

class Book(BaseModel):
    id: int
    title: str
    author: str
    inventory: int
    daily_fee: float

class BorrowingCreate(BaseModel):
    book_id: int
    expected_return_date: date

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
    status: str 
    payment_type: str 
    amount: float

users_db = {
    1: UserInDB(id=1, email="admin@library.com", is_admin=True, hashed_password="admin"),
    2: UserInDB(id=2, email="user@library.com", is_admin=False, hashed_password="user")
}
books_db = {
    1: Book(id=1, title="The Great Gatsby", author="F. Scott Fitzgerald", inventory=3, daily_fee=2.0),
    2: Book(id=2, title="1984", author="George Orwell", inventory=5, daily_fee=1.5)
}
borrowings_db = {}
payments_db = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=2)
    payload.update({"exp": expire.timestamp()})
    return create_jwt(payload, SECRET_KEY)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_jwt(token, SECRET_KEY)
        if datetime.now(timezone.utc).timestamp() > payload.get("exp", 0):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = next((u for u in users_db.values() if u.email == email), None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_current_admin(user: UserInDB = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user

app = FastAPI(
    title="Library Service API",
    docs_url="/api/v1/doc/swagger/",
    redoc_url=None
)

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in users_db.values() if u.email == form_data.username), None)
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/", response_class=HTMLResponse)
def admin_panel(admin: UserInDB = Depends(get_current_admin)):
    return """
    <html>
        <head><title>Admin Panel</title></head>
        <body>
            <h1>Library Admin Panel</h1>
            <p>Welcome to the administrative dashboard.</p>
            <ul>
                <li><a href="/api/v1/doc/swagger/">API Documentation</a></li>
            </ul>
        </body>
    </html>
    """

@app.post("/books/", response_model=Book)
def create_book(book: Book, admin: UserInDB = Depends(get_current_admin)):
    if book.id in books_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book ID already exists")
    books_db[book.id] = book
    return book

@app.get("/books/", response_model=List[Book])
def get_books(
    title: Optional[str] = Query(None, description="Filter by book title"),
    author: Optional[str] = Query(None, description="Filter by book author")
):
    results = list(books_db.values())
    if title:
        results = [b for b in results if title.lower() in b.title.lower()]
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    return results

@app.post("/borrowings/", response_model=Borrowing)
def create_borrowing(borrowing_in: BorrowingCreate, user: UserInDB = Depends(get_current_user)):
    book = books_db.get(borrowing_in.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.inventory < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book is out of stock")
    
    if borrowing_in.expected_return_date <= date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected return date must be in the future")

    book.inventory -= 1
    borrowing_id = len(borrowings_db) + 1
    borrowing = Borrowing(
        id=borrowing_id,
        user_id=user.id,
        book_id=book.id,
        borrow_date=date.today(),
        expected_return_date=borrowing_in.expected_return_date
    )
    borrowings_db[borrowing_id] = borrowing

    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    amount = days * book.daily_fee
    payment_id = len(payments_db) + 1
    payment = Payment(
        id=payment_id,
        borrowing_id=borrowing_id,
        status="PENDING",
        payment_type="PAYMENT",
        amount=amount
    )
    payments_db[payment_id] = payment

    return borrowing

@app.get("/borrowings/", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[date] = Query(None, description="Filter by actual return date"),
    user: UserInDB = Depends(get_current_user)
):
    if not user.is_admin:
        user_id = user.id 

    results = list(borrowings_db.values())
    if user_id is not None:
        results = [b for b in results if b.user_id == user_id]
    if actual_return_date is not None:
        results = [b for b in results if b.actual_return_date == actual_return_date]
    return results

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, user: UserInDB = Depends(get_current_user)):
    borrowing = borrowings_db.get(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrowing not found")
    if borrowing.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to return this borrowing")
    if borrowing.actual_return_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrowing already returned")

    borrowing.actual_return_date = date.today()
    book = books_db[borrowing.book_id]
    book.inventory += 1

    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_multiplier = 2.0
        fine_amount = overdue_days * book.daily_fee * fine_multiplier
        
        payment_id = len(payments_db) + 1
        fine_payment = Payment(
            id=payment_id,
            borrowing_id=borrowing_id,
            status="PENDING",
            payment_type="FINE",
            amount=fine_amount
        )
        payments_db[payment_id] = fine_payment

    return borrowing

@app.get("/payments/", response_model=List[Payment])
def get_payments(
    status: Optional[str] = Query(None, description="Filter by payment status (PENDING, PAID)"),
    payment_type: Optional[str] = Query(None, description="Filter by payment type (PAYMENT, FINE)"),
    user: UserInDB = Depends(get_current_user)
):
    if user.is_admin:
        results = list(payments_db.values())
    else:
        user_borrowing_ids = {b.id for b in borrowings_db.values() if b.user_id == user.id}
        results = [p for p in payments_db.values() if p.borrowing_id in user_borrowing_ids]

    if status:
        results = [p for p in results if p.status.upper() == status.upper()]
    if payment_type:
        results = [p for p in results if p.payment_type.upper() == payment_type.upper()]
    
    return results

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, user: UserInDB = Depends(get_current_user)):
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    borrowing = borrowings_db[payment.borrowing_id]
    if borrowing.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to pay this payment")

    if payment.status == "PAID":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment is already paid")

    payment.status = "PAID"
    return payment