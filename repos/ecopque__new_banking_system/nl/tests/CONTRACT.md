# Behavioral contract — `new_banking_system` **NL track**

## Description features

| Description feature |
|---|
| "Managing accounts … performing transactions" / zero opening balance |
| "Performing deposits" + "proper validation" |
| "Performing … withdrawals" + "minimum balance checks" (no overdraft) |
| "Transaction history per account" / "tracking operations" |
| Running-balance accumulation |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Construction / balance | **New balance = 0.** A newly-constructed account starts at balance `0`. |
| N2 | Deposit | **Deposit increases.** Depositing a positive amount increases the balance by exactly that amount. |
| N3 | Deposit | **Deposit `0` rejected.** Depositing `0` leaves the balance unchanged. |
| N4 | Deposit | **Deposit `<0` rejected.** Depositing a negative amount leaves the balance unchanged. |
| N5 | Withdraw | **Withdraw `<` balance.** Withdrawing less than the balance decreases it by exactly that amount. |
| N6 | Withdraw | **No overdraft.** Withdrawing more than the balance is rejected; balance unchanged. |
| N7 | Withdraw | **Withdraw `≤0` rejected.** Withdrawing `0` or a negative amount leaves the balance unchanged. |
| N8 | Withdraw | **Withdraw full → 0.** Withdrawing exactly the full balance succeeds and leaves balance `0`. |
| N9 | Deposit | **Deposits accumulate.** Successive deposits accumulate into a running sum. |
| N10 | Transaction history | **Deposit recorded.** A successful deposit is recorded in the account's transaction history (observable via the history / statement / report surface). |

## Dependency usage

> "Abstract Base Classes: Use of the abc module to define contracts for interfaces and abstract behaviors (e.g., AbstractAccount, AbstractTransaction)."

| # | Check |
|---|---|
| D1 | imports and uses `abc` |
