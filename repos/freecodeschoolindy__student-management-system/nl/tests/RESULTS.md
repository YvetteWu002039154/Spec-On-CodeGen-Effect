# Conformance results — `student-management-system` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
Each is driven by its own explicit driver in `adapter.py`. `pass` = behavior
matches the contract · `FAIL` = capability wrong or **not exposed** (this suite
does not skip / mark N/A). Suite: `nl/tests/test_conformance.py` (9 behaviors,
see [CONTRACT.md](CONTRACT.md)).

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  login succeeds | pass | pass | FAIL | pass |
| N2  wrong password rejected | pass | pass | FAIL | pass |
| N3  unknown user rejected | pass | pass | FAIL | pass |
| N4  profile visible to owner | pass | pass | FAIL | pass |
| N5  profile denied to other user | pass | pass | FAIL | pass |
| N6  profile visible to admin | pass | pass | FAIL | pass |
| N7  waitlist add → listed | pass | pass | FAIL | pass |
| N8  volunteer add → listed | pass | pass | FAIL | pass |
| N9  role vocabulary (student/admin) | pass | pass | FAIL | pass |

**Totals:** 27 passed, 9 failed.

## Interpretation

The NL description ("students/organizers/admins login; a private student
profile visible only to the user and organizers/admins; an admin dashboard with
volunteer management and a waitlist") admits several architectures, and the three
runnable generations each realized the full behavioral surface with a different
shape:

- **claude** — a `StudentManagementSystem` facade with **token sessions**.
  Profile access is `get_student_profile(token, profile_id)`; the owner and an
  admin token succeed, a second student's token raises `PermissionError`. Waitlist
  and volunteers are system-level (`add_to_waitlist`/`get_waitlist`,
  `add_volunteer`/`get_all_volunteers`). Roles are `student`/`organizer`/`admin`.
- **gpt** — a facade keyed by **username**. Access is
  `get_private_student_profile(requester, student)` (owner/admin succeed, other
  raises `AuthorizationError`); waitlist/volunteers via the standalone `Waitlist`
  and `VolunteerManagement` classes. Roles are `student`/`admin`.
- **gemini** — **object handles**. A `Student` object answers
  `get_profile(requester)` (identity or `Role.ADMIN` succeeds, else
  `PermissionError`); waitlist via the `Waitlist` class; volunteers via
  `register_volunteer` + the public `volunteers` collection. A `Role` enum carries
  `student`/`admin`.

## The failures

- **deepseek** — this generation is a **Django app module** (custom `User`,
  `StudentProfile`, admin registrations, views, URLs) rather than a runnable
  service. It cannot be imported standalone — loading it raises
  `LookupError: No installed app with label 'admin'` (it depends on a full Django
  project's app registry). The deepseek driver names its real Django surface
  (`User`, `StudentProfile`, `WaitlistEntry`, `Volunteer`), but because the module
  never loads every attribute access raises `AttributeError`, so all 9 behaviors
  **FAIL**. This is a meaningful conformance observation: the NL description was
  answered with a framework-embedded app, not a self-contained API.

## Reproduce

```bash
cd repos/freecodeschoolindy__student-management-system/nl/tests
python3 -m pytest -q -p no:warnings
```

## Dependency usage

Complementary to the behavior matrix above: does each generation **import
and use the package(s) the description names** (static AST check,
`loader.dependency_used`), or hand-roll a substitute? `pass` = imports and
references the package · `FAIL` = does not use it (absent, or a dead import).

| dependency | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| `django` | FAIL | FAIL | pass | FAIL |

Only **deepseek** builds on Django (models/admin); claude, gpt and gemini hand-roll the student store in plain Python and never import `django` — the exact gap this axis surfaces.
