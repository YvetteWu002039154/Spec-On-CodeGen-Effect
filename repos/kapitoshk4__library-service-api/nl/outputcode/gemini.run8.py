import hashlib
import jwt
import uvicorn
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

SECRET_KEY = "super-secret-library-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    docs_url="/api/v1/doc/swagger/"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"

class PaymentType(str, Enum):
    PAYMENT = "PAYMENT"
    FINE = "FINE"

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class User(UserBase):
    id: int
    is_admin: bool

class UserInDB(User):
    password_hash: str

class BookBase(BaseModel):
    title: str
    author: str
    inventory: int
    daily_fee: float

class Book(BookBase):
    id: int

class BorrowingBase(BaseModel):
    book_id: int
    days: int

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
    payment_type: PaymentType

class Database:
    def __init__(self):
        self.users: Dict[int, UserInDB] = {}
        self.books: Dict[int, Book] = {}
        self.borrowings: Dict[int, Borrowing] = {}
        self.payments: Dict[int, Payment] = {}
        
        self.user_id_counter = 1
        self.book_id_counter = 1
        self.borrowing_id_counter = 1
        self.payment_id_counter = 1

    def add_user(self, user_create: UserCreate) -> UserInDB:
        user = UserInDB(
            id=self.user_id_counter,
            email=user_create.email,
            password_hash=get_password_hash(user_create.password),
            is_admin=user_create.is_admin
        )
        self.users[self.user_id_counter] = user
        self.user_id_counter += 1
        return user

db = Database()

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
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
        
    user = next((u for u in db.users.values() if u.email == email), None)
    if user is None:
        raise credentials_exception
    return user

def get_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@app.on_event("startup")
def startup_event():
    if not any(u.email == "admin@library.com" for u in db.users.values()):
        db.add_user(UserCreate(email="admin@library.com", password="admin", is_admin=True))
    if not db.books:
        book = Book(id=db.book_id_counter, title="1984", author="George Orwell", inventory=5, daily_fee=1.5)
        db.books[db.book_id_counter] = book
        db.book_id_counter += 1

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((u for u in db.users.values() if u.email == form_data.username), None)
    if not user or not verify_password(form_data.password, user.password_hash):
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
def admin_panel(current_user: UserInDB = Depends(get_admin_user)):
    return {
        "message": "Welcome to the Admin Panel",
        "admin_email": current_user.email,
        "total_users": len(db.users),
        "total_books": len(db.books),
        "total_borrowings": len(db.borrowings),
        "total_payments": len(db.payments)
    }

@app.post("/users/", response_model=User)
def create_user(user: UserCreate):
    if any(u.email == user.email for u in db.users.values()):
        raise HTTPException(status_code=400, detail="Email already registered")
    return db.add_user(user)

@app.get("/books/", response_model=List[Book])
def get_books(title: Optional[str] = None, author: Optional[str] = None):
    results = list(db.books.values())
    if title:
        results = [b for b in results if title.lower() in b.title.lower()]
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    return results

@app.post("/books/", response_model=Book)
def create_book(book: BookBase, current_user: UserInDB = Depends(get_admin_user)):
    new_book = Book(id=db.book_id_counter, **book.dict())
    db.books[db.book_id_counter] = new_book
    db.book_id_counter += 1
    return new_book

@app.get("/borrowings/", response_model=List[Borrowing])
def get_borrowings(
    user_id: Optional[int] = None,
    actual_return_date: Optional[date] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    results = list(db.borrowings.values())
    
    if not current_user.is_admin:
        results = [b for b in results if b.user_id == current_user.id]
    elif user_id is not None:
        results = [b for b in results if b.user_id == user_id]
        
    if actual_return_date is not None:
        results = [b for b in results if b.actual_return_date == actual_return_date]
        
    return results

@app.post("/borrowings/", response_model=Borrowing)
def create_borrowing(
    borrowing_req: BorrowingBase,
    current_user: UserInDB = Depends(get_current_user)
):
    book = db.books.get(borrowing_req.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.inventory < 1:
        raise HTTPException(status_code=400, detail="Book is out of stock")
        
    book.inventory -= 1
    
    borrow_date = date.today()
    expected_return_date = borrow_date + timedelta(days=borrowing_req.days)
    
    borrowing = Borrowing(
        id=db.borrowing_id_counter,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=borrow_date,
        expected_return_date=expected_return_date
    )
    db.borrowings[borrowing.id] = borrowing
    db.borrowing_id_counter += 1
    
    payment = Payment(
        id=db.payment_id_counter,
        borrowing_id=borrowing.id,
        amount=book.daily_fee * borrowing_req.days,
        status=PaymentStatus.PENDING,
        payment_type=PaymentType.PAYMENT
    )
    db.payments[payment.id] = payment
    db.payment_id_counter += 1
    
    return borrowing

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(
    borrowing_id: int,
    current_user: UserInDB = Depends(get_current_user)
):
    borrowing = db.borrowings.get(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=404, detail="Borrowing not found")
        
    if borrowing.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to return this borrowing")
        
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=400, detail="Borrowing has already been returned")
        
    borrowing.actual_return_date = date.today()
    
    book = db.books.get(borrowing.book_id)
    if book:
        book.inventory += 1
        
    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_multiplier = 2.0
        fine_amount = overdue_days * book.daily_fee * fine_multiplier
        
        fine_payment = Payment(
            id=db.payment_id_counter,
            borrowing_id=borrowing.id,
            amount=fine_amount,
            status=PaymentStatus.PENDING,
            payment_type=PaymentType.FINE
        )
        db.payments[fine_payment.id] = fine_payment
        db.payment_id_counter += 1
        
    return borrowing

@app.get("/payments/", response_model=List[Payment])
def get_payments(
    status: Optional[PaymentStatus] = None,
    payment_type: Optional[PaymentType] = None,
    current_user: UserInDB = Depends(get_current_user)
):
    if current_user.is_admin:
        results = list(db.payments.values())
    else:
        user_borrowing_ids = {b.id for b in db.borrowings.values() if b.user_id == current_user.id}
        results = [p for p in db.payments.values() if p.borrowing_id in user_borrowing_ids]
        
    if status:
        results = [p for p in results if p.status == status]
    if payment_type:
        results = [p for p in results if p.payment_type == payment_type]
        
    return results

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(
    payment_id: int,
    current_user: UserInDB = Depends(get_current_user)
):
    payment = db.payments.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    borrowing = db.borrowings.get(payment.borrowing_id)
    if borrowing and borrowing.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to pay this payment")
        
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Payment is already paid")
        
    payment.status = PaymentStatus.PAID
    return payment

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)