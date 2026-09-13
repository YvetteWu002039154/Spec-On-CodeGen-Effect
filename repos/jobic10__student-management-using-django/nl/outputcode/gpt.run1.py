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
    feedback_replied: int


class User:
    def __init__(self, user_id: int, name: str, role: Role) -> None:
        if not name or not name.strip():
            raise ValueError("name must be non-empty")
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
    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id, name, Role.STUDENT)


class Course:
    def __init__(self, course_id: int, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("course name must be non-empty")
        self._id = int(course_id)
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


class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if not name or not name.strip():
            raise ValueError("subject name must be non-empty")
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

    def update(self, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        if name is not None:
            if not name or not name.strip():
                raise ValueError("subject name must be non-empty")
            self._name = name.strip()
        if course_id is not None:
            self._course_id = int(course_id)
        if staff_id is not None:
            self._staff_id = int(staff_id)


class Session:
    def __init__(self, session_id: int, name: str, start_date: date, end_date: date) -> None:
        if not name or not name.strip():
            raise ValueError("session name must be non-empty")
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")
        self._id = int(session_id)
        self._name = name.strip()
        self._start_date = start_date
        self._end_date = end_date

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date:
        return self._end_date

    def update(self, name: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> None:
        new_name = self._name if name is None else name.strip()
        if not new_name:
            raise ValueError("session name must be non-empty")
        new_start = self._start_date if start_date is None else start_date
        new_end = self._end_date if end_date is None else end_date
        if new_end < new_start:
            raise ValueError("end_date must be >= start_date")
        self._name = new_name
        self._start_date = new_start
        self._end_date = new_end


class Enrollment:
    def __init__(self, student_id: int, course_id: int, session_id: int) -> None:
        self._student_id = int(student_id)
        self._course_id = int(course_id)
        self._session_id = int(session_id)

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def course_id(self) -> int:
        return self._course_id

    @property
    def session_id(self) -> int:
        return self._session_id


class AttendanceRecord:
    def __init__(self, record_id: int, student_id: int, subject_id: int, session_id: int, on_date: date, present: bool, taken_by_staff_id: int) -> None:
        self._id = int(record_id)
        self._student_id = int(student_id)
        self._subject_id = int(subject_id)
        self._session_id = int(session_id)
        self._date = on_date
        self._present = bool(present)
        self._taken_by_staff_id = int(taken_by_staff_id)
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
    def session_id(self) -> int:
        return self._session_id

    @property
    def date(self) -> date:
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

    def update(self, present: bool, updated_by_staff_id: int) -> None:
        self._present = bool(present)
        self._taken_by_staff_id = int(updated_by_staff_id)
        self._updated_at = datetime.utcnow()


class ResultRecord:
    def __init__(self, result_id: int, student_id: int, subject_id: int, session_id: int, score: float, added_by_staff_id: int) -> None:
        self._id = int(result_id)
        self._student_id = int(student_id)
        self._subject_id = int(subject_id)
        self._session_id = int(session_id)
        self._score = float(score)
        self._added_by_staff_id = int(added_by_staff_id)
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
    def session_id(self) -> int:
        return self._session_id

    @property
    def score(self) -> float:
        return self._score

    @property
    def added_by_staff_id(self) -> int:
        return self._added_by_staff_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(self, score: float, updated_by_staff_id: int) -> None:
        self._score = float(score)
        self._added_by_staff_id = int(updated_by_staff_id)
        self._updated_at = datetime.utcnow()


class Feedback:
    def __init__(self, feedback_id: int, from_role: Role, from_user_id: int, message: str) -> None:
        if not message or not message.strip():
            raise ValueError("feedback message must be non-empty")
        self._id = int(feedback_id)
        self._from_role = from_role
        self._from_user_id = int(from_user_id)
        self._message = message.strip()
        self._created_at = datetime.utcnow()
        self._reply: Optional[str] = None
        self._replied_at: Optional[datetime] = None
        self._replied_by_admin_id: Optional[int] = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def from_role(self) -> Role:
        return self._from_role

    @property
    def from_user_id(self) -> int:
        return self._from_user_id

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
        if not reply or not reply.strip():
            raise ValueError("reply must be non-empty")
        self._reply = reply.strip()
        self._replied_at = datetime.utcnow()
        self._replied_by_admin_id = int(admin_id)


class LeaveRequest:
    def __init__(self, leave_id: int, from_role: Role, from_user_id: int, start_date: date, end_date: date, reason: str) -> None:
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")
        if not reason or not reason.strip():
            raise ValueError("reason must be non-empty")
        self._id = int(leave_id)
        self._from_role = from_role
        self._from_user_id = int(from_user_id)
        self._start_date = start_date
        self._end_date = end_date
        self._reason = reason.strip()
        self._status = LeaveStatus.PENDING
        self._created_at = datetime.utcnow()
        self._reviewed_at: Optional[datetime] = None
        self._reviewed_by_admin_id: Optional[int] = None
        self._review_note: Optional[str] = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def from_role(self) -> Role:
        return self._from_role

    @property
    def from_user_id(self) -> int:
        return self._from_user_id

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date:
        return self._end_date

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

    @property
    def review_note(self) -> Optional[str]:
        return self._review_note

    def review(self, admin_id: int, approve: bool, note: Optional[str] = None) -> None:
        if self._status != LeaveStatus.PENDING:
            raise ValueError("leave request already reviewed")
        self._status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        self._reviewed_at = datetime.utcnow()
        self._reviewed_by_admin_id = int(admin_id)
        if note is not None:
            self._review_note = note.strip() if note.strip() else None


class StudentManagementSystem:
    def __init__(self) -> None:
        self._admins: Dict[int, Admin] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}

        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}

        self._enrollments: Dict[int, Enrollment] = {}

        self._attendance: Dict[int, AttendanceRecord] = {}
        self._attendance_index: Dict[Tuple[int, int, int, date], int] = {}

        self._results: Dict[int, ResultRecord] = {}
        self._results_index: Dict[Tuple[int, int, int], int] = {}

        self._feedback: Dict[int, Feedback] = {}
        self._leave: Dict[int, LeaveRequest] = {}

        self._next_admin_id = 1
        self._next_staff_id = 1
        self._next_student_id = 1
        self._next_course_id = 1
        self._next_subject_id = 1
        self._next_session_id = 1
        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_feedback_id = 1
        self._next_leave_id = 1

    def _require_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(int(admin_id))
        if admin is None:
            raise KeyError("admin not found")
        return admin

    def _require_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(int(staff_id))
        if staff is None:
            raise KeyError("staff not found")
        return staff

    def _require_student(self, student_id: int) -> Student:
        student = self._students.get(int(student_id))
        if student is None:
            raise KeyError("student not found")
        return student

    def _require_course(self, course_id: int) -> Course:
        course = self._courses.get(int(course_id))
        if course is None:
            raise KeyError("course not found")
        return course

    def _require_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(int(subject_id))
        if subject is None:
            raise KeyError("subject not found")
        return subject

    def _require_session(self, session_id: int) -> Session:
        session = self._sessions.get(int(session_id))
        if session is None:
            raise KeyError("session not found")
        return session

    def _require_enrollment(self, student_id: int) -> Enrollment:
        enr = self._enrollments.get(int(student_id))
        if enr is None:
            raise KeyError("student not enrolled")
        return enr

    def _ensure_subject_in_student_course(self, student_id: int, subject_id: int) -> None:
        enr = self._require_enrollment(student_id)
        subj = self._require_subject(subject_id)
        if subj.course_id != enr.course_id:
            raise ValueError("subject not in student's course")

    def _ensure_subject_staff(self, staff_id: int, subject_id: int) -> None:
        subj = self._require_subject(subject_id)
        if subj.staff_id != int(staff_id):
            raise PermissionError("staff not assigned to subject")

    def create_admin(self, name: str) -> Admin:
        admin = Admin(self._next_admin_id, name)
        self._admins[admin.id] = admin
        self._next_admin_id += 1
        return admin

    def create_staff(self, admin_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        staff = Staff(self._next_staff_id, name)
        self._staff[staff.id] = staff
        self._next_staff_id += 1
        return staff

    def update_staff(self, admin_id: int, staff_id: int, name: str) -> None:
        self._require_admin(admin_id)
        staff = self._require_staff(staff_id)
        if not name or not name.strip():
            raise ValueError("name must be non-empty")
        staff._name = name.strip()

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        staff_id = int(staff_id)
        if staff_id not in self._staff:
            raise KeyError("staff not found")
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValueError("cannot delete staff assigned to a subject")
        del self._staff[staff_id]

    def create_student(self, admin_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_session(session_id)
        student = Student(self._next_student_id, name)
        self._students[student.id] = student
        self._enrollments[student.id] = Enrollment(student.id, int(course_id), int(session_id))
        self._next_student_id += 1
        return student

    def update_student(self, admin_id: int, student_id: int, name: Optional[str] = None, course_id: Optional[int] = None, session_id: Optional[int] = None) -> None:
        self._require_admin(admin_id)
        student = self._require_student(student_id)
        if name is not None:
            if not name or not name.strip():
                raise ValueError("name must be non-empty")
            student._name = name.strip()
        if course_id is not None or session_id is not None:
            enr = self._require_enrollment(student_id)
            new_course_id = enr.course_id if course_id is None else int(course_id)
            new_session_id = enr.session_id if session_id is None else int(session_id)
            self._require_course(new_course_id)
            self._require_session(new_session_id)
            self._enrollments[student.id] = Enrollment(student.id, new_course_id, new_session_id)

    def delete_student(self, admin_id: int, student_id: int) -> None:
        self._require_admin(admin_id)
        student_id = int(student_id)
        if student_id not in self._students:
            raise KeyError("student not found")
        attendance_ids = [rid for rid, rec in self._attendance.items() if rec.student_id == student_id]
        for rid in attendance_ids:
            rec = self._attendance[rid]
            key = (rec.student_id, rec.subject_id, rec.session_id, rec.date)
            self._attendance_index.pop(key, None)
            del self._attendance[rid]
        result_ids = [rid for rid, rec in self._results.items() if rec.student_id == student_id]
        for rid in result_ids:
            rec = self._results[rid]
            key = (rec.student_id, rec.subject_id, rec.session_id)
            self._results_index.pop(key, None)
            del self._results[rid]
        del self._students[student_id]
        self._enrollments.pop(student_id, None)

    def create_course(self, admin_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        course = Course(self._next_course_id, name)
        self._courses[course.id] = course
        self._next_course_id += 1
        return course

    def update_course(self, admin_id: int, course_id: int, name: str) -> None:
        self._require_admin(admin_id)
        course = self._require_course(course_id)
        course.update(name)

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        course_id = int(course_id)
        if course_id not in self._courses:
            raise KeyError("course not found")
        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValueError("cannot delete course with subjects")
        for enr in self._enrollments.values():
            if enr.course_id == course_id:
                raise ValueError("cannot delete course with enrolled students")
        del self._courses[course_id]

    def create_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_staff(staff_id)
        subject = Subject(self._next_subject_id, name, int(course_id), int(staff_id))
        self._subjects[subject.id] = subject
        self._next_subject_id += 1
        return subject

    def update_subject(self, admin_id: int, subject_id: int, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        self._require_admin(admin_id)
        subject = self._require_subject(subject_id)
        if course_id is not None:
            self._require_course(course_id)
        if staff_id is not None:
            self._require_staff(staff_id)
        subject.update(name=name, course_id=course_id, staff_id=staff_id)

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        subject_id = int(subject_id)
        if subject_id not in self._subjects:
            raise KeyError("subject not found")
        for rec in self._attendance.values():
            if rec.subject_id == subject_id:
                raise ValueError("cannot delete subject with attendance records")
        for rec in self._results.values():
            if rec.subject_id == subject_id:
                raise ValueError("cannot delete subject with result records")
        del self._subjects[subject_id]

    def create_session(self, admin_id: int, name: str, start_date: date, end_date: date) -> Session:
        self._require_admin(admin_id)
        session = Session(self._next_session_id, name, start_date, end_date)
        self._sessions[session.id] = session
        self._next_session_id += 1
        return session

    def update_session(self, admin_id: int, session_id: int, name: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> None:
        self._require_admin(admin_id)
        session = self._require_session(session_id)
        session.update(name=name, start_date=start_date, end_date=end_date)

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        session_id = int(session_id)
        if session_id not in self._sessions:
            raise KeyError("session not found")
        for enr in self._enrollments.values():
            if enr.session_id == session_id:
                raise ValueError("cannot delete session with enrolled students")
        for rec in self._attendance.values():
            if rec.session_id == session_id:
                raise ValueError("cannot delete session with attendance records")
        for rec in self._results.values():
            if rec.session_id == session_id:
                raise ValueError("cannot delete session with result records")
        del self._sessions[session_id]

    def take_or_update_attendance(self, staff_id: int, student_id: int, subject_id: int, on_date: date, present: bool) -> AttendanceRecord:
        self._require_staff(staff_id)
        self._require_student(student_id)
        self._require_subject(subject_id)
        self._ensure_subject_staff(staff_id, subject_id)
        self._ensure_subject_in_student_course(student_id, subject_id)
        enr = self._require_enrollment(student_id)
        self._require_session(enr.session_id)

        key = (int(student_id), int(subject_id), int(enr.session_id), on_date)
        existing_id = self._attendance_index.get(key)
        if existing_id is not None:
            rec = self._attendance[existing_id]
            rec.update(present=present, updated_by_staff_id=int(staff_id))
            return rec

        rec = AttendanceRecord(
            self._next_attendance_id,
            int(student_id),
            int(subject_id),
            int(enr.session_id),
            on_date,
            bool(present),
            int(staff_id),
        )
        self._attendance[rec.id] = rec
        self._attendance_index[key] = rec.id
        self._next_attendance_id += 1
        return rec

    def view_student_attendance(self, requester_role: Role, requester_id: int, student_id: int) -> List[AttendanceRecord]:
        if requester_role == Role.ADMIN:
            self._require_admin(requester_id)
        elif requester_role == Role.STAFF:
            self._require_staff(requester_id)
        elif requester_role == Role.STUDENT:
            self._require_student(requester_id)
            if int(requester_id) != int(student_id):
                raise PermissionError("students can only view their own attendance")
        else:
            raise ValueError("invalid role")

        self._require_student(student_id)
        return sorted(
            [rec for rec in self._attendance.values() if rec.student_id == int(student_id)],
            key=lambda r: (r.date, r.subject_id, r.id),
        )

    def add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, score: float) -> ResultRecord:
        self._require_staff(staff_id)
        self._require_student(student_id)
        self._require_subject(subject_id)
        self._ensure_subject_staff(staff_id, subject_id)
        self._ensure_subject_in_student_course(student_id, subject_id)
        enr = self._require_enrollment(student_id)
        self._require_session(enr.session_id)

        key = (int(student_id), int(subject_id), int(enr.session_id))
        existing_id = self._results_index.get(key)
        if existing_id is not None:
            rec = self._results[existing_id]
            rec.update(score=float(score), updated_by_staff_id=int(staff_id))
            return rec

        rec = ResultRecord(
            self._next_result_id,
            int(student_id),
            int(subject_id),
            int(enr.session_id),
            float(score),
            int(staff_id),
        )
        self._results[rec.id] = rec
        self._results_index[key] = rec.id
        self._next_result_id += 1
        return rec

    def view_student_results(self, requester_role: Role, requester_id: int, student_id: int) -> List[ResultRecord]:
        if requester_role == Role.ADMIN:
            self._require_admin(requester_id)
        elif requester_role == Role.STAFF:
            self._require_staff(requester_id)
        elif requester_role == Role.STUDENT:
            self._require_student(requester_id)
            if int(requester_id) != int(student_id):
                raise PermissionError("students can only view their own results")
        else:
            raise ValueError("invalid role")

        self._require_student(student_id)
        return sorted(
            [rec for rec in self._results.values() if rec.student_id == int(student_id)],
            key=lambda r: (r.subject_id, r.id),
        )

    def apply_leave(self, from_role: Role, from_user_id: int, start_date: date, end_date: date, reason: str) -> LeaveRequest:
        if from_role == Role.STAFF:
            self._require_staff(from_user_id)
        elif from_role == Role.STUDENT:
            self._require_student(from_user_id)
        else:
            raise ValueError("only staff or students can apply for leave")
        leave = LeaveRequest(self._next_leave_id, from_role, int(from_user_id), start_date, end_date, reason)
        self._leave[leave.id] = leave
        self._next_leave_id += 1
        return leave

    def review_leave(self, admin_id: int, leave_id: int, approve: bool, note: Optional[str] = None) -> None:
        self._require_admin(admin_id)
        leave = self._leave.get(int(leave_id))
        if leave is None:
            raise KeyError("leave request not found")
        leave.review(int(admin_id), bool(approve), note=note)

    def send_feedback(self, from_role: Role, from_user_id: int, message: str) -> Feedback:
        if from_role == Role.STAFF:
            self._require_staff(from_user_id)
        elif from_role == Role.STUDENT:
            self._require_student(from_user_id)
        else:
            raise ValueError("only staff or students can send feedback")
        fb = Feedback(self._next_feedback_id, from_role, int(from_user_id), message)
        self._feedback[fb.id] = fb
        self._next_feedback_id += 1
        return fb

    def reply_feedback(self, admin_id: int, feedback_id: int, reply: str) -> None:
        self._require_admin(admin_id)
        fb = self._feedback.get(int(feedback_id))
        if fb is None:
            raise KeyError("feedback not found")
        fb.reply_by_admin(int(admin_id), reply)

    def list_feedback(self, admin_id: int) -> List[Feedback]:
        self._require_admin(admin_id)
        return sorted(self._feedback.values(), key=lambda f: (f.created_at, f.id))

    def list_leave_requests(self, admin_id: int) -> List[LeaveRequest]:
        self._require_admin(admin_id)
        return sorted(self._leave.values(), key=lambda l: (l.created_at, l.id))

    def get_admin_summary(self, admin_id: int) -> Summary:
        self._require_admin(admin_id)
        leave_total = len(self._leave)
        leave_pending = sum(1 for l in self._leave.values() if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leave.values() if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leave.values() if l.status == LeaveStatus.REJECTED)
        feedback_total = len(self._feedback)
        feedback_replied = sum(1 for f in self._feedback.values() if f.reply is not None)
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
            feedback_replied=feedback_replied,
        )

    def get_staff_summary(self, staff_id: int) -> Summary:
        self._require_staff(staff_id)
        staff_subject_ids: Set[int] = {s.id for s in self._subjects.values() if s.staff_id == int(staff_id)}
        attendance_count = sum(1 for a in self._attendance.values() if a.subject_id in staff_subject_ids)
        results_count = sum(1 for r in self._results.values() if r.subject_id in staff_subject_ids)
        leave_total = sum(1 for l in self._leave.values() if l.from_role == Role.STAFF and l.from_user_id == int(staff_id))
        leave_pending = sum(1 for l in self._leave.values() if l.from_role == Role.STAFF and l.from_user_id == int(staff_id) and l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leave.values() if l.from_role == Role.STAFF and l.from_user_id == int(staff_id) and l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leave.values() if l.from_role == Role.STAFF and l.from_user_id == int(staff_id) and l.status == LeaveStatus.REJECTED)
        feedback_total = sum(1 for f in self._feedback.values() if f.from_role == Role.STAFF and f.from_user_id == int(staff_id))
        feedback_replied = sum(1 for f in self._feedback.values() if f.from_role == Role.STAFF and f.from_user_id == int(staff_id) and f.reply is not None)
        return Summary(
            students_count=len(self._students),
            staff_count=len(self._staff),
            courses_count=len(self._courses),
            subjects_count=len(staff_subject_ids),
            sessions_count=len(self._sessions),
            attendance_records_count=attendance_count,
            results_count=results_count,
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_total=feedback_total,
            feedback_replied=feedback_replied,
        )

    def get_student_summary(self, student_id: int) -> Summary:
        self._require_student(student_id)
        attendance_count = sum(1 for a in self._attendance.values() if a.student_id == int(student_id))
        results_count = sum(1 for r in self._results.values() if r.student_id == int(student_id))
        leave_total = sum(1 for l in self._leave.values() if l.from_role == Role.STUDENT and l.from_user_id == int(student_id))
        leave_pending = sum(1 for l in self._leave.values() if l.from_role == Role.STUDENT and l.from_user_id == int(student_id) and l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leave.values() if l.from_role == Role.STUDENT and l.from_user_id == int(student_id) and l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leave.values() if l.from_role == Role.STUDENT and l.from_user_id == int(student_id) and l.status == LeaveStatus.REJECTED)
        feedback_total = sum(1 for f in self._feedback.values() if f.from_role == Role.STUDENT and f.from_user_id == int(student_id))
        feedback_replied = sum(1 for f in self._feedback.values() if f.from_role == Role.STUDENT and f.from_user_id == int(student_id) and f.reply is not None)
        enr = self._enrollments.get(int(student_id))
        subjects_count = 0
        if enr is not None:
            subjects_count = sum(1 for s in self._subjects.values() if s.course_id == enr.course_id)
        return Summary(
            students_count=len(self._students),
            staff_count=len(self._staff),
            courses_count=len(self._courses),
            subjects_count=subjects_count,
            sessions_count=len(self._sessions),
            attendance_records_count=attendance_count,
            results_count=results_count,
            leave_total=leave_total,
            leave_pending=leave_pending,
            leave_approved=leave_approved,
            leave_rejected=leave_rejected,
            feedback_total=feedback_total,
            feedback_replied=feedback_replied,
        )