"""Structure-conformance suite for the banking domain — **UML track**.

One shared test body runs against the 4 UML generations, via the adapter.
Expected structure comes only from CONTRACT.md, derived from the
class diagram `uml/input/classes.puml` (a pyreverse extraction of the origin
`main.py`). The diagram records inheritance links (`--|>`), a composition link
(`--*`), and the methods under each class — each test pins one fact (Un),
checked by reflection on the loaded classes, never by running behavior. A class
a generation omits is a FAILURE, as is a present-but-wrong link/method; this
track does not skip / mark N/A.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, [load_gencodemodule(ident, _PATHS[ident])])
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
# Inheritance links (--|>)
# ---------------------------------------------------------------------------
def test_deposit_specializes_transaction(impl):
    # U1: A002_DepositCLS --|> A001_TransactionCLS.
    assert _guard(lambda: impl.subclass_link("A002_DepositCLS", "A001_TransactionCLS")) is True


def test_withdraw_specializes_transaction(impl):
    # U2: A003_WithdrawCLS --|> A001_TransactionCLS.
    assert _guard(lambda: impl.subclass_link("A003_WithdrawCLS", "A001_TransactionCLS")) is True


def test_current_account_specializes_account(impl):
    # U3: C002_CurrentAccountCLS --|> C001_AccountCLS.
    assert _guard(lambda: impl.subclass_link("C002_CurrentAccountCLS", "C001_AccountCLS")) is True


def test_decorated_specializes_current_account(impl):
    # U4: C003_DecoratedCAAccountCLS --|> C002_CurrentAccountCLS.
    assert _guard(lambda: impl.subclass_link("C003_DecoratedCAAccountCLS", "C002_CurrentAccountCLS")) is True


# ---------------------------------------------------------------------------
# Abstract method
# ---------------------------------------------------------------------------
def test_transaction_register_is_abstract(impl):
    # U5: A001_TransactionCLS.A001_registerMTD is an {abstract} method.
    # (Fail if the class is absent; fail if present but not abstract.)
    _guard(lambda: impl.member_names("A001_TransactionCLS"))  # fail if class absent
    assert impl.is_abstract_method("A001_TransactionCLS", "A001_registerMTD") is True


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_history_defines_its_methods(impl):
    # U6: B001_HistoryCLS defines B001_add_transactionMTD & B001_transaction_generatorMTD.
    m = _guard(lambda: impl.member_names("B001_HistoryCLS"))
    assert {"B001_add_transactionMTD", "B001_transaction_generatorMTD"} <= m


def test_account_defines_core_operations(impl):
    # U7: C001_AccountCLS defines C001_depositMTD, C001_withdrawMTD, C001_transaction_reportMTD.
    m = _guard(lambda: impl.member_names("C001_AccountCLS"))
    assert {"C001_depositMTD", "C001_withdrawMTD", "C001_transaction_reportMTD"} <= m


def test_current_account_overrides_withdraw(impl):
    # U8: C002_CurrentAccountCLS defines its own C002_withdrawMTD (polymorphic override).
    m = _guard(lambda: impl.member_names("C002_CurrentAccountCLS"))
    assert "C002_withdrawMTD" in m


def test_decorated_defines_property_accessors(impl):
    # U9: C003_DecoratedCAAccountCLS defines C003_balanceMTD & C003_limitMTD.
    m = _guard(lambda: impl.member_names("C003_DecoratedCAAccountCLS"))
    assert {"C003_balanceMTD", "C003_limitMTD"} <= m


# ---------------------------------------------------------------------------
# Composition link (--*)
# ---------------------------------------------------------------------------
def test_account_composes_history(impl):
    # U10: B001_HistoryCLS --* C001_AccountCLS : C001_history
    # (C001_AccountCLS owns a history built from B001_HistoryCLS).
    assert _guard(lambda: impl.composes("C001_AccountCLS", "B001_HistoryCLS")) is True
