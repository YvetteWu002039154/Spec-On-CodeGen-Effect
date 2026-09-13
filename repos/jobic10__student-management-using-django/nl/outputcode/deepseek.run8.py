from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

# --------------------- Enums ---------------------
class LeaveStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class FeedbackStatus(Enum):
    PENDING = "Pending"
    REPLIED = "Replied"

class AttendanceStatus(Enum):
    PRESENT = "Present"
    ABSENT = "Absent"

class UserType(Enum):
    ADMIN = "Admin"
    STAFF = "Staff"
    STUDENT = "Student"

# --------------------- Base Person ---------------------
class Person(ABC):
    def __init__(self, user_id: str, name: str, email: str) -> None:
        self.user_id = user_id
        self.name = name
        self.email = email

    @abstractmethod
    def get_role(self) -> UserType:
        ...

    def __str__(self) -> str:
        return f"{self.get_role().value}: {self.name} ({self.user_id})"

# --------------------- Admin, Staff, Student ---------------------
class Admin(Person):
    def __init__(self, admin_id: str, name: str, email: str) -> None:
        super().__init__(admin_id, name, email)

    def get_role(self) -> UserType:
        return UserType.ADMIN

class Staff(Person):
    def __init__(self, staff_id: str, name: str, email: str) -> None:
        super().__init__(staff_id, name, email)

    def get_role(self) -> UserType:
        return UserType.STAFF

class Student(Person):
    def __init__(self, student_id: str, name: str, email: str) -> None:
        super().__init__(student_id, name, email)

    def get_role(self) -> UserType:
        return UserType.STUDENT

# --------------------- Entities ---------------------
@dataclass
class Course:
    course_id: str
    name: str
    code: str
    description: str = ""

@dataclass
class Subject:
    subject_id: str
    name: str
    code: str
    course_id: str

@dataclass
class Session:
    session_id: str
    year: int
    term: str
    start_date: date
    end_date: date

@dataclass
class Attendance:
    attendance_id: str
    student_id: str
    subject_id: str
    session_id: str
    date: date
    status: AttendanceStatus
    marked_by_staff_id: str

@dataclass
class Result:
    result_id: str
    student_id: str
    subject_id: str
    session_id: str
    marks: float
    grade: str = ""  # Could be derived from marks later

@dataclass
class Leave:
    leave_id: str
    applicant_id: str
    applicant_type: UserType
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus = LeaveStatus.PENDING
    reviewed_by_admin_id: Optional[str] = None

@dataclass
class Feedback:
    feedback_id: str
    sender_id: str
    sender_type: UserType
    message: str
    reply: Optional[str] = None
    status: FeedbackStatus = FeedbackStatus.PENDING
    replied_by_admin_id: Optional[str] = None

# --------------------- Management System ---------------------
class StudentManagementSystem:
    def __init__(self) -> None:
        # Data stores
        self.admins: Dict[str, Admin] = {}
        self.staffs: Dict[str, Staff] = {}
        self.students: Dict[str, Student] = {}
        self.courses: Dict[str, Course] = {}
        self.subjects: Dict[str, Subject] = {}
        self.sessions: Dict[str, Session] = {}
        self.attendances: Dict[str, Attendance] = {}
        self.results: Dict[str, Result] = {}
        self.leaves: Dict[str, Leave] = {}
        self.feedbacks: Dict[str, Feedback] = {}

        # ID counters for simplicity (they should be unique per type)
        self._id_counters = {
            "admin": 0, "staff": 0, "student": 0,
            "course": 0, "subject": 0, "session": 0,
            "attendance": 0, "result": 0, "leave": 0, "feedback": 0
        }

    def _generate_id(self, prefix: str) -> str:
        key = prefix.lower()
        self._id_counters[key] += 1
        return f"{prefix}_{self._id_counters[key]}"

    # ---------- Auth (simple lookup) ----------
    def authenticate(self, user_id: str, role: UserType):
        if role == UserType.ADMIN:
            return self.admins.get(user_id)
        elif role == UserType.STAFF:
            return self.staffs.get(user_id)
        elif role == UserType.STUDENT:
            return self.students.get(user_id)
        return None

    # ---------- Admin management (restricted to Admin) ----------
    def add_admin(self, name: str, email: str) -> Admin:
        admin_id = self._generate_id("ADM")
        admin = Admin(admin_id, name, email)
        self.admins[admin_id] = admin
        return admin

    # ---------- Staff management ----------
    def admin_add_staff(self, name: str, email: str) -> Staff:
        staff_id = self._generate_id("STF")
        staff = Staff(staff_id, name, email)
        self.staffs[staff_id] = staff
        return staff

    def admin_update_staff(self, staff_id: str, name: Optional[str] = None, email: Optional[str] = None) -> bool:
        staff = self.staffs.get(staff_id)
        if not staff:
            return False
        if name:
            staff.name = name
        if email:
            staff.email = email
        return True

    def admin_delete_staff(self, staff_id: str) -> bool:
        if staff_id in self.staffs:
            del self.staffs[staff_id]
            # Cascade deletion of related records? Not specified, but we could leave them or delete.
            return True
        return False

    # ---------- Student management ----------
    def admin_add_student(self, name: str, email: str) -> Student:
        student_id = self._generate_id("STU")
        student = Student(student_id, name, email)
        self.students[student_id] = student
        return student

    def admin_update_student(self, student_id: str, name: Optional[str] = None, email: Optional[str] = None) -> bool:
        student = self.students.get(student_id)
        if not student:
            return False
        if name:
            student.name = name
        if email:
            student.email = email
        return True

    def admin_delete_student(self, student_id: str) -> bool:
        if student_id in self.students:
            del self.students[student_id]
            return True
        return False

    # ---------- Course management ----------
    def add_course(self, name: str, code: str, description: str = "") -> Course:
        course_id = self._generate_id("CRS")
        course = Course(course_id, name, code, description)
        self.courses[course_id] = course
        return course

    def update_course(self, course_id: str, name: Optional[str] = None, code: Optional[str] = None, description: Optional[str] = None) -> bool:
        course = self.courses.get(course_id)
        if not course:
            return False
        if name:
            course.name = name
        if code:
            course.code = code
        if description is not None:
            course.description = description
        return True

    def delete_course(self, course_id: str) -> bool:
        if course_id in self.courses:
            del self.courses[course_id]
            # Cascade subjects? For simplicity not, but we can add later.
            return True
        return False

    # ---------- Subject management ----------
    def add_subject(self, name: str, code: str, course_id: str) -> Optional[Subject]:
        if course_id not in self.courses:
            return None  # invalid course
        subject_id = self._generate_id("SUB")
        subject = Subject(subject_id, name, code, course_id)
        self.subjects[subject_id] = subject
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None, code: Optional[str] = None, course_id: Optional[str] = None) -> bool:
        subject = self.subjects.get(subject_id)
        if not subject:
            return False
        if name:
            subject.name = name
        if code:
            subject.code = code
        if course_id and course_id in self.courses:
            subject.course_id = course_id
        return True

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id in self.subjects:
            del self.subjects[subject_id]
            return True
        return False

    # ---------- Session management ----------
    def add_session(self, year: int, term: str, start_date: date, end_date: date) -> Session:
        session_id = self._generate_id("SES")
        session = Session(session_id, year, term, start_date, end_date)
        self.sessions[session_id] = session
        return session

    def update_session(self, session_id: str, year: Optional[int] = None, term: Optional[str] = None,
                       start_date: Optional[date] = None, end_date: Optional[date] = None) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        if year:
            session.year = year
        if term:
            session.term = term
        if start_date:
            session.start_date = start_date
        if end_date:
            session.end_date = end_date
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    # ---------- Attendance (Staff) ----------
    def staff_take_attendance(self, student_id: str, subject_id: str, session_id: str,
                              date_val: date, status: AttendanceStatus, staff_id: str) -> Optional[Attendance]:
        # Validate existence
        if student_id not in self.students:
            return None
        if subject_id not in self.subjects:
            return None
        if session_id not in self.sessions:
            return None
        if staff_id not in self.staffs:
            return None
        attendance_id = self._generate_id("ATT")
        attendance = Attendance(attendance_id, student_id, subject_id, session_id,
                                date_val, status, staff_id)
        self.attendances[attendance_id] = attendance
        return attendance

    def staff_update_attendance(self, attendance_id: str, status: AttendanceStatus, staff_id: str) -> bool:
        attendance = self.attendances.get(attendance_id)
        if not attendance or attendance.marked_by_staff_id != staff_id:
            return False  # Only the marking staff can update
        attendance.status = status
        return True

    # ---------- Result (Staff) ----------
    def staff_add_result(self, student_id: str, subject_id: str, session_id: str,
                         marks: float, grade: str, staff_id: str) -> Optional[Result]:
        if student_id not in self.students or subject_id not in self.subjects or session_id not in self.sessions or staff_id not in self.staffs:
            return None
        result_id = self._generate_id("RES")
        result = Result(result_id, student_id, subject_id, session_id, marks, grade)
        self.results[result_id] = result
        return result

    def staff_update_result(self, result_id: str, marks: Optional[float] = None, grade: Optional[str] = None, staff_id: str) -> bool:
        result = self.results.get(result_id)
        if not result:
            return False
        # For simplicity, any staff can update (could restrict to subjects they teach)
        if marks is not None:
            result.marks = marks
        if grade is not None:
            result.grade = grade
        return True

    # ---------- Leave Application (Staff and Student) ----------
    def apply_leave(self, applicant_id: str, applicant_type: UserType, start_date: date, end_date: date, reason: str) -> Optional[Leave]:
        if applicant_type == UserType.STAFF and applicant_id not in self.staffs:
            return None
        if applicant_type == UserType.STUDENT and applicant_id not in self.students:
            return None
        leave_id = self._generate_id("LEV")
        leave = Leave(leave_id, applicant_id, applicant_type, start_date, end_date, reason)
        self.leaves[leave_id] = leave
        return leave

    def admin_review_leave(self, leave_id: str, decision: LeaveStatus, admin_id: str) -> bool:
        if admin_id not in self.admins:
            return False
        leave = self.leaves.get(leave_id)
        if not leave or leave.status != LeaveStatus.PENDING:
            return False
        leave.status = decision
        leave.reviewed_by_admin_id = admin_id
        return True

    # ---------- Feedback (Staff and Student) ----------
    def send_feedback(self, sender_id: str, sender_type: UserType, message: str) -> Optional[Feedback]:
        if sender_type == UserType.STAFF and sender_id not in self.staffs:
            return None
        if sender_type == UserType.STUDENT and sender_id not in self.students:
            return None
        feedback_id = self._generate_id("FBK")
        feedback = Feedback(feedback_id, sender_id, sender_type, message)
        self.feedbacks[feedback_id] = feedback
        return feedback

    def admin_reply_feedback(self, feedback_id: str, reply: str, admin_id: str) -> bool:
        if admin_id not in self.admins:
            return False
        feedback = self.feedbacks.get(feedback_id)
        if not feedback or feedback.status != FeedbackStatus.PENDING:
            return False
        feedback.reply = reply
        feedback.status = FeedbackStatus.REPLIED
        feedback.replied_by_admin_id = admin_id
        return True

    # ---------- Summary/Charts ----------
    def admin_overall_summary(self) -> Dict:
        total_students = len(self.students)
        total_staff = len(self.staffs)
        total_courses = len(self.courses)
        total_subjects = len(self.subjects)
        total_sessions = len(self.sessions)
        total_attendance = len(self.attendances)
        total_results = len(self.results)
        pending_leaves = sum(1 for l in self.leaves.values() if l.status == LeaveStatus.PENDING)
        pending_feedbacks = sum(1 for f in self.feedbacks.values() if f.status == FeedbackStatus.PENDING)

        return {
            "total_students": total_students,
            "total_staff": total_staff,
            "total_courses": total_courses,
            "total_subjects": total_subjects,
            "total_sessions": total_sessions,
            "total_attendance_records": total_attendance,
            "total_results": total_results,
            "pending_leaves": pending_leaves,
            "pending_feedbacks": pending_feedbacks
        }

    def staff_summary(self, staff_id: str) -> Optional[Dict]:
        if staff_id not in self.staffs:
            return None
        # Marked attendance count
        marked_attendance = [a for a in self.attendances.values() if a.marked_by_staff_id == staff_id]
        total_attendance = len(marked_attendance)
        # Results with staff_id? Actually results aren't directly linked to a staff. We'll assume staff teaches subjects.
        # For simplicity, staff summary can show total attendance taken.
        # Staff leaves
        staff_leaves = [l for l in self.leaves.values() if l.applicant_id == staff_id and l.applicant_type == UserType.STAFF]
        leave_counts = {"Pending": 0, "Approved": 0, "Rejected": 0}
        for l in staff_leaves:
            leave_counts[l.status.value] += 1
        # Staff feedback
        staff_feedback = [f for f in self.feedbacks.values() if f.sender_id == staff_id and f.sender_type == UserType.STAFF]
        feedback_status_counts = {"Pending": 0, "Replied": 0}
        for f in staff_feedback:
            feedback_status_counts[f.status.value] += 1

        return {
            "staff_name": self.staffs[staff_id].name,
            "total_attendance_marked": total_attendance,
            "leave_summary": leave_counts,
            "feedback_summary": feedback_status_counts
        }

    def student_summary(self, student_id: str) -> Optional[Dict]:
        if student_id not in self.students:
            return None
        # Attendance for student
        student_attendance = [a for a in self.attendances.values() if a.student_id == student_id]
        attendance_counts = {"Present": 0, "Absent": 0}
        for a in student_attendance:
            attendance_counts[a.status.value] += 1
        # Results
        student_results = [r for r in self.results.values() if r.student_id == student_id]
        # Leaves
        student_leaves = [l for l in self.leaves.values() if l.applicant_id == student_id and l.applicant_type == UserType.STUDENT]
        leave_counts = {"Pending": 0, "Approved": 0, "Rejected": 0}
        for l in student_leaves:
            leave_counts[l.status.value] += 1
        # Feedbacks
        student_feedback = [f for f in self.feedbacks.values() if f.sender_id == student_id and f.sender_type == UserType.STUDENT]
        feedback_status_counts = {"Pending": 0, "Replied": 0}
        for f in student_feedback:
            feedback_status_counts[f.status.value] += 1

        return {
            "student_name": self.students[student_id].name,
            "attendance_summary": attendance_counts,
            "result_count": len(student_results),
            "leave_summary": leave_counts,
            "feedback_summary": feedback_status_counts
        }

    def view_student_attendance_admin(self, student_id: str) -> List[Attendance]:
        return [a for a in self.attendances.values() if a.student_id == student_id]

    def view_student_attendance(self, student_id: str) -> List[Attendance]:
        return self.view_student_attendance_admin(student_id)

    def view_student_result(self, student_id: str) -> List[Result]:
        return [r for r in self.results.values() if r.student_id == student_id]