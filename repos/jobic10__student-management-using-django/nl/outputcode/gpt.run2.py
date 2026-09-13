from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class Role(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


@dataclass(frozen=True)
class Summary:
    students_count: int
    staff_count: int
    courses_count: int
    subjects_count: int
    sessions_count: int
    leave_pending_count: int
    leave_approved_count: int
    leave_rejected_count: int
    feedback_unreplied_count: int
    feedback_replied_count: int


@dataclass(frozen=True)
class StaffSummary:
    staff_id: int
    subjects_count: int
    students_in_subjects_count: int
    leave_pending_count: int
    leave_approved_count: int
    leave_rejected_count: int
    feedback_sent_count: int


@dataclass(frozen=True)
class StudentSummary:
    student_id: int
    subjects_count: int
    attendance_present: int
    attendance_absent: int
    leave_pending_count: int
    leave_approved_count: int
    leave_rejected_count: int
    feedback_sent_count: int


class EntityNotFoundError(ValueError):
    pass


class PermissionError(ValueError):
    pass


class ValidationError(ValueError):
    pass


class User:
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        if user_id <= 0:
            raise ValidationError("user_id must be positive")
        if not name or not name.strip():
            raise ValidationError("name is required")
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
            raise ValidationError("course name is required")
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
            raise ValidationError("course name is required")
        self._name = name.strip()


class Session:
    def __init__(self, session_id: int, name: str) -> None:
        if session_id <= 0:
            raise ValidationError("session_id must be positive")
        if not name or not name.strip():
            raise ValidationError("session name is required")
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
            raise ValidationError("session name is required")
        self._name = name.strip()


class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if subject_id <= 0:
            raise ValidationError("subject_id must be positive")
        if not name or not name.strip():
            raise ValidationError("subject name is required")
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
                raise ValidationError("subject name is required")
            self._name = name.strip()
        if course_id is not None:
            if course_id <= 0:
                raise ValidationError("course_id must be positive")
            self._course_id = course_id
        if staff_id is not None:
            if staff_id <= 0:
                raise ValidationError("staff_id must be positive")
            self._staff_id = staff_id


class AttendanceRecord:
    def __init__(self, record_id: int, student_id: int, subject_id: int, on_date: date, status: AttendanceStatus, taken_by_staff_id: int) -> None:
        if record_id <= 0:
            raise ValidationError("record_id must be positive")
        if student_id <= 0:
            raise ValidationError("student_id must be positive")
        if subject_id <= 0:
            raise ValidationError("subject_id must be positive")
        if taken_by_staff_id <= 0:
            raise ValidationError("taken_by_staff_id must be positive")
        if not isinstance(on_date, date):
            raise ValidationError("on_date must be a date")
        self._id = record_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._date = on_date
        self._status = status
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
    def status(self) -> AttendanceStatus:
        return self._status

    @property
    def taken_by_staff_id(self) -> int:
        return self._taken_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_status(self, status: AttendanceStatus, updated_by_staff_id: int) -> None:
        if updated_by_staff_id <= 0:
            raise ValidationError("updated_by_staff_id must be positive")
        self._status = status
        self._taken_by_staff_id = updated_by_staff_id
        self._updated_at = datetime.utcnow()


class ResultRecord:
    def __init__(self, result_id: int, student_id: int, subject_id: int, score: float, updated_by_staff_id: int) -> None:
        if result_id <= 0:
            raise ValidationError("result_id must be positive")
        if student_id <= 0:
            raise ValidationError("student_id must be positive")
        if subject_id <= 0:
            raise ValidationError("subject_id must be positive")
        if updated_by_staff_id <= 0:
            raise ValidationError("updated_by_staff_id must be positive")
        if not isinstance(score, (int, float)):
            raise ValidationError("score must be numeric")
        self._id = result_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._score = float(score)
        self._updated_by_staff_id = updated_by_staff_id
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
    def score(self) -> float:
        return self._score

    @property
    def updated_by_staff_id(self) -> int:
        return self._updated_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_score(self, score: float, updated_by_staff_id: int) -> None:
        if updated_by_staff_id <= 0:
            raise ValidationError("updated_by_staff_id must be positive")
        if not isinstance(score, (int, float)):
            raise ValidationError("score must be numeric")
        self._score = float(score)
        self._updated_by_staff_id = updated_by_staff_id
        self._updated_at = datetime.utcnow()


class Feedback:
    def __init__(self, feedback_id: int, sender_role: Role, sender_id: int, message: str) -> None:
        if feedback_id <= 0:
            raise ValidationError("feedback_id must be positive")
        if sender_id <= 0:
            raise ValidationError("sender_id must be positive")
        if sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("sender_role must be staff or student")
        if not message or not message.strip():
            raise ValidationError("message is required")
        self._id = feedback_id
        self._sender_role = sender_role
        self._sender_id = sender_id
        self._message = message.strip()
        self._created_at = datetime.utcnow()
        self._reply: Optional[str] = None
        self._replied_at: Optional[datetime] = None
        self._replied_by_admin_id: Optional[int] = None

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
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def reply(self) -> Optional[str]:
        return self._reply

    @property
    def replied_at(self) -> Optional[datetime]:
        return self._replied_at

    @property
    def replied_by_admin_id(self) -> Optional[int]:
        return self._replied_by_admin_id

    def reply_by_admin(self, admin_id: int, reply: str) -> None:
        if admin_id <= 0:
            raise ValidationError("admin_id must be positive")
        if not reply or not reply.strip():
            raise ValidationError("reply is required")
        self._reply = reply.strip()
        self._replied_at = datetime.utcnow()
        self._replied_by_admin_id = admin_id

    def is_replied(self) -> bool:
        return self._reply is not None


class LeaveRequest:
    def __init__(self, leave_id: int, requester_role: Role, requester_id: int, from_date: date, to_date: date, reason: str) -> None:
        if leave_id <= 0:
            raise ValidationError("leave_id must be positive")
        if requester_id <= 0:
            raise ValidationError("requester_id must be positive")
        if requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("requester_role must be staff or student")
        if not isinstance(from_date, date) or not isinstance(to_date, date):
            raise ValidationError("from_date/to_date must be date")
        if to_date < from_date:
            raise ValidationError("to_date must be on or after from_date")
        if not reason or not reason.strip():
            raise ValidationError("reason is required")
        self._id = leave_id
        self._requester_role = requester_role
        self._requester_id = requester_id
        self._from_date = from_date
        self._to_date = to_date
        self._reason = reason.strip()
        self._status = LeaveStatus.PENDING
        self._created_at = datetime.utcnow()
        self._reviewed_at: Optional[datetime] = None
        self._reviewed_by_admin_id: Optional[int] = None

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
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def reviewed_at(self) -> Optional[datetime]:
        return self._reviewed_at

    @property
    def reviewed_by_admin_id(self) -> Optional[int]:
        return self._reviewed_by_admin_id

    def approve(self, admin_id: int) -> None:
        if admin_id <= 0:
            raise ValidationError("admin_id must be positive")
        self._status = LeaveStatus.APPROVED
        self._reviewed_at = datetime.utcnow()
        self._reviewed_by_admin_id = admin_id

    def reject(self, admin_id: int) -> None:
        if admin_id <= 0:
            raise ValidationError("admin_id must be positive")
        self._status = LeaveStatus.REJECTED
        self._reviewed_at = datetime.utcnow()
        self._reviewed_by_admin_id = admin_id


class StudentManagementSystem:
    def __init__(self) -> None:
        self._admins: Dict[int, Admin] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}
        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}

        self._attendance: Dict[int, AttendanceRecord] = {}
        self._attendance_index: Dict[Tuple[int, int, date], int] = {}

        self._results: Dict[int, ResultRecord] = {}
        self._results_index: Dict[Tuple[int, int], int] = {}

        self._feedback: Dict[int, Feedback] = {}
        self._leave: Dict[int, LeaveRequest] = {}

        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_feedback_id = 1
        self._next_leave_id = 1

    def _require_admin(self, admin_id: int) -> None:
        if admin_id not in self._admins:
            raise PermissionError("admin not found or not authorized")

    def _require_staff(self, staff_id: int) -> None:
        if staff_id not in self._staff:
            raise PermissionError("staff not found or not authorized")

    def _require_student(self, student_id: int) -> None:
        if student_id not in self._students:
            raise PermissionError("student not found or not authorized")

    def _get_subject(self, subject_id: int) -> Subject:
        subj = self._subjects.get(subject_id)
        if subj is None:
            raise EntityNotFoundError("subject not found")
        return subj

    def _get_student(self, student_id: int) -> Student:
        st = self._students.get(student_id)
        if st is None:
            raise EntityNotFoundError("student not found")
        return st

    def _get_staff(self, staff_id: int) -> Staff:
        sf = self._staff.get(staff_id)
        if sf is None:
            raise EntityNotFoundError("staff not found")
        return sf

    def _get_course(self, course_id: int) -> Course:
        c = self._courses.get(course_id)
        if c is None:
            raise EntityNotFoundError("course not found")
        return c

    def _get_session(self, session_id: int) -> Session:
        s = self._sessions.get(session_id)
        if s is None:
            raise EntityNotFoundError("session not found")
        return s

    def add_admin(self, admin_id: int, name: str) -> Admin:
        if admin_id in self._admins or admin_id in self._staff or admin_id in self._students:
            raise ValidationError("user_id already exists")
        admin = Admin(admin_id, name)
        self._admins[admin_id] = admin
        return admin

    def add_staff(self, admin_id: int, staff_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        if staff_id in self._admins or staff_id in self._staff or staff_id in self._students:
            raise ValidationError("user_id already exists")
        staff = Staff(staff_id, name)
        self._staff[staff_id] = staff
        return staff

    def update_staff(self, admin_id: int, staff_id: int, name: str) -> None:
        self._require_admin(admin_id)
        staff = self._get_staff(staff_id)
        if not name or not name.strip():
            raise ValidationError("name is required")
        staff._User__dict__ if False else None
        staff._name = name.strip()

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        if staff_id not in self._staff:
            raise EntityNotFoundError("staff not found")
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValidationError("cannot delete staff assigned to a subject")
        del self._staff[staff_id]

    def add_student(self, admin_id: int, student_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin_id)
        if student_id in self._admins or student_id in self._staff or student_id in self._students:
            raise ValidationError("user_id already exists")
        self._get_course(course_id)
        self._get_session(session_id)
        student = Student(student_id, name, course_id, session_id)
        self._students[student_id] = student
        return student

    def update_student(
        self,
        admin_id: int,
        student_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> None:
        self._require_admin(admin_id)
        student = self._get_student(student_id)
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("name is required")
            student._name = name.strip()
        if course_id is not None:
            self._get_course(course_id)
            student._set_course_id(course_id)
        if session_id is not None:
            self._get_session(session_id)
            student._set_session_id(session_id)

    def delete_student(self, admin_id: int, student_id: int) -> None:
        self._require_admin(admin_id)
        if student_id not in self._students:
            raise EntityNotFoundError("student not found")
        del self._students[student_id]

    def add_course(self, admin_id: int, course_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        if course_id in self._courses:
            raise ValidationError("course_id already exists")
        course = Course(course_id, name)
        self._courses[course_id] = course
        return course

    def update_course(self, admin_id: int, course_id: int, name: str) -> None:
        self._require_admin(admin_id)
        course = self._get_course(course_id)
        course.update(name)

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        if course_id not in self._courses:
            raise EntityNotFoundError("course not found")
        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValidationError("cannot delete course with subjects")
        for st in self._students.values():
            if st.course_id == course_id:
                raise ValidationError("cannot delete course with students")
        del self._courses[course_id]

    def add_session(self, admin_id: int, session_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        if session_id in self._sessions:
            raise ValidationError("session_id already exists")
        sess = Session(session_id, name)
        self._sessions[session_id] = sess
        return sess

    def update_session(self, admin_id: int, session_id: int, name: str) -> None:
        self._require_admin(admin_id)
        sess = self._get_session(session_id)
        sess.update(name)

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        if session_id not in self._sessions:
            raise EntityNotFoundError("session not found")
        for st in self._students.values():
            if st.session_id == session_id:
                raise ValidationError("cannot delete session with students")
        del self._sessions[session_id]

    def add_subject(self, admin_id: int, subject_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin_id)
        if subject_id in self._subjects:
            raise ValidationError("subject_id already exists")
        self._get_course(course_id)
        self._get_staff(staff_id)
        subj = Subject(subject_id, name, course_id, staff_id)
        self._subjects[subject_id] = subj
        return subj

    def update_subject(
        self,
        admin_id: int,
        subject_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        staff_id: Optional[int] = None,
    ) -> None:
        self._require_admin(admin_id)
        subj = self._get_subject(subject_id)
        if course_id is not None:
            self._get_course(course_id)
        if staff_id is not None:
            self._get_staff(staff_id)
        subj.update(name=name, course_id=course_id, staff_id=staff_id)

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        if subject_id not in self._subjects:
            raise EntityNotFoundError("subject not found")
        del self._subjects[subject_id]

    def take_or_update_attendance(
        self,
        staff_id: int,
        subject_id: int,
        on_date: date,
        entries: Dict[int, AttendanceStatus],
    ) -> List[AttendanceRecord]:
        self._require_staff(staff_id)
        subj = self._get_subject(subject_id)
        if subj.staff_id != staff_id:
            raise PermissionError("staff not assigned to this subject")
        if not isinstance(on_date, date):
            raise ValidationError("on_date must be a date")
        if not entries:
            raise ValidationError("entries required")

        updated: List[AttendanceRecord] = []
        for student_id, status in entries.items():
            student = self._get_student(student_id)
            if student.course_id != subj.course_id:
                raise ValidationError("student not in subject course")
            key = (student_id, subject_id, on_date)
            existing_id = self._attendance_index.get(key)
            if existing_id is None:
                rec_id = self._next_attendance_id
                self._next_attendance_id += 1
                rec = AttendanceRecord(rec_id, student_id, subject_id, on_date, status, staff_id)
                self._attendance[rec_id] = rec
                self._attendance_index[key] = rec_id
                updated.append(rec)
            else:
                rec = self._attendance[existing_id]
                rec.update_status(status, staff_id)
                updated.append(rec)
        return updated

    def view_student_attendance(self, requester_id: int, student_id: int) -> List[AttendanceRecord]:
        if requester_id in self._admins:
            pass
        elif requester_id in self._staff:
            pass
        elif requester_id in self._students:
            if requester_id != student_id:
                raise PermissionError("students can only view their own attendance")
        else:
            raise PermissionError("requester not authorized")

        self._get_student(student_id)
        return sorted(
            [r for r in self._attendance.values() if r.student_id == student_id],
            key=lambda r: (r.on_date, r.subject_id, r.id),
        )

    def add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, score: float) -> ResultRecord:
        self._require_staff(staff_id)
        subj = self._get_subject(subject_id)
        if subj.staff_id != staff_id:
            raise PermissionError("staff not assigned to this subject")
        student = self._get_student(student_id)
        if student.course_id != subj.course_id:
            raise ValidationError("student not in subject course")

        key = (student_id, subject_id)
        existing_id = self._results_index.get(key)
        if existing_id is None:
            res_id = self._next_result_id
            self._next_result_id += 1
            rec = ResultRecord(res_id, student_id, subject_id, score, staff_id)
            self._results[res_id] = rec
            self._results_index[key] = res_id
            return rec
        rec = self._results[existing_id]
        rec.update_score(score, staff_id)
        return rec

    def view_student_results(self, requester_id: int, student_id: int) -> List[ResultRecord]:
        if requester_id in self._admins:
            pass
        elif requester_id in self._staff:
            pass
        elif requester_id in self._students:
            if requester_id != student_id:
                raise PermissionError("students can only view their own results")
        else:
            raise PermissionError("requester not authorized")

        self._get_student(student_id)
        return sorted(
            [r for r in self._results.values() if r.student_id == student_id],
            key=lambda r: (r.subject_id, r.id),
        )

    def apply_leave(self, requester_role: Role, requester_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        if requester_role == Role.STAFF:
            self._require_staff(requester_id)
        elif requester_role == Role.STUDENT:
            self._require_student(requester_id)
        else:
            raise PermissionError("only staff or students can apply for leave")

        leave_id = self._next_leave_id
        self._next_leave_id += 1
        req = LeaveRequest(leave_id, requester_role, requester_id, from_date, to_date, reason)
        self._leave[leave_id] = req
        return req

    def review_leave(self, admin_id: int, leave_id: int, approve: bool) -> None:
        self._require_admin(admin_id)
        req = self._leave.get(leave_id)
        if req is None:
            raise EntityNotFoundError("leave request not found")
        if approve:
            req.approve(admin_id)
        else:
            req.reject(admin_id)

    def send_feedback_to_hod(self, sender_role: Role, sender_id: int, message: str) -> Feedback:
        if sender_role == Role.STAFF:
            self._require_staff(sender_id)
        elif sender_role == Role.STUDENT:
            self._require_student(sender_id)
        else:
            raise PermissionError("only staff or students can send feedback")

        fb_id = self._next_feedback_id
        self._next_feedback_id += 1
        fb = Feedback(fb_id, sender_role, sender_id, message)
        self._feedback[fb_id] = fb
        return fb

    def reply_feedback(self, admin_id: int, feedback_id: int, reply: str) -> None:
        self._require_admin(admin_id)
        fb = self._feedback.get(feedback_id)
        if fb is None:
            raise EntityNotFoundError("feedback not found")
        fb.reply_by_admin(admin_id, reply)

    def list_feedback(self, admin_id: int) -> List[Feedback]:
        self._require_admin(admin_id)
        return sorted(self._feedback.values(), key=lambda f: f.id)

    def list_leave_requests(self, admin_id: int) -> List[LeaveRequest]:
        self._require_admin(admin_id)
        return sorted(self._leave.values(), key=lambda l: l.id)

    def get_admin_summary(self, admin_id: int) -> Summary:
        self._require_admin(admin_id)
        leave_pending = sum(1 for l in self._leave.values() if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leave.values() if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leave.values() if l.status == LeaveStatus.REJECTED)
        feedback_unreplied = sum(1 for f in self._feedback.values() if not f.is_replied())
        feedback_replied = sum(1 for f in self._feedback.values() if f.is_replied())
        return Summary(
            students_count=len(self._students),
            staff_count=len(self._staff),
            courses_count=len(self._courses),
            subjects_count=len(self._subjects),
            sessions_count=len(self._sessions),
            leave_pending_count=leave_pending,
            leave_approved_count=leave_approved,
            leave_rejected_count=leave_rejected,
            feedback_unreplied_count=feedback_unreplied,
            feedback_replied_count=feedback_replied,
        )

    def get_staff_summary(self, staff_id: int) -> StaffSummary:
        self._require_staff(staff_id)
        subjects = [s for s in self._subjects.values() if s.staff_id == staff_id]
        subject_ids = {s.id for s in subjects}
        course_ids = {s.course_id for s in subjects}
        students_in_subjects: Set[int] = set()
        for st in self._students.values():
            if st.course_id in course_ids:
                students_in_subjects.add(st.id)

        leave_pending = sum(
            1 for l in self._leave.values()
            if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.PENDING
        )
        leave_approved = sum(
            1 for l in self._leave.values()
            if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.APPROVED
        )
        leave_rejected = sum(
            1 for l in self._leave.values()
            if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.REJECTED
        )
        feedback_sent = sum(
            1 for f in self._feedback.values()
            if f.sender_role == Role.STAFF and f.sender_id == staff_id
        )
        return StaffSummary(
            staff_id=staff_id,
            subjects_count=len(subject_ids),
            students_in_subjects_count=len(students_in_subjects),
            leave_pending_count=leave_pending,
            leave_approved_count=leave_approved,
            leave_rejected_count=leave_rejected,
            feedback_sent_count=feedback_sent,
        )

    def get_student_summary(self, student_id: int) -> StudentSummary:
        self._require_student(student_id)
        student = self._get_student(student_id)
        subjects = [s for s in self._subjects.values() if s.course_id == student.course_id]
        subject_ids = {s.id for s in subjects}

        present = sum(
            1 for a in self._attendance.values()
            if a.student_id == student_id and a.status == AttendanceStatus.PRESENT
        )
        absent = sum(
            1 for a in self._attendance.values()
            if a.student_id == student_id and a.status == AttendanceStatus.ABSENT
        )
        leave_pending = sum(
            1 for l in self._leave.values()
            if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.PENDING
        )
        leave_approved = sum(
            1 for l in self._leave.values()
            if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.APPROVED
        )
        leave_rejected = sum(
            1 for l in self._leave.values()
            if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.REJECTED
        )
        feedback_sent = sum(
            1 for f in self._feedback.values()
            if f.sender_role == Role.STUDENT and f.sender_id == student_id
        )
        return StudentSummary(
            student_id=student_id,
            subjects_count=len(subject_ids),
            attendance_present=present,
            attendance_absent=absent,
            leave_pending_count=leave_pending,
            leave_approved_count=leave_approved,
            leave_rejected_count=leave_rejected,
            feedback_sent_count=feedback_sent,
        )