# Behavioral contract — `student-management-system` **NL track**

## Description features

| Description feature |
| --- |
| "accounts for students to login" |
| Students **and** Organizers/Admin accounts |
| "Private Student Profile: Visible to only the user and organizers/admins" |
| Admin Dashboard → **Waitlist** |
| Admin Dashboard → **Volunteer management** |
| Admin Dashboard → **Student Progress/Outcomes** |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Authentication | **Login succeeds.** A registered student can log in with the correct password (login returns without raising). |
| N2 | Authentication | **Wrong password rejected.** Logging in with an incorrect password raises. |
| N3 | Authentication | **Unknown user rejected.** Logging in with an unknown username raises. |
| N4 | Private student profile (access control) | **Owner can view.** A student profile is viewable by its owner. |
| N5 | Private student profile (access control) | **Other user denied.** The same profile is **not** viewable by a different non-admin user (access is denied). |
| N6 | Private student profile (access control) | **Admin can view.** The profile is viewable by an admin/organizer. |
| N7 | Waitlist | **Waitlist add → listed.** An entry added to the waitlist then appears in the waitlist listing. |
| N8 | Volunteer management | **Volunteer add → listed.** A volunteer added to the system then appears among the listed volunteers. |
| N9 | Roles | **Role vocabulary.** The system distinguishes a **student** role from an **admin** role. |

## Dependency usage

> "admins can login and see everyone via the Django admin interface."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `django` | FAIL | FAIL | pass | FAIL |
