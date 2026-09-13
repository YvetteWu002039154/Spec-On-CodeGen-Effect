from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class Role(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class LeaveStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FeedbackStatus(Enum):
    PENDING = "pending"
    REPLIED = "replied"


class EntityNotFoundError(ValueError):
    pass


class ValidationError(ValueError):
    pass


class PermissionError(ValueError):
    pass


@dataclass(frozen=True)
class SummaryCharts:
    students_count: int
    staff_count: int
    courses_count: int
    subjects_count: int
    sessions_count: int
    attendance_records_count: int
    results_count: int
    leaves_total: int
    leaves_pending: int
    leaves_approved: int
    leaves_rejected: int
    feedback_total: int
    feedback_pending: int
    feedback_replied: int


@dataclass(frozen=True)
class AttendanceSummary:
    total_classes: int
    present: int
    absent: int

    @property
    def percentage(self) -> float:
        if self.total_classes == 0:
            return 0.0
        return (self.present / self.total_classes) * 100.0


@dataclass(frozen=True)
class ResultSummary:
    subjects_count: int
    average_score: float


class User:
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        self._id = user_id
        self._name = name.strip()
        self._role = role
        if not self._name:
            raise ValidationError("User name cannot be empty.")

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def role(self) -> Role:
        return self._role


class Admin(User):
    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id, name, Role.ADMIN)


class Staff(User):
    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id, name, Role.STAFF)


class Student(User):
    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id, name, Role.STUDENT)


class Course:
    def __init__(self, course_id: int, name: str) -> None:
        self._id = course_id
        self._name = name.strip()
        if not self._name:
            raise ValidationError("Course name cannot be empty.")

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def update(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Course name cannot be empty.")
        self._name = name


class Session:
    def __init__(self, session_id: int, name: str) -> None:
        self._id = session_id
        self._name = name.strip()
        if not self._name:
            raise ValidationError("Session name cannot be empty.")

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def update(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Session name cannot be empty.")
        self._name = name


class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        self._id = subject_id
        self._name = name.strip()
        self._course_id = course_id
        self._staff_id = staff_id
        if not self._name:
            raise ValidationError("Subject name cannot be empty.")

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def staff_id(self) -> int:
        return self._staff_id

    def update(self, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("Subject name cannot be empty.")
            self._name = name
        if course_id is not None:
            self._course_id = course_id
        if staff_id is not None:
            self._staff_id = staff_id


class Enrollment:
    def __init__(self, student_id: int, course_id: int, session_id: int) -> None:
        self._student_id = student_id
        self._course_id = course_id
        self._session_id = session_id

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def session_id(self) -> int:
        return self._session_id

    def update(self, course_id: Optional[int] = None, session_id: Optional[int] = None) -> None:
        if course_id is not None:
            self._course_id = course_id
        if session_id is not None:
            self._session_id = session_id


class AttendanceRecord:
    def __init__(self, record_id: int, student_id: int, subject_id: int, on_date: date, present: bool, taken_by_staff_id: int) -> None:
        self._id = record_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._date = on_date
        self._present = present
        self._taken_by_staff_id = taken_by_staff_id
        self._updated_at = datetime.utcnow()

    @property
    def id(self) -> int:
        return self._id

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def subject_id(self) -> int:
        return self._subject_id

    @property
    def on_date(self) -> date:
        return self._date

    @property
    def present(self) -> bool:
        return self._present

    @property
    def taken_by_staff_id(self) -> int:
        return self._taken_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(self, present: bool, taken_by_staff_id: int) -> None:
        self._present = present
        self._taken_by_staff_id = taken_by_staff_id
        self._updated_at = datetime.utcnow()


class ResultRecord:
    def __init__(self, result_id: int, student_id: int, subject_id: int, score: float, updated_by_staff_id: int) -> None:
        self._id = result_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._score = float(score)
        self._updated_by_staff_id = updated_by_staff_id
        self._updated_at = datetime.utcnow()
        if self._score < 0.0 or self._score > 100.0:
            raise ValidationError("Score must be between 0 and 100.")

    @property
    def id(self) -> int:
        return self._id

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def subject_id(self) -> int:
        return self._subject_id

    @property
    def score(self) -> float:
        return self._score

    @property
    def updated_by_staff_id(self) -> int:
        return self._updated_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(self, score: float, updated_by_staff_id: int) -> None:
        score = float(score)
        if score < 0.0 or score > 100.0:
            raise ValidationError("Score must be between 0 and 100.")
        self._score = score
        self._updated_by_staff_id = updated_by_staff_id
        self._updated_at = datetime.utcnow()


class LeaveRequest:
    def __init__(self, leave_id: int, requester_role: Role, requester_id: int, from_date: date, to_date: date, reason: str) -> None:
        if requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("Leave requester must be staff or student.")
        if to_date < from_date:
            raise ValidationError("Leave to_date cannot be earlier than from_date.")
        reason = reason.strip()
        if not reason:
            raise ValidationError("Leave reason cannot be empty.")
        self._id = leave_id
        self._requester_role = requester_role
        self._requester_id = requester_id
        self._from_date = from_date
        self._to_date = to_date
        self._reason = reason
        self._status = LeaveStatus.PENDING
        self._reviewed_by_admin_id: Optional[int] = None
        self._reviewed_at: Optional[datetime] = None
        self._review_note: Optional[str] = None
        self._created_at = datetime.utcnow()

    @property
    def id(self) -> int:
        return self._id

    @property
    def requester_role(self) -> Role:
        return self._requester_role

    @property
    def requester_id(self) -> int:
        return self._requester_id

    @property
    def from_date(self) -> date:
        return self._from_date

    @property
    def to_date(self) -> date:
        return self._to_date

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def status(self) -> LeaveStatus:
        return self._status

    @property
    def reviewed_by_admin_id(self) -> Optional[int]:
        return self._reviewed_by_admin_id

    @property
    def reviewed_at(self) -> Optional[datetime]:
        return self._reviewed_at

    @property
    def review_note(self) -> Optional[str]:
        return self._review_note

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def review(self, admin_id: int, approve: bool, note: Optional[str] = None) -> None:
        if self._status != LeaveStatus.PENDING:
            raise ValidationError("Leave request already reviewed.")
        self._status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        self._reviewed_by_admin_id = admin_id
        self._reviewed_at = datetime.utcnow()
        if note is not None:
            note = note.strip()
            self._review_note = note if note else None


class Feedback:
    def __init__(self, feedback_id: int, sender_role: Role, sender_id: int, message: str) -> None:
        if sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("Feedback sender must be staff or student.")
        message = message.strip()
        if not message:
            raise ValidationError("Feedback message cannot be empty.")
        self._id = feedback_id
        self._sender_role = sender_role
        self._sender_id = sender_id
        self._message = message
        self._status = FeedbackStatus.PENDING
        self._reply: Optional[str] = None
        self._replied_by_admin_id: Optional[int] = None
        self._replied_at: Optional[datetime] = None
        self._created_at = datetime.utcnow()

    @property
    def id(self) -> int:
        return self._id

    @property
    def sender_role(self) -> Role:
        return self._sender_role

    @property
    def sender_id(self) -> int:
        return self._sender_id

    @property
    def message(self) -> str:
        return self._message

    @property
    def status(self) -> FeedbackStatus:
        return self._status

    @property
    def reply(self) -> Optional[str]:
        return self._reply

    @property
    def replied_by_admin_id(self) -> Optional[int]:
        return self._replied_by_admin_id

    @property
    def replied_at(self) -> Optional[datetime]:
        return self._replied_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def reply_by_admin(self, admin_id: int, reply: str) -> None:
        if self._status == FeedbackStatus.REPLIED:
            raise ValidationError("Feedback already replied.")
        reply = reply.strip()
        if not reply:
            raise ValidationError("Reply cannot be empty.")
        self._reply = reply
        self._status = FeedbackStatus.REPLIED
        self._replied_by_admin_id = admin_id
        self._replied_at = datetime.utcnow()


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_user_id = 1
        self._next_course_id = 1
        self._next_subject_id = 1
        self._next_session_id = 1
        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_leave_id = 1
        self._next_feedback_id = 1

        self._admins: Dict[int, Admin] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}

        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}

        self._enrollments: Dict[int, Enrollment] = {}

        self._attendance: Dict[int, AttendanceRecord] = {}
        self._attendance_index: Dict[Tuple[int, int, date], int] = {}

        self._results: Dict[int, ResultRecord] = {}
        self._results_index: Dict[Tuple[int, int], int] = {}

        self._leaves: Dict[int, LeaveRequest] = {}
        self._feedback: Dict[int, Feedback] = {}

    def _require_role(self, user: User, role: Role) -> None:
        if user.role != role:
            raise PermissionError(f"Operation requires role {role.value}.")

    def _get_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(admin_id)
        if not admin:
            raise EntityNotFoundError("Admin not found.")
        return admin

    def _get_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(staff_id)
        if not staff:
            raise EntityNotFoundError("Staff not found.")
        return staff

    def _get_student(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if not student:
            raise EntityNotFoundError("Student not found.")
        return student

    def _get_course(self, course_id: int) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise EntityNotFoundError("Course not found.")
        return course

    def _get_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise EntityNotFoundError("Subject not found.")
        return subject

    def _get_session(self, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise EntityNotFoundError("Session not found.")
        return session

    def _ensure_student_enrolled_in_subject_course(self, student_id: int, subject_id: int) -> None:
        enrollment = self._enrollments.get(student_id)
        if not enrollment:
            raise ValidationError("Student is not enrolled in any course/session.")
        subject = self._get_subject(subject_id)
        if subject.course_id != enrollment.course_id:
            raise ValidationError("Subject does not belong to student's course.")

    def _ensure_staff_teaches_subject(self, staff_id: int, subject_id: int) -> None:
        subject = self._get_subject(subject_id)
        if subject.staff_id != staff_id:
            raise PermissionError("Staff is not assigned to this subject.")

    def create_admin(self, name: str) -> Admin:
        admin = Admin(self._next_user_id, name)
        self._admins[admin.id] = admin
        self._next_user_id += 1
        return admin

    def create_staff(self, admin: Admin, name: str) -> Staff:
        self._require_role(admin, Role.ADMIN)
        staff = Staff(self._next_user_id, name)
        self._staff[staff.id] = staff
        self._next_user_id += 1
        return staff

    def update_staff(self, admin: Admin, staff_id: int, name: str) -> None:
        self._require_role(admin, Role.ADMIN)
        staff = self._get_staff(staff_id)
        name = name.strip()
        if not name:
            raise ValidationError("Staff name cannot be empty.")
        staff._name = name  # type: ignore[attr-defined]

    def delete_staff(self, admin: Admin, staff_id: int) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_staff(staff_id)
        for subject in self._subjects.values():
            if subject.staff_id == staff_id:
                raise ValidationError("Cannot delete staff assigned to a subject.")
        del self._staff[staff_id]

    def create_student(self, admin: Admin, name: str, course_id: int, session_id: int) -> Student:
        self._require_role(admin, Role.ADMIN)
        self._get_course(course_id)
        self._get_session(session_id)
        student = Student(self._next_user_id, name)
        self._students[student.id] = student
        self._enrollments[student.id] = Enrollment(student.id, course_id, session_id)
        self._next_user_id += 1
        return student

    def update_student(self, admin: Admin, student_id: int, name: Optional[str] = None, course_id: Optional[int] = None, session_id: Optional[int] = None) -> None:
        self._require_role(admin, Role.ADMIN)
        student = self._get_student(student_id)
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("Student name cannot be empty.")
            student._name = name  # type: ignore[attr-defined]
        if course_id is not None:
            self._get_course(course_id)
        if session_id is not None:
            self._get_session(session_id)
        if course_id is not None or session_id is not None:
            enrollment = self._enrollments.get(student_id)
            if not enrollment:
                raise EntityNotFoundError("Enrollment not found.")
            enrollment.update(course_id=course_id, session_id=session_id)

    def delete_student(self, admin: Admin, student_id: int) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_student(student_id)
        self._students.pop(student_id, None)
        self._enrollments.pop(student_id, None)

    def create_course(self, admin: Admin, name: str) -> Course:
        self._require_role(admin, Role.ADMIN)
        course = Course(self._next_course_id, name)
        self._courses[course.id] = course
        self._next_course_id += 1
        return course

    def update_course(self, admin: Admin, course_id: int, name: str) -> None:
        self._require_role(admin, Role.ADMIN)
        course = self._get_course(course_id)
        course.update(name)

    def delete_course(self, admin: Admin, course_id: int) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_course(course_id)
        for subject in self._subjects.values():
            if subject.course_id == course_id:
                raise ValidationError("Cannot delete course with subjects.")
        for enrollment in self._enrollments.values():
            if enrollment.course_id == course_id:
                raise ValidationError("Cannot delete course with enrolled students.")
        del self._courses[course_id]

    def create_session(self, admin: Admin, name: str) -> Session:
        self._require_role(admin, Role.ADMIN)
        session = Session(self._next_session_id, name)
        self._sessions[session.id] = session
        self._next_session_id += 1
        return session

    def update_session(self, admin: Admin, session_id: int, name: str) -> None:
        self._require_role(admin, Role.ADMIN)
        session = self._get_session(session_id)
        session.update(name)

    def delete_session(self, admin: Admin, session_id: int) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_session(session_id)
        for enrollment in self._enrollments.values():
            if enrollment.session_id == session_id:
                raise ValidationError("Cannot delete session with enrolled students.")
        del self._sessions[session_id]

    def create_subject(self, admin: Admin, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_role(admin, Role.ADMIN)
        self._get_course(course_id)
        self._get_staff(staff_id)
        subject = Subject(self._next_subject_id, name, course_id, staff_id)
        self._subjects[subject.id] = subject
        self._next_subject_id += 1
        return subject

    def update_subject(self, admin: Admin, subject_id: int, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        self._require_role(admin, Role.ADMIN)
        subject = self._get_subject(subject_id)
        if course_id is not None:
            self._get_course(course_id)
        if staff_id is not None:
            self._get_staff(staff_id)
        subject.update(name=name, course_id=course_id, staff_id=staff_id)

    def delete_subject(self, admin: Admin, subject_id: int) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_subject(subject_id)
        del self._subjects[subject_id]

    def take_or_update_attendance(self, staff: Staff, student_id: int, subject_id: int, on_date: date, present: bool) -> AttendanceRecord:
        self._require_role(staff, Role.STAFF)
        self._get_student(student_id)
        self._ensure_staff_teaches_subject(staff.id, subject_id)
        self._ensure_student_enrolled_in_subject_course(student_id, subject_id)

        key = (student_id, subject_id, on_date)
        existing_id = self._attendance_index.get(key)
        if existing_id is not None:
            record = self._attendance[existing_id]
            record.update(present=present, taken_by_staff_id=staff.id)
            return record

        record = AttendanceRecord(self._next_attendance_id, student_id, subject_id, on_date, present, staff.id)
        self._attendance[record.id] = record
        self._attendance_index[key] = record.id
        self._next_attendance_id += 1
        return record

    def add_or_update_result(self, staff: Staff, student_id: int, subject_id: int, score: float) -> ResultRecord:
        self._require_role(staff, Role.STAFF)
        self._get_student(student_id)
        self._ensure_staff_teaches_subject(staff.id, subject_id)
        self._ensure_student_enrolled_in_subject_course(student_id, subject_id)

        key = (student_id, subject_id)
        existing_id = self._results_index.get(key)
        if existing_id is not None:
            record = self._results[existing_id]
            record.update(score=score, updated_by_staff_id=staff.id)
            return record

        record = ResultRecord(self._next_result_id, student_id, subject_id, score, staff.id)
        self._results[record.id] = record
        self._results_index[key] = record.id
        self._next_result_id += 1
        return record

    def apply_leave(self, requester: User, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        if requester.role not in (Role.STAFF, Role.STUDENT):
            raise PermissionError("Only staff or students can apply for leave.")
        if requester.role == Role.STAFF:
            self._get_staff(requester.id)
        else:
            self._get_student(requester.id)

        leave = LeaveRequest(self._next_leave_id, requester.role, requester.id, from_date, to_date, reason)
        self._leaves[leave.id] = leave
        self._next_leave_id += 1
        return leave

    def review_leave(self, admin: Admin, leave_id: int, approve: bool, note: Optional[str] = None) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_admin(admin.id)
        leave = self._leaves.get(leave_id)
        if not leave:
            raise EntityNotFoundError("Leave request not found.")
        leave.review(admin_id=admin.id, approve=approve, note=note)

    def send_feedback_to_hod(self, sender: User, message: str) -> Feedback:
        if sender.role not in (Role.STAFF, Role.STUDENT):
            raise PermissionError("Only staff or students can send feedback.")
        if sender.role == Role.STAFF:
            self._get_staff(sender.id)
        else:
            self._get_student(sender.id)

        fb = Feedback(self._next_feedback_id, sender.role, sender.id, message)
        self._feedback[fb.id] = fb
        self._next_feedback_id += 1
        return fb

    def reply_feedback(self, admin: Admin, feedback_id: int, reply: str) -> None:
        self._require_role(admin, Role.ADMIN)
        self._get_admin(admin.id)
        fb = self._feedback.get(feedback_id)
        if not fb:
            raise EntityNotFoundError("Feedback not found.")
        fb.reply_by_admin(admin_id=admin.id, reply=reply)

    def view_student_attendance(self, viewer: User, student_id: int, subject_id: Optional[int] = None) -> List[AttendanceRecord]:
        if viewer.role == Role.ADMIN:
            self._get_admin(viewer.id)
        elif viewer.role == Role.STAFF:
            self._get_staff(viewer.id)
        elif viewer.role == Role.STUDENT:
            if viewer.id != student_id:
                raise PermissionError("Students can only view their own attendance.")
            self._get_student(viewer.id)
        else:
            raise PermissionError("Invalid role.")

        self._get_student(student_id)
        if subject_id is not None:
            self._get_subject(subject_id)

        records = [r for r in self._attendance.values() if r.student_id == student_id and (subject_id is None or r.subject_id == subject_id)]
        records.sort(key=lambda r: (r.on_date, r.subject_id, r.id))
        return records

    def view_student_result(self, viewer: User, student_id: int) -> List[ResultRecord]:
        if viewer.role == Role.ADMIN:
            self._get_admin(viewer.id)
        elif viewer.role == Role.STAFF:
            self._get_staff(viewer.id)
        elif viewer.role == Role.STUDENT:
            if viewer.id != student_id:
                raise PermissionError("Students can only view their own results.")
            self._get_student(viewer.id)
        else:
            raise PermissionError("Invalid role.")

        self._get_student(student_id)
        records = [r for r in self._results.values() if r.student_id == student_id]
        records.sort(key=lambda r: (r.subject_id, r.id))
        return records

    def list_leaves(self, viewer: User, status: Optional[LeaveStatus] = None) -> List[LeaveRequest]:
        if viewer.role == Role.ADMIN:
            self._get_admin(viewer.id)
            leaves = list(self._leaves.values())
        elif viewer.role == Role.STAFF:
            self._get_staff(viewer.id)
            leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == viewer.id]
        elif viewer.role == Role.STUDENT:
            self._get_student(viewer.id)
            leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == viewer.id]
        else:
            raise PermissionError("Invalid role.")

        if status is not None:
            leaves = [l for l in leaves if l.status == status]
        leaves.sort(key=lambda l: (l.created_at, l.id))
        return leaves

    def list_feedback(self, viewer: User, status: Optional[FeedbackStatus] = None) -> List[Feedback]:
        if viewer.role == Role.ADMIN:
            self._get_admin(viewer.id)
            items = list(self._feedback.values())
        elif viewer.role == Role.STAFF:
            self._get_staff(viewer.id)
            items = [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == viewer.id]
        elif viewer.role == Role.STUDENT:
            self._get_student(viewer.id)
            items = [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == viewer.id]
        else:
            raise PermissionError("Invalid role.")

        if status is not None:
            items = [f for f in items if f.status == status]
        items.sort(key=lambda f: (f.created_at, f.id))
        return items

    def get_summary_charts(self, viewer: User) -> SummaryCharts:
        if viewer.role == Role.ADMIN:
            self._get_admin(viewer.id)
            attendance_count = len(self._attendance)
            results_count = len(self._results)
            leaves = list(self._leaves.values())
            feedback = list(self._feedback.values())
            return self._build_summary(
                students_count=len(self._students),
                staff_count=len(self._staff),
                courses_count=len(self._courses),
                subjects_count=len(self._subjects),
                sessions_count=len(self._sessions),
                attendance_records_count=attendance_count,
                results_count=results_count,
                leaves=leaves,
                feedback=feedback,
            )

        if viewer.role == Role.STAFF:
            self._get_staff(viewer.id)
            staff_subject_ids = {s.id for s in self._subjects.values() if s.staff_id == viewer.id}
            attendance_count = sum(1 for r in self._attendance.values() if r.subject_id in staff_subject_ids)
            results_count = sum(1 for r in self._results.values() if r.subject_id in staff_subject_ids)
            leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == viewer.id]
            feedback = [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == viewer.id]
            return self._build_summary(
                students_count=len(self._students),
                staff_count=len(self._staff),
                courses_count=len(self._courses),
                subjects_count=len(staff_subject_ids),
                sessions_count=len(self._sessions),
                attendance_records_count=attendance_count,
                results_count=results_count,
                leaves=leaves,
                feedback=feedback,
            )

        if viewer.role == Role.STUDENT:
            self._get_student(viewer.id)
            attendance_count = sum(1 for r in self._attendance.values() if r.student_id == viewer.id)
            results_count = sum(1 for r in self._results.values() if r.student_id == viewer.id)
            leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == viewer.id]
            feedback = [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == viewer.id]
            return self._build_summary(
                students_count=1,
                staff_count=len(self._staff),
                courses_count=len(self._courses),
                subjects_count=self._count_subjects_for_student(viewer.id),
                sessions_count=len(self._sessions),
                attendance_records_count=attendance_count,
                results_count=results_count,
                leaves=leaves,
                feedback=feedback,
            )

        raise PermissionError("Invalid role.")

    def _count_subjects_for_student(self, student_id: int) -> int:
        enrollment = self._enrollments.get(student_id)
        if not enrollment:
            return 0
        return sum(1 for s in self._subjects.values() if s.course_id == enrollment.course_id)

    def _build_summary(
        self,
        students_count: int,
        staff_count: int,
        courses_count: int,
        subjects_count: int,
        sessions_count: int,
        attendance_records_count: int,
        results_count: int,
        leaves: List[LeaveRequest],
        feedback: List[Feedback],
    ) -> SummaryCharts:
        leaves_total = len(leaves)
        leaves_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)

        feedback_total = len(feedback)
        feedback_pending = sum(1 for f in feedback if f.status == FeedbackStatus.PENDING)
        feedback_replied = sum(1 for f in feedback if f.status == FeedbackStatus.REPLIED)

        return SummaryCharts(
            students_count=students_count,
            staff_count=staff_count,
            courses_count=courses_count,
            subjects_count=subjects_count,
            sessions_count=sessions_count,
            attendance_records_count=attendance_records_count,
            results_count=results_count,
            leaves_total=leaves_total,
            leaves_pending=leaves_pending,
            leaves_approved=leaves_approved,
            leaves_rejected=leaves_rejected,
            feedback_total=feedback_total,
            feedback_pending=feedback_pending,
            feedback_replied=feedback_replied,
        )

    def get_attendance_summary_for_student(self, student: Student, subject_id: Optional[int] = None) -> AttendanceSummary:
        self._require_role(student, Role.STUDENT)
        self._get_student(student.id)
        if subject_id is not None:
            self._get_subject(subject_id)

        records = [r for r in self._attendance.values() if r.student_id == student.id and (subject_id is None or r.subject_id == subject_id)]
        total = len(records)
        present = sum(1 for r in records if r.present)
        absent = total - present
        return AttendanceSummary(total_classes=total, present=present, absent=absent)

    def get_result_summary_for_student(self, student: Student) -> ResultSummary:
        self._require_role(student, Role.STUDENT)
        self._get_student(student.id)
        records = [r for r in self._results.values() if r.student_id == student.id]
        if not records:
            return ResultSummary(subjects_count=0, average_score=0.0)
        avg = sum(r.score for r in records) / len(records)
        return ResultSummary(subjects_count=len(records), average_score=avg)

    def get_staff_subjects(self, staff: Staff) -> List[Subject]:
        self._require_role(staff, Role.STAFF)
        self._get_staff(staff.id)
        subjects = [s for s in self._subjects.values() if s.staff_id == staff.id]
        subjects.sort(key=lambda s: (s.course_id, s.id))
        return subjects

    def get_student_subjects(self, student: Student) -> List[Subject]:
        self._require_role(student, Role.STUDENT)
        self._get_student(student.id)
        enrollment = self._enrollments.get(student.id)
        if not enrollment:
            return []
        subjects = [s for s in self._subjects.values() if s.course_id == enrollment.course_id]
        subjects.sort(key=lambda s: (s.id,))
        return subjects

    def get_students_for_staff(self, staff: Staff) -> List[Student]:
        self._require_role(staff, Role.STAFF)
        self._get_staff(staff.id)
        course_ids: Set[int] = {s.course_id for s in self._subjects.values() if s.staff_id == staff.id}
        student_ids = [sid for sid, e in self._enrollments.items() if e.course_id in course_ids]
        students = [self._students[sid] for sid in student_ids if sid in self._students]
        students.sort(key=lambda st: st.id)
        return students

    def get_enrollment(self, viewer: User, student_id: int) -> Enrollment:
        if viewer.role == Role.ADMIN:
            self._get_admin(viewer.id)
        elif viewer.role == Role.STAFF:
            self._get_staff(viewer.id)
        elif viewer.role == Role.STUDENT:
            if viewer.id != student_id:
                raise PermissionError("Students can only view their own enrollment.")
            self._get_student(viewer.id)
        else:
            raise PermissionError("Invalid role.")
        enrollment = self._enrollments.get(student_id)
        if not enrollment:
            raise EntityNotFoundError("Enrollment not found.")
        return enrollment