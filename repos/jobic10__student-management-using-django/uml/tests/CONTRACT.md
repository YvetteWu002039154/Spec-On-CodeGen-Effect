# Structural contract — `student-management-using-django` **UML track**

Reference: origin repo `student-management-using-django-main/main_app/models.py`
— the single module the class diagram was extracted from.

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the Django models) and
grounded in that origin code. A class diagram records *structure*, not runtime
behavior, so the pinned facts are the three things this diagram actually draws:

1. **Methods under a class** — only `CustomUserManager` carries any
   (`create_user`, `create_superuser`).
2. The one explicit relationship line, the composition
   `CustomUserManager --* CustomUser : objects`.
3. **Attributes/fields under each class** — pyreverse renders each as
   `name : FieldType`; several are typed associations to *other model classes*
   (a `ForeignKey`/`OneToOneField` to Course, Staff, Session, …).

## Diagram fact → origin grounding

| Diagram fact | Origin evidence (`main_app/models.py`) |
|---|---|
| `CustomUserManager` methods `create_user`, `create_superuser` | `class CustomUserManager(UserManager)` L11–30 |
| `CustomUserManager --* CustomUser : objects` | `objects = CustomUserManager()` L57 |
| `CustomUser : USER_TYPE, GENDER, USERNAME_FIELD, REQUIRED_FIELDS` | L42–56 |
| `Student : admin, course, session` (FK/O2O) | `admin=OneToOneField(CustomUser)`, `course=FK(Course)`, `session=FK(Session)` L77–80 |
| `Staff : admin, course` | `admin=OneToOneField(CustomUser)`, `course=FK(Course)` L86–88 |
| `Subject : course, staff` | `course=FK(Course)`, `staff=FK(Staff)` L94–97 |
| `Attendance : session, subject` | `session=FK(Session)`, `subject=FK(Subject)` L105–108 |
| `AttendanceReport : attendance, student, status` | `attendance=FK(Attendance)`, `student=FK(Student)`, `status=BooleanField` L113–116 |
| `StudentResult : student, subject, test, exam` | `student=FK(Student)`, `subject=FK(Subject)`, `test/exam=FloatField` L169–172 |
| `Session : start_year, end_year` | `start_year=DateField()`, `end_year=DateField()` L33–35 |

## Facts pinned

### Methods under a class
- **U1. Manager methods.** `CustomUserManager` defines `create_user` and
  `create_superuser`.

### Composition link (`--*`) and CustomUser vocabulary
- **U2. `CustomUserManager --* CustomUser`.** `CustomUser.objects` is (an
  instance of) `CustomUserManager` — the diagram's one explicit relationship.
- **U3. Auth vocabulary.** `CustomUser` declares the class-level attributes
  `USER_TYPE`, `GENDER`, `USERNAME_FIELD`, `REQUIRED_FIELDS`.

### Association links (`--> : attr`) — checked on the target type
- **U4. Student.** `Student.admin → CustomUser`, `Student.course → Course`,
  `Student.session → Session`.
- **U5. Staff.** `Staff.admin → CustomUser`, `Staff.course → Course`.
- **U6. Subject.** `Subject.course → Course`, `Subject.staff → Staff`.
- **U7. Attendance.** `Attendance.session → Session`,
  `Attendance.subject → Subject`.
- **U8. AttendanceReport.** `AttendanceReport.attendance → Attendance`,
  `AttendanceReport.student → Student`, plus a `status` field.
- **U9. StudentResult.** `StudentResult.student → Student`,
  `StudentResult.subject → Subject`, plus `test` and `exam` mark fields.
- **U10. Session span.** `Session` carries `start_year` and `end_year`.

## Harness

The pinned surface is the **structure the class diagram draws** — the
`CustomUserManager` methods, the one composition link
(`CustomUserManager --* CustomUser`), and the attributes/associations under each
model — asserted by **reflection on the loaded classes** (method names, the
`objects` manager, class-level fields/annotations/properties, and association
target types), never by executing behavior. A pinned method must be a **real (non-stub) implementation**: a body that is only `pass` / `...` / `return None` / `raise NotImplementedError` is judged statically (from source, never executed) as *not* implemented and fails the method set. Because the same structure appears in
three shapes across the generations (Django `_meta` fields; `__init__`-typed
dataclass-style; `@property` getters), the adapter resolves each uniformly. A
class or attribute a generation does not define is a **FAILURE**, as is an
association whose target type is wrong. This track does not skip / mark N/A. Subjects are
the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin
`main_app/models.py` the diagram was extracted from grounds the facts above but is
not itself a test subject.

## Portability

The reference and two generations (`claude`, `deepseek`) are Django model
modules; they load under a minimal in-memory Django config, each registered as a
one-off app so its models get a valid `app_label`. The other two (`gpt`, `gemini`)
are plain-Python and load unchanged.

## Resolution notes for the adapter

- **Association target type** is resolved, in order, from: a Django field's
  `related_model`; a `@property` getter's return annotation; an `__init__`
  parameter annotation of the same name; or a class-level annotation — dropping
  field-wrapper (`ForeignKey`, …) and typing (`Optional`, …) noise. If the
  attribute is absent → **failure**; if present but no target type is recoverable
  → **failure**; if a target type is recovered but is the wrong class → **failure**.
- **Attribute presence** counts a class attribute, an annotation anywhere in the
  MRO, or a Django `_meta` field — so Django models, annotation-only classes,
  and property-based classes all resolve.
- **`objects` manager** is matched by `isinstance` / class-name / subclass so a
  Django-wrapped manager still counts.
