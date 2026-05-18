"""
Correctness tests for: thesis_results/ecopeque__new_banking_system/nl/gpt/generated_code.py
Ground truth:          tmp/new_banking_system-main/main.py
See:                   step3_evaluation/behaviors.md for full behavior spec.

Interface notes:
  Individual(name, birth_date, cpf, address)  ← requires valid CPF checksum
  Account(agency, number, client)             ← concrete base account
  CurrentAccount(agency, number, client, withdrawal_limit=500, daily_withdrawal_limit=3)
  Deposit(amount).register(account)           ← records to history
  Withdrawal(amount).register(account)        ← records to history
  account.deposit(amount) / account.withdraw(amount) ← do NOT record to history
  Failures raise ValidationError or BusinessRuleError (not return False)
  history stored as objects with .type_name attribute

Known deviation:
  T07 — no global daily transaction limit (10) in NL spec → EXPECTED FAIL.
"""
import sys, os
import pytest
sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "../outputcode/gpt"
)))
sys.modules.pop("generated_code", None)
from generated_code import (
    Individual, Account, CurrentAccount,
    Deposit, Withdrawal, ValidationError, BusinessRuleError,
)

VALID_CPF = "52998224725"


# ── fixtures ──────────────────────────────────────────────────────────────────

def _client():
    return Individual("Alice", "01/01/1990", VALID_CPF, "Street 1")

def _account(client=None):
    return Account("0001", 1, client or _client())

def _current(client=None):
    return CurrentAccount("0001", 1, client or _client())

def _rejected(fn, *args):
    try:
        r = fn(*args)
        return r is False or r is None
    except Exception:
        return True


# ── T01 ───────────────────────────────────────────────────────────────────────

def test_T01_deposit_positive_succeeds():
    acc = _account()
    result = acc.deposit(100)
    assert result is True
    assert acc.balance == 100


# ── T02 ───────────────────────────────────────────────────────────────────────

def test_T02_deposit_nonpositive_rejected():
    acc = _account()
    assert _rejected(acc.deposit, 0)
    assert _rejected(acc.deposit, -50)
    assert acc.balance == 0


# ── T03 ───────────────────────────────────────────────────────────────────────

def test_T03_withdraw_within_balance_succeeds():
    acc = _account()
    acc.deposit(500)
    result = acc.withdraw(200)
    assert result is True
    assert acc.balance == 300


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_withdraw_exceeds_balance_rejected():
    acc = _account()
    acc.deposit(100)
    assert _rejected(acc.withdraw, 200)
    assert acc.balance == 100


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_current_withdraw_exceeds_per_tx_limit_rejected():
    acc = _current()  # withdrawal_limit=500
    acc.deposit(1000)
    assert _rejected(acc.withdraw, 600)
    assert acc.balance == 1000


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_current_daily_withdrawal_count_limit():
    # nl/gpt counts withdrawals from history; must use Withdrawal.register to populate it
    acc = _current()  # daily_withdrawal_limit=3
    acc.deposit(2000)
    Withdrawal(100).register(acc)
    Withdrawal(100).register(acc)
    Withdrawal(100).register(acc)
    assert _rejected(acc.withdraw, 100)


# ── T07 ───────────────────────────────────────────────────────────────────────

def test_T07_daily_total_transaction_limit():
    """EXPECTED FAIL: NL spec has no 10-transaction-per-day global cap."""
    acc = _account()
    for _ in range(10):
        acc.deposit(10)
    assert _rejected(acc.deposit, 10)


# ── T08 ───────────────────────────────────────────────────────────────────────

def test_T08_history_records_deposit():
    # Use Deposit.register to populate history (account.deposit alone does not)
    acc = _account()
    Deposit(150).register(acc)
    txs = acc.history.transactions
    assert len(txs) == 1
    assert txs[0].type_name == "deposit"


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_history_records_withdrawal():
    acc = _account()
    Deposit(500).register(acc)
    Withdrawal(200).register(acc)
    assert len(acc.history.transactions) == 2


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_history_filter_by_type():
    acc = _account()
    Deposit(100).register(acc)
    Deposit(200).register(acc)
    Withdrawal(50).register(acc)
    deps = [t for t in acc.history.transactions if t.type_name == "deposit"]
    wds  = [t for t in acc.history.transactions if t.type_name == "withdrawal"]
    assert len(deps) == 2
    assert len(wds)  == 1


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_client_holds_account_reference():
    c = _client()
    acc = CurrentAccount("0001", 1, c)
    c.add_account(acc)
    assert acc in c.accounts


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_accounts_iterable():
    c = _client()
    a1 = Account("0001", 1, c)
    a2 = Account("0001", 2, c)
    c.add_account(a1)
    c.add_account(a2)
    result = list(c.accounts)
    assert len(result) == 2
    assert a1 in result and a2 in result
