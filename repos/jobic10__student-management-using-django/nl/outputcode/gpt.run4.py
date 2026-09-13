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
class StudentSummaryCharts:
    student_id: int
    subjects_count: int
    attendance_total: int
    attendance_present: int
    attendance_absent: int
    results_count: int
    leaves_total: int
    leaves_pending: int
    leaves_approved: int
    leaves_rejected: int
    feedback_total: int
    feedback_pending: int
    feedback_replied: int


@dataclass(frozen=True)
class StaffSummaryCharts:
    staff_id: int
    subjects_count: int
    students_count: int
    attendance_records_count: int
    results_count: int
    leaves_total: int
    leaves_pending: int
    leaves_approved: int
    leaves_rejected: int
    feedback_total: int
    feedback_pending: int
    feedback_replied: int


class User:
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        if user_id <= 0:
            raise ValidationError("user_id must be positive")
        if not name or not name.strip():
            raise ValidationError("name must be non-empty")
        self._id = user_id
        self._name = name.strip()
        self._role = role

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
    def __init__(self, user_id: int, name: str, course_id: int, session_id: int) -> None:
        super().__init__(user_id, name, Role.STUDENT)
        if course_id <= 0:
            raise ValidationError("course_id must be positive")
        if session_id <= 0:
            raise ValidationError("session_id must be positive")
        self._course_id = course_id
        self._session_id = session_id

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def session_id(self) -> int:
        return self._session_id

    def _set_course_id(self, course_id: int) -> None:
        if course_id <= 0:
            raise ValidationError("course_id must be positive")
        self._course_id = course_id

    def _set_session_id(self, session_id: int) -> None:
        if session_id <= 0:
            raise ValidationError("session_id must be positive")
        self._session_id = session_id


class Course:
    def __init__(self, course_id: int, name: str) -> None:
        if course_id <= 0:
            raise ValidationError("course_id must be positive")
        if not name or not name.strip():
            raise ValidationError("course name must be non-empty")
        self._id = course_id
        self._name = name.strip()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def update(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("course name must be non-empty")
        self._name = name.strip()


class Session:
    def __init__(self, session_id: int, name: str) -> None:
        if session_id <= 0:
            raise ValidationError("session_id must be positive")
        if not name or not name.strip():
            raise ValidationError("session name must be non-empty")
        self._id = session_id
        self._name = name.strip()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def update(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("session name must be non-empty")
        self._name = name.strip()


class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if subject_id <= 0:
            raise ValidationError("subject_id must be positive")
        if not name or not name.strip():
            raise ValidationError("subject name must be non-empty")
        if course_id <= 0:
            raise ValidationError("course_id must be positive")
        if staff_id <= 0:
            raise ValidationError("staff_id must be positive")
        self._id = subject_id
        self._name = name.strip()
        self._course_id = course_id
        self._staff_id = staff_id

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
            if not name or not name.strip():
                raise ValidationError("subject name must be non-empty")
            self._name = name.strip()
        if course_id is not None:
            if course_id <= 0:
                raise ValidationError("course_id must be positive")
            self._course_id = course_id
        if staff_id is not None:
            if staff_id <= 0:
                raise ValidationError("staff_id must be positive")
            self._staff_id = staff_id


class AttendanceStatus(Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceRecord:
    def __init__(self, record_id: int, student_id: int, subject_id: int, staff_id: int, on_date: date, status: AttendanceStatus) -> None:
        if record_id <= 0:
            raise ValidationError("record_id must be positive")
        if student_id <= 0:
            raise ValidationError("student_id must be positive")
        if subject_id <= 0:
            raise ValidationError("subject_id must be positive")
        if staff_id <= 0:
            raise ValidationError("staff_id must be positive")
        if not isinstance(on_date, date):
            raise ValidationError("on_date must be a date")
        self._id = record_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._staff_id = staff_id
        self._date = on_date
        self._status = status

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
    def staff_id(self) -> int:
        return self._staff_id

    @property
    def date(self) -> date:
        return self._date

    @property
    def status(self) -> AttendanceStatus:
        return self._status

    def update_status(self, status: AttendanceStatus) -> None:
        self._status = status


class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, staff_id: int, score: float) -> None:
        if result_id <= 0:
            raise ValidationError("result_id must be positive")
        if student_id <= 0:
            raise ValidationError("student_id must be positive")
        if subject_id <= 0:
            raise ValidationError("subject_id must be positive")
        if staff_id <= 0:
            raise ValidationError("staff_id must be positive")
        if not isinstance(score, (int, float)):
            raise ValidationError("score must be numeric")
        self._id = result_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._staff_id = staff_id
        self._score = float(score)

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
    def staff_id(self) -> int:
        return self._staff_id

    @property
    def score(self) -> float:
        return self._score

    def update_score(self, score: float) -> None:
        if not isinstance(score, (int, float)):
            raise ValidationError("score must be numeric")
        self._score = float(score)


class LeaveRequest:
    def __init__(self, leave_id: int, requester_role: Role, requester_id: int, from_date: date, to_date: date, reason: str) -> None:
        if leave_id <= 0:
            raise ValidationError("leave_id must be positive")
        if requester_id <= 0:
            raise ValidationError("requester_id must be positive")
        if requester_role not in (Role.STUDENT, Role.STAFF):
            raise ValidationError("requester_role must be student or staff")
        if not isinstance(from_date, date) or not isinstance(to_date, date):
            raise ValidationError("from_date/to_date must be date")
        if to_date < from_date:
            raise ValidationError("to_date must be >= from_date")
        if not reason or not reason.strip():
            raise ValidationError("reason must be non-empty")
        self._id = leave_id
        self._requester_role = requester_role
        self._requester_id = requester_id
        self._from_date = from_date
        self._to_date = to_date
        self._reason = reason.strip()
        self._status = LeaveStatus.PENDING
        self._reviewed_by_admin_id: Optional[int] = None
        self._reviewed_at: Optional[datetime] = None

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

    def approve(self, admin_id: int) -> None:
        if self._status != LeaveStatus.PENDING:
            raise ValidationError("leave request already reviewed")
        if admin_id <= 0:
            raise ValidationError("admin_id must be positive")
        self._status = LeaveStatus.APPROVED
        self._reviewed_by_admin_id = admin_id
        self._reviewed_at = datetime.utcnow()

    def reject(self, admin_id: int) -> None:
        if self._status != LeaveStatus.PENDING:
            raise ValidationError("leave request already reviewed")
        if admin_id <= 0:
            raise ValidationError("admin_id must be positive")
        self._status = LeaveStatus.REJECTED
        self._reviewed_by_admin_id = admin_id
        self._reviewed_at = datetime.utcnow()


class Feedback:
    def __init__(self, feedback_id: int, sender_role: Role, sender_id: int, message: str) -> None:
        if feedback_id <= 0:
            raise ValidationError("feedback_id must be positive")
        if sender_id <= 0:
            raise ValidationError("sender_id must be positive")
        if sender_role not in (Role.STUDENT, Role.STAFF):
            raise ValidationError("sender_role must be student or staff")
        if not message or not message.strip():
            raise ValidationError("message must be non-empty")
        self._id = feedback_id
        self._sender_role = sender_role
        self._sender_id = sender_id
        self._message = message.strip()
        self._status = FeedbackStatus.PENDING
        self._reply: Optional[str] = None
        self._replied_by_admin_id: Optional[int] = None
        self._replied_at: Optional[datetime] = None
        self._created_at: datetime = datetime.utcnow()

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
        if self._status != FeedbackStatus.PENDING:
            raise ValidationError("feedback already replied")
        if admin_id <= 0:
            raise ValidationError("admin_id must be positive")
        if not reply or not reply.strip():
            raise ValidationError("reply must be non-empty")
        self._reply = reply.strip()
        self._replied_by_admin_id = admin_id
        self._replied_at = datetime.utcnow()
        self._status = FeedbackStatus.REPLIED


class StudentManagementSystem:
    def __init__(self) -> None:
        self._admins: Dict[int, Admin] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}
        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}
        self._attendance: Dict[int, AttendanceRecord] = {}
        self._results: Dict[int, Result] = {}
        self._leaves: Dict[int, LeaveRequest] = {}
        self._feedback: Dict[int, Feedback] = {}

        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_leave_id = 1
        self._next_feedback_id = 1

    def _require_admin(self, actor: User) -> None:
        if actor.role != Role.ADMIN:
            raise PermissionError("admin permission required")

    def _require_staff(self, actor: User) -> None:
        if actor.role != Role.STAFF:
            raise PermissionError("staff permission required")

    def _require_student(self, actor: User) -> None:
        if actor.role != Role.STUDENT:
            raise PermissionError("student permission required")

    def _get_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(admin_id)
        if not admin:
            raise EntityNotFoundError("admin not found")
        return admin

    def _get_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(staff_id)
        if not staff:
            raise EntityNotFoundError("staff not found")
        return staff

    def _get_student(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if not student:
            raise EntityNotFoundError("student not found")
        return student

    def _get_course(self, course_id: int) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise EntityNotFoundError("course not found")
        return course

    def _get_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise EntityNotFoundError("subject not found")
        return subject

    def _get_session(self, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise EntityNotFoundError("session not found")
        return session

    def add_admin(self, admin_id: int, name: str) -> Admin:
        if admin_id in self._admins or admin_id in self._staff or admin_id in self._students:
            raise ValidationError("user_id already exists")
        admin = Admin(admin_id, name)
        self._admins[admin_id] = admin
        return admin

    def add_staff(self, actor: User, staff_id: int, name: str) -> Staff:
        self._require_admin(actor)
        if staff_id in self._admins or staff_id in self._staff or staff_id in self._students:
            raise ValidationError("user_id already exists")
        staff = Staff(staff_id, name)
        self._staff[staff_id] = staff
        return staff

    def update_staff(self, actor: User, staff_id: int, name: str) -> None:
        self._require_admin(actor)
        staff = self._get_staff(staff_id)
        if not name or not name.strip():
            raise ValidationError("name must be non-empty")
        staff._name = name.strip()

    def delete_staff(self, actor: User, staff_id: int) -> None:
        self._require_admin(actor)
        self._get_staff(staff_id)
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValidationError("cannot delete staff assigned to a subject")
        del self._staff[staff_id]

    def add_course(self, actor: User, course_id: int, name: str) -> Course:
        self._require_admin(actor)
        if course_id in self._courses:
            raise ValidationError("course_id already exists")
        course = Course(course_id, name)
        self._courses[course_id] = course
        return course

    def update_course(self, actor: User, course_id: int, name: str) -> None:
        self._require_admin(actor)
        course = self._get_course(course_id)
        course.update(name)

    def delete_course(self, actor: User, course_id: int) -> None:
        self._require_admin(actor)
        self._get_course(course_id)
        for student in self._students.values():
            if student.course_id == course_id:
                raise ValidationError("cannot delete course with enrolled students")
        for subject in self._subjects.values():
            if subject.course_id == course_id:
                raise ValidationError("cannot delete course with subjects")
        del self._courses[course_id]

    def add_session(self, actor: User, session_id: int, name: str) -> Session:
        self._require_admin(actor)
        if session_id in self._sessions:
            raise ValidationError("session_id already exists")
        session = Session(session_id, name)
        self._sessions[session_id] = session
        return session

    def update_session(self, actor: User, session_id: int, name: str) -> None:
        self._require_admin(actor)
        session = self._get_session(session_id)
        session.update(name)

    def delete_session(self, actor: User, session_id: int) -> None:
        self._require_admin(actor)
        self._get_session(session_id)
        for student in self._students.values():
            if student.session_id == session_id:
                raise ValidationError("cannot delete session with enrolled students")
        del self._sessions[session_id]

    def add_subject(self, actor: User, subject_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(actor)
        if subject_id in self._subjects:
            raise ValidationError("subject_id already exists")
        self._get_course(course_id)
        self._get_staff(staff_id)
        subject = Subject(subject_id, name, course_id, staff_id)
        self._subjects[subject_id] = subject
        return subject

    def update_subject(
        self,
        actor: User,
        subject_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        staff_id: Optional[int] = None,
    ) -> None:
        self._require_admin(actor)
        subject = self._get_subject(subject_id)
        if course_id is not None:
            self._get_course(course_id)
        if staff_id is not None:
            self._get_staff(staff_id)
        subject.update(name=name, course_id=course_id, staff_id=staff_id)

    def delete_subject(self, actor: User, subject_id: int) -> None:
        self._require_admin(actor)
        self._get_subject(subject_id)
        for rec in self._attendance.values():
            if rec.subject_id == subject_id:
                raise ValidationError("cannot delete subject with attendance records")
        for res in self._results.values():
            if res.subject_id == subject_id:
                raise ValidationError("cannot delete subject with results")
        del self._subjects[subject_id]

    def add_student(self, actor: User, student_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(actor)
        if student_id in self._admins or student_id in self._staff or student_id in self._students:
            raise ValidationError("user_id already exists")
        self._get_course(course_id)
        self._get_session(session_id)
        student = Student(student_id, name, course_id, session_id)
        self._students[student_id] = student
        return student

    def update_student(
        self,
        actor: User,
        student_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> None:
        self._require_admin(actor)
        student = self._get_student(student_id)
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("name must be non-empty")
            student._name = name.strip()
        if course_id is not None:
            self._get_course(course_id)
            student._set_course_id(course_id)
        if session_id is not None:
            self._get_session(session_id)
            student._set_session_id(session_id)

    def delete_student(self, actor: User, student_id: int) -> None:
        self._require_admin(actor)
        self._get_student(student_id)
        for rec in self._attendance.values():
            if rec.student_id == student_id:
                raise ValidationError("cannot delete student with attendance records")
        for res in self._results.values():
            if res.student_id == student_id:
                raise ValidationError("cannot delete student with results")
        for leave in self._leaves.values():
            if leave.requester_role == Role.STUDENT and leave.requester_id == student_id:
                raise ValidationError("cannot delete student with leave requests")
        for fb in self._feedback.values():
            if fb.sender_role == Role.STUDENT and fb.sender_id == student_id:
                raise ValidationError("cannot delete student with feedback")
        del self._students[student_id]

    def take_attendance(self, actor: User, subject_id: int, on_date: date, student_status: Dict[int, AttendanceStatus]) -> List[AttendanceRecord]:
        self._require_staff(actor)
        subject = self._get_subject(subject_id)
        if subject.staff_id != actor.id:
            raise PermissionError("staff not assigned to this subject")
        if not isinstance(on_date, date):
            raise ValidationError("on_date must be a date")
        if not student_status:
            raise ValidationError("student_status must be non-empty")

        created: List[AttendanceRecord] = []
        for student_id, status in student_status.items():
            student = self._get_student(student_id)
            if student.course_id != subject.course_id:
                raise ValidationError("student not in subject course")
            existing = self._find_attendance_record(student_id=student_id, subject_id=subject_id, on_date=on_date)
            if existing is not None:
                raise ValidationError("attendance already exists for student/subject/date")
            rec_id = self._next_attendance_id
            self._next_attendance_id += 1
            rec = AttendanceRecord(rec_id, student_id, subject_id, actor.id, on_date, status)
            self._attendance[rec_id] = rec
            created.append(rec)
        return created

    def update_attendance(self, actor: User, record_id: int, status: AttendanceStatus) -> None:
        self._require_staff(actor)
        rec = self._attendance.get(record_id)
        if not rec:
            raise EntityNotFoundError("attendance record not found")
        subject = self._get_subject(rec.subject_id)
        if subject.staff_id != actor.id:
            raise PermissionError("staff not assigned to this subject")
        rec.update_status(status)

    def view_student_attendance(self, actor: User, student_id: int) -> List[AttendanceRecord]:
        if actor.role == Role.STUDENT and actor.id != student_id:
            raise PermissionError("students can only view their own attendance")
        if actor.role == Role.STAFF:
            self._get_staff(actor.id)
        if actor.role == Role.ADMIN:
            self._get_admin(actor.id)
        self._get_student(student_id)
        return sorted([r for r in self._attendance.values() if r.student_id == student_id], key=lambda r: (r.date, r.subject_id, r.id))

    def add_or_update_result(self, actor: User, student_id: int, subject_id: int, score: float) -> Result:
        self._require_staff(actor)
        subject = self._get_subject(subject_id)
        if subject.staff_id != actor.id:
            raise PermissionError("staff not assigned to this subject")
        student = self._get_student(student_id)
        if student.course_id != subject.course_id:
            raise ValidationError("student not in subject course")

        existing = self._find_result(student_id=student_id, subject_id=subject_id)
        if existing is None:
            res_id = self._next_result_id
            self._next_result_id += 1
            res = Result(res_id, student_id, subject_id, actor.id, score)
            self._results[res_id] = res
            return res
        existing.update_score(score)
        return existing

    def view_student_results(self, actor: User, student_id: int) -> List[Result]:
        if actor.role == Role.STUDENT and actor.id != student_id:
            raise PermissionError("students can only view their own results")
        if actor.role == Role.STAFF:
            self._get_staff(actor.id)
        if actor.role == Role.ADMIN:
            self._get_admin(actor.id)
        self._get_student(student_id)
        return sorted([r for r in self._results.values() if r.student_id == student_id], key=lambda r: (r.subject_id, r.id))

    def apply_leave(self, actor: User, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        if actor.role not in (Role.STUDENT, Role.STAFF):
            raise PermissionError("only student or staff can apply for leave")
        if actor.role == Role.STUDENT:
            self._get_student(actor.id)
        else:
            self._get_staff(actor.id)
        leave_id = self._next_leave_id
        self._next_leave_id += 1
        leave = LeaveRequest(leave_id, actor.role, actor.id, from_date, to_date, reason)
        self._leaves[leave_id] = leave
        return leave

    def review_leave(self, actor: User, leave_id: int, approve: bool) -> None:
        self._require_admin(actor)
        leave = self._leaves.get(leave_id)
        if not leave:
            raise EntityNotFoundError("leave request not found")
        if approve:
            leave.approve(actor.id)
        else:
            leave.reject(actor.id)

    def list_leaves(self, actor: User) -> List[LeaveRequest]:
        if actor.role == Role.ADMIN:
            self._get_admin(actor.id)
            return sorted(self._leaves.values(), key=lambda l: (l.status.value, l.id))
        if actor.role == Role.STUDENT:
            self._get_student(actor.id)
            return sorted([l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == actor.id], key=lambda l: l.id)
        if actor.role == Role.STAFF:
            self._get_staff(actor.id)
            return sorted([l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == actor.id], key=lambda l: l.id)
        raise PermissionError("invalid role")

    def send_feedback_to_hod(self, actor: User, message: str) -> Feedback:
        if actor.role not in (Role.STUDENT, Role.STAFF):
            raise PermissionError("only student or staff can send feedback")
        if actor.role == Role.STUDENT:
            self._get_student(actor.id)
        else:
            self._get_staff(actor.id)
        feedback_id = self._next_feedback_id
        self._next_feedback_id += 1
        fb = Feedback(feedback_id, actor.role, actor.id, message)
        self._feedback[feedback_id] = fb
        return fb

    def review_and_reply_feedback(self, actor: User, feedback_id: int, reply: str) -> None:
        self._require_admin(actor)
        fb = self._feedback.get(feedback_id)
        if not fb:
            raise EntityNotFoundError("feedback not found")
        fb.reply_by_admin(actor.id, reply)

    def list_feedback(self, actor: User) -> List[Feedback]:
        if actor.role == Role.ADMIN:
            self._get_admin(actor.id)
            return sorted(self._feedback.values(), key=lambda f: (f.status.value, f.id))
        if actor.role == Role.STUDENT:
            self._get_student(actor.id)
            return sorted([f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == actor.id], key=lambda f: f.id)
        if actor.role == Role.STAFF:
            self._get_staff(actor.id)
            return sorted([f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == actor.id], key=lambda f: f.id)
        raise PermissionError("invalid role")

    def admin_summary_charts(self, actor: User) -> SummaryCharts:
        self._require_admin(actor)
        leaves_total = len(self._leaves)
        leaves_pending = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.REJECTED)

        feedback_total = len(self._feedback)
        feedback_pending = sum(1 for f in self._feedback.values() if f.status == FeedbackStatus.PENDING)
        feedback_replied = sum(1 for f in self._feedback.values() if f.status == FeedbackStatus.REPLIED)

        return SummaryCharts(
            students_count=len(self._students),
            staff_count=len(self._staff),
            courses_count=len(self._courses),
            subjects_count=len(self._subjects),
            sessions_count=len(self._sessions),
            attendance_records_count=len(self._attendance),
            results_count=len(self._results),
            leaves_total=leaves_total,
            leaves_pending=leaves_pending,
            leaves_approved=leaves_approved,
            leaves_rejected=leaves_rejected,
            feedback_total=feedback_total,
            feedback_pending=feedback_pending,
            feedback_replied=feedback_replied,
        )

    def staff_summary_charts(self, actor: User) -> StaffSummaryCharts:
        self._require_staff(actor)
        staff_id = actor.id
        subjects = [s for s in self._subjects.values() if s.staff_id == staff_id]
        subject_ids = {s.id for s in subjects}
        course_ids = {s.course_id for s in subjects}

        students_count = sum(1 for st in self._students.values() if st.course_id in course_ids) if course_ids else 0
        attendance_records_count = sum(1 for r in self._attendance.values() if r.staff_id == staff_id and r.subject_id in subject_ids)
        results_count = sum(1 for r in self._results.values() if r.staff_id == staff_id and r.subject_id in subject_ids)

        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id]
        leaves_total = len(leaves)
        leaves_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)

        feedback = [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id]
        feedback_total = len(feedback)
        feedback_pending = sum(1 for f in feedback if f.status == FeedbackStatus.PENDING)
        feedback_replied = sum(1 for f in feedback if f.status == FeedbackStatus.REPLIED)

        return StaffSummaryCharts(
            staff_id=staff_id,
            subjects_count=len(subjects),
            students_count=students_count,
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

    def student_summary_charts(self, actor: User) -> StudentSummaryCharts:
        self._require_student(actor)
        student = self._get_student(actor.id)
        subjects = [s for s in self._subjects.values() if s.course_id == student.course_id]
        subject_ids = {s.id for s in subjects}

        attendance = [r for r in self._attendance.values() if r.student_id == student.id and r.subject_id in subject_ids]
        attendance_total = len(attendance)
        attendance_present = sum(1 for r in attendance if r.status == AttendanceStatus.PRESENT)
        attendance_absent = sum(1 for r in attendance if r.status == AttendanceStatus.ABSENT)

        results = [r for r in self._results.values() if r.student_id == student.id and r.subject_id in subject_ids]
        results_count = len(results)

        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student.id]
        leaves_total = len(leaves)
        leaves_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)

        feedback = [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student.id]
        feedback_total = len(feedback)
        feedback_pending = sum(1 for f in feedback if f.status == FeedbackStatus.PENDING)
        feedback_replied = sum(1 for f in feedback if f.status == FeedbackStatus.REPLIED)

        return StudentSummaryCharts(
            student_id=student.id,
            subjects_count=len(subjects),
            attendance_total=attendance_total,
            attendance_present=attendance_present,
            attendance_absent=attendance_absent,
            results_count=results_count,
            leaves_total=leaves_total,
            leaves_pending=leaves_pending,
            leaves_approved=leaves_approved,
            leaves_rejected=leaves_rejected,
            feedback_total=feedback_total,
            feedback_pending=feedback_pending,
            feedback_replied=feedback_replied,
        )

    def _find_attendance_record(self, student_id: int, subject_id: int, on_date: date) -> Optional[AttendanceRecord]:
        for rec in self._attendance.values():
            if rec.student_id == student_id and rec.subject_id == subject_id and rec.date == on_date:
                return rec
        return None

    def _find_result(self, student_id: int, subject_id: int) -> Optional[Result]:
        for res in self._results.values():
            if res.student_id == student_id and res.subject_id == subject_id:
                return res
        return None

    def list_courses(self) -> List[Course]:
        return sorted(self._courses.values(), key=lambda c: c.id)

    def list_sessions(self) -> List[Session]:
        return sorted(self._sessions.values(), key=lambda s: s.id)

    def list_subjects(self) -> List[Subject]:
        return sorted(self._subjects.values(), key=lambda s: s.id)

    def list_students(self) -> List[Student]:
        return sorted(self._students.values(), key=lambda s: s.id)

    def list_staff(self) -> List[Staff]:
        return sorted(self._staff.values(), key=lambda s: s.id)

    def staff_subjects(self, actor: User) -> List[Subject]:
        self._require_staff(actor)
        return sorted([s for s in self._subjects.values() if s.staff_id == actor.id], key=lambda s: s.id)

    def student_subjects(self, actor: User) -> List[Subject]:
        self._require_student(actor)
        student = self._get_student(actor.id)
        return sorted([s for s in self._subjects.values() if s.course_id == student.course_id], key=lambda s: s.id)