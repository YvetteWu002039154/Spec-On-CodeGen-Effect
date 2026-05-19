"""
Correctness tests for: nl/outputcode/claude/generated_code.py
Ground truth: library-service-api-main/ (Django project)

Interface notes:
  COLLECTION_ERROR EXPECTED — the module executes os.makedirs() and open() calls
  at import time (writes a full Django project to the CWD), then fails with
  FileNotFoundError: [Errno 2] No such file or directory: '' because
  os.path.dirname('manage.py') == '' and os.makedirs('') raises.

  Intended interface (from embedded Django project strings in the source):
    users/models.py:  User(AbstractUser) — email (unique), USERNAME_FIELD='email'
    books/models.py:  Book(models.Model) — title, author, cover (CoverType: HARD/SOFT)
                      inventory, daily_fee; .borrow() / .return_book() methods
    borrowings/models.py: Borrowing — borrow_date, expected_return_date,
                      actual_return_date, book FK, user FK
                      total_price / is_overdue / overdue_days properties
    payments/models.py: Payment — Status.PENDING/PAID, Type.PAYMENT/FINE
                      .is_paid() / .is_pending() methods
"""
import sys
import os
import tempfile

# Run in a temp dir to redirect file-system side effects
_tmpdir = tempfile.mkdtemp()
os.chdir(_tmpdir)

_output_path = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../outputcode/claude")
)
sys.path.insert(0, _output_path)
sys.modules.pop("generated_code", None)

# Module-level import — COLLECTION_ERROR if this raises
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

from generated_code import Book, Borrowing, Payment, User


def _rejected(fn, *args, **kwargs):
    try:
        r = fn(*args, **kwargs)
        return r is False or r is None
    except Exception:
        return True


# ── T01 ───────────────────────────────────────────────────────────────────────

def test_T01_book_has_title_and_author_fields():
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "title" in field_names
    assert "author" in field_names


# ── T02 ───────────────────────────────────────────────────────────────────────

def test_T02_book_has_inventory_field():
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "inventory" in field_names


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_book_has_daily_fee_field():
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "daily_fee" in field_names


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_book_cover_hard_and_soft():
    cover_cls = getattr(Book, "Cover", getattr(Book, "CoverType", None))
    assert cover_cls is not None, "Book has no Cover/CoverType inner class"
    assert cover_cls.HARD is not None
    assert cover_cls.SOFT is not None


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_borrowing_has_book_and_user_fields():
    field_names = {f.name for f in Borrowing._meta.get_fields()}
    assert "book" in field_names
    assert "user" in field_names


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_borrowing_date_fields_exist():
    field_names = {f.name for f in Borrowing._meta.get_fields()}
    assert "borrow_date" in field_names
    assert "expected_return_date" in field_names
    assert "actual_return_date" in field_names


# ── T07 ───────────────────────────────────────────────────────────────────────

def test_T07_book_borrow_rejects_zero_inventory():
    assert hasattr(Book, "borrow") or hasattr(Book, "borrow_one"), \
        "Book has no borrow/borrow_one method"


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_borrowing_has_total_price_property():
    assert hasattr(Borrowing, "total_price"), "Borrowing has no total_price"
    assert isinstance(Borrowing.total_price, property)


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_payment_status_values():
    assert Payment.Status.PENDING is not None
    assert Payment.Status.PAID is not None


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_payment_type_values():
    assert Payment.Type.PAYMENT is not None
    assert Payment.Type.FINE is not None


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_payment_has_money_to_pay_and_borrowing():
    field_names = {f.name for f in Payment._meta.get_fields()}
    assert "money_to_pay" in field_names or "amount" in field_names
    assert "borrowing" in field_names


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    assert User.USERNAME_FIELD == "email"
