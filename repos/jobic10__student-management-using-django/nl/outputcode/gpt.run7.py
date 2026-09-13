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


class ValidationError(ValueError):
    pass


class NotFoundError(KeyError):
    pass


class PermissionError(RuntimeError):
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
    total_marked: int
    present: int
    absent: int

    @property
    def present_percentage(self) -> float:
        if self.total_marked == 0:
            return 0.0
        return (self.present / self.total_marked) * 100.0


@dataclass
class Course:
    id: int
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Course name cannot be empty.")
        self.name = self.name.strip()


@dataclass
class Session:
    id: int
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Session name cannot be empty.")
        self.name = self.name.strip()


@dataclass
class Subject:
    id: int
    name: str
    course_id: int
    staff_id: int

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Subject name cannot be empty.")
        self.name = self.name.strip()


@dataclass
class User:
    id: int
    name: str
    role: Role

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("User name cannot be empty.")
        self.name = self.name.strip()


@dataclass
class Staff(User):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id, name=name, role=Role.STAFF)


@dataclass
class Student(User):
    course_id: int
    session_id: int

    def __init__(self, id: int, name: str, course_id: int, session_id: int) -> None:
        super().__init__(id=id, name=name, role=Role.STUDENT)
        self.course_id = course_id
        self.session_id = session_id


@dataclass
class Admin(User):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id, name=name, role=Role.ADMIN)


@dataclass
class AttendanceRecord:
    id: int
    student_id: int
    subject_id: int
    on_date: date
    present: bool
    marked_by_staff_id: int
    updated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.on_date, date):
            raise ValidationError("on_date must be a date.")
        if not isinstance(self.updated_at, datetime):
            raise ValidationError("updated_at must be a datetime.")


@dataclass
class ResultRecord:
    id: int
    student_id: int
    subject_id: int
    score: float
    updated_by_staff_id: int
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.score < 0:
            raise ValidationError("Score cannot be negative.")
        if not isinstance(self.updated_at, datetime):
            raise ValidationError("updated_at must be a datetime.")


@dataclass
class LeaveRequest:
    id: int
    requester_role: Role
    requester_id: int
    from_date: date
    to_date: date
    reason: str
    status: LeaveStatus
    reviewed_by_admin_id: Optional[int]
    reviewed_at: Optional[datetime]

    def __post_init__(self) -> None:
        if self.requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("Leave requester must be staff or student.")
        if self.from_date > self.to_date:
            raise ValidationError("from_date cannot be after to_date.")
        if not self.reason or not self.reason.strip():
            raise ValidationError("Leave reason cannot be empty.")
        self.reason = self.reason.strip()


@dataclass
class Feedback:
    id: int
    sender_role: Role
    sender_id: int
    message: str
    status: FeedbackStatus
    reply: Optional[str]
    replied_by_admin_id: Optional[int]
    created_at: datetime
    replied_at: Optional[datetime]

    def __post_init__(self) -> None:
        if self.sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValidationError("Feedback sender must be staff or student.")
        if not self.message or not self.message.strip():
            raise ValidationError("Feedback message cannot be empty.")
        self.message = self.message.strip()
        if not isinstance(self.created_at, datetime):
            raise ValidationError("created_at must be a datetime.")


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_id: Dict[str, int] = {
            "user": 1,
            "course": 1,
            "session": 1,
            "subject": 1,
            "attendance": 1,
            "result": 1,
            "leave": 1,
            "feedback": 1,
        }

        self._admins: Dict[int, Admin] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}

        self._courses: Dict[int, Course] = {}
        self._sessions: Dict[int, Session] = {}
        self._subjects: Dict[int, Subject] = {}

        self._attendance: Dict[int, AttendanceRecord] = {}
        self._attendance_index: Dict[Tuple[int, int, date], int] = {}

        self._results: Dict[int, ResultRecord] = {}
        self._results_index: Dict[Tuple[int, int], int] = {}

        self._leaves: Dict[int, LeaveRequest] = {}
        self._feedback: Dict[int, Feedback] = {}

    def _new_id(self, key: str) -> int:
        v = self._next_id[key]
        self._next_id[key] = v + 1
        return v

    def _require_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(admin_id)
        if not admin:
            raise PermissionError("Admin not found or not authorized.")
        return admin

    def _require_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(staff_id)
        if not staff:
            raise PermissionError("Staff not found or not authorized.")
        return staff

    def _require_student(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if not student:
            raise PermissionError("Student not found or not authorized.")
        return student

    def _require_course(self, course_id: int) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise NotFoundError("Course not found.")
        return course

    def _require_session(self, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise NotFoundError("Session not found.")
        return session

    def _require_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise NotFoundError("Subject not found.")
        return subject

    def create_admin(self, name: str) -> Admin:
        admin_id = self._new_id("user")
        admin = Admin(id=admin_id, name=name)
        self._admins[admin_id] = admin
        return admin

    def create_staff(self, admin_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        staff_id = self._new_id("user")
        staff = Staff(id=staff_id, name=name)
        self._staff[staff_id] = staff
        return staff

    def update_staff(self, admin_id: int, staff_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        staff = self._staff.get(staff_id)
        if not staff:
            raise NotFoundError("Staff not found.")
        if not name or not name.strip():
            raise ValidationError("Staff name cannot be empty.")
        staff.name = name.strip()
        return staff

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        if staff_id not in self._staff:
            raise NotFoundError("Staff not found.")
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValidationError("Cannot delete staff assigned to a subject.")
        del self._staff[staff_id]

    def create_course(self, admin_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        course_id = self._new_id("course")
        course = Course(id=course_id, name=name)
        self._courses[course_id] = course
        return course

    def update_course(self, admin_id: int, course_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        course = self._require_course(course_id)
        if not name or not name.strip():
            raise ValidationError("Course name cannot be empty.")
        course.name = name.strip()
        return course

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        self._require_course(course_id)
        for student in self._students.values():
            if student.course_id == course_id:
                raise ValidationError("Cannot delete course with enrolled students.")
        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValidationError("Cannot delete course with subjects.")
        del self._courses[course_id]

    def create_session(self, admin_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        session_id = self._new_id("session")
        session = Session(id=session_id, name=name)
        self._sessions[session_id] = session
        return session

    def update_session(self, admin_id: int, session_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        session = self._require_session(session_id)
        if not name or not name.strip():
            raise ValidationError("Session name cannot be empty.")
        session.name = name.strip()
        return session

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        self._require_session(session_id)
        for student in self._students.values():
            if student.session_id == session_id:
                raise ValidationError("Cannot delete session with enrolled students.")
        del self._sessions[session_id]

    def create_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_staff(staff_id)
        subject_id = self._new_id("subject")
        subject = Subject(id=subject_id, name=name, course_id=course_id, staff_id=staff_id)
        self._subjects[subject_id] = subject
        return subject

    def update_subject(
        self,
        admin_id: int,
        subject_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        staff_id: Optional[int] = None,
    ) -> Subject:
        self._require_admin(admin_id)
        subject = self._require_subject(subject_id)
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("Subject name cannot be empty.")
            subject.name = name.strip()
        if course_id is not None:
            self._require_course(course_id)
            subject.course_id = course_id
        if staff_id is not None:
            self._require_staff(staff_id)
            subject.staff_id = staff_id
        return subject

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        self._require_subject(subject_id)
        for rec in self._attendance.values():
            if rec.subject_id == subject_id:
                raise ValidationError("Cannot delete subject with attendance records.")
        for res in self._results.values():
            if res.subject_id == subject_id:
                raise ValidationError("Cannot delete subject with result records.")
        del self._subjects[subject_id]

    def create_student(self, admin_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin_id)
        self._require_course(course_id)
        self._require_session(session_id)
        student_id = self._new_id("user")
        student = Student(id=student_id, name=name, course_id=course_id, session_id=session_id)
        self._students[student_id] = student
        return student

    def update_student(
        self,
        admin_id: int,
        student_id: int,
        name: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> Student:
        self._require_admin(admin_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError("Student not found.")
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("Student name cannot be empty.")
            student.name = name.strip()
        if course_id is not None:
            self._require_course(course_id)
            student.course_id = course_id
        if session_id is not None:
            self._require_session(session_id)
            student.session_id = session_id
        return student

    def delete_student(self, admin_id: int, student_id: int) -> None:
        self._require_admin(admin_id)
        if student_id not in self._students:
            raise NotFoundError("Student not found.")
        attendance_ids = [aid for aid, rec in self._attendance.items() if rec.student_id == student_id]
        for aid in attendance_ids:
            rec = self._attendance[aid]
            self._attendance_index.pop((rec.student_id, rec.subject_id, rec.on_date), None)
            del self._attendance[aid]
        result_ids = [rid for rid, res in self._results.items() if res.student_id == student_id]
        for rid in result_ids:
            res = self._results[rid]
            self._results_index.pop((res.student_id, res.subject_id), None)
            del self._results[rid]
        del self._students[student_id]

    def view_student_attendance(self, admin_id: int, student_id: int, subject_id: Optional[int] = None) -> List[AttendanceRecord]:
        self._require_admin(admin_id)
        self._require_student(student_id)
        if subject_id is not None:
            self._require_subject(subject_id)
        records = [r for r in self._attendance.values() if r.student_id == student_id and (subject_id is None or r.subject_id == subject_id)]
        records.sort(key=lambda r: (r.on_date, r.subject_id, r.id))
        return records

    def review_leave(self, admin_id: int, leave_id: int, approve: bool) -> LeaveRequest:
        admin = self._require_admin(admin_id)
        leave = self._leaves.get(leave_id)
        if not leave:
            raise NotFoundError("Leave request not found.")
        if leave.status != LeaveStatus.PENDING:
            raise ValidationError("Leave request already reviewed.")
        leave.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        leave.reviewed_by_admin_id = admin.id
        leave.reviewed_at = datetime.utcnow()
        return leave

    def reply_feedback(self, admin_id: int, feedback_id: int, reply: str) -> Feedback:
        admin = self._require_admin(admin_id)
        fb = self._feedback.get(feedback_id)
        if not fb:
            raise NotFoundError("Feedback not found.")
        if not reply or not reply.strip():
            raise ValidationError("Reply cannot be empty.")
        fb.reply = reply.strip()
        fb.status = FeedbackStatus.REPLIED
        fb.replied_by_admin_id = admin.id
        fb.replied_at = datetime.utcnow()
        return fb

    def admin_summary_charts(self, admin_id: int) -> SummaryCharts:
        self._require_admin(admin_id)
        return self._summary_charts(
            student_filter=None,
            staff_filter=None,
            subject_filter=None,
        )

    def staff_summary_charts(self, staff_id: int) -> SummaryCharts:
        staff = self._require_staff(staff_id)
        subject_ids = {s.id for s in self._subjects.values() if s.staff_id == staff.id}
        return self._summary_charts(
            student_filter=None,
            staff_filter={staff.id},
            subject_filter=subject_ids,
        )

    def student_summary_charts(self, student_id: int) -> SummaryCharts:
        student = self._require_student(student_id)
        return self._summary_charts(
            student_filter={student.id},
            staff_filter=None,
            subject_filter=None,
        )

    def _summary_charts(
        self,
        student_filter: Optional[Set[int]],
        staff_filter: Optional[Set[int]],
        subject_filter: Optional[Set[int]],
    ) -> SummaryCharts:
        def _in_filter(value: int, flt: Optional[Set[int]]) -> bool:
            return True if flt is None else value in flt

        students_count = len(self._students) if student_filter is None else sum(1 for sid in self._students if sid in student_filter)
        staff_count = len(self._staff) if staff_filter is None else sum(1 for sid in self._staff if sid in staff_filter)
        courses_count = len(self._courses)
        subjects_count = len(self._subjects) if subject_filter is None else sum(1 for s in self._subjects.values() if s.id in subject_filter)
        sessions_count = len(self._sessions)

        attendance_records_count = 0
        for rec in self._attendance.values():
            if _in_filter(rec.student_id, student_filter) and _in_filter(rec.subject_id, subject_filter):
                attendance_records_count += 1

        results_count = 0
        for res in self._results.values():
            if _in_filter(res.student_id, student_filter) and _in_filter(res.subject_id, subject_filter):
                results_count += 1

        leaves_total = 0
        leaves_pending = 0
        leaves_approved = 0
        leaves_rejected = 0
        for lv in self._leaves.values():
            if lv.requester_role == Role.STAFF and staff_filter is not None and lv.requester_id not in staff_filter:
                continue
            if lv.requester_role == Role.STUDENT and student_filter is not None and lv.requester_id not in student_filter:
                continue
            leaves_total += 1
            if lv.status == LeaveStatus.PENDING:
                leaves_pending += 1
            elif lv.status == LeaveStatus.APPROVED:
                leaves_approved += 1
            else:
                leaves_rejected += 1

        feedback_total = 0
        feedback_pending = 0
        feedback_replied = 0
        for fb in self._feedback.values():
            if fb.sender_role == Role.STAFF and staff_filter is not None and fb.sender_id not in staff_filter:
                continue
            if fb.sender_role == Role.STUDENT and student_filter is not None and fb.sender_id not in student_filter:
                continue
            feedback_total += 1
            if fb.status == FeedbackStatus.PENDING:
                feedback_pending += 1
            else:
                feedback_replied += 1

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

    def take_or_update_attendance(
        self,
        staff_id: int,
        student_id: int,
        subject_id: int,
        on_date: date,
        present: bool,
    ) -> AttendanceRecord:
        staff = self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._require_subject(subject_id)
        if subject.staff_id != staff.id:
            raise PermissionError("Staff not assigned to this subject.")
        if student.course_id != subject.course_id:
            raise ValidationError("Student course does not match subject course.")
        key = (student_id, subject_id, on_date)
        now = datetime.utcnow()
        existing_id = self._attendance_index.get(key)
        if existing_id is not None:
            rec = self._attendance[existing_id]
            rec.present = bool(present)
            rec.marked_by_staff_id = staff.id
            rec.updated_at = now
            return rec
        attendance_id = self._new_id("attendance")
        rec = AttendanceRecord(
            id=attendance_id,
            student_id=student_id,
            subject_id=subject_id,
            on_date=on_date,
            present=bool(present),
            marked_by_staff_id=staff.id,
            updated_at=now,
        )
        self._attendance[attendance_id] = rec
        self._attendance_index[key] = attendance_id
        return rec

    def staff_view_attendance(self, staff_id: int, subject_id: int, on_date: Optional[date] = None) -> List[AttendanceRecord]:
        staff = self._require_staff(staff_id)
        subject = self._require_subject(subject_id)
        if subject.staff_id != staff.id:
            raise PermissionError("Staff not assigned to this subject.")
        records = [r for r in self._attendance.values() if r.subject_id == subject_id and (on_date is None or r.on_date == on_date)]
        records.sort(key=lambda r: (r.on_date, r.student_id, r.id))
        return records

    def add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, score: float) -> ResultRecord:
        staff = self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._require_subject(subject_id)
        if subject.staff_id != staff.id:
            raise PermissionError("Staff not assigned to this subject.")
        if student.course_id != subject.course_id:
            raise ValidationError("Student course does not match subject course.")
        if score < 0:
            raise ValidationError("Score cannot be negative.")
        key = (student_id, subject_id)
        now = datetime.utcnow()
        existing_id = self._results_index.get(key)
        if existing_id is not None:
            res = self._results[existing_id]
            res.score = float(score)
            res.updated_by_staff_id = staff.id
            res.updated_at = now
            return res
        result_id = self._new_id("result")
        res = ResultRecord(
            id=result_id,
            student_id=student_id,
            subject_id=subject_id,
            score=float(score),
            updated_by_staff_id=staff.id,
            updated_at=now,
        )
        self._results[result_id] = res
        self._results_index[key] = result_id
        return res

    def student_view_attendance(self, student_id: int, subject_id: Optional[int] = None) -> List[AttendanceRecord]:
        student = self._require_student(student_id)
        if subject_id is not None:
            subject = self._require_subject(subject_id)
            if subject.course_id != student.course_id:
                raise PermissionError("Subject not available for this student.")
        records = [r for r in self._attendance.values() if r.student_id == student.id and (subject_id is None or r.subject_id == subject_id)]
        records.sort(key=lambda r: (r.on_date, r.subject_id, r.id))
        return records

    def student_attendance_summary(self, student_id: int, subject_id: Optional[int] = None) -> AttendanceSummary:
        records = self.student_view_attendance(student_id=student_id, subject_id=subject_id)
        total = len(records)
        present = sum(1 for r in records if r.present)
        absent = total - present
        return AttendanceSummary(total_marked=total, present=present, absent=absent)

    def student_view_result(self, student_id: int, subject_id: Optional[int] = None) -> List[ResultRecord]:
        student = self._require_student(student_id)
        if subject_id is not None:
            subject = self._require_subject(subject_id)
            if subject.course_id != student.course_id:
                raise PermissionError("Subject not available for this student.")
        results = [r for r in self._results.values() if r.student_id == student.id and (subject_id is None or r.subject_id == subject_id)]
        results.sort(key=lambda r: (r.subject_id, r.id))
        return results

    def apply_leave_student(self, student_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        student = self._require_student(student_id)
        leave_id = self._new_id("leave")
        leave = LeaveRequest(
            id=leave_id,
            requester_role=Role.STUDENT,
            requester_id=student.id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            status=LeaveStatus.PENDING,
            reviewed_by_admin_id=None,
            reviewed_at=None,
        )
        self._leaves[leave_id] = leave
        return leave

    def apply_leave_staff(self, staff_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        staff = self._require_staff(staff_id)
        leave_id = self._new_id("leave")
        leave = LeaveRequest(
            id=leave_id,
            requester_role=Role.STAFF,
            requester_id=staff.id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            status=LeaveStatus.PENDING,
            reviewed_by_admin_id=None,
            reviewed_at=None,
        )
        self._leaves[leave_id] = leave
        return leave

    def list_leaves_for_admin(self, admin_id: int, status: Optional[LeaveStatus] = None) -> List[LeaveRequest]:
        self._require_admin(admin_id)
        leaves = list(self._leaves.values())
        if status is not None:
            leaves = [l for l in leaves if l.status == status]
        leaves.sort(key=lambda l: (l.status.value, l.id))
        return leaves

    def list_leaves_for_student(self, student_id: int) -> List[LeaveRequest]:
        student = self._require_student(student_id)
        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STUDENT and l.requester_id == student.id]
        leaves.sort(key=lambda l: (l.status.value, l.id))
        return leaves

    def list_leaves_for_staff(self, staff_id: int) -> List[LeaveRequest]:
        staff = self._require_staff(staff_id)
        leaves = [l for l in self._leaves.values() if l.requester_role == Role.STAFF and l.requester_id == staff.id]
        leaves.sort(key=lambda l: (l.status.value, l.id))
        return leaves

    def send_feedback_student(self, student_id: int, message: str) -> Feedback:
        student = self._require_student(student_id)
        feedback_id = self._new_id("feedback")
        fb = Feedback(
            id=feedback_id,
            sender_role=Role.STUDENT,
            sender_id=student.id,
            message=message,
            status=FeedbackStatus.PENDING,
            reply=None,
            replied_by_admin_id=None,
            created_at=datetime.utcnow(),
            replied_at=None,
        )
        self._feedback[feedback_id] = fb
        return fb

    def send_feedback_staff(self, staff_id: int, message: str) -> Feedback:
        staff = self._require_staff(staff_id)
        feedback_id = self._new_id("feedback")
        fb = Feedback(
            id=feedback_id,
            sender_role=Role.STAFF,
            sender_id=staff.id,
            message=message,
            status=FeedbackStatus.PENDING,
            reply=None,
            replied_by_admin_id=None,
            created_at=datetime.utcnow(),
            replied_at=None,
        )
        self._feedback[feedback_id] = fb
        return fb

    def list_feedback_for_admin(self, admin_id: int, status: Optional[FeedbackStatus] = None) -> List[Feedback]:
        self._require_admin(admin_id)
        items = list(self._feedback.values())
        if status is not None:
            items = [f for f in items if f.status == status]
        items.sort(key=lambda f: (f.status.value, f.id))
        return items

    def list_feedback_for_student(self, student_id: int) -> List[Feedback]:
        student = self._require_student(student_id)
        items = [f for f in self._feedback.values() if f.sender_role == Role.STUDENT and f.sender_id == student.id]
        items.sort(key=lambda f: (f.status.value, f.id))
        return items

    def list_feedback_for_staff(self, staff_id: int) -> List[Feedback]:
        staff = self._require_staff(staff_id)
        items = [f for f in self._feedback.values() if f.sender_role == Role.STAFF and f.sender_id == staff.id]
        items.sort(key=lambda f: (f.status.value, f.id))
        return items

    def list_courses(self) -> List[Course]:
        items = list(self._courses.values())
        items.sort(key=lambda c: c.id)
        return items

    def list_sessions(self) -> List[Session]:
        items = list(self._sessions.values())
        items.sort(key=lambda s: s.id)
        return items

    def list_subjects(self) -> List[Subject]:
        items = list(self._subjects.values())
        items.sort(key=lambda s: s.id)
        return items

    def list_students(self) -> List[Student]:
        items = list(self._students.values())
        items.sort(key=lambda s: s.id)
        return items

    def list_staff(self) -> List[Staff]:
        items = list(self._staff.values())
        items.sort(key=lambda s: s.id)
        return items