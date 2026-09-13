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


class EntityNotFoundError(ValueError):
    pass


class ValidationError(ValueError):
    pass


class PermissionError(ValueError):
    pass


class User:
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        if not name or not name.strip():
            raise ValidationError("Name must be non-empty.")
        self._id = int(user_id)
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
        self._course_id = int(course_id)
        self._session_id = int(session_id)

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def session_id(self) -> int:
        return self._session_id

    def _set_course_id(self, course_id: int) -> None:
        self._course_id = int(course_id)

    def _set_session_id(self, session_id: int) -> None:
        self._session_id = int(session_id)


class Course:
    def __init__(self, course_id: int, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Course name must be non-empty.")
        self._id = int(course_id)
        self._name = name.strip()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def _set_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Course name must be non-empty.")
        self._name = name.strip()


class Session:
    def __init__(self, session_id: int, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Session name must be non-empty.")
        self._id = int(session_id)
        self._name = name.strip()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def _set_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Session name must be non-empty.")
        self._name = name.strip()


class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if not name or not name.strip():
            raise ValidationError("Subject name must be non-empty.")
        self._id = int(subject_id)
        self._name = name.strip()
        self._course_id = int(course_id)
        self._staff_id = int(staff_id)

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

    def _set_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Subject name must be non-empty.")
        self._name = name.strip()

    def _set_course_id(self, course_id: int) -> None:
        self._course_id = int(course_id)

    def _set_staff_id(self, staff_id: int) -> None:
        self._staff_id = int(staff_id)


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceRecord:
    def __init__(
        self,
        record_id: int,
        student_id: int,
        subject_id: int,
        on_date: date,
        status: AttendanceStatus,
        taken_by_staff_id: int,
        taken_at: Optional[datetime] = None,
    ) -> None:
        self._id = int(record_id)
        self._student_id = int(student_id)
        self._subject_id = int(subject_id)
        self._date = on_date
        self._status = status
        self._taken_by_staff_id = int(taken_by_staff_id)
        self._taken_at = taken_at or datetime.utcnow()

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
    def taken_at(self) -> datetime:
        return self._taken_at

    def _set_status(self, status: AttendanceStatus, staff_id: int) -> None:
        self._status = status
        self._taken_by_staff_id = int(staff_id)
        self._taken_at = datetime.utcnow()


class Result:
    def __init__(
        self,
        result_id: int,
        student_id: int,
        subject_id: int,
        score: float,
        added_by_staff_id: int,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self._id = int(result_id)
        self._student_id = int(student_id)
        self._subject_id = int(subject_id)
        self._score = float(score)
        self._added_by_staff_id = int(added_by_staff_id)
        self._updated_at = updated_at or datetime.utcnow()

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
    def added_by_staff_id(self) -> int:
        return self._added_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _set_score(self, score: float, staff_id: int) -> None:
        self._score = float(score)
        self._added_by_staff_id = int(staff_id)
        self._updated_at = datetime.utcnow()


class LeaveRequest:
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
        review_note: Optional[str] = None,
    ) -> None:
        if requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("Leave requester must be staff or student.")
        if to_date < from_date:
            raise ValidationError("Leave to_date must be >= from_date.")
        if not reason or not reason.strip():
            raise ValidationError("Leave reason must be non-empty.")
        self._id = int(leave_id)
        self._requester_role = requester_role
        self._requester_id = int(requester_id)
        self._from_date = from_date
        self._to_date = to_date
        self._reason = reason.strip()
        self._status = status
        self._reviewed_by_admin_id = reviewed_by_admin_id
        self._reviewed_at = reviewed_at
        self._review_note = review_note

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

    def _review(self, admin_id: int, approve: bool, note: Optional[str]) -> None:
        self._status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        self._reviewed_by_admin_id = int(admin_id)
        self._reviewed_at = datetime.utcnow()
        self._review_note = note.strip() if note is not None else None


class Feedback:
    def __init__(
        self,
        feedback_id: int,
        sender_role: Role,
        sender_id: int,
        message: str,
        created_at: Optional[datetime] = None,
        replied_by_admin_id: Optional[int] = None,
        reply_message: Optional[str] = None,
        replied_at: Optional[datetime] = None,
    ) -> None:
        if sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("Feedback sender must be staff or student.")
        if not message or not message.strip():
            raise ValidationError("Feedback message must be non-empty.")
        self._id = int(feedback_id)
        self._sender_role = sender_role
        self._sender_id = int(sender_id)
        self._message = message.strip()
        self._created_at = created_at or datetime.utcnow()
        self._replied_by_admin_id = replied_by_admin_id
        self._reply_message = reply_message.strip() if reply_message is not None else None
        self._replied_at = replied_at

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
    def replied_by_admin_id(self) -> Optional[int]:
        return self._replied_by_admin_id

    @property
    def reply_message(self) -> Optional[str]:
        return self._reply_message

    @property
    def replied_at(self) -> Optional[datetime]:
        return self._replied_at

    @property
    def is_replied(self) -> bool:
        return self._replied_at is not None

    def _reply(self, admin_id: int, reply_message: str) -> None:
        if not reply_message or not reply_message.strip():
            raise ValidationError("Reply message must be non-empty.")
        self._replied_by_admin_id = int(admin_id)
        self._reply_message = reply_message.strip()
        self._replied_at = datetime.utcnow()


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

        self._results: Dict[int, Result] = {}
        self._results_index: Dict[Tuple[int, int], int] = {}

        self._leaves: Dict[int, LeaveRequest] = {}
        self._feedback: Dict[int, Feedback] = {}

        self._next_admin_id = 1
        self._next_staff_id = 1
        self._next_student_id = 1
        self._next_course_id = 1
        self._next_subject_id = 1
        self._next_session_id = 1
        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_leave_id = 1
        self._next_feedback_id = 1

    def _require_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(int(admin_id))
        if admin is None:
            raise PermissionError("Admin not found or not authorized.")
        return admin

    def _require_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(int(staff_id))
        if staff is None:
            raise PermissionError("Staff not found or not authorized.")
        return staff

    def _require_student(self, student_id: int) -> Student:
        student = self._students.get(int(student_id))
        if student is None:
            raise PermissionError("Student not found or not authorized.")
        return student

    def _get_course(self, course_id: int) -> Course:
        course = self._courses.get(int(course_id))
        if course is None:
            raise EntityNotFoundError("Course not found.")
        return course

    def _get_session(self, session_id: int) -> Session:
        session = self._sessions.get(int(session_id))
        if session is None:
            raise EntityNotFoundError("Session not found.")
        return session

    def _get_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(int(subject_id))
        if subject is None:
            raise EntityNotFoundError("Subject not found.")
        return subject

    def _get_leave(self, leave_id: int) -> LeaveRequest:
        leave = self._leaves.get(int(leave_id))
        if leave is None:
            raise EntityNotFoundError("Leave request not found.")
        return leave

    def _get_feedback(self, feedback_id: int) -> Feedback:
        fb = self._feedback.get(int(feedback_id))
        if fb is None:
            raise EntityNotFoundError("Feedback not found.")
        return fb

    def create_admin(self, name: str) -> Admin:
        admin = Admin(self._next_admin_id, name)
        self._admins[admin.id] = admin
        self._next_admin_id += 1
        return admin

    def admin_add_staff(self, admin_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        staff = Staff(self._next_staff_id, name)
        self._staff[staff.id] = staff
        self._next_staff_id += 1
        return staff

    def admin_update_staff(self, admin_id: int, staff_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        staff = self._staff.get(int(staff_id))
        if staff is None:
            raise EntityNotFoundError("Staff not found.")
        if not name or not name.strip():
            raise ValidationError("Name must be non-empty.")
        staff._name = name.strip()
        return staff

    def admin_delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        staff_id = int(staff_id)
        if staff_id not in self._staff:
            raise EntityNotFoundError("Staff not found.")
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValidationError("Cannot delete staff assigned to a subject.")
        del self._staff[staff_id]

    def admin_add_course(self, admin_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        course = Course(self._next_course_id, name)
        self._courses[course.id] = course
        self._next_course_id += 1
        return course

    def admin_update_course(self, admin_id: int, course_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        course = self._get_course(course_id)
        course._set_name(name)
        return course

    def admin_delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        course_id = int(course_id)
        if course_id not in self._courses:
            raise EntityNotFoundError("Course not found.")
        for student in self._students.values():
            if student.course_id == course_id:
                raise ValidationError("Cannot delete course with enrolled students.")
        for subject in self._subjects.values():
            if subject.course_id == course_id:
                raise ValidationError("Cannot delete course with subjects.")
        del self._courses[course_id]

    def admin_add_session(self, admin_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        session = Session(self._next_session_id, name)
        self._sessions[session.id] = session
        self._next_session_id += 1
        return session

    def admin_update_session(self, admin_id: int, session_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        session = self._get_session(session_id)
        session._set_name(name)
        return session

    def admin_delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        session_id = int(session_id)
        if session_id not in self._sessions:
            raise EntityNotFoundError("Session not found.")
        for student in self._students.values():
            if student.session_id == session_id:
                raise ValidationError("Cannot delete session with enrolled students.")
        del self._sessions[session_id]

    def admin_add_student(self, admin_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin_id)
        self._get_course(course_id)
        self._get_session(session_id)
        student = Student(self._next_student_id, name, course_id, session_id)
        self._students[student.id] = student
        self._next_student_id += 1
        return student

    def admin_update_student(
        self,
        admin_id: int,
        student_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> Student:
        self._require_admin(admin_id)
        student = self._students.get(int(student_id))
        if student is None:
            raise EntityNotFoundError("Student not found.")
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("Name must be non-empty.")
            student._name = name.strip()
        if course_id is not None:
            self._get_course(course_id)
            student._set_course_id(course_id)
        if session_id is not None:
            self._get_session(session_id)
            student._set_session_id(session_id)
        return student

    def admin_delete_student(self, admin_id: int, student_id: int) -> None:
        self._require_admin(admin_id)
        student_id = int(student_id)
        if student_id not in self._students:
            raise EntityNotFoundError("Student not found.")
        attendance_ids_to_delete = [rid for rid, rec in self._attendance.items() if rec.student_id == student_id]
        for rid in attendance_ids_to_delete:
            rec = self._attendance[rid]
            self._attendance_index.pop((rec.student_id, rec.subject_id, rec.date), None)
            del self._attendance[rid]
        result_ids_to_delete = [rid for rid, res in self._results.items() if res.student_id == student_id]
        for rid in result_ids_to_delete:
            res = self._results[rid]
            self._results_index.pop((res.student_id, res.subject_id), None)
            del self._results[rid]
        leave_ids_to_delete = [lid for lid, lv in self._leaves.items() if lv.requester_role == Role.STUDENT and lv.requester_id == student_id]
        for lid in leave_ids_to_delete:
            del self._leaves[lid]
        feedback_ids_to_delete = [fid for fid, fb in self._feedback.items() if fb.sender_role == Role.STUDENT and fb.sender_id == student_id]
        for fid in feedback_ids_to_delete:
            del self._feedback[fid]
        del self._students[student_id]

    def admin_add_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin_id)
        self._get_course(course_id)
        if int(staff_id) not in self._staff:
            raise EntityNotFoundError("Staff not found.")
        subject = Subject(self._next_subject_id, name, course_id, staff_id)
        self._subjects[subject.id] = subject
        self._next_subject_id += 1
        return subject

    def admin_update_subject(
        self,
        admin_id: int,
        subject_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        staff_id: Optional[int] = None,
    ) -> Subject:
        self._require_admin(admin_id)
        subject = self._get_subject(subject_id)
        if name is not None:
            subject._set_name(name)
        if course_id is not None:
            self._get_course(course_id)
            subject._set_course_id(course_id)
        if staff_id is not None:
            if int(staff_id) not in self._staff:
                raise EntityNotFoundError("Staff not found.")
            subject._set_staff_id(staff_id)
        return subject

    def admin_delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        subject_id = int(subject_id)
        if subject_id not in self._subjects:
            raise EntityNotFoundError("Subject not found.")
        attendance_ids_to_delete = [rid for rid, rec in self._attendance.items() if rec.subject_id == subject_id]
        for rid in attendance_ids_to_delete:
            rec = self._attendance[rid]
            self._attendance_index.pop((rec.student_id, rec.subject_id, rec.date), None)
            del self._attendance[rid]
        result_ids_to_delete = [rid for rid, res in self._results.items() if res.subject_id == subject_id]
        for rid in result_ids_to_delete:
            res = self._results[rid]
            self._results_index.pop((res.student_id, res.subject_id), None)
            del self._results[rid]
        del self._subjects[subject_id]

    def staff_take_or_update_attendance(
        self,
        staff_id: int,
        student_id: int,
        subject_id: int,
        on_date: date,
        status: AttendanceStatus,
    ) -> AttendanceRecord:
        self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._get_subject(subject_id)
        if subject.staff_id != int(staff_id):
            raise PermissionError("Staff not assigned to this subject.")
        if subject.course_id != student.course_id:
            raise ValidationError("Student course does not match subject course.")
        key = (int(student_id), int(subject_id), on_date)
        existing_id = self._attendance_index.get(key)
        if existing_id is not None:
            rec = self._attendance[existing_id]
            rec._set_status(status, staff_id)
            return rec
        rec = AttendanceRecord(
            record_id=self._next_attendance_id,
            student_id=student_id,
            subject_id=subject_id,
            on_date=on_date,
            status=status,
            taken_by_staff_id=staff_id,
        )
        self._attendance[rec.id] = rec
        self._attendance_index[key] = rec.id
        self._next_attendance_id += 1
        return rec

    def staff_add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, score: float) -> Result:
        self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._get_subject(subject_id)
        if subject.staff_id != int(staff_id):
            raise PermissionError("Staff not assigned to this subject.")
        if subject.course_id != student.course_id:
            raise ValidationError("Student course does not match subject course.")
        key = (int(student_id), int(subject_id))
        existing_id = self._results_index.get(key)
        if existing_id is not None:
            res = self._results[existing_id]
            res._set_score(score, staff_id)
            return res
        res = Result(
            result_id=self._next_result_id,
            student_id=student_id,
            subject_id=subject_id,
            score=score,
            added_by_staff_id=staff_id,
        )
        self._results[res.id] = res
        self._results_index[key] = res.id
        self._next_result_id += 1
        return res

    def staff_apply_leave(self, staff_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        self._require_staff(staff_id)
        leave = LeaveRequest(
            leave_id=self._next_leave_id,
            requester_role=Role.STAFF,
            requester_id=staff_id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
        )
        self._leaves[leave.id] = leave
        self._next_leave_id += 1
        return leave

    def student_apply_leave(self, student_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        self._require_student(student_id)
        leave = LeaveRequest(
            leave_id=self._next_leave_id,
            requester_role=Role.STUDENT,
            requester_id=student_id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
        )
        self._leaves[leave.id] = leave
        self._next_leave_id += 1
        return leave

    def staff_send_feedback_to_hod(self, staff_id: int, message: str) -> Feedback:
        self._require_staff(staff_id)
        fb = Feedback(
            feedback_id=self._next_feedback_id,
            sender_role=Role.STAFF,
            sender_id=staff_id,
            message=message,
        )
        self._feedback[fb.id] = fb
        self._next_feedback_id += 1
        return fb

    def student_send_feedback_to_hod(self, student_id: int, message: str) -> Feedback:
        self._require_student(student_id)
        fb = Feedback(
            feedback_id=self._next_feedback_id,
            sender_role=Role.STUDENT,
            sender_id=student_id,
            message=message,
        )
        self._feedback[fb.id] = fb
        self._next_feedback_id += 1
        return fb

    def admin_review_leave(self, admin_id: int, leave_id: int, approve: bool, note: Optional[str] = None) -> LeaveRequest:
        self._require_admin(admin_id)
        leave = self._get_leave(leave_id)
        if leave.status != LeaveStatus.PENDING:
            raise ValidationError("Leave request already reviewed.")
        leave._review(admin_id=admin_id, approve=approve, note=note)
        return leave

    def admin_reply_feedback(self, admin_id: int, feedback_id: int, reply_message: str) -> Feedback:
        self._require_admin(admin_id)
        fb = self._get_feedback(feedback_id)
        fb._reply(admin_id=admin_id, reply_message=reply_message)
        return fb

    def admin_view_student_attendance(
        self,
        admin_id: int,
        student_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[AttendanceRecord]:
        self._require_admin(admin_id)
        return self._filter_attendance(student_id, subject_id, from_date, to_date)

    def student_view_attendance(
        self,
        student_id: int,
        subject_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[AttendanceRecord]:
        self._require_student(student_id)
        return self._filter_attendance(student_id, subject_id, from_date, to_date)

    def _filter_attendance(
        self,
        student_id: Optional[int],
        subject_id: Optional[int],
        from_date: Optional[date],
        to_date: Optional[date],
    ) -> List[AttendanceRecord]:
        sid = int(student_id) if student_id is not None else None
        subid = int(subject_id) if subject_id is not None else None
        if from_date is not None and to_date is not None and to_date < from_date:
            raise ValidationError("to_date must be >= from_date.")
        out: List[AttendanceRecord] = []
        for rec in self._attendance.values():
            if sid is not None and rec.student_id != sid:
                continue
            if subid is not None and rec.subject_id != subid:
                continue
            if from_date is not None and rec.date < from_date:
                continue
            if to_date is not None and rec.date > to_date:
                continue
            out.append(rec)
        out.sort(key=lambda r: (r.date, r.subject_id, r.student_id))
        return out

    def student_view_results(self, student_id: int, subject_id: Optional[int] = None) -> List[Result]:
        self._require_student(student_id)
        sid = int(student_id)
        subid = int(subject_id) if subject_id is not None else None
        out: List[Result] = []
        for res in self._results.values():
            if res.student_id != sid:
                continue
            if subid is not None and res.subject_id != subid:
                continue
            out.append(res)
        out.sort(key=lambda r: (r.subject_id, r.updated_at))
        return out

    def staff_view_leave_status(self, staff_id: int) -> List[LeaveRequest]:
        self._require_staff(staff_id)
        sid = int(staff_id)
        out = [lv for lv in self._leaves.values() if lv.requester_role == Role.STAFF and lv.requester_id == sid]
        out.sort(key=lambda l: (l.status.value, l.from_date, l.id))
        return out

    def student_view_leave_status(self, student_id: int) -> List[LeaveRequest]:
        self._require_student(student_id)
        sid = int(student_id)
        out = [lv for lv in self._leaves.values() if lv.requester_role == Role.STUDENT and lv.requester_id == sid]
        out.sort(key=lambda l: (l.status.value, l.from_date, l.id))
        return out

    def admin_list_feedback(self, admin_id: int, pending_only: bool = False) -> List[Feedback]:
        self._require_admin(admin_id)
        out = list(self._feedback.values())
        if pending_only:
            out = [f for f in out if not f.is_replied]
        out.sort(key=lambda f: (f.is_replied, f.created_at, f.id))
        return out

    def admin_list_leave_requests(self, admin_id: int, status: Optional[LeaveStatus] = None) -> List[LeaveRequest]:
        self._require_admin(admin_id)
        out = list(self._leaves.values())
        if status is not None:
            out = [l for l in out if l.status == status]
        out.sort(key=lambda l: (l.status.value, l.from_date, l.id))
        return out

    def admin_overall_summary_charts(self, admin_id: int) -> SummaryCharts:
        self._require_admin(admin_id)
        leaves_total = len(self._leaves)
        leaves_pending = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.REJECTED)
        feedback_total = len(self._feedback)
        feedback_replied = sum(1 for f in self._feedback.values() if f.is_replied)
        feedback_pending = feedback_total - feedback_replied
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

    def staff_summary_charts(self, staff_id: int) -> StaffSummaryCharts:
        self._require_staff(staff_id)
        sid = int(staff_id)
        subjects = [s for s in self._subjects.values() if s.staff_id == sid]
        subject_ids: Set[int] = {s.id for s in subjects}
        course_ids: Set[int] = {s.course_id for s in subjects}
        students = [st for st in self._students.values() if st.course_id in course_ids]
        student_ids: Set[int] = {st.id for st in students}
        attendance_count = sum(1 for a in self._attendance.values() if a.subject_id in subject_ids and a.student_id in student_ids)
        results_count = sum(1 for r in self._results.values() if r.subject_id in subject_ids and r.student_id in student_ids)
        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == sid]
        leaves_total = len(leaves)
        leaves_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)
        feedback = [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == sid]
        feedback_total = len(feedback)
        feedback_replied = sum(1 for f in feedback if f.is_replied)
        feedback_pending = feedback_total - feedback_replied
        return StaffSummaryCharts(
            staff_id=sid,
            subjects_count=len(subjects),
            students_count=len(students),
            attendance_records_count=attendance_count,
            results_count=results_count,
            leaves_total=leaves_total,
            leaves_pending=leaves_pending,
            leaves_approved=leaves_approved,
            leaves_rejected=leaves_rejected,
            feedback_total=feedback_total,
            feedback_pending=feedback_pending,
            feedback_replied=feedback_replied,
        )

    def student_summary_charts(self, student_id: int) -> StudentSummaryCharts:
        student = self._require_student(student_id)
        sid = int(student.id)
        subjects = [s for s in self._subjects.values() if s.course_id == student.course_id]
        subject_ids: Set[int] = {s.id for s in subjects}
        attendance = [a for a in self._attendance.values() if a.student_id == sid and a.subject_id in subject_ids]
        attendance_total = len(attendance)
        attendance_present = sum(1 for a in attendance if a.status == AttendanceStatus.PRESENT)
        attendance_absent = attendance_total - attendance_present
        results_count = sum(1 for r in self._results.values() if r.student_id == sid and r.subject_id in subject_ids)
        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == sid]
        leaves_total = len(leaves)
        leaves_pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        leaves_approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        leaves_rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)
        feedback = [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == sid]
        feedback_total = len(feedback)
        feedback_replied = sum(1 for f in feedback if f.is_replied)
        feedback_pending = feedback_total - feedback_replied
        return StudentSummaryCharts(
            student_id=sid,
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

    def list_students(self) -> List[Student]:
        out = list(self._students.values())
        out.sort(key=lambda s: s.id)
        return out

    def list_staff(self) -> List[Staff]:
        out = list(self._staff.values())
        out.sort(key=lambda s: s.id)
        return out

    def list_courses(self) -> List[Course]:
        out = list(self._courses.values())
        out.sort(key=lambda c: c.id)
        return out

    def list_subjects(self) -> List[Subject]:
        out = list(self._subjects.values())
        out.sort(key=lambda s: s.id)
        return out

    def list_sessions(self) -> List[Session]:
        out = list(self._sessions.values())
        out.sort(key=lambda s: s.id)
        return out