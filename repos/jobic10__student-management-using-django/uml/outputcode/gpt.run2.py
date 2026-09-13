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


class CustomUser(BaseModel):
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (
        ("1", "Admin"),
        ("2", "Staff"),
        ("3", "Student"),
    )
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = []

    objects: ClassVar["CustomUserManager"]

    def __init__(
        self,
        email: str,
        password: Union[str, bytes],
        user_type: str,
        address: str = "",
        gender: str = "Other",
        profile_pic: str = "",
        fcm_token: str = "",
        username: Optional[None] = None,
    ) -> None:
        super().__init__()
        self.username: Optional[None] = username
        self.email: str = self._validate_email(email)
        self.password: Union[str, bytes] = self._validate_password(password)
        self.user_type: str = self._validate_user_type(user_type)
        self.address: str = address
        self.gender: str = self._validate_gender(gender)
        self.profile_pic: str = profile_pic
        self.fcm_token: str = fcm_token

    @staticmethod
    def _validate_email(email: str) -> str:
        if not isinstance(email, str) or not email.strip():
            raise ValidationError("email must be a non-empty string")
        email = email.strip()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValidationError("email must contain '@' and be a valid format")
        return email.lower()

    @staticmethod
    def _validate_password(password: Union[str, bytes]) -> Union[str, bytes]:
        if isinstance(password, bytes):
            if len(password) == 0:
                raise ValidationError("password must not be empty")
            return password
        if isinstance(password, str):
            if not password:
                raise ValidationError("password must not be empty")
            return password
        raise ValidationError("password must be str or bytes")

    @classmethod
    def _validate_user_type(cls, user_type: str) -> str:
        valid = {k for k, _ in cls.USER_TYPE}
        if user_type not in valid:
            raise ValidationError(f"user_type must be one of {sorted(valid)}")
        return user_type

    @classmethod
    def _validate_gender(cls, gender: str) -> str:
        if gender not in cls.GENDER:
            raise ValidationError(f"gender must be one of {cls.GENDER}")
        return gender


class CustomUserManager:
    def __init__(self) -> None:
        self._users_by_email: Dict[str, CustomUser] = {}

    def create_user(self, email: str, password: Union[str, bytes]) -> CustomUser:
        email_norm = CustomUser._validate_email(email)
        if email_norm in self._users_by_email:
            raise ValidationError("A user with this email already exists")
        user = CustomUser(email=email_norm, password=password, user_type="3")
        self._users_by_email[email_norm] = user
        return user

    def create_superuser(self, email: str, password: Union[str, bytes]) -> CustomUser:
        email_norm = CustomUser._validate_email(email)
        if email_norm in self._users_by_email:
            raise ValidationError("A user with this email already exists")
        user = CustomUser(email=email_norm, password=password, user_type="1")
        self._users_by_email[email_norm] = user
        return user

    def get_by_email(self, email: str) -> Optional[CustomUser]:
        try:
            email_norm = CustomUser._validate_email(email)
        except ValidationError:
            return None
        return self._users_by_email.get(email_norm)


CustomUser.objects = CustomUserManager()


class Admin(BaseModel):
    def __init__(self, admin: CustomUser) -> None:
        super().__init__()
        self.admin: CustomUser = self._validate_admin_user(admin)

    @staticmethod
    def _validate_admin_user(user: CustomUser) -> CustomUser:
        if not isinstance(user, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if user.user_type != "1":
            raise ValidationError("CustomUser must have user_type '1' for Admin")
        return user


class Course(BaseModel):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = self._validate_name(name)

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        return name.strip()


class Session(BaseModel):
    def __init__(self, start_year: date, end_year: date) -> None:
        super().__init__()
        self.start_year: date = self._validate_date(start_year, "start_year")
        self.end_year: date = self._validate_date(end_year, "end_year")

    @staticmethod
    def _validate_date(value: date, field_name: str) -> date:
        if not isinstance(value, date):
            raise ValidationError(f"{field_name} must be a date")
        return value


class Staff(BaseModel):
    def __init__(self, admin: CustomUser, course: Course) -> None:
        super().__init__()
        self.admin: CustomUser = self._validate_staff_user(admin)
        self.course: Course = self._validate_course(course)

    @staticmethod
    def _validate_staff_user(user: CustomUser) -> CustomUser:
        if not isinstance(user, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if user.user_type != "2":
            raise ValidationError("CustomUser must have user_type '2' for Staff")
        return user

    @staticmethod
    def _validate_course(course: Course) -> Course:
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        return course


class Student(BaseModel):
    def __init__(self, admin: CustomUser, course: Course, session: Session) -> None:
        super().__init__()
        self.admin: CustomUser = self._validate_student_user(admin)
        self.course: Course = self._validate_course(course)
        self.session: Session = self._validate_session(session)

    @staticmethod
    def _validate_student_user(user: CustomUser) -> CustomUser:
        if not isinstance(user, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if user.user_type != "3":
            raise ValidationError("CustomUser must have user_type '3' for Student")
        return user

    @staticmethod
    def _validate_course(course: Course) -> Course:
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        return course

    @staticmethod
    def _validate_session(session: Session) -> Session:
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        return session


class Subject(BaseModel):
    def __init__(self, name: str, course: Course, staff: Staff) -> None:
        super().__init__()
        self.name: str = self._validate_name(name)
        self.course: Course = self._validate_course(course)
        self.staff: Staff = self._validate_staff(staff)

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        return name.strip()

    @staticmethod
    def _validate_course(course: Course) -> Course:
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        return course

    @staticmethod
    def _validate_staff(staff: Staff) -> Staff:
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        return staff


class Attendance(BaseModel):
    def __init__(self, date_value: date, session: Session, subject: Subject) -> None:
        super().__init__()
        self.date: date = self._validate_date(date_value)
        self.session: Session = self._validate_session(session)
        self.subject: Subject = self._validate_subject(subject)

    @staticmethod
    def _validate_date(value: date) -> date:
        if not isinstance(value, date):
            raise ValidationError("date must be a date")
        return value

    @staticmethod
    def _validate_session(session: Session) -> Session:
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        return session

    @staticmethod
    def _validate_subject(subject: Subject) -> Subject:
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        return subject


class AttendanceReport(BaseModel):
    def __init__(self, student: Student, attendance: Attendance, status: bool) -> None:
        super().__init__()
        self.student: Student = self._validate_student(student)
        self.attendance: Attendance = self._validate_attendance(attendance)
        self.status: bool = self._validate_status(status)

    @staticmethod
    def _validate_student(student: Student) -> Student:
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        return student

    @staticmethod
    def _validate_attendance(attendance: Attendance) -> Attendance:
        if not isinstance(attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        return attendance

    @staticmethod
    def _validate_status(status: bool) -> bool:
        if not isinstance(status, bool):
            raise ValidationError("status must be a bool")
        return status


class FeedbackStaff(BaseModel):
    def __init__(self, staff: Staff, feedback: str, reply: str = "") -> None:
        super().__init__()
        self.staff: Staff = self._validate_staff(staff)
        self.feedback: str = self._validate_text(feedback, "feedback")
        self.reply: str = self._validate_text(reply, "reply", allow_empty=True)

    @staticmethod
    def _validate_staff(staff: Staff) -> Staff:
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        return staff

    @staticmethod
    def _validate_text(value: str, field_name: str, allow_empty: bool = False) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        if not allow_empty and not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string")
        return value


class FeedbackStudent(BaseModel):
    def __init__(self, student: Student, feedback: str, reply: str = "") -> None:
        super().__init__()
        self.student: Student = self._validate_student(student)
        self.feedback: str = self._validate_text(feedback, "feedback")
        self.reply: str = self._validate_text(reply, "reply", allow_empty=True)

    @staticmethod
    def _validate_student(student: Student) -> Student:
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        return student

    @staticmethod
    def _validate_text(value: str, field_name: str, allow_empty: bool = False) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        if not allow_empty and not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string")
        return value


class LeaveReportStaff(BaseModel):
    def __init__(self, staff: Staff, date_value: str, message: str, status: int = 0) -> None:
        super().__init__()
        self.staff: Staff = self._validate_staff(staff)
        self.date: str = self._validate_text(date_value, "date")
        self.message: str = self._validate_text(message, "message")
        self.status: int = self._validate_status(status)

    @staticmethod
    def _validate_staff(staff: Staff) -> Staff:
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        return staff

    @staticmethod
    def _validate_text(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string")
        return value

    @staticmethod
    def _validate_status(status: int) -> int:
        if not isinstance(status, int):
            raise ValidationError("status must be an int")
        if status < -32768 or status > 32767:
            raise ValidationError("status must fit in SmallInteger range")
        return status


class LeaveReportStudent(BaseModel):
    def __init__(self, student: Student, date_value: str, message: str, status: int = 0) -> None:
        super().__init__()
        self.student: Student = self._validate_student(student)
        self.date: str = self._validate_text(date_value, "date")
        self.message: str = self._validate_text(message, "message")
        self.status: int = self._validate_status(status)

    @staticmethod
    def _validate_student(student: Student) -> Student:
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        return student

    @staticmethod
    def _validate_text(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string")
        return value

    @staticmethod
    def _validate_status(status: int) -> int:
        if not isinstance(status, int):
            raise ValidationError("status must be an int")
        if status < -32768 or status > 32767:
            raise ValidationError("status must fit in SmallInteger range")
        return status


class NotificationStaff(BaseModel):
    def __init__(self, staff: Staff, message: str) -> None:
        super().__init__()
        self.staff: Staff = self._validate_staff(staff)
        self.message: str = self._validate_message(message)

    @staticmethod
    def _validate_staff(staff: Staff) -> Staff:
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        return staff

    @staticmethod
    def _validate_message(message: str) -> str:
        if not isinstance(message, str) or not message.strip():
            raise ValidationError("message must be a non-empty string")
        return message


class NotificationStudent(BaseModel):
    def __init__(self, student: Student, message: str) -> None:
        super().__init__()
        self.student: Student = self._validate_student(student)
        self.message: str = self._validate_message(message)

    @staticmethod
    def _validate_student(student: Student) -> Student:
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        return student

    @staticmethod
    def _validate_message(message: str) -> str:
        if not isinstance(message, str) or not message.strip():
            raise ValidationError("message must be a non-empty string")
        return message


class StudentResult(BaseModel):
    def __init__(self, student: Student, subject: Subject, test: float, exam: float) -> None:
        super().__init__()
        self.student: Student = self._validate_student(student)
        self.subject: Subject = self._validate_subject(subject)
        self.test: float = self._validate_float(test, "test")
        self.exam: float = self._validate_float(exam, "exam")

    @staticmethod
    def _validate_student(student: Student) -> Student:
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        return student

    @staticmethod
    def _validate_subject(subject: Subject) -> Subject:
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        return subject

    @staticmethod
    def _validate_float(value: float, field_name: str) -> float:
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{field_name} must be a number")
        return float(value)