# Behavioral contract — `student-management-using-django` **NL track**

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
