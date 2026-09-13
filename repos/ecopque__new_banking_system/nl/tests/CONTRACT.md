# Behavioral contract — `new_banking_system` **NL track**

## Description feature → origin grounding

| Description feature | Origin evidence (`main.py`) |
|---|---|
| "Managing accounts … performing transactions" / zero opening balance | `C001_AccountCLS.__init__` sets `C001_balance = 0` (L130) |
| "Performing deposits" + "proper validation" | `A002_DepositCLS.A001_registerMTD` adds `value` but rejects `value <= 0` (L81–88) |
| "Performing … withdrawals" + "minimum balance checks" (no overdraft) | `A003_WithdrawCLS.A001_registerMTD` rejects `value <= 0` and `value > balance` (L93–104) |
| "Transaction history per account" / "tracking operations" | each account owns `C001_history` (`B001_HistoryCLS`); a successful deposit calls `B001_add_transactionMTD` (L87, L131) |
| Running-balance accumulation | balance is a mutated running sum across `A002`/`A003` (L86, L102) |

*Grounding decision — reference-specific numeric caps are NOT pinned here.* The
origin enforces a **3-withdrawal cap** (`C002_limit_withdrawals = 3`), a **500
per-transaction ceiling** (`if value > self.C001_limit`), and a **10/day
transaction limit** (`C001_daily_trans_limit = 10`). The prose only says
"business rules like … withdrawal limits" without any numbers, so these
reference-specific magnitudes are out of scope for the NL track (they are
grounded and pinned in the repo's structural / UML work instead). The NL track
pins only the transaction semantics the description states outright.

## Behaviors pinned

### Construction / balance
- **N1. New balance = 0.** A newly-constructed account starts at balance `0`.

### Deposit
- **N2. Deposit increases.** Depositing a positive amount increases the balance
  by exactly that amount.
- **N3. Deposit `0` rejected.** Depositing `0` leaves the balance unchanged.
- **N4. Deposit `<0` rejected.** Depositing a negative amount leaves the balance
  unchanged.
- **N9. Deposits accumulate.** Successive deposits accumulate into a running sum.

### Withdraw
- **N5. Withdraw `<` balance.** Withdrawing less than the balance decreases it by
  exactly that amount.
- **N6. No overdraft.** Withdrawing more than the balance is rejected; balance
  unchanged.
- **N7. Withdraw `≤0` rejected.** Withdrawing `0` or a negative amount leaves the
  balance unchanged.
- **N8. Withdraw full → 0.** Withdrawing exactly the full balance succeeds and
  leaves balance `0`.

### Transaction history
- **N10. Deposit recorded.** A successful deposit is recorded in the account's
  transaction history (observable via the history / statement / report surface).

## Dependency usage

> "Abstract Base Classes: Use of the abc module to define contracts for interfaces and abstract behaviors (e.g., AbstractAccount, AbstractTransaction)."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `abc` | pass | pass | pass | pass |
