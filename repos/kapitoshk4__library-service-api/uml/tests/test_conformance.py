import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodules  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

_BOOK_ATTRS = frozenset({"title", "author", "cover", "inventory", "daily_fee"})
_BORROWING_ATTRS = frozenset({"book", "user", "borrow_date",
                              "expected_return_date", "actual_return_date",
                              "total_price"})
_PAYMENT_ATTRS = frozenset({"borrowing", "money_to_pay", "session_id",
                            "session_url", "status", "type"})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
        except Exception as exc:
            # A generation that does not load exposes no structure at all: build
            # an empty implementation so every behavior FAILS (this track never
            # skips / marks N/A -- a module that does not load is a failure).
            impl = Implementation(ident, [])
            impl._load_error = exc
            _cache[ident] = impl
    return _cache[ident]


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


def _guard(fn):
    try:
        return fn()
    except Unsupported as exc:
        pytest.fail(f"structure not present: {exc}")


# ---------------------------------------------------------------------------
# Attributes under a class
# ---------------------------------------------------------------------------
def test_book_attributes(impl):
    # U1: Book models title/author/cover/inventory/daily_fee.
    assert _BOOK_ATTRS <= _guard(lambda: impl.attributes("Book"))


def test_borrowing_attributes(impl):
    # U2: Borrowing models book/user/borrow_date/expected_return_date/
    #     actual_return_date/total_price.
    assert _BORROWING_ATTRS <= _guard(lambda: impl.attributes("Borrowing"))


def test_payment_attributes(impl):
    # U3: Payment models borrowing/money_to_pay/session_id/session_url/status/type.
    assert _PAYMENT_ATTRS <= _guard(lambda: impl.attributes("Payment"))


# ---------------------------------------------------------------------------
# Nested choice / enum classes
# ---------------------------------------------------------------------------
def test_book_cover_choices(impl):
    # U4: Book.Cover defines HARD and SOFT.
    toks = _guard(lambda: impl.nested_tokens("Book", "Cover"))
    assert {"hard", "soft"} <= toks


def test_payment_status_choices(impl):
    # U5: Payment.Status defines PENDING, PAID, EXPIRED.
    toks = _guard(lambda: impl.nested_tokens("Payment", "Status"))
    assert {"pending", "paid", "expired"} <= toks


def test_payment_type_choices(impl):
    # U6: Payment.Type defines PAYMENT and FINE.
    toks = _guard(lambda: impl.nested_tokens("Payment", "Type"))
    assert {"payment", "fine"} <= toks


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_borrowing_validate_borrowing_method(impl):
    # U7: Borrowing exposes validate_borrowing(inventory).
    assert "validate_borrowing" in _guard(lambda: impl.methods("Borrowing"))


def test_borrowing_clean_method(impl):
    # U8: Borrowing exposes clean().
    assert "clean" in _guard(lambda: impl.methods("Borrowing"))


def test_user_manager_methods(impl):
    # U9: UserManager exposes create_user and create_superuser.
    assert {"create_user", "create_superuser"} <= _guard(
        lambda: impl.methods("UserManager"))


# ---------------------------------------------------------------------------
# Association (--*)
# ---------------------------------------------------------------------------
def test_user_objects_is_user_manager(impl):
    # U10: User.objects --* UserManager (the manager association).
    assert _guard(impl.objects_manager_name) == "UserManager"
