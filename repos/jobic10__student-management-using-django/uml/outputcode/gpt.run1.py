from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, TypeVar, Union


T = TypeVar("T", bound="BaseModel")


class ValidationError(ValueError):
    pass


class BaseModel:
    id: int
    created_at: datetime
    updated_at: datetime

    _id_counter: ClassVar[int] = 1

    def __init__(self) -> None:
        self.id = self.__class__._id_counter
        self.__class__._id_counter += 1
        now = datetime.now()
        self.created_at = now
        self.updated_at = now

    def touch(self) -> None:
        self.updated_at = datetime.now()


class CustomUserManager:
    def __init__(self) -> None:
        self._users_by_email: Dict[str, CustomUser] = {}

    def create_user(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        if not email or not isinstance(email, str):
            raise ValidationError("email is required")
        normalized = email.strip().lower()
        if not normalized:
            raise ValidationError("email is required")
        if normalized in self._users_by_email:
            raise ValidationError("email already exists")
        user = CustomUser(email=normalized, password=password)
        self._users_by_email[normalized] = user
        return user

    def create_superuser(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.is_superuser = True
        user.is_staff = True
        user.touch()
        return user


class CustomUser(BaseModel):
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (
        ("1", "Admin"),
        ("2", "Staff"),
        ("3", "Student"),
    )
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = []

    objects: ClassVar[CustomUserManager] = CustomUserManager()

    def __init__(
        self,
        email: str,
        password: Union[str, bytes],
        address: str = "",
        fcm_token: str = "",
        gender: str = "Other",
        profile_pic: str = "",
        user_type: str = "1",
        username: Optional[None] = None,
    ) -> None:
        super().__init__()
        if not email or not isinstance(email, str):
            raise ValidationError("email is required")
        email_norm = email.strip().lower()
        if not email_norm:
            raise ValidationError("email is required")
        if gender not in self.GENDER:
            raise ValidationError("invalid gender")
        if user_type not in {ut[0] for ut in self.USER_TYPE}:
            raise ValidationError("invalid user_type")

        self.email: str = email_norm
        self.password: Union[str, bytes] = password
        self.address: str = address
        self.fcm_token: str = fcm_token
        self.gender: str = gender
        self.profile_pic: str = profile_pic
        self.user_type: str = user_type
        self.username: Optional[None] = username

        self.is_superuser: bool = False
        self.is_staff: bool = False

        self._admin_profile: Optional[Admin] = None
        self._staff_profile: Optional[Staff] = None
        self._student_profile: Optional[Student] = None

    @property
    def admin_profile(self) -> Optional["Admin"]:
        return self._admin_profile

    @property
    def staff_profile(self) -> Optional["Staff"]:
        return self._staff_profile

    @property
    def student_profile(self) -> Optional["Student"]:
        return self._student_profile

    def _set_admin_profile(self, profile: Optional["Admin"]) -> None:
        self._admin_profile = profile
        self.touch()

    def _set_staff_profile(self, profile: Optional["Staff"]) -> None:
        self._staff_profile = profile
        self.touch()

    def _set_student_profile(self, profile: Optional["Student"]) -> None:
        self._student_profile = profile
        self.touch()


class Admin(BaseModel):
    def __init__(self, admin: CustomUser) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if admin.admin_profile is not None:
            raise ValidationError("CustomUser already has an Admin profile")
        self.admin: CustomUser = admin
        admin._set_admin_profile(self)


class Course(BaseModel):
    def __init__(self, name: str) -> None:
        super().__init__()
        if not name or not isinstance(name, str):
            raise ValidationError("name is required")
        self.name: str = name


class Session(BaseModel):
    def __init__(self, start_year: date, end_year: date) -> None:
        super().__init__()
        if not isinstance(start_year, date) or not isinstance(end_year, date):
            raise ValidationError("start_year and end_year must be date")
        self.start_year: date = start_year
        self.end_year: date = end_year


class Staff(BaseModel):
    def __init__(self, admin: CustomUser, course: Course) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if admin.staff_profile is not None:
            raise ValidationError("CustomUser already has a Staff profile")
        self.admin: CustomUser = admin
        self.course: Course = course
        admin._set_staff_profile(self)


class Student(BaseModel):
    def __init__(self, admin: CustomUser, course: Course, session: Session) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        if admin.student_profile is not None:
            raise ValidationError("CustomUser already has a Student profile")
        self.admin: CustomUser = admin
        self.course: Course = course
        self.session: Session = session
        admin._set_student_profile(self)


class Subject(BaseModel):
    def __init__(self, name: str, course: Course, staff: Staff) -> None:
        super().__init__()
        if not name or not isinstance(name, str):
            raise ValidationError("name is required")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.name: str = name
        self.course: Course = course
        self.staff: Staff = staff


class Attendance(BaseModel):
    def __init__(self, date_value: date, session: Session, subject: Subject) -> None:
        super().__init__()
        if not isinstance(date_value, date):
            raise ValidationError("date must be a date")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        self.date: date = date_value
        self.session: Session = session
        self.subject: Subject = subject


class AttendanceReport(BaseModel):
    def __init__(self, attendance: Attendance, student: Student, status: bool) -> None:
        super().__init__()
        if not isinstance(attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(status, bool):
            raise ValidationError("status must be a bool")
        self.attendance: Attendance = attendance
        self.student: Student = student
        self.status: bool = status


class FeedbackStaff(BaseModel):
    def __init__(self, staff: Staff, feedback: str, reply: str = "") -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(feedback, str):
            raise ValidationError("feedback must be a string")
        if not isinstance(reply, str):
            raise ValidationError("reply must be a string")
        self.staff: Staff = staff
        self.feedback: str = feedback
        self.reply: str = reply


class FeedbackStudent(BaseModel):
    def __init__(self, student: Student, feedback: str, reply: str = "") -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(feedback, str):
            raise ValidationError("feedback must be a string")
        if not isinstance(reply, str):
            raise ValidationError("reply must be a string")
        self.student: Student = student
        self.feedback: str = feedback
        self.reply: str = reply


class LeaveReportStaff(BaseModel):
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
        if status < -32768 or status > 32767:
            raise ValidationError("status out of SmallInteger range")
        self.staff: Staff = staff
        self.date: str = date_value
        self.message: str = message
        self.status: int = status


class LeaveReportStudent(BaseModel):
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
        if status < -32768 or status > 32767:
            raise ValidationError("status out of SmallInteger range")
        self.student: Student = student
        self.date: str = date_value
        self.message: str = message
        self.status: int = status


class NotificationStaff(BaseModel):
    def __init__(self, staff: Staff, message: str) -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        self.staff: Staff = staff
        self.message: str = message


class NotificationStudent(BaseModel):
    def __init__(self, student: Student, message: str) -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        self.student: Student = student
        self.message: str = message


class StudentResult(BaseModel):
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
        self.student: Student = student
        self.subject: Subject = subject
        self.test: float = float(test)
        self.exam: float = float(exam)