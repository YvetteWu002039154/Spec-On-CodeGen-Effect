# Behavioral contract — `student-management-system` **NL track**

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

## Dependency usage

> "admins can login and see everyone via the Django admin interface."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `django` | FAIL | FAIL | pass | FAIL |
