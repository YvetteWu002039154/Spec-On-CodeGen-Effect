from datetime import datetime, date
from typing import List, Tuple, Union, Optional

class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        return CustomUser(email=email, password=password, user_type='Student')

    def create_superuser(self, email: str, password: Union[bytes, str]) -> 'CustomUser':
        return CustomUser(email=email, password=password, user_type='Admin')

class CustomUser:
    GENDER: List[str] = ['Male', 'Female', 'Other']
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = 'email'
    USER_TYPE: Tuple[str, ...] = ('Admin', 'Staff', 'Student')
    
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: str, password: Union[bytes, str], user_type: str,
                 address: str = "", fcm_token: str = "", gender: str = "",
                 profile_pic: str = ""):
        self.email: str = email
        self.password: Union[bytes, str] = password
        self.user_type: str = user_type
        self.address: str = address
        self.fcm_token: str = fcm_token
        self.gender: str = gender
        self.profile_pic: str = profile_pic
        self.username: None = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class Admin:
    def __init__(self, admin: CustomUser):
        self.admin: CustomUser = admin

class Course:
    def __init__(self, name: str):
        self.name: str = name
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class Session:
    def __init__(self, start_year: date, end_year: date):
        self.start_year: date = start_year
        self.end_year: date = end_year

class Staff:
    def __init__(self, admin: CustomUser, course: Course):
        self.admin: CustomUser = admin
        self.course: Course = course

class Student:
    def __init__(self, admin: CustomUser, course: Course, session: Session):
        self.admin: CustomUser = admin
        self.course: Course = course
        self.session: Session = session

class Subject:
    def __init__(self, name: str, course: Course, staff: Staff):
        self.name: str = name
        self.course: Course = course
        self.staff: Staff = staff
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class Attendance:
    def __init__(self, date_val: date, session: Session, subject: Subject):
        self.date: date = date_val
        self.session: Session = session
        self.subject: Subject = subject
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class AttendanceReport:
    def __init__(self, attendance: Attendance, student: Student, status: bool):
        self.attendance: Attendance = attendance
        self.student: Student = student
        self.status: bool = status
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class FeedbackStaff:
    def __init__(self, staff: Staff, feedback: str, reply: str = ""):
        self.staff: Staff = staff
        self.feedback: str = feedback
        self.reply: str = reply
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class FeedbackStudent:
    def __init__(self, student: Student, feedback: str, reply: str = ""):
        self.student: Student = student
        self.feedback: str = feedback
        self.reply: str = reply
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class LeaveReportStaff:
    def __init__(self, staff: Staff, date_val: str, message: str, status: int):
        self.staff: Staff = staff
        self.date: str = date_val
        self.message: str = message
        self.status: int = status
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class LeaveReportStudent:
    def __init__(self, student: Student, date_val: str, message: str, status: int):
        self.student: Student = student
        self.date: str = date_val
        self.message: str = message
        self.status: int = status
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class NotificationStaff:
    def __init__(self, staff: Staff, message: str):
        self.staff: Staff = staff
        self.message: str = message
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class NotificationStudent:
    def __init__(self, student: Student, message: str):
        self.student: Student = student
        self.message: str = message
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

class StudentResult:
    def __init__(self, student: Student, subject: Subject, test: float, exam: float):
        self.student: Student = student
        self.subject: Subject = subject
        self.test: float = test
        self.exam: float = exam
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()