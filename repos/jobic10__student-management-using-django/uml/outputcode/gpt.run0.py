from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union


class ValidationError(ValueError):
    pass


class InMemoryDB:
    _counters: ClassVar[Dict[type, int]] = {}

    @classmethod
    def next_id(cls, model_cls: type) -> int:
        cls._counters.setdefault(model_cls, 0)
        cls._counters[model_cls] += 1
        return cls._counters[model_cls]


@dataclass(frozen=True)
class OneToOneField:
    target: Any


@dataclass(frozen=True)
class ForeignKey:
    target: Any


class BaseModel:
    id: int

    def __init__(self) -> None:
        self.id = InMemoryDB.next_id(self.__class__)


class TimestampedModel(BaseModel):
    created_at: datetime
    updated_at: datetime

    def __init__(self) -> None:
        super().__init__()
        now = datetime.utcnow()
        self.created_at = now
        self.updated_at = now

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> "CustomUser":
        if not email or not isinstance(email, str):
            raise ValidationError("email is required")
        if password is None or (isinstance(password, str) and password == "") or (isinstance(password, (bytes, bytearray)) and len(password) == 0):
            raise ValidationError("password is required")
        user = CustomUser(email=email, password=password)
        return user

    def create_superuser(self, email: str, password: Union[bytes, str]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.user_type = "1"
        user.touch()
        return user


class CustomUser(TimestampedModel):
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (("1", "Admin"), ("2", "Staff"), ("3", "Student"))
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = []

    objects: ClassVar[CustomUserManager] = CustomUserManager()

    username: None
    email: str
    password: Union[bytes, str]
    user_type: str
    address: str
    gender: str
    profile_pic: str
    fcm_token: str

    def __init__(
        self,
        email: str,
        password: Union[bytes, str],
        user_type: str = "3",
        address: str = "",
        gender: str = "Other",
        profile_pic: str = "",
        fcm_token: str = "",
    ) -> None:
        super().__init__()
        self.username = None
        self.email = email
        self.password = password
        self.user_type = user_type
        self.address = address
        self.gender = gender
        self.profile_pic = profile_pic
        self.fcm_token = fcm_token
        self._validate()

    def _validate(self) -> None:
        if not isinstance(self.email, str) or not self.email:
            raise ValidationError("email must be a non-empty string")
        if "@" not in self.email:
            raise ValidationError("email must contain '@'")
        if self.user_type not in {k for k, _ in self.USER_TYPE}:
            raise ValidationError("invalid user_type")
        if self.gender not in self.GENDER:
            raise ValidationError("invalid gender")


class Admin(BaseModel):
    admin: OneToOneField

    def __init__(self, admin: CustomUser) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        self.admin = OneToOneField(admin)


class Course(TimestampedModel):
    name: str

    def __init__(self, name: str) -> None:
        super().__init__()
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        self.name = name.strip()


class Session(BaseModel):
    start_year: date
    end_year: date

    def __init__(self, start_year: date, end_year: date) -> None:
        super().__init__()
        if not isinstance(start_year, date) or not isinstance(end_year, date):
            raise ValidationError("start_year and end_year must be date")
        if end_year < start_year:
            raise ValidationError("end_year must be >= start_year")
        self.start_year = start_year
        self.end_year = end_year


class Staff(BaseModel):
    admin: OneToOneField
    course: ForeignKey

    def __init__(self, admin: CustomUser, course: Course) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        self.admin = OneToOneField(admin)
        self.course = ForeignKey(course)


class Student(BaseModel):
    admin: OneToOneField
    course: ForeignKey
    session: ForeignKey

    def __init__(self, admin: CustomUser, course: Course, session: Session) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        self.admin = OneToOneField(admin)
        self.course = ForeignKey(course)
        self.session = ForeignKey(session)


class Subject(TimestampedModel):
    name: str
    course: ForeignKey
    staff: ForeignKey

    def __init__(self, name: str, course: Course, staff: Staff) -> None:
        super().__init__()
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.name = name.strip()
        self.course = ForeignKey(course)
        self.staff = ForeignKey(staff)


class Attendance(TimestampedModel):
    date: date
    session: ForeignKey
    subject: ForeignKey

    def __init__(self, date_value: date, session: Session, subject: Subject) -> None:
        super().__init__()
        if not isinstance(date_value, date):
            raise ValidationError("date must be a date")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        self.date = date_value
        self.session = ForeignKey(session)
        self.subject = ForeignKey(subject)


class AttendanceReport(TimestampedModel):
    attendance: ForeignKey
    student: ForeignKey
    status: bool

    def __init__(self, attendance: Attendance, student: Student, status: bool) -> None:
        super().__init__()
        if not isinstance(attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(status, bool):
            raise ValidationError("status must be a bool")
        self.attendance = ForeignKey(attendance)
        self.student = ForeignKey(student)
        self.status = status


class FeedbackStaff(TimestampedModel):
    staff: ForeignKey
    feedback: str
    reply: str

    def __init__(self, staff: Staff, feedback: str, reply: str = "") -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(feedback, str):
            raise ValidationError("feedback must be a string")
        if not isinstance(reply, str):
            raise ValidationError("reply must be a string")
        self.staff = ForeignKey(staff)
        self.feedback = feedback
        self.reply = reply


class FeedbackStudent(TimestampedModel):
    student: ForeignKey
    feedback: str
    reply: str

    def __init__(self, student: Student, feedback: str, reply: str = "") -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(feedback, str):
            raise ValidationError("feedback must be a string")
        if not isinstance(reply, str):
            raise ValidationError("reply must be a string")
        self.student = ForeignKey(student)
        self.feedback = feedback
        self.reply = reply


class LeaveReportStaff(TimestampedModel):
    staff: ForeignKey
    date: str
    message: str
    status: int

    def __init__(self, staff: Staff, date_value: str, message: str, status: int = 0) -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(date_value, str):
            raise ValidationError("date must be a string")
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        if not isinstance(status, int):
            raise ValidationError("status must be an int")
        self.staff = ForeignKey(staff)
        self.date = date_value
        self.message = message
        self.status = status


class LeaveReportStudent(TimestampedModel):
    student: ForeignKey
    date: str
    message: str
    status: int

    def __init__(self, student: Student, date_value: str, message: str, status: int = 0) -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(date_value, str):
            raise ValidationError("date must be a string")
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        if not isinstance(status, int):
            raise ValidationError("status must be an int")
        self.student = ForeignKey(student)
        self.date = date_value
        self.message = message
        self.status = status


class NotificationStaff(TimestampedModel):
    staff: ForeignKey
    message: str

    def __init__(self, staff: Staff, message: str) -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        self.staff = ForeignKey(staff)
        self.message = message


class NotificationStudent(TimestampedModel):
    student: ForeignKey
    message: str

    def __init__(self, student: Student, message: str) -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        self.student = ForeignKey(student)
        self.message = message


class StudentResult(TimestampedModel):
    student: ForeignKey
    subject: ForeignKey
    test: float
    exam: float

    def __init__(self, student: Student, subject: Subject, test: float, exam: float) -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        if not isinstance(test, (int, float)):
            raise ValidationError("test must be a number")
        if not isinstance(exam, (int, float)):
            raise ValidationError("exam must be a number")
        self.student = ForeignKey(student)
        self.subject = ForeignKey(subject)
        self.test = float(test)
        self.exam = float(exam)