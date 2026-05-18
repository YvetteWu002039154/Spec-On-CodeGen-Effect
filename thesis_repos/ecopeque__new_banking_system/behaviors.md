# Behavior Test Specification
## Banking System — Correctness Evaluation

**Ground truth:** `tmp/new_banking_system-main/main.py`  
**Evaluated codes:** `./{condition}/outputcode/{model}/generated_code.py`  
**Conditions:** `uml` (4 models), `nl` (4 models)  
**Models:** `gpt`, `claude`, `gemini`, `deepseek`

---

## Test Suite Overview

12 behavioral tests derived from the ground truth. Each test targets one observable behavior. Tests are **interface-adapted** per model (different constructor signatures, naming conventions) but test the **same semantic behavior** in all cases.

Failure signaling is accepted in two forms: returning `False`/`None` (original style) or raising any `Exception` (adopted by several generated codes). Both are treated as correct rejection.

---

## T01 — Deposit positive value succeeds

**Source:** `A002_DepositCLS.A001_registerMTD` / `C001_AccountCLS.C001_depositMTD`

**Behavior:** Depositing a positive amount returns success and increases the account balance by the deposited amount.

**Setup:** Create a base account with zero balance.  
**Action:** Deposit 100.  
**Assert:** Operation succeeds; balance == 100.

**Expected:** PASS for all 8 codes.

---

## T02 — Deposit zero or negative value is rejected

**Source:** `A002_DepositCLS.A001_registerMTD` lines: `if self.A001_value <= 0: return False`

**Behavior:** Depositing zero or a negative amount is rejected. Balance remains unchanged.

**Setup:** Create a base account with zero balance.  
**Action:** Deposit 0, then deposit -50.  
**Assert:** Both operations fail (return False or raise); balance remains 0.

**Expected:** PASS for all 8 codes.

---

## T03 — Withdrawal within available balance succeeds

**Source:** `A003_WithdrawCLS.A001_registerMTD` lines: balance check → `account.C001_balance -= self.A001_value`

**Behavior:** Withdrawing an amount that does not exceed the balance returns success and reduces the balance correctly.

**Setup:** Create a base account; deposit 500.  
**Action:** Withdraw 200.  
**Assert:** Operation succeeds; balance == 300.

**Expected:** PASS for all 8 codes.  
*Note: nl/deepseek uses overdraft semantics (allows negative balance up to limit), so T03 still passes because 200 ≤ 500.*

---

## T04 — Withdrawal exceeding balance is rejected

**Source:** `A003_WithdrawCLS.A001_registerMTD` lines: `elif self.A001_value > account.C001_balance: return False`

**Behavior:** Withdrawing more than the current balance is rejected. Balance remains unchanged.

**Setup:** Create a base account (no overdraft); deposit 100.  
**Action:** Withdraw 200.  
**Assert:** Operation fails; balance remains 100.

**Expected:** PASS for uml/\*, nl/gpt, nl/claude, nl/gemini.  
**FAIL for nl/deepseek** — uses overdraft semantics; 200 − 100 = −100 > −500 limit, so withdrawal succeeds.

---

## T05 — CurrentAccount rejects withdrawal exceeding per-transaction limit (500)

**Source:** `C002_CurrentAccountCLS.C002_withdrawMTD` line: `if value > self.C001_limit: return False` (limit=500)

**Behavior:** A current account rejects any single withdrawal above 500, even if sufficient balance exists.

**Setup:** Create a current account; deposit 1000 (sufficient balance).  
**Action:** Withdraw 600.  
**Assert:** Operation fails; balance remains 1000.

**Expected:** PASS for uml/gpt, nl/gpt, nl/claude, nl/gemini.  
**FAIL for uml/claude** — uses overdraft logic: rejects only if value > (balance + limit), 600 ≤ 1500.  
**FAIL for uml/gemini** — uses overdraft logic: rejects only if (balance + limit) < value.  
**FAIL for uml/deepseek** — uses overdraft logic with default limit=1000.  
**FAIL for nl/deepseek** — uses daily-amount limit (1000 total/day), not per-transaction count.

---

## T06 — CurrentAccount enforces daily withdrawal count limit (3)

**Source:** `C002_CurrentAccountCLS.C002_withdrawMTD` lines: `if self.C002_number_withdrawals >= self.C002_limit_withdrawals: return False` (limit=3)

**Behavior:** A current account allows at most 3 withdrawals per day. The 4th withdrawal attempt on the same day is rejected.

**Setup:** Create a current account; deposit 2000.  
**Action:** Withdraw 100 three times (all succeed); attempt a 4th withdrawal of 100.  
**Assert:** 4th withdrawal fails.

**Expected:** PASS for uml/\*, nl/gpt, nl/claude, nl/gemini.  
**FAIL for nl/deepseek** — enforces a daily withdrawal *amount* ceiling (1000), not a *count* limit; 4 × 100 = 400 ≤ 1000 so all 4 succeed.

---

## T07 — Global daily transaction limit (10) applies to all accounts

**Source:** `C001_AccountCLS.C001_depositMTD` / `C001_withdrawMTD` lines: `if self.C001_daily_trans_count >= self.C001_daily_trans_limit: return False` (limit=10)

**Behavior:** Any account (not just current) allows at most 10 transactions (deposits + withdrawals combined) per calendar day. The 11th transaction is rejected.

**Setup:** Create a base account.  
**Action:** Deposit 10 ten times (exhausts daily limit); attempt an 11th deposit.  
**Assert:** 11th deposit fails.

**Expected:** PASS for all 4 uml codes.  
**FAIL for all 4 nl codes** — NL specification does not mention a daily total transaction cap; none of the NL-generated codes implement it.

---

## T08 — Deposit is recorded in transaction history

**Source:** `B001_HistoryCLS.B001_add_transactionMTD` called from `A002_DepositCLS.A001_registerMTD`

**Behavior:** After a successful deposit, the transaction history contains exactly one entry referencing the deposited amount.

**Setup:** Create a base account.  
**Action:** Deposit 150.  
**Assert:** History has 1 entry; entry contains "150" or "deposit" (case-insensitive).

**Expected:** PASS for uml/gpt, uml/claude, uml/deepseek, all nl codes.  
**FAIL for uml/gemini** — `C001_depositMTD` does not call `B001_add_transactionMTD`; history recording is only done via `A002_DepositCLS.A001_registerMTD`, which is not invoked by `depositMTD`.

---

## T09 — Withdrawal is recorded in transaction history

**Source:** `B001_HistoryCLS.B001_add_transactionMTD` called from `A003_WithdrawCLS.A001_registerMTD`

**Behavior:** After a deposit followed by a withdrawal, the history contains exactly 2 entries.

**Setup:** Create a base account; deposit 500; withdraw 200.  
**Assert:** History has 2 entries.

**Expected:** Same as T08 (FAIL only for uml/gemini).

---

## T10 — History generator filters entries by transaction type

**Source:** `B001_HistoryCLS.B001_transaction_generatorMTD(filter_type)` — yields only entries matching the filter keyword

**Behavior:** When filtered by "deposit", only deposit entries are returned. When filtered by "withdraw", only withdrawal entries are returned.

**Setup:** Create a base account; deposit 100; deposit 200; withdraw 50.  
**Action:** Filter history by "deposit"; filter history by "withdraw".  
**Assert:** 2 deposit entries returned; 1 withdrawal entry returned.

**Expected:** Same as T08 (FAIL only for uml/gemini — history is empty when using direct method calls).

---

## T11 — Client stores account reference

**Source:** `D001_ClientCLS.D001_add_accountMTD` appends to `D001_accounts`

**Behavior:** After linking an account to a client, the account appears in the client's account list.

**Setup:** Create a client and an account.  
**Action:** Add account to client.  
**Assert:** Account is present in client's accounts list.

**Expected:** PASS for all 8 codes.

---

## T12 — Account iterator yields all accounts

**Source:** `E001_IteratorAccountCLS.__iter__` / `__next__`

**Behavior:** The account iterator visits each account exactly once in order.

**Setup:** Create two accounts; wrap in iterator (or equivalent list for NL codes).  
**Assert:** Iterating produces exactly 2 items containing both accounts.

**Expected:** PASS for all 8 codes.  
*Note: NL codes have no dedicated iterator class; the test uses `client.accounts` list, which is equivalent.*

---

## Expected Pass Rates (Predicted)

| Test | uml/gpt | uml/claude | uml/gemini | uml/deepseek | nl/gpt | nl/claude | nl/gemini | nl/deepseek |
|------|:-------:|:----------:|:----------:|:------------:|:------:|:---------:|:---------:|:-----------:|
| T01  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T02  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T03  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T04  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| T05  | PASS | **FAIL** | **FAIL** | **FAIL** | PASS | PASS | PASS | **FAIL** |
| T06  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| T07  | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| T08  | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS |
| T09  | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS |
| T10  | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS |
| T11  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T12  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **Score** | **12/12** | **10/12** | **7/12** | **11/12** | **11/12** | **11/12** | **11/12** | **7/12** |

### Key Findings (Predicted)

- **UML avg:** (12 + 10 + 7 + 11) / 48 = **83.3%**
- **NL avg:** (11 + 11 + 11 + 7) / 48 = **83.3%**
- T07 (daily total limit) is exclusively in the UML spec — all NL codes miss it.
- T05 (per-transaction cap) is implemented correctly only in uml/gpt and the three NL codes that use count-based logic.
- uml/gemini fails history tests because its deposit method does not record to history directly.
- nl/deepseek diverges most severely: uses overdraft + amount-based daily limits instead of balance-only + count-based daily limits.

---

## pass@k Definition

For each model/condition pair (one generated sample), **pass@1** is computed in two ways:

1. **Test pass rate** (continuous): `c / n` where `c` = tests passed, `n` = 12 total tests.
2. **Strict pass@1** (binary): `1` if all 12 tests pass, else `0`.

For multiple samples (if re-run at different temperatures), the unbiased estimator is:

```
pass@k = 1 - C(n - c, k) / C(n, k)
```

where `n` = total samples, `c` = samples passing all tests, `k` = the k value.
