# Conformance results — `library-service-api` **UML track**

Reference: origin repo `library-service-api-main/` model layer · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see [CONTRACT.md](CONTRACT.md)) ·
pytest 9 / Python 3.12 / Django 6.0. Subjects: the 4 UML generations
(`uml/outputcode/{claude,gpt,deepseek,gemini}`). The origin model layer the
diagram was extracted from grounds the contract but is not a test subject.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 `Book` attributes | P | P | P | P |
| U2 `Borrowing` attributes | P | P | P | P |
| U3 `Payment` attributes | P | P | P | P |
| U4 `Book.Cover` {HARD, SOFT} | P | P | P | P |
| U5 `Payment.Status` {PENDING, PAID, EXPIRED} | P | P | P | P |
| U6 `Payment.Type` {PAYMENT, FINE} | P | P | P | P |
| U7 `Borrowing.validate_borrowing` | P | P | P | P |
| U8 `Borrowing.clean` | P | P | F | F |
| U9 `UserManager` create_user/create_superuser | P | P | P | P |
| U10 `User.objects --* UserManager` | P | P | P | P |
| **Pass / 10** | 10 | 10 | 9 | 9 |
| **Score** | 1.000 | 1.000 | 0.900 | 0.900 |

Run summary: **38 passed, 2 failed, 0 N/A.**

## How the structure diverged

The class structure is reproduced with near-full fidelity: every generation
defines all three entity classes with the diagrammed attributes, all three
nested choice families (`Cover` / `Status` / `Type`) with their complete member
sets, `Borrowing.validate_borrowing`, both `UserManager` factory methods, and the
`User.objects = UserManager()` association.

- The plain-Python generations (`gpt`, `deepseek`, `gemini`) realize the
  attributes as `__init__` parameters/assignments and the choice families as
  `enum.Enum` (`gpt`) or plain constant-holding classes (`deepseek`, `gemini`)
  rather than Django fields / `TextChoices`; the contract grades the *structural
  fact* (the attribute/member exists), so these count as conformant.
- `uml/claude` mirrors the origin most literally (Django models + `TextChoices`).

The one method-body divergence is **U8 `Borrowing.clean`**: the method-set facts
now require a real (non-stub) body. `uml/claude` and `uml/gpt` give `clean`
genuine validation logic and pass; `uml/deepseek` and `uml/gemini` emit it as a
bare `pass` (a placeholder that drops the model-wide validation the diagram
draws), so it is judged *not* implemented and fails. `validate_borrowing` (U7) is
really implemented in all four.

Further divergence in this repo is **behavioral**, not structural (e.g. whether
the borrowing price is computed vs taken as a constructor input) — captured by
the NL track, not the class diagram.

## Classification

- **2 F** (`uml/deepseek`, `uml/gemini` at U8) — `Borrowing.clean` present only
  as a stub. **No N/A**: every generation defines all diagrammed classes.
- The set/superset checks tolerate extra members, and U10 grades the *class name*
  of `User.objects` (which Django preserves for a real manager), so the passes
  are genuine rather than over-permissive.

## Reproduce

```bash
cd thesis_repos/kapitoshk4__library-service-api/uml/tests
python3 -m pytest -v                # full matrix
```
