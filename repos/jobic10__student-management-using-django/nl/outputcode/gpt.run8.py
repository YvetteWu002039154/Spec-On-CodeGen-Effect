from __future__ import annotations

from dataclasses import dataclass, field
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


class ValidationError(ValueError):
    pass


class NotFoundError(KeyError):
    pass


class PermissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Session:
    id: int
    name: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Session name cannot be empty.")
        if self.end_date < self.start_date:
            raise ValidationError("Session end_date cannot be before start_date.")


@dataclass(frozen=True)
class Course:
    id: int
    name: str
    session_id: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Course name cannot be empty.")


@dataclass(frozen=True)
class Subject:
    id: int
    name: str
    course_id: int
    staff_id: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Subject name cannot be empty.")


@dataclass(frozen=True)
class User:
    id: int
    name: str
    role: Role

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("User name cannot be empty.")


@dataclass(frozen=True)
class Staff(User):
    def __post_init__(self) -> None:
        object.__setattr__(self, "role", Role.STAFF)
        super().__post_init__()


@dataclass(frozen=True)
class Student(User):
    course_id: int
    session_id: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", Role.STUDENT)
        super().__post_init__()


@dataclass(frozen=True)
class Admin(User):
    def __post_init__(self) -> None:
        object.__setattr__(self, "role", Role.ADMIN)
        super().__post_init__()


@dataclass
class Feedback:
    id: int
    from_role: Role
    from_user_id: int
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    reply: Optional[str] = None
    replied_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValidationError("Feedback message cannot be empty.")

    def set_reply(self, reply: str) -> None:
        if not reply.strip():
            raise ValidationError("Reply cannot be empty.")
        self.reply = reply
        self.replied_at = datetime.utcnow()


@dataclass
class LeaveRequest:
    id: int
    from_role: Role
    from_user_id: int
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus = LeaveStatus.PENDING
    reviewed_by_admin_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValidationError("Leave end_date cannot be before start_date.")
        if not self.reason.strip():
            raise ValidationError("Leave reason cannot be empty.")

    def review(self, admin_id: int, approve: bool, note: Optional[str] = None) -> None:
        if self.status != LeaveStatus.PENDING:
            raise ValidationError("Leave request has already been reviewed.")
        self.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        self.reviewed_by_admin_id = admin_id
        self.reviewed_at = datetime.utcnow()
        if note is not None:
            if not note.strip():
                raise ValidationError("Review note cannot be empty if provided.")
            self.review_note = note


@dataclass(frozen=True)
class AttendanceRecord:
    id: int
    student_id: int
    subject_id: int
    on_date: date
    status: AttendanceStatus
    taken_by_staff_id: int
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ResultRecord:
    id: int
    student_id: int
    subject_id: int
    score: float
    updated_by_staff_id: int
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.score < 0:
            raise ValidationError("Score cannot be negative.")


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_id: Dict[str, int] = {
            "session": 1,
            "course": 1,
            "subject": 1,
            "staff": 1,
            "student": 1,
            "admin": 1,
            "feedback": 1,
            "leave": 1,
            "attendance": 1,
            "result": 1,
        }

        self._sessions: Dict[int, Session] = {}
        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}
        self._admins: Dict[int, Admin] = {}

        self._feedback: Dict[int, Feedback] = {}
        self._leaves: Dict[int, LeaveRequest] = {}

        self._attendance: Dict[int, AttendanceRecord] = {}
        self._attendance_index: Dict[Tuple[int, int, date], int] = {}

        self._results: Dict[int, ResultRecord] = {}
        self._result_index: Dict[Tuple[int, int], int] = {}

    def _new_id(self, key: str) -> int:
        v = self._next_id[key]
        self._next_id[key] = v + 1
        return v

    @staticmethod
    def _require_admin(user: User) -> None:
        if user.role != Role.ADMIN:
            raise PermissionError("Admin privileges required.")

    @staticmethod
    def _require_staff(user: User) -> None:
        if user.role != Role.STAFF:
            raise PermissionError("Staff privileges required.")

    @staticmethod
    def _require_student(user: User) -> None:
        if user.role != Role.STUDENT:
            raise PermissionError("Student privileges required.")

    def _get_admin(self, admin_id: int) -> Admin:
        try:
            return self._admins[admin_id]
        except KeyError as e:
            raise NotFoundError("Admin not found.") from e

    def _get_staff(self, staff_id: int) -> Staff:
        try:
            return self._staff[staff_id]
        except KeyError as e:
            raise NotFoundError("Staff not found.") from e

    def _get_student(self, student_id: int) -> Student:
        try:
            return self._students[student_id]
        except KeyError as e:
            raise NotFoundError("Student not found.") from e

    def _get_session(self, session_id: int) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as e:
            raise NotFoundError("Session not found.") from e

    def _get_course(self, course_id: int) -> Course:
        try:
            return self._courses[course_id]
        except KeyError as e:
            raise NotFoundError("Course not found.") from e

    def _get_subject(self, subject_id: int) -> Subject:
        try:
            return self._subjects[subject_id]
        except KeyError as e:
            raise NotFoundError("Subject not found.") from e

    def add_admin(self, name: str) -> Admin:
        admin = Admin(id=self._new_id("admin"), name=name, role=Role.ADMIN)
        self._admins[admin.id] = admin
        return admin

    def add_staff(self, admin: Admin, name: str) -> Staff:
        self._require_admin(admin)
        staff = Staff(id=self._new_id("staff"), name=name, role=Role.STAFF)
        self._staff[staff.id] = staff
        return staff

    def update_staff(self, admin: Admin, staff_id: int, name: str) -> Staff:
        self._require_admin(admin)
        self._get_staff(staff_id)
        if not name.strip():
            raise ValidationError("Staff name cannot be empty.")
        staff = Staff(id=staff_id, name=name, role=Role.STAFF)
        self._staff[staff_id] = staff
        return staff

    def delete_staff(self, admin: Admin, staff_id: int) -> None:
        self._require_admin(admin)
        self._get_staff(staff_id)

        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValidationError("Cannot delete staff assigned to a subject.")

        del self._staff[staff_id]

    def add_session(self, admin: Admin, name: str, start_date: date, end_date: date) -> Session:
        self._require_admin(admin)
        session = Session(id=self._new_id("session"), name=name, start_date=start_date, end_date=end_date)
        self._sessions[session.id] = session
        return session

    def update_session(self, admin: Admin, session_id: int, name: str, start_date: date, end_date: date) -> Session:
        self._require_admin(admin)
        self._get_session(session_id)
        session = Session(id=session_id, name=name, start_date=start_date, end_date=end_date)
        self._sessions[session_id] = session
        return session

    def delete_session(self, admin: Admin, session_id: int) -> None:
        self._require_admin(admin)
        self._get_session(session_id)

        for course in self._courses.values():
            if course.session_id == session_id:
                raise ValidationError("Cannot delete session with courses.")
        for student in self._students.values():
            if student.session_id == session_id:
                raise ValidationError("Cannot delete session with students.")

        del self._sessions[session_id]

    def add_course(self, admin: Admin, name: str, session_id: int) -> Course:
        self._require_admin(admin)
        self._get_session(session_id)
        course = Course(id=self._new_id("course"), name=name, session_id=session_id)
        self._courses[course.id] = course
        return course

    def update_course(self, admin: Admin, course_id: int, name: str, session_id: int) -> Course:
        self._require_admin(admin)
        self._get_course(course_id)
        self._get_session(session_id)
        course = Course(id=course_id, name=name, session_id=session_id)
        self._courses[course_id] = course
        return course

    def delete_course(self, admin: Admin, course_id: int) -> None:
        self._require_admin(admin)
        self._get_course(course_id)

        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValidationError("Cannot delete course with subjects.")
        for student in self._students.values():
            if student.course_id == course_id:
                raise ValidationError("Cannot delete course with students.")

        del self._courses[course_id]

    def add_subject(self, admin: Admin, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin)
        self._get_course(course_id)
        self._get_staff(staff_id)
        subject = Subject(id=self._new_id("subject"), name=name, course_id=course_id, staff_id=staff_id)
        self._subjects[subject.id] = subject
        return subject

    def update_subject(self, admin: Admin, subject_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin)
        self._get_subject(subject_id)
        self._get_course(course_id)
        self._get_staff(staff_id)
        subject = Subject(id=subject_id, name=name, course_id=course_id, staff_id=staff_id)
        self._subjects[subject_id] = subject
        return subject

    def delete_subject(self, admin: Admin, subject_id: int) -> None:
        self._require_admin(admin)
        self._get_subject(subject_id)

        for key, att_id in list(self._attendance_index.items()):
            _student_id, subj_id, _d = key
            if subj_id == subject_id:
                del self._attendance[att_id]
                del self._attendance_index[key]

        for key, res_id in list(self._result_index.items()):
            _student_id, subj_id = key
            if subj_id == subject_id:
                del self._results[res_id]
                del self._result_index[key]

        del self._subjects[subject_id]

    def add_student(self, admin: Admin, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin)
        self._get_course(course_id)
        self._get_session(session_id)
        student = Student(id=self._new_id("student"), name=name, role=Role.STUDENT, course_id=course_id, session_id=session_id)
        self._students[student.id] = student
        return student

    def update_student(self, admin: Admin, student_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin)
        self._get_student(student_id)
        self._get_course(course_id)
        self._get_session(session_id)
        student = Student(id=student_id, name=name, role=Role.STUDENT, course_id=course_id, session_id=session_id)
        self._students[student_id] = student
        return student

    def delete_student(self, admin: Admin, student_id: int) -> None:
        self._require_admin(admin)
        self._get_student(student_id)

        for key, att_id in list(self._attendance_index.items()):
            stu_id, _subj_id, _d = key
            if stu_id == student_id:
                del self._attendance[att_id]
                del self._attendance_index[key]

        for key, res_id in list(self._result_index.items()):
            stu_id, _subj_id = key
            if stu_id == student_id:
                del self._results[res_id]
                del self._result_index[key]

        del self._students[student_id]

    def staff_take_or_update_attendance(
        self,
        staff: Staff,
        student_id: int,
        subject_id: int,
        on_date: date,
        status: AttendanceStatus,
    ) -> AttendanceRecord:
        self._require_staff(staff)
        student = self._get_student(student_id)
        subject = self._get_subject(subject_id)

        if subject.staff_id != staff.id:
            raise PermissionError("Staff can only take attendance for their own subjects.")
        if subject.course_id != student.course_id:
            raise ValidationError("Subject course does not match student's course.")

        key = (student_id, subject_id, on_date)
        existing_id = self._attendance_index.get(key)
        if existing_id is None:
            rec_id = self._new_id("attendance")
            rec = AttendanceRecord(
                id=rec_id,
                student_id=student_id,
                subject_id=subject_id,
                on_date=on_date,
                status=status,
                taken_by_staff_id=staff.id,
                updated_at=datetime.utcnow(),
            )
            self._attendance[rec_id] = rec
            self._attendance_index[key] = rec_id
            return rec

        rec_id = existing_id
        rec = AttendanceRecord(
            id=rec_id,
            student_id=student_id,
            subject_id=subject_id,
            on_date=on_date,
            status=status,
            taken_by_staff_id=staff.id,
            updated_at=datetime.utcnow(),
        )
        self._attendance[rec_id] = rec
        return rec

    def staff_add_or_update_result(
        self,
        staff: Staff,
        student_id: int,
        subject_id: int,
        score: float,
    ) -> ResultRecord:
        self._require_staff(staff)
        student = self._get_student(student_id)
        subject = self._get_subject(subject_id)

        if subject.staff_id != staff.id:
            raise PermissionError("Staff can only add/update results for their own subjects.")
        if subject.course_id != student.course_id:
            raise ValidationError("Subject course does not match student's course.")

        key = (student_id, subject_id)
        existing_id = self._result_index.get(key)
        if existing_id is None:
            rec_id = self._new_id("result")
            rec = ResultRecord(
                id=rec_id,
                student_id=student_id,
                subject_id=subject_id,
                score=score,
                updated_by_staff_id=staff.id,
                updated_at=datetime.utcnow(),
            )
            self._results[rec_id] = rec
            self._result_index[key] = rec_id
            return rec

        rec_id = existing_id
        rec = ResultRecord(
            id=rec_id,
            student_id=student_id,
            subject_id=subject_id,
            score=score,
            updated_by_staff_id=staff.id,
            updated_at=datetime.utcnow(),
        )
        self._results[rec_id] = rec
        return rec

    def apply_for_leave(self, user: User, start_date: date, end_date: date, reason: str) -> LeaveRequest:
        if user.role not in (Role.STAFF, Role.STUDENT):
            raise PermissionError("Only staff or students can apply for leave.")
        if user.role == Role.STAFF:
            self._get_staff(user.id)
        else:
            self._get_student(user.id)

        leave = LeaveRequest(
            id=self._new_id("leave"),
            from_role=user.role,
            from_user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )
        self._leaves[leave.id] = leave
        return leave

    def send_feedback_to_hod(self, user: User, message: str) -> Feedback:
        if user.role not in (Role.STAFF, Role.STUDENT):
            raise PermissionError("Only staff or students can send feedback.")
        if user.role == Role.STAFF:
            self._get_staff(user.id)
        else:
            self._get_student(user.id)

        fb = Feedback(
            id=self._new_id("feedback"),
            from_role=user.role,
            from_user_id=user.id,
            message=message,
        )
        self._feedback[fb.id] = fb
        return fb

    def admin_reply_feedback(self, admin: Admin, feedback_id: int, reply: str) -> Feedback:
        self._require_admin(admin)
        self._get_admin(admin.id)
        try:
            fb = self._feedback[feedback_id]
        except KeyError as e:
            raise NotFoundError("Feedback not found.") from e
        fb.set_reply(reply)
        return fb

    def admin_review_leave(self, admin: Admin, leave_id: int, approve: bool, note: Optional[str] = None) -> LeaveRequest:
        self._require_admin(admin)
        self._get_admin(admin.id)
        try:
            leave = self._leaves[leave_id]
        except KeyError as e:
            raise NotFoundError("Leave request not found.") from e
        leave.review(admin_id=admin.id, approve=approve, note=note)
        return leave

    def view_student_attendance_admin(self, admin: Admin, student_id: int) -> List[AttendanceRecord]:
        self._require_admin(admin)
        self._get_student(student_id)
        return sorted(
            [r for r in self._attendance.values() if r.student_id == student_id],
            key=lambda r: (r.on_date, r.subject_id, r.id),
        )

    def view_attendance_student(self, student: Student) -> List[AttendanceRecord]:
        self._require_student(student)
        self._get_student(student.id)
        return sorted(
            [r for r in self._attendance.values() if r.student_id == student.id],
            key=lambda r: (r.on_date, r.subject_id, r.id),
        )

    def view_result_student(self, student: Student) -> List[ResultRecord]:
        self._require_student(student)
        self._get_student(student.id)
        return sorted(
            [r for r in self._results.values() if r.student_id == student.id],
            key=lambda r: (r.subject_id, r.id),
        )

    def _attendance_summary_for_student(self, student_id: int) -> Dict[str, int]:
        records = [r for r in self._attendance.values() if r.student_id == student_id]
        present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
        return {"present": present, "absent": absent, "total": present + absent}

    def _leave_summary_for_user(self, role: Role, user_id: int) -> Dict[str, int]:
        leaves = [l for l in self._leaves.values() if l.from_role == role and l.from_user_id == user_id]
        pending = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        approved = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        rejected = sum(1 for l in leaves if l.status == LeaveStatus.REJECTED)
        return {"pending": pending, "approved": approved, "rejected": rejected, "total": pending + approved + rejected}

    def _feedback_summary_for_user(self, role: Role, user_id: int) -> Dict[str, int]:
        fbs = [f for f in self._feedback.values() if f.from_role == role and f.from_user_id == user_id]
        replied = sum(1 for f in fbs if f.reply is not None)
        unreplied = sum(1 for f in fbs if f.reply is None)
        return {"replied": replied, "unreplied": unreplied, "total": replied + unreplied}

    def admin_overall_summary(self, admin: Admin) -> Dict[str, object]:
        self._require_admin(admin)
        students_count = len(self._students)
        staff_count = len(self._staff)
        courses_count = len(self._courses)
        subjects_count = len(self._subjects)
        sessions_count = len(self._sessions)

        leave_pending = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.PENDING)
        leave_approved = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.APPROVED)
        leave_rejected = sum(1 for l in self._leaves.values() if l.status == LeaveStatus.REJECTED)

        feedback_total = len(self._feedback)
        feedback_replied = sum(1 for f in self._feedback.values() if f.reply is not None)
        feedback_unreplied = feedback_total - feedback_replied

        attendance_total = len(self._attendance)
        attendance_present = sum(1 for r in self._attendance.values() if r.status == AttendanceStatus.PRESENT)
        attendance_absent = attendance_total - attendance_present

        return {
            "counts": {
                "students": students_count,
                "staff": staff_count,
                "courses": courses_count,
                "subjects": subjects_count,
                "sessions": sessions_count,
            },
            "leave": {
                "pending": leave_pending,
                "approved": leave_approved,
                "rejected": leave_rejected,
                "total": leave_pending + leave_approved + leave_rejected,
            },
            "feedback": {
                "replied": feedback_replied,
                "unreplied": feedback_unreplied,
                "total": feedback_total,
            },
            "attendance": {
                "present": attendance_present,
                "absent": attendance_absent,
                "total": attendance_total,
            },
        }

    def staff_overall_summary(self, staff: Staff) -> Dict[str, object]:
        self._require_staff(staff)
        self._get_staff(staff.id)

        subjects = [s for s in self._subjects.values() if s.staff_id == staff.id]
        subject_ids: Set[int] = {s.id for s in subjects}

        attendance_records = [r for r in self._attendance.values() if r.subject_id in subject_ids]
        present = sum(1 for r in attendance_records if r.status == AttendanceStatus.PRESENT)
        absent = sum(1 for r in attendance_records if r.status == AttendanceStatus.ABSENT)

        results_records = [r for r in self._results.values() if r.subject_id in subject_ids]

        leave_summary = self._leave_summary_for_user(Role.STAFF, staff.id)
        feedback_summary = self._feedback_summary_for_user(Role.STAFF, staff.id)

        return {
            "subjects": {"count": len(subjects)},
            "attendance": {"present": present, "absent": absent, "total": present + absent},
            "results": {"count": len(results_records)},
            "leave": leave_summary,
            "feedback": feedback_summary,
        }

    def student_overall_summary(self, student: Student) -> Dict[str, object]:
        self._require_student(student)
        self._get_student(student.id)

        attendance_summary = self._attendance_summary_for_student(student.id)
        results_count = sum(1 for r in self._results.values() if r.student_id == student.id)
        leave_summary = self._leave_summary_for_user(Role.STUDENT, student.id)
        feedback_summary = self._feedback_summary_for_user(Role.STUDENT, student.id)

        subjects_count = sum(1 for s in self._subjects.values() if s.course_id == student.course_id)

        return {
            "subjects": {"count": subjects_count},
            "attendance": attendance_summary,
            "results": {"count": results_count},
            "leave": leave_summary,
            "feedback": feedback_summary,
        }

    def list_feedback_admin(self, admin: Admin) -> List[Feedback]:
        self._require_admin(admin)
        return sorted(self._feedback.values(), key=lambda f: (f.created_at, f.id))

    def list_leave_requests_admin(self, admin: Admin) -> List[LeaveRequest]:
        self._require_admin(admin)
        return sorted(self._leaves.values(), key=lambda l: (l.created_at, l.id))

    def list_students_admin(self, admin: Admin) -> List[Student]:
        self._require_admin(admin)
        return sorted(self._students.values(), key=lambda s: s.id)

    def list_staff_admin(self, admin: Admin) -> List[Staff]:
        self._require_admin(admin)
        return sorted(self._staff.values(), key=lambda s: s.id)

    def list_courses_admin(self, admin: Admin) -> List[Course]:
        self._require_admin(admin)
        return sorted(self._courses.values(), key=lambda c: c.id)

    def list_subjects_admin(self, admin: Admin) -> List[Subject]:
        self._require_admin(admin)
        return sorted(self._subjects.values(), key=lambda s: s.id)

    def list_sessions_admin(self, admin: Admin) -> List[Session]:
        self._require_admin(admin)
        return sorted(self._sessions.values(), key=lambda s: s.id)