from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, List, Optional, Tuple, Union


class CustomUserManager:
    def create_user(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        if not email or not isinstance(email, str):
            raise ValueError("email must be a non-empty string")
        if password is None or (isinstance(password, (str, bytes)) and len(password) == 0):
            raise ValueError("password must be provided")
        return CustomUser(email=email, password=password)

    def create_superuser(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.user_type = "1"
        return user


@dataclass(frozen=True)
class OneToOneField:
    target: Any


@dataclass(frozen=True)
class ForeignKey:
    target: Any


@dataclass(frozen=True)
class DateTimeField:
    value: datetime


@dataclass(frozen=True)
class DateField:
    value: date


@dataclass(frozen=True)
class CharField:
    value: str


@dataclass(frozen=True)
class TextField:
    value: str


@dataclass(frozen=True)
class EmailField:
    value: str


@dataclass(frozen=True)
class ImageField:
    value: str


@dataclass(frozen=True)
class BooleanField:
    value: bool


@dataclass(frozen=True)
class SmallIntegerField:
    value: int


@dataclass(frozen=True)
class FloatField:
    value: float


class CustomUser:
    GENDER: ClassVar[List[str]] = ["Male", "Female"]
    REQUIRED_FIELDS: ClassVar[List[str]] = []
    USERNAME_FIELD: ClassVar[str] = "email"
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (
        ("1", "Admin"),
        ("2", "Staff"),
        ("3", "Student"),
    )

    objects: ClassVar[CustomUserManager] = CustomUserManager()

    def __init__(
        self,
        email: str,
        password: Union[bytes, str],
        address: str = "",
        fcm_token: str = "",
        gender: str = "",
        profile_pic: str = "",
        user_type: str = "3",
        username: Optional[None] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not email or not isinstance(email, str):
            raise ValueError("email must be a non-empty string")
        if password is None or (isinstance(password, (str, bytes)) and len(password) == 0):
            raise ValueError("password must be provided")
        if gender and gender not in self.GENDER:
            raise ValueError(f"gender must be one of {self.GENDER}")
        if user_type not in {t[0] for t in self.USER_TYPE}:
            raise ValueError("user_type is invalid")

        self.email: EmailField = EmailField(email)
        self.password: Union[bytes, str] = password
        self.address: TextField = TextField(address)
        self.fcm_token: TextField = TextField(fcm_token)
        self.gender: CharField = CharField(gender)
        self.profile_pic: ImageField = ImageField(profile_pic)
        self.user_type: CharField = CharField(user_type)
        self.username: Optional[None] = username

        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class Course:
    def __init__(
        self,
        name: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        self.name: CharField = CharField(name)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class Session:
    def __init__(self, start_year: date, end_year: date) -> None:
        if not isinstance(start_year, date) or not isinstance(end_year, date):
            raise ValueError("start_year and end_year must be date instances")
        if end_year < start_year:
            raise ValueError("end_year must be >= start_year")
        self.start_year: DateField = DateField(start_year)
        self.end_year: DateField = DateField(end_year)


class Admin:
    def __init__(self, admin: CustomUser) -> None:
        if not isinstance(admin, CustomUser):
            raise TypeError("admin must be a CustomUser")
        self.admin: OneToOneField = OneToOneField(admin)


class Staff:
    def __init__(self, admin: CustomUser, course: Course) -> None:
        if not isinstance(admin, CustomUser):
            raise TypeError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise TypeError("course must be a Course")
        self.admin: OneToOneField = OneToOneField(admin)
        self.course: ForeignKey = ForeignKey(course)


class Student:
    def __init__(self, admin: CustomUser, course: Course, session: Session) -> None:
        if not isinstance(admin, CustomUser):
            raise TypeError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise TypeError("course must be a Course")
        if not isinstance(session, Session):
            raise TypeError("session must be a Session")
        self.admin: OneToOneField = OneToOneField(admin)
        self.course: ForeignKey = ForeignKey(course)
        self.session: ForeignKey = ForeignKey(session)


class Subject:
    def __init__(
        self,
        name: str,
        course: Course,
        staff: Staff,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        if not isinstance(course, Course):
            raise TypeError("course must be a Course")
        if not isinstance(staff, Staff):
            raise TypeError("staff must be a Staff")
        self.name: CharField = CharField(name)
        self.course: ForeignKey = ForeignKey(course)
        self.staff: ForeignKey = ForeignKey(staff)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class Attendance:
    def __init__(
        self,
        date_value: date,
        session: Session,
        subject: Subject,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(date_value, date):
            raise TypeError("date must be a date")
        if not isinstance(session, Session):
            raise TypeError("session must be a Session")
        if not isinstance(subject, Subject):
            raise TypeError("subject must be a Subject")
        self.date: DateField = DateField(date_value)
        self.session: ForeignKey = ForeignKey(session)
        self.subject: ForeignKey = ForeignKey(subject)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class AttendanceReport:
    def __init__(
        self,
        attendance: Attendance,
        student: Student,
        status: bool,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(attendance, Attendance):
            raise TypeError("attendance must be an Attendance")
        if not isinstance(student, Student):
            raise TypeError("student must be a Student")
        if not isinstance(status, bool):
            raise TypeError("status must be a bool")
        self.attendance: ForeignKey = ForeignKey(attendance)
        self.student: ForeignKey = ForeignKey(student)
        self.status: BooleanField = BooleanField(status)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class FeedbackStaff:
    def __init__(
        self,
        staff: Staff,
        feedback: str,
        reply: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(staff, Staff):
            raise TypeError("staff must be a Staff")
        if feedback is None or not isinstance(feedback, str):
            raise TypeError("feedback must be a string")
        if reply is None or not isinstance(reply, str):
            raise TypeError("reply must be a string")
        self.staff: ForeignKey = ForeignKey(staff)
        self.feedback: TextField = TextField(feedback)
        self.reply: TextField = TextField(reply)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class FeedbackStudent:
    def __init__(
        self,
        student: Student,
        feedback: str,
        reply: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(student, Student):
            raise TypeError("student must be a Student")
        if feedback is None or not isinstance(feedback, str):
            raise TypeError("feedback must be a string")
        if reply is None or not isinstance(reply, str):
            raise TypeError("reply must be a string")
        self.student: ForeignKey = ForeignKey(student)
        self.feedback: TextField = TextField(feedback)
        self.reply: TextField = TextField(reply)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class LeaveReportStaff:
    def __init__(
        self,
        staff: Staff,
        date_value: str,
        message: str,
        status: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(staff, Staff):
            raise TypeError("staff must be a Staff")
        if date_value is None or not isinstance(date_value, str):
            raise TypeError("date must be a string")
        if message is None or not isinstance(message, str):
            raise TypeError("message must be a string")
        if not isinstance(status, int):
            raise TypeError("status must be an int")
        self.staff: ForeignKey = ForeignKey(staff)
        self.date: CharField = CharField(date_value)
        self.message: TextField = TextField(message)
        self.status: SmallIntegerField = SmallIntegerField(status)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class LeaveReportStudent:
    def __init__(
        self,
        student: Student,
        date_value: str,
        message: str,
        status: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(student, Student):
            raise TypeError("student must be a Student")
        if date_value is None or not isinstance(date_value, str):
            raise TypeError("date must be a string")
        if message is None or not isinstance(message, str):
            raise TypeError("message must be a string")
        if not isinstance(status, int):
            raise TypeError("status must be an int")
        self.student: ForeignKey = ForeignKey(student)
        self.date: CharField = CharField(date_value)
        self.message: TextField = TextField(message)
        self.status: SmallIntegerField = SmallIntegerField(status)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class NotificationStaff:
    def __init__(
        self,
        staff: Staff,
        message: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(staff, Staff):
            raise TypeError("staff must be a Staff")
        if message is None or not isinstance(message, str):
            raise TypeError("message must be a string")
        self.staff: ForeignKey = ForeignKey(staff)
        self.message: TextField = TextField(message)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class NotificationStudent:
    def __init__(
        self,
        student: Student,
        message: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(student, Student):
            raise TypeError("student must be a Student")
        if message is None or not isinstance(message, str):
            raise TypeError("message must be a string")
        self.student: ForeignKey = ForeignKey(student)
        self.message: TextField = TextField(message)
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())


class StudentResult:
    def __init__(
        self,
        student: Student,
        subject: Subject,
        test: float,
        exam: float,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not isinstance(student, Student):
            raise TypeError("student must be a Student")
        if not isinstance(subject, Subject):
            raise TypeError("subject must be a Subject")
        if not isinstance(test, (int, float)):
            raise TypeError("test must be a number")
        if not isinstance(exam, (int, float)):
            raise TypeError("exam must be a number")
        self.student: ForeignKey = ForeignKey(student)
        self.subject: ForeignKey = ForeignKey(subject)
        self.test: FloatField = FloatField(float(test))
        self.exam: FloatField = FloatField(float(exam))
        now = datetime.utcnow()
        self.created_at: DateTimeField = DateTimeField(created_at or now)
        self.updated_at: DateTimeField = DateTimeField(updated_at or now)

    def touch(self) -> None:
        self.updated_at = DateTimeField(datetime.utcnow())