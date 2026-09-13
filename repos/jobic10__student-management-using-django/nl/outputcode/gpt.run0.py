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


class FeedbackStatus(str, Enum):
    OPEN = "open"
    REPLIED = "replied"


@dataclass(frozen=True)
class SummaryCharts:
    students_count: int
    staff_count: int
    courses_count: int
    subjects_count: int
    sessions_count: int
    attendance_records_count: int
    results_count: int
    leave_total: int
    leave_pending: int
    leave_approved: int
    leave_rejected: int
    feedback_total: int
    feedback_open: int
    feedback_replied: int


class User:
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        if not name or not name.strip():
            raise ValueError("name must be non-empty")
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
    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id, name, Role.STUDENT)


class Course:
    def __init__(self, course_id: int, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("course name must be non-empty")
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
            raise ValueError("course name must be non-empty")
        self._name = name.strip()


class Session:
    def __init__(self, session_id: int, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("session name must be non-empty")
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
            raise ValueError("session name must be non-empty")
        self._name = name.strip()


class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if not name or not name.strip():
            raise ValueError("subject name must be non-empty")
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
                raise ValueError("subject name must be non-empty")
            self._name = name.strip()
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


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceRecord:
    def __init__(self, record_id: int, student_id: int, subject_id: int, on_date: date, status: AttendanceStatus, taken_by_staff_id: int) -> None:
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
    def date(self) -> date:
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
        self._status = status
        self._taken_by_staff_id = updated_by_staff_id
        self._updated_at = datetime.utcnow()


class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, marks: float, added_by_staff_id: int) -> None:
        if marks < 0:
            raise ValueError("marks must be >= 0")
        self._id = result_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._marks = float(marks)
        self._added_by_staff_id = added_by_staff_id
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
    def marks(self) -> float:
        return self._marks

    @property
    def added_by_staff_id(self) -> int:
        return self._added_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_marks(self, marks: float, updated_by_staff_id: int) -> None:
        if marks < 0:
            raise ValueError("marks must be >= 0")
        self._marks = float(marks)
        self._added_by_staff_id = updated_by_staff_id
        self._updated_at = datetime.utcnow()


class LeaveRequest:
    def __init__(self, leave_id: int, requester_role: Role, requester_id: int, from_date: date, to_date: date, reason: str) -> None:
        if requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValueError("leave requester must be staff or student")
        if to_date < from_date:
            raise ValueError("to_date must be >= from_date")
        if not reason or not reason.strip():
            raise ValueError("reason must be non-empty")
        self._id = leave_id
        self._requester_role = requester_role
        self._requester_id = requester_id
        self._from_date = from_date
        self._to_date = to_date
        self._reason = reason.strip()
        self._status = LeaveStatus.PENDING
        self._reviewed_by_admin_id: Optional[int] = None
        self._review_note: Optional[str] = None
        self._created_at = datetime.utcnow()
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
    def review_note(self) -> Optional[str]:
        return self._review_note

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def reviewed_at(self) -> Optional[datetime]:
        return self._reviewed_at

    def review(self, admin_id: int, approve: bool, note: Optional[str] = None) -> None:
        if self._status != LeaveStatus.PENDING:
            raise ValueError("leave request already reviewed")
        self._status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        self._reviewed_by_admin_id = admin_id
        self._review_note = note.strip() if note is not None and note.strip() else None
        self._reviewed_at = datetime.utcnow()


class Feedback:
    def __init__(self, feedback_id: int, sender_role: Role, sender_id: int, message: str) -> None:
        if sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValueError("feedback sender must be staff or student")
        if not message or not message.strip():
            raise ValueError("message must be non-empty")
        self._id = feedback_id
        self._sender_role = sender_role
        self._sender_id = sender_id
        self._message = message.strip()
        self._status = FeedbackStatus.OPEN
        self._reply: Optional[str] = None
        self._replied_by_admin_id: Optional[int] = None
        self._created_at = datetime.utcnow()
        self._replied_at: Optional[datetime] = None

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
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def replied_at(self) -> Optional[datetime]:
        return self._replied_at

    def reply_by_admin(self, admin_id: int, reply: str) -> None:
        if not reply or not reply.strip():
            raise ValueError("reply must be non-empty")
        self._reply = reply.strip()
        self._replied_by_admin_id = admin_id
        self._status = FeedbackStatus.REPLIED
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

        self._results: Dict[int, Result] = {}
        self._results_index: Dict[Tuple[int, int], int] = {}

        self._leaves: Dict[int, LeaveRequest] = {}
        self._feedback: Dict[int, Feedback] = {}

    def _new_user_id(self) -> int:
        uid = self._next_user_id
        self._next_user_id += 1
        return uid

    def _new_course_id(self) -> int:
        cid = self._next_course_id
        self._next_course_id += 1
        return cid

    def _new_subject_id(self) -> int:
        sid = self._next_subject_id
        self._next_subject_id += 1
        return sid

    def _new_session_id(self) -> int:
        sid = self._next_session_id
        self._next_session_id += 1
        return sid

    def _new_attendance_id(self) -> int:
        aid = self._next_attendance_id
        self._next_attendance_id += 1
        return aid

    def _new_result_id(self) -> int:
        rid = self._next_result_id
        self._next_result_id += 1
        return rid

    def _new_leave_id(self) -> int:
        lid = self._next_leave_id
        self._next_leave_id += 1
        return lid

    def _new_feedback_id(self) -> int:
        fid = self._next_feedback_id
        self._next_feedback_id += 1
        return fid

    def _require_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(admin_id)
        if admin is None:
            raise KeyError("admin not found")
        return admin

    def _require_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(staff_id)
        if staff is None:
            raise KeyError("staff not found")
        return staff

    def _require_student(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if student is None:
            raise KeyError("student not found")
        return student

    def _require_course(self, course_id: int) -> Course:
        course = self._courses.get(course_id)
        if course is None:
            raise KeyError("course not found")
        return course

    def _require_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(subject_id)
        if subject is None:
            raise KeyError("subject not found")
        return subject

    def _require_session(self, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("session not found")
        return session

    def _require_enrollment(self, student_id: int) -> Enrollment:
        enr = self._enrollments.get(student_id)
        if enr is None:
            raise KeyError("student not enrolled")
        return enr

    def _subject_belongs_to_student_course(self, student_id: int, subject_id: int) -> bool:
        enr = self._require_enrollment(student_id)
        subj = self._require_subject(subject_id)
        return subj.course_id == enr.course_id

    def _staff_teaches_subject(self, staff_id: int, subject_id: int) -> bool:
        subj = self._require_subject(subject_id)
        return subj.staff_id == staff_id

    def create_admin(self, name: str) -> int:
        admin_id = self._new_user_id()
        self._admins[admin_id] = Admin(admin_id, name)
        return admin_id

    def create_staff(self, admin_id: int, name: str) -> int:
        self._require_admin(admin_id)
        staff_id = self._new_user_id()
        self._staff[staff_id] = Staff(staff_id, name)
        return staff_id

    def update_staff(self, admin_id: int, staff_id: int, name: str) -> None:
        self._require_admin(admin_id)
        staff = self._require_staff(staff_id)
        if not name or not name.strip():
            raise ValueError("name must be non-empty")
        staff._name = name.strip()

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        self._require_staff(staff_id)
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValueError("cannot delete staff assigned to a subject")
        del self._staff[staff_id]

    def create_student(self, admin_id: int, name: str, course_id: int, session_id: int) -> int:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_session(session_id)
        student_id = self._new_user_id()
        self._students[student_id] = Student(student_id, name)
        self._enrollments[student_id] = Enrollment(student_id, course_id, session_id)
        return student_id

    def update_student(self, admin_id: int, student_id: int, name: Optional[str] = None, course_id: Optional[int] = None, session_id: Optional[int] = None) -> None:
        self._require_admin(admin_id)
        student = self._require_student(student_id)
        if name is not None:
            if not name or not name.strip():
                raise ValueError("name must be non-empty")
            student._name = name.strip()
        if course_id is not None:
            self._require_course(course_id)
        if session_id is not None:
            self._require_session(session_id)
        if course_id is not None or session_id is not None:
            enr = self._require_enrollment(student_id)
            enr.update(course_id=course_id, session_id=session_id)

    def delete_student(self, admin_id: int, student_id: int) -> None:
        self._require_admin(admin_id)
        self._require_student(student_id)

        to_delete_attendance = [rid for rid, rec in self._attendance.items() if rec.student_id == student_id]
        for rid in to_delete_attendance:
            rec = self._attendance[rid]
            self._attendance_index.pop((rec.student_id, rec.subject_id, rec.date), None)
            del self._attendance[rid]

        to_delete_results = [rid for rid, res in self._results.items() if res.student_id == student_id]
        for rid in to_delete_results:
            res = self._results[rid]
            self._results_index.pop((res.student_id, res.subject_id), None)
            del self._results[rid]

        to_delete_leaves = [lid for lid, lr in self._leaves.items() if lr.requester_role == Role.STUDENT and lr.requester_id == student_id]
        for lid in to_delete_leaves:
            del self._leaves[lid]

        to_delete_feedback = [fid for fid, fb in self._feedback.items() if fb.sender_role == Role.STUDENT and fb.sender_id == student_id]
        for fid in to_delete_feedback:
            del self._feedback[fid]

        self._enrollments.pop(student_id, None)
        del self._students[student_id]

    def create_course(self, admin_id: int, name: str) -> int:
        self._require_admin(admin_id)
        course_id = self._new_course_id()
        self._courses[course_id] = Course(course_id, name)
        return course_id

    def update_course(self, admin_id: int, course_id: int, name: str) -> None:
        self._require_admin(admin_id)
        course = self._require_course(course_id)
        course.update(name)

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        self._require_course(course_id)
        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValueError("cannot delete course with subjects")
        for enr in self._enrollments.values():
            if enr.course_id == course_id:
                raise ValueError("cannot delete course with enrolled students")
        del self._courses[course_id]

    def create_session(self, admin_id: int, name: str) -> int:
        self._require_admin(admin_id)
        session_id = self._new_session_id()
        self._sessions[session_id] = Session(session_id, name)
        return session_id

    def update_session(self, admin_id: int, session_id: int, name: str) -> None:
        self._require_admin(admin_id)
        session = self._require_session(session_id)
        session.update(name)

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        self._require_session(session_id)
        for enr in self._enrollments.values():
            if enr.session_id == session_id:
                raise ValueError("cannot delete session with enrolled students")
        del self._sessions[session_id]

    def create_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> int:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_staff(staff_id)
        subject_id = self._new_subject_id()
        self._subjects[subject_id] = Subject(subject_id, name, course_id, staff_id)
        return subject_id

    def update_subject(self, admin_id: int, subject_id: int, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        self._require_admin(admin_id)
        subj = self._require_subject(subject_id)
        if course_id is not None:
            self._require_course(course_id)
        if staff_id is not None:
            self._require_staff(staff_id)
        subj.update(name=name, course_id=course_id, staff_id=staff_id)

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        self._require_subject(subject_id)

        to_delete_attendance = [rid for rid, rec in self._attendance.items() if rec.subject_id == subject_id]
        for rid in to_delete_attendance:
            rec = self._attendance[rid]
            self._attendance_index.pop((rec.student_id, rec.subject_id, rec.date), None)
            del self._attendance[rid]

        to_delete_results = [rid for rid, res in self._results.items() if res.subject_id == subject_id]
        for rid in to_delete_results:
            res = self._results[rid]
            self._results_index.pop((res.student_id, res.subject_id), None)
            del self._results[rid]

        del self._subjects[subject_id]

    def view_student_attendance_as_admin(self, admin_id: int, student_id: int) -> List[AttendanceRecord]:
        self._require_admin(admin_id)
        self._require_student(student_id)
        return sorted(
            [rec for rec in self._attendance.values() if rec.student_id == student_id],
            key=lambda r: (r.date, r.subject_id, r.id),
        )

    def take_or_update_attendance(self, staff_id: int, student_id: int, subject_id: int, on_date: date, status: AttendanceStatus) -> int:
        self._require_staff(staff_id)
        self._require_student(student_id)
        self._require_subject(subject_id)
        if not self._staff_teaches_subject(staff_id, subject_id):
            raise PermissionError("staff not assigned to this subject")
        if not self._subject_belongs_to_student_course(student_id, subject_id):
            raise ValueError("subject not in student's course")

        key = (student_id, subject_id, on_date)
        existing_id = self._attendance_index.get(key)
        if existing_id is not None:
            rec = self._attendance[existing_id]
            rec.update_status(status, updated_by_staff_id=staff_id)
            return rec.id

        record_id = self._new_attendance_id()
        rec = AttendanceRecord(record_id, student_id, subject_id, on_date, status, taken_by_staff_id=staff_id)
        self._attendance[record_id] = rec
        self._attendance_index[key] = record_id
        return record_id

    def view_attendance_as_student(self, student_id: int) -> List[AttendanceRecord]:
        self._require_student(student_id)
        return sorted(
            [rec for rec in self._attendance.values() if rec.student_id == student_id],
            key=lambda r: (r.date, r.subject_id, r.id),
        )

    def view_attendance_as_staff(self, staff_id: int) -> List[AttendanceRecord]:
        self._require_staff(staff_id)
        staff_subjects: Set[int] = {s.id for s in self._subjects.values() if s.staff_id == staff_id}
        return sorted(
            [rec for rec in self._attendance.values() if rec.subject_id in staff_subjects],
            key=lambda r: (r.date, r.subject_id, r.student_id, r.id),
        )

    def add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, marks: float) -> int:
        self._require_staff(staff_id)
        self._require_student(student_id)
        self._require_subject(subject_id)
        if not self._staff_teaches_subject(staff_id, subject_id):
            raise PermissionError("staff not assigned to this subject")
        if not self._subject_belongs_to_student_course(student_id, subject_id):
            raise ValueError("subject not in student's course")

        key = (student_id, subject_id)
        existing_id = self._results_index.get(key)
        if existing_id is not None:
            res = self._results[existing_id]
            res.update_marks(marks, updated_by_staff_id=staff_id)
            return res.id

        result_id = self._new_result_id()
        res = Result(result_id, student_id, subject_id, marks, added_by_staff_id=staff_id)
        self._results[result_id] = res
        self._results_index[key] = result_id
        return result_id

    def view_result_as_student(self, student_id: int) -> List[Result]:
        self._require_student(student_id)
        return sorted(
            [res for res in self._results.values() if res.student_id == student_id],
            key=lambda r: (r.subject_id, r.id),
        )

    def view_results_as_staff(self, staff_id: int) -> List[Result]:
        self._require_staff(staff_id)
        staff_subjects: Set[int] = {s.id for s in self._subjects.values() if s.staff_id == staff_id}
        return sorted(
            [res for res in self._results.values() if res.subject_id in staff_subjects],
            key=lambda r: (r.subject_id, r.student_id, r.id),
        )

    def apply_leave_as_student(self, student_id: int, from_date: date, to_date: date, reason: str) -> int:
        self._require_student(student_id)
        leave_id = self._new_leave_id()
        self._leaves[leave_id] = LeaveRequest(leave_id, Role.STUDENT, student_id, from_date, to_date, reason)
        return leave_id

    def apply_leave_as_staff(self, staff_id: int, from_date: date, to_date: date, reason: str) -> int:
        self._require_staff(staff_id)
        leave_id = self._new_leave_id()
        self._leaves[leave_id] = LeaveRequest(leave_id, Role.STAFF, staff_id, from_date, to_date, reason)
        return leave_id

    def review_leave(self, admin_id: int, leave_id: int, approve: bool, note: Optional[str] = None) -> None:
        self._require_admin(admin_id)
        leave = self._leaves.get(leave_id)
        if leave is None:
            raise KeyError("leave request not found")
        leave.review(admin_id=admin_id, approve=approve, note=note)

    def list_leaves_as_admin(self, admin_id: int) -> List[LeaveRequest]:
        self._require_admin(admin_id)
        return sorted(self._leaves.values(), key=lambda l: (l.status.value, l.created_at, l.id))

    def list_leaves_as_student(self, student_id: int) -> List[LeaveRequest]:
        self._require_student(student_id)
        return sorted(
            [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id],
            key=lambda l: (l.created_at, l.id),
        )

    def list_leaves_as_staff(self, staff_id: int) -> List[LeaveRequest]:
        self._require_staff(staff_id)
        return sorted(
            [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id],
            key=lambda l: (l.created_at, l.id),
        )

    def send_feedback_as_student(self, student_id: int, message: str) -> int:
        self._require_student(student_id)
        feedback_id = self._new_feedback_id()
        self._feedback[feedback_id] = Feedback(feedback_id, Role.STUDENT, student_id, message)
        return feedback_id

    def send_feedback_as_staff(self, staff_id: int, message: str) -> int:
        self._require_staff(staff_id)
        feedback_id = self._new_feedback_id()
        self._feedback[feedback_id] = Feedback(feedback_id, Role.STAFF, staff_id, message)
        return feedback_id

    def review_and_reply_feedback(self, admin_id: int, feedback_id: int, reply: str) -> None:
        self._require_admin(admin_id)
        fb = self._feedback.get(feedback_id)
        if fb is None:
            raise KeyError("feedback not found")
        fb.reply_by_admin(admin_id=admin_id, reply=reply)

    def list_feedback_as_admin(self, admin_id: int) -> List[Feedback]:
        self._require_admin(admin_id)
        return sorted(self._feedback.values(), key=lambda f: (f.status.value, f.created_at, f.id))

    def list_feedback_as_student(self, student_id: int) -> List[Feedback]:
        self._require_student(student_id)
        return sorted(
            [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id],
            key=lambda f: (f.created_at, f.id),
        )

    def list_feedback_as_staff(self, staff_id: int) -> List[Feedback]:
        self._require_staff(staff_id)
        return sorted(
            [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id],
            key=lambda f: (f.created_at, f.id),
        )

    def get_overall_summary_charts_as_admin(self, admin_id: int) -> SummaryCharts:
        self._require_admin(admin_id)
        return self._build_summary()

    def get_overall_summary_charts_as_staff(self, staff_id: int) -> SummaryCharts:
        self._require_staff(staff_id)
        staff_subjects: Set[int] = {s.id for s in self._subjects.values() if s.staff_id == staff_id}

        attendance_count = sum(1 for a in self._attendance.values() if a.subject_id in staff_subjects)
        results_count = sum(1 for r in self._results.values() if r.subject_id in staff_subjects)

        leave_total = sum(1 for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id)
        leave_pending = sum(1 for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.REJECTED)

        feedback_total = sum(1 for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id)
        feedback_open = sum(1 for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id and f.status == FeedbackStatus.OPEN)
        feedback_replied = sum(1 for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id and f.status == FeedbackStatus.REPLIED)

        return SummaryCharts(
            students_count=len(self._students),
            staff_count=len(self._staff),
            courses_count=len(self._courses),
            subjects_count=len(staff_subjects),
            sessions_count=len(self._sessions),
            attendance_records_count=attendance_count,
            results_count=results_count,
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_total=feedback_total,
            feedback_open=feedback_open,
            feedback_replied=feedback_replied,
        )

    def get_overall_summary_charts_as_student(self, student_id: int) -> SummaryCharts:
        self._require_student(student_id)
        enr = self._require_enrollment(student_id)
        student_subjects: Set[int] = {s.id for s in self._subjects.values() if s.course_id == enr.course_id}

        attendance_count = sum(1 for a in self._attendance.values() if a.student_id == student_id)
        results_count = sum(1 for r in self._results.values() if r.student_id == student_id)

        leave_total = sum(1 for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id)
        leave_pending = sum(1 for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.REJECTED)

        feedback_total = sum(1 for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id)
        feedback_open = sum(1 for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id and f.status == FeedbackStatus.OPEN)
        feedback_replied = sum(1 for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id and f.status == FeedbackStatus.REPLIED)

        return SummaryCharts(
            students_count=1,
            staff_count=len(self._staff),
            courses_count=1,
            subjects_count=len(student_subjects),
            sessions_count=1,
            attendance_records_count=attendance_count,
            results_count=results_count,
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_total=feedback_total,
            feedback_open=feedback_open,
            feedback_replied=feedback_replied,
        )

    def _build_summary(self) -> SummaryCharts:
        leave_total = len(self._leaves)
        leave_pending = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.REJECTED)

        feedback_total = len(self._feedback)
        feedback_open = sum(1 for f in self._feedback.values() if f.status == FeedbackStatus.OPEN)
        feedback_replied = sum(1 for f in self._feedback.values() if f.status == FeedbackStatus.REPLIED)

        return SummaryCharts(
            students_count=len(self._students),
            staff_count=len(self._staff),
            courses_count=len(self._courses),
            subjects_count=len(self._subjects),
            sessions_count=len(self._sessions),
            attendance_records_count=len(self._attendance),
            results_count=len(self._results),
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_total=feedback_total,
            feedback_open=feedback_open,
            feedback_replied=feedback_replied,
        )