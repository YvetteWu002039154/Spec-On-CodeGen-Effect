# Conformance results — `student-management-using-django` **UML track**

Reference: origin `student-management-using-django-main/main_app/models.py` ·
Suite: `uml/tests/test_conformance.py` (10 structural facts, see
[CONTRACT.md](CONTRACT.md)) · pytest 9 / Python 3.12 / Django 6.0.

## Matrix (P = pass, F = fail)

| Fact | uml/claude | uml/gpt | uml/deepseek | uml/gemini |
|---|---|---|---|---|
| U1 manager create_user/superuser | P | P | P | P |
| U2 `CustomUserManager --* CustomUser` | P | P | P | P |
| U3 CustomUser auth vocabulary | P | P | P | P |
| U4 Student → CustomUser/Course/Session | P | P | P | P |
| U5 Staff → CustomUser/Course | P | P | P | P |
| U6 Subject → Course/**Staff** | **F** | P | P | P |
| U7 Attendance → Session/Subject | P | P | P | P |
| U8 AttendanceReport → Attendance/Student | P | P | P | P |
| U9 StudentResult → Student/Subject | P | P | P | P |
| U10 Session start_year/end_year | P | P | P | P |
| **Pass / 10** | 9 | 10 | 10 | 10 |
| **Score** | 0.900 | 1.000 | 1.000 | 1.000 |

Run summary: **39 passed, 1 failed, 0 N/A.**

## How the structure diverged

The UML class structure is reproduced with **high fidelity**. All four
generations define the full set of model classes, the `CustomUserManager` method
pair, the
`objects` composition link, the CustomUser auth vocabulary, and the association
web — across three quite different representations (Django ORM, annotation-only,
property-based).

The only divergence:

- **`uml/claude` mis-targets `Subject.staff`.** The diagram (and origin) draw
  `Subject.staff → Staff`, but `uml/claude` declares
  `staff = models.ForeignKey(CustomUser, …)` — the association points at
  `CustomUser` instead of the `Staff` profile model (U6 → F). Every other
  association it draws is correct. The three other generations target `Staff`.

## Classification

- The one `F` is a genuine structural divergence (the association's target class
  is wrong), not an over-strict test: the membership checks tolerate extra
  referenced names.
- **No N/A** this track — every generation defines all the classes, attributes,
  and the manager methods the diagram names, and every association target type was
  recoverable by reflection for all four generations.

## Reproduce

```bash
cd thesis_repos/jobic10__student-management-using-django/uml/tests
python3 -m pytest -v -p no:warnings                # full matrix
```
