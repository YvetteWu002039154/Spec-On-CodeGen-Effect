# Conformance results — `library-service-api` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
No reference subject in this track. Each generation is driven by its own explicit
driver in `adapter.py`. Suite: `nl/tests/test_conformance.py`
(6 behaviors / 8 test cases, see [CONTRACT.md](CONTRACT.md)) · pytest 9 /
Python 3.12 / Django 6.0.

`pass` = behavior matches the contract · `FAIL` = capability wrong or **not
exposed** at a drivable domain level. This suite does **not** skip / mark N/A: a
missing capability is a FAILURE (the driver attempts the real domain API and the
resulting empty/`AttributeError`/wrong value fails the assert).

## Matrix (P = pass, F = fail)

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  price = days × daily_fee | P | P | F | F |
| N2  overdue fine = overdue × fee × 2 | P | P | F | F |
| N3  no fine when returned on time | P | P | F | F |
| N4  payment-type distinguishes FINE | F | P | F | P |
| N5  payment-status pending/paid | F | P | F | P |
| N6  out-of-stock borrowing rejected | P | F | F | F |
| **Pass / 8 cases** | **6** | **6** | **0** | **2** |

**Totals:** 14 passed, 18 failed (0 skipped).

## Per-implementation

- **claude (6/8).** Computes the borrowing price and overdue fine through
  `PaymentCalculator.calculate_payment` / `calculate_fine` (fine multiplier
  `2.0`), reading books from its in-memory `db`; `db.create_borrowing` rejects an
  out-of-stock book (N6). It has **no payment enum** — payment type/status are
  bare strings validated inside functions — so the driver's `m.PaymentType` /
  `m.PaymentStatus` lookup raises `AttributeError` (N4, N5) → **FAIL**.
- **gpt (6/8).** Computes the price (`calculate_borrowing_amount`) and fine
  (`calculate_fine_amount`, multiplier `2.00`) as module helpers over a DRF
  `Borrowing`, and defines `Payment.Type` / `Payment.Status` (N4, N5). Its
  out-of-stock check lives in the DRF serializer, not the model, so the driver's
  attempt at a model-level `Borrowing.validate_borrowing` raises `AttributeError`
  (N6) → **FAIL**. (Its regular payment type is named `BORROWING`, not `PAYMENT`
  — N4 grades the fine-vs-regular distinction, so this still passes.)
- **gemini (2/8).** A FastAPI service: price and fine are computed **inline**
  inside the `create_borrowing` / `return_borrowing` endpoints (no standalone
  calculator), and the stock check is an HTTP guard — so N1–N3 and N6 fail
  (`AttributeError` on the absent calculator / model guard). It does define
  `PaymentType` / `PaymentStatus` enums (N4, N5 pass).
- **deepseek (0/8).** **Does not import**: the file was scaffolded into a Django
  package and uses an unresolved relative import (`attempted relative import with
  no known parent package`). The driver wraps the load failure, so every behavior
  fails — no skip, no false pass.

## Classification

- Every cell that passed under the previous (reflection-based) suite still
  passes; the former `N/A` (skip) cells are now surfaced as `FAIL`, and the
  `deepseek` load failure is a `FAIL` rather than a skip.
- Each generation exposes a *different* subset of drivable domain behavior:
  `claude` computes money and guards stock but has no payment enum; `gpt` has
  both compute and vocab but validates stock in a serializer; `gemini` has only
  the vocab (its money/stock logic is endpoint-only); `deepseek` exposes nothing
  (does not load).

## Reproduce

```bash
cd thesis_repos/kapitoshk4__library-service-api/nl/tests
python3 -m pytest -q
```
