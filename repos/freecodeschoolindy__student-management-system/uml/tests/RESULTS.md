# Conformance results — `student-management-system` **UML track**

Reference: origin `student-management-system-main/apps/**/models.py` · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see [CONTRACT.md](CONTRACT.md))
· pytest 9 / Python 3.12 / Django 6.0.

## Matrix (P = pass, F = fail)

| Fact | uml/claude | uml/gpt | uml/deepseek | uml/gemini |
|---|---|---|---|---|
| U1 `WaitlistEntry --|> AbstractTableMeta` | P | P | F | P |
| U2 `Certificate --|> AbstractTableMeta` | P | P | F | P |
| U3 `User --* CustomUserManager` | P | P | F | P |
| U4 `UserProfile --> User` | P | P | F | P |
| U5 manager `create_user`/`create_superuser` | P | P | F | P |
| U6 user `has_perm`/`has_module_perms` | P | P | F | P |
| U7 `WaitlistEntry.full_name` | P | P | F | P |
| U8 `Volunteer.full_name` | P | P | F | P |
| U9 user role flags `is_admin/is_staff/is_student` | F | P | F | P |
| U10 `UserProfile.LEVELS : tuple` | P | P | F | P |
| **Pass / 10** | 9 | 10 | 0 | 10 |
| **Score** | 0.900 | 1.000 | 0.000 | 1.000 |

Run summary: **29 passed, 11 failed, 0 skipped.**

## How the structure was reproduced

The UML class structure is reproduced with **high fidelity**. Both inheritance
links (`WaitlistEntry`/`Certificate --|> AbstractTableMeta`), the
`User --* CustomUserManager` composition, the `UserProfile --> User` association,
the `CustomUserManager`/`User` method sets, and the two `full_name` members are
matched by **every** importable generation (claude, gpt, gemini). `UserProfile.LEVELS`
is a tuple in all of them (its *values* differ — `Level 1..5`, `Beginner/…`, or
empty `()` — but the diagram only declared `LEVELS : tuple`, so the type is what
is pinned).

The non-pass cells are structural, not test artifacts. This track does **not**
skip / mark N/A: a diagrammed class/attribute a generation does not expose is a
**FAIL**.

- **`uml/claude` / U9 → FAIL.** claude's `User.__init__(self, email='', **kwargs)`
  pulls `is_admin`/`is_staff`/`is_student` out of `**kwargs` and never *declares*
  them as class fields, annotations, or explicit parameters. The class exists but
  omits the declared role flags → FAIL (the diagram names them and they are not
  exposed). gpt and gemini declare them as `__init__` parameters; the origin
  Django models declare them as `BooleanField`s.
- **`uml/deepseek` / all → FAIL.** This generation is a Django **models module**
  with concrete models but no `app_label`; importing it standalone raises
  `RuntimeError: Model class …User doesn't declare an explicit app_label …`. It
  cannot be reflected without a full Django project, so it exposes none of the
  diagrammed structure and all 10 facts FAIL.

## Classification

- **Among the importable generations, `uml/gpt` and `uml/gemini` have no `F`;
  `uml/claude` fails only U9** (undeclared role flags). Each reproduces the
  diagram's inheritance, association, method, and attribute structure otherwise.
  `uml/deepseek` fails all 10 (non-standalone Django module that does not import).
  The behavioral divergences the combined root suite once recorded (email
  normalization, password hashing, `has_perm` returning `is_admin`) are
  *behavioral*, not structural, and are out of scope for this reflection-only track.

## Reproduce

```bash
cd repos/freecodeschoolindy__student-management-system/uml/tests
python3 -m pytest -v -p no:warnings          # full matrix
```
