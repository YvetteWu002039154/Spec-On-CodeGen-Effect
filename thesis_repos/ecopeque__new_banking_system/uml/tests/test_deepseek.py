"""
Correctness tests for: thesis_results/ecopeque__new_banking_system/uml/deepseek/generated_code.py
Ground truth:          tmp/new_banking_system-main/main.py
See:                   step3_evaluation/behaviors.md for full behavior spec.

Interface notes:
  C001_AccountCLS(agency, number, client, balance=0, limit=1000, daily_trans_limit=10)
    ← default limit=1000 (overdraft allowance); tests use limit=0 for base account
      so that T04 (withdraw > balance) is tested without overdraft influence.
  C002_CurrentAccountCLS(agency, number, client, balance=0, limit=1000, daily_trans_limit=10, limit_withdrawals=3)
    ← C002_withdrawMTD is a SEPARATE method; C001_withdrawMTD is NOT overridden.
  D001_ClientCLS(name, cpf, address, birth)  ← address before birth
  Methods RAISE exceptions (ValueError, Exception) on rejection instead of returning False.
  History entries are plain strings.

Known deviation:
  T05 — uses overdraft logic: rejects if (balance + limit) < value.
         With limit=1000 and balance=1000: (2000) >= 600 → succeeds → EXPECTED FAIL.
"""
import sys, os
from datetime import date as _date
sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "../outputcode/deepseek"
)))
sys.modules.pop("generated_code", None)
from generated_code import (
    C001_AccountCLS, C002_CurrentAccountCLS,
    D001_ClientCLS, E001_IteratorAccountCLS,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _client():
    # D001_ClientCLS(name, cpf, address, birth)
    return D001_ClientCLS("Alice", "12345678901", "Street 1", _date(1990, 1, 1))

def _account(client=None):
    # limit=0 → strict balance-only withdrawals (no overdraft) for T03/T04
    return C001_AccountCLS("0001", "1", client or _client(), limit=0)

def _current(client=None):
    # limit=1000 default; withdrawal count limit = 3
    return C002_CurrentAccountCLS("0001", "1", client or _client())

def _rejected(fn, *args):
    try:
        r = fn(*args)
        return r is False or r is None
    except Exception:
        return True


# ── T01 ───────────────────────────────────────────────────────────────────────

def test_T01_deposit_positive_succeeds():
    acc = _account()
    acc.C001_depositMTD(100)
    assert acc.C001_balance == 100


# ── T02 ───────────────────────────────────────────────────────────────────────

def test_T02_deposit_nonpositive_rejected():
    acc = _account()
    assert _rejected(acc.C001_depositMTD, 0)
    assert _rejected(acc.C001_depositMTD, -50)
    assert acc.C001_balance == 0


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_withdraw_within_balance_succeeds():
    acc = _account()  # limit=0
    acc.C001_depositMTD(500)
    acc.C001_withdrawMTD(200)
    assert acc.C001_balance == 300


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_withdraw_exceeds_balance_rejected():
    # With limit=0: (100 + 0) < 200 → raises exception
    acc = _account()
    acc.C001_depositMTD(100)
    assert _rejected(acc.C001_withdrawMTD, 200)
    assert acc.C001_balance == 100


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_current_withdraw_exceeds_per_tx_limit_rejected():
    """EXPECTED FAIL: overdraft logic; (1000 + 1000) >= 600 → withdrawal succeeds."""
    acc = _current()
    acc.C001_depositMTD(1000)
    assert _rejected(acc.C002_withdrawMTD, 600)
    assert acc.C001_balance == 1000


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_current_daily_withdrawal_count_limit():
    # Must call C002_withdrawMTD (dedicated current-account method)
    acc = _current()
    acc.C001_depositMTD(2000)
    acc.C002_withdrawMTD(100)
    acc.C002_withdrawMTD(100)
    acc.C002_withdrawMTD(100)
    assert _rejected(acc.C002_withdrawMTD, 100)


# ── T07 ───────────────────────────────────────────────────────────────────────

def test_T07_daily_total_transaction_limit():
    acc = _account()
    for _ in range(10):
        acc.C001_depositMTD(10)
    assert _rejected(acc.C001_depositMTD, 10)


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_history_records_deposit():
    acc = _account()
    acc.C001_depositMTD(150)
    entries = list(acc.C001_history.B001_transaction_generatorMTD(None))
    assert len(entries) == 1
    entry = str(entries[0])
    assert "150" in entry or "deposit" in entry.lower()


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_history_records_withdrawal():
    acc = _account()
    acc.C001_depositMTD(500)
    acc.C001_withdrawMTD(200)
    entries = list(acc.C001_history.B001_transaction_generatorMTD(None))
    assert len(entries) == 2


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_history_filter_by_type():
    acc = _account()
    acc.C001_depositMTD(100)
    acc.C001_depositMTD(200)
    acc.C001_withdrawMTD(50)
    deps = list(acc.C001_history.B001_transaction_generatorMTD("deposit"))
    wds  = list(acc.C001_history.B001_transaction_generatorMTD("withdraw"))
    assert len(deps) == 2
    assert len(wds)  == 1


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_client_holds_account_reference():
    c = _client()
    acc = _account(c)
    c.D001_add_accountMTD(acc)
    assert acc in c.D001_accounts


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_iterator_yields_all_accounts():
    c = _client()
    a1 = C001_AccountCLS("0001", "1", c, limit=0)
    a2 = C001_AccountCLS("0001", "2", c, limit=0)
    result = list(E001_IteratorAccountCLS([a1, a2]))
    assert len(result) == 2
    assert a1 in result and a2 in result
