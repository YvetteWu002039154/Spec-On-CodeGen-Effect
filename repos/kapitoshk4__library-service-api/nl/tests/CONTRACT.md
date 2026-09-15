# Behavioral contract — `library-service-api` **NL track**

## Description features

| Description feature |
|---|
| "Make borrowing" / "Make payment after borrowing" |
| "FINE payment if borrowing is overdue" |
| "Make payment" + "FINE payment" |
| payment lifecycle |
| "Make borrowing and return them" / manage book stock |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Borrowing price | **Price = days × daily_fee.** The amount owed for a borrowing equals the number of days between borrow and expected-return multiplied by the book's daily fee. (Pinned twice: `7 × 2.00 = 14.00`, and linear scaling `10 × 1.50 = 15.00`.) |
| N2 | Overdue fine | **Overdue fine = overdue_days × daily_fee × 2.** Returning 5 days late at `2.00`/day incurs a `20.00` fine. |
| N3 | Overdue fine | **No fine when on time.** Returning on the expected date incurs a `0` fine. |
| N4 | Payment vocabulary | **Payment-type distinguishes a FINE.** The payment-type vocabulary carries a `fine` type plus at least one regular (non-fine) payment type. Asserted on the presence of a fine-vs-regular distinction, not a literal token, since the origin's regular type is `Payment` while `gpt` names it `Borrowing`. |
| N5 | Payment vocabulary | **Payment-status vocabulary.** The payment-status vocabulary contains both `pending` and `paid`. |
| N6 | Stock control | **Out-of-stock borrowing rejected.** A borrowing against a book with `inventory == 0` is rejected (raises), while `inventory > 0` is allowed. (Pinned as two cases.) |

