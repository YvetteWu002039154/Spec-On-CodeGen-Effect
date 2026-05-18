"""
Correctness tests for: thesis_results/ecopeque__new_banking_system/nl/deepseek/generated_code.py
Ground truth:          tmp/new_banking_system-main/main.py
See:                   step3_evaluation/behaviors.md for full behavior spec.

Interface notes:
  IndividualClient(name, cpf, address)  ← no birth_date; requires valid CPF checksum
  CurrentAccount(account_number, agency, client, overdraft_limit=500, daily_withdrawal_limit=1000)
    ← overdraft_limit: how far below zero balance can go (not per-tx cap)
    ← daily_withdrawal_limit: max AMOUNT per day (not COUNT)
    ← AbstractAccount.__init__ auto-calls client.add_account(self)
  account.deposit(value)   → void; raises ValueError for ≤ 0
  account.withdraw(value)  → void; raises InsufficientFundsError or DailyLimitExceededError
  account.transactions     → list of Transaction objects (no separate history object)

Known deviations:
  T04 — overdraft semantics: balance=100, withdraw=200 → balance=-100 ≥ -500 → succeeds → EXPECTED FAIL.
  T05 — no per-transaction count limit; uses daily-amount limit (1000) → EXPECTED FAIL.
  T06 — daily limit is amount-based (1000), not count-based (3) → 4×100=400 ≤ 1000 → EXPECTED FAIL.
  T07 — no global daily transaction limit (10) → EXPECTED FAIL.
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "../outputcode/deepseek"
)))
sys.modules.pop("generated_code", None)
from generated_code import (
    IndividualClient, CurrentAccount,
    Deposit, Withdrawal,
    InsufficientFundsError, DailyLimitExceededError,
)

VALID_CPF = "52998224725"


# ── fixtures ──────────────────────────────────────────────────────────────────

def _client():
    return IndividualClient("Alice", VALID_CPF, "Street 1")

def _account(client=None):
    # AbstractAccount.__init__ automatically calls client.add_account(self)
    return CurrentAccount(1, "0001", client or _client())

def _current(client=None):
    return CurrentAccount(1, "0001", client or _client(), overdraft_limit=500)

def _rejected(fn, *args):
    try:
        r = fn(*args)
        return r is False or r is None
    except Exception:
        return True


# ── T01 ───────────────────────────────────────────────────────────────────────

def test_T01_deposit_positive_succeeds():
    acc = _account()
    acc.deposit(100)
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
    acc.withdraw(200)
    assert acc.balance == 300


# ── T04 ───────────────────────────────────────────────────────────────────────

def test_T04_withdraw_exceeds_balance_rejected():
    """EXPECTED FAIL: overdraft allows balance − 200 = −100 ≥ −500 → withdrawal succeeds."""
    acc = _account()
    acc.deposit(100)
    assert _rejected(acc.withdraw, 200)
    assert acc.balance == 100


# ── T05 ───────────────────────────────────────────────────────────────────────

def test_T05_current_withdraw_exceeds_per_tx_limit_rejected():
    """EXPECTED FAIL: no per-transaction count limit; uses daily-amount ceiling (1000)."""
    acc = _current()
    acc.deposit(1000)
    assert _rejected(acc.withdraw, 600)
    assert acc.balance == 1000


# ── T06 ───────────────────────────────────────────────────────────────────────

def test_T06_current_daily_withdrawal_count_limit():
    """EXPECTED FAIL: limit is amount-based (1000/day); 4 × 100 = 400 ≤ 1000 → all succeed."""
    acc = _current()
    acc.deposit(2000)
    acc.withdraw(100)
    acc.withdraw(100)
    acc.withdraw(100)
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
    # deposit() records directly to self._transactions
    acc = _account()
    acc.deposit(150)
    txs = acc.transactions
    assert len(txs) == 1
    assert isinstance(txs[0], Deposit)


# ── T09 ───────────────────────────────────────────────────────────────────────

def test_T09_history_records_withdrawal():
    acc = _account()
    acc.deposit(500)
    acc.withdraw(200)
    assert len(acc.transactions) == 2


# ── T10 ───────────────────────────────────────────────────────────────────────

def test_T10_history_filter_by_type():
    acc = _account()
    acc.deposit(100)
    acc.deposit(200)
    acc.withdraw(50)
    deps = [t for t in acc.transactions if isinstance(t, Deposit)]
    wds  = [t for t in acc.transactions if isinstance(t, Withdrawal)]
    assert len(deps) == 2
    assert len(wds)  == 1


# ── T11 ───────────────────────────────────────────────────────────────────────

def test_T11_client_holds_account_reference():
    # Account constructor auto-adds itself to client
    c = _client()
    acc = CurrentAccount(1, "0001", c)
    assert acc in c.accounts


# ── T12 ───────────────────────────────────────────────────────────────────────

def test_T12_accounts_iterable():
    c = _client()
    a1 = CurrentAccount(1, "0001", c)
    a2 = CurrentAccount(2, "0001", c)
    result = list(c.accounts)
    assert len(result) == 2
    assert a1 in result and a2 in result
