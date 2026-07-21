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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence (`main.py`) |
|---|---|
| `A002_DepositCLS --|> A001_TransactionCLS` | `class A002_DepositCLS(A001_TransactionCLS)` (L78) |
| `A003_WithdrawCLS --|> A001_TransactionCLS` | `class A003_WithdrawCLS(A001_TransactionCLS)` (L90) |
| `C002_CurrentAccountCLS --|> C001_AccountCLS` | `class C002_CurrentAccountCLS(C001_AccountCLS)` (L179) |
| `C003_DecoratedCAAccountCLS --|> C002_CurrentAccountCLS` | `class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS)` (L201) |
| `{abstract} A001_registerMTD(account)` on `A001_TransactionCLS` | `@abstractmethod def A001_registerMTD` (L74–75) |
| `B001_HistoryCLS` methods | `B001_add_transactionMTD` (L111), `B001_transaction_generatorMTD` (L116) |
| `C001_AccountCLS` methods | `C001_depositMTD` (L143), `C001_withdrawMTD` (L159), `C001_transaction_reportMTD` (L175) |
| `C002_CurrentAccountCLS` method | `C002_withdrawMTD` (L186) |
| `C003_DecoratedCAAccountCLS` members | `C003_balanceMTD` / `C003_limitMTD` `@property` accessors (L205–227) |
| `B001_HistoryCLS --* C001_AccountCLS : C001_history` | `self.C001_history = B001_HistoryCLS()` in `C001_AccountCLS.__init__` (L131) |

## Facts pinned

### Inheritance links (`--|>`)
- **U1. `A002_DepositCLS --|> A001_TransactionCLS`.** Deposit is a proper subclass
  of the abstract transaction.
- **U2. `A003_WithdrawCLS --|> A001_TransactionCLS`.** Withdraw is a proper
  subclass of the abstract transaction.
- **U3. `C002_CurrentAccountCLS --|> C001_AccountCLS`.** The current account
  specializes the base account.
- **U4. `C003_DecoratedCAAccountCLS --|> C002_CurrentAccountCLS`.** The decorated
  account specializes the current account.

### Abstract operation
- **U5. Abstract `A001_registerMTD`.** `A001_TransactionCLS.A001_registerMTD` is
  present **and** marked abstract (the polymorphism contract the subclasses
  override). Class absent → fail; present but not abstract → fail.

### Methods / properties under a class
- **U6. History method set.** `B001_HistoryCLS` defines both
  `B001_add_transactionMTD` and `B001_transaction_generatorMTD`.
- **U7. Account core operations.** `C001_AccountCLS` defines `C001_depositMTD`,
  `C001_withdrawMTD`, and `C001_transaction_reportMTD`.
- **U8. Current-account withdraw override.** `C002_CurrentAccountCLS` defines its
  own `C002_withdrawMTD` (the distinct method the diagram draws on the subclass,
  distinct from the inherited `C001_withdrawMTD`).
- **U9. Decorated property accessors.** `C003_DecoratedCAAccountCLS` defines both
  `C003_balanceMTD` and `C003_limitMTD` (the `@property` members the box lists).

### Composition link (`--*`)
- **U10. `B001_HistoryCLS --* C001_AccountCLS`.** `C001_AccountCLS` owns a history
  attribute (`C001_history`) built from `B001_HistoryCLS`. Detected statically:
  the part-class name appears in the owner's `__init__` code object or in a class
  annotation (no instantiation). Part class absent → fail; owner present but not
  wiring it up → fail.

## Harness

The pinned surface is the **structure the class diagram draws** — inheritance
links (`--|>`), the `{abstract}` operation, the methods/properties under each
class, and the `--*` composition — asserted by **reflection on the loaded
classes** (subclass relations, `__dict__`/`dir` membership, `__isabstractmethod__`,
the `__init__` code object), never by executing behavior. A class a generation
does not define is a **FAILURE**, as is a class that is present but whose
link/method diverges. This track does not skip / mark N/A. Subjects are the 4 UML generations
(`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin `main.py` the diagram
was extracted from grounds the facts above but is not itself a test subject.

## Portability

Every source here is pure standard library; the loader still installs a
permissive import finder so any optional third-party top a generation might import
(and that is missing on the host) resolves to a stub and the module execs far
enough to *define* its classes. Only the standard library is required.
