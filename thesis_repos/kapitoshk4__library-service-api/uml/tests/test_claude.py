"""
Correctness tests for: uml/outputcode/claude/generated_code.py
Ground truth: library-service-api-main/ (Django project)

Interface notes:
  Requires Django to be fully configured with the generated_code app registered.
  This test file pre-configures Django with a minimal in-memory SQLite setup,
  then imports the module.  If Django model registration fails (e.g. app_label
  mismatch), pytest will report a COLLECTION_ERROR (0/0 pass).

  User(AbstractBaseUser, PermissionsMixin)
    - email = EmailField(unique=True), full_name = CharField
    - User.USERNAME_FIELD = "email", User.username = None, REQUIRED_FIELDS = []
  Book(models.Model)
    - title, author, cover (Book.Cover TextChoices: HARD/SOFT), inventory, daily_fee
  Borrowing(models.Model)
    - borrow_date, expected_return_date, actual_return_date (null), book FK, user FK
    - .validate_borrowing(inventory) static: raises ValidationError if inventory <= 0
    - .total_price property: days × daily_fee
  Payment(models.Model)
    - Payment.Status: PENDING, PAID, EXPIRED  (TextChoices)
    - Payment.Type:   PAYMENT, FINE           (TextChoices)
    - borrowing FK, session_url, session_id, money_to_pay, status, type

Known deviations:
  T01–T06, T08, T11 — require Django ORM to introspect model meta.
  Tests use _meta.get_fields() to check structure (no DB rows needed).
  T07 — uses validate_borrowing() static method (no DB needed).
"""
import sys
import os

# ── Django setup (must happen before any model import) ────────────────────────
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        AUTH_PASSWORD_VALIDATORS=[],
        USE_TZ=False,
    )
    django.setup()

# Register 'generated_code' as a fake Django app so models are accepted
from django.apps import apps as _dapps
if "generated_code" not in _dapps.app_configs:
    _outputcode_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../outputcode/claude")
    )
    from django.apps.config import AppConfig as _AC
    _cfg = object.__new__(_AC)
    _cfg.name = "generated_code"
    _cfg.label = "generated_code"
    _cfg.models = {}
    _cfg.models_module = None
    _cfg.apps = _dapps
    _cfg.path = _outputcode_path
    _cfg.verbose_name = "generated_code"
    _dapps.app_configs["generated_code"] = _cfg
    _dapps.all_models["generated_code"] = {}
    _cfg.models = _dapps.all_models["generated_code"]

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../outputcode/claude")))
sys.modules.pop("generated_code", None)

# Import at module level — collection fails (COLLECTION_ERROR) if this raises
from generated_code import Book, Borrowing, Payment, User, UserManager
from django.core.exceptions import ValidationError


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
    assert Book.Cover.HARD is not None
    assert Book.Cover.SOFT is not None
    assert Book.Cover.HARD != Book.Cover.SOFT


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

def test_T07_validate_borrowing_rejects_zero_inventory():
    # validate_borrowing is a static method — no DB needed
    assert _rejected(Borrowing.validate_borrowing, 0)
    assert _rejected(Borrowing.validate_borrowing, -1)


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_borrowing_has_total_price_property():
    assert isinstance(Borrowing.total_price, property)


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

def test_T11_payment_has_money_to_pay_and_borrowing_fields():
    field_names = {f.name for f in Payment._meta.get_fields()}
    assert "money_to_pay" in field_names
    assert "borrowing" in field_names
    assert "status" in field_names


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_user_email_identifier():
    assert User.USERNAME_FIELD == "email"
    assert User.username is None
    assert User.REQUIRED_FIELDS == []
