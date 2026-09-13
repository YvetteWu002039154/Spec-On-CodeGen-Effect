import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

SECRET_KEY = "library_secret_key_for_jwt"
ALGORITHM = "HS256"

def create_jwt(data: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = data.copy()
    payload_data["exp"] = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"

def decode_jwt(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected_signature = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid signature")
        padded_payload = payload + "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded_payload).decode())
        if data.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            raise ValueError("Token expired")
        return data
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

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
    borrow_date: datetime
    expected_return_date: datetime
    actual_return_date: Optional[datetime] = None

class BorrowingCreate(BaseModel):
    book_id: int
    days: int = Field(..., gt=0)

class Payment(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    status: str
    payment_type: str

users_db: Dict[int, User] = {}
books_db: Dict[int, Book] = {}
borrowings_db: Dict[int, Borrowing] = {}
payments_db: Dict[int, Payment] = {}

user_id_counter = 1
book_id_counter = 1
borrowing_id_counter = 1
payment_id_counter = 1

users_db[user_id_counter] = User(
    id=user_id_counter,
    email="admin@library.com",
    password_hash=hashlib.sha256("admin".encode()).hexdigest(),
    is_admin=True
)
user_id_counter += 1

app = FastAPI(
    title="Library Service API",
    description="API Library service for borrowing books.",
    docs_url="/api/v1/doc/swagger/"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id or int(user_id) not in users_db:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return users_db[int(user_id)]

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    global user_id_counter
    for u in users_db.values():
        if u.email == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        id=user_id_counter,
        email=user.email,
        password_hash=hashlib.sha256(user.password.encode()).hexdigest(),
        is_admin=user.is_admin
    )
    users_db[user_id_counter] = new_user
    user_id_counter += 1
    return new_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    hashed_pw = hashlib.sha256(form_data.password.encode()).hexdigest()
    for user in users_db.values():
        if user.email == form_data.username and user.password_hash == hashed_pw:
            token = create_jwt({"sub": str(user.id), "is_admin": user.is_admin})
            return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect email or password")

@app.get("/admin/")
def admin_panel(admin: User = Depends(get_admin_user)):
    return {
        "message": "Welcome to the Admin Panel",
        "total_users": len(users_db),
        "total_books": len(books_db),
        "total_borrowings": len(borrowings_db),
        "total_payments": len(payments_db)
    }

@app.post("/books", response_model=Book)
def add_book(book: BookCreate, admin: User = Depends(get_admin_user)):
    global book_id_counter
    new_book = Book(
        id=book_id_counter,
        title=book.title,
        author=book.author,
        inventory=book.inventory,
        daily_fee=book.daily_fee
    )
    books_db[book_id_counter] = new_book
    book_id_counter += 1
    return new_book

@app.get("/books", response_model=List[Book])
def list_books():
    return list(books_db.values())

@app.post("/borrowings", response_model=Borrowing)
def create_borrowing(borrowing: BorrowingCreate, current_user: User = Depends(get_current_user)):
    global borrowing_id_counter, payment_id_counter
    book = books_db.get(borrowing.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.inventory <= 0:
        raise HTTPException(status_code=400, detail="Book not available in inventory")

    user_borrowings = [b.id for b in borrowings_db.values() if b.user_id == current_user.id]
    pending_payments = [p for p in payments_db.values() if p.borrowing_id in user_borrowings and p.status == "PENDING"]
    if pending_payments:
        raise HTTPException(status_code=400, detail="Cannot borrow new books with pending payments")

    book.inventory -= 1
    
    borrow_date = datetime.now(timezone.utc)
    expected_return_date = borrow_date + timedelta(days=borrowing.days)
    
    new_borrowing = Borrowing(
        id=borrowing_id_counter,
        user_id=current_user.id,
        book_id=book.id,
        borrow_date=borrow_date,
        expected_return_date=expected_return_date
    )
    borrowings_db[borrowing_id_counter] = new_borrowing
    
    amount = book.daily_fee * borrowing.days
    new_payment = Payment(
        id=payment_id_counter,
        borrowing_id=new_borrowing.id,
        amount=amount,
        status="PENDING",
        payment_type="PAYMENT"
    )
    payments_db[payment_id_counter] = new_payment
    
    borrowing_id_counter += 1
    payment_id_counter += 1
    
    return new_borrowing

@app.get("/borrowings", response_model=List[Borrowing])
def list_borrowings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    is_returned: Optional[bool] = Query(None, description="Filter by actual return date presence"),
    current_user: User = Depends(get_current_user)
):
    results = list(borrowings_db.values())
    
    if not current_user.is_admin:
        results = [b for b in results if b.user_id == current_user.id]
    elif user_id is not None:
        results = [b for b in results if b.user_id == user_id]
        
    if is_returned is not None:
        if is_returned:
            results = [b for b in results if b.actual_return_date is not None]
        else:
            results = [b for b in results if b.actual_return_date is None]
            
    return results

@app.post("/borrowings/{borrowing_id}/return", response_model=Borrowing)
def return_borrowing(borrowing_id: int, current_user: User = Depends(get_current_user)):
    global payment_id_counter
    borrowing = borrowings_db.get(borrowing_id)
    if not borrowing:
        raise HTTPException(status_code=404, detail="Borrowing not found")
    if not current_user.is_admin and borrowing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to return this borrowing")
    if borrowing.actual_return_date is not None:
        raise HTTPException(status_code=400, detail="Borrowing already returned")
        
    borrowing.actual_return_date = datetime.now(timezone.utc)
    
    book = books_db.get(borrowing.book_id)
    if book:
        book.inventory += 1
        
    if borrowing.actual_return_date > borrowing.expected_return_date:
        overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
        if overdue_days > 0 and book:
            fine_amount = overdue_days * book.daily_fee * 2.0
            new_fine = Payment(
                id=payment_id_counter,
                borrowing_id=borrowing.id,
                amount=fine_amount,
                status="PENDING",
                payment_type="FINE"
            )
            payments_db[payment_id_counter] = new_fine
            payment_id_counter += 1
            
    return borrowing

@app.get("/payments", response_model=List[Payment])
def list_payments(current_user: User = Depends(get_current_user)):
    if current_user.is_admin:
        return list(payments_db.values())
    user_borrowings = {b.id for b in borrowings_db.values() if b.user_id == current_user.id}
    return [p for p in payments_db.values() if p.borrowing_id in user_borrowings]

@app.post("/payments/{payment_id}/pay", response_model=Payment)
def pay_payment(payment_id: int, current_user: User = Depends(get_current_user)):
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    borrowing = borrowings_db.get(payment.borrowing_id)
    if not current_user.is_admin and borrowing and borrowing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this payment")
        
    if payment.status == "PAID":
        raise HTTPException(status_code=400, detail="Payment already paid")
        
    payment.status = "PAID"
    return payment

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)