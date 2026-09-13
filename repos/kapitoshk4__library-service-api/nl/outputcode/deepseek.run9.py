from datetime import datetime, timedelta
from typing import Optional, List
import secrets
import uuid

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Float, select, func, and_
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, selectinload
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

# ---- Security ----
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---- Database setup ----
DATABASE_URL = "sqlite+aiosqlite:///./library.db"
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ---- Models ----
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    borrowings = relationship("Borrowing", back_populates="user")
    payments = relationship("Payment", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn = Column(String, unique=True, index=True, nullable=False)
    is_available = Column(Boolean, default=True)

    borrowings = relationship("Borrowing", back_populates="book")


class Borrowing(Base):
    __tablename__ = "borrowings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    borrowed_date = Column(DateTime, default=datetime.utcnow)
    expected_return_date = Column(DateTime, nullable=False)
    actual_return_date = Column(DateTime, nullable=True)
    is_returned = Column(Boolean, default=False)

    user = relationship("User", back_populates="borrowings")
    book = relationship("Book", back_populates="borrowings")
    payments = relationship("Payment", back_populates="borrowing")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    borrowing_id = Column(Integer, ForeignKey("borrowings.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(String, nullable=False)  # "borrowing_fee" or "fine"
    payment_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="paid")  # paid, pending

    user = relationship("User", back_populates="payments")
    borrowing = relationship("Borrowing", back_populates="payments")


# ---- Pydantic schemas ----
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserOut(UserBase):
    id: int
    is_active: bool
    is_staff: bool
    created_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class BookBase(BaseModel):
    title: str
    author: str
    isbn: str


class BookCreate(BookBase):
    pass


class BookOut(BookBase):
    id: int
    is_available: bool

    class Config:
        orm_mode = True


class BorrowingCreate(BaseModel):
    book_id: int
    expected_return_date: datetime


class BorrowingOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrowed_date: datetime
    expected_return_date: datetime
    actual_return_date: Optional[datetime]
    is_returned: bool

    class Config:
        orm_mode = True


class PaymentOut(BaseModel):
    id: int
    user_id: int
    borrowing_id: int
    amount: float
    payment_type: str
    payment_date: datetime
    status: str

    class Config:
        orm_mode = True


class ReturnBookResponse(BaseModel):
    message: str
    fine: Optional[float] = None


# ---- Dependencies ----
async def get_db():
    async with async_session() as session:
        yield session


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
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
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
        current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


# ---- CRUD functions ----
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    hashed = get_password_hash(user_in.password)
    user = User(email=user_in.email, password_hash=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_book(db: AsyncSession, book_id: int) -> Optional[Book]:
    result = await db.execute(select(Book).filter(Book.id == book_id))
    return result.scalars().first()


async def get_borrowing(db: AsyncSession, borrowing_id: int) -> Optional[Borrowing]:
    result = await db.execute(select(Borrowing).filter(Borrowing.id == borrowing_id))
    return result.scalars().first()


# ---- App and Admin ----
app = FastAPI(
    title="Library Service API",
    docs_url="/api/v1/doc/swagger",
    openapi_url="/api/v1/openapi.json",
)

# Admin setup
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        if not email or not password:
            return False
        async with async_session() as db:
            user = await get_user_by_email(db, email)
            if user and user.is_staff and verify_password(password, user.password_hash):
                request.session.update({"user_id": user.id})
                return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")
        if not user_id:
            return False
        async with async_session() as db:
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalars().first()
            return user is not None and user.is_staff


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.is_active, User.is_staff, User.created_at]


class BookAdmin(ModelView, model=Book):
    column_list = [Book.id, Book.title, Book.author, Book.isbn, Book.is_available]


class BorrowingAdmin(ModelView, model=Borrowing):
    column_list = [Borrowing.id, Borrowing.user, Borrowing.book, Borrowing.borrowed_date, Borrowing.expected_return_date, Borrowing.actual_return_date, Borrowing.is_returned]


class PaymentAdmin(ModelView, model=Payment):
    column_list = [Payment.id, Payment.user, Payment.borrowing, Payment.amount, Payment.payment_type, Payment.payment_date, Payment.status]


admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=SECRET_KEY))
admin.add_view(UserAdmin)
admin.add_view(BookAdmin)
admin.add_view(BorrowingAdmin)
admin.add_view(PaymentAdmin)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/api/v1/doc/swagger")


# ---- Auth routes ----
@app.post("/api/v1/auth/register", response_model=UserOut, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await create_user(db, user_in)
    return user


@app.post("/api/v1/auth/token", response_model=Token)
async def login(
        db: AsyncSession = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ---- Book routes ----
@app.get("/api/v1/books/", response_model=List[BookOut])
async def list_books(
        title: Optional[str] = Query(None),
        author: Optional[str] = Query(None),
        isbn: Optional[str] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db)
):
    query = select(Book)
    filters = []
    if title:
        filters.append(Book.title.ilike(f"%{title}%"))
    if author:
        filters.append(Book.author.ilike(f"%{author}%"))
    if isbn:
        filters.append(Book.isbn.ilike(f"%{isbn}%"))
    if filters:
        query = query.where(and_(*filters))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@app.post("/api/v1/books/", response_model=BookOut, status_code=201)
async def create_book(
        book_in: BookCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    new_book = Book(**book_in.dict())
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    return new_book


@app.put("/api/v1/books/{book_id}", response_model=BookOut)
async def update_book(
        book_id: int,
        book_in: BookCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    for field, value in book_in.dict().items():
        setattr(book, field, value)
    await db.commit()
    await db.refresh(book)
    return book


@app.delete("/api/v1/books/{book_id}", status_code=204)
async def delete_book(
        book_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.delete(book)
    await db.commit()
    return None


# ---- Borrowing routes ----
@app.get("/api/v1/borrowings/", response_model=List[BorrowingOut])
async def list_borrowings(
        user_id: Optional[int] = Query(None),
        actual_return_date_min: Optional[datetime] = Query(None),
        actual_return_date_max: Optional[datetime] = Query(None),
        is_returned: Optional[bool] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    query = select(Borrowing)
    filters = []
    if user_id:
        filters.append(Borrowing.user_id == user_id)
    if actual_return_date_min:
        filters.append(Borrowing.actual_return_date >= actual_return_date_min)
    if actual_return_date_max:
        filters.append(Borrowing.actual_return_date <= actual_return_date_max)
    if is_returned is not None:
        filters.append(Borrowing.is_returned == is_returned)
    # Non-admin users can only see their own borrowings unless they are staff
    if not current_user.is_staff:
        filters.append(Borrowing.user_id == current_user.id)
    if filters:
        query = query.where(and_(*filters))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@app.post("/api/v1/borrowings/", response_model=BorrowingOut, status_code=201)
async def create_borrowing(
        borrowing_in: BorrowingCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    book = await get_book(db, borrowing_in.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.is_available:
        raise HTTPException(status_code=400, detail="Book is not available")

    # Check if user already has an active borrowing for this book
    active_result = await db.execute(
        select(Borrowing).filter(
            Borrowing.user_id == current_user.id,
            Borrowing.book_id == book.id,
            Borrowing.is_returned == False
        )
    )
    if active_result.scalars().first():
        raise HTTPException(status_code=400, detail="You have already borrowed this book and not returned it")

    borrowing = Borrowing(
        user_id=current_user.id,
        book_id=book.id,
        expected_return_date=borrowing_in.expected_return_date
    )
    book.is_available = False
    db.add(borrowing)
    await db.commit()
    await db.refresh(borrowing)

    # Automatically create a payment for borrowing fee (e.g., fixed $5)
    borrowing_fee_amount = 5.0
    payment = Payment(
        user_id=current_user.id,
        borrowing_id=borrowing.id,
        amount=borrowing_fee_amount,
        payment_type="borrowing_fee",
        status="pending"
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return borrowing


@app.put("/api/v1/borrowings/{borrowing_id}/return", response_model=ReturnBookResponse)
async def return_book(
        borrowing_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    borrowing = await get_borrowing(db, borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=404, detail="Borrowing not found")
    if borrowing.is_returned:
        raise HTTPException(status_code=400, detail="Book already returned")
    if borrowing.user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="You can only return your own borrowings")

    borrowing.actual_return_date = datetime.utcnow()
    borrowing.is_returned = True
    borrowing.book.is_available = True

    fine_amount = 0.0
    # Calculate fine if overdue
    if borrowing.actual_return_date > borrowing.expected_return_date:
        days_overdue = (borrowing.actual_return_date - borrowing.expected_return_date).days
        fine_per_day = 1.0
        fine_amount = days_overdue * fine_per_day
        if fine_amount > 0:
            fine_payment = Payment(
                user_id=borrowing.user_id,
                borrowing_id=borrowing.id,
                amount=fine_amount,
                payment_type="fine",
                status="pending"
            )
            db.add(fine_payment)

    await db.commit()
    return ReturnBookResponse(message="Book returned successfully", fine=fine_amount if fine_amount > 0 else None)


# ---- Payment routes ----
@app.get("/api/v1/payments/", response_model=List[PaymentOut])
async def list_payments(
        user_id: Optional[int] = Query(None),
        borrowing_id: Optional[int] = Query(None),
        payment_type: Optional[str] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    query = select(Payment)
    filters = []
    if user_id:
        filters.append(Payment.user_id == user_id)
    if borrowing_id:
        filters.append(Payment.borrowing_id == borrowing_id)
    if payment_type:
        filters.append(Payment.payment_type == payment_type)
    if not current_user.is_staff:
        filters.append(Payment.user_id == current_user.id)
    if filters:
        query = query.where(and_(*filters))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@app.post("/api/v1/payments/{payment_id}/pay", response_model=PaymentOut)
async def process_payment(
        payment_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    payment_result = await db.execute(select(Payment).filter(Payment.id == payment_id))
    payment = payment_result.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Not authorized to pay this payment")
    if payment.status == "paid":
        raise HTTPException(status_code=400, detail="Payment already completed")
    # Simulate payment processing
    payment.status = "paid"
    payment.payment_date = datetime.utcnow()
    await db.commit()
    await db.refresh(payment)
    return payment


if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True)