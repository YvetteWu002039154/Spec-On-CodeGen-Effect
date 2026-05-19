"""
Correctness tests for: nl/outputcode/deepseek/generated_code.py
Ground truth: library-service-api-main/ (Django project)

Interface notes:
  COLLECTION_ERROR EXPECTED — the generated file contains raw shell commands
  and docker-compose YAML embedded as bare text (not inside strings), causing
  a SyntaxError at line 539.

  Intended interface (from the multi-file Django structure in the source):
    library/models.py:
      Book(models.Model) — title, author, isbn, description, date_added
        NOTE: no inventory / daily_fee fields (fundamental deviation from spec)
      Borrowing(models.Model) — user FK, book FK, borrow_date,
                                expected_return_date, actual_return_date (null),
                                is_overdue (property)
      Payment(models.Model)
        Payment.PaymentType.FEE / FINE    (ground truth expects PAYMENT/FINE)
        Payment.PaymentStatus.PENDING / PAID   (no EXPIRED)
        borrowing FK, amount, payment_date, payment_type, status

Known deviations (ALL EXPECTED FAIL — COLLECTION_ERROR on SyntaxError):
  T02, T03 — Book has no inventory or daily_fee fields.
  T04       — Book has no cover attribute.
  T08       — No total_price concept.
  T09       — PaymentStatus has no EXPIRED; type uses FEE not PAYMENT.
  T12       — Uses standard Django User (username-based).
"""
import sys
import os

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../outputcode/deepseek")))
sys.modules.pop("generated_code", None)

# Configure Django before trying any import (module may try to import Django)
import django
from django.conf import settings
if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=False,
        AUTH_PASSWORD_VALIDATORS=[],
    )
    django.setup()

# Module-level import — COLLECTION_ERROR (SyntaxError) expected
import generated_code as _m


def _rejected(fn, *args, **kwargs):
    try:
        r = fn(*args, **kwargs)
        return r is False or r is None
    except Exception:
        return True


# ── T01 ───────────────────────────────────────────────────────────────────────

def test_T01_book_has_title_and_author_fields():
    Book = _m.Book
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "title" in field_names
    assert "author" in field_names


# ── T02 ───────────────────────────────────────────────────────────────────────

def test_T02_book_has_inventory_field():
    """EXPECTED FAIL: NL/DeepSeek Book has no inventory field."""
    Book = _m.Book
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "inventory" in field_names, "Book has no inventory field"


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_book_has_daily_fee_field():
    """EXPECTED FAIL: NL/DeepSeek Book has no daily_fee field."""
    Book = _m.Book
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "daily_fee" in field_names, "Book has no daily_fee field"


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_book_cover_hard_and_soft():
    """EXPECTED FAIL: NL/DeepSeek Book has no cover field."""
    Book = _m.Book
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "cover" in field_names, "Book has no cover field"


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_borrowing_has_book_and_user_fields():
    Borrowing = _m.Borrowing
    field_names = {f.name for f in Borrowing._meta.get_fields()}
    assert "book" in field_names
    assert "user" in field_names


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_borrowing_date_fields_exist():
    Borrowing = _m.Borrowing
    field_names = {f.name for f in Borrowing._meta.get_fields()}
    assert "borrow_date" in field_names
    assert "expected_return_date" in field_names
    assert "actual_return_date" in field_names


# ── T07 ───────────────────────────────────────────────────────────────────────

def test_T07_borrowing_rejects_zero_inventory():
    """EXPECTED FAIL: NL/DeepSeek Borrowing has no validate_borrowing method."""
    Borrowing = _m.Borrowing
    assert hasattr(Borrowing, "validate_borrowing"), "No validate_borrowing method"


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_borrowing_total_price():
    """EXPECTED FAIL: NL/DeepSeek has no total_price concept."""
    Borrowing = _m.Borrowing
    assert hasattr(Borrowing, "total_price"), "No total_price on Borrowing"


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_payment_status_values():
    """EXPECTED FAIL: uses PaymentStatus, no EXPIRED."""
    Payment = _m.Payment
    cls = getattr(Payment, "PaymentStatus", getattr(Payment, "Status", None))
    assert cls is not None, "No Status/PaymentStatus class on Payment"
    assert hasattr(cls, "PENDING")
    assert hasattr(cls, "PAID")
    assert hasattr(cls, "EXPIRED"), "No EXPIRED status"


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_payment_type_values():
    Payment = _m.Payment
    cls = getattr(Payment, "PaymentType", getattr(Payment, "Type", None))
    assert cls is not None, "No Type/PaymentType class on Payment"
    assert hasattr(cls, "FINE")
    # Ground truth uses PAYMENT; NL/DeepSeek may use FEE
    assert hasattr(cls, "PAYMENT") or hasattr(cls, "FEE")


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_payment_has_amount_and_borrowing():
    Payment = _m.Payment
    field_names = {f.name for f in Payment._meta.get_fields()}
    assert "amount" in field_names or "money_to_pay" in field_names
    assert "borrowing" in field_names


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    """EXPECTED FAIL: uses standard Django User (username-based)."""
    from django.contrib.auth.models import User as DjangoUser
    assert DjangoUser.USERNAME_FIELD == "email", \
        "NL/DeepSeek uses standard Django User (USERNAME_FIELD='username'); expected email-based custom User"
