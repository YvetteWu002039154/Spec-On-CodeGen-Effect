import os
import sys
from datetime import date
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PATHS = dict(gencode_paths())
_CACHE = {}
_TOL = Decimal("0.01")


class _Unloadable:
    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise self._exc


@pytest.fixture(params=sorted(_PATHS))
def driver(request):
    ident = request.param
    if ident not in _CACHE:
        try:
            module = load_gencodemodule(ident, _PATHS[ident])
        except Exception as exc:
            module = _Unloadable(exc)
        _CACHE[ident] = build_driver(ident.split("/")[-1], module)
    return _CACHE[ident]


def _close(a, b):
    return abs(Decimal(a) - Decimal(b)) <= _TOL


# ---------------------------------------------------------------------------
# Borrowing price  ("Make borrowing" / "Make payment after borrowing")
# ---------------------------------------------------------------------------
def test_borrowing_price_days_times_fee(driver):
    assert _close(driver.borrowing_price(date(2030, 1, 1), date(2030, 1, 8), "2.00"), Decimal("14.00"))


def test_borrowing_price_scales_with_days(driver):
    assert _close(driver.borrowing_price(date(2030, 1, 1), date(2030, 1, 11), "1.50"), Decimal("15.00"))


# ---------------------------------------------------------------------------
# Overdue fine  ("FINE payment if borrowing is overdue")
# ---------------------------------------------------------------------------
def test_overdue_fine_is_overdue_days_times_fee_times_two(driver):
    f = driver.overdue_fine(date(2030, 1, 1), date(2030, 1, 8), date(2030, 1, 13), "2.00")
    assert _close(f, Decimal("20.00"))


def test_no_fine_when_returned_on_time(driver):
    f = driver.overdue_fine(date(2030, 1, 1), date(2030, 1, 8), date(2030, 1, 8), "2.00")
    assert _close(f, Decimal("0.00"))


# ---------------------------------------------------------------------------
# Payment vocabularies  ("Make payment" + "FINE payment")
# ---------------------------------------------------------------------------
def test_payment_type_distinguishes_fine(driver):
    vocab = driver.payment_type_vocab()
    assert "fine" in vocab and len(vocab - {"fine"}) >= 1


def test_payment_status_pending_and_paid(driver):
    assert {"pending", "paid"} <= driver.payment_status_vocab()


# ---------------------------------------------------------------------------
# Stock control  ("Make borrowing" requires available inventory)
# ---------------------------------------------------------------------------
def test_borrow_rejected_when_out_of_stock(driver):
    assert driver.borrow_allowed(0) is False


def test_borrow_allowed_when_in_stock(driver):
    assert driver.borrow_allowed(3) is True
