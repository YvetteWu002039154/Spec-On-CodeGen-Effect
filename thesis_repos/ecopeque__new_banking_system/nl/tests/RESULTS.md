# Conformance results — `new_banking_system` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
Suite: `nl/tests/test_conformance.py` (10 behaviors, see [CONTRACT.md](CONTRACT.md)).
Each generation is driven by its own explicit driver in `adapter.py`.
`pass` = behavior matches the contract · `FAIL` = capability wrong or **not
exposed** (this suite does not skip / mark N/A). Success is judged by the
observable **balance change** / history effect, so bool-returning,
`None`-returning, and exception-raising impls are compared on equal footing.

## Matrix (P = pass, F = fail)

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  new balance = 0 | P | P | P | P |
| N2  deposit increases | P | P | P | P |
| N3  deposit 0 rejected | P | P | P | P |
| N4  deposit <0 rejected | P | P | P | P |
| N9  deposits accumulate | P | P | P | P |
| N5  withdraw < balance | P | P | P | P |
| N6  no overdraft (withdraw > balance rejected) | P | P | **F** | P |
| N7  withdraw ≤0 rejected | **F** | P | P | P |
| N8  withdraw full → 0 | P | P | P | P |
| N10 deposit recorded in history | **F** | **F** | P | **F** |
| **Pass / 10** | 8 | 9 | 9 | 9 |

**Run summary:** 35 passed, 5 failed, 0 skipped (~0.04s, no hang).

## All four agree on the arithmetic core (N1–N5, N8, N9)

Every NL generation correctly implements zero opening balance, positive-amount
validation on deposit, deposit accumulation, and basic withdrawal arithmetic
including the exact-balance boundary. The divergence is confined to two
behaviors.

## Failure analysis (all are genuine divergences)

Each `F` was traced to source; none is an over-strict test (each driver names
that generation's real deposit/withdraw entry point, and the six shared
arithmetic behaviors pass for all four).

- **N6 — overdraft allowed (`nl/deepseek`).** `CurrentAccount._validate_withdraw`
  treats the account `limit` as an **overdraft allowance** (permits while
  `balance + limit >= amount`), so withdrawing 200 from a 100 balance succeeds.
  The description's "minimum balance checks" and the origin `A003_WithdrawCLS`
  both forbid overdraft. Genuine semantic divergence.
- **N7 — negative withdrawal raises the balance (`nl/claude`).** `CurrentAccount.
  withdraw` has no positive-amount guard: a negative amount passes the
  insufficient-balance check and is then *subtracted*, so `withdraw(-25)`
  **increases** the balance. Clear bug.
- **N10 — deposit not recorded (`nl/claude`, `nl/gpt`, `nl/gemini`).** Each
  defines a history/record container but **never calls it from `deposit`**, so
  the log stays empty — the capability is present but not wired (→ FAIL, not
  N/A). `nl/deepseek` records correctly.

## No N/A cells

Every NL generation was constructible and exposed a readable balance, a
deposit/withdraw entry point, and a history surface, so every behavior resolved
to a genuine pass or fail (no capability was absent). Had a capability been
missing, the driver's real call would have failed the assert (FAIL), never
skipped.

## Reproduce

```bash
cd thesis_repos/ecopeque__new_banking_system/nl/tests
python3 -m pytest -v -p no:warnings
```

## Dependency usage

Complementary to the behavior matrix above: does each generation **import
and use the package(s) the description names** (static AST check,
`loader.dependency_used`), or hand-roll a substitute? `pass` = imports and
references the package · `FAIL` = does not use it (absent, or a dead import).

| dependency | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| `abc` | pass | pass | pass | pass |

All four use `abc` (ABCMeta / `abstractmethod`) to declare the abstract account/transaction bases the description calls for.
