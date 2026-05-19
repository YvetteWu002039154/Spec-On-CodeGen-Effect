"""
Correctness tests for: nl/outputcode/gemini/generated_code.py
Ground truth: library-service-api-main/ (Django project)

Interface notes:
  COLLECTION_ERROR EXPECTED — the module imports rest_framework_simplejwt,
  drf_spectacular, and django_filters which are not installed in the thesis
  evaluation environment, causing ImportError at collection time.

  (If all deps were available, the module self-configures Django with an
  in-memory SQLite DB using app_label='__main__' on each model.)

  Intended interface:
    Book(models.Model)  — title, author, inventory (PositiveIntegerField),
                          daily_fee (DecimalField). No cover field.
    Borrowing(models.Model) — borrow_date (auto), expected_return_date,
                          actual_return_date (null), book FK, user FK (contrib.auth)
                          Inventory validated in BorrowingSerializer.validate()
    Payment(models.Model)
      Payment.StatusChoices.PENDING / PAID   (no EXPIRED)
      Payment.TypeChoices.PAYMENT / FINE
      borrowing FK, session_url, session_id, money_to_pay

Known deviations (ALL EXPECTED FAIL — COLLECTION_ERROR on import):
  T04 — no cover field on Book.
  T09 — StatusChoices has no EXPIRED.
  T12 — uses standard Django contrib.auth User (username-based), not email-based.
"""
import sys
import os

# Configure Django BEFORE any import that touches Django internals
import django
from django.conf import settings
from django.apps import apps as _dapps

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=False,
        AUTH_PASSWORD_VALIDATORS=[],
    )
    django.setup()

# Register '__main__' as a fake Django app (Gemini sets app_label='__main__')
if "__main__" not in _dapps.app_configs:
    from django.apps.config import AppConfig as _AC
    _cfg = object.__new__(_AC)
    _cfg.name = "__main__"
    _cfg.label = "__main__"
    _cfg.models = {}
    _cfg.models_module = None
    _cfg.apps = _dapps
    _cfg.path = "/tmp"
    _cfg.verbose_name = "__main__"
    _dapps.app_configs["__main__"] = _cfg
    _dapps.all_models["__main__"] = {}
    _cfg.models = _dapps.all_models["__main__"]

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../outputcode/gemini")))
sys.modules.pop("generated_code", None)

# Module-level import — COLLECTION_ERROR if this raises
import generated_code as _m
Book = _m.Book
Borrowing = _m.Borrowing
Payment = _m.Payment


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
    """EXPECTED FAIL: NL/Gemini Book has no cover field."""
    field_names = {f.name for f in Book._meta.get_fields()}
    assert "cover" in field_names, "Book has no cover field"


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

def test_T07_borrowing_serializer_validates_inventory():
    # Inventory validation lives in BorrowingSerializer.validate()
    assert hasattr(_m, "BorrowingSerializer"), "No BorrowingSerializer"
    assert hasattr(_m.BorrowingSerializer, "validate")


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_payment_money_to_pay_field_exists():
    field_names = {f.name for f in Payment._meta.get_fields()}
    assert "money_to_pay" in field_names


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_payment_status_values():
    assert Payment.StatusChoices.PENDING is not None
    assert Payment.StatusChoices.PAID is not None
    # EXPECTED FAIL: no EXPIRED in NL/Gemini Payment
    assert hasattr(Payment.StatusChoices, "EXPIRED"), "StatusChoices has no EXPIRED"


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_payment_type_values():
    assert Payment.TypeChoices.PAYMENT is not None
    assert Payment.TypeChoices.FINE is not None
    assert Payment.TypeChoices.PAYMENT != Payment.TypeChoices.FINE


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_payment_has_borrowing_and_money_and_defaults_pending():
    field_names = {f.name for f in Payment._meta.get_fields()}
    assert "money_to_pay" in field_names
    assert "borrowing" in field_names
    status_field = Payment._meta.get_field("status")
    assert status_field.default == Payment.StatusChoices.PENDING


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    """EXPECTED FAIL: NL/Gemini uses Django's built-in contrib.auth User."""
    from django.contrib.auth.models import User as DjangoUser
    # Standard Django User uses 'username' not 'email'
    assert DjangoUser.USERNAME_FIELD == "email", \
        "NL/Gemini uses standard Django User (USERNAME_FIELD='username'); expected email-based custom User"
