"""Behavior-conformance suite for the banking domain — **NL track**.

Each NL generation is driven by its own explicit driver in `adapter.py`, which
names the concrete current-account class and its deposit / withdraw / balance /
history surface. One plain-assert test per contract behavior (see CONTRACT.md)
runs against every generation. Success is judged by the observable balance
change / history effect. A capability a generation does not expose is a
behavioral FAILURE — this suite does not skip / mark N/A.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

_DRIVERS = {
    ident: build_driver(ident.split("/")[-1], load_gencodemodule(ident, path))
    for ident, path in gencode_paths()
}


@pytest.fixture(params=sorted(_DRIVERS))
def driver(request):
    return _DRIVERS[request.param]


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
_PATHS = dict(gencode_paths())


@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


NAMED_DEPENDENCIES = ('abc',)


@pytest.mark.parametrize("dep", NAMED_DEPENDENCIES)
def test_uses_named_dependency(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )
