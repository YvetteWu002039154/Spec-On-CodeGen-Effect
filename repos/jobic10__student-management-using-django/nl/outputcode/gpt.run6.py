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


class FeedbackStatus(str, Enum):
    PENDING = "pending"
    REPLIED = "replied"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


@dataclass(frozen=True)
class Session:
    session_id: int
    name: str


@dataclass(frozen=True)
class Course:
    course_id: int
    name: str


@dataclass(frozen=True)
class Subject:
    subject_id: int
    name: str
    course_id: int
    staff_id: int


@dataclass
class User:
    user_id: int
    name: str
    role: Role


@dataclass
class Admin(User):
    def __init__(self, user_id: int, name: str):
        super().__init__(user_id=user_id, name=name, role=Role.ADMIN)


@dataclass
class Staff(User):
    def __init__(self, user_id: int, name: str):
        super().__init__(user_id=user_id, name=name, role=Role.STAFF)


@dataclass
class Student(User):
    course_id: int
    session_id: int

    def __init__(self, user_id: int, name: str, course_id: int, session_id: int):
        super().__init__(user_id=user_id, name=name, role=Role.STUDENT)
        self.course_id = course_id
        self.session_id = session_id


@dataclass
class LeaveRequest:
    leave_id: int
    requester_role: Role
    requester_id: int
    from_date: date
    to_date: date
    reason: str
    status: LeaveStatus = LeaveStatus.PENDING
    reviewed_by_admin_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.from_date > self.to_date:
            raise ValueError("from_date must be <= to_date")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty")
        if self.requester_role not in (Role.STAFF, Role.STUDENT):
            raise ValueError("Only staff or students can request leave")


@dataclass
class Feedback:
    feedback_id: int
    sender_role: Role
    sender_id: int
    message: str
    status: FeedbackStatus = FeedbackStatus.PENDING
    reply: Optional[str] = None
    replied_by_admin_id: Optional[int] = None
    replied_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("message must be non-empty")
        if self.sender_role not in (Role.STAFF, Role.STUDENT):
            raise ValueError("Only staff or students can send feedback")


@dataclass
class ResultRecord:
    student_id: int
    subject_id: int
    score: float
    updated_by_staff_id: int
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.score < 0:
            raise ValueError("score must be >= 0")


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_user_id: int = 1
        self._next_course_id: int = 1
        self._next_subject_id: int = 1
        self._next_session_id: int = 1
        self._next_leave_id: int = 1
        self._next_feedback_id: int = 1

        self._admins: Dict[int, Admin] = {}
        self._staff: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}

        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}

        self._attendance: Dict[Tuple[int, int, date], AttendanceStatus] = {}
        self._results: Dict[Tuple[int, int], ResultRecord] = {}

        self._leave_requests: Dict[int, LeaveRequest] = {}
        self._feedbacks: Dict[int, Feedback] = {}

    def _require_admin(self, admin_id: int) -> Admin:
        admin = self._admins.get(admin_id)
        if not admin:
            raise ValueError("Invalid admin_id")
        return admin

    def _require_staff(self, staff_id: int) -> Staff:
        staff = self._staff.get(staff_id)
        if not staff:
            raise ValueError("Invalid staff_id")
        return staff

    def _require_student(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if not student:
            raise ValueError("Invalid student_id")
        return student

    def _require_course(self, course_id: int) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise ValueError("Invalid course_id")
        return course

    def _require_subject(self, subject_id: int) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError("Invalid subject_id")
        return subject

    def _require_session(self, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("Invalid session_id")
        return session

    def _validate_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("name must be non-empty")

    def create_admin(self, name: str) -> Admin:
        self._validate_name(name)
        admin = Admin(user_id=self._next_user_id, name=name.strip())
        self._admins[admin.user_id] = admin
        self._next_user_id += 1
        return admin

    def create_staff(self, admin_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        self._validate_name(name)
        staff = Staff(user_id=self._next_user_id, name=name.strip())
        self._staff[staff.user_id] = staff
        self._next_user_id += 1
        return staff

    def update_staff(self, admin_id: int, staff_id: int, name: str) -> Staff:
        self._require_admin(admin_id)
        self._validate_name(name)
        staff = self._require_staff(staff_id)
        staff.name = name.strip()
        return staff

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._require_admin(admin_id)
        self._require_staff(staff_id)
        for subj in self._subjects.values():
            if subj.staff_id == staff_id:
                raise ValueError("Cannot delete staff assigned to a subject")
        del self._staff[staff_id]

    def create_student(self, admin_id: int, name: str, course_id: int, session_id: int) -> Student:
        self._require_admin(admin_id)
        self._validate_name(name)
        self._require_course(course_id)
        self._require_session(session_id)
        student = Student(user_id=self._next_user_id, name=name.strip(), course_id=course_id, session_id=session_id)
        self._students[student.user_id] = student
        self._next_user_id += 1
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
        student = self._require_student(student_id)
        if name is not None:
            self._validate_name(name)
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
        self._require_student(student_id)
        keys_to_delete = [k for k in self._attendance.keys() if k[0] == student_id]
        for k in keys_to_delete:
            del self._attendance[k]
        result_keys = [k for k in self._results.keys() if k[0] == student_id]
        for k in result_keys:
            del self._results[k]
        del self._students[student_id]

    def create_course(self, admin_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        self._validate_name(name)
        course = Course(course_id=self._next_course_id, name=name.strip())
        self._courses[course.course_id] = course
        self._next_course_id += 1
        return course

    def update_course(self, admin_id: int, course_id: int, name: str) -> Course:
        self._require_admin(admin_id)
        self._validate_name(name)
        self._require_course(course_id)
        course = Course(course_id=course_id, name=name.strip())
        self._courses[course_id] = course
        return course

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._require_admin(admin_id)
        self._require_course(course_id)
        for s in self._students.values():
            if s.course_id == course_id:
                raise ValueError("Cannot delete course with enrolled students")
        for subj in self._subjects.values():
            if subj.course_id == course_id:
                raise ValueError("Cannot delete course with subjects")
        del self._courses[course_id]

    def create_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        self._require_admin(admin_id)
        self._validate_name(name)
        self._require_course(course_id)
        self._require_staff(staff_id)
        subject = Subject(subject_id=self._next_subject_id, name=name.strip(), course_id=course_id, staff_id=staff_id)
        self._subjects[subject.subject_id] = subject
        self._next_subject_id += 1
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
        new_name = subject.name
        new_course_id = subject.course_id
        new_staff_id = subject.staff_id
        if name is not None:
            self._validate_name(name)
            new_name = name.strip()
        if course_id is not None:
            self._require_course(course_id)
            new_course_id = course_id
        if staff_id is not None:
            self._require_staff(staff_id)
            new_staff_id = staff_id
        updated = Subject(subject_id=subject_id, name=new_name, course_id=new_course_id, staff_id=new_staff_id)
        self._subjects[subject_id] = updated
        return updated

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._require_admin(admin_id)
        self._require_subject(subject_id)
        attendance_keys = [k for k in self._attendance.keys() if k[1] == subject_id]
        for k in attendance_keys:
            del self._attendance[k]
        result_keys = [k for k in self._results.keys() if k[1] == subject_id]
        for k in result_keys:
            del self._results[k]
        del self._subjects[subject_id]

    def create_session(self, admin_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        self._validate_name(name)
        session = Session(session_id=self._next_session_id, name=name.strip())
        self._sessions[session.session_id] = session
        self._next_session_id += 1
        return session

    def update_session(self, admin_id: int, session_id: int, name: str) -> Session:
        self._require_admin(admin_id)
        self._validate_name(name)
        self._require_session(session_id)
        session = Session(session_id=session_id, name=name.strip())
        self._sessions[session_id] = session
        return session

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._require_admin(admin_id)
        self._require_session(session_id)
        for s in self._students.values():
            if s.session_id == session_id:
                raise ValueError("Cannot delete session with enrolled students")
        del self._sessions[session_id]

    def take_or_update_attendance(
        self,
        staff_id: int,
        student_id: int,
        subject_id: int,
        on_date: date,
        status: AttendanceStatus,
    ) -> None:
        self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._require_subject(subject_id)
        if subject.staff_id != staff_id:
            raise ValueError("Staff not assigned to this subject")
        if student.course_id != subject.course_id:
            raise ValueError("Student course does not match subject course")
        key = (student_id, subject_id, on_date)
        self._attendance[key] = status

    def view_student_attendance(self, admin_id: int, student_id: int) -> List[Tuple[int, date, AttendanceStatus]]:
        self._require_admin(admin_id)
        self._require_student(student_id)
        records: List[Tuple[int, date, AttendanceStatus]] = []
        for (sid, subj_id, d), st in self._attendance.items():
            if sid == student_id:
                records.append((subj_id, d, st))
        records.sort(key=lambda x: (x[0], x[1]))
        return records

    def student_view_attendance(self, student_id: int) -> List[Tuple[int, date, AttendanceStatus]]:
        self._require_student(student_id)
        records: List[Tuple[int, date, AttendanceStatus]] = []
        for (sid, subj_id, d), st in self._attendance.items():
            if sid == student_id:
                records.append((subj_id, d, st))
        records.sort(key=lambda x: (x[0], x[1]))
        return records

    def add_or_update_result(self, staff_id: int, student_id: int, subject_id: int, score: float) -> ResultRecord:
        self._require_staff(staff_id)
        student = self._require_student(student_id)
        subject = self._require_subject(subject_id)
        if subject.staff_id != staff_id:
            raise ValueError("Staff not assigned to this subject")
        if student.course_id != subject.course_id:
            raise ValueError("Student course does not match subject course")
        record = ResultRecord(student_id=student_id, subject_id=subject_id, score=score, updated_by_staff_id=staff_id)
        self._results[(student_id, subject_id)] = record
        return record

    def student_view_results(self, student_id: int) -> List[ResultRecord]:
        self._require_student(student_id)
        records = [r for (sid, _), r in self._results.items() if sid == student_id]
        records.sort(key=lambda r: r.subject_id)
        return records

    def apply_leave_staff(self, staff_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        self._require_staff(staff_id)
        leave = LeaveRequest(
            leave_id=self._next_leave_id,
            requester_role=Role.STAFF,
            requester_id=staff_id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
        )
        self._leave_requests[leave.leave_id] = leave
        self._next_leave_id += 1
        return leave

    def apply_leave_student(self, student_id: int, from_date: date, to_date: date, reason: str) -> LeaveRequest:
        self._require_student(student_id)
        leave = LeaveRequest(
            leave_id=self._next_leave_id,
            requester_role=Role.STUDENT,
            requester_id=student_id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
        )
        self._leave_requests[leave.leave_id] = leave
        self._next_leave_id += 1
        return leave

    def review_leave(self, admin_id: int, leave_id: int, approve: bool, note: Optional[str] = None) -> LeaveRequest:
        self._require_admin(admin_id)
        leave = self._leave_requests.get(leave_id)
        if not leave:
            raise ValueError("Invalid leave_id")
        if leave.status != LeaveStatus.PENDING:
            raise ValueError("Leave request already reviewed")
        leave.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        leave.reviewed_by_admin_id = admin_id
        leave.reviewed_at = datetime.utcnow()
        leave.review_note = note
        return leave

    def send_feedback_staff(self, staff_id: int, message: str) -> Feedback:
        self._require_staff(staff_id)
        fb = Feedback(
            feedback_id=self._next_feedback_id,
            sender_role=Role.STAFF,
            sender_id=staff_id,
            message=message,
        )
        self._feedbacks[fb.feedback_id] = fb
        self._next_feedback_id += 1
        return fb

    def send_feedback_student(self, student_id: int, message: str) -> Feedback:
        self._require_student(student_id)
        fb = Feedback(
            feedback_id=self._next_feedback_id,
            sender_role=Role.STUDENT,
            sender_id=student_id,
            message=message,
        )
        self._feedbacks[fb.feedback_id] = fb
        self._next_feedback_id += 1
        return fb

    def reply_feedback(self, admin_id: int, feedback_id: int, reply: str) -> Feedback:
        self._require_admin(admin_id)
        fb = self._feedbacks.get(feedback_id)
        if not fb:
            raise ValueError("Invalid feedback_id")
        if not reply or not reply.strip():
            raise ValueError("reply must be non-empty")
        fb.reply = reply.strip()
        fb.status = FeedbackStatus.REPLIED
        fb.replied_by_admin_id = admin_id
        fb.replied_at = datetime.utcnow()
        return fb

    def admin_summary(self, admin_id: int) -> Dict[str, int]:
        self._require_admin(admin_id)
        return {
            "students": len(self._students),
            "staff": len(self._staff),
            "courses": len(self._courses),
            "subjects": len(self._subjects),
            "sessions": len(self._sessions),
            "leave_total": len(self._leave_requests),
            "leave_pending": sum(1 for l in self._leave_requests.values() if l.status == LeaveStatus.PENDING),
            "feedback_total": len(self._feedbacks),
            "feedback_pending": sum(1 for f in self._feedbacks.values() if f.status == FeedbackStatus.PENDING),
            "attendance_records": len(self._attendance),
            "result_records": len(self._results),
        }

    def staff_summary(self, staff_id: int) -> Dict[str, int]:
        self._require_staff(staff_id)
        subject_ids = [s.subject_id for s in self._subjects.values() if s.staff_id == staff_id]
        subject_set: Set[int] = set(subject_ids)
        student_ids_for_subjects: Set[int] = set()
        for subj_id in subject_set:
            subj = self._subjects[subj_id]
            for st in self._students.values():
                if st.course_id == subj.course_id:
                    student_ids_for_subjects.add(st.user_id)

        leave_total = sum(
            1 for l in self._leave_requests.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id
        )
        leave_pending = sum(
            1
            for l in self._leave_requests.values()
            if l.requester_role == Role.STAFF and l.requester_id == staff_id and l.status == LeaveStatus.PENDING
        )

        feedback_total = sum(
            1 for f in self._feedbacks.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id
        )
        feedback_pending = sum(
            1
            for f in self._feedbacks.values()
            if f.sender_role == Role.STAFF and f.sender_id == staff_id and f.status == FeedbackStatus.PENDING
        )

        attendance_records = sum(1 for (sid, subj_id, _d) in self._attendance.keys() if subj_id in subject_set)
        result_records = sum(1 for (sid, subj_id) in self._results.keys() if subj_id in subject_set)

        return {
            "subjects_assigned": len(subject_set),
            "students_in_assigned_courses": len(student_ids_for_subjects),
            "leave_total": leave_total,
            "leave_pending": leave_pending,
            "feedback_total": feedback_total,
            "feedback_pending": feedback_pending,
            "attendance_records_for_subjects": attendance_records,
            "result_records_for_subjects": result_records,
        }

    def student_summary(self, student_id: int) -> Dict[str, int]:
        student = self._require_student(student_id)
        subject_ids = [s.subject_id for s in self._subjects.values() if s.course_id == student.course_id]
        subject_set = set(subject_ids)

        attendance_total = sum(1 for (sid, subj_id, _d) in self._attendance.keys() if sid == student_id)
        attendance_present = sum(
            1
            for (sid, subj_id, d), st in self._attendance.items()
            if sid == student_id and st == AttendanceStatus.PRESENT
        )
        attendance_absent = sum(
            1
            for (sid, subj_id, d), st in self._attendance.items()
            if sid == student_id and st == AttendanceStatus.ABSENT
        )

        results_total = sum(1 for (sid, _subj_id) in self._results.keys() if sid == student_id)

        leave_total = sum(
            1 for l in self._leave_requests.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id
        )
        leave_pending = sum(
            1
            for l in self._leave_requests.values()
            if l.requester_role == Role.STUDENT and l.requester_id == student_id and l.status == LeaveStatus.PENDING
        )

        feedback_total = sum(
            1 for f in self._feedbacks.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id
        )
        feedback_pending = sum(
            1
            for f in self._feedbacks.values()
            if f.sender_role == Role.STUDENT and f.sender_id == student_id and f.status == FeedbackStatus.PENDING
        )

        return {
            "subjects_in_course": len(subject_set),
            "attendance_total": attendance_total,
            "attendance_present": attendance_present,
            "attendance_absent": attendance_absent,
            "results_total": results_total,
            "leave_total": leave_total,
            "leave_pending": leave_pending,
            "feedback_total": feedback_total,
            "feedback_pending": feedback_pending,
        }

    def list_leave_requests(self, admin_id: int, status: Optional[LeaveStatus] = None) -> List[LeaveRequest]:
        self._require_admin(admin_id)
        leaves = list(self._leave_requests.values())
        if status is not None:
            leaves = [l for l in leaves if l.status == status]
        leaves.sort(key=lambda l: (l.status.value, l.created_at))
        return leaves

    def list_feedbacks(self, admin_id: int, status: Optional[FeedbackStatus] = None) -> List[Feedback]:
        self._require_admin(admin_id)
        fbs = list(self._feedbacks.values())
        if status is not None:
            fbs = [f for f in fbs if f.status == status]
        fbs.sort(key=lambda f: (f.status.value, f.created_at))
        return fbs

    def staff_list_own_leave_requests(self, staff_id: int) -> List[LeaveRequest]:
        self._require_staff(staff_id)
        leaves = [l for l in self._leave_requests.values() if l.requester_role == Role.STAFF and l.requester_id == staff_id]
        leaves.sort(key=lambda l: l.created_at)
        return leaves

    def student_list_own_leave_requests(self, student_id: int) -> List[LeaveRequest]:
        self._require_student(student_id)
        leaves = [
            l for l in self._leave_requests.values() if l.requester_role == Role.STUDENT and l.requester_id == student_id
        ]
        leaves.sort(key=lambda l: l.created_at)
        return leaves

    def staff_list_own_feedbacks(self, staff_id: int) -> List[Feedback]:
        self._require_staff(staff_id)
        fbs = [f for f in self._feedbacks.values() if f.sender_role == Role.STAFF and f.sender_id == staff_id]
        fbs.sort(key=lambda f: f.created_at)
        return fbs

    def student_list_own_feedbacks(self, student_id: int) -> List[Feedback]:
        self._require_student(student_id)
        fbs = [f for f in self._feedbacks.values() if f.sender_role == Role.STUDENT and f.sender_id == student_id]
        fbs.sort(key=lambda f: f.created_at)
        return fbs

    def get_course(self, course_id: int) -> Course:
        return self._require_course(course_id)

    def get_subject(self, subject_id: int) -> Subject:
        return self._require_subject(subject_id)

    def get_session(self, session_id: int) -> Session:
        return self._require_session(session_id)

    def get_staff(self, staff_id: int) -> Staff:
        return self._require_staff(staff_id)

    def get_student(self, student_id: int) -> Student:
        return self._require_student(student_id)

    def list_courses(self) -> List[Course]:
        return sorted(self._courses.values(), key=lambda c: c.course_id)

    def list_subjects(self) -> List[Subject]:
        return sorted(self._subjects.values(), key=lambda s: s.subject_id)

    def list_sessions(self) -> List[Session]:
        return sorted(self._sessions.values(), key=lambda s: s.session_id)

    def list_staff(self) -> List[Staff]:
        return sorted(self._staff.values(), key=lambda s: s.user_id)

    def list_students(self) -> List[Student]:
        return sorted(self._students.values(), key=lambda s: s.user_id)