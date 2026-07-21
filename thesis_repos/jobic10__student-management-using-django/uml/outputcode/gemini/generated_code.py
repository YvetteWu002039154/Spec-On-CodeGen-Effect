from __future__ import annotations
from datetime import datetime, date
from typing import List, Tuple, Union, Optional, Any

class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> CustomUser:
        user = CustomUser(email=email, password=password)
        user.user_type = '3'
        return user

    def create_superuser(self, email: str, password: Union[bytes, str]) -> CustomUser:
        user = CustomUser(email=email, password=password)
        user.user_type = '1'
        return user

class CustomUser:
    GENDER: List[str] = ['Male', 'Female', 'Other']
    REQUIRED_FIELDS: List[str] = []
    USERNAME_FIELD: str = 'email'
    USER_TYPE: Tuple[Tuple[str, str], ...] = (('1', 'HOD'), ('2', 'Staff'), ('3', 'Student'))
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: str = "", password: Union[bytes, str] = "", address: str = "",
                 fcm_token: str = "", gender: str = "", profile_pic: str = "",
                 user_type: str = "3", username: type(None) = None):
        self._email = email
        self._password = password
        self._address = address
        self._fcm_token = fcm_token
        self._gender = gender
        self._profile_pic = profile_pic
        self._user_type = user_type
        self._username = username
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def email(self) -> str: return self._email
    @email.setter
    def email(self, value: str):
        self._email = value
        self._updated_at = datetime.now()

    @property
    def password(self) -> Union[bytes, str]: return self._password
    @password.setter
    def password(self, value: Union[bytes, str]):
        self._password = value
        self._updated_at = datetime.now()

    @property
    def address(self) -> str: return self._address
    @address.setter
    def address(self, value: str):
        self._address = value
        self._updated_at = datetime.now()

    @property
    def fcm_token(self) -> str: return self._fcm_token
    @fcm_token.setter
    def fcm_token(self, value: str):
        self._fcm_token = value
        self._updated_at = datetime.now()

    @property
    def gender(self) -> str: return self._gender
    @gender.setter
    def gender(self, value: str):
        if value and value not in self.GENDER:
            raise ValueError(f"Gender must be one of {self.GENDER}")
        self._gender = value
        self._updated_at = datetime.now()

    @property
    def profile_pic(self) -> str: return self._profile_pic
    @profile_pic.setter
    def profile_pic(self, value: str):
        self._profile_pic = value
        self._updated_at = datetime.now()

    @property
    def user_type(self) -> str: return self._user_type
    @user_type.setter
    def user_type(self, value: str):
        self._user_type = value
        self._updated_at = datetime.now()

    @property
    def username(self) -> type(None): return self._username
    @username.setter
    def username(self, value: type(None)):
        self._username = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class Admin:
    def __init__(self, admin: CustomUser):
        self._admin = admin

    @property
    def admin(self) -> CustomUser: return self._admin
    @admin.setter
    def admin(self, value: CustomUser): self._admin = value

class Session:
    def __init__(self, start_year: date, end_year: date):
        self._start_year = start_year
        self._end_year = end_year

    @property
    def start_year(self) -> date: return self._start_year
    @start_year.setter
    def start_year(self, value: date): self._start_year = value

    @property
    def end_year(self) -> date: return self._end_year
    @end_year.setter
    def end_year(self, value: date): self._end_year = value

class Course:
    def __init__(self, name: str):
        self._name = name
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def name(self) -> str: return self._name
    @name.setter
    def name(self, value: str):
        self._name = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class Staff:
    def __init__(self, admin: CustomUser, course: Course):
        self._admin = admin
        self._course = course

    @property
    def admin(self) -> CustomUser: return self._admin
    @admin.setter
    def admin(self, value: CustomUser): self._admin = value

    @property
    def course(self) -> Course: return self._course
    @course.setter
    def course(self, value: Course): self._course = value

class Student:
    def __init__(self, admin: CustomUser, course: Course, session: Session):
        self._admin = admin
        self._course = course
        self._session = session

    @property
    def admin(self) -> CustomUser: return self._admin
    @admin.setter
    def admin(self, value: CustomUser): self._admin = value

    @property
    def course(self) -> Course: return self._course
    @course.setter
    def course(self, value: Course): self._course = value

    @property
    def session(self) -> Session: return self._session
    @session.setter
    def session(self, value: Session): self._session = value

class Subject:
    def __init__(self, name: str, course: Course, staff: Staff):
        self._name = name
        self._course = course
        self._staff = staff
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def name(self) -> str: return self._name
    @name.setter
    def name(self, value: str):
        self._name = value
        self._updated_at = datetime.now()

    @property
    def course(self) -> Course: return self._course
    @course.setter
    def course(self, value: Course):
        self._course = value
        self._updated_at = datetime.now()

    @property
    def staff(self) -> Staff: return self._staff
    @staff.setter
    def staff(self, value: Staff):
        self._staff = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class Attendance:
    def __init__(self, date_val: date, session: Session, subject: Subject):
        self._date = date_val
        self._session = session
        self._subject = subject
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def date(self) -> date: return self._date
    @date.setter
    def date(self, value: date):
        self._date = value
        self._updated_at = datetime.now()

    @property
    def session(self) -> Session: return self._session
    @session.setter
    def session(self, value: Session):
        self._session = value
        self._updated_at = datetime.now()

    @property
    def subject(self) -> Subject: return self._subject
    @subject.setter
    def subject(self, value: Subject):
        self._subject = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class AttendanceReport:
    def __init__(self, attendance: Attendance, student: Student, status: bool):
        self._attendance = attendance
        self._student = student
        self._status = status
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def attendance(self) -> Attendance: return self._attendance
    @attendance.setter
    def attendance(self, value: Attendance):
        self._attendance = value
        self._updated_at = datetime.now()

    @property
    def student(self) -> Student: return self._student
    @student.setter
    def student(self, value: Student):
        self._student = value
        self._updated_at = datetime.now()

    @property
    def status(self) -> bool: return self._status
    @status.setter
    def status(self, value: bool):
        self._status = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class FeedbackStaff:
    def __init__(self, staff: Staff, feedback: str, reply: str):
        self._staff = staff
        self._feedback = feedback
        self._reply = reply
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def staff(self) -> Staff: return self._staff
    @staff.setter
    def staff(self, value: Staff):
        self._staff = value
        self._updated_at = datetime.now()

    @property
    def feedback(self) -> str: return self._feedback
    @feedback.setter
    def feedback(self, value: str):
        self._feedback = value
        self._updated_at = datetime.now()

    @property
    def reply(self) -> str: return self._reply
    @reply.setter
    def reply(self, value: str):
        self._reply = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class FeedbackStudent:
    def __init__(self, student: Student, feedback: str, reply: str):
        self._student = student
        self._feedback = feedback
        self._reply = reply
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def student(self) -> Student: return self._student
    @student.setter
    def student(self, value: Student):
        self._student = value
        self._updated_at = datetime.now()

    @property
    def feedback(self) -> str: return self._feedback
    @feedback.setter
    def feedback(self, value: str):
        self._feedback = value
        self._updated_at = datetime.now()

    @property
    def reply(self) -> str: return self._reply
    @reply.setter
    def reply(self, value: str):
        self._reply = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class LeaveReportStaff:
    def __init__(self, staff: Staff, date_val: str, message: str, status: int):
        self._staff = staff
        self._date = date_val
        self._message = message
        self._status = status
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def staff(self) -> Staff: return self._staff
    @staff.setter
    def staff(self, value: Staff):
        self._staff = value
        self._updated_at = datetime.now()

    @property
    def date(self) -> str: return self._date
    @date.setter
    def date(self, value: str):
        self._date = value
        self._updated_at = datetime.now()

    @property
    def message(self) -> str: return self._message
    @message.setter
    def message(self, value: str):
        self._message = value
        self._updated_at = datetime.now()

    @property
    def status(self) -> int: return self._status
    @status.setter
    def status(self, value: int):
        self._status = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class LeaveReportStudent:
    def __init__(self, student: Student, date_val: str, message: str, status: int):
        self._student = student
        self._date = date_val
        self._message = message
        self._status = status
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def student(self) -> Student: return self._student
    @student.setter
    def student(self, value: Student):
        self._student = value
        self._updated_at = datetime.now()

    @property
    def date(self) -> str: return self._date
    @date.setter
    def date(self, value: str):
        self._date = value
        self._updated_at = datetime.now()

    @property
    def message(self) -> str: return self._message
    @message.setter
    def message(self, value: str):
        self._message = value
        self._updated_at = datetime.now()

    @property
    def status(self) -> int: return self._status
    @status.setter
    def status(self, value: int):
        self._status = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class NotificationStaff:
    def __init__(self, staff: Staff, message: str):
        self._staff = staff
        self._message = message
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def staff(self) -> Staff: return self._staff
    @staff.setter
    def staff(self, value: Staff):
        self._staff = value
        self._updated_at = datetime.now()

    @property
    def message(self) -> str: return self._message
    @message.setter
    def message(self, value: str):
        self._message = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class NotificationStudent:
    def __init__(self, student: Student, message: str):
        self._student = student
        self._message = message
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def student(self) -> Student: return self._student
    @student.setter
    def student(self, value: Student):
        self._student = value
        self._updated_at = datetime.now()

    @property
    def message(self) -> str: return self._message
    @message.setter
    def message(self, value: str):
        self._message = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at

class StudentResult:
    def __init__(self, student: Student, subject: Subject, test: float, exam: float):
        self._student = student
        self._subject = subject
        self._test = test
        self._exam = exam
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def student(self) -> Student: return self._student
    @student.setter
    def student(self, value: Student):
        self._student = value
        self._updated_at = datetime.now()

    @property
    def subject(self) -> Subject: return self._subject
    @subject.setter
    def subject(self, value: Subject):
        self._subject = value
        self._updated_at = datetime.now()

    @property
    def test(self) -> float: return self._test
    @test.setter
    def test(self, value: float):
        self._test = value
        self._updated_at = datetime.now()

    @property
    def exam(self) -> float: return self._exam
    @exam.setter
    def exam(self, value: float):
        self._exam = value
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def updated_at(self) -> datetime: return self._updated_at