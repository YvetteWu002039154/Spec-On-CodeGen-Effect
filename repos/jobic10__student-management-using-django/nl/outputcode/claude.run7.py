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
    def __init__(self, subject_id: str, name: str, course_id: str,
                 staff_id: Optional[str] = None):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id
        self.created_at = datetime.now()

    def assign_staff(self, staff_id: str) -> None:
        self.staff_id = staff_id

    def unassign_staff(self) -> None:
        self.staff_id = None

    def __repr__(self):
        return f"<Subject id={self.subject_id} name={self.name}>"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str,
                 address: str = "", course_id: Optional[str] = None):
        super().__init__(user_id, username, password, email,
                         UserRole.STAFF, first_name, last_name)
        self.address = address
        self.course_id = course_id

    def get_info(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.get_full_name(),
            "address": self.address,
            "course_id": self.course_id,
            "role": self.role,
        }

    def __repr__(self):
        return f"<Staff id={self.user_id} name={self.get_full_name()}>"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str,
                 address: str = "", course_id: Optional[str] = None,
                 session_id: Optional[str] = None, gender: str = ""):
        super().__init__(user_id, username, password, email,
                         UserRole.STUDENT, first_name, last_name)
        self.address = address
        self.course_id = course_id
        self.session_id = session_id
        self.gender = gender

    def get_info(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.get_full_name(),
            "address": self.address,
            "course_id": self.course_id,
            "session_id": self.session_id,
            "gender": self.gender,
            "role": self.role,
        }

    def __repr__(self):
        return f"<Student id={self.user_id} name={self.get_full_name()}>"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str,
                 session_id: str, attendance_date: date,
                 created_by: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.attendance_date = attendance_date
        self.created_by = created_by
        self.created_at = datetime.now()
        self.records: list = []

    def add_record(self, record) -> None:
        self.records.append(record)

    def get_records(self) -> list:
        return list(self.records)

    def __repr__(self):
        return (f"<Attendance id={self.attendance_id} "
                f"subject={self.subject_id} date={self.attendance_date}>")


class AttendanceRecord:
    def __init__(self, record_id: str, attendance_id: str,
                 student_id: str, status: str):
        if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
            raise ValueError(f"Invalid attendance status: {status}")
        self.record_id = record_id
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.status = status
        self.created_at = datetime.now()

    def __repr__(self):
        return (f"<AttendanceRecord student={self.student_id} "
                f"status={self.status}>")


class Result:
    def __init__(self, result_id: str, student_id: str,
                 subject_id: str, session_id: str,
                 exam_marks: float, assignment_marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @property
    def total_marks(self) -> float:
        return self.exam_marks + self.assignment_marks

    def update_marks(self, exam_marks: float, assignment_marks: float) -> None:
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.updated_at = datetime.now()

    def __repr__(self):
        return (f"<Result student={self.student_id} "
                f"subject={self.subject_id} total={self.total_marks}>")


class LeaveApplication:
    def __init__(self, leave_id: str, applicant_id: str,
                 applicant_role: str, start_date: date,
                 end_date: date, reason: str):
        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")
        self.leave_id = leave_id
        self.applicant_id = applicant_id
        self.applicant_role = applicant_role
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = LeaveStatus.PENDING
        self.admin_reply: Optional[str] = None
        self.applied_at = datetime.now()
        self.reviewed_at: Optional[datetime] = None

    def approve(self, reply: str = "") -> None:
        self.status = LeaveStatus.APPROVED
        self.admin_reply = reply
        self.reviewed_at = datetime.now()

    def reject(self, reply: str = "") -> None:
        self.status = LeaveStatus.REJECTED
        self.admin_reply = reply
        self.reviewed_at = datetime.now()

    def get_duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def __repr__(self):
        return (f"<LeaveApplication id={self.leave_id} "
                f"applicant={self.applicant_id} status={self.status}>")


class Feedback:
    def __init__(self, feedback_id: str, sender_id: str,
                 sender_role: str, message: str):
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.sender_role = sender_role
        self.message = message
        self.status = FeedbackStatus.UNREAD
        self.reply: Optional[str] = None
        self.sent_at = datetime.now()
        self.replied_at: Optional[datetime] = None

    def mark_read(self) -> None:
        if self.status == FeedbackStatus.UNREAD:
            self.status = FeedbackStatus.READ

    def add_reply(self, reply: str) -> None:
        self.reply = reply
        self.status = FeedbackStatus.REPLIED
        self.replied_at = datetime.now()

    def __repr__(self):
        return (f"<Feedback id={self.feedback_id} "
                f"sender={self.sender_id} status={self.status}>")


# ─────────────────────────────────────────────
# Repositories (in-memory storage)
# ─────────────────────────────────────────────

class UserRepository:
    def __init__(self):
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        if user.user_id in self._users:
            raise ValueError(f"User with id {user.user_id} already exists")
        if self.find_by_username(user.username):
            raise ValueError(f"Username '{user.username}' already taken")
        self._users[user.user_id] = user

    def find_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def find_by_role(self, role: str) -> list:
        return [u for u in self._users.values() if u.role == role]

    def update(self, user: User) -> None:
        if user.user_id not in self._users:
            raise ValueError(f"User {user.user_id} not found")
        self._users[user.user_id] = user

    def delete(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def get_all(self) -> list:
        return list(self._users.values())


class CourseRepository:
    def __init__(self):
        self._courses: dict[str, Course] = {}

    def add(self, course: Course) -> None:
        if course.course_id in self._courses:
            raise ValueError(f"Course {course.course_id} already exists")
        self._courses[course.course_id] = course

    def find_by_id(self, course_id: str) -> Optional[Course]:
        return self._courses.get(course_id)

    def find_by_name(self, name: str) -> Optional[Course]:
        for c in self._courses.values():
            if c.name.lower() == name.lower():
                return c
        return None

    def update(self, course: Course) -> None:
        if course.course_id not in self._courses:
            raise ValueError(f"Course {course.course_id} not found")
        self._courses[course.course_id] = course

    def delete(self, course_id: str) -> bool:
        if course_id in self._courses:
            del self._courses[course_id]
            return True
        return False

    def get_all(self) -> list:
        return list(self._courses.values())


class SubjectRepository:
    def __init__(self):
        self._subjects: dict[str, Subject] = {}

    def add(self, subject: Subject) -> None:
        if subject.subject_id in self._subjects:
            raise ValueError(f"Subject {subject.subject_id} already exists")
        self._subjects[subject.subject_id] = subject

    def find_by_id(self, subject_id: str) -> Optional[Subject]:
        return self._subjects.get(subject_id)

    def find_by_course(self, course_id: str) -> list:
        return [s for s in self._subjects.values() if s.course_id == course_id]

    def find_by_staff(self, staff_id: str) -> list:
        return [s for s in self._subjects.values() if s.staff_id == staff_id]

    def update(self, subject: Subject) -> None:
        if subject.subject_id not in self._subjects:
            raise ValueError(f"Subject {subject.subject_id} not found")
        self._subjects[subject.subject_id] = subject

    def delete(self, subject_id: str) -> bool:
        if subject_id in self._subjects:
            del self._subjects[subject_id]
            return True
        return False

    def get_all(self) -> list:
        return list(self._subjects.values())


class SessionRepository:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        if session.session_id in self._sessions:
            raise ValueError(f"Session {session.session_id} already exists")
        self._sessions[session.session_id] = session

    def find_by_id(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update(self, session: Session) -> None:
        if session.session_id not in self._sessions:
            raise ValueError(f"Session {session.session_id} not found")
        self._sessions[session.session_id] = session

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_all(self) -> list:
        return list(self._sessions.values())


class AttendanceRepository:
    def __init__(self):
        self._attendances: dict[str, Attendance] = {}
        self._records: dict[str, AttendanceRecord] = {}

    def add_attendance(self, attendance: Attendance) -> None:
        self._attendances[attendance.attendance_id] = attendance

    def find_attendance_by_id(self, attendance_id: str) -> Optional[Attendance]:
        return self._attendances.get(attendance_id)

    def find_by_subject_and_date(self, subject_id: str,
                                  attendance_date: date) -> Optional[Attendance]:
        for a in self._attendances.values():
            if a.subject_id == subject_id and a.attendance_date == attendance_date:
                return a
        return None

    def find_by_subject(self, subject_id: str) -> list:
        return [a for a in self._attendances.values()
                if a.subject_id == subject_id]

    def find_by_student(self, student_id: str) -> list:
        result = []
        for a in self._attendances.values():
            for r in a.records:
                if r.student_id == student_id:
                    result.append((a, r))
        return result

    def add_record(self, record: AttendanceRecord) -> None:
        self._records[record.record_id] = record

    def find_records_by_attendance(self, attendance_id: str) -> list:
        return [r for r in self._records.values()
                if r.attendance_id == attendance_id]

    def find_record_by_student_attendance(self, student_id: str,
                                           attendance_id: str) -> Optional[AttendanceRecord]:
        for r in self._records.values():
            if r.student_id == student_id and r.attendance_id == attendance_id:
                return r
        return None

    def get_all_attendances(self) -> list:
        return list(self._attendances.values())


class ResultRepository:
    def __init__(self):
        self._results: dict[str, Result] = {}

    def add(self, result: Result) -> None:
        self._results[result.result_id] = result

    def find_by_id(self, result_id: str) -> Optional[Result]:
        return self._results.get(result_id)

    def find_by_student(self, student_id: str) -> list:
        return [r for r in self._results.values()
                if r.student_id == student_id]

    def find_by_student_and_subject(self, student_id: str,
                                     subject_id: str) -> Optional[Result]:
        for r in self._results.values():
            if r.student_id == student_id and r.subject_id == subject_id:
                return r
        return None

    def find_by_subject(self, subject_id: str) -> list:
        return [r for r in self._results.values()
                if r.subject_id == subject_id]

    def update(self, result: Result) -> None:
        if result.result_id not in self._results:
            raise ValueError(f"Result {result.result_id} not found")
        self._results[result.result_id] = result

    def get_all(self) -> list:
        return list(self._results.values())


class LeaveRepository:
    def __init__(self):
        self._leaves: dict[str, LeaveApplication] = {}

    def add(self, leave: LeaveApplication) -> None:
        self._leaves[leave.leave_id] = leave

    def find_by_id(self, leave_id: str) -> Optional[LeaveApplication]:
        return self._leaves.get(leave_id)

    def find_by_applicant(self, applicant_id: str) -> list:
        return [l for l in self._leaves.values()
                if l.applicant_id == applicant_id]

    def find_by_status(self, status: str) -> list:
        return [l for l in self._leaves.values() if l.status == status]

    def find_by_role(self, role: str) -> list:
        return [l for l in self._leaves.values()
                if l.applicant_role == role]

    def update(self, leave: LeaveApplication) -> None:
        if leave.leave_id not in self._leaves:
            raise ValueError(f"Leave {leave.leave_id} not found")
        self._leaves[leave.leave_id] = leave

    def get_all(self) -> list:
        return list(self._leaves.values())


class FeedbackRepository:
    def __init__(self):
        self._feedbacks: dict[str, Feedback] = {}

    def add(self, feedback: Feedback) -> None:
        self._feedbacks[feedback.feedback_id] = feedback

    def find_by_id(self, feedback_id: str) -> Optional[Feedback]:
        return self._feedbacks.get(feedback_id)

    def find_by_sender(self, sender_id: str) -> list:
        return [f for f in self._feedbacks.values()
                if f.sender_id == sender_id]

    def find_by_status(self, status: str) -> list:
        return [f for f in self._feedbacks.values()
                if f.status == status]

    def find_by_role(self, role: str) -> list:
        return [f for f in self._feedbacks.values()
                if f.sender_role == role]

    def update(self, feedback: Feedback) -> None:
        if feedback.feedback_id not in self._feedbacks:
            raise ValueError(f"Feedback {feedback.feedback_id} not found")
        self._feedbacks[feedback.feedback_id] = feedback

    def get_all(self) -> list:
        return list(self._feedbacks.values())


# ─────────────────────────────────────────────
# Services
# ─────────────────────────────────────────────

def _generate_id() -> str:
    return str(uuid.uuid4())


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._active_sessions: dict[str, str] = {}

    def login(self, username: str, password: str) -> Optional[dict]:
        user = self._user_repo.find_by_username(username)
        if user and user.is_active and user.verify_password(password):
            token = _generate_id()
            self._active_sessions[token] = user.user_id
            return {"token": token, "user_id": user.user_id,
                    "role": user.role, "full_name": user.get_full_name()}
        return None

    def logout(self, token: str) -> bool:
        if token in self._active_sessions:
            del self._active_sessions[token]
            return True
        return False

    def get_user_from_token(self, token: str) -> Optional[User]:
        user_id = self._active_sessions.get(token)
        if user_id:
            return self._user_repo.find_by_id(user_id)
        return None

    def is_authenticated(self, token: str) -> bool:
        return token in self._active_sessions


class AdminService:
    def __init__(self, user_repo: UserRepository,
                 course_repo: CourseRepository,
                 subject_repo: SubjectRepository,
                 session_repo: SessionRepository,
                 attendance_repo: AttendanceRepository,
                 result_repo: ResultRepository,
                 leave_repo: LeaveRepository,
                 feedback_repo: FeedbackRepository):
        self._user_repo = user_repo
        self._course_repo = course_repo
        self._subject_repo = subject_repo
        self._session_repo = session_repo
        self._attendance_repo = attendance_repo
        self._result_repo = result_repo
        self._leave_repo = leave_repo
        self._feedback_repo = feedback_repo

    # ── Staff Management ──────────────────────

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str,
                  address: str = "", course_id: Optional[str] = None) -> Staff:
        if course_id and not self._course_repo.find_by_id(course_id):
            raise ValueError(f"Course {course_id} not found")
        staff = Staff(_generate_id(), username, password, email,
                      first_name, last_name, address, course_id)
        self._user_repo.add(staff)
        return staff

    def update_staff(self, staff_id: str, email: Optional[str] = None,
                     first_name: Optional[str] = None,
                     last_name: Optional[str] = None,
                     address: Optional[str] = None,
                     course_id: Optional[str] = None) -> Staff:
        user = self._user_repo.find_by_id(staff_id)
        if not user or user.role != UserRole.STAFF:
            raise ValueError(f"Staff {staff_id} not found")
        if email:
            user.email = email
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if address is not None:
            user.address = address
        if course_id is not None:
            if course_id and not self._course_repo.find_by_id(course_id):
                raise ValueError(f"Course {course_id} not found")
            user.course_id = course_id
        self._user_repo.update(user)
        return user

    def delete_staff(self, staff_id: str) -> bool:
        user = self._user_repo.find_by_id(staff_id)
        if not user or user.role != UserRole.STAFF:
            raise ValueError(f"Staff {staff_id} not found")
        return self._user_repo.delete(staff_id)

    def get_all_staff(self) -> list:
        return self._user_repo.find_by_role(UserRole.STAFF)

    # ── Student Management ────────────────────

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str,
                    address: str = "", course_id: Optional[str] = None,
                    session_id: Optional[str] = None,
                    gender: str = "") -> Student:
        if course_id and not self._course_repo.find_by_id(course_id):
            raise ValueError(f"Course {course_id} not found")
        if session_id and not self._session_repo.find_by_id(session_id):
            raise ValueError(f"Session {session_id} not found")
        student = Student(_generate_id(), username, password, email,
                          first_name, last_name, address,
                          course_id, session_id, gender)
        self._user_repo.add(student)
        return student

    def update_student(self, student_id: str, email: Optional[str] = None,
                       first_name: Optional[str] = None,
                       last_name: Optional[str] = None,
                       address: Optional[str] = None,
                       course_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       gender: Optional[str] = None) -> Student:
        user = self._user_repo.find_by_id(student_id)
        if not user or user.role != UserRole.STUDENT:
            raise ValueError(f"Student {student_id} not found")
        if email:
            user.email = email
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if address is not None:
            user.address = address
        if course_id is not None:
            if course_id and not self._course_repo.find_by_id(course_id):
                raise ValueError(f"Course {course_id} not found")
            user.course_id = course_id
        if session_id is not None:
            if session_id and not self._session_repo.find_by_id(session_id):
                raise ValueError(f"Session {session_id} not found")
            user.session_id = session_id
        if gender is not None:
            user.gender = gender
        self._user_repo.update(user)
        return user

    def delete_student(self, student_id: str) -> bool:
        user = self._user_repo.find_by_id(student_id)
        if not user or user.role != UserRole.STUDENT:
            raise ValueError(f"Student {student_id} not found")
        return self._user_repo.delete(student_id)

    def get_all_students(self) -> list:
        return self._user_repo.find_by_role(UserRole.STUDENT)

    # ── Course Management ─────────────────────

    def add_course(self, name: str, description: str = "") -> Course:
        course = Course(_generate_id(), name, description)
        self._course_repo.add(course)
        return course

    def update_course(self, course_id: str, name: Optional[str] = None,
                      description: Optional[str] = None) -> Course:
        course = self._course_repo.find_by_id(course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found")
        if name:
            course.name = name
        if description is not None:
            course.description = description
        self._course_repo.update(course)
        return course

    def delete_course(self, course_id: str) -> bool:
        if not self._course_repo.find_by_id(course_id):
            raise ValueError(f"Course {course_id} not found")
        return self._course_repo.delete(course_id)

    def get_all_courses(self) -> list:
        return self._course_repo.get_all()

    # ── Subject Management ────────────────────

    def add_subject(self, name: str, course_id: str,
                    staff_id: Optional[str] = None) -> Subject:
        if not self._course_repo.find_by_id(course_id):
            raise ValueError(f"Course {course_id} not found")
        if staff_id:
            staff = self._user_repo.find_by_id(staff_id)
            if not staff or staff.role != UserRole.STAFF:
                raise ValueError(f"Staff {staff_id} not found")
        subject = Subject(_generate_id(), name, course_id, staff_id)
        self._subject_repo.add(subject)
        course = self._course_repo.find_by_id(course_id)
        course.add_subject(subject)
        self._course_repo.update(course)
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None,
                       course_id: Optional[str] = None,
                       staff_id: Optional[str] = None) -> Subject:
        subject = self._subject_repo.find_by_id(subject_id)
        if not subject:
            raise ValueError(f"Subject {subject_id} not found")
        if name:
            subject.name = name
        if course_id is not None:
            if course_id and not self._course_repo.find_by_id(course_id):
                raise ValueError(f"Course {course_id} not found")
            subject.course_id = course_id
        if staff_id is not None:
            if staff_id:
                staff = self._user_repo.find_by_id(staff_id)
                if not staff or staff.role != UserRole.STAFF:
                    raise ValueError(f"Staff {staff_id} not found")
            subject.staff_id = staff_id if staff_id else None
        self._subject_repo.update(subject)
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        subject = self._subject_repo.find_by_id(subject_id)
        if not subject:
            raise ValueError(f"Subject {subject_id} not found")
        course = self._course_repo.find_by_id(subject.course_id)
        if course:
            course.remove_subject(subject)
            self._course_repo.update(course)
        return self._subject_repo.delete(subject_id)

    def get_all_subjects(self) -> list:
        return self._subject_repo.get_all()

    # ── Session Management ────────────────────

    def add_session(self, start_year: int, end_year: int) -> Session:
        session = Session(_generate_id(), start_year, end_year)
        self._session_repo.add(session)
        return session

    def update_session(self, session_id: str,
                       start_year: Optional[int] = None,
                       end_year: Optional[int] = None) -> Session:
        session = self._session_repo.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        new_start = start_year if start_year is not None else session.start_year
        new_end = end_year if end_year is not None else session.end_year
        if new_end <= new_start:
            raise ValueError("end_year must be greater than start_year")
        session.start_year = new_start
        session.end_year = new_end
        self._session_repo.update(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        if not self._session_repo.find_by_id(session_id):
            raise ValueError(f"Session {session_id} not found")
        return self._session_repo.delete(session_id)

    def get_all_sessions(self) -> list:
        return self._session_repo.get_all()

    # ── Attendance View ───────────────────────

    def view_all_attendance(self) -> list:
        return self._attendance_repo.get_all_attendances()

    def view_student_attendance(self, student_id: str) -> list:
        return self._attendance_repo.find_by_student(student_id)

    # ── Leave Management ──────────────────────

    def get_all_leaves(self) -> list:
        return self._leave_repo.get_all()

    def get_pending_leaves(self) -> list:
        return self._leave_repo.find_by_status(LeaveStatus.PENDING)

    def approve_leave(self, leave_id: str, reply: str = "") -> LeaveApplication:
        leave = self._leave_repo.find_by_id(leave_id)
        if not leave:
            raise ValueError(f"Leave {leave_id} not found")
        if leave.status != LeaveStatus.PENDING:
            raise ValueError("Only pending leaves can be approved")
        leave.approve(reply)
        self._leave_repo.update(leave)
        return leave

    def reject_leave(self, leave_id: str, reply: str = "") -> LeaveApplication:
        leave = self._leave_repo.find_by_id(leave_id)
        if not leave:
            raise ValueError(f"Leave {leave_id} not found")
        if leave.status != LeaveStatus.PENDING:
            raise ValueError("Only pending leaves can be rejected")
        leave.reject(reply)
        self._leave_repo.update(leave)
        return leave

    # ── Feedback Management ───────────────────

    def get_all_feedbacks(self) -> list:
        return self._feedback_repo.get_all()

    def get_unread_feedbacks(self) -> list:
        return self._feedback_repo.find_by_status(FeedbackStatus.UNREAD)

    def read_feedback(self, feedback_id: str) -> Feedback:
        feedback = self._feedback_repo.find_by_id(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback {feedback_id} not found")
        feedback.mark_read()
        self._feedback_repo.update(feedback)
        return feedback

    def reply_feedback(self, feedback_id: str, reply: str) -> Feedback:
        feedback = self._feedback_repo.find_by_id(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback {feedback_id} not found")
        feedback.add_reply(reply)
        self._feedback_repo.update(feedback)
        return feedback

    # ── Summary / Dashboard ───────────────────

    def get_summary(self) -> dict:
        students = self._user_repo.find_by_role(UserRole.STUDENT)
        staff = self._user_repo.find_by_role(UserRole.STAFF)
        courses = self._course_repo.get_all()
        subjects = self._subject_repo.get_all()
        sessions = self._session_repo.get_all()
        leaves = self._leave_repo.get_all()
        feedbacks = self._feedback_repo.get_all()
        attendances = self._attendance_repo.get_all_attendances()

        pending_leaves = [l for l in leaves if l.status == LeaveStatus.PENDING]
        unread_feedbacks = [f for f in feedbacks
                            if f.status == FeedbackStatus.UNREAD]

        return {
            "total_students": len(students),
            "total_staff": len(staff),
            "total_courses": len(courses),
            "total_subjects": len(subjects),
            "total_sessions": len(sessions),
            "total_leaves": len(leaves),
            "pending_leaves": len(pending_leaves),
            "total_feedbacks": len(feedbacks),
            "unread_feedbacks": len(unread_feedbacks),
            "total_attendance_records": len(attendances),
        }


class StaffService:
    def __init__(self, user_repo: UserRepository,
                 subject_repo: SubjectRepository,
                 session_repo: SessionRepository,
                 attendance_repo: AttendanceRepository,
                 result_repo: ResultRepository,
                 leave_repo: LeaveRepository,
                 feedback_repo: FeedbackRepository):
        self._user_repo = user_repo
        self._subject_repo = subject_repo
        self._session_repo = session_repo
        self._attendance_repo = attendance_repo
        self._result_repo = result_repo
        self._leave_repo = leave_repo
        self._feedback_repo = feedback_repo

    def _get_staff(self, staff_id: str) -> Staff:
        user = self._user_repo.find_by_id(staff_id)
        if not user or user.role != UserRole.STAFF:
            raise ValueError(f"Staff {staff_id} not found")
        return user

    # ── Attendance ────────────────────────────

    def take_attendance(self, staff_id: str, subject_id: str,
                        session_id: str, attendance_date: date,
                        student_statuses: dict) -> Attendance:
        self._get_staff(staff_id)
        subject = self._subject_repo.find_by_id(subject_id)
        if not subject:
            raise ValueError(f"Subject {subject_id} not found")
        if subject.staff_id != staff_id:
            raise ValueError("Staff not assigned to this subject")
        if not self._session_repo.find_by_id(session_id):
            raise ValueError(f"Session {session_id} not found")

        existing = self._attendance_repo.find_by_subject_and_date(
            subject_id, attendance_date)
        if existing:
            raise ValueError("Attendance already taken for this subject on this date")

        attendance = Attendance(_generate_id(), subject_id, session_id,
                                attendance_date, staff_id)
        self._attendance_repo.add_attendance(attendance)

        for student_id, status in student_statuses.items():
            student = self._user_repo.find_by_id(student_id)
            if not student or student.role != UserRole.STUDENT:
                continue
            record = AttendanceRecord(_generate_id(), attendance.attendance_id,
                                      student_id, status)
            attendance.add_record(record)
            self._attendance_repo.add_record(record)

        return attendance

    def update_attendance(self, staff_id: str, attendance_id: str,
                          student_statuses: dict) -> Attendance:
        self._get_staff(staff_id)
        attendance = self._attendance_repo.find_attendance_by_id(attendance_id)
        if not attendance:
            raise ValueError(f"Attendance {attendance_id} not found")
        if attendance.created_by != staff_id:
            raise ValueError("Staff can only update their own attendance records")

        for student_id, status in student_statuses.items():
            record = self._attendance_repo.find_record_by_student_attendance(
                student_id, attendance_id)
            if record:
                record.status = status
            else:
                student = self._user_repo.find_by_id(student_id)
                if student and student.role == UserRole.STUDENT:
                    record = AttendanceRecord(_generate_id(), attendance_id,
                                             student_id, status)
                    attendance.add_record(record)
                    self._attendance_repo.add_record(record)

        return attendance

    def get_subject_attendance(self, staff_id: str, subject_id: str) -> list:
        self._get_staff(staff_id)
        subject = self._subject_repo.find_by_id(subject_id)
        if not subject or subject.staff_id != staff_id:
            raise ValueError("Staff not assigned to this subject")
        return self._attendance_repo.find_by_subject(subject_id)

    # ── Results ───────────────────────────────

    def add_result(self, staff_id: str, student_id: str,
                   subject_id: str, session_id: str,
                   exam_marks: float, assignment_marks: float) -> Result:
        self._get_staff(staff_id)
        subject = self._subject_repo.find_by_id(subject_id)
        if not subject or subject.staff_id != staff_id:
            raise ValueError("Staff not assigned to this subject")
        student = self._user_repo.find_by_id(student_id)
        if not student or student.role != UserRole.STUDENT:
            raise ValueError(f"Student {student_id} not found")
        if not self._session_repo.find_by_id(session_id):
            raise ValueError(f"Session {session_id} not found")

        existing = self._result_repo.find_by_student_and_subject(
            student_id, subject_id)
        if existing:
            raise ValueError("Result already exists; use update_result instead")

        result = Result(_generate_id(), student_id, subject_id,
                        session_id, exam_marks, assignment_marks)
        self._result_repo.add(result)
        return result

    def update_result(self, staff_id: str, result_id: str,
                      exam_marks: float, assignment_marks: float) -> Result:
        self._get_staff(staff_id)
        result = self._result_repo.find_by_id(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")
        subject = self._subject_repo.find_by_id(result.subject_id)
        if not subject or subject.staff_id != staff_id:
            raise ValueError("Staff not assigned to this subject")
        result.update_marks(exam_marks, assignment_marks)
        self._result_repo.update(result)
        return result

    # ── Leave ─────────────────────────────────

    def apply_for_leave(self, staff_id: str, start_date: date,
                        end_date: date, reason: str) -> LeaveApplication:
        self._get_staff(staff_id)
        leave = LeaveApplication(_generate_id(), staff_id,
                                 UserRole.STAFF, start_date, end_date, reason)
        self._leave_repo.add(leave)
        return leave

    def get_my_leaves(self, staff_id: str) -> list:
        self._get_staff(staff_id)
        return self._leave_repo.find_by_applicant(staff_id)

    # ── Feedback ──────────────────────────────

    def send_feedback(self, staff_id: str, message: str) -> Feedback:
        self._get_staff(staff_id)
        feedback = Feedback(_generate_id(), staff_id, UserRole.STAFF, message)
        self._feedback_repo.add(feedback)
        return feedback

    def get_my_feedbacks(self, staff_id: str) -> list:
        self._get_staff(staff_id)
        return self._feedback_repo.find_by_sender(staff_id)

    # ── Summary / Dashboard ───────────────────

    def get_summary(self, staff_id: str) -> dict:
        self._get_staff(staff_id)
        subjects = self._subject_repo.find_by_staff(staff_id)
        leaves = self._leave_repo.find_by_applicant(staff_id)
        feedbacks = self._feedback_repo.find_by_sender(staff_id)

        total_attendance = 0
        for subject in subjects:
            records = self._attendance_repo.find_by_subject(subject.subject_id)
            total_attendance += len(records)

        pending_leaves = [l for l in leaves if l.status == LeaveStatus.PENDING]
        approved_leaves = [l for l in leaves if l.status == LeaveStatus.APPROVED]
        rejected_leaves = [l for l in leaves if l.status == LeaveStatus.REJECTED]

        return {
            "staff_id": staff_id,
            "total_subjects": len(subjects),
            "total_attendance_sessions": total_attendance,
            "total_leaves": len(leaves),
            "pending_leaves": len(pending_leaves),
            "approved_leaves": len(approved_leaves),
            "rejected_leaves": len(rejected_leaves),
            "total_feedbacks": len(feedbacks),
        }


class StudentService:
    def __init__(self, user_repo: UserRepository,
                 subject_repo: SubjectRepository,
                 attendance_repo: AttendanceRepository,
                 result_repo: ResultRepository,
                 leave_repo: LeaveRepository,
                 feedback_repo: FeedbackRepository):
        self._user_repo = user_repo
        self._subject_repo = subject_repo
        self._attendance_repo = attendance_repo
        self._result_repo = result_repo
        self._leave_repo = leave_repo
        self._feedback_repo = feedback_repo

    def _get_student(self, student_id: str) -> Student:
        user = self._user_repo.find_by_id(student_id)
        if not user or user.role != UserRole.STUDENT:
            raise ValueError(f"Student {student_id} not found")
        return user

    # ── Attendance ────────────────────────────

    def view_attendance(self, student_id: str) -> list:
        self._get_student(student_id)
        return self._attendance_repo.find_by_student(student_id)

    def get_attendance_summary(self, student_id: str) -> dict:
        self._get_student(student_id)
        records = self._attendance_repo.find_by_student(student_id)
        total = len(records)
        present = sum(1 for _, r in records
                      if r.status == AttendanceStatus.PRESENT)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0.0
        return {
            "student_id": student_id,
            "total_classes": total,
            "present": present,
            "absent": absent,
            "attendance_percentage": round(percentage, 2),
        }

    # ── Results ───────────────────────────────

    def view_results(self, student_id: str) -> list:
        self._get_student(student_id)
        return self._result_repo.find_by_student(student_id)

    def get_result_summary(self, student_id: str) -> dict:
        self._get_student(student_id)
        results = self._result_repo.find_by_student(student_id)
        if not results:
            return {"student_id": student_id, "results": [],
                    "average_total": 0.0}
        avg = sum(r.total_marks for r in results) / len(results)
        return {
            "student_id": student_id,
            "results": [
                {
                    "subject_id": r.subject_id,
                    "exam_marks": r.exam_marks,
                    "assignment_marks": r.assignment_marks,
                    "total_marks": r.total_marks,
                }
                for r in results
            ],
            "average_total": round(avg, 2),
        }

    # ── Leave ─────────────────────────────────

    def apply_for_leave(self, student_id: str, start_date: date,
                        end_date: date, reason: str) -> LeaveApplication:
        self._get_student(student_id)
        leave = LeaveApplication(_generate_id(), student_id,
                                 UserRole.STUDENT, start_date, end_date, reason)
        self._leave_repo.add(leave)
        return leave

    def get_my_leaves(self, student_id: str) -> list:
        self._get_student(student_id)
        return self._leave_repo.find_by_applicant(student_id)

    # ── Feedback ──────────────────────────────

    def send_feedback(self, student_id: str, message: str) -> Feedback:
        self._get_student(student_id)
        feedback = Feedback(_generate_id(), student_id,
                            UserRole.STUDENT, message)
        self._feedback_repo.add(feedback)
        return feedback

    def get_my_feedbacks(self, student_id: str) -> list:
        self._get_student(student_id)
        return self._feedback_repo.find_by_sender(student_id)

    # ── Summary / Dashboard ───────────────────

    def get_summary(self, student_id: str) -> dict:
        student = self._get_student(student_id)
        attendance_records = self._attendance_repo.find_by_student(student_id)
        total_classes = len(attendance_records)
        present = sum(1 for _, r in attendance_records
                      if r.status == AttendanceStatus.PRESENT)
        attendance_pct = (present / total_classes * 100) if total_classes > 0 else 0.0

        results = self._result_repo.find_by_student(student_id)
        leaves = self._leave_repo.find_by_applicant(student_id)
        feedbacks = self._feedback_repo.find_by_sender(student_id)

        subjects = (self._subject_repo.find_by_course(student.course_id)
                    if student.course_id else [])

        pending_leaves = [l for l in leaves if l.status == LeaveStatus.PENDING]
        approved_leaves = [l for l in leaves if l.status == LeaveStatus.APPROVED]

        return {
            "student_id": student_id,
            "full_name": student.get_full_name(),
            "course_id": student.course_id,
            "total_subjects": len(subjects),
            "total_classes": total_classes,
            "present": present,
            "attendance_percentage": round(attendance_pct, 2),
            "total_results": len(results),
            "total_leaves": len(leaves),
            "pending_leaves": len(pending_leaves),
            "approved_leaves": len(approved_leaves),
            "total_feedbacks": len(feedbacks),
        }


# ─────────────────────────────────────────────
# Application (Facade / Entry Point)
# ─────────────────────────────────────────────

class StudentManagementSystem:
    def __init__(self):
        # Repositories
        self._user_repo = UserRepository()
        self._course_repo = CourseRepository()
        self._subject_repo = SubjectRepository()
        self._session_repo = SessionRepository()
        self._attendance_repo = AttendanceRepository()
        self._result_repo = ResultRepository()
        self._leave_repo = LeaveRepository()
        self._feedback_repo = FeedbackRepository()

        # Services
        self.auth = AuthService(self._user_repo)

        self.admin_service = AdminService(
            self._user_repo, self._course_repo, self._subject_repo,
            self._session_repo, self._attendance_repo, self._result_repo,
            self._leave_repo, self._feedback_repo
        )

        self.staff_service = StaffService(
            self._user_repo, self._subject_repo, self._session_repo,
            self._attendance_repo, self._result_repo,
            self._leave_repo, self._feedback_repo
        )

        self.student_service = StudentService(
            self._user_repo, self._subject_repo,
            self._attendance_repo, self._result_repo,
            self._leave_repo, self._feedback_repo
        )

        # Bootstrap default admin
        self._bootstrap_admin()

    def _bootstrap_admin(self) -> None:
        admin = Admin(_generate_id(), "admin", "admin123",
                      "admin@school.com", "System", "Admin")
        self._user_repo.add(admin)

    def login(self, username: str, password: str) -> Optional[dict]:
        return self.auth.login(username, password)

    def logout(self, token: str) -> bool:
        return self.auth.logout(token)

    def get_current_user(self, token: str) -> Optional[User]:
        return self.auth.get_user_from_token(token)


# ─────────────────────────────────────────────
# Demo / Smoke Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sms = StudentManagementSystem()

    # Admin login
    session = sms.login("admin", "admin123")
    assert session is not None
    print("Admin logged in:", session["full_name"])

    # Add course
    course = sms.admin_service.add_course("Computer Science", "CS degree")
    print("Course added:", course)

    # Add session
    academic_session = sms.admin_service.add_session(2023, 2024)
    print("Session added:", academic_session)

    # Add staff
    staff = sms.admin_service.add_staff(
        "jdoe", "pass123", "jdoe@school.com",
        "John", "Doe", "123 Main St", course.course_id
    )
    print("Staff added:", staff)

    # Add student
    student = sms.admin_service.add_student(
        "alice", "pass456", "alice@school.com",
        "Alice", "Smith", "456 Oak Ave",
        course.course_id, academic_session.session_id, "Female"
    )
    print("Student added:", student)

    # Add subject and assign staff
    subject = sms.admin_service.add_subject(
        "Data Structures", course.course_id, staff.user_id
    )
    print("Subject added:", subject)

    # Staff takes attendance
    att = sms.staff_service.take_attendance(
        staff.user_id, subject.subject_id,
        academic_session.session_id, date.today(),
        {student.user_id: AttendanceStatus.PRESENT}
    )
    print("Attendance taken:", att)

    # Staff adds result
    result = sms.staff_service.add_result(
        staff.user_id, student.user_id,
        subject.subject_id, academic_session.session_id,
        75.0, 20.0
    )
    print("Result added:", result, "Total:", result.total_marks)

    # Student views attendance
    att_records = sms.student_service.view_attendance(student.user_id)
    print("Student attendance records:", len(att_records))

    # Student views results
    results = sms.student_service.view_results(student.user_id)
    print("Student results:", results)

    # Student applies for leave
    leave = sms.student_service.apply_for_leave(
        student.user_id, date(2024, 3, 1), date(2024, 3, 3), "Medical"
    )
    print("Leave applied:", leave)

    # Admin approves leave
    approved = sms.admin_service.approve_leave(leave.leave_id, "Get well soon")
    print("Leave approved:", approved.status)

    # Student sends feedback
    fb = sms.student_service.send_feedback(student.user_id, "Great course!")
    print("Feedback sent:", fb)

    # Admin replies to feedback
    replied = sms.admin_service.reply_feedback(fb.feedback_id, "Thank you!")
    print("Feedback replied:", replied.status, "Reply:", replied.reply)

    # Admin summary
    summary = sms.admin_service.get_summary()
    print("Admin Summary:", summary)

    # Student summary
    student_summary = sms.student_service.get_summary(student.user_id)
    print("Student Summary:", student_summary)

    # Staff summary
    staff_summary = sms.staff_service.get_summary(staff.user_id)
    print("Staff Summary:", staff_summary)

    print("\nAll tests passed successfully!")