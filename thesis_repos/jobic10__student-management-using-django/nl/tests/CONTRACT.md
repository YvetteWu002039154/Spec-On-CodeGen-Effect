# Behavioral contract — `student-management-using-django` **NL track**

Reference for grounding: origin repo `student-management-using-django-main/` —
the Django app `main_app/models.py` (and the feature list it implements).

This contract is derived by comparing the **NL description**
(`nl/input/description.txt`, a feature list of what Admin / Staff / Student can
do) with the **origin code**, then pinning the observable behaviors every
reasonable implementation of that description would expose.

Behaviors are asserted on **observable capability and effect**. The four NL
generations diverge sharply in architecture (a single facade; an admin-id facade
returning ids; module-level global stores; and role objects taking the system as
an argument), so each generation is driven by its **own explicit driver**
(`adapter.py`) that names the concrete classes and methods it uses, with one
method per behavior (Nn) in N order. A capability a generation does not expose is
a behavioral **FAILURE** — the driver drives the real API and the resulting empty
result / `AttributeError` / wrong value fails the test's assert. This suite does
**not** skip or mark N/A.

There is **no reference subject** in the NL track (the description, not a single
canonical module, is the source of truth); the four generations are the only
subjects.

## Description feature → origin grounding

| Description feature | Origin evidence (`main_app/models.py`) |
|---|---|
| Admin: "Manage Course (Add…)" | `Course.name` (CharField) |
| Admin: "Manage Staff (Add…)" | `Staff` model (OneToOne `admin`, FK `course`) |
| Admin: "Manage Students (Add…)" | `Student` model (OneToOne `admin`, FK `course`/`session`) |
| Admin: "Manage Subjects (Add…)" | `Subject.name` (FK `course`, FK `staff`) |
| Admin: "Manage Sessions (Add…)" | `Session` (start_year / end_year) |
| Staff: "Take/Update Students Attendance"; Student: "View Attendance" | `AttendanceReport.status` (BooleanField — present/absent) |
| Staff: "Add/Update Result"; Student: "View Result" | `StudentResult` (`test` / `exam` FloatField) |
| Staff & Student: "Apply for Leave" | `LeaveReportStudent.status` (SmallIntegerField, **default 0 = pending**) |
| Admin: "Review (Approve/Reject) Student/Staff Leave" | `LeaveReport*.status` transitions 0→1 (approved) |
| Send Feedback to HOD + Admin "Review and Reply … Feedback" | `FeedbackStudent.feedback` + `FeedbackStudent.reply` |

## Behaviors pinned

### Manage entities (Admin add-operations)
- **N1. Add course.** A created course carries the name it was given
  (asserted `== "Physics"`).
- **N2. Add staff.** A staff member can be added and is then present in the
  system.
- **N3. Add student.** A student can be added and is then present in the system.
- **N4. Add subject.** A created subject carries its name (asserted
  `== "Algebra"`).
- **N5. Add session.** A session can be created (the generation's own
  session-creation path is exercised).

### Attendance & results (Staff operations, read back as Student)
- **N6. Take attendance.** Attendance recorded as present reads back as
  **present** (bool `True` / `"Present"` / a `PRESENT` enum member all normalize).
- **N7. Add result.** A recorded result exposes the marks entered (asserted the
  observed marks `== 80.0`).

### Leave workflow
- **N8. Apply leave → pending.** A freshly applied leave is in the **pending**
  state (int `0` / `"Pending"` / `LeaveStatus.PENDING` all normalize to
  `"pending"`).
- **N9. Review leave → approved.** An admin approving a pending leave moves it to
  the **approved** state (normalizes to `"approved"`).

### Feedback workflow
- **N10. Reply to feedback.** An admin's reply to submitted feedback is stored on
  the feedback (asserted the stored reply `== "thanks"`).

## Normalization notes for the adapter

- **Explicit per-generation drivers.** Each generation has one driver in
  `adapter.py` that names its concrete API: `claude` → `StudentManagementSystem`
  facade (`add_course`, `add_staff`, `take_attendance` …); `gpt` →
  `StudentManagementSystem` create-methods gated on `admin_id` returning ids;
  `deepseek` → module-level `courses`/`users` stores driven by `Admin`/`Staff`/
  `Student` role objects; `gemini` → `Admin`/`Staff`/`Student` role methods that
  take the `StudentManagementSystem` as their first argument.
- **Status vocabulary** is normalized to lowercase words: integers via
  `{0:pending, 1:approved, 2/-1:rejected}`, enums via their value/name, strings
  lowercased. Attendance "present" is likewise normalized across bool / string /
  enum.
- Entities created through id-returning facades (`gpt`) are read back out of the
  facade's private stores by id **and class name** (per-entity id counters mean
  the same integer can appear in several stores).
- For `deepseek`, whose `add_student`/`add_staff` create plain `Person` objects,
  the adapter constructs explicit `Staff`/`Student` role instances to drive the
  attendance / result / leave / feedback behaviors those roles own.

## Portability

Each NL generation is a self-contained plain-Python program (stdlib only), so no
Django and no stubbing is needed to load and drive it.
