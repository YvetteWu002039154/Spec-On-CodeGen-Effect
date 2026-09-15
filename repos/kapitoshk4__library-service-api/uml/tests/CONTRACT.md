# Structural contract — `library-service-api` **UML track**

Reference: origin repo `library-service-api-main/` model layer (`books`,
`borrowings`, `payments`, `users` `.models`) — the modules the class diagram was
extracted from.

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the origin models) and
grounded in that origin code. A class diagram records *structure*, not runtime
behavior, so the pinned facts are the four things the diagram actually draws:

1. **Attributes under a class** — the fields listed inside `Book`, `Borrowing`,
   `Payment`.
2. **Nested choice/enum classes** — `Book.Cover`, `Payment.Status`,
   `Payment.Type` and their members.
3. **Methods under a class** — `Borrowing.clean` / `validate_borrowing`,
   `UserManager.create_user` / `create_superuser`.
4. **The association** — `UserManager --* User : objects` (the one relationship
   the diagram draws): `User.objects` is a `UserManager`.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `Book`: title/author/cover/inventory/daily_fee | `books/models.py::Book` fields |
| U2 | `Borrowing`: book/user/borrow_date/expected_return_date/actual_return_date/total_price | `borrowings/models.py::Borrowing` (fields + `total_price` property) |
| U3 | `Payment`: borrowing/money_to_pay/session_id/session_url/status/type | `payments/models.py::Payment` fields |
| U4 | `Book.Cover : {HARD, SOFT}` | `class Cover(models.TextChoices)` in `Book` |
| U5 | `Payment.Status : {PENDING, PAID, EXPIRED}` | `class Status(models.TextChoices)` in `Payment` |
| U6 | `Payment.Type : {PAYMENT, FINE}` | `class Type(models.TextChoices)` in `Payment` |
| U7 | `Borrowing.validate_borrowing(inventory: int)` | `@staticmethod validate_borrowing` |
| U8 | `Borrowing.clean()` | `def clean(self)` |
| U9 | `UserManager.create_user / create_superuser(email, password)` | `users/models.py::UserManager` |
| U10 | `UserManager --* User : objects` | `objects = UserManager()` on `User` |
