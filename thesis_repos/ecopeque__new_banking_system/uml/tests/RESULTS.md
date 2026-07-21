# Conformance results — `new_banking_system` **UML track**

Reference: origin repo `new_banking_system-main/main.py` · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see [CONTRACT.md](CONTRACT.md)).
Subjects: the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`).
The origin `main.py` the diagram was extracted from grounds the contract but is
not a test subject.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 `A002_DepositCLS --|> A001_TransactionCLS` | P | P | P | P |
| U2 `A003_WithdrawCLS --|> A001_TransactionCLS` | P | P | P | P |
| U3 `C002_CurrentAccountCLS --|> C001_AccountCLS` | P | P | P | P |
| U4 `C003_DecoratedCAAccountCLS --|> C002_CurrentAccountCLS` | P | P | P | P |
| U5 `{abstract} A001_registerMTD` | P | P | P | P |
| U6 `B001_HistoryCLS` method set | P | P | P | P |
| U7 `C001_AccountCLS` core operations | P | P | P | P |
| U8 `C002_CurrentAccountCLS.C002_withdrawMTD` | **F** | P | P | P |
| U9 `C003` property accessors | P | P | P | P |
| U10 `B001_HistoryCLS --* C001_AccountCLS` | P | P | P | P |
| **Pass / 10** | 9 | 10 | 10 | 10 |
| **Score** | 0.900 | 1.000 | 1.000 | 1.000 |

**Run summary:** 39 passed, 1 failed, 0 skipped.

## How the structure diverged

The UML class structure is reproduced with **high fidelity**: both inheritance
families (the transaction hierarchy; the account hierarchy `C001 → C002 → C003`),
the abstract `A001_registerMTD` contract, the `B001_HistoryCLS`/`C001_AccountCLS`
method sets, the `C003` property accessors, and the `C001_history` composition
are matched by **all four** generations.

The only divergence:

- **`uml/claude` renames the current-account withdraw override (U8 → F).** The
  diagram draws `C002_withdrawMTD` as the distinct method on
  `C002_CurrentAccountCLS`; `uml/claude` instead overrides the base
  `C001_withdrawMTD` on the subclass and never defines `C002_withdrawMTD`. The
  override *behavior* is present, but the specifically-named method the diagram
  models is absent — a genuine structural divergence. (All four gens still keep
  the `C002_CurrentAccountCLS --|> C001_AccountCLS` link intact, so U3 passes for
  claude.)

## Classification

- The single `F` is a genuine structural divergence (the diagrammed method name
  is absent from a class that is otherwise present), not an over-strict test: the
  subset checks tolerate extra members.
- **No N/A** this track — every generation defines all the diagrammed classes;
  divergence shows up as a fail, not an absent class.

## Reproduce

```bash
cd thesis_repos/ecopeque__new_banking_system/uml/tests
python3 -m pytest -v -p no:warnings        # full matrix
```
