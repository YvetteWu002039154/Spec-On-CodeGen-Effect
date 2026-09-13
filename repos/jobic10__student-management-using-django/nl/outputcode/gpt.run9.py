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


@dataclass(frozen=True)
class Summary:
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
    feedback_unreplied: int


@dataclass(frozen=True)
class StaffSummary:
    staff_id: int
    subjects_count: int
    students_count: int
    attendance_records_count: int
    results_count: int
    leave_total: int
    leave_pending: int
    leave_approved: int
    leave_rejected: int
    feedback_sent: int


@dataclass(frozen=True)
class StudentSummary:
    student_id: int
    subjects_count: int
    attendance_total: int
    attendance_present: int
    attendance_absent: int
    results_count: int
    leave_total: int
    leave_pending: int
    leave_approved: int
    leave_rejected: int
    feedback_sent: int


class Entity:
    def __init__(self, entity_id: int) -> None:
        self._id = entity_id

    @property
    def id(self) -> int:
        return self._id


class User(Entity):
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        super().__init__(user_id)
        if not name or not name.strip():
            raise ValueError("User name must be non-empty.")
        self._name = name.strip()
        self._role = role

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
        self._course_id = course_id
        self._session_id = session_id

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def session_id(self) -> int:
        return self._session_id

    def _set_course_id(self, course_id: int) -> None:
        self._course_id = course_id

    def _set_session_id(self, session_id: int) -> None:
        self._session_id = session_id


class Course(Entity):
    def __init__(self, course_id: int, name: str) -> None:
        super().__init__(course_id)
        if not name or not name.strip():
            raise ValueError("Course name must be non-empty.")
        self._name = name.strip()

    @property
    def name(self) -> str:
        return self._name

    def _set_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Course name must be non-empty.")
        self._name = name.strip()


class Subject(Entity):
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        super().__init__(subject_id)
        if not name or not name.strip():
            raise ValueError("Subject name must be non-empty.")
        self._name = name.strip()
        self._course_id = course_id
        self._staff_id = staff_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def staff_id(self) -> int:
        return self._staff_id

    def _set_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Subject name must be non-empty.")
        self._name = name.strip()

    def _set_course_id(self, course_id: int) -> None:
        self._course_id = course_id

    def _set_staff_id(self, staff_id: int) -> None:
        self._staff_id = staff_id


class Session(Entity):
    def __init__(self, session_id: int, name: str) -> None:
        super().__init__(session_id)
        if not name or not name.strip():
            raise ValueError("Session name must be non-empty.")
        self._name = name.strip()

    @property
    def name(self) -> str:
        return self._name

    def _set_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Session name must be non-empty.")
        self._name = name.strip()


class AttendanceRecord(Entity):
    def __init__(
        self,
        record_id: int,
        student_id: int,
        subject_id: int,
        staff_id: int,
        on_date: date,
        present: bool,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(record_id)
        self._student_id = student_id
        self._subject_id = subject_id
        self._staff_id = staff_id
        self._date = on_date
        self._present = present
        self._updated_at = updated_at or datetime.utcnow()

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
    def present(self) -> bool:
        return self._present

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _set_present(self, present: bool) -> None:
        self._present = present
        self._updated_at = datetime.utcnow()


class ResultRecord(Entity):
    def __init__(
        self,
        result_id: int,
        student_id: int,
        subject_id: int,
        staff_id: int,
        score: float,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(result_id)
        self._student_id = student_id
        self._subject_id = subject_id
        self._staff_id = staff_id
        self._score = float(score)
        self._updated_at = updated_at or datetime.utcnow()

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

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _set_score(self, score: float) -> None:
        self._score = float(score)
        self._updated_at = datetime.utcnow()


class LeaveRequest(Entity):
    def __init__(
        self,
        leave_id: int,
        requester_role: Role,
        requester_id: int,
        from_date: date,
        to_date: date,
        reason: str,
        status: LeaveStatus = LeaveStatus.PENDING,
        reviewed_by_admin_id: Optional[int] = None,
        reviewed_at: Optional[datetime] = None,
        review_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(leave_id)
        if requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValueError("Leave requester must be staff or student.")
        if to_date < from_date:
            raise ValueError("Leave to_date must be >= from_date.")
        if not reason or not reason.strip():
            raise ValueError("Leave reason must be non-empty.")
        self._requester_role = requester_role
        self._requester_id = requester_id
        self._from_date = from_date
        self._to_date = to_date
        self._reason = reason.strip()
        self._status = status
        self._reviewed_by_admin_id = reviewed_by_admin_id
        self._reviewed_at = reviewed_at
        self._review_message = review_message.strip() if review_message else None
        self._created_at = created_at or datetime.utcnow()

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
    def review_message(self) -> Optional[str]:
        return self._review_message

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def _review(self, admin_id: int, approve: bool, message: Optional[str]) -> None:
        self._status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        self._reviewed_by_admin_id = admin_id
        self._reviewed_at = datetime.utcnow()
        self._review_message = message.strip() if message and message.strip() else None


class Feedback(Entity):
    def __init__(
        self,
        feedback_id: int,
        sender_role: Role,
        sender_id: int,
        message: str,
        reply: Optional[str] = None,
        replied_by_admin_id: Optional[int] = None,
        replied_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(feedback_id)
        if sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValueError("Feedback sender must be staff or student.")
        if not message or not message.strip():
            raise ValueError("Feedback message must be non-empty.")
        self._sender_role = sender_role
        self._sender_id = sender_id
        self._message = message.strip()
        self._reply = reply.strip() if reply else None
        self._replied_by_admin_id = replied_by_admin_id
        self._replied_at = replied_at
        self._created_at = created_at or datetime.utcnow()

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

    def _set_reply(self, admin_id: int, reply: str) -> None:
        if not reply or not reply.strip():
            raise ValueError("Reply must be non-empty.")
        self._reply = reply.strip()
        self._replied_by_admin_id = admin_id
        self._replied_at = datetime.utcnow()


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_id: int = 1

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

        self._leaves: Dict[int, LeaveRequest] = {}
        self._feedback: Dict[int, Feedback] = {}

    def _new_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def _require_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(admin_id)
        if not admin:
            raise ValueError("Admin not found.")
        return admin

    def _require_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(staff_id)
        if not staff:
            raise ValueError("Staff not found.")
        return staff

    def _require_student(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if not student:
            raise ValueError("Student not found.")
        return student

    def _require_course(self, course_id: int) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise ValueError("Course not found.")
        return course

    def _require_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError("Subject not found.")
        return subject

    def _require_session(self, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("Session not found.")
        return session

    def _require_leave(self, leave_id: int) -> LeaveRequest:
        leave = self._leaves.get(leave_id)
        if not leave:
            raise ValueError("Leave request not found.")
        return leave

    def _require_feedback(self, feedback_id: int) -> Feedback:
        fb = self._feedback.get(feedback_id)
        if not fb:
            raise ValueError("Feedback not found.")
        return fb

    def create_admin(self, name: str) -> int:
        admin_id = self._new_id()
        self._admins[admin_id] = Admin(admin_id, name)
        return admin_id

    def create_staff(self, admin_id: int, name: str) -> int:
        self._require_admin(admin_id)
        staff_id = self._new_id()
        self._staff[staff_id] = Staff(staff_id, name)
        return staff_id

    def update_staff(self, admin_id: int, staff_id: int, name: str) -> None:
        self._require_admin(admin_id)
        staff = self._require_staff(staff_id)
        if not name or not name.strip():
            raise ValueError("Staff name must be non-empty.")
        staff._name = name.strip()

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        self._require_staff(staff_id)

        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValueError("Cannot delete staff assigned to a subject.")

        for rec in self._attendance.values():
            if rec.staff_id == staff_id:
                raise ValueError("Cannot delete staff with attendance records.")

        for res in self._results.values():
            if res.staff_id == staff_id:
                raise ValueError("Cannot delete staff with result records.")

        del self._staff[staff_id]

    def add_course(self, admin_id: int, name: str) -> int:
        self._require_admin(admin_id)
        course_id = self._new_id()
        self._courses[course_id] = Course(course_id, name)
        return course_id

    def update_course(self, admin_id: int, course_id: int, name: str) -> None:
        self._require_admin(admin_id)
        course = self._require_course(course_id)
        course._set_name(name)

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        self._require_course(course_id)

        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValueError("Cannot delete course with subjects.")
        for stu in self._students.values():
            if stu.course_id == course_id:
                raise ValueError("Cannot delete course with students.")

        del self._courses[course_id]

    def add_session(self, admin_id: int, name: str) -> int:
        self._require_admin(admin_id)
        session_id = self._new_id()
        self._sessions[session_id] = Session(session_id, name)
        return session_id

    def update_session(self, admin_id: int, session_id: int, name: str) -> None:
        self._require_admin(admin_id)
        session = self._require_session(session_id)
        session._set_name(name)

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        self._require_session(session_id)

        for stu in self._students.values():
            if stu.session_id == session_id:
                raise ValueError("Cannot delete session with students.")

        del self._sessions[session_id]

    def add_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> int:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_staff(staff_id)
        subject_id = self._new_id()
        self._subjects[subject_id] = Subject(subject_id, name, course_id, staff_id)
        return subject_id

    def update_subject(
        self,
        admin_id: int,
        subject_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        staff_id: Optional[int] = None,
    ) -> None:
        self._require_admin(admin_id)
        subject = self._require_subject(subject_id)
        if name is not None:
            subject._set_name(name)
        if course_id is not None:
            self._require_course(course_id)
            subject._set_course_id(course_id)
        if staff_id is not None:
            self._require_staff(staff_id)
            subject._set_staff_id(staff_id)

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        self._require_subject(subject_id)

        for rec in self._attendance.values():
            if rec.subject_id == subject_id:
                raise ValueError("Cannot delete subject with attendance records.")
        for res in self._results.values():
            if res.subject_id == subject_id:
                raise ValueError("Cannot delete subject with result records.")

        del self._subjects[subject_id]

    def add_student(self, admin_id: int, name: str, course_id: int, session_id: int) -> int:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_session(session_id)
        student_id = self._new_id()
        self._students[student_id] = Student(student_id, name, course_id, session_id)
        return student_id

    def update_student(
        self,
        admin_id: int,
        student_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> None:
        self._require_admin(admin_id)
        student = self._require_student(student_id)
        if name is not None:
            if not name or not name.strip():
                raise ValueError("Student name must be non-empty.")
            student._name = name.strip()
        if course_id is not None:
            self._require_course(course_id)
            student._set_course_id(course_id)
        if session_id is not None:
            self._require_session(session_id)
            student._set_session_id(session_id)

    def delete_student(self, admin_id: int, student_id: int) -> None:
        self._require_admin(admin_id)
        self._require_student(student_id)

        for rec in self._attendance.values():
            if rec.student_id == student_id:
                raise ValueError("Cannot delete student with attendance records.")
        for res in self._results.values():
            if res.student_id == student_id:
                raise ValueError("Cannot delete student with result records.")
        for leave in self._leaves.values():
            if leave.requester_role == Role.STUDENT and leave.requester_id == student_id:
                raise ValueError("Cannot delete student with leave requests.")
        for fb in self._feedback.values():
            if fb.sender_role == Role.STUDENT and fb.sender_id == student_id:
                raise ValueError("Cannot delete student with feedback.")

        del self._students[student_id]

    def take_or_update_attendance(
        self,
        staff_id: int,
        student_id: int,
        subject_id: int,
        on_date: date,
        present: bool,
    ) -> int:
        self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._require_subject(subject_id)

        if subject.staff_id != staff_id:
            raise ValueError("Staff is not assigned to this subject.")
        if subject.course_id != student.course_id:
            raise ValueError("Subject course does not match student's course.")

        key = (student_id, subject_id, on_date)
        existing_id = self._attendance_index.get(key)
        if existing_id is not None:
            rec = self._attendance[existing_id]
            rec._set_present(present)
            return rec.id

        record_id = self._new_id()
        rec = AttendanceRecord(record_id, student_id, subject_id, staff_id, on_date, present)
        self._attendance[record_id] = rec
        self._attendance_index[key] = record_id
        return record_id

    def view_student_attendance(self, viewer_role: Role, viewer_id: int, student_id: int) -> List[AttendanceRecord]:
        if viewer_role == Role.ADMIN:
            self._require_admin(viewer_id)
        elif viewer_role == Role.STAFF:
            self._require_staff(viewer_id)
        elif viewer_role == Role.STUDENT:
            if viewer_id != student_id:
                raise ValueError("Students can only view their own attendance.")
            self._require_student(viewer_id)
        else:
            raise ValueError("Invalid role.")

        self._require_student(student_id)
        records = [r for r in self._attendance.values() if r.student_id == student_id]
        records.sort(key=lambda r: (r.date, r.subject_id, r.id))
        return records

    def add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, score: float) -> int:
        self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._require_subject(subject_id)

        if subject.staff_id != staff_id:
            raise ValueError("Staff is not assigned to this subject.")
        if subject.course_id != student.course_id:
            raise ValueError("Subject course does not match student's course.")

        key = (student_id, subject_id)
        existing_id = self._results_index.get(key)
        if existing_id is not None:
            res = self._results[existing_id]
            res._set_score(score)
            return res.id

        result_id = self._new_id()
        res = ResultRecord(result_id, student_id, subject_id, staff_id, score)
        self._results[result_id] = res
        self._results_index[key] = result_id
        return result_id

    def view_student_results(self, viewer_role: Role, viewer_id: int, student_id: int) -> List[ResultRecord]:
        if viewer_role == Role.ADMIN:
            self._require_admin(viewer_id)
        elif viewer_role == Role.STAFF:
            self._require_staff(viewer_id)
        elif viewer_role == Role.STUDENT:
            if viewer_id != student_id:
                raise ValueError("Students can only view their own results.")
            self._require_student(viewer_id)
        else:
            raise ValueError("Invalid role.")

        self._require_student(student_id)
        results = [r for r in self._results.values() if r.student_id == student_id]
        results.sort(key=lambda r: (r.subject_id, r.id))
        return results

    def apply_for_leave(self, requester_role: Role, requester_id: int, from_date: date, to_date: date, reason: str) -> int:
        if requester_role == Role.STAFF:
            self._require_staff(requester_id)
        elif requester_role == Role.STUDENT:
            self._require_student(requester_id)
        else:
            raise ValueError("Only staff or students can apply for leave.")

        leave_id = self._new_id()
        self._leaves[leave_id] = LeaveRequest(leave_id, requester_role, requester_id, from_date, to_date, reason)
        return leave_id

    def review_leave(self, admin_id: int, leave_id: int, approve: bool, message: Optional[str] = None) -> None:
        self._require_admin(admin_id)
        leave = self._require_leave(leave_id)
        if leave.status != LeaveStatus.PENDING:
            raise ValueError("Leave request has already been reviewed.")
        leave._review(admin_id, approve, message)

    def list_leaves(self, viewer_role: Role, viewer_id: int) -> List[LeaveRequest]:
        if viewer_role == Role.ADMIN:
            self._require_admin(viewer_id)
            leaves = list(self._leaves.values())
        elif viewer_role == Role.STAFF:
            self._require_staff(viewer_id)
            leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == viewer_id]
        elif viewer_role == Role.STUDENT:
            self._require_student(viewer_id)
            leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == viewer_id]
        else:
            raise ValueError("Invalid role.")

        leaves.sort(key=lambda l: (l.status.value, l.created_at, l.id))
        return leaves

    def send_feedback(self, sender_role: Role, sender_id: int, message: str) -> int:
        if sender_role == Role.STAFF:
            self._require_staff(sender_id)
        elif sender_role == Role.STUDENT:
            self._require_student(sender_id)
        else:
            raise ValueError("Only staff or students can send feedback.")

        feedback_id = self._new_id()
        self._feedback[feedback_id] = Feedback(feedback_id, sender_role, sender_id, message)
        return feedback_id

    def reply_feedback(self, admin_id: int, feedback_id: int, reply: str) -> None:
        self._require_admin(admin_id)
        fb = self._require_feedback(feedback_id)
        fb._set_reply(admin_id, reply)

    def list_feedback(self, viewer_role: Role, viewer_id: int) -> List[Feedback]:
        if viewer_role == Role.ADMIN:
            self._require_admin(viewer_id)
            items = list(self._feedback.values())
        elif viewer_role == Role.STAFF:
            self._require_staff(viewer_id)
            items = [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == viewer_id]
        elif viewer_role == Role.STUDENT:
            self._require_student(viewer_id)
            items = [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == viewer_id]
        else:
            raise ValueError("Invalid role.")

        items.sort(key=lambda f: (f.replied_at is None, f.created_at, f.id))
        return items

    def admin_summary(self, admin_id: int) -> Summary:
        self._require_admin(admin_id)

        leave_total = len(self._leaves)
        leave_pending = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.REJECTED)

        feedback_total = len(self._feedback)
        feedback_unreplied = sum(1 for f in self._feedback.values() if f.reply is None)

        return Summary(
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
            feedback_unreplied=feedback_unreplied,
        )

    def staff_summary(self, staff_id: int) -> StaffSummary:
        self._require_staff(staff_id)

        subjects = [s for s in self._subjects.values() if s.staff_id == staff_id]
        subject_ids: Set[int] = {s.id for s in subjects}
        course_ids: Set[int] = {s.course_id for s in subjects}

        students_count = sum(1 for st in self._students.values() if st.course_id in course_ids)

        attendance_records_count = sum(1 for a in self._attendance.values() if a.staff_id == staff_id and a.subject_id in subject_ids)
        results_count = sum(1 for r in self._results.values() if r.staff_id == staff_id and r.subject_id in subject_ids)

        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id]
        leave_total = len(leaves)
        leave_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)

        feedback_sent = sum(1 for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id)

        return StaffSummary(
            staff_id=staff_id,
            subjects_count=len(subjects),
            students_count=students_count,
            attendance_records_count=attendance_records_count,
            results_count=results_count,
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_sent=feedback_sent,
        )

    def student_summary(self, student_id: int) -> StudentSummary:
        student = self._require_student(student_id)

        subjects = [s for s in self._subjects.values() if s.course_id == student.course_id]
        subject_ids: Set[int] = {s.id for s in subjects}

        attendance = [a for a in self._attendance.values() if a.student_id == student_id and a.subject_id in subject_ids]
        attendance_total = len(attendance)
        attendance_present = sum(1 for a in attendance if a.present)
        attendance_absent = attendance_total - attendance_present

        results_count = sum(1 for r in self._results.values() if r.student_id == student_id and r.subject_id in subject_ids)

        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id]
        leave_total = len(leaves)
        leave_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)

        feedback_sent = sum(1 for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id)

        return StudentSummary(
            student_id=student_id,
            subjects_count=len(subjects),
            attendance_total=attendance_total,
            attendance_present=attendance_present,
            attendance_absent=attendance_absent,
            results_count=results_count,
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_sent=feedback_sent,
        )

    def list_students(self, admin_id: int) -> List[Student]:
        self._require_admin(admin_id)
        items = list(self._students.values())
        items.sort(key=lambda s: s.id)
        return items

    def list_staff(self, admin_id: int) -> List[Staff]:
        self._require_admin(admin_id)
        items = list(self._staff.values())
        items.sort(key=lambda s: s.id)
        return items

    def list_courses(self, admin_id: int) -> List[Course]:
        self._require_admin(admin_id)
        items = list(self._courses.values())
        items.sort(key=lambda c: c.id)
        return items

    def list_subjects(self, admin_id: int) -> List[Subject]:
        self._require_admin(admin_id)
        items = list(self._subjects.values())
        items.sort(key=lambda s: s.id)
        return items

    def list_sessions(self, admin_id: int) -> List[Session]:
        self._require_admin(admin_id)
        items = list(self._sessions.values())
        items.sort(key=lambda s: s.id)
        return items