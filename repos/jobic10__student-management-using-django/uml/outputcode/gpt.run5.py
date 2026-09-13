from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, TypeVar, Union


T = TypeVar("T")


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
    def __init__(self, value: bool = False):
        self.value = value


class SmallIntegerField:
    def __init__(self, value: int = 0):
        self.value = value


class FloatField:
    def __init__(self, value: float = 0.0):
        self.value = value


def _now() -> datetime:
    return datetime.now()


def _validate_email(email: str) -> None:
    if not isinstance(email, str) or not email.strip():
        raise ValidationError("Email is required.")
    if "@" not in email or email.count("@") != 1:
        raise ValidationError("Invalid email format.")
    local, domain = email.split("@", 1)
    if not local or not domain or "." not in domain:
        raise ValidationError("Invalid email format.")


def _hash_password(password: Union[str, bytes]) -> bytes:
    if isinstance(password, str):
        password_bytes = password.encode("utf-8")
    elif isinstance(password, (bytes, bytearray)):
        password_bytes = bytes(password)
    else:
        raise ValidationError("Password must be str or bytes.")
    if len(password_bytes) == 0:
        raise ValidationError("Password cannot be empty.")
    return password_bytes


@dataclass
class CustomUser:
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (("1", "Admin"), ("2", "Staff"), ("3", "Student"))
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = []

    email: str
    password: Union[bytes, str]
    user_type: str

    address: str = ""
    gender: str = "Other"
    profile_pic: Optional[str] = None
    fcm_token: str = ""
    username: None = None

    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    objects: ClassVar["CustomUserManager"]

    def __post_init__(self) -> None:
        _validate_email(self.email)
        self.password = _hash_password(self.password)
        if self.user_type not in {k for k, _ in self.USER_TYPE}:
            raise ValidationError("Invalid user_type.")
        if self.gender not in self.GENDER:
            raise ValidationError("Invalid gender.")

    def set_password(self, password: Union[str, bytes]) -> None:
        self.password = _hash_password(password)
        self.updated_at = _now()

    def check_password(self, password: Union[str, bytes]) -> bool:
        try:
            return self.password == _hash_password(password)
        except ValidationError:
            return False


class CustomUserManager:
    def __init__(self) -> None:
        self._users_by_email: Dict[str, CustomUser] = {}

    def create_user(self, email: str, password: Union[str, bytes]) -> CustomUser:
        _validate_email(email)
        key = email.strip().lower()
        if key in self._users_by_email:
            raise ValidationError("A user with this email already exists.")
        user = CustomUser(email=key, password=password, user_type="3")
        self._users_by_email[key] = user
        return user

    def create_superuser(self, email: str, password: Union[str, bytes]) -> CustomUser:
        _validate_email(email)
        key = email.strip().lower()
        if key in self._users_by_email:
            raise ValidationError("A user with this email already exists.")
        user = CustomUser(email=key, password=password, user_type="1")
        self._users_by_email[key] = user
        return user

    def get_by_email(self, email: str) -> Optional[CustomUser]:
        if not isinstance(email, str):
            return None
        return self._users_by_email.get(email.strip().lower())


CustomUser.objects = CustomUserManager()


@dataclass
class Course:
    name: str
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Course name is required.")


@dataclass
class Session:
    start_year: date
    end_year: date

    def __post_init__(self) -> None:
        if not isinstance(self.start_year, date) or not isinstance(self.end_year, date):
            raise ValidationError("start_year and end_year must be date.")
        if self.end_year < self.start_year:
            raise ValidationError("end_year cannot be before start_year.")


@dataclass
class Admin:
    admin: CustomUser

    def __post_init__(self) -> None:
        if not isinstance(self.admin, CustomUser):
            raise ValidationError("admin must be a CustomUser.")
        if self.admin.user_type != "1":
            raise ValidationError("CustomUser user_type must be Admin ('1').")


@dataclass
class Staff:
    admin: CustomUser
    course: Course

    def __post_init__(self) -> None:
        if not isinstance(self.admin, CustomUser):
            raise ValidationError("admin must be a CustomUser.")
        if self.admin.user_type != "2":
            raise ValidationError("CustomUser user_type must be Staff ('2').")
        if not isinstance(self.course, Course):
            raise ValidationError("course must be a Course.")


@dataclass
class Student:
    admin: CustomUser
    course: Course
    session: Session

    def __post_init__(self) -> None:
        if not isinstance(self.admin, CustomUser):
            raise ValidationError("admin must be a CustomUser.")
        if self.admin.user_type != "3":
            raise ValidationError("CustomUser user_type must be Student ('3').")
        if not isinstance(self.course, Course):
            raise ValidationError("course must be a Course.")
        if not isinstance(self.session, Session):
            raise ValidationError("session must be a Session.")


@dataclass
class Subject:
    course: Course
    name: str
    staff: Staff
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.course, Course):
            raise ValidationError("course must be a Course.")
        if not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Subject name is required.")
        if self.staff.course is not self.course:
            raise ValidationError("Subject course must match staff course.")


@dataclass
class Attendance:
    date: date
    session: Session
    subject: Subject
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.date, date):
            raise ValidationError("date must be a date.")
        if not isinstance(self.session, Session):
            raise ValidationError("session must be a Session.")
        if not isinstance(self.subject, Subject):
            raise ValidationError("subject must be a Subject.")


@dataclass
class AttendanceReport:
    attendance: Attendance
    student: Student
    status: bool
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.attendance, Attendance):
            raise ValidationError("attendance must be an Attendance.")
        if not isinstance(self.student, Student):
            raise ValidationError("student must be a Student.")
        if not isinstance(self.status, bool):
            raise ValidationError("status must be a bool.")
        if self.student.session is not self.attendance.session:
            raise ValidationError("Student session must match attendance session.")
        if self.student.course is not self.attendance.subject.course:
            raise ValidationError("Student course must match attendance subject course.")


@dataclass
class FeedbackStaff:
    staff: Staff
    feedback: str
    reply: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff.")
        if not isinstance(self.feedback, str) or not self.feedback.strip():
            raise ValidationError("feedback is required.")
        if not isinstance(self.reply, str):
            raise ValidationError("reply must be a string.")


@dataclass
class FeedbackStudent:
    student: Student
    feedback: str
    reply: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.student, Student):
            raise ValidationError("student must be a Student.")
        if not isinstance(self.feedback, str) or not self.feedback.strip():
            raise ValidationError("feedback is required.")
        if not isinstance(self.reply, str):
            raise ValidationError("reply must be a string.")


@dataclass
class LeaveReportStaff:
    staff: Staff
    date: str
    message: str
    status: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff.")
        if not isinstance(self.date, str) or not self.date.strip():
            raise ValidationError("date is required.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValidationError("message is required.")
        if not isinstance(self.status, int):
            raise ValidationError("status must be an int.")


@dataclass
class LeaveReportStudent:
    student: Student
    date: str
    message: str
    status: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.student, Student):
            raise ValidationError("student must be a Student.")
        if not isinstance(self.date, str) or not self.date.strip():
            raise ValidationError("date is required.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValidationError("message is required.")
        if not isinstance(self.status, int):
            raise ValidationError("status must be an int.")


@dataclass
class NotificationStaff:
    staff: Staff
    message: str
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.staff, Staff):
            raise ValidationError("staff must be a Staff.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValidationError("message is required.")


@dataclass
class NotificationStudent:
    student: Student
    message: str
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.student, Student):
            raise ValidationError("student must be a Student.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValidationError("message is required.")


@dataclass
class StudentResult:
    student: Student
    subject: Subject
    test: float
    exam: float
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.student, Student):
            raise ValidationError("student must be a Student.")
        if not isinstance(self.subject, Subject):
            raise ValidationError("subject must be a Subject.")
        if not isinstance(self.test, (int, float)):
            raise ValidationError("test must be a number.")
        if not isinstance(self.exam, (int, float)):
            raise ValidationError("exam must be a number.")
        self.test = float(self.test)
        self.exam = float(self.exam)
        if self.student.course is not self.subject.course:
            raise ValidationError("Student course must match subject course.")