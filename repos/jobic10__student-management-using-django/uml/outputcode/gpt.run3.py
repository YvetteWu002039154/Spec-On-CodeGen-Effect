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


class DateTimeField:
    def __init__(self, value: Optional[datetime] = None):
        self.value = value


class DateField:
    def __init__(self, value: Optional[date] = None):
        self.value = value


class CharField:
    def __init__(self, value: Optional[str] = None):
        self.value = value


class TextField:
    def __init__(self, value: Optional[str] = None):
        self.value = value


class EmailField:
    def __init__(self, value: Optional[str] = None):
        self.value = value


class ImageField:
    def __init__(self, value: Optional[str] = None):
        self.value = value


class BooleanField:
    def __init__(self, value: Optional[bool] = None):
        self.value = value


class SmallIntegerField:
    def __init__(self, value: Optional[int] = None):
        self.value = value


class FloatField:
    def __init__(self, value: Optional[float] = None):
        self.value = value


def _now() -> datetime:
    return datetime.utcnow()


def _require_non_empty(value: Optional[str], field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return str(value)


def _validate_email(value: Optional[str]) -> str:
    v = _require_non_empty(value, "email").strip().lower()
    if "@" not in v or v.startswith("@") or v.endswith("@"):
        raise ValidationError("email must be a valid email address")
    return v


def _validate_choice(value: Optional[str], choices: List[str], field_name: str) -> str:
    v = _require_non_empty(value, field_name)
    if v not in choices:
        raise ValidationError(f"{field_name} must be one of {choices}")
    return v


def _validate_user_type(value: Optional[str], allowed: Tuple[Tuple[str, str], ...]) -> str:
    v = _require_non_empty(value, "user_type")
    allowed_keys = [k for k, _ in allowed]
    if v not in allowed_keys:
        raise ValidationError(f"user_type must be one of {allowed_keys}")
    return v


def _validate_small_int(value: int, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an int")
    if value < -32768 or value > 32767:
        raise ValidationError(f"{field_name} must fit in SmallInteger range")
    return value


def _validate_float(value: float, field_name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{field_name} must be a float")
    return float(value)


class CustomUserManager:
    def create_user(self, email: str, password: Union[bytes, str]) -> "CustomUser":
        return CustomUser(email=email, password=password)

    def create_superuser(self, email: str, password: Union[bytes, str]) -> "CustomUser":
        user = CustomUser(email=email, password=password)
        user.is_superuser = True
        user.is_staff = True
        return user


class CustomUser:
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    REQUIRED_FIELDS: ClassVar[List[str]] = ["email"]
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
        gender: str = "Other",
        profile_pic: str = "",
        user_type: str = "3",
        username: None = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.username: None = username
        self.email: str = _validate_email(email)
        self.password: Union[bytes, str] = password
        self.address: str = address
        self.fcm_token: str = fcm_token
        self.gender: str = _validate_choice(gender, self.GENDER, "gender")
        self.user_type: str = _validate_user_type(user_type, self.USER_TYPE)
        self.profile_pic: str = profile_pic
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

        self.is_superuser: bool = False
        self.is_staff: bool = False

    def touch(self) -> None:
        self.updated_at = _now()


class Admin:
    def __init__(self, admin: CustomUser):
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        self.admin: CustomUser = admin


class Course:
    def __init__(
        self,
        name: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.name: str = _require_non_empty(name, "name")
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class Session:
    def __init__(self, start_year: date, end_year: date):
        if not isinstance(start_year, date) or not isinstance(end_year, date):
            raise ValidationError("start_year and end_year must be date instances")
        self.start_year: date = start_year
        self.end_year: date = end_year


class Staff:
    def __init__(self, admin: CustomUser, course: Course):
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        self.admin: CustomUser = admin
        self.course: Course = course


class Student:
    def __init__(self, admin: CustomUser, course: Course, session: Session):
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        self.admin: CustomUser = admin
        self.course: Course = course
        self.session: Session = session


class Subject:
    def __init__(
        self,
        name: str,
        course: Course,
        staff: Staff,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.name: str = _require_non_empty(name, "name")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.course: Course = course
        self.staff: Staff = staff
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class Attendance:
    def __init__(
        self,
        date_value: date,
        session: Session,
        subject: Subject,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(date_value, date):
            raise ValidationError("date must be a date instance")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        self.date: date = date_value
        self.session: Session = session
        self.subject: Subject = subject
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class AttendanceReport:
    def __init__(
        self,
        student: Student,
        attendance: Attendance,
        status: bool,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        if not isinstance(status, bool):
            raise ValidationError("status must be a bool")
        self.student: Student = student
        self.attendance: Attendance = attendance
        self.status: bool = status
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class FeedbackStaff:
    def __init__(
        self,
        staff: Staff,
        feedback: str,
        reply: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.staff: Staff = staff
        self.feedback: str = _require_non_empty(feedback, "feedback")
        self.reply: str = reply
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class FeedbackStudent:
    def __init__(
        self,
        student: Student,
        feedback: str,
        reply: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        self.student: Student = student
        self.feedback: str = _require_non_empty(feedback, "feedback")
        self.reply: str = reply
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class LeaveReportStaff:
    def __init__(
        self,
        staff: Staff,
        date_value: str,
        message: str,
        status: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.staff: Staff = staff
        self.date: str = _require_non_empty(date_value, "date")
        self.message: str = _require_non_empty(message, "message")
        self.status: int = _validate_small_int(status, "status")
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class LeaveReportStudent:
    def __init__(
        self,
        student: Student,
        date_value: str,
        message: str,
        status: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        self.student: Student = student
        self.date: str = _require_non_empty(date_value, "date")
        self.message: str = _require_non_empty(message, "message")
        self.status: int = _validate_small_int(status, "status")
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class NotificationStaff:
    def __init__(
        self,
        staff: Staff,
        message: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.staff: Staff = staff
        self.message: str = _require_non_empty(message, "message")
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class NotificationStudent:
    def __init__(
        self,
        student: Student,
        message: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        self.student: Student = student
        self.message: str = _require_non_empty(message, "message")
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()


class StudentResult:
    def __init__(
        self,
        student: Student,
        subject: Subject,
        test: float,
        exam: float,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        self.student: Student = student
        self.subject: Subject = subject
        self.test: float = _validate_float(test, "test")
        self.exam: float = _validate_float(exam, "exam")
        self.created_at: datetime = created_at or _now()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = _now()