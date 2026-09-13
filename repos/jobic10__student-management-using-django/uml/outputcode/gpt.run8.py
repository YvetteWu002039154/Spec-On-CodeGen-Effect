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
        now = datetime.utcnow()
        self.created_at = now
        self.updated_at = now

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class OneToOneRegistry:
    def __init__(self) -> None:
        self._forward: Dict[Tuple[Type[Any], int, str], BaseModel] = {}
        self._reverse: Dict[Tuple[Type[Any], int, str], BaseModel] = {}

    def set(
        self,
        owner: BaseModel,
        attr_name: str,
        target: BaseModel,
        reverse_attr_name: str,
    ) -> None:
        owner_key = (type(owner), owner.id, attr_name)
        target_key = (type(target), target.id, reverse_attr_name)

        existing_target = self._forward.get(owner_key)
        if existing_target is not None and existing_target is not target:
            raise ValidationError(f"{type(owner).__name__}.{attr_name} already set")

        existing_owner = self._reverse.get(target_key)
        if existing_owner is not None and existing_owner is not owner:
            raise ValidationError(f"{type(target).__name__}.{reverse_attr_name} already linked")

        self._forward[owner_key] = target
        self._reverse[target_key] = owner

    def get_forward(self, owner: BaseModel, attr_name: str) -> Optional[BaseModel]:
        return self._forward.get((type(owner), owner.id, attr_name))

    def get_reverse(self, target: BaseModel, reverse_attr_name: str) -> Optional[BaseModel]:
        return self._reverse.get((type(target), target.id, reverse_attr_name))


_one_to_one_registry = OneToOneRegistry()


class CustomUserManager:
    def create_user(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        if not email or not isinstance(email, str):
            raise ValidationError("email is required")
        if password is None or (isinstance(password, (str, bytes)) and len(password) == 0):
            raise ValidationError("password is required")
        user = CustomUser(email=email, password=password)
        return user

    def create_superuser(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.user_type = "ADMIN"
        user.touch()
        return user


class CustomUser(BaseModel):
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (
        ("ADMIN", "Admin"),
        ("STAFF", "Staff"),
        ("STUDENT", "Student"),
    )
    REQUIRED_FIELDS: ClassVar[List[str]] = ["password"]
    USERNAME_FIELD: ClassVar[str] = "email"

    objects: ClassVar[CustomUserManager] = CustomUserManager()

    def __init__(
        self,
        email: str,
        password: Union[bytes, str],
        address: str = "",
        fcm_token: str = "",
        gender: str = "Other",
        profile_pic: Optional[str] = None,
        user_type: str = "STUDENT",
        username: None = None,
    ) -> None:
        super().__init__()
        if not email or not isinstance(email, str):
            raise ValidationError("email must be a non-empty string")
        if gender not in self.GENDER:
            raise ValidationError("invalid gender")
        if user_type not in {k for k, _ in self.USER_TYPE}:
            raise ValidationError("invalid user_type")
        if username is not None:
            raise ValidationError("username must be NoneType")

        self.email: str = email
        self.password: Union[bytes, str] = password
        self.address: str = address
        self.fcm_token: str = fcm_token
        self.gender: str = gender
        self.profile_pic: Optional[str] = profile_pic
        self.user_type: str = user_type
        self.username: None = None

    @property
    def admin_profile(self) -> Optional["Admin"]:
        obj = _one_to_one_registry.get_reverse(self, "admin")
        return obj if isinstance(obj, Admin) else None

    @property
    def staff_profile(self) -> Optional["Staff"]:
        obj = _one_to_one_registry.get_reverse(self, "admin")
        return obj if isinstance(obj, Staff) else None

    @property
    def student_profile(self) -> Optional["Student"]:
        obj = _one_to_one_registry.get_reverse(self, "admin")
        return obj if isinstance(obj, Student) else None


class Course(BaseModel):
    def __init__(self, name: str) -> None:
        super().__init__()
        if not name or not isinstance(name, str):
            raise ValidationError("name must be a non-empty string")
        self.name: str = name


class Session(BaseModel):
    def __init__(self, start_year: date, end_year: date) -> None:
        super().__init__()
        if not isinstance(start_year, date) or not isinstance(end_year, date):
            raise ValidationError("start_year and end_year must be date")
        if end_year < start_year:
            raise ValidationError("end_year must be >= start_year")
        self.start_year: date = start_year
        self.end_year: date = end_year


class Admin(BaseModel):
    def __init__(self, admin: CustomUser) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        _one_to_one_registry.set(self, "admin", admin, "admin")
        self.touch()

    @property
    def admin(self) -> CustomUser:
        obj = _one_to_one_registry.get_forward(self, "admin")
        if not isinstance(obj, CustomUser):
            raise ValidationError("Admin.admin not set")
        return obj


class Staff(BaseModel):
    def __init__(self, admin: CustomUser, course: Course) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        _one_to_one_registry.set(self, "admin", admin, "admin")
        self.course: Course = course
        self.touch()

    @property
    def admin(self) -> CustomUser:
        obj = _one_to_one_registry.get_forward(self, "admin")
        if not isinstance(obj, CustomUser):
            raise ValidationError("Staff.admin not set")
        return obj


class Student(BaseModel):
    def __init__(self, admin: CustomUser, course: Course, session: Session) -> None:
        super().__init__()
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        _one_to_one_registry.set(self, "admin", admin, "admin")
        self.course: Course = course
        self.session: Session = session
        self.touch()

    @property
    def admin(self) -> CustomUser:
        obj = _one_to_one_registry.get_forward(self, "admin")
        if not isinstance(obj, CustomUser):
            raise ValidationError("Student.admin not set")
        return obj


class Subject(BaseModel):
    def __init__(self, name: str, course: Course, staff: Staff) -> None:
        super().__init__()
        if not name or not isinstance(name, str):
            raise ValidationError("name must be a non-empty string")
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
            raise ValidationError("status out of SmallIntegerField range")
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
            raise ValidationError("status out of SmallIntegerField range")
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
            raise ValidationError("test must be a float")
        if not isinstance(exam, (int, float)):
            raise ValidationError("exam must be a float")
        self.student: Student = student
        self.subject: Subject = subject
        self.test: float = float(test)
        self.exam: float = float(exam)