import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

_PATHS = dict(gencode_paths())
_CACHE = {}


class _Unloadable:
    """Stand-in for a generation that raised on import.

    Building all four drivers eagerly meant one unloadable generation took down
    collection for the whole module — scoring every OTHER model 0-of-0 too, and,
    having no [impl_id] in its name, the crash was dropped by the scorer rather
    than counted. Loading lazily and capturing the exception makes an unloadable
    generation fail its own tests (the correct score for it) and leaves the rest
    intact. See Reports/variance_pilot/: across runs, one bad generation would
    otherwise blank an entire run.
    """

    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise self._exc


def _driver_for(ident):
    if ident not in _CACHE:
        try:
            module = load_gencodemodule(ident, _PATHS[ident])
        except Exception as exc:                          # noqa: BLE001
            module = _Unloadable(exc)
        _CACHE[ident] = build_driver(ident.split("/")[-1], module)
    return _CACHE[ident]


@pytest.fixture(params=sorted(_PATHS))
def driver(request):
    return _driver_for(request.param)


# ---------------------------------------------------------------------------
# Construction / balance
# ---------------------------------------------------------------------------
def test_new_account_balance_is_zero(driver):
    assert driver.new_balance() == 0


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------
def test_deposit_positive_increases_balance(driver):
    assert driver.deposit_increase() == 200


def test_deposit_zero_is_rejected(driver):
    assert driver.deposit_zero_rejected() == 100


def test_deposit_negative_is_rejected(driver):
    assert driver.deposit_negative_rejected() == 100


def test_successive_deposits_accumulate(driver):
    assert driver.deposits_accumulate() == 600


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------
def test_withdraw_less_than_balance_decreases_balance(driver):
    assert driver.withdraw_less() == 200


def test_withdraw_more_than_balance_is_rejected(driver):
    assert driver.withdraw_over_rejected() == 100


def test_withdraw_zero_or_negative_is_rejected(driver):
    assert driver.withdraw_nonpositive_rejected() == 100


def test_withdraw_full_balance_leaves_zero(driver):
    assert driver.withdraw_full() == 0


# ---------------------------------------------------------------------------
# Transaction history
# ---------------------------------------------------------------------------
def test_successful_deposit_is_recorded_in_history(driver):
    assert driver.deposit_recorded() > 0


# ---------------------------------------------------------------------------
# Dependency usage — the description names abc; does the generation
# import and use it, or hand-roll a substitute? Static (AST) check — see
# loader.dependency_used and CONTRACT.md § "Dependency usage".
# ---------------------------------------------------------------------------
@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


# One test per named dependency rather than a @parametrize: parametrize ids
# append "-<dep>" inside the brackets, which breaks the canonical
# test_xxx[nl/<model>] id shape the step3 scorer parses.
def _assert_dependency_used(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )


def test_uses_named_dependency_abc(ident):
    _assert_dependency_used(ident, "abc")
