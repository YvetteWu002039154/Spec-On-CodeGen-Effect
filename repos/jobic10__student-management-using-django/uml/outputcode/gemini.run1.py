from typing import List, Tuple, Optional, Union
from datetime import datetime, date

class CustomUserManager:
    def create_user(self, email: str, password: Union[str, bytes]) -> 'CustomUser':
        return CustomUser(email=email, password=password)

    def create_superuser(self, email: str, password: Union[str, bytes]) -> 'CustomUser':
        user = self.create_user(email, password)
        user.user_type = '1'
        return user

class CustomUser:
    GENDER: List[str] = ['Male', 'Female']
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = 'email'
    USER_TYPE: Tuple[Tuple[str, str], ...] = (('1', 'HOD'), ('2', 'Staff'), ('3', 'Student'))
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: str, password: Union[str, bytes],
                 address: str = "", fcm_token: str = "", gender: str = "",
                 profile_pic: str = "", user_type: str = "", username: None = None,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.email = email
        self.password = password
        self.address = address
        self.fcm_token = fcm_token
        self.gender = gender
        self.profile_pic = profile_pic
        self.user_type = user_type
        self.username = username
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class Admin:
    def __init__(self, admin: CustomUser):
        self.admin = admin

class Course:
    def __init__(self, name: str, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.name = name
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class Session:
    def __init__(self, start_year: date, end_year: date):
        self.start_year = start_year
        self.end_year = end_year

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
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.name = name
        self.course = course
        self.staff = staff
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class Attendance:
    def __init__(self, date: date, session: Session, subject: Subject,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.date = date
        self.session = session
        self.subject = subject
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class AttendanceReport:
    def __init__(self, attendance: Attendance, student: Student, status: bool,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.attendance = attendance
        self.student = student
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class FeedbackStaff:
    def __init__(self, staff: Staff, feedback: str, reply: str,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.staff = staff
        self.feedback = feedback
        self.reply = reply
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class FeedbackStudent:
    def __init__(self, student: Student, feedback: str, reply: str,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.student = student
        self.feedback = feedback
        self.reply = reply
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class LeaveReportStaff:
    def __init__(self, staff: Staff, date: str, message: str, status: int,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.staff = staff
        self.date = date
        self.message = message
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class LeaveReportStudent:
    def __init__(self, student: Student, date: str, message: str, status: int,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.student = student
        self.date = date
        self.message = message
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class NotificationStaff:
    def __init__(self, staff: Staff, message: str,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.staff = staff
        self.message = message
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class NotificationStudent:
    def __init__(self, student: Student, message: str,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.student = student
        self.message = message
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class StudentResult:
    def __init__(self, student: Student, subject: Subject, test: float, exam: float,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.student = student
        self.subject = subject
        self.test = test
        self.exam = exam
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()