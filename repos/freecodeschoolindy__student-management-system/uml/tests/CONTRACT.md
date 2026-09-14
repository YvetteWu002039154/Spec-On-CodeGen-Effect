# Structural contract — `student-management-system` **UML track**

Reference: origin repo `student-management-system-main/apps/**/models.py` — the
Django model layer the class diagram was extracted from (loaded under a minimal
Django config).

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the origin models) and
grounded in that origin code. A class diagram records *structure*, not runtime
behavior, so the pinned facts are the things the diagram actually draws:

1. **Inheritance links** — `Child --|> AbstractTableMeta`.
2. **Composition / association** — `User --* CustomUserManager : objects`;
   `UserProfile --> User : user`.
3. **Methods under a class** — under `CustomUserManager`, `User`,
   `WaitlistEntry`, `Volunteer`.
4. **Declared attributes** — `User.is_admin/is_staff/is_student`;
   `UserProfile.LEVELS : tuple`.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `WaitlistEntry --|> AbstractTableMeta` (L105) | `apps/waitlist/models.py`: `class WaitlistEntry(AbstractTableMeta, models.Model)` |
| U2 | `Certificate --|> AbstractTableMeta` (L100) | `apps/certificates/models.py`: `class Certificate(AbstractTableMeta, models.Model)` |
| U3 | `User --* CustomUserManager : objects` (L106) | `apps/users/models.py`: `objects = CustomUserManager()` |
| U4 | `UserProfile --> User : user` (L78) | `apps/users/models.py`: `user = models.OneToOneField(User, …)` |
| U5 | `CustomUserManager` methods (L18–20) | `create_user(self, email, password=None)`, `create_superuser(self, email, password=None)` |
| U6 | `User` methods (L62–63) | `has_perm(self, perm, obj=None)`, `has_module_perms(self, app_label)` |
| U7 | `WaitlistEntry.full_name()` (L98) | `apps/waitlist/models.py`: `def full_name(self)` (method) |
| U8 | `Volunteer.full_name` (L83) | `apps/volunteers/models.py`: `@property def full_name` |
| U9 | `User.is_admin/is_staff/is_student` (L57–60) | `is_admin`/`is_staff`/`is_student = models.BooleanField(...)` |
| U10 | `UserProfile.LEVELS : tuple` (L66) | `LEVELS = ((1,'Level One'),(2,'Level Two'))` |

## Notes for the adapter

- Attribute presence (`U9`) is checked across class attributes, class/`__init__`
  annotations, and — for Django models — `_meta` fields, so both Django-based and
  plain-Python generations are covered by one reflection path.
  A class that declares **none** of the named attributes → **failure** (the
  diagram names them and the generation does not expose them).
- A generation that is a **Django models module** with concrete models but no
  `app_label` cannot be imported standalone, so every fact FAILS for it.
