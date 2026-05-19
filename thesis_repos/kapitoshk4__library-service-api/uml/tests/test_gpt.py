"""
Correctness tests for: uml/outputcode/gpt/generated_code.py
Ground truth: library-service-api-main/ (Django project with books/borrowings/payments/users apps)

Interface notes:
  Book(title, author, cover, daily_fee, inventory)
    - cover: Book.Cover enum (HARD/SOFT)
    - daily_fee: Decimal; raises ValueError on negative
    - raises ValueError on negative inventory
  User(email, full_name="")
    - User.USERNAME_FIELD = "email", User.username = None
  Borrowing(book, user, borrow_date, expected_return_date, actual_return_date=None)
    - __init__ calls clean() which calls validate_borrowing(book.inventory)
    - raises ValueError if expected_return_date < borrow_date or inventory <= 0
    - .total_price = (end_date - borrow_date).days * book.daily_fee
  Payment(borrowing, money_to_pay, session_id, session_url, status, type)
    - Payment.Status: PENDING, PAID, EXPIRED  (str Enum)
    - Payment.Type:   PAYMENT, FINE           (str Enum)
    - raises ValueError on invalid status/type or negative money_to_pay
"""
import sys
import os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../outputcode/gpt")))
sys.modules.pop("generated_code", None)

from decimal import Decimal
from datetime import date
import pytest
from generated_code import Book, Borrowing, Payment, User

TODAY = date(2024, 1, 1)
NEXT_WEEK = date(2024, 1, 8)  # 7 days later


def _book(inventory=3):
    return Book(title="Clean Code", author="Martin", cover=Book.Cover.HARD,
                daily_fee=Decimal("1.50"), inventory=inventory)


def _user():
    return User(email="alice@example.com")


def _borrowing(book=None, user=None, actual=None):
    return Borrowing(
        book=book or _book(),
        user=user or _user(),
        borrow_date=TODAY,
        expected_return_date=NEXT_WEEK,
        actual_return_date=actual,
    )


def _payment(borrowing=None, status=None, ptype=None):
    b = borrowing or _borrowing()
    return Payment(
        borrowing=b,
        money_to_pay=Decimal("10.50"),
        session_id="sess_abc",
        session_url="https://pay.example.com/sess_abc",
        status=status or Payment.Status.PENDING,
        type=ptype or Payment.Type.PAYMENT,
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
    b = _book(inventory=0)
    assert b.inventory == 0
    assert _rejected(Book, title="X", author="Y", cover=Book.Cover.HARD,
                     daily_fee=Decimal("1"), inventory=-1)


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_book_has_daily_fee():
    b = _book()
    assert b.daily_fee == Decimal("1.50")


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_book_cover_hard_and_soft():
    assert Book.Cover.HARD is not None
    assert Book.Cover.SOFT is not None
    assert Book.Cover.HARD != Book.Cover.SOFT
    b = Book(title="A", author="B", cover=Book.Cover.SOFT, daily_fee=Decimal("1"), inventory=1)
    assert b.cover == Book.Cover.SOFT


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_borrowing_links_book_and_user():
    book = _book()
    user = _user()
    br = _borrowing(book=book, user=user)
    assert br.book is book
    assert br.user is user


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_borrowing_dates_and_null_actual_return():
    br = _borrowing()
    assert br.borrow_date == TODAY
    assert br.expected_return_date == NEXT_WEEK
    assert br.actual_return_date is None


# ── T07 ───────────────────────────────────────────────────────────────────────

def test_T07_borrowing_rejects_zero_inventory():
    empty_book = Book(title="X", author="Y", cover=Book.Cover.HARD,
                      daily_fee=Decimal("1"), inventory=0)
    assert _rejected(Borrowing, book=empty_book, user=_user(),
                     borrow_date=TODAY, expected_return_date=NEXT_WEEK)


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_borrowing_total_price():
    br = _borrowing()
    expected = Decimal("1.50") * (NEXT_WEEK - TODAY).days  # 7 days
    assert br.total_price == expected


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_payment_status_values():
    assert Payment.Status.PENDING is not None
    assert Payment.Status.PAID is not None
    assert Payment.Status.EXPIRED is not None
    assert Payment.Status.PENDING != Payment.Status.PAID


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_payment_type_values():
    assert Payment.Type.PAYMENT is not None
    assert Payment.Type.FINE is not None
    assert Payment.Type.PAYMENT != Payment.Type.FINE


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_payment_stores_amount_and_links_borrowing():
    br = _borrowing()
    p = _payment(borrowing=br)
    assert p.borrowing is br
    assert p.money_to_pay == Decimal("10.50")
    assert p.status == Payment.Status.PENDING


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    u = _user()
    assert u.email == "alice@example.com"
    assert User.USERNAME_FIELD == "email"
    assert u.username is None
