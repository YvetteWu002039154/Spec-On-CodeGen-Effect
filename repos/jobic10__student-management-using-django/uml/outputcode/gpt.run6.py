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
    def create_user(self, email: str, password: Union[bytes, str]) -> "CustomUser":
        if email is None or str(email).strip() == "":
            raise ValidationError("Email is required")
        if password is None or (isinstance(password, str) and password == "") or (isinstance(password, (bytes, bytearray)) and len(password) == 0):
            raise ValidationError("Password is required")
        user = CustomUser(email=email, password=password)
        return user

    def create_superuser(self, email: str, password: Union[bytes, str]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.user_type = "1"
        return user


class CustomUser:
    GENDER: ClassVar[List[str]] = ["Male", "Female"]
    REQUIRED_FIELDS: ClassVar[List[str]] = []
    USERNAME_FIELD: ClassVar[str] = "email"
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (("1", "Admin"), ("2", "Staff"), ("3", "Student"))

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
    ):
        if email is None or str(email).strip() == "":
            raise ValidationError("email is required")
        self.email: str = str(email).strip()

        if password is None or (isinstance(password, str) and password == "") or (isinstance(password, (bytes, bytearray)) and len(password) == 0):
            raise ValidationError("password is required")
        self.password: Union[bytes, str] = password

        self.address: str = str(address)
        self.fcm_token: str = str(fcm_token)
        self.gender: str = str(gender)
        self.profile_pic: str = str(profile_pic)
        self.user_type: str = str(user_type)
        self.username: Optional[None] = username

        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

        self._admin_profile: Optional[Admin] = None
        self._staff_profile: Optional[Staff] = None
        self._student_profile: Optional[Student] = None

    def touch(self) -> None:
        self.updated_at = datetime.now()

    @property
    def admin_profile(self) -> Optional["Admin"]:
        return self._admin_profile

    @property
    def staff_profile(self) -> Optional["Staff"]:
        return self._staff_profile

    @property
    def student_profile(self) -> Optional["Student"]:
        return self._student_profile


class Admin:
    def __init__(self, admin: CustomUser):
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        self.admin: CustomUser = admin
        if admin._admin_profile is not None and admin._admin_profile is not self:
            raise ValidationError("CustomUser already has an Admin profile")
        admin._admin_profile = self
        admin.touch()


class Course:
    def __init__(
        self,
        name: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if name is None or str(name).strip() == "":
            raise ValidationError("name is required")
        self.name: str = str(name).strip()
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


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
        if admin._staff_profile is not None and admin._staff_profile is not self:
            raise ValidationError("CustomUser already has a Staff profile")
        admin._staff_profile = self
        admin.touch()


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
        if admin._student_profile is not None and admin._student_profile is not self:
            raise ValidationError("CustomUser already has a Student profile")
        admin._student_profile = self
        admin.touch()


class Subject:
    def __init__(
        self,
        name: str,
        course: Course,
        staff: Staff,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if name is None or str(name).strip() == "":
            raise ValidationError("name is required")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.name: str = str(name).strip()
        self.course: Course = course
        self.staff: Staff = staff
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


class Attendance:
    def __init__(
        self,
        date: date,
        session: Session,
        subject: Subject,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(date, date):
            raise ValidationError("date must be a date instance")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        self.date: date = date
        self.session: Session = session
        self.subject: Subject = subject
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


class AttendanceReport:
    def __init__(
        self,
        attendance: Attendance,
        student: Student,
        status: bool,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        self.attendance: Attendance = attendance
        self.student: Student = student
        self.status: bool = bool(status)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


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
        if feedback is None:
            raise ValidationError("feedback is required")
        self.staff: Staff = staff
        self.feedback: str = str(feedback)
        self.reply: str = str(reply)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


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
        if feedback is None:
            raise ValidationError("feedback is required")
        self.student: Student = student
        self.feedback: str = str(feedback)
        self.reply: str = str(reply)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


class LeaveReportStaff:
    def __init__(
        self,
        staff: Staff,
        date: str,
        message: str,
        status: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if date is None:
            raise ValidationError("date is required")
        if message is None:
            raise ValidationError("message is required")
        self.staff: Staff = staff
        self.date: str = str(date)
        self.message: str = str(message)
        self.status: int = int(status)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


class LeaveReportStudent:
    def __init__(
        self,
        student: Student,
        date: str,
        message: str,
        status: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if date is None:
            raise ValidationError("date is required")
        if message is None:
            raise ValidationError("message is required")
        self.student: Student = student
        self.date: str = str(date)
        self.message: str = str(message)
        self.status: int = int(status)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


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
        if message is None:
            raise ValidationError("message is required")
        self.staff: Staff = staff
        self.message: str = str(message)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


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
        if message is None:
            raise ValidationError("message is required")
        self.student: Student = student
        self.message: str = str(message)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()


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
        self.test: float = float(test)
        self.exam: float = float(exam)
        self.created_at: datetime = created_at if created_at is not None else datetime.now()
        self.updated_at: datetime = updated_at if updated_at is not None else self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now()