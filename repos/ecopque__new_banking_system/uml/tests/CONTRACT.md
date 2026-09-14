# Structural contract — `new_banking_system` **UML track**

Reference: origin repo `new_banking_system-main/main.py` — the single module the
class diagram was extracted from.

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the origin `main.py`) and
grounded in that origin code. A class diagram records *structure*, not runtime
behavior, so the pinned facts are the things the diagram actually draws:

1. **Inheritance links** — `Child --|> Parent`.
2. **An abstract operation** — a method drawn `{abstract}`.
3. **Methods / properties under a class** — the members listed inside each box.
4. **Composition link** — `Part --* Owner : attr`.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `A002_DepositCLS --|> A001_TransactionCLS` | `class A002_DepositCLS(A001_TransactionCLS)` (L78) |
| U2 | `A003_WithdrawCLS --|> A001_TransactionCLS` | `class A003_WithdrawCLS(A001_TransactionCLS)` (L90) |
| U3 | `C002_CurrentAccountCLS --|> C001_AccountCLS` | `class C002_CurrentAccountCLS(C001_AccountCLS)` (L179) |
| U4 | `C003_DecoratedCAAccountCLS --|> C002_CurrentAccountCLS` | `class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS)` (L201) |
| U5 | `{abstract} A001_registerMTD(account)` on `A001_TransactionCLS` | `@abstractmethod def A001_registerMTD` (L74–75) |
| U6 | `B001_HistoryCLS` methods | `B001_add_transactionMTD` (L111), `B001_transaction_generatorMTD` (L116) |
| U7 | `C001_AccountCLS` methods | `C001_depositMTD` (L143), `C001_withdrawMTD` (L159), `C001_transaction_reportMTD` (L175) |
| U8 | `C002_CurrentAccountCLS` method | `C002_withdrawMTD` (L186) |
| U9 | `C003_DecoratedCAAccountCLS` members | `C003_balanceMTD` / `C003_limitMTD` `@property` accessors (L205–227) |
| U10 | `B001_HistoryCLS --* C001_AccountCLS : C001_history` | `self.C001_history = B001_HistoryCLS()` in `C001_AccountCLS.__init__` (L131) |
