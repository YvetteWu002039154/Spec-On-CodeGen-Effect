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
    UNREAD = "unread"
    READ = "read"
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


class Admin(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str):
        super().__init__(user_id, username, password, email,
                         UserRole.ADMIN, first_name, last_name)

    def __repr__(self):
        return f"<Admin id={self.user_id} name={self.get_full_name()}>"


class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self.course_id = course_id
        self.name = name
        self.description = description
        self.created_at = datetime.now()
        self.subjects: list = []

    def add_subject(self, subject) -> None:
        if subject not in self.subjects:
            self.subjects.append(subject)

    def remove_subject(self, subject) -> bool:
        if subject in self.subjects:
            self.subjects.remove(subject)
            return True
        return False

    def get_subjects(self) -> list:
        return list(self.subjects)

    def __repr__(self):
        return f"<Course id={self.course_id} name={self.name}>"


class Session:
    def __init__(self, session_id: str, start_year: int, end_year: int):
        if end_year <= start_year:
            raise ValueError("end_year must be greater than start_year")
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year
        self.created_at = datetime.now()

    def get_session_name(self) -> str:
        return f"{self.start_year}-{self.end_year}"

    def __repr__(self):
        return f"<Session {self.get_session_name()}>"


class Subject:
    def __init__(self, subject_id: str, name: str, course: Course,
                 staff=None, description: str = ""):
        self.subject_id = subject_id
        self.name = name
        self.course = course
        self.staff = staff
        self.description = description
        self.created_at = datetime.now()
        course.add_subject(self)

    def assign_staff(self, staff) -> None:
        self.staff = staff

    def remove_staff(self) -> None:
        self.staff = None

    def __repr__(self):
        return f"<Subject id={self.subject_id} name={self.name}>"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str,
                 address: str = ""):
        super().__init__(user_id, username, password, email,
                         UserRole.STAFF, first_name, last_name)
        self.address = address
        self.subjects: list = []
        self.leave_applications: list = []
        self.feedbacks: list = []

    def get_subjects(self) -> list:
        return list(self.subjects)

    def get_leave_applications(self) -> list:
        return list(self.leave_applications)

    def get_feedbacks(self) -> list:
        return list(self.feedbacks)

    def get_leave_status_summary(self) -> dict:
        summary = {
            LeaveStatus.PENDING: 0,
            LeaveStatus.APPROVED: 0,
            LeaveStatus.REJECTED: 0
        }
        for leave in self.leave_applications:
            summary[leave.status] += 1
        return summary

    def __repr__(self):
        return f"<Staff id={self.user_id} name={self.get_full_name()}>"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str,
                 course: Course, session: Session,
                 address: str = "", gender: str = ""):
        super().__init__(user_id, username, password, email,
                         UserRole.STUDENT, first_name, last_name)
        self.course = course
        self.session = session
        self.address = address
        self.gender = gender
        self.attendance_records: list = []
        self.results: list = []
        self.leave_applications: list = []
        self.feedbacks: list = []

    def get_attendance_records(self) -> list:
        return list(self.attendance_records)

    def get_results(self) -> list:
        return list(self.results)

    def get_leave_applications(self) -> list:
        return list(self.leave_applications)

    def get_feedbacks(self) -> list:
        return list(self.feedbacks)

    def get_attendance_summary(self) -> dict:
        total = len(self.attendance_records)
        present = sum(1 for a in self.attendance_records
                      if a.status == AttendanceStatus.PRESENT)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0.0
        return {
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 2)
        }

    def get_leave_status_summary(self) -> dict:
        summary = {
            LeaveStatus.PENDING: 0,
            LeaveStatus.APPROVED: 0,
            LeaveStatus.REJECTED: 0
        }
        for leave in self.leave_applications:
            summary[leave.status] += 1
        return summary

    def __repr__(self):
        return f"<Student id={self.user_id} name={self.get_full_name()}>"


class Attendance:
    def __init__(self, attendance_id: str, student: Student,
                 subject: Subject, date_of_attendance: date,
                 status: str, staff: Staff):
        self.attendance_id = attendance_id
        self.student = student
        self.subject = subject
        self.date_of_attendance = date_of_attendance
        self.status = status
        self.staff = staff
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        student.attendance_records.append(self)

    def update_status(self, status: str) -> None:
        if status not in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
            raise ValueError(f"Invalid attendance status: {status}")
        self.status = status
        self.updated_at = datetime.now()

    def __repr__(self):
        return (f"<Attendance id={self.attendance_id} "
                f"student={self.student.get_full_name()} "
                f"date={self.date_of_attendance} status={self.status}>")


class Result:
    def __init__(self, result_id: str, student: Student,
                 subject: Subject, exam_score: float,
                 assignment_score: float, staff: Staff):
        if not (0 <= exam_score <= 100):
            raise ValueError("exam_score must be between 0 and 100")
        if not (0 <= assignment_score <= 100):
            raise ValueError("assignment_score must be between 0 and 100")
        self.result_id = result_id
        self.student = student
        self.subject = subject
        self.exam_score = exam_score
        self.assignment_score = assignment_score
        self.staff = staff
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        student.results.append(self)

    def get_total_score(self) -> float:
        return round((self.exam_score + self.assignment_score) / 2, 2)

    def get_grade(self) -> str:
        total = self.get_total_score()
        if total >= 90:
            return "A+"
        elif total >= 80:
            return "A"
        elif total >= 70:
            return "B"
        elif total >= 60:
            return "C"
        elif total >= 50:
            return "D"
        else:
            return "F"

    def update_scores(self, exam_score: float, assignment_score: float) -> None:
        if not (0 <= exam_score <= 100):
            raise ValueError("exam_score must be between 0 and 100")
        if not (0 <= assignment_score <= 100):
            raise ValueError("assignment_score must be between 0 and 100")
        self.exam_score = exam_score
        self.assignment_score = assignment_score
        self.updated_at = datetime.now()

    def __repr__(self):
        return (f"<Result id={self.result_id} "
                f"student={self.student.get_full_name()} "
                f"subject={self.subject.name} "
                f"total={self.get_total_score()} grade={self.get_grade()}>")


class LeaveApplication:
    def __init__(self, leave_id: str, applicant,
                 start_date: date, end_date: date,
                 reason: str, leave_type: str = "general"):
        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")
        self.leave_id = leave_id
        self.applicant = applicant
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.leave_type = leave_type
        self.status = LeaveStatus.PENDING
        self.admin_reply: Optional[str] = None
        self.reviewed_by: Optional[Admin] = None
        self.reviewed_at: Optional[datetime] = None
        self.created_at = datetime.now()
        applicant.leave_applications.append(self)

    def get_duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def approve(self, admin: Admin, reply: str = "") -> None:
        self.status = LeaveStatus.APPROVED
        self.admin_reply = reply
        self.reviewed_by = admin
        self.reviewed_at = datetime.now()

    def reject(self, admin: Admin, reply: str = "") -> None:
        self.status = LeaveStatus.REJECTED
        self.admin_reply = reply
        self.reviewed_by = admin
        self.reviewed_at = datetime.now()

    def __repr__(self):
        return (f"<LeaveApplication id={self.leave_id} "
                f"applicant={self.applicant.get_full_name()} "
                f"status={self.status}>")


class Feedback:
    def __init__(self, feedback_id: str, sender,
                 message: str, subject_line: str = ""):
        self.feedback_id = feedback_id
        self.sender = sender
        self.message = message
        self.subject_line = subject_line
        self.status = FeedbackStatus.UNREAD
        self.reply: Optional[str] = None
        self.replied_by: Optional[Admin] = None
        self.replied_at: Optional[datetime] = None
        self.created_at = datetime.now()
        sender.feedbacks.append(self)

    def mark_as_read(self) -> None:
        if self.status == FeedbackStatus.UNREAD:
            self.status = FeedbackStatus.READ

    def reply_feedback(self, admin: Admin, reply_message: str) -> None:
        self.reply = reply_message
        self.replied_by = admin
        self.replied_at = datetime.now()
        self.status = FeedbackStatus.REPLIED

    def __repr__(self):
        return (f"<Feedback id={self.feedback_id} "
                f"sender={self.sender.get_full_name()} "
                f"status={self.status}>")


# ─────────────────────────────────────────────
# Management System (Facade / Controller)
# ─────────────────────────────────────────────

class StudentManagementSystem:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._courses: dict[str, Course] = {}
        self._subjects: dict[str, Subject] = {}
        self._sessions: dict[str, Session] = {}
        self._attendance_records: dict[str, Attendance] = {}
        self._results: dict[str, Result] = {}
        self._leave_applications: dict[str, LeaveApplication] = {}
        self._feedbacks: dict[str, Feedback] = {}
        self._username_index: dict[str, str] = {}

        # Create default admin
        self._create_default_admin()

    # ── Helpers ──────────────────────────────

    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

    def _create_default_admin(self) -> None:
        admin = Admin(
            user_id=self._generate_id(),
            username="admin",
            password="admin123",
            email="admin@sms.com",
            first_name="System",
            last_name="Admin"
        )
        self._users[admin.user_id] = admin
        self._username_index[admin.username] = admin.user_id

    def _get_user_by_username(self, username: str) -> Optional[User]:
        uid = self._username_index.get(username)
        return self._users.get(uid) if uid else None

    def _username_exists(self, username: str) -> bool:
        return username in self._username_index

    # ── Authentication ────────────────────────

    def login(self, username: str, password: str) -> Optional[User]:
        user = self._get_user_by_username(username)
        if user and user.is_active and user.verify_password(password):
            return user
        return None

    # ── Admin: Staff Management ───────────────

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str,
                  address: str = "") -> Staff:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        staff = Staff(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address
        )
        self._users[staff.user_id] = staff
        self._username_index[staff.username] = staff.user_id
        return staff

    def update_staff(self, staff_id: str, email: Optional[str] = None,
                     first_name: Optional[str] = None,
                     last_name: Optional[str] = None,
                     address: Optional[str] = None) -> Staff:
        staff = self._users.get(staff_id)
        if not staff or not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        if email is not None:
            staff.email = email
        if first_name is not None:
            staff.first_name = first_name
        if last_name is not None:
            staff.last_name = last_name
        if address is not None:
            staff.address = address
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        staff = self._users.get(staff_id)
        if not staff or not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        del self._username_index[staff.username]
        del self._users[staff_id]
        for subject in self._subjects.values():
            if subject.staff and subject.staff.user_id == staff_id:
                subject.remove_staff()
        return True

    def get_all_staff(self) -> list:
        return [u for u in self._users.values() if isinstance(u, Staff)]

    def get_staff_by_id(self, staff_id: str) -> Optional[Staff]:
        user = self._users.get(staff_id)
        return user if isinstance(user, Staff) else None

    # ── Admin: Student Management ─────────────

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str,
                    course_id: str, session_id: str,
                    address: str = "", gender: str = "") -> Student:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        course = self._courses.get(course_id)
        if not course:
            raise ValueError(f"Course with id '{course_id}' not found")
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session with id '{session_id}' not found")
        student = Student(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            course=course,
            session=session,
            address=address,
            gender=gender
        )
        self._users[student.user_id] = student
        self._username_index[student.username] = student.user_id
        return student

    def update_student(self, student_id: str,
                       email: Optional[str] = None,
                       first_name: Optional[str] = None,
                       last_name: Optional[str] = None,
                       course_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       address: Optional[str] = None,
                       gender: Optional[str] = None) -> Student:
        student = self._users.get(student_id)
        if not student or not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        if email is not None:
            student.email = email
        if first_name is not None:
            student.first_name = first_name
        if last_name is not None:
            student.last_name = last_name
        if course_id is not None:
            course = self._courses.get(course_id)
            if not course:
                raise ValueError(f"Course with id '{course_id}' not found")
            student.course = course
        if session_id is not None:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session with id '{session_id}' not found")
            student.session = session
        if address is not None:
            student.address = address
        if gender is not None:
            student.gender = gender
        return student

    def delete_student(self, student_id: str) -> bool:
        student = self._users.get(student_id)
        if not student or not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        del self._username_index[student.username]
        del self._users[student_id]
        return True

    def get_all_students(self) -> list:
        return [u for u in self._users.values() if isinstance(u, Student)]

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        user = self._users.get(student_id)
        return user if isinstance(user, Student) else None

    # ── Admin: Course Management ──────────────

    def add_course(self, name: str, description: str = "") -> Course:
        course = Course(
            course_id=self._generate_id(),
            name=name,
            description=description
        )
        self._courses[course.course_id] = course
        return course

    def update_course(self, course_id: str,
                      name: Optional[str] = None,
                      description: Optional[str] = None) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise ValueError(f"Course with id '{course_id}' not found")
        if name is not None:
            course.name = name
        if description is not None:
            course.description = description
        return course

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self._courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        del self._courses[course_id]
        return True

    def get_all_courses(self) -> list:
        return list(self._courses.values())

    def get_course_by_id(self, course_id: str) -> Optional[Course]:
        return self._courses.get(course_id)

    # ── Admin: Subject Management ─────────────

    def add_subject(self, name: str, course_id: str,
                    staff_id: Optional[str] = None,
                    description: str = "") -> Subject:
        course = self._courses.get(course_id)
        if not course:
            raise ValueError(f"Course with id '{course_id}' not found")
        staff = None
        if staff_id:
            staff = self._users.get(staff_id)
            if not isinstance(staff, Staff):
                raise ValueError(f"Staff with id '{staff_id}' not found")
        subject = Subject(
            subject_id=self._generate_id(),
            name=name,
            course=course,
            staff=staff,
            description=description
        )
        self._subjects[subject.subject_id] = subject
        if staff:
            staff.subjects.append(subject)
        return subject

    def update_subject(self, subject_id: str,
                       name: Optional[str] = None,
                       staff_id: Optional[str] = None,
                       description: Optional[str] = None) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        if name is not None:
            subject.name = name
        if description is not None:
            subject.description = description
        if staff_id is not None:
            old_staff = subject.staff
            if old_staff and subject in old_staff.subjects:
                old_staff.subjects.remove(subject)
            new_staff = self._users.get(staff_id)
            if not isinstance(new_staff, Staff):
                raise ValueError(f"Staff with id '{staff_id}' not found")
            subject.assign_staff(new_staff)
            new_staff.subjects.append(subject)
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        subject.course.remove_subject(subject)
        if subject.staff and subject in subject.staff.subjects:
            subject.staff.subjects.remove(subject)
        del self._subjects[subject_id]
        return True

    def get_all_subjects(self) -> list:
        return list(self._subjects.values())

    def get_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        return self._subjects.get(subject_id)

    # ── Admin: Session Management ─────────────

    def add_session(self, start_year: int, end_year: int) -> Session:
        session = Session(
            session_id=self._generate_id(),
            start_year=start_year,
            end_year=end_year
        )
        self._sessions[session.session_id] = session
        return session

    def update_session(self, session_id: str,
                       start_year: Optional[int] = None,
                       end_year: Optional[int] = None) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session with id '{session_id}' not found")
        new_start = start_year if start_year is not None else session.start_year
        new_end = end_year if end_year is not None else session.end_year
        if new_end <= new_start:
            raise ValueError("end_year must be greater than start_year")
        session.start_year = new_start
        session.end_year = new_end
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        del self._sessions[session_id]
        return True

    def get_all_sessions(self) -> list:
        return list(self._sessions.values())

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    # ── Staff: Attendance Management ─────────

    def take_attendance(self, staff_id: str, subject_id: str,
                        student_id: str, date_of_attendance: date,
                        status: str) -> Attendance:
        staff = self._users.get(staff_id)
        if not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        student = self._users.get(student_id)
        if not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        if status not in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
            raise ValueError(f"Invalid attendance status: {status}")
        attendance = Attendance(
            attendance_id=self._generate_id(),
            student=student,
            subject=subject,
            date_of_attendance=date_of_attendance,
            status=status,
            staff=staff
        )
        self._attendance_records[attendance.attendance_id] = attendance
        return attendance

    def update_attendance(self, attendance_id: str, status: str) -> Attendance:
        attendance = self._attendance_records.get(attendance_id)
        if not attendance:
            raise ValueError(f"Attendance record '{attendance_id}' not found")
        attendance.update_status(status)
        return attendance

    def get_attendance_by_subject(self, subject_id: str) -> list:
        return [a for a in self._attendance_records.values()
                if a.subject.subject_id == subject_id]

    def get_attendance_by_student(self, student_id: str) -> list:
        student = self._users.get(student_id)
        if not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        return list(student.attendance_records)

    def get_all_attendance(self) -> list:
        return list(self._attendance_records.values())

    # ── Staff: Result Management ──────────────

    def add_result(self, staff_id: str, student_id: str,
                   subject_id: str, exam_score: float,
                   assignment_score: float) -> Result:
        staff = self._users.get(staff_id)
        if not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        student = self._users.get(student_id)
        if not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        result = Result(
            result_id=self._generate_id(),
            student=student,
            subject=subject,
            exam_score=exam_score,
            assignment_score=assignment_score,
            staff=staff
        )
        self._results[result.result_id] = result
        return result

    def update_result(self, result_id: str,
                      exam_score: Optional[float] = None,
                      assignment_score: Optional[float] = None) -> Result:
        result = self._results.get(result_id)
        if not result:
            raise ValueError(f"Result with id '{result_id}' not found")
        new_exam = exam_score if exam_score is not None else result.exam_score
        new_assign = assignment_score if assignment_score is not None else result.assignment_score
        result.update_scores(new_exam, new_assign)
        return result

    def get_results_by_student(self, student_id: str) -> list:
        student = self._users.get(student_id)
        if not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        return list(student.results)

    def get_results_by_subject(self, subject_id: str) -> list:
        return [r for r in self._results.values()
                if r.subject.subject_id == subject_id]

    def get_all_results(self) -> list:
        return list(self._results.values())

    # ── Leave Applications ────────────────────

    def apply_for_leave(self, applicant_id: str,
                        start_date: date, end_date: date,
                        reason: str, leave_type: str = "general") -> LeaveApplication:
        applicant = self._users.get(applicant_id)
        if not applicant or not isinstance(applicant, (Staff, Student)):
            raise ValueError(f"User with id '{applicant_id}' not found or not eligible")
        leave = LeaveApplication(
            leave_id=self._generate_id(),
            applicant=applicant,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            leave_type=leave_type
        )
        self._leave_applications[leave.leave_id] = leave
        return leave

    def approve_leave(self, admin_id: str, leave_id: str,
                      reply: str = "") -> LeaveApplication:
        admin = self._users.get(admin_id)
        if not isinstance(admin, Admin):
            raise ValueError(f"Admin with id '{admin_id}' not found")
        leave = self._leave_applications.get(leave_id)
        if not leave:
            raise ValueError(f"Leave application '{leave_id}' not found")
        leave.approve(admin, reply)
        return leave

    def reject_leave(self, admin_id: str, leave_id: str,
                     reply: str = "") -> LeaveApplication:
        admin = self._users.get(admin_id)
        if not isinstance(admin, Admin):
            raise ValueError(f"Admin with id '{admin_id}' not found")
        leave = self._leave_applications.get(leave_id)
        if not leave:
            raise ValueError(f"Leave application '{leave_id}' not found")
        leave.reject(admin, reply)
        return leave

    def get_all_leave_applications(self) -> list:
        return list(self._leave_applications.values())

    def get_leave_applications_by_user(self, user_id: str) -> list:
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")
        return list(user.leave_applications)

    def get_pending_leave_applications(self) -> list:
        return [l for l in self._leave_applications.values()
                if l.status == LeaveStatus.PENDING]

    # ── Feedback ──────────────────────────────

    def send_feedback(self, sender_id: str, message: str,
                      subject_line: str = "") -> Feedback:
        sender = self._users.get(sender_id)
        if not sender or not isinstance(sender, (Staff, Student)):
            raise ValueError(f"User with id '{sender_id}' not found or not eligible")
        feedback = Feedback(
            feedback_id=self._generate_id(),
            sender=sender,
            message=message,
            subject_line=subject_line
        )
        self._feedbacks[feedback.feedback_id] = feedback
        return feedback

    def reply_feedback(self, admin_id: str, feedback_id: str,
                       reply_message: str) -> Feedback:
        admin = self._users.get(admin_id)
        if not isinstance(admin, Admin):
            raise ValueError(f"Admin with id '{admin_id}' not found")
        feedback = self._feedbacks.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback with id '{feedback_id}' not found")
        feedback.reply_feedback(admin, reply_message)
        return feedback

    def mark_feedback_read(self, feedback_id: str) -> Feedback:
        feedback = self._feedbacks.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback with id '{feedback_id}' not found")
        feedback.mark_as_read()
        return feedback

    def get_all_feedbacks(self) -> list:
        return list(self._feedbacks.values())

    def get_feedbacks_by_user(self, user_id: str) -> list:
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")
        return list(user.feedbacks)

    def get_unread_feedbacks(self) -> list:
        return [f for f in self._feedbacks.values()
                if f.status == FeedbackStatus.UNREAD]

    # ── Summary / Dashboard ───────────────────

    def get_admin_summary(self) -> dict:
        all_students = self.get_all_students()
        all_staff = self.get_all_staff()
        all_attendance = self.get_all_attendance()
        total_present = sum(1 for a in all_attendance
                            if a.status == AttendanceStatus.PRESENT)
        total_absent = sum(1 for a in all_attendance
                           if a.status == AttendanceStatus.ABSENT)
        leave_summary = {
            LeaveStatus.PENDING: 0,
            LeaveStatus.APPROVED: 0,
            LeaveStatus.REJECTED: 0
        }
        for leave in self._leave_applications.values():
            leave_summary[leave.status] += 1
        feedback_summary = {
            FeedbackStatus.UNREAD: 0,
            FeedbackStatus.READ: 0,
            FeedbackStatus.REPLIED: 0
        }
        for fb in self._feedbacks.values():
            feedback_summary[fb.status] += 1
        return {
            "total_students": len(all_students),
            "total_staff": len(all_staff),
            "total_courses": len(self._courses),
            "total_subjects": len(self._subjects),
            "total_sessions": len(self._sessions),
            "total_attendance_records": len(all_attendance),
            "attendance_present": total_present,
            "attendance_absent": total_absent,
            "leave_summary": leave_summary,
            "feedback_summary": feedback_summary,
            "total_results": len(self._results)
        }

    def get_staff_summary(self, staff_id: str) -> dict:
        staff = self._users.get(staff_id)
        if not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        staff_subjects = staff.get_subjects()
        subject_ids = {s.subject_id for s in staff_subjects}
        staff_attendance = [a for a in self._attendance_records.values()
                            if a.subject.subject_id in subject_ids]
        total_present = sum(1 for a in staff_attendance
                            if a.status == AttendanceStatus.PRESENT)
        total_absent = len(staff_attendance) - total_present
        staff_results = [r for r in self._results.values()
                         if r.subject.subject_id in subject_ids]
        leave_summary = staff.get_leave_status_summary()
        return {
            "staff_name": staff.get_full_name(),
            "total_subjects": len(staff_subjects),
            "subjects": [s.name for s in staff_subjects],
            "total_attendance_taken": len(staff_attendance),
            "attendance_present": total_present,
            "attendance_absent": total_absent,
            "total_results_added": len(staff_results),
            "leave_summary": leave_summary,
            "total_feedbacks_sent": len(staff.feedbacks)
        }

    def get_student_summary(self, student_id: str) -> dict:
        student = self._users.get(student_id)
        if not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        attendance_summary = student.get_attendance_summary()
        leave_summary = student.get_leave_status_summary()
        results = student.get_results()
        avg_score = 0.0
        if results:
            avg_score = round(sum(r.get_total_score() for r in results) / len(results), 2)
        return {
            "student_name": student.get_full_name(),
            "course": student.course.name,
            "session": student.session.get_session_name(),
            "attendance_summary": attendance_summary,
            "leave_summary": leave_summary,
            "total_results": len(results),
            "average_score": avg_score,
            "total_feedbacks_sent": len(student.feedbacks)
        }

    def get_course_performance_summary(self, course_id: str) -> dict:
        course = self._courses.get(course_id)
        if not course:
            raise ValueError(f"Course with id '{course_id}' not found")
        students = [s for s in self.get_all_students()
                    if s.course.course_id == course_id]
        all_results = []
        for student in students:
            all_results.extend(student.results)
        avg_score = 0.0
        if all_results:
            avg_score = round(sum(r.get_total_score() for r in all_results) / len(all_results), 2)
        return {
            "course_name": course.name,
            "total_students": len(students),
            "total_subjects": len(course.subjects),
            "total_results": len(all_results),
            "average_score": avg_score
        }

    # ── Utility ───────────────────────────────

    def get_all_users(self) -> list:
        return list(self._users.values())

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def deactivate_user(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")
        user.is_active = False
        return True

    def activate_user(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")
        user.is_active = True
        return True

    def change_user_password(self, user_id: str,
                             old_password: str, new_password: str) -> bool:
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")
        return user.change_password(old_password, new_password)

    def __repr__(self):
        return (f"<StudentManagementSystem "
                f"users={len(self._users)} "
                f"courses={len(self._courses)} "
                f"subjects={len(self._subjects)}>")


# ─────────────────────────────────────────────
# Demo / Entry Point
# ─────────────────────────────────────────────

def main():
    sms = StudentManagementSystem()
    print("=== Student Management System ===\n")

    # Login as admin
    admin_user = sms.login("admin", "admin123")
    print(f"Logged in as: {admin_user.get_full_name()} [{admin_user.role}]")

    # Add a session
    session = sms.add_session(2023, 2024)
    print(f"\nAdded session: {session.get_session_name()}")

    # Add a course
    course = sms.add_course("Computer Science", "CS degree program")
    print(f"Added course: {course.name}")

    # Add staff
    staff = sms.add_staff(
        username="john_doe",
        password="staff123",
        email="john@sms.com",
        first_name="John",
        last_name="Doe",
        address="123 Main St"
    )
    print(f"Added staff: {staff.get_full_name()}")

    # Add subjects
    subject1 = sms.add_subject("Mathematics", course.course_id, staff.user_id)
    subject2 = sms.add_subject("Physics", course.course_id, staff.user_id)
    print(f"Added subjects: {subject1.name}, {subject2.name}")

    # Add students
    student1 = sms.add_student(
        username="alice",
        password="student123",
        email="alice@sms.com",
        first_name="Alice",
        last_name="Smith",
        course_id=course.course_id,
        session_id=session.session_id,
        gender="Female"
    )
    student2 = sms.add_student(
        username="bob",
        password="student123",
        email="bob@sms.com",
        first_name="Bob",
        last_name="Jones",
        course_id=course.course_id,
        session_id=session.session_id,
        gender="Male"
    )
    print(f"Added students: {student1.get_full_name()}, {student2.get_full_name()}")

    # Take attendance
    today = date.today()
    att1 = sms.take_attendance(staff.user_id, subject1.subject_id,
                               student1.user_id, today, AttendanceStatus.PRESENT)
    att2 = sms.take_attendance(staff.user_id, subject1.subject_id,
                               student2.user_id, today, AttendanceStatus.ABSENT)
    print(f"\nAttendance taken: {att1.student.get_full_name()} - {att1.status}")
    print(f"Attendance taken: {att2.student.get_full_name()} - {att2.status}")

    # Add results
    result1 = sms.add_result(staff.user_id, student1.user_id,
                             subject1.subject_id, 85.0, 90.0)
    result2 = sms.add_result(staff.user_id, student2.user_id,
                             subject1.subject_id, 70.0, 75.0)
    print(f"\nResult for {result1.student.get_full_name()}: "
          f"Total={result1.get_total_score()} Grade={result1.get_grade()}")
    print(f"Result for {result2.student.get_full_name()}: "
          f"Total={result2.get_total_score()} Grade={result2.get_grade()}")

    # Apply for leave
    leave1 = sms.apply_for_leave(
        student1.user_id,
        date(2024, 3, 10),
        date(2024, 3, 12),
        "Medical appointment",
        "medical"
    )
    print(f"\nLeave applied by {leave1.applicant.get_full_name()}: {leave1.status}")

    # Admin approves leave
    sms.approve_leave(admin_user.user_id, leave1.leave_id, "Approved. Get well soon!")
    print(f"Leave status after approval: {leave1.status}")
    print(f"Admin reply: {leave1.admin_reply}")

    # Send feedback
    fb1 = sms.send_feedback(student1.user_id,
                            "The course material is excellent!",
                            "Course Feedback")
    print(f"\nFeedback sent by {fb1.sender.get_full_name()}: '{fb1.subject_line}'")

    # Admin replies to feedback
    sms.reply_feedback(admin_user.user_id, fb1.feedback_id,
                       "Thank you for your feedback!")
    print(f"Feedback status: {fb1.status}, Reply: {fb1.reply}")

    # Staff applies for leave
    staff_leave = sms.apply_for_leave(
        staff.user_id,
        date(2024, 4, 1),
        date(2024, 4, 3),
        "Personal reasons"
    )
    sms.reject_leave(admin_user.user_id, staff_leave.leave_id,
                     "Cannot approve during exam period")
    print(f"\nStaff leave status: {staff_leave.status}")

    # Summaries
    print("\n=== Admin Summary ===")
    admin_summary = sms.get_admin_summary()
    for key, value in admin_summary.items():
        print(f"  {key}: {value}")

    print("\n=== Staff Summary ===")
    staff_summary = sms.get_staff_summary(staff.user_id)
    for key, value in staff_summary.items():
        print(f"  {key}: {value}")

    print("\n=== Student Summary (Alice) ===")
    student_summary = sms.get_student_summary(student1.user_id)
    for key, value in student_summary.items():
        print(f"  {key}: {value}")

    print("\n=== Course Performance Summary ===")
    course_summary = sms.get_course_performance_summary(course.course_id)
    for key, value in course_summary.items():
        print(f"  {key}: {value}")

    print(f"\n{sms}")


if __name__ == "__main__":
    main()