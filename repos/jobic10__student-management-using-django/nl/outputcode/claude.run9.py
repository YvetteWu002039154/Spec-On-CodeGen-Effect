from datetime import datetime, date
from typing import Optional
import hashlib
import uuid


# ─────────────────────────────────────────────
# Enumerations / Constants
# ─────────────────────────────────────────────

class UserRole:
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class LeaveStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AttendanceStatus:
    PRESENT = "present"
    ABSENT = "absent"


class FeedbackStatus:
    PENDING = "pending"
    REPLIED = "replied"


# ─────────────────────────────────────────────
# Core Models
# ─────────────────────────────────────────────

class User:
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, role: str, first_name: str, last_name: str):
        self.user_id = user_id
        self.username = username
        self._password_hash = self._hash_password(password)
        self.email = email
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.created_at = datetime.now()
        self.is_active = True

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self._password_hash == self._hash_password(password)

    def change_password(self, old_password: str, new_password: str) -> bool:
        if self.verify_password(old_password):
            self._password_hash = self._hash_password(new_password)
            return True
        return False

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User id={self.user_id} username={self.username} role={self.role}>"


class Session:
    def __init__(self, session_id: str, session_name: str,
                 start_year: int, end_year: int):
        self.session_id = session_id
        self.session_name = session_name
        self.start_year = start_year
        self.end_year = end_year
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<Session {self.session_name} ({self.start_year}-{self.end_year})>"


class Course:
    def __init__(self, course_id: str, course_name: str, description: str = ""):
        self.course_id = course_id
        self.course_name = course_name
        self.description = description
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<Course id={self.course_id} name={self.course_name}>"


class Subject:
    def __init__(self, subject_id: str, subject_name: str,
                 course_id: str, staff_id: str):
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.course_id = course_id
        self.staff_id = staff_id
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<Subject id={self.subject_id} name={self.subject_name}>"


class Staff:
    def __init__(self, staff_id: str, user_id: str, address: str = ""):
        self.staff_id = staff_id
        self.user_id = user_id
        self.address = address
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<Staff id={self.staff_id} user_id={self.user_id}>"


class Student:
    def __init__(self, student_id: str, user_id: str, course_id: str,
                 session_id: str, gender: str = "", address: str = ""):
        self.student_id = student_id
        self.user_id = user_id
        self.course_id = course_id
        self.session_id = session_id
        self.gender = gender
        self.address = address
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<Student id={self.student_id} user_id={self.user_id}>"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str,
                 session_id: str, attendance_date: date, staff_id: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.attendance_date = attendance_date
        self.staff_id = staff_id
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<Attendance id={self.attendance_id} date={self.attendance_date}>"


class AttendanceReport:
    def __init__(self, report_id: str, student_id: str,
                 attendance_id: str, status: str):
        self.report_id = report_id
        self.student_id = student_id
        self.attendance_id = attendance_id
        self.status = status
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<AttendanceReport student={self.student_id} status={self.status}>"


class LeaveReport:
    def __init__(self, leave_id: str, user_id: str, user_role: str,
                 leave_date: str, leave_message: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.user_role = user_role
        self.leave_date = leave_date
        self.leave_message = leave_message
        self.status = LeaveStatus.PENDING
        self.created_at = datetime.now()
        self.reviewed_at: Optional[datetime] = None
        self.admin_reply: str = ""

    def __repr__(self):
        return f"<LeaveReport id={self.leave_id} status={self.status}>"


class Feedback:
    def __init__(self, feedback_id: str, user_id: str, user_role: str,
                 feedback_message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.user_role = user_role
        self.feedback_message = feedback_message
        self.status = FeedbackStatus.PENDING
        self.reply: str = ""
        self.created_at = datetime.now()
        self.replied_at: Optional[datetime] = None

    def __repr__(self):
        return f"<Feedback id={self.feedback_id} status={self.status}>"


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 exam_score: float, assignment_score: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.exam_score = exam_score
        self.assignment_score = assignment_score
        self.total_score = exam_score + assignment_score
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def update_scores(self, exam_score: float, assignment_score: float):
        self.exam_score = exam_score
        self.assignment_score = assignment_score
        self.total_score = exam_score + assignment_score
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"<Result student={self.student_id} subject={self.subject_id} total={self.total_score}>"


# ─────────────────────────────────────────────
# In-Memory Database
# ─────────────────────────────────────────────

class Database:
    def __init__(self):
        self.users: dict[str, User] = {}
        self.sessions: dict[str, Session] = {}
        self.courses: dict[str, Course] = {}
        self.subjects: dict[str, Subject] = {}
        self.staff: dict[str, Staff] = {}
        self.students: dict[str, Student] = {}
        self.attendances: dict[str, Attendance] = {}
        self.attendance_reports: dict[str, AttendanceReport] = {}
        self.leave_reports: dict[str, LeaveReport] = {}
        self.feedbacks: dict[str, Feedback] = {}
        self.results: dict[str, Result] = {}

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Services
# ─────────────────────────────────────────────

class AuthService:
    def __init__(self, db: Database):
        self.db = db
        self.current_user: Optional[User] = None

    def register(self, username: str, password: str, email: str,
                 role: str, first_name: str, last_name: str) -> User:
        for user in self.db.users.values():
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists.")
            if user.email == email:
                raise ValueError(f"Email '{email}' already exists.")
        user_id = self.db.generate_id()
        user = User(user_id, username, password, email, role, first_name, last_name)
        self.db.users[user_id] = user
        return user

    def login(self, username: str, password: str) -> Optional[User]:
        for user in self.db.users.values():
            if user.username == username and user.verify_password(password):
                if not user.is_active:
                    raise PermissionError("Account is deactivated.")
                self.current_user = user
                return user
        return None

    def logout(self):
        self.current_user = None

    def get_current_user(self) -> Optional[User]:
        return self.current_user


class SessionService:
    def __init__(self, db: Database):
        self.db = db

    def add_session(self, session_name: str, start_year: int, end_year: int) -> Session:
        if start_year >= end_year:
            raise ValueError("Start year must be less than end year.")
        session_id = self.db.generate_id()
        session = Session(session_id, session_name, start_year, end_year)
        self.db.sessions[session_id] = session
        return session

    def update_session(self, session_id: str, session_name: Optional[str] = None,
                       start_year: Optional[int] = None, end_year: Optional[int] = None) -> Session:
        session = self.db.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")
        if session_name:
            session.session_name = session_name
        if start_year:
            session.start_year = start_year
        if end_year:
            session.end_year = end_year
        if session.start_year >= session.end_year:
            raise ValueError("Start year must be less than end year.")
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self.db.sessions:
            raise ValueError(f"Session '{session_id}' not found.")
        del self.db.sessions[session_id]
        return True

    def get_all_sessions(self) -> list[Session]:
        return list(self.db.sessions.values())

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.db.sessions.get(session_id)


class CourseService:
    def __init__(self, db: Database):
        self.db = db

    def add_course(self, course_name: str, description: str = "") -> Course:
        for c in self.db.courses.values():
            if c.course_name == course_name:
                raise ValueError(f"Course '{course_name}' already exists.")
        course_id = self.db.generate_id()
        course = Course(course_id, course_name, description)
        self.db.courses[course_id] = course
        return course

    def update_course(self, course_id: str, course_name: Optional[str] = None,
                      description: Optional[str] = None) -> Course:
        course = self.db.courses.get(course_id)
        if not course:
            raise ValueError(f"Course '{course_id}' not found.")
        if course_name:
            course.course_name = course_name
        if description is not None:
            course.description = description
        return course

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self.db.courses:
            raise ValueError(f"Course '{course_id}' not found.")
        del self.db.courses[course_id]
        return True

    def get_all_courses(self) -> list[Course]:
        return list(self.db.courses.values())

    def get_course(self, course_id: str) -> Optional[Course]:
        return self.db.courses.get(course_id)


class SubjectService:
    def __init__(self, db: Database):
        self.db = db

    def add_subject(self, subject_name: str, course_id: str, staff_id: str) -> Subject:
        if course_id not in self.db.courses:
            raise ValueError(f"Course '{course_id}' not found.")
        if staff_id not in self.db.staff:
            raise ValueError(f"Staff '{staff_id}' not found.")
        subject_id = self.db.generate_id()
        subject = Subject(subject_id, subject_name, course_id, staff_id)
        self.db.subjects[subject_id] = subject
        return subject

    def update_subject(self, subject_id: str, subject_name: Optional[str] = None,
                       course_id: Optional[str] = None, staff_id: Optional[str] = None) -> Subject:
        subject = self.db.subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject '{subject_id}' not found.")
        if subject_name:
            subject.subject_name = subject_name
        if course_id:
            if course_id not in self.db.courses:
                raise ValueError(f"Course '{course_id}' not found.")
            subject.course_id = course_id
        if staff_id:
            if staff_id not in self.db.staff:
                raise ValueError(f"Staff '{staff_id}' not found.")
            subject.staff_id = staff_id
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id not in self.db.subjects:
            raise ValueError(f"Subject '{subject_id}' not found.")
        del self.db.subjects[subject_id]
        return True

    def get_all_subjects(self) -> list[Subject]:
        return list(self.db.subjects.values())

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        return self.db.subjects.get(subject_id)

    def get_subjects_by_course(self, course_id: str) -> list[Subject]:
        return [s for s in self.db.subjects.values() if s.course_id == course_id]

    def get_subjects_by_staff(self, staff_id: str) -> list[Subject]:
        return [s for s in self.db.subjects.values() if s.staff_id == staff_id]


class StaffService:
    def __init__(self, db: Database, auth_service: AuthService):
        self.db = db
        self.auth_service = auth_service

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str, address: str = "") -> Staff:
        user = self.auth_service.register(username, password, email,
                                          UserRole.STAFF, first_name, last_name)
        staff_id = self.db.generate_id()
        staff = Staff(staff_id, user.user_id, address)
        self.db.staff[staff_id] = staff
        return staff

    def update_staff(self, staff_id: str, first_name: Optional[str] = None,
                     last_name: Optional[str] = None, email: Optional[str] = None,
                     address: Optional[str] = None) -> Staff:
        staff = self.db.staff.get(staff_id)
        if not staff:
            raise ValueError(f"Staff '{staff_id}' not found.")
        user = self.db.users.get(staff.user_id)
        if not user:
            raise ValueError(f"User for staff '{staff_id}' not found.")
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        if address is not None:
            staff.address = address
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        staff = self.db.staff.get(staff_id)
        if not staff:
            raise ValueError(f"Staff '{staff_id}' not found.")
        user = self.db.users.get(staff.user_id)
        if user:
            del self.db.users[staff.user_id]
        del self.db.staff[staff_id]
        return True

    def get_all_staff(self) -> list[Staff]:
        return list(self.db.staff.values())

    def get_staff(self, staff_id: str) -> Optional[Staff]:
        return self.db.staff.get(staff_id)

    def get_staff_by_user_id(self, user_id: str) -> Optional[Staff]:
        for s in self.db.staff.values():
            if s.user_id == user_id:
                return s
        return None

    def get_staff_summary(self, staff_id: str) -> dict:
        staff = self.db.staff.get(staff_id)
        if not staff:
            raise ValueError(f"Staff '{staff_id}' not found.")
        subjects = [s for s in self.db.subjects.values() if s.staff_id == staff_id]
        leave_reports = [lr for lr in self.db.leave_reports.values()
                         if lr.user_id == staff.user_id and lr.user_role == UserRole.STAFF]
        feedbacks = [f for f in self.db.feedbacks.values()
                     if f.user_id == staff.user_id and f.user_role == UserRole.STAFF]
        student_ids = set()
        for subject in subjects:
            for ar in self.db.attendance_reports.values():
                att = self.db.attendances.get(ar.attendance_id)
                if att and att.subject_id == subject.subject_id:
                    student_ids.add(ar.student_id)
        return {
            "staff_id": staff_id,
            "total_subjects": len(subjects),
            "total_students": len(student_ids),
            "total_leave_requests": len(leave_reports),
            "pending_leaves": sum(1 for lr in leave_reports if lr.status == LeaveStatus.PENDING),
            "approved_leaves": sum(1 for lr in leave_reports if lr.status == LeaveStatus.APPROVED),
            "rejected_leaves": sum(1 for lr in leave_reports if lr.status == LeaveStatus.REJECTED),
            "total_feedbacks": len(feedbacks),
        }


class StudentService:
    def __init__(self, db: Database, auth_service: AuthService):
        self.db = db
        self.auth_service = auth_service

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str, course_id: str,
                    session_id: str, gender: str = "", address: str = "") -> Student:
        if course_id not in self.db.courses:
            raise ValueError(f"Course '{course_id}' not found.")
        if session_id not in self.db.sessions:
            raise ValueError(f"Session '{session_id}' not found.")
        user = self.auth_service.register(username, password, email,
                                          UserRole.STUDENT, first_name, last_name)
        student_id = self.db.generate_id()
        student = Student(student_id, user.user_id, course_id, session_id, gender, address)
        self.db.students[student_id] = student
        return student

    def update_student(self, student_id: str, first_name: Optional[str] = None,
                       last_name: Optional[str] = None, email: Optional[str] = None,
                       course_id: Optional[str] = None, session_id: Optional[str] = None,
                       gender: Optional[str] = None, address: Optional[str] = None) -> Student:
        student = self.db.students.get(student_id)
        if not student:
            raise ValueError(f"Student '{student_id}' not found.")
        user = self.db.users.get(student.user_id)
        if not user:
            raise ValueError(f"User for student '{student_id}' not found.")
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        if course_id:
            if course_id not in self.db.courses:
                raise ValueError(f"Course '{course_id}' not found.")
            student.course_id = course_id
        if session_id:
            if session_id not in self.db.sessions:
                raise ValueError(f"Session '{session_id}' not found.")
            student.session_id = session_id
        if gender is not None:
            student.gender = gender
        if address is not None:
            student.address = address
        return student

    def delete_student(self, student_id: str) -> bool:
        student = self.db.students.get(student_id)
        if not student:
            raise ValueError(f"Student '{student_id}' not found.")
        user = self.db.users.get(student.user_id)
        if user:
            del self.db.users[student.user_id]
        del self.db.students[student_id]
        return True

    def get_all_students(self) -> list[Student]:
        return list(self.db.students.values())

    def get_student(self, student_id: str) -> Optional[Student]:
        return self.db.students.get(student_id)

    def get_student_by_user_id(self, user_id: str) -> Optional[Student]:
        for s in self.db.students.values():
            if s.user_id == user_id:
                return s
        return None

    def get_students_by_course(self, course_id: str) -> list[Student]:
        return [s for s in self.db.students.values() if s.course_id == course_id]

    def get_student_summary(self, student_id: str) -> dict:
        student = self.db.students.get(student_id)
        if not student:
            raise ValueError(f"Student '{student_id}' not found.")
        reports = [ar for ar in self.db.attendance_reports.values()
                   if ar.student_id == student_id]
        present = sum(1 for r in reports if r.status == AttendanceStatus.PRESENT)
        absent = sum(1 for r in reports if r.status == AttendanceStatus.ABSENT)
        leave_reports = [lr for lr in self.db.leave_reports.values()
                         if lr.user_id == student.user_id and lr.user_role == UserRole.STUDENT]
        results = [r for r in self.db.results.values() if r.student_id == student_id]
        subjects = [s for s in self.db.subjects.values() if s.course_id == student.course_id]
        return {
            "student_id": student_id,
            "total_attendance": len(reports),
            "present_count": present,
            "absent_count": absent,
            "attendance_percentage": (present / len(reports) * 100) if reports else 0,
            "total_subjects": len(subjects),
            "total_results": len(results),
            "total_leave_requests": len(leave_reports),
            "pending_leaves": sum(1 for lr in leave_reports if lr.status == LeaveStatus.PENDING),
            "approved_leaves": sum(1 for lr in leave_reports if lr.status == LeaveStatus.APPROVED),
            "rejected_leaves": sum(1 for lr in leave_reports if lr.status == LeaveStatus.REJECTED),
        }


class AttendanceService:
    def __init__(self, db: Database):
        self.db = db

    def take_attendance(self, subject_id: str, session_id: str,
                        attendance_date: date, staff_id: str,
                        student_statuses: dict[str, str]) -> Attendance:
        if subject_id not in self.db.subjects:
            raise ValueError(f"Subject '{subject_id}' not found.")
        if session_id not in self.db.sessions:
            raise ValueError(f"Session '{session_id}' not found.")
        attendance_id = self.db.generate_id()
        attendance = Attendance(attendance_id, subject_id, session_id,
                                attendance_date, staff_id)
        self.db.attendances[attendance_id] = attendance
        for student_id, status in student_statuses.items():
            if student_id not in self.db.students:
                raise ValueError(f"Student '{student_id}' not found.")
            if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
                raise ValueError(f"Invalid status '{status}'.")
            report_id = self.db.generate_id()
            report = AttendanceReport(report_id, student_id, attendance_id, status)
            self.db.attendance_reports[report_id] = report
        return attendance

    def update_attendance(self, attendance_id: str,
                          student_statuses: dict[str, str]) -> Attendance:
        attendance = self.db.attendances.get(attendance_id)
        if not attendance:
            raise ValueError(f"Attendance '{attendance_id}' not found.")
        existing_reports = {ar.student_id: ar for ar in self.db.attendance_reports.values()
                            if ar.attendance_id == attendance_id}
        for student_id, status in student_statuses.items():
            if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
                raise ValueError(f"Invalid status '{status}'.")
            if student_id in existing_reports:
                existing_reports[student_id].status = status
            else:
                if student_id not in self.db.students:
                    raise ValueError(f"Student '{student_id}' not found.")
                report_id = self.db.generate_id()
                report = AttendanceReport(report_id, student_id, attendance_id, status)
                self.db.attendance_reports[report_id] = report
        return attendance

    def get_attendance_by_subject(self, subject_id: str) -> list[Attendance]:
        return [a for a in self.db.attendances.values() if a.subject_id == subject_id]

    def get_attendance_by_student(self, student_id: str) -> list[dict]:
        reports = [ar for ar in self.db.attendance_reports.values()
                   if ar.student_id == student_id]
        result = []
        for report in reports:
            attendance = self.db.attendances.get(report.attendance_id)
            if attendance:
                subject = self.db.subjects.get(attendance.subject_id)
                result.append({
                    "report_id": report.report_id,
                    "attendance_id": report.attendance_id,
                    "subject_name": subject.subject_name if subject else "Unknown",
                    "date": attendance.attendance_date,
                    "status": report.status,
                })
        return result

    def get_attendance_report_by_subject_and_student(
            self, subject_id: str, student_id: str) -> list[dict]:
        attendances = {a.attendance_id: a for a in self.db.attendances.values()
                       if a.subject_id == subject_id}
        reports = [ar for ar in self.db.attendance_reports.values()
                   if ar.student_id == student_id and ar.attendance_id in attendances]
        result = []
        for report in reports:
            attendance = attendances[report.attendance_id]
            result.append({
                "date": attendance.attendance_date,
                "status": report.status,
            })
        return result

    def get_all_attendance(self) -> list[Attendance]:
        return list(self.db.attendances.values())


class LeaveService:
    def __init__(self, db: Database):
        self.db = db

    def apply_leave(self, user_id: str, user_role: str,
                    leave_date: str, leave_message: str) -> LeaveReport:
        if user_id not in self.db.users:
            raise ValueError(f"User '{user_id}' not found.")
        leave_id = self.db.generate_id()
        leave = LeaveReport(leave_id, user_id, user_role, leave_date, leave_message)
        self.db.leave_reports[leave_id] = leave
        return leave

    def review_leave(self, leave_id: str, status: str, admin_reply: str = "") -> LeaveReport:
        leave = self.db.leave_reports.get(leave_id)
        if not leave:
            raise ValueError(f"Leave report '{leave_id}' not found.")
        if status not in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
            raise ValueError(f"Invalid status '{status}'. Must be 'approved' or 'rejected'.")
        leave.status = status
        leave.admin_reply = admin_reply
        leave.reviewed_at = datetime.now()
        return leave

    def get_all_leave_reports(self) -> list[LeaveReport]:
        return list(self.db.leave_reports.values())

    def get_leave_reports_by_user(self, user_id: str) -> list[LeaveReport]:
        return [lr for lr in self.db.leave_reports.values() if lr.user_id == user_id]

    def get_pending_leave_reports(self) -> list[LeaveReport]:
        return [lr for lr in self.db.leave_reports.values()
                if lr.status == LeaveStatus.PENDING]

    def get_leave_report(self, leave_id: str) -> Optional[LeaveReport]:
        return self.db.leave_reports.get(leave_id)


class FeedbackService:
    def __init__(self, db: Database):
        self.db = db

    def send_feedback(self, user_id: str, user_role: str,
                      feedback_message: str) -> Feedback:
        if user_id not in self.db.users:
            raise ValueError(f"User '{user_id}' not found.")
        feedback_id = self.db.generate_id()
        feedback = Feedback(feedback_id, user_id, user_role, feedback_message)
        self.db.feedbacks[feedback_id] = feedback
        return feedback

    def reply_feedback(self, feedback_id: str, reply: str) -> Feedback:
        feedback = self.db.feedbacks.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback '{feedback_id}' not found.")
        feedback.reply = reply
        feedback.status = FeedbackStatus.REPLIED
        feedback.replied_at = datetime.now()
        return feedback

    def get_all_feedbacks(self) -> list[Feedback]:
        return list(self.db.feedbacks.values())

    def get_feedbacks_by_user(self, user_id: str) -> list[Feedback]:
        return [f for f in self.db.feedbacks.values() if f.user_id == user_id]

    def get_pending_feedbacks(self) -> list[Feedback]:
        return [f for f in self.db.feedbacks.values()
                if f.status == FeedbackStatus.PENDING]

    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        return self.db.feedbacks.get(feedback_id)


class ResultService:
    def __init__(self, db: Database):
        self.db = db

    def add_result(self, student_id: str, subject_id: str,
                   exam_score: float, assignment_score: float) -> Result:
        if student_id not in self.db.students:
            raise ValueError(f"Student '{student_id}' not found.")
        if subject_id not in self.db.subjects:
            raise ValueError(f"Subject '{subject_id}' not found.")
        for r in self.db.results.values():
            if r.student_id == student_id and r.subject_id == subject_id:
                raise ValueError(f"Result for student '{student_id}' and subject '{subject_id}' already exists. Use update.")
        result_id = self.db.generate_id()
        result = Result(result_id, student_id, subject_id, exam_score, assignment_score)
        self.db.results[result_id] = result
        return result

    def update_result(self, result_id: str, exam_score: float,
                      assignment_score: float) -> Result:
        result = self.db.results.get(result_id)
        if not result:
            raise ValueError(f"Result '{result_id}' not found.")
        result.update_scores(exam_score, assignment_score)
        return result

    def get_results_by_student(self, student_id: str) -> list[Result]:
        return [r for r in self.db.results.values() if r.student_id == student_id]

    def get_results_by_subject(self, subject_id: str) -> list[Result]:
        return [r for r in self.db.results.values() if r.subject_id == subject_id]

    def get_result(self, result_id: str) -> Optional[Result]:
        return self.db.results.get(result_id)

    def get_result_by_student_and_subject(self, student_id: str,
                                          subject_id: str) -> Optional[Result]:
        for r in self.db.results.values():
            if r.student_id == student_id and r.subject_id == subject_id:
                return r
        return None


class AdminService:
    def __init__(self, db: Database):
        self.db = db

    def get_overall_summary(self) -> dict:
        total_students = len(self.db.students)
        total_staff = len(self.db.staff)
        total_courses = len(self.db.courses)
        total_subjects = len(self.db.subjects)
        total_sessions = len(self.db.sessions)
        total_leave_reports = len(self.db.leave_reports)
        pending_leaves = sum(1 for lr in self.db.leave_reports.values()
                             if lr.status == LeaveStatus.PENDING)
        approved_leaves = sum(1 for lr in self.db.leave_reports.values()
                              if lr.status == LeaveStatus.APPROVED)
        rejected_leaves = sum(1 for lr in self.db.leave_reports.values()
                              if lr.status == LeaveStatus.REJECTED)
        total_feedbacks = len(self.db.feedbacks)
        pending_feedbacks = sum(1 for f in self.db.feedbacks.values()
                                if f.status == FeedbackStatus.PENDING)
        total_attendance = len(self.db.attendance_reports)
        present_count = sum(1 for ar in self.db.attendance_reports.values()
                            if ar.status == AttendanceStatus.PRESENT)
        absent_count = total_attendance - present_count
        return {
            "total_students": total_students,
            "total_staff": total_staff,
            "total_courses": total_courses,
            "total_subjects": total_subjects,
            "total_sessions": total_sessions,
            "total_leave_reports": total_leave_reports,
            "pending_leaves": pending_leaves,
            "approved_leaves": approved_leaves,
            "rejected_leaves": rejected_leaves,
            "total_feedbacks": total_feedbacks,
            "pending_feedbacks": pending_feedbacks,
            "total_attendance_records": total_attendance,
            "present_count": present_count,
            "absent_count": absent_count,
            "attendance_percentage": (present_count / total_attendance * 100)
            if total_attendance else 0,
        }

    def get_student_performance_summary(self) -> list[dict]:
        summaries = []
        for student in self.db.students.values():
            user = self.db.users.get(student.user_id)
            reports = [ar for ar in self.db.attendance_reports.values()
                       if ar.student_id == student.student_id]
            present = sum(1 for r in reports if r.status == AttendanceStatus.PRESENT)
            results = [r for r in self.db.results.values()
                       if r.student_id == student.student_id]
            avg_score = (sum(r.total_score for r in results) / len(results)) if results else 0
            summaries.append({
                "student_id": student.student_id,
                "name": user.get_full_name() if user else "Unknown",
                "course_id": student.course_id,
                "attendance_percentage": (present / len(reports) * 100) if reports else 0,
                "average_score": avg_score,
            })
        return summaries

    def get_staff_performance_summary(self) -> list[dict]:
        summaries = []
        for staff in self.db.staff.values():
            user = self.db.users.get(staff.user_id)
            subjects = [s for s in self.db.subjects.values()
                        if s.staff_id == staff.staff_id]
            student_ids = set()
            for subject in subjects:
                for ar in self.db.attendance_reports.values():
                    att = self.db.attendances.get(ar.attendance_id)
                    if att and att.subject_id == subject.subject_id:
                        student_ids.add(ar.student_id)
            summaries.append({
                "staff_id": staff.staff_id,
                "name": user.get_full_name() if user else "Unknown",
                "total_subjects": len(subjects),
                "total_students_taught": len(student_ids),
            })
        return summaries


# ─────────────────────────────────────────────
# Main Application / Facade
# ─────────────────────────────────────────────

class StudentManagementSystem:
    def __init__(self):
        self.db = Database()
        self.auth_service = AuthService(self.db)
        self.session_service = SessionService(self.db)
        self.course_service = CourseService(self.db)
        self.subject_service = SubjectService(self.db)
        self.staff_service = StaffService(self.db, self.auth_service)
        self.student_service = StudentService(self.db, self.auth_service)
        self.attendance_service = AttendanceService(self.db)
        self.leave_service = LeaveService(self.db)
        self.feedback_service = FeedbackService(self.db)
        self.result_service = ResultService(self.db)
        self.admin_service = AdminService(self.db)
        self._bootstrap_admin()

    def _bootstrap_admin(self):
        try:
            admin_user = self.auth_service.register(
                username="admin",
                password="admin123",
                email="admin@school.com",
                role=UserRole.ADMIN,
                first_name="System",
                last_name="Admin"
            )
        except ValueError:
            pass

    def login(self, username: str, password: str) -> Optional[User]:
        return self.auth_service.login(username, password)

    def logout(self):
        self.auth_service.logout()

    def get_current_user(self) -> Optional[User]:
        return self.auth_service.get_current_user()

    def _require_role(self, *roles: str):
        user = self.get_current_user()
        if not user:
            raise PermissionError("You must be logged in.")
        if user.role not in roles:
            raise PermissionError(f"Access denied. Required roles: {roles}")
        return user

    # ── Admin Operations ──────────────────────

    def admin_get_summary(self) -> dict:
        self._require_role(UserRole.ADMIN)
        return self.admin_service.get_overall_summary()

    def admin_get_student_performance(self) -> list[dict]:
        self._require_role(UserRole.ADMIN)
        return self.admin_service.get_student_performance_summary()

    def admin_get_staff_performance(self) -> list[dict]:
        self._require_role(UserRole.ADMIN)
        return self.admin_service.get_staff_performance_summary()

    def admin_add_staff(self, username: str, password: str, email: str,
                        first_name: str, last_name: str, address: str = "") -> Staff:
        self._require_role(UserRole.ADMIN)
        return self.staff_service.add_staff(username, password, email,
                                            first_name, last_name, address)

    def admin_update_staff(self, staff_id: str, **kwargs) -> Staff:
        self._require_role(UserRole.ADMIN)
        return self.staff_service.update_staff(staff_id, **kwargs)

    def admin_delete_staff(self, staff_id: str) -> bool:
        self._require_role(UserRole.ADMIN)
        return self.staff_service.delete_staff(staff_id)

    def admin_get_all_staff(self) -> list[Staff]:
        self._require_role(UserRole.ADMIN)
        return self.staff_service.get_all_staff()

    def admin_add_student(self, username: str, password: str, email: str,
                          first_name: str, last_name: str, course_id: str,
                          session_id: str, gender: str = "", address: str = "") -> Student:
        self._require_role(UserRole.ADMIN)
        return self.student_service.add_student(username, password, email,
                                                first_name, last_name, course_id,
                                                session_id, gender, address)

    def admin_update_student(self, student_id: str, **kwargs) -> Student:
        self._require_role(UserRole.ADMIN)
        return self.student_service.update_student(student_id, **kwargs)

    def admin_delete_student(self, student_id: str) -> bool:
        self._require_role(UserRole.ADMIN)
        return self.student_service.delete_student(student_id)

    def admin_get_all_students(self) -> list[Student]:
        self._require_role(UserRole.ADMIN)
        return self.student_service.get_all_students()

    def admin_add_course(self, course_name: str, description: str = "") -> Course:
        self._require_role(UserRole.ADMIN)
        return self.course_service.add_course(course_name, description)

    def admin_update_course(self, course_id: str, **kwargs) -> Course:
        self._require_role(UserRole.ADMIN)
        return self.course_service.update_course(course_id, **kwargs)

    def admin_delete_course(self, course_id: str) -> bool:
        self._require_role(UserRole.ADMIN)
        return self.course_service.delete_course(course_id)

    def admin_get_all_courses(self) -> list[Course]:
        self._require_role(UserRole.ADMIN)
        return self.course_service.get_all_courses()

    def admin_add_subject(self, subject_name: str, course_id: str,
                          staff_id: str) -> Subject:
        self._require_role(UserRole.ADMIN)
        return self.subject_service.add_subject(subject_name, course_id, staff_id)

    def admin_update_subject(self, subject_id: str, **kwargs) -> Subject:
        self._require_role(UserRole.ADMIN)
        return self.subject_service.update_subject(subject_id, **kwargs)

    def admin_delete_subject(self, subject_id: str) -> bool:
        self._require_role(UserRole.ADMIN)
        return self.subject_service.delete_subject(subject_id)

    def admin_get_all_subjects(self) -> list[Subject]:
        self._require_role(UserRole.ADMIN)
        return self.subject_service.get_all_subjects()

    def admin_add_session(self, session_name: str, start_year: int,
                          end_year: int) -> Session:
        self._require_role(UserRole.ADMIN)
        return self.session_service.add_session(session_name, start_year, end_year)

    def admin_update_session(self, session_id: str, **kwargs) -> Session:
        self._require_role(UserRole.ADMIN)
        return self.session_service.update_session(session_id, **kwargs)

    def admin_delete_session(self, session_id: str) -> bool:
        self._require_role(UserRole.ADMIN)
        return self.session_service.delete_session(session_id)

    def admin_get_all_sessions(self) -> list[Session]:
        self._require_role(UserRole.ADMIN)
        return self.session_service.get_all_sessions()

    def admin_view_student_attendance(self, student_id: Optional[str] = None) -> list:
        self._require_role(UserRole.ADMIN)
        if student_id:
            return self.attendance_service.get_attendance_by_student(student_id)
        return self.attendance_service.get_all_attendance()

    def admin_review_leave(self, leave_id: str, status: str,
                           admin_reply: str = "") -> LeaveReport:
        self._require_role(UserRole.ADMIN)
        return self.leave_service.review_leave(leave_id, status, admin_reply)

    def admin_get_all_leave_reports(self) -> list[LeaveReport]:
        self._require_role(UserRole.ADMIN)
        return self.leave_service.get_all_leave_reports()

    def admin_reply_feedback(self, feedback_id: str, reply: str) -> Feedback:
        self._require_role(UserRole.ADMIN)
        return self.feedback_service.reply_feedback(feedback_id, reply)

    def admin_get_all_feedbacks(self) -> list[Feedback]:
        self._require_role(UserRole.ADMIN)
        return self.feedback_service.get_all_feedbacks()

    # ── Staff Operations ──────────────────────

    def staff_get_summary(self) -> dict:
        user = self._require_role(UserRole.STAFF)
        staff = self.staff_service.get_staff_by_user_id(user.user_id)
        if not staff:
            raise ValueError("Staff profile not found.")
        return self.staff_service.get_staff_summary(staff.staff_id)

    def staff_take_attendance(self, subject_id: str, session_id: str,
                              attendance_date: date,
                              student_statuses: dict[str, str]) -> Attendance:
        user = self._require_role(UserRole.STAFF)
        staff = self.staff_service.get_staff_by_user_id(user.user_id)
        if not staff:
            raise ValueError("Staff profile not found.")
        subject = self.subject_service.get_subject(subject_id)
        if not subject or subject.staff_id != staff.staff_id:
            raise PermissionError("You can only take attendance for your own subjects.")
        return self.attendance_service.take_attendance(
            subject_id, session_id, attendance_date, staff.staff_id, student_statuses)

    def staff_update_attendance(self, attendance_id: str,
                                student_statuses: dict[str, str]) -> Attendance:
        user = self._require_role(UserRole.STAFF)
        staff = self.staff_service.get_staff_by_user_id(user.user_id)
        if not staff:
            raise ValueError("Staff profile not found.")
        attendance = self.db.attendances.get(attendance_id)
        if not attendance or attendance.staff_id != staff.staff_id:
            raise PermissionError("You can only update attendance you created.")
        return self.attendance_service.update_attendance(attendance_id, student_statuses)

    def staff_add_result(self, student_id: str, subject_id: str,
                         exam_score: float, assignment_score: float) -> Result:
        user = self._require_role(UserRole.STAFF)
        staff = self.staff_service.get_staff_by_user_id(user.user_id)
        if not staff:
            raise ValueError("Staff profile not found.")
        subject = self.subject_service.get_subject(subject_id)
        if not subject or subject.staff_id != staff.staff_id:
            raise PermissionError("You can only add results for your own subjects.")
        return self.result_service.add_result(student_id, subject_id,
                                              exam_score, assignment_score)

    def staff_update_result(self, result_id: str, exam_score: float,
                            assignment_score: float) -> Result:
        user = self._require_role(UserRole.STAFF)
        staff = self.staff_service.get_staff_by_user_id(user.user_id)
        if not staff:
            raise ValueError("Staff profile not found.")
        result = self.result_service.get_result(result_id)
        if not result:
            raise ValueError(f"Result '{result_id}' not found.")
        subject = self.subject_service.get_subject(result.subject_id)
        if not subject or subject.staff_id != staff.staff_id:
            raise PermissionError("You can only update results for your own subjects.")
        return self.result_service.update_result(result_id, exam_score, assignment_score)

    def staff_apply_leave(self, leave_date: str, leave_message: str) -> LeaveReport:
        user = self._require_role(UserRole.STAFF)
        return self.leave_service.apply_leave(user.user_id, UserRole.STAFF,
                                              leave_date, leave_message)

    def staff_get_leave_reports(self) -> list[LeaveReport]:
        user = self._require_role(UserRole.STAFF)
        return self.leave_service.get_leave_reports_by_user(user.user_id)

    def staff_send_feedback(self, feedback_message: str) -> Feedback:
        user = self._require_role(UserRole.STAFF)
        return self.feedback_service.send_feedback(user.user_id, UserRole.STAFF,
                                                   feedback_message)

    def staff_get_feedbacks(self) -> list[Feedback]:
        user = self._require_role(UserRole.STAFF)
        return self.feedback_service.get_feedbacks_by_user(user.user_id)

    def staff_get_subjects(self) -> list[Subject]:
        user = self._require_role(UserRole.STAFF)
        staff = self.staff_service.get_staff_by_user_id(user.user_id)
        if not staff:
            raise ValueError("Staff profile not found.")
        return self.subject_service.get_subjects_by_staff(staff.staff_id)

    # ── Student Operations ────────────────────

    def student_get_summary(self) -> dict:
        user = self._require_role(UserRole.STUDENT)
        student = self.student_service.get_student_by_user_id(user.user_id)
        if not student:
            raise ValueError("Student profile not found.")
        return self.student_service.get_student_summary(student.student_id)

    def student_view_attendance(self) -> list[dict]:
        user = self._require_role(UserRole.STUDENT)
        student = self.student_service.get_student_by_user_id(user.user_id)
        if not student:
            raise ValueError("Student profile not found.")
        return self.attendance_service.get_attendance_by_student(student.student_id)

    def student_view_results(self) -> list[Result]:
        user = self._require_role(UserRole.STUDENT)
        student = self.student_service.get_student_by_user_id(user.user_id)
        if not student:
            raise ValueError("Student profile not found.")
        return self.result_service.get_results_by_student(student.student_id)

    def student_apply_leave(self, leave_date: str, leave_message: str) -> LeaveReport:
        user = self._require_role(UserRole.STUDENT)
        return self.leave_service.apply_leave(user.user_id, UserRole.STUDENT,
                                              leave_date, leave_message)

    def student_get_leave_reports(self) -> list[LeaveReport]:
        user = self._require_role(UserRole.STUDENT)
        return self.leave_service.get_leave_reports_by_user(user.user_id)

    def student_send_feedback(self, feedback_message: str) -> Feedback:
        user = self._require_role(UserRole.STUDENT)
        return self.feedback_service.send_feedback(user.user_id, UserRole.STUDENT,
                                                   feedback_message)

    def student_get_feedbacks(self) -> list[Feedback]:
        user = self._require_role(UserRole.STUDENT)
        return self.feedback_service.get_feedbacks_by_user(user.user_id)

    def student_get_subjects(self) -> list[Subject]:
        user = self._require_role(UserRole.STUDENT)
        student = self.student_service.get_student_by_user_id(user.user_id)
        if not student:
            raise ValueError("Student profile not found.")
        return self.subject_service.get_subjects_by_course(student.course_id)


# ─────────────────────────────────────────────
# Demo / Entry Point
# ─────────────────────────────────────────────

def main():
    sms = StudentManagementSystem()

    print("=" * 60)
    print("Student Management System - Demo")
    print("=" * 60)

    # Admin login
    admin = sms.login("admin", "admin123")
    print(f"\n[+] Logged in as: {admin.get_full_name()} ({admin.role})")

    # Add session
    session = sms.admin_add_session("2023-2024", 2023, 2024)
    print(f"[+] Session added: {session}")

    # Add course
    course = sms.admin_add_course("Computer Science", "CS Degree Program")
    print(f"[+] Course added: {course}")

    # Add staff
    staff = sms.admin_add_staff("john_doe", "pass123", "john@school.com",
                                "John", "Doe", "123 Main St")
    print(f"[+] Staff added: {staff}")

    # Add subject
    subject = sms.admin_add_subject("Data Structures", course.course_id, staff.staff_id)
    print(f"[+] Subject added: {subject}")

    # Add student
    student = sms.admin_add_student("jane_smith", "pass456", "jane@school.com",
                                    "Jane", "Smith", course.course_id,
                                    session.session_id, "Female", "456 Oak Ave")
    print(f"[+] Student added: {student}")

    # Admin summary
    summary = sms.admin_get_summary()
    print(f"\n[Admin Summary]")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    sms.logout()

    # Staff login
    staff_user = sms.login("john_doe", "pass123")
    print(f"\n[+] Logged in as: {staff_user.get_full_name()} ({staff_user.role})")

    # Take attendance
    student_statuses = {student.student_id: AttendanceStatus.PRESENT}
    attendance = sms.staff_take_attendance(
        subject.subject_id, session.session_id,
        date.today(), student_statuses)
    print(f"[+] Attendance taken: {attendance}")

    # Add result
    result = sms.staff_add_result(student.student_id, subject.subject_id, 75.0, 20.0)
    print(f"[+] Result added: {result}")

    # Apply leave
    leave = sms.staff_apply_leave("2024-01-15", "Medical appointment")
    print(f"[+] Leave applied: {leave}")

    # Send feedback
    feedback = sms.staff_send_feedback("The new curriculum is excellent!")
    print(f"[+] Feedback sent: {feedback}")

    # Staff summary
    staff_summary = sms.staff_get_summary()
    print(f"\n[Staff Summary]")
    for k, v in staff_summary.items():
        print(f"  {k}: {v}")

    sms.logout()

    # Student login
    student_user = sms.login("jane_smith", "pass456")
    print(f"\n[+] Logged in as: {student_user.get_full_name()} ({student_user.role})")

    # View attendance
    attendance_records = sms.student_view_attendance()
    print(f"[+] Attendance records: {attendance_records}")

    # View results
    results = sms.student_view_results()
    print(f"[+] Results: {results}")

    # Apply leave
    student_leave = sms.student_apply_leave("2024-01-20", "Family event")
    print(f"[+] Leave applied: {student_leave}")

    # Send feedback
    student_feedback = sms.student_send_feedback("Great teaching methods!")
    print(f"[+] Feedback sent: {student_feedback}")

    # Student summary
    student_summary = sms.student_get_summary()
    print(f"\n[Student Summary]")
    for k, v in student_summary.items():
        print(f"  {k}: {v}")

    sms.logout()

    # Admin reviews
    admin = sms.login("admin", "admin123")
    print(f"\n[+] Logged in as: {admin.get_full_name()} ({admin.role})")

    # Review leave
    updated_leave = sms.admin_review_leave(leave.leave_id, LeaveStatus.APPROVED,
                                           "Approved. Get well soon.")
    print(f"[+] Leave reviewed: {updated_leave} - Status: {updated_leave.status}")

    # Reply feedback
    replied_feedback = sms.admin_reply_feedback(feedback.feedback_id,
                                                "Thank you for your feedback!")
    print(f"[+] Feedback replied: {replied_feedback} - Status: {replied_feedback.status}")

    # Final summary
    final_summary = sms.admin_get_summary()
    print(f"\n[Final Admin Summary]")
    for k, v in final_summary.items():
        print(f"  {k}: {v}")

    sms.logout()
    print("\n[+] Demo completed successfully.")


if __name__ == "__main__":
    main()