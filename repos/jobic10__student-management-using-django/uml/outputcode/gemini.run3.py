from datetime import date, datetime
from typing import List, Tuple, Union, Optional

class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        return CustomUser(
            address="",
            created_at=datetime.now(),
            email=email,
            fcm_token="",
            gender="Other",
            password=password,
            profile_pic="",
            updated_at=datetime.now(),
            user_type="Student",
            username=None
        )

    def create_superuser(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        user = self.create_user(email, password)
        user.user_type = "Admin"
        return user

class CustomUser:
    GENDER: List[str] = ['Male', 'Female', 'Other']
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = 'email'
    USER_TYPE: Tuple[str, ...] = ('Admin', 'Staff', 'Student')
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, address: str, created_at: datetime, email: str, fcm_token: str,
                 gender: str, password: Union[bytes, str], profile_pic: str,
                 updated_at: datetime, user_type: str, username: None = None):
        self.address = address
        self.created_at = created_at
        self.email = email
        self.fcm_token = fcm_token
        self.gender = gender
        self.password = password
        self.profile_pic = profile_pic
        self.updated_at = updated_at
        self.user_type = user_type
        self.username = username

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        if "@" not in value:
            raise ValueError("Invalid email address")
        self._email = value

    @property
    def user_type(self) -> str:
        return self._user_type

    @user_type.setter
    def user_type(self, value: str):
        if value not in self.USER_TYPE:
            raise ValueError(f"Invalid user type. Must be one of {self.USER_TYPE}")
        self._user_type = value

class Admin:
    def __init__(self, admin: CustomUser):
        self.admin = admin

class Course:
    def __init__(self, created_at: datetime, name: str, updated_at: datetime):
        self.created_at = created_at
        self.name = name
        self.updated_at = updated_at

class Session:
    def __init__(self, end_year: date, start_year: date):
        self.start_year = start_year
        self.end_year = end_year

    @property
    def end_year(self) -> date:
        return self._end_year

    @end_year.setter
    def end_year(self, value: date):
        if hasattr(self, 'start_year') and value < self.start_year:
            raise ValueError("End year cannot be before start year")
        self._end_year = value

class Staff:
    def __init__(self, admin: CustomUser, course: Course):
        self.admin = admin
        self.course = course

class Student:
    def __init__(self, admin: CustomUser, course: Course, session: Session):
        self.admin = admin
        self.course = course
        self.session = session

class Subject:
    def __init__(self, course: Course, created_at: datetime, name: str, staff: Staff, updated_at: datetime):
        self.course = course
        self.created_at = created_at
        self.name = name
        self.staff = staff
        self.updated_at = updated_at

class Attendance:
    def __init__(self, created_at: datetime, date: date, session: Session, subject: Subject, updated_at: datetime):
        self.created_at = created_at
        self.date = date
        self.session = session
        self.subject = subject
        self.updated_at = updated_at

class AttendanceReport:
    def __init__(self, attendance: Attendance, created_at: datetime, status: bool, student: Student, updated_at: datetime):
        self.attendance = attendance
        self.created_at = created_at
        self.status = status
        self.student = student
        self.updated_at = updated_at

class StudentResult:
    def __init__(self, created_at: datetime, exam: float, student: Student, subject: Subject, test: float, updated_at: datetime):
        self.created_at = created_at
        self.student = student
        self.subject = subject
        self.exam = exam
        self.test = test
        self.updated_at = updated_at

    @property
    def exam(self) -> float:
        return self._exam

    @exam.setter
    def exam(self, value: float):
        if value < 0.0:
            raise ValueError("Exam score cannot be negative")
        self._exam = value

    @property
    def test(self) -> float:
        return self._test

    @test.setter
    def test(self, value: float):
        if value < 0.0:
            raise ValueError("Test score cannot be negative")
        self._test = value

class BaseReport:
    def __init__(self, created_at: datetime, updated_at: datetime):
        self.created_at = created_at
        self.updated_at = updated_at

class LeaveReport(BaseReport):
    def __init__(self, created_at: datetime, date: str, message: str, status: int, updated_at: datetime):
        super().__init__(created_at, updated_at)
        self.date = date
        self.message = message
        self.status = status

class LeaveReportStaff(LeaveReport):
    def __init__(self, created_at: datetime, date: str, message: str, staff: Staff, status: int, updated_at: datetime):
        super().__init__(created_at, date, message, status, updated_at)
        self.staff = staff

class LeaveReportStudent(LeaveReport):
    def __init__(self, created_at: datetime, date: str, message: str, status: int, student: Student, updated_at: datetime):
        super().__init__(created_at, date, message, status, updated_at)
        self.student = student

class Feedback(BaseReport):
    def __init__(self, created_at: datetime, feedback: str, reply: str, updated_at: datetime):
        super().__init__(created_at, updated_at)
        self.feedback = feedback
        self.reply = reply

class FeedbackStaff(Feedback):
    def __init__(self, created_at: datetime, feedback: str, reply: str, staff: Staff, updated_at: datetime):
        super().__init__(created_at, feedback, reply, updated_at)
        self.staff = staff

class FeedbackStudent(Feedback):
    def __init__(self, created_at: datetime, feedback: str, reply: str, student: Student, updated_at: datetime):
        super().__init__(created_at, feedback, reply, updated_at)
        self.student = student

class Notification(BaseReport):
    def __init__(self, created_at: datetime, message: str, updated_at: datetime):
        super().__init__(created_at, updated_at)
        self.message = message

class NotificationStaff(Notification):
    def __init__(self, created_at: datetime, message: str, staff: Staff, updated_at: datetime):
        super().__init__(created_at, message, updated_at)
        self.staff = staff

class NotificationStudent(Notification):
    def __init__(self, created_at: datetime, message: str, student: Student, updated_at: datetime):
        super().__init__(created_at, message, updated_at)
        self.student = student