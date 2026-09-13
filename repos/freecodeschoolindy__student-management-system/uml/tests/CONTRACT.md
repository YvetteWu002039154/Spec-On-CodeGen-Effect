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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `WaitlistEntry --|> AbstractTableMeta` (L105) | `apps/waitlist/models.py`: `class WaitlistEntry(AbstractTableMeta, models.Model)` |
| `Certificate --|> AbstractTableMeta` (L100) | `apps/certificates/models.py`: `class Certificate(AbstractTableMeta, models.Model)` |
| `User --* CustomUserManager : objects` (L106) | `apps/users/models.py`: `objects = CustomUserManager()` |
| `UserProfile --> User : user` (L78) | `apps/users/models.py`: `user = models.OneToOneField(User, …)` |
| `CustomUserManager` methods (L18–20) | `create_user(self, email, password=None)`, `create_superuser(self, email, password=None)` |
| `User` methods (L62–63) | `has_perm(self, perm, obj=None)`, `has_module_perms(self, app_label)` |
| `WaitlistEntry.full_name()` (L98) | `apps/waitlist/models.py`: `def full_name(self)` (method) |
| `Volunteer.full_name` (L83) | `apps/volunteers/models.py`: `@property def full_name` |
| `User.is_admin/is_staff/is_student` (L57–60) | `is_admin`/`is_staff`/`is_student = models.BooleanField(...)` |
| `UserProfile.LEVELS : tuple` (L66) | `LEVELS = ((1,'Level One'),(2,'Level Two'))` |

## Facts pinned

### Inheritance links (`--|>`)
- **U1. `WaitlistEntry --|> AbstractTableMeta`.**
- **U2. `Certificate --|> AbstractTableMeta`.**

### Composition / association (`--*`, `-->`)
- **U3. `User --* CustomUserManager`.** `User.objects` is an instance of a
  `CustomUserManager` (asserted on the manager's class name).
- **U4. `UserProfile --> User`.** `UserProfile.user`'s type reference is `User`
  (Django related model, class annotation, or `__init__` parameter annotation).

### Methods under a class
- **U5. Manager methods.** `CustomUserManager` defines `create_user` and
  `create_superuser`.
- **U6. User permission methods.** `User` defines `has_perm` and
  `has_module_perms`.
- **U7. `WaitlistEntry.full_name`.** Present (a method in the diagram).
- **U8. `Volunteer.full_name`.** Present (a property in the diagram).

### Declared attributes
- **U9. User role flags.** `User` declares `is_admin`, `is_staff`, and
  `is_student` (as class fields, annotations, or `__init__` parameters).
- **U10. `UserProfile.LEVELS`.** Declared as a **tuple**-typed class attribute.
  (The diagram declares `LEVELS : tuple` with no values, so only the type is
  pinned, not the specific level pairs.)

## Harness

The pinned surface is the **structure the class diagram draws** — inheritance
links (`--|>`), a composition/association (`--*`, `-->`), the methods under
`CustomUserManager`/`User`/`WaitlistEntry`/`Volunteer`, and declared attributes —
asserted by **reflection on the loaded classes** (subclass relations, manager
type, method names, declared attributes), never by executing behavior. A class or
attribute a generation does not define is a **FAILURE**, as is a present-but-wrong
link/attribute. This track does not skip / mark N/A. Subjects are the 4 UML generations; the origin
model modules the diagram was extracted from ground the facts above but are not
themselves a test subject.

## Portability

The origin's own `config.settings` needs PostgreSQL, env vars, and a large
third-party stack, so a *minimal* Django config that registers only the diagram's
model apps (utils, users, certificates, waitlist, volunteers) with corrected app
labels is set up once — enough for a Django-based generation to build its field
descriptors. The three plain-Python generations need only the standard library.

## Notes for the adapter

- Attribute presence (`U9`) is checked across class attributes, class/`__init__`
  annotations, and — for Django models — `_meta` fields, so both Django-based and
  plain-Python generations are covered by one reflection path.
  A class that declares **none** of the named attributes → **failure** (the
  diagram names them and the generation does not expose them).
- A generation that is a **Django models module** with concrete models but no
  `app_label` cannot be imported standalone, so every fact FAILS for it.
