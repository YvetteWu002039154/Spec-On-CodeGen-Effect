from datetime import datetime, date
from typing import List, Tuple, Union, Optional

class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        return CustomUser(
            email=email,
            password=password,
            user_type='Student',
            address='',
            created_at=datetime.now(),
            fcm_token='',
            gender='',
            profile_pic='',
            updated_at=datetime.now(),
            username=None
        )

    def create_superuser(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        return CustomUser(
            email=email,
            password=password,
            user_type='Admin',
            address='',
            created_at=datetime.now(),
            fcm_token='',
            gender='',
            profile_pic='',
            updated_at=datetime.now(),
            username=None
        )

class CustomUser:
    GENDER: List[str] = ['Male', 'Female', 'Other']
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = 'email'
    USER_TYPE: Tuple[str, ...] = ('Admin', 'Staff', 'Student')
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: str, password: Union[bytes, str], user_type: str,
                 address: str, created_at: datetime, fcm_token: str, gender: str,
                 profile_pic: str, updated_at: datetime, username: None):
        self.email = email
        self.password = password
        self.user_type = user_type
        self.address = address
        self.created_at = created_at
        self.fcm_token = fcm_token
        self.gender = gender
        self.profile_pic = profile_pic
        self.updated_at = updated_at
        self.username = username

class Session:
    def __init__(self, start_year: date, end_year: date):
        self.start_year = start_year
        self.end_year = end_year

class Course:
    def __init__(self, name: str, created_at: datetime, updated_at: datetime):
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at

class Admin:
    def __init__(self, admin: CustomUser):
        self.admin = admin

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
    def __init__(self, name: str, course: Course, staff: Staff,
                 created_at: datetime, updated_at: datetime):
        self.name = name
        self.course = course
        self.staff = staff
        self.created_at = created_at
        self.updated_at = updated_at

class Attendance:
    def __init__(self, date: date, session: Session, subject: Subject,
                 created_at: datetime, updated_at: datetime):
        self.date = date
        self.session = session
        self.subject = subject
        self.created_at = created_at
        self.updated_at = updated_at

class AttendanceReport:
    def __init__(self, attendance: Attendance, student: Student, status: bool,
                 created_at: datetime, updated_at: datetime):
        self.attendance = attendance
        self.student = student
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

class FeedbackStaff:
    def __init__(self, staff: Staff, feedback: str, reply: str,
                 created_at: datetime, updated_at: datetime):
        self.staff = staff
        self.feedback = feedback
        self.reply = reply
        self.created_at = created_at
        self.updated_at = updated_at

class FeedbackStudent:
    def __init__(self, student: Student, feedback: str, reply: str,
                 created_at: datetime, updated_at: datetime):
        self.student = student
        self.feedback = feedback
        self.reply = reply
        self.created_at = created_at
        self.updated_at = updated_at

class LeaveReportStaff:
    def __init__(self, staff: Staff, date: str, message: str, status: int,
                 created_at: datetime, updated_at: datetime):
        self.staff = staff
        self.date = date
        self.message = message
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

class LeaveReportStudent:
    def __init__(self, student: Student, date: str, message: str, status: int,
                 created_at: datetime, updated_at: datetime):
        self.student = student
        self.date = date
        self.message = message
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

class NotificationStaff:
    def __init__(self, staff: Staff, message: str,
                 created_at: datetime, updated_at: datetime):
        self.staff = staff
        self.message = message
        self.created_at = created_at
        self.updated_at = updated_at

class NotificationStudent:
    def __init__(self, student: Student, message: str,
                 created_at: datetime, updated_at: datetime):
        self.student = student
        self.message = message
        self.created_at = created_at
        self.updated_at = updated_at

class StudentResult:
    def __init__(self, student: Student, subject: Subject, exam: float, test: float,
                 created_at: datetime, updated_at: datetime):
        self.student = student
        self.subject = subject
        self.exam = exam
        self.test = test
        self.created_at = created_at
        self.updated_at = updated_at