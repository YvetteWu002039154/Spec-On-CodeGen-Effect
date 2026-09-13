from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, List, Optional, Tuple, Union


class ValidationError(ValueError):
    pass


class OneToOneField:
    def __init__(self, related: Any):
        self.related = related


class ForeignKey:
    def __init__(self, related: Any):
        self.related = related


class DateTimeField(datetime):
    pass


class DateField(date):
    pass


class CharField(str):
    pass


class TextField(str):
    pass


class EmailField(str):
    pass


class ImageField(str):
    pass


class BooleanField(bool):
    pass


class SmallIntegerField(int):
    pass


class FloatField(float):
    pass


class CustomUserManager:
    def create_user(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        if email is None or str(email).strip() == "":
            raise ValidationError("Email is required")
        if password is None or (isinstance(password, (str, bytes)) and len(password) == 0):
            raise ValidationError("Password is required")
        user = CustomUser(email=str(email).strip().lower(), password=password)
        return user

    def create_superuser(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.user_type = "1"
        return user


@dataclass
class CustomUser:
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    REQUIRED_FIELDS: ClassVar[List[str]] = ["password"]
    USERNAME_FIELD: ClassVar[str] = "email"
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (
        ("1", "Admin"),
        ("2", "Staff"),
        ("3", "Student"),
    )

    objects: ClassVar[CustomUserManager] = CustomUserManager()

    address: TextField = TextField("")
    created_at: datetime = datetime.utcnow()
    email: EmailField = EmailField("")
    fcm_token: TextField = TextField("")
    gender: CharField = CharField("")
    password: Union[bytes, str] = ""
    profile_pic: ImageField = ImageField("")
    updated_at: datetime = datetime.utcnow()
    user_type: CharField = CharField("")
    username: None = None

    def __post_init__(self) -> None:
        if self.email is None or str(self.email).strip() == "":
            raise ValidationError("email cannot be empty")
        self.email = EmailField(str(self.email).strip().lower())
        if self.gender and str(self.gender) not in self.GENDER:
            raise ValidationError(f"gender must be one of {self.GENDER}")
        if self.user_type and str(self.user_type) not in {k for k, _ in self.USER_TYPE}:
            raise ValidationError("user_type is invalid")
        if not isinstance(self.created_at, datetime):
            raise ValidationError("created_at must be a datetime")
        if not isinstance(self.updated_at, datetime):
            raise ValidationError("updated_at must be a datetime")


@dataclass
class Course:
    created_at: datetime = datetime.utcnow()
    name: CharField = CharField("")
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.name is None or str(self.name).strip() == "":
            raise ValidationError("Course name cannot be empty")
        self.name = CharField(str(self.name).strip())
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class Session:
    end_year: date = date.today()
    start_year: date = date.today()

    def __post_init__(self) -> None:
        if not isinstance(self.start_year, date) or not isinstance(self.end_year, date):
            raise ValidationError("start_year/end_year must be date")
        if self.end_year < self.start_year:
            raise ValidationError("end_year cannot be before start_year")


@dataclass
class Admin:
    admin: CustomUser

    def __post_init__(self) -> None:
        if not isinstance(self.admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")


@dataclass
class Staff:
    admin: CustomUser
    course: Course

    def __post_init__(self) -> None:
        if not isinstance(self.admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(self.course, Course):
            raise ValidationError("course must be a Course")


@dataclass
class Student:
    admin: CustomUser
    course: Course
    session: Session

    def __post_init__(self) -> None:
        if not isinstance(self.admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(self.course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(self.session, Session):
            raise ValidationError("session must be a Session")


@dataclass
class Subject:
    course: Course
    created_at: datetime = datetime.utcnow()
    name: CharField = CharField("")
    staff: Staff = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if not isinstance(self.course, Course):
            raise ValidationError("course must be a Course")
        if self.staff is None or not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff")
        if self.name is None or str(self.name).strip() == "":
            raise ValidationError("Subject name cannot be empty")
        self.name = CharField(str(self.name).strip())
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class Attendance:
    created_at: datetime = datetime.utcnow()
    date: date = date.today()
    session: Session = None  # type: ignore[assignment]
    subject: Subject = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if not isinstance(self.date, date):
            raise ValidationError("date must be a date")
        if self.session is None or not isinstance(self.session, Session):
            raise ValidationError("session must be a Session")
        if self.subject is None or not isinstance(self.subject, Subject):
            raise ValidationError("subject must be a Subject")
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class AttendanceReport:
    attendance: Attendance
    created_at: datetime = datetime.utcnow()
    status: bool = False
    student: Student = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if not isinstance(self.attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        if self.student is None or not isinstance(self.student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(self.status, bool):
            raise ValidationError("status must be bool")
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class FeedbackStaff:
    created_at: datetime = datetime.utcnow()
    feedback: TextField = TextField("")
    reply: TextField = TextField("")
    staff: Staff = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.staff is None or not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff")
        if self.feedback is None:
            raise ValidationError("feedback cannot be None")
        self.feedback = TextField(str(self.feedback))
        self.reply = TextField("" if self.reply is None else str(self.reply))
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class FeedbackStudent:
    created_at: datetime = datetime.utcnow()
    feedback: TextField = TextField("")
    reply: TextField = TextField("")
    student: Student = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.student is None or not isinstance(self.student, Student):
            raise ValidationError("student must be a Student")
        if self.feedback is None:
            raise ValidationError("feedback cannot be None")
        self.feedback = TextField(str(self.feedback))
        self.reply = TextField("" if self.reply is None else str(self.reply))
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class LeaveReportStaff:
    created_at: datetime = datetime.utcnow()
    date: CharField = CharField("")
    message: TextField = TextField("")
    staff: Staff = None  # type: ignore[assignment]
    status: int = 0
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.staff is None or not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff")
        if self.date is None:
            raise ValidationError("date cannot be None")
        self.date = CharField(str(self.date))
        self.message = TextField("" if self.message is None else str(self.message))
        if not isinstance(self.status, int):
            raise ValidationError("status must be int")
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class LeaveReportStudent:
    created_at: datetime = datetime.utcnow()
    date: CharField = CharField("")
    message: TextField = TextField("")
    status: int = 0
    student: Student = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.student is None or not isinstance(self.student, Student):
            raise ValidationError("student must be a Student")
        if self.date is None:
            raise ValidationError("date cannot be None")
        self.date = CharField(str(self.date))
        self.message = TextField("" if self.message is None else str(self.message))
        if not isinstance(self.status, int):
            raise ValidationError("status must be int")
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class NotificationStaff:
    created_at: datetime = datetime.utcnow()
    message: TextField = TextField("")
    staff: Staff = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.staff is None or not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.message = TextField("" if self.message is None else str(self.message))
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class NotificationStudent:
    created_at: datetime = datetime.utcnow()
    message: TextField = TextField("")
    student: Student = None  # type: ignore[assignment]
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.student is None or not isinstance(self.student, Student):
            raise ValidationError("student must be a Student")
        self.message = TextField("" if self.message is None else str(self.message))
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")


@dataclass
class StudentResult:
    created_at: datetime = datetime.utcnow()
    exam: float = 0.0
    student: Student = None  # type: ignore[assignment]
    subject: Subject = None  # type: ignore[assignment]
    test: float = 0.0
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if self.student is None or not isinstance(self.student, Student):
            raise ValidationError("student must be a Student")
        if self.subject is None or not isinstance(self.subject, Subject):
            raise ValidationError("subject must be a Subject")
        if not isinstance(self.test, (int, float)) or not isinstance(self.exam, (int, float)):
            raise ValidationError("test/exam must be numeric")
        self.test = float(self.test)
        self.exam = float(self.exam)
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise ValidationError("created_at/updated_at must be datetime")