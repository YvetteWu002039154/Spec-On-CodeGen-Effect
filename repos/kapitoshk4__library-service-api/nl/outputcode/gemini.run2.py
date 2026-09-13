import datetime
import enum
from typing import List, Optional

import jwt
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"

class PaymentType(enum.Enum):
    PAYMENT = "PAYMENT"
    FINE = "FINE"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Integer, default=0)
    
    borrowings = relationship("Borrowing", back_populates="user")

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    inventory = Column(Integer, default=1)
    daily_fee = Column(Float, default=1.0)
    
    borrowings = relationship("Borrowing", back_populates="book")

class Borrowing(Base):
    __tablename__ = "borrowings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    borrow_date = Column(Date, default=datetime.date.today)
    expected_return_date = Column(Date)
    actual_return_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="borrowings")
    book = relationship("Book", back_populates="borrowings")
    payments = relationship("Payment", back_populates="borrowing")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    borrowing_id = Column(Integer, ForeignKey("borrowings.id"))
    amount = Column(Float)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_type = Column(SQLEnum(PaymentType), default=PaymentType.PAYMENT)

    borrowing = relationship("Borrowing", back_populates="payments")

class UserCreate(BaseModel):
    email: str
    password: str
    is_admin: bool = False

class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool

    class Config:
        orm_mode = True
        from_attributes = True

class BookCreate(BaseModel):
    title: str
    author: str
    inventory: int
    daily_fee: float

class BookResponse(BookCreate):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True

class BorrowingCreate(BaseModel):
    book_id: int
    days: int

class BorrowingResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrow_date: datetime.date
    expected_return_date: datetime.date
    actual_return_date: Optional[datetime.date]

    class Config:
        orm_mode = True
        from_attributes = True

class PaymentResponse(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    status: PaymentStatus
    payment_type: PaymentType

    class Config:
        orm_mode = True
        from_attributes = True

SECRET_KEY = "library_secret_key_for_jwt_auth"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

class LibraryService:
    def __init__(self, db: Session):
        self.db = db

    def create_book(self, book_data: BookCreate) -> Book:
        book = Book(
            title=book_data.title,
            author=book_data.author,
            inventory=book_data.inventory,
            daily_fee=book_data.daily_fee
        )
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book

    def get_books(self) -> List[Book]:
        return self.db.query(Book).all()

    def borrow_book(self, user: User, borrow_data: BorrowingCreate) -> Borrowing:
        book = self.db.query(Book).filter(Book.id == borrow_data.book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.inventory <= 0:
            raise HTTPException(status_code=400, detail="Book is currently out of stock")

        book.inventory -= 1
        borrow_date = datetime.date.today()
        expected_return_date = borrow_date + datetime.timedelta(days=borrow_data.days)

        borrowing = Borrowing(
            user_id=user.id,
            book_id=book.id,
            borrow_date=borrow_date,
            expected_return_date=expected_return_date
        )
        self.db.add(borrowing)
        self.db.commit()
        self.db.refresh(borrowing)

        payment_amount = book.daily_fee * borrow_data.days
        payment = Payment(
            borrowing_id=borrowing.id,
            amount=payment_amount,
            status=PaymentStatus.PENDING,
            payment_type=PaymentType.PAYMENT
        )
        self.db.add(payment)
        self.db.commit()

        return borrowing

    def return_book(self, borrowing_id: int, user: User) -> Borrowing:
        borrowing = self.db.query(Borrowing).filter(Borrowing.id == borrowing_id).first()
        if not borrowing:
            raise HTTPException(status_code=404, detail="Borrowing not found")
        if borrowing.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to return this book")
        if borrowing.actual_return_date:
            raise HTTPException(status_code=400, detail="Book has already been returned")

        borrowing.actual_return_date = datetime.date.today()
        book = self.db.query(Book).filter(Book.id == borrowing.book_id).first()
        book.inventory += 1

        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_multiplier = 2.0 
            fine_amount = overdue_days * book.daily_fee * fine_multiplier
            fine_payment = Payment(
                borrowing_id=borrowing.id,
                amount=fine_amount,
                status=PaymentStatus.PENDING,
                payment_type=PaymentType.FINE
            )
            self.db.add(fine_payment)

        self.db.commit()
        self.db.refresh(borrowing)
        return borrowing

    def get_borrowings(self, user_id: Optional[int] = None, actual_return_date: Optional[datetime.date] = None) -> List[Borrowing]:
        query = self.db.query(Borrowing)
        if user_id is not None:
            query = query.filter(Borrowing.user_id == user_id)
        if actual_return_date is not None:
            query = query.filter(Borrowing.actual_return_date == actual_return_date)
        return query.all()

    def pay_payment(self, payment_id: int, user: User) -> Payment:
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        borrowing = self.db.query(Borrowing).filter(Borrowing.id == payment.borrowing_id).first()
        if borrowing.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to pay this payment")
        
        if payment.status == PaymentStatus.PAID:
            raise HTTPException(status_code=400, detail="Payment is already paid")

        payment.status = PaymentStatus.PAID
        self.db.commit()
        self.db.refresh(payment)
        return payment

app = FastAPI(
    title="Library Service API",
    docs_url="/api/v1/doc/swagger/",
    openapi_url="/api/v1/openapi.json"
)

Base.metadata.create_all(bind=engine)

@app.post("/users/", response_model=UserResponse, tags=["Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(email=user.email, hashed_password=user.password, is_admin=user.is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/", tags=["Admin"])
def admin_panel(current_user: User = Depends(get_admin_user)):
    return {
        "message": "Welcome to the Admin Panel",
        "admin_email": current_user.email,
        "status": "Active"
    }

@app.post("/books/", response_model=BookResponse, tags=["Books"])
def add_book(book: BookCreate, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    service = LibraryService(db)
    return service.create_book(book)

@app.get("/books/", response_model=List[BookResponse], tags=["Books"])
def list_books(db: Session = Depends(get_db)):
    service = LibraryService(db)
    return service.get_books()

@app.post("/borrowings/", response_model=BorrowingResponse, tags=["Borrowings"])
def borrow_book(borrow_data: BorrowingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = LibraryService(db)
    return service.borrow_book(current_user, borrow_data)

@app.post("/borrowings/{borrowing_id}/return", response_model=BorrowingResponse, tags=["Borrowings"])
def return_book(borrowing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = LibraryService(db)
    return service.return_book(borrowing_id, current_user)

@app.get("/borrowings/", response_model=List[BorrowingResponse], tags=["Borrowings"])
def list_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    actual_return_date: Optional[datetime.date] = Query(None, description="Filter by actual return date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = LibraryService(db)
    if not current_user.is_admin:
        if user_id is not None and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view other users' borrowings")
        user_id = current_user.id
    return service.get_borrowings(user_id=user_id, actual_return_date=actual_return_date)

@app.post("/payments/{payment_id}/pay", response_model=PaymentResponse, tags=["Payments"])
def pay_payment(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = LibraryService(db)
    return service.pay_payment(payment_id, current_user)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)