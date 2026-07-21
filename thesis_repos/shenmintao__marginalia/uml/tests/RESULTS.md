# Conformance results — `marginalia` **UML track**

Reference: origin `marginalia-main/src/marginalia/db/models/` · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see [CONTRACT.md](CONTRACT.md))
· pytest 9.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 entities share `Base` | P | P | P | P |
| U2 entities share `IdMixin` | P | P | P | P |
| U3 `UtcDateTime` hook pair | P | P | P | P |
| U4 `Base` metadata/type_annotation_map | P | P | P | P |
| U5 `TimestampMixin` created/updated | P | P | P | P |
| U6 `Task` queue field set | P | P | P | P |
| U7 `File` content field set | P | P | P | P |
| U8 `Conversation` counter field set | P | P | P | P |
| U9 `total_cost_estimate --> Decimal` | P | P | P | P |
| U10 `is_system --> bool` | P | P | P | P |
| **Pass / 10** | 10 | 10 | 10 | 10 |
| **Score** | 1.000 | 1.000 | 1.000 | 1.000 |

Run summary: **40 passed, 0 failed, 0 N/A.**

## Interpretation

The DB schema is reproduced with **complete structural fidelity** across all
four generations — unsurprising given the class diagram was the prompt: every
generation defines all 15 ORM entities plus the four mixin/type classes, each
with its full drawn member set, the two `UtcDateTime` hooks, and the
distinctive `Decimal`/`bool` member types.

Notable-but-not-pinned variations (they don't touch the drawn structure, so they
neither pass nor fail here):

- **`UtcDateTime` base.** The origin, `uml/claude`, `uml/deepseek`, `uml/gemini`
  subclass SQLAlchemy's `TypeDecorator`; `uml/gpt` makes `UtcDateTime` a plain
  class. The diagram draws no `--|>` for it, so U3 grades only the two methods —
  which all four define.
- **`Mapped` provenance.** `uml/gpt` defines its own `Mapped`/`MetaData`
  placeholders instead of importing SQLAlchemy's; the annotations still read
  `Mapped[Decimal]` etc., so U9/U10 pass.
- **`EntryTag` identity.** In the origin `EntryTag` has a composite PK and no
  `IdMixin`; every generation instead gives it `IdMixin`. U2 deliberately
  excludes `EntryTag` (matching the origin); the widening is a non-drawn detail.

(The *behavioral* fidelity of `UtcDateTime` — whether `process_bind_param`
actually converts an aware datetime to UTC — is a separate question graded on
the NL/behavioral axis of the combined analysis, not here: this track only
asserts the method *exists*.)

## Reproduce

```bash
cd thesis_repos/shenmintao__marginalia/uml/tests
python3 -m pytest -v -p no:warnings                     # full matrix
```
