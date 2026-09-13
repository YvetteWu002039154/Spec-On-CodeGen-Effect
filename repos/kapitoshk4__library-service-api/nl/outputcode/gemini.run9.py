import uvicorn
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt

SECRET_KEY = "library_secret_key_for_jwt_auth"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    docs_url="/api/v1/doc/swagger/",
    redoc_url=None
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class User(BaseModel):
    id: int
    email: str
    password: str
    is_admin: bool

class BookBase(BaseModel):
    title: str
    author: str
    inventory: int
    daily_fee: float

class Book(BookBase):
    id: int

class BorrowingBase(BaseModel):
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
    amount: float
    status: str 
    payment_type: str 

class Token(BaseModel):
    access_token: str
    token_type: str

users_db: List[User] = [
    User(id=1, email="admin@library.com", password="adminpassword", is_admin=True),
    User(id=2, email="user@library.com", password="userpassword", is_admin=False)
]
books_db: List[Book] = [
    Book(id=1, title="The Great Gatsby", author="F. Scott Fitzgerald", inventory=5, daily_fee=2.0),
    Book(id=2, title="1984", author="George Orwell", inventory=2, daily_fee=1.5)
]
borrowings_db: List[Borrowing] = []
payments_db: List[Payment] = []

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = next((u for u in users_db if u.email == email), None)
    if user is None:
        raise credentials_exception
    return user

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in users_db if u.email == form_data.username and u.password == form_data.password), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/")
def admin_panel(current_user: User = Depends(get_admin_user)):
    return {
        "message": "Welcome to the Admin Panel",
        "total_users": len(users_db),
        "total_books": len(books_db),
        "total_borrowings": len(borrowings_db),
        "total_payments": len(payments_db)
    }

@app.get("/books", response_model=List[Book])
def get_books(
    author: Optional[str] = Query(None, description="Filter by author"),
    title: Optional[str] = Query(None, description="Filter by title")
):
    results = books_db
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    if title:
        results = [b for b in results if title.lower() in b.title.lower()]
    return results

@app.post("/books", response_model=Book)
def create_book(book: BookBase, current_user: User = Depends(get_admin_user)):
    new_id = max([b.id for b in books_db], default=0) + 1
    new_book = Book(id=new_id, **book.dict())
    books_db.append(new_book)
    return new_book

@app.get("/borrowings", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[date] = Query(None, description="Filter by actual return date"),
    current_user: User = Depends(get_current_user)
):
    results = borrowings_db
    if not current_user.is_admin:
        results = [b for b in results if b.user_id == current_user.id]
    elif user_id is not None:
        results = [b for b in results if b.user_id == user_id]

    if actual_return_date is not None:
        results = [b for b in results if b.actual_return_date == actual_return_date]

    return results

@app.post("/borrowings", response_model=Borrowing)
def create_borrowing(borrowing_data: BorrowingBase, current_user: User = Depends(get_current_user)):
    book = next((b for b in books_db if b.id == borrowing_data.book_id), None)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.inventory <= 0:
        raise HTTPException(status_code=400, detail="Book is currently out of stock")
    if borrowing_data.expected_return_date <= date.today():
        raise HTTPException(status_code=400, detail="Expected return date must be in the future")

    book.inventory -= 1
    borrow_date = date.today()
    new_id = max([b.id for b in borrowings_db], default=0) + 1
    
    borrowing = Borrowing(
        id=new_id,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=borrow_date,
        expected_return_date=borrowing_data.expected_return_date
    )
    borrowings_db.append(borrowing)

    days = (borrowing_data.expected_return_date - borrow_date).days
    payment_id = max([p.id for p in payments_db], default=0) + 1
    payment = Payment(
        id=payment_id,
        borrowing_id=borrowing.id,
        amount=days * book.daily_fee,
        status="PENDING",
        payment_type="PAYMENT"
    )
    payments_db.append(payment)
    
    return borrowing

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    borrowing = next((b for b in borrowings_db if b.id == borrowing_id), None)
    if not borrowing:
        raise HTTPException(status_code=404, detail="Borrowing not found")
    if not current_user.is_admin and borrowing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to return this borrowing")
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=400, detail="Borrowing has already been returned")

    borrowing.actual_return_date = date.today()
    book = next((b for b in books_db if b.id == borrowing.book_id))
    book.inventory += 1

    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_multiplier = 2.0
        fine_amount = overdue_days * book.daily_fee * fine_multiplier
        
        payment_id = max([p.id for p in payments_db], default=0) + 1
        fine_payment = Payment(
            id=payment_id,
            borrowing_id=borrowing.id,
            amount=fine_amount,
            status="PENDING",
            payment_type="FINE"
        )
        payments_db.append(fine_payment)

    return borrowing

@app.get("/payments", response_model=List[Payment])
def get_payments(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, PAID)"),
    payment_type: Optional[str] = Query(None, description="Filter by type (PAYMENT, FINE)"),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_admin:
        results = payments_db
    else:
        user_borrowing_ids = [b.id for b in borrowings_db if b.user_id == current_user.id]
        results = [p for p in payments_db if p.borrowing_id in user_borrowing_ids]

    if status:
        results = [p for p in results if p.status.upper() == status.upper()]
    if payment_type:
        results = [p for p in results if p.payment_type.upper() == payment_type.upper()]

    return results

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    payment = next((p for p in payments_db if p.id == payment_id), None)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    borrowing = next((b for b in borrowings_db if b.id == payment.borrowing_id))
    if not current_user.is_admin and borrowing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this payment")

    if payment.status == "PAID":
        raise HTTPException(status_code=400, detail="Payment is already paid")

    payment.status = "PAID"
    return payment

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)