from datetime import datetime, date
from typing import Union, List, Tuple, Optional, Any

class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        return CustomUser(
            address="",
            created_at=datetime.now(),
            email=email,
            fcm_token="",
            gender="",
            password=password,
            profile_pic="",
            updated_at=datetime.now(),
            user_type="user",
            username=None
        )

    def create_superuser(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        user = self.create_user(email, password)
        user.user_type = "superuser"
        return user

class CustomUser:
    GENDER: List[str] = []
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = ""
    USER_TYPE: Tuple[str, ...] = ()
    objects: CustomUserManager = CustomUserManager()

    def __init__(
        self,
        address: str,
        created_at: datetime,
        email: str,
        fcm_token: str,
        gender: str,
        password: Union[bytes, str],
        profile_pic: str,
        updated_at: datetime,
        user_type: str,
        username: None = None
    ):
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
        self.end_year = end_year
        self.start_year = start_year

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

class FeedbackStaff:
    def __init__(self, created_at: datetime, feedback: str, reply: str, staff: Staff, updated_at: datetime):
        self.created_at = created_at
        self.feedback = feedback
        self.reply = reply
        self.staff = staff
        self.updated_at = updated_at

class FeedbackStudent:
    def __init__(self, created_at: datetime, feedback: str, reply: str, student: Student, updated_at: datetime):
        self.created_at = created_at
        self.feedback = feedback
        self.reply = reply
        self.student = student
        self.updated_at = updated_at

class LeaveReportStaff:
    def __init__(self, created_at: datetime, date: str, message: str, staff: Staff, status: int, updated_at: datetime):
        self.created_at = created_at
        self.date = date
        self.message = message
        self.staff = staff
        self.status = status
        self.updated_at = updated_at

class LeaveReportStudent:
    def __init__(self, created_at: datetime, date: str, message: str, status: int, student: Student, updated_at: datetime):
        self.created_at = created_at
        self.date = date
        self.message = message
        self.status = status
        self.student = student
        self.updated_at = updated_at

class NotificationStaff:
    def __init__(self, created_at: datetime, message: str, staff: Staff, updated_at: datetime):
        self.created_at = created_at
        self.message = message
        self.staff = staff
        self.updated_at = updated_at

class NotificationStudent:
    def __init__(self, created_at: datetime, message: str, student: Student, updated_at: datetime):
        self.created_at = created_at
        self.message = message
        self.student = student
        self.updated_at = updated_at

class StudentResult:
    def __init__(self, created_at: datetime, exam: float, student: Student, subject: Subject, test: float, updated_at: datetime):
        self.created_at = created_at
        self.exam = exam
        self.student = student
        self.subject = subject
        self.test = test
        self.updated_at = updated_at