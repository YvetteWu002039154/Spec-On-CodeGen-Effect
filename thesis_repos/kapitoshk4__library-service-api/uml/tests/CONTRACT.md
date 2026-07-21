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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `Book`: title/author/cover/inventory/daily_fee | `books/models.py::Book` fields |
| `Book.Cover : {HARD, SOFT}` | `class Cover(models.TextChoices)` in `Book` |
| `Borrowing`: book/user/borrow_date/expected_return_date/actual_return_date/total_price | `borrowings/models.py::Borrowing` (fields + `total_price` property) |
| `Payment`: borrowing/money_to_pay/session_id/session_url/status/type | `payments/models.py::Payment` fields |
| `Payment.Status : {PENDING, PAID, EXPIRED}` | `class Status(models.TextChoices)` in `Payment` |
| `Payment.Type : {PAYMENT, FINE}` | `class Type(models.TextChoices)` in `Payment` |
| `Borrowing.validate_borrowing(inventory: int)` | `@staticmethod validate_borrowing` |
| `Borrowing.clean()` | `def clean(self)` |
| `UserManager.create_user / create_superuser(email, password)` | `users/models.py::UserManager` |
| `UserManager --* User : objects` | `objects = UserManager()` on `User` |

## Facts pinned

### Attributes under a class
- **U1. `Book` attributes.** `Book` models `title`, `author`, `cover`,
  `inventory`, `daily_fee`.
- **U2. `Borrowing` attributes.** `Borrowing` models `book`, `user`,
  `borrow_date`, `expected_return_date`, `actual_return_date`, `total_price`.
- **U3. `Payment` attributes.** `Payment` models `borrowing`, `money_to_pay`,
  `session_id`, `session_url`, `status`, `type`.

### Nested choice / enum classes
- **U4. `Book.Cover`.** A nested `Cover` type defining `HARD` and `SOFT`.
- **U5. `Payment.Status`.** A nested `Status` type defining `PENDING`, `PAID`,
  `EXPIRED`.
- **U6. `Payment.Type`.** A nested `Type` type defining `PAYMENT` and `FINE`.

### Methods under a class
- **U7. `Borrowing.validate_borrowing`.** The stock-validation method is present.
- **U8. `Borrowing.clean`.** The `clean()` method is present.
- **U9. `UserManager` methods.** Both `create_user` and `create_superuser` are
  present.

### Association (`--*`)
- **U10. `User.objects --* UserManager`.** `User.objects` is a `UserManager`
  (the one association the diagram draws).

## Harness

The pinned surface is the **structure the class diagram draws** — attributes,
nested choice/enum classes, methods, and the `User.objects --* UserManager`
association — asserted by **reflection on the loaded classes** (attribute/field
names, nested-class members, method names, the type of `objects`), never by
executing behavior. A pinned method must be a **real (non-stub) implementation**: a body that is only `pass` / `...` / `return None` / `raise NotImplementedError` is judged statically (from source, never executed) as *not* implemented and fails the method set. "Attribute is modelled" is read from any of: Django model
fields (`_meta`), class-level descriptors/properties, `__init__` parameters, and
class annotations — so both the Django reference and the plain-Python generations
(which assign attributes in `__init__`) are graded fairly. A class or attribute a
generation does not define is a **FAILURE**, as is a structural mismatch (the
class exists but a member/type is wrong or absent). This track does not skip /
mark N/A. Subjects are
the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin
model layer the diagram was extracted from grounds the facts above but is not
itself a test subject.

## Portability

`uml/claude` is a Django model module whose metaclass needs a configured Django to
build field descriptors, so a minimal Django (the four origin model apps + DRF) is
set up once; the other three UML generations are plain Python and load directly.
