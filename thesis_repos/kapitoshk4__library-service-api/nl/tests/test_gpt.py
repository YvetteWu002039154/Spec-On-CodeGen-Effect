"""
Correctness tests for: nl/outputcode/gpt/generated_code.py
Ground truth: library-service-api-main/ (Django project)

Interface notes:
  Pure-Python service-layer implementation (no Django).
  Book(title, author, inventory, daily_fee)
    - daily_fee stored as Decimal
    - raises ValidationError on negative inventory or negative daily_fee
    - .available() → bool
    - .borrow_one() → raises ValidationError when inventory == 0
    - .return_one()
  User(email, password, is_admin=False)
    - .email (lowercased), .password_hash, .is_admin
    - .check_password(password) → bool
    - No USERNAME_FIELD class attr; no username attr
  Borrowing(user_id, book_id, borrow_date, expected_return_date)
    - stores IDs, not object refs
    - .actual_return_date = None initially
    - .is_active (property)
    - .mark_returned(return_date=None)
    - .borrowing_days() → int
    - .overdue_days(on_date=None) → int
    - No total_price property (days × daily_fee must be computed externally)
  PaymentStatus.PENDING = "PENDING",  .PAID = "PAID"   (no EXPIRED)
  PaymentType.PAYMENT = "PAYMENT",    .FINE = "FINE"
  Payment(borrowing_id, user_id, amount, payment_type, status=PENDING, ...)
    - uses .amount (Decimal), not .money_to_pay
    - links by borrowing_id (int), not borrowing object
    - .mark_paid()

Known deviations:
  T04 — no Book.Cover attribute → EXPECTED FAIL.
  T05 — Borrowing stores IDs, not object references.
  T08 — no .total_price property; test uses .borrowing_days() × book.daily_fee.
  T09 — PaymentStatus has no EXPIRED value → EXPECTED FAIL.
  T11 — Payment uses .amount (not .money_to_pay) and borrowing_id (not borrowing obj).
  T12 — User has no USERNAME_FIELD class attribute → EXPECTED FAIL.
"""
import sys
import os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../outputcode/gpt")))
sys.modules.pop("generated_code", None)

from decimal import Decimal
from datetime import date
import pytest
from generated_code import (
    Book, Borrowing, Payment, User,
    PaymentStatus, PaymentType, ValidationError,
)

TODAY = date(2024, 1, 1)
NEXT_WEEK = date(2024, 1, 8)  # 7 days later


def _book(inventory=3):
    return Book(title="Clean Code", author="Martin",
                inventory=inventory, daily_fee=Decimal("1.50"))


def _user():
    return User(email="alice@example.com", password="secret")


def _borrowing(user_id=1, book_id=1, actual=None):
    br = Borrowing(user_id=user_id, book_id=book_id,
                   borrow_date=TODAY, expected_return_date=NEXT_WEEK)
    if actual is not None:
        br.actual_return_date = actual
    return br


def _payment(borrowing_id=1, user_id=1, amount=Decimal("10.50")):
    return Payment(
        borrowing_id=borrowing_id,
        user_id=user_id,
        amount=amount,
        payment_type=PaymentType.PAYMENT,
        status=PaymentStatus.PENDING,
    )


def _rejected(fn, *args, **kwargs):
    try:
        r = fn(*args, **kwargs)
        return r is False or r is None
    except Exception:
        return True


# ── T01 ───────────────────────────────────────────────────────────────────────

def test_T01_book_stores_title_and_author():
    b = _book()
    assert b.title == "Clean Code"
    assert b.author == "Martin"


# ── T02 ───────────────────────────────────────────────────────────────────────

def test_T02_book_inventory_nonnegative():
    b = _book(inventory=5)
    assert b.inventory == 5
    assert _rejected(Book, title="X", author="Y", inventory=-1, daily_fee=Decimal("1"))


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_book_has_daily_fee():
    b = _book()
    assert b.daily_fee == Decimal("1.50")


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_book_cover_hard_and_soft():
    """EXPECTED FAIL: NL spec does not describe a cover type — no Book.Cover."""
    assert hasattr(Book, "Cover"), "Book has no Cover attribute"
    assert Book.Cover.HARD is not None
    assert Book.Cover.SOFT is not None


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_borrowing_stores_user_and_book_ids():
    # NL/GPT stores IDs, not object references
    br = _borrowing(user_id=7, book_id=42)
    assert br.user_id == 7
    assert br.book_id == 42


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_borrowing_dates_and_null_actual_return():
    br = _borrowing()
    assert br.borrow_date == TODAY
    assert br.expected_return_date == NEXT_WEEK
    assert br.actual_return_date is None


# ── T07 ───────────────────────────────────────────────────────────────────────

def test_T07_book_borrow_one_rejects_zero_inventory():
    # NL/GPT uses book.borrow_one() which raises when inventory==0
    b = _book(inventory=0)
    assert _rejected(b.borrow_one)


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_borrowing_days_times_fee_equals_expected_price():
    # No .total_price; verify borrowing_days() * daily_fee matches expected
    br = _borrowing()
    book = _book()
    days = br.borrowing_days()
    price = book.daily_fee * days
    assert price > 0


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_payment_status_values():
    assert PaymentStatus.PENDING is not None
    assert PaymentStatus.PAID is not None
    # EXPECTED FAIL: no EXPIRED in PaymentStatus
    assert hasattr(PaymentStatus, "EXPIRED"), "PaymentStatus has no EXPIRED"


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_payment_type_values():
    assert PaymentType.PAYMENT is not None
    assert PaymentType.FINE is not None
    assert PaymentType.PAYMENT != PaymentType.FINE


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_payment_stores_amount_starts_pending():
    # Uses .amount (not .money_to_pay); links by borrowing_id not borrowing object
    p = _payment(borrowing_id=5, amount=Decimal("10.50"))
    assert p.amount == Decimal("10.50")
    assert p.borrowing_id == 5
    assert p.status == PaymentStatus.PENDING


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    u = _user()
    assert u.email == "alice@example.com"
    # EXPECTED FAIL: no USERNAME_FIELD on User class
    assert hasattr(User, "USERNAME_FIELD"), "User has no USERNAME_FIELD"
    assert User.USERNAME_FIELD == "email"
