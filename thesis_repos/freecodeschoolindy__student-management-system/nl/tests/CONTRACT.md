# Behavioral contract — `student-management-system` **NL track**

Reference for grounding: the origin repo `student-management-system-main/`
(a Django REST project) — chiefly `apps/users/models.py`,
`apps/waitlist/models.py`, `apps/volunteers/models.py`.

This contract is derived by comparing the **NL description**
(`nl/input/description.txt`) with the **origin code**, then pinning the
observable behaviors every reasonable implementation of that description would
expose. Behaviors are asserted on **observable capability and effect**. Each
generation is driven by its own explicit driver (`adapter.py`) that names the
exact classes and methods it uses. A capability a generation does not expose is
a behavioral **FAILURE** — this suite does not skip / mark N/A. There is **no
reference subject** in the NL track — the 4 NL generations are the only subjects.

## Description feature → origin grounding

| Description feature | Origin evidence |
|---|---|
| "accounts for students to login" | `apps/users/models.py::CustomUserManager.create_user` + `User(AbstractBaseUser)` — email/password auth via `set_password`/`check_password` |
| Students **and** Organizers/Admin accounts | `User.is_admin` / `User.is_staff` / `User.is_student` role flags distinguish admins from students |
| "Private Student Profile: Visible to only the user and organizers/admins" | `apps/users/models.py::UserProfile` (a per-user profile) + `User.has_perm`/`has_module_perms` and the role flags gating who may view it |
| Admin Dashboard → **Waitlist** | `apps/waitlist/models.py::WaitlistEntry` (email/name entries) |
| Admin Dashboard → **Volunteer management** | `apps/volunteers/models.py::Volunteer` (+ `VolunteerHours`) |
| Admin Dashboard → **Student Progress/Outcomes** | the profile/role surface admins read (progress/outcomes attached to students) |

## Behaviors pinned

### Authentication
- **N1. Login succeeds.** A registered student can log in with the correct
  password (login returns without raising).
- **N2. Wrong password rejected.** Logging in with an incorrect password raises.
- **N3. Unknown user rejected.** Logging in with an unknown username raises.

### Private student profile (access control)
- **N4. Owner can view.** A student profile is viewable by its owner.
- **N5. Other user denied.** The same profile is **not** viewable by a
  different non-admin user (access is denied).
- **N6. Admin can view.** The profile is viewable by an admin/organizer.

### Waitlist
- **N7. Waitlist add → listed.** An entry added to the waitlist then appears in
  the waitlist listing.

### Volunteer management
- **N8. Volunteer add → listed.** A volunteer added to the system then appears
  among the listed volunteers.

### Roles
- **N9. Role vocabulary.** The system distinguishes a **student** role from an
  **admin** role.

## Per-generation drivers

The description drove four very different architectures, so `adapter.py` defines
one explicit driver per generation that names the concrete classes/methods it
uses. There is no reflection / auto-detection and no skip: a behavior a
generation cannot express **fails**.

- **claude** — a `StudentManagementSystem` facade with **token sessions**:
  `register_user(..., role=...)`, `login` returns a `{token, user}` dict, profile
  access is `create_student_profile(token,…)` + `get_student_profile(token, id)`,
  waitlist/volunteers are system-level (`add_to_waitlist`/`get_waitlist`,
  `add_volunteer`/`get_all_volunteers`). Roles come from the returned `role` token.
- **gpt** — a facade keyed by **username**: `register_student`/`register_admin`,
  `login` returns a `UserAccount`, access is
  `get_private_student_profile(requester, student)` (other → `AuthorizationError`),
  waitlist via the standalone `Waitlist`, volunteers via `VolunteerManagement`.
- **gemini** — **object handles**: `register_student`/`register_admin`/
  `register_volunteer`, a `Student` object answers `get_profile(requester)`
  (identity or `Role.ADMIN` succeeds, else `PermissionError`), waitlist via the
  `Waitlist` class, volunteers via the public `volunteers` collection, roles via a
  `Role` enum.
- **deepseek** — a **Django app module** (models + admin) that cannot be imported
  standalone (`LookupError: No installed app with label 'admin'`). Its driver
  names deepseek's real surface (`User`, `StudentProfile`, `WaitlistEntry`,
  `Volunteer`); because the module never loads, every behavior **fails**.

## Dependency usage
The behaviors above are deliberately **dependency-agnostic** (the drivers
fake or stub external services), so a generation that reimplements a
dependency with a plain substitute still passes them. This section pins the
complementary axis — does a generation **import and use the package(s) the
description names**, rather than hand-roll a substitute?

> "admins can login and see everyone via the Django admin interface."

The check is **static** (`loader.dependency_used`, AST only — it never
imports the module, so it is independent of whether the package is installed).
A dependency passes when the file both **imports** the package *and*
**references** what it imported at least once (guarding against a dead
import). It is deliberately scoped to import-and-use, not correct-API
verification. A generation delivered as a full project directory passes if
any of its `.py` files imports-and-uses the package.

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `django` | FAIL | FAIL | pass | FAIL |

Only **deepseek** builds on Django (models/admin); claude, gpt and gemini hand-roll the student store in plain Python and never import `django` — the exact gap this axis surfaces.
