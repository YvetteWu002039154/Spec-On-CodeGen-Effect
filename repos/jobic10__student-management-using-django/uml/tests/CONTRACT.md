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

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `CustomUserManager` methods `create_user`, `create_superuser` | `class CustomUserManager(UserManager)` L11–30 |
| U2 | `CustomUserManager --* CustomUser : objects` | `objects = CustomUserManager()` L57 |
| U3 | `CustomUser : USER_TYPE, GENDER, USERNAME_FIELD, REQUIRED_FIELDS` | L42–56 |
| U4 | `Student : admin, course, session` (FK/O2O) | `admin=OneToOneField(CustomUser)`, `course=FK(Course)`, `session=FK(Session)` L77–80 |
| U5 | `Staff : admin, course` | `admin=OneToOneField(CustomUser)`, `course=FK(Course)` L86–88 |
| U6 | `Subject : course, staff` | `course=FK(Course)`, `staff=FK(Staff)` L94–97 |
| U7 | `Attendance : session, subject` | `session=FK(Session)`, `subject=FK(Subject)` L105–108 |
| U8 | `AttendanceReport : attendance, student, status` | `attendance=FK(Attendance)`, `student=FK(Student)`, `status=BooleanField` L113–116 |
| U9 | `StudentResult : student, subject, test, exam` | `student=FK(Student)`, `subject=FK(Subject)`, `test/exam=FloatField` L169–172 |
| U10 | `Session : start_year, end_year` | `start_year=DateField()`, `end_year=DateField()` L33–35 |