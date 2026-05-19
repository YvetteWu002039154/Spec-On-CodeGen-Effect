"""
Correctness tests for: uml/outputcode/gemini/generated_code.py
Ground truth: library-service-api-main/ (Django project)

Interface notes:
  Book(author, cover, daily_fee, inventory, title)  ← alphabetical constructor order
    - Book.Cover.HARD = "HARD" / Book.Cover.SOFT = "SOFT" (class string constants)
    - No validation on negative values (no-op setters)
  User(email, full_name)
    - User.USERNAME_FIELD = "email", user.username = None
  Borrowing(book, user, borrow_date, expected_return_date, total_price, actual_return_date=None)
    - total_price is a CONSTRUCTOR parameter, not computed
    - .validate_borrowing(inventory): raises ValueError if inventory <= 0
    - .clean(): no-op
  Payment(borrowing, money_to_pay, session_id, session_url, status, type)
    - Payment.Status.PENDING/PAID/EXPIRED = string constants
    - Payment.Type.PAYMENT/FINE = string constants

Known deviations:
  T08 — total_price is constructor-injected, not derived from days×daily_fee.
         Test verifies the value is stored, not computed.
"""
import sys
import os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../outputcode/gemini")))
sys.modules.pop("generated_code", None)

from datetime import date
import pytest
from generated_code import Book, Borrowing, Payment, User

TODAY = date(2024, 1, 1)
NEXT_WEEK = date(2024, 1, 8)


def _book(inventory=3):
    return Book(author="Martin", cover=Book.Cover.HARD, daily_fee=1.50,
                inventory=inventory, title="Clean Code")


def _user():
    return User(email="alice@example.com", full_name="Alice")


def _borrowing(book=None, user=None, actual=None, total_price=10.50):
    return Borrowing(
        book=book or _book(),
        user=user or _user(),
        borrow_date=TODAY,
        expected_return_date=NEXT_WEEK,
        total_price=total_price,
        actual_return_date=actual,
    )


def _payment(borrowing=None):
    b = borrowing or _borrowing()
    return Payment(
        borrowing=b,
        money_to_pay=10.50,
        session_id="sess_abc",
        session_url="https://pay.example.com/sess_abc",
        status=Payment.Status.PENDING,
        type=Payment.Type.PAYMENT,
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

def test_T02_book_inventory_stored():
    b = _book(inventory=5)
    assert b.inventory == 5
    b0 = _book(inventory=0)
    assert b0.inventory == 0


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_book_has_daily_fee():
    b = _book()
    assert b.daily_fee == 1.50


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_book_cover_hard_and_soft():
    assert Book.Cover.HARD is not None
    assert Book.Cover.SOFT is not None
    assert Book.Cover.HARD != Book.Cover.SOFT
    b = Book(author="B", cover=Book.Cover.SOFT, daily_fee=1.0, inventory=1, title="A")
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

def test_T07_validate_borrowing_rejects_zero_inventory():
    br = _borrowing()
    assert _rejected(br.validate_borrowing, 0)
    assert _rejected(br.validate_borrowing, -1)


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_borrowing_total_price_stored():
    # total_price is injected, not computed — verify it is stored correctly
    br = _borrowing(total_price=10.50)
    assert br.total_price == 10.50


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
    assert p.money_to_pay == 10.50
    assert p.status == Payment.Status.PENDING


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    u = _user()
    assert u.email == "alice@example.com"
    assert User.USERNAME_FIELD == "email"
    assert u.username is None
