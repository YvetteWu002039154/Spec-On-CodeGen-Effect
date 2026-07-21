# Conformance results — `student-management-using-django` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
There is **no reference** in the NL track. Suite:
`nl/tests/test_conformance.py` (10 behaviors, see [CONTRACT.md](CONTRACT.md)) ·
pytest 9 / Python 3.12.

`pass` = observed effect matches the contract · `FAIL` = capability wrong or
**not exposed** (this suite does not skip / mark N/A — a missing capability fails
naturally when its driver drives the real API).

## Matrix (P = pass, F = FAIL)

| Behavior | nl/claude | nl/gpt | nl/deepseek | nl/gemini |
|---|---|---|---|---|
| N1  add course (carries name) | P | P | P | P |
| N2  add staff (present after) | P | P | P | P |
| N3  add student (present after) | P | P | P | P |
| N4  add subject (carries name) | P | P | P | P |
| N5  add session | P | P | P | P |
| N6  take attendance → present | P | P | P | P |
| N7  add result → marks readable | P | P | P | P |
| N8  apply leave → pending | P | P | P | P |
| N9  review leave → approved | P | P | P | P |
| N10 reply to feedback → stored | P | P | P | P |
| **Pass / 10** | 10 | 10 | 10 | 10 |
| **Score** | 1.000 | 1.000 | 1.000 | 1.000 |

Run summary: **40 passed, 0 failed.**

## Interpretation

The NL description is a **feature list** (CRUD over staff/students/courses/
subjects/sessions, plus attendance, results, leave review, and feedback reply).
All four generations reproduce that feature set faithfully, so every pinned
behavior is present and behaves correctly once its architecture is driven
appropriately:

- **nl/claude** — a single `StudentManagementSystem` facade; ids are UUID
  strings; passwords are sha256-hashed; leave status is an int (`0/1/-1`).
- **nl/gpt** — an admin-gated facade: create-methods require an `admin_id` and
  return integer ids; leave/feedback use `Enum` vocabularies
  (`LeaveStatus.PENDING/APPROVED`, `FeedbackStatus`); attendance uses an
  `AttendanceStatus` enum.
- **nl/deepseek** — module-level global stores (`users`, `courses`, …) plus
  `Admin`/`Staff`/`Student` role objects; leave uses an `Enum`; attendance is a
  bool. The adapter builds explicit `Staff`/`Student` instances because
  `add_staff`/`add_student` create plain `Person` objects.
- **nl/gemini** — a `StudentManagementSystem` holding the stores, with role
  methods that take the system as their first argument; leave status is a plain
  string (`"Pending"`/`"Approved"`).

No divergences surfaced against this behavior set: the differences between the
generations are **architectural** (how you reach a capability), not
**behavioral** (what the capability does), and each explicit driver reaches its
generation's real API. Any generation that had, e.g., not exposed the capability,
stored a leave as already-approved, dropped the attendance status, or failed to
persist a feedback reply would have produced a genuine `FAIL` here.

## Reproduce

```bash
cd thesis_repos/jobic10__student-management-using-django/nl/tests
python3 -m pytest -v -p no:warnings
```
