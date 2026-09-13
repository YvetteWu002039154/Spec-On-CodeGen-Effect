# Behavioral contract — `library-service-api` **NL track**

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
