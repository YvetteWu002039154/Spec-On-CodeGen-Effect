# Behavioral contract — `student-management-using-django` **NL track**

## Description features

| Description feature |
|---|
| Admin: "Manage Course (Add…)" |
| Admin: "Manage Staff (Add…)" |
| Admin: "Manage Students (Add…)" |
| Admin: "Manage Subjects (Add…)" |
| Admin: "Manage Sessions (Add…)" |
| Staff: "Take/Update Students Attendance"; Student: "View Attendance" |
| Staff: "Add/Update Result"; Student: "View Result" |
| Staff & Student: "Apply for Leave" |
| Admin: "Review (Approve/Reject) Student/Staff Leave" |
| Send Feedback to HOD + Admin "Review and Reply … Feedback" |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Manage entities (Admin add-operations) | **Add course.** A created course carries the name it was given (asserted `== "Physics"`). |
| N2 | Manage entities (Admin add-operations) | **Add staff.** A staff member can be added and is then present in the system. |
| N3 | Manage entities (Admin add-operations) | **Add student.** A student can be added and is then present in the system. |
| N4 | Manage entities (Admin add-operations) | **Add subject.** A created subject carries its name (asserted `== "Algebra"`). |
| N5 | Manage entities (Admin add-operations) | **Add session.** A session can be created (the generation's own session-creation path is exercised). |
| N6 | Attendance & results (Staff operations, read back as Student) | **Take attendance.** Attendance recorded as present reads back as **present** (bool `True` / `"Present"` / a `PRESENT` enum member all normalize). |
| N7 | Attendance & results (Staff operations, read back as Student) | **Add result.** A recorded result exposes the marks entered (asserted the observed marks `== 80.0`). |
| N8 | Leave workflow | **Apply leave → pending.** A freshly applied leave is in the **pending** state (int `0` / `"Pending"` / `LeaveStatus.PENDING` all normalize to `"pending"`). |
| N9 | Leave workflow | **Review leave → approved.** An admin approving a pending leave moves it to the **approved** state (normalizes to `"approved"`). |
| N10 | Feedback workflow | **Reply to feedback.** An admin's reply to submitted feedback is stored on the feedback (asserted the stored reply `== "thanks"`). |

