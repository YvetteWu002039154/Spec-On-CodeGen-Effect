import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

SECRET_KEY = "library_super_secret_key_for_jwt"
ALGORITHM = "HS256"

def create_jwt_token(data: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    payload_bytes = json.dumps(data).encode()
    payload = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    signature_bytes = hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(signature_bytes).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"

def decode_jwt_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected_signature_bytes = hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        expected_signature = base64.urlsafe_b64encode(expected_signature_bytes).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid signature")
        padded_payload = payload + "=" * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded_payload).decode())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

class User(BaseModel):
    id: int
    username: str
    is_admin: bool

class UserInDB(User):
    hashed_password: str

class BookBase(BaseModel):
    title: str
    author: str
    inventory: int = Field(ge=0)
    daily_fee: float = Field(ge=0.0)

class Book(BookBase):
    id: int

class BorrowingBase(BaseModel):
    book_id: int
    expected_return_date: date

class Borrowing(BorrowingBase):
    id: int
    user_id: int
    borrow_date: date
    actual_return_date: Optional[date] = None

class Payment(BaseModel):
    id: int
    borrowing_id: int
    user_id: int
    status: str 
    type: str 
    amount: float

class LibraryService:
    def __init__(self):
        self.users: Dict[str, UserInDB] = {
            "admin": UserInDB(id=1, username="admin", hashed_password="password", is_admin=True),
            "user": UserInDB(id=2, username="user", hashed_password="password", is_admin=False)
        }
        self.books: Dict[int, Book] = {
            1: Book(id=1, title="1984", author="George Orwell", inventory=5, daily_fee=1.5),
            2: Book(id=2, title="The Hobbit", author="J.R.R. Tolkien", inventory=2, daily_fee=2.0)
        }
        self.borrowings: Dict[int, Borrowing] = {}
        self.payments: Dict[int, Payment] = {}
        
        self._book_id_counter = 3
        self._borrowing_id_counter = 1
        self._payment_id_counter = 1

    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        return self.users.get(username)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        for user in self.users.values():
            if user.id == user_id:
                return User(**user.dict())
        return None

    def create_book(self, book_data: BookBase) -> Book:
        book = Book(id=self._book_id_counter, **book_data.dict())
        self.books[self._book_id_counter] = book
        self._book_id_counter += 1
        return book

    def get_books(self, title: Optional[str] = None, author: Optional[str] = None) -> List[Book]:
        result = list(self.books.values())
        if title:
            result = [b for b in result if title.lower() in b.title.lower()]
        if author:
            result = [b for b in result if author.lower() in b.author.lower()]
        return result

    def create_borrowing(self, user_id: int, borrowing_data: BorrowingBase) -> Borrowing:
        book = self.books.get(borrowing_data.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.inventory <= 0:
            raise HTTPException(status_code=400, detail="Book is out of stock")
        if borrowing_data.expected_return_date <= date.today():
            raise HTTPException(status_code=400, detail="Expected return date must be in the future")

        book.inventory -= 1
        
        borrowing = Borrowing(
            id=self._borrowing_id_counter,
            user_id=user_id,
            book_id=book.id,
            borrow_date=date.today(),
            expected_return_date=borrowing_data.expected_return_date,
            actual_return_date=None
        )
        self.borrowings[self._borrowing_id_counter] = borrowing
        self._borrowing_id_counter += 1

        days_borrowed = (borrowing.expected_return_date - borrowing.borrow_date).days
        payment_amount = days_borrowed * book.daily_fee
        
        payment = Payment(
            id=self._payment_id_counter,
            borrowing_id=borrowing.id,
            user_id=user_id,
            status="PENDING",
            type="PAYMENT",
            amount=payment_amount
        )
        self.payments[self._payment_id_counter] = payment
        self._payment_id_counter += 1

        return borrowing

    def return_borrowing(self, borrowing_id: int, user_id: int) -> Borrowing:
        borrowing = self.borrowings.get(borrowing_id)
        if not borrowing:
            raise HTTPException(status_code=404, detail="Borrowing not found")
        if borrowing.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to return this borrowing")
        if borrowing.actual_return_date is not None:
            raise HTTPException(status_code=400, detail="Borrowing already returned")

        borrowing.actual_return_date = date.today()
        
        book = self.books.get(borrowing.book_id)
        if book:
            book.inventory += 1

        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_multiplier = 2.0 
            fine_amount = overdue_days * book.daily_fee * fine_multiplier
            
            fine_payment = Payment(
                id=self._payment_id_counter,
                borrowing_id=borrowing.id,
                user_id=user_id,
                status="PENDING",
                type="FINE",
                amount=fine_amount
            )
            self.payments[self._payment_id_counter] = fine_payment
            self._payment_id_counter += 1

        return borrowing

    def get_borrowings(self, user_id: Optional[int] = None, actual_return_date: Optional[date] = None) -> List[Borrowing]:
        result = list(self.borrowings.values())
        if user_id is not None:
            result = [b for b in result if b.user_id == user_id]
        if actual_return_date is not None:
            result = [b for b in result if b.actual_return_date == actual_return_date]
        return result

    def get_payments(self, user_id: Optional[int] = None, status: Optional[str] = None, type: Optional[str] = None) -> List[Payment]:
        result = list(self.payments.values())
        if user_id is not None:
            result = [p for p in result if p.user_id == user_id]
        if status is not None:
            result = [p for p in result if p.status == status]
        if type is not None:
            result = [p for p in result if p.type == type]
        return result

    def process_payment(self, payment_id: int, user_id: int) -> Payment:
        payment = self.payments.get(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to pay this payment")
        if payment.status == "PAID":
            raise HTTPException(status_code=400, detail="Payment already processed")
        
        payment.status = "PAID"
        return payment


app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    version="1.0.0",
    docs_url="/api/v1/doc/swagger/"
)

library_service = LibraryService()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt_token(token)
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = library_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@app.post("/api/v1/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = library_service.get_user_by_username(form_data.username)
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_jwt_token({"sub": user.id, "username": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/", response_class=HTMLResponse)
def admin_panel(current_user: User = Depends(get_current_admin_user)):
    html_content = f"""
    <html>
        <head>
            <title>Admin Panel - Library Service</title>
        </head>
        <body>
            <h1>Welcome to the Admin Panel, {current_user.username}!</h1>
            <p>Here you can manage the library service.</p>
            <ul>
                <li><a href="/api/v1/doc/swagger/">Swagger Documentation</a></li>
            </ul>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/api/v1/books/", response_model=List[Book])
def read_books(
    title: Optional[str] = Query(None, description="Filter by book title"),
    author: Optional[str] = Query(None, description="Filter by book author")
):
    return library_service.get_books(title=title, author=author)

@app.post("/api/v1/books/", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookBase, current_user: User = Depends(get_current_admin_user)):
    return library_service.create_book(book)

@app.get("/api/v1/borrowings/", response_model=List[Borrowing])
def read_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[date] = Query(None, description="Filter by actual return date"),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin and user_id != current_user.id:
        user_id = current_user.id 
    return library_service.get_borrowings(user_id=user_id, actual_return_date=actual_return_date)

@app.post("/api/v1/borrowings/", response_model=Borrowing, status_code=status.HTTP_201_CREATED)
def create_borrowing(borrowing: BorrowingBase, current_user: User = Depends(get_current_user)):
    return library_service.create_borrowing(current_user.id, borrowing)

@app.post("/api/v1/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    return library_service.return_borrowing(borrowing_id, current_user.id)

@app.get("/api/v1/payments/", response_model=List[Payment])
def read_payments(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by payment status (PENDING, PAID)"),
    type: Optional[str] = Query(None, description="Filter by payment type (PAYMENT, FINE)"),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin and user_id != current_user.id:
        user_id = current_user.id
    return library_service.get_payments(user_id=user_id, status=status, type=type)

@app.post("/api/v1/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    return library_service.process_payment(payment_id, current_user.id)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)