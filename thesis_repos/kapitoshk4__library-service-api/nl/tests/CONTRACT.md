# Behavioral contract — `library-service-api` **NL track**

Reference for grounding: origin repo `library-service-api-main/` (a Django REST
library borrowing service). **There is no reference *subject* in the NL track** —
the four NL generations are the only subjects. This contract is derived by
comparing the **NL description** (`nl/input/description.txt`) with the **origin
code**, then pinning the observable behaviors every reasonable implementation of
that description would expose.

Behaviors are asserted on **observable capability and effect**. Each generation
is driven by its own explicit driver (`adapter.py`) that names the exact
classes/functions it uses — the generations diverge wildly: an embedded WSGI
project with an in-memory `db` and a `PaymentCalculator` (`claude`), DRF models
plus business-logic helper functions (`gpt`), a FastAPI/pydantic service with
inline endpoint logic (`gemini`), and a relative-import Django package that does
not import here (`deepseek`). A capability a generation does not expose at a
drivable domain level is a behavioral **FAILURE** — this suite does not skip /
mark N/A. The driver attempts the real domain API and the resulting
empty/`AttributeError`/wrong value fails the assert.

## Description feature → origin grounding

| Description feature | Origin evidence |
|---|---|
| "Make borrowing" / "Make payment after borrowing" | `Borrowing.total_price` = `(expected_return_date − borrow_date).days × book.daily_fee` (`borrowings/models.py`) |
| "FINE payment if borrowing is overdue" | overdue fine = `overdue_days × daily_fee × 2` (fine multiplier); charged only when returned late |
| "Make payment" + "FINE payment" | `Payment.Type` = `{Payment, Fine}` (`payments/models.py`) |
| payment lifecycle | `Payment.Status` = `{Pending, Paid, Expired}` (`payments/models.py`) |
| "Make borrowing and return them" / manage book stock | `Borrowing.validate_borrowing(inventory)` raises `ValidationError` when `inventory == 0` (`borrowings/models.py`) |

## Behaviors pinned

### Borrowing price
- **N1. Price = days × daily_fee.** The amount owed for a borrowing equals the
  number of days between borrow and expected-return multiplied by the book's
  daily fee. (Pinned twice: `7 × 2.00 = 14.00`, and linear scaling `10 × 1.50 =
  15.00`.)

### Overdue fine
- **N2. Overdue fine = overdue_days × daily_fee × 2.** Returning 5 days late at
  `2.00`/day incurs a `20.00` fine.
- **N3. No fine when on time.** Returning on the expected date incurs a `0` fine.

### Payment vocabulary
- **N4. Payment-type distinguishes a FINE.** The payment-type vocabulary carries
  a `fine` type plus at least one regular (non-fine) payment type. Asserted on
  the presence of a fine-vs-regular distinction, not a literal token, since the
  origin's regular type is `Payment` while `gpt` names it `Borrowing`.
- **N5. Payment-status vocabulary.** The payment-status vocabulary contains both
  `pending` and `paid`.

### Stock control
- **N6. Out-of-stock borrowing rejected.** A borrowing against a book with
  `inventory == 0` is rejected (raises), while `inventory > 0` is allowed.
  (Pinned as two cases.)

## Notes for the drivers

- **Price/fine** are driven through the calculator a generation exposes: a
  static calculator reading a shared in-memory store (`claude`:
  `PaymentCalculator.calculate_payment` / `calculate_fine`, backed by the
  module-level `db`) or a module-level helper taking a borrowing object (`gpt`:
  `calculate_borrowing_amount` / `calculate_fine_amount`). Test dates are in the
  future and the fine cases pass an explicit actual-return date, isolating the
  computation. A generation whose price/fine logic lives only inside an HTTP
  endpoint (`gemini`) exposes no drivable calculator, so its driver attempts the
  calculator and fails (`AttributeError`) → **FAIL**.
- **Out-of-stock** is driven via a shared store's `create_borrowing` (`claude`).
  Generations that validate stock only inside a DRF serializer / FastAPI endpoint
  (`gpt`, `gemini`) expose no model-level guard, so their drivers attempt the
  guard and fail → **FAIL**.
- **Vocabularies** (N4/N5) are read from each generation's payment enums
  (`gpt`: `Payment.Type` / `Payment.Status`; `gemini`: `PaymentType` /
  `PaymentStatus`). `claude` uses bare string constants validated in functions
  and exposes no enum, so its driver attempts the enum and fails → **FAIL**.
- **`deepseek`** does not import (a relative import with no parent package), so
  every behavior its driver drives fails → **FAIL** across the board.
- **Out of scope** (no portable, description-level entry point): JWT auth, the
  `/admin/` panel, Swagger docs, and per-endpoint filtering — these are framework
  plumbing rather than domain behavior.

## Portability

A minimal Django config (the four origin model apps + DRF) is set up once so the
Django-model generations exec far enough to define their classes; each generation
is loaded under a synthetic one-off Django app. System libraries (Django, DRF,
FastAPI, pydantic) are kept real. A `CheckConstraint(check=…)` → `condition=…`
compat shim maps a kwarg Django 6 renamed. `nl/gpt` / `nl/deepseek` were later
scaffolded into full projects with the single file preserved as
`generated_code(original).py`; the loader falls back to that name. `deepseek`
still fails to import (unresolved relative import); its driver then fails every
behavior rather than skipping.
