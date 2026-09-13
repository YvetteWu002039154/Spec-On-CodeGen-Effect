from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, List, Optional, Tuple, Type, TypeVar, Union


T = TypeVar("T")


class ValidationError(ValueError):
    pass


class OneToOneField:
    def __init__(self, related_type: Type[Any]):
        self.related_type = related_type


class ForeignKey:
    def __init__(self, related_type: Type[Any]):
        self.related_type = related_type


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


class BaseModel:
    def __init__(self) -> None:
        now = datetime.utcnow()
        self.created_at: datetime = now
        self.updated_at: datetime = now

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class CustomUserManager:
    def create_user(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        if not email or not isinstance(email, str):
            raise ValidationError("email is required")
        if password is None or (isinstance(password, str) and password == "") or (isinstance(password, (bytes, bytearray)) and len(password) == 0):
            raise ValidationError("password is required")
        user = CustomUser(email=email)
        user.set_password(password)
        return user

    def create_superuser(self, email: str, password: Union[str, bytes]) -> "CustomUser":
        user = self.create_user(email=email, password=password)
        user.user_type = "1"
        return user


class CustomUser(BaseModel):
    GENDER: ClassVar[List[str]] = ["Male", "Female", "Other"]
    USER_TYPE: ClassVar[Tuple[Tuple[str, str], ...]] = (("1", "Admin"), ("2", "Staff"), ("3", "Student"))
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = []

    objects: ClassVar[CustomUserManager] = CustomUserManager()

    def __init__(
        self,
        email: str,
        password: Optional[Union[str, bytes]] = None,
        address: str = "",
        fcm_token: str = "",
        gender: str = "Other",
        profile_pic: str = "",
        user_type: str = "3",
        username: Optional[None] = None,
    ) -> None:
        super().__init__()
        if not email or not isinstance(email, str):
            raise ValidationError("email is required")
        self.email: str = email
        self.username: Optional[None] = username
        self.address: str = address
        self.fcm_token: str = fcm_token
        if gender not in self.GENDER:
            raise ValidationError("invalid gender")
        self.gender: str = gender
        self.profile_pic: str = profile_pic
        if user_type not in {k for k, _ in self.USER_TYPE}:
            raise ValidationError("invalid user_type")
        self.user_type: str = user_type
        self.password: Union[str, bytes] = b""
        if password is not None:
            self.set_password(password)

    def set_password(self, password: Union[str, bytes]) -> None:
        if password is None:
            raise ValidationError("password is required")
        if isinstance(password, str):
            if password == "":
                raise ValidationError("password is required")
            self.password = password.encode("utf-8")
        elif isinstance(password, (bytes, bytearray)):
            if len(password) == 0:
                raise ValidationError("password is required")
            self.password = bytes(password)
        else:
            raise ValidationError("password must be str or bytes")
        self.touch()

    def check_password(self, password: Union[str, bytes]) -> bool:
        if isinstance(password, str):
            return self.password == password.encode("utf-8")
        if isinstance(password, (bytes, bytearray)):
            return self.password == bytes(password)
        return False


class Admin:
    admin: OneToOneField = OneToOneField(CustomUser)

    def __init__(self, admin: CustomUser) -> None:
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        self.admin_user: CustomUser = admin


class Course(BaseModel):
    def __init__(self, name: str) -> None:
        super().__init__()
        if not name or not isinstance(name, str):
            raise ValidationError("name is required")
        self.name: str = name


class Session:
    def __init__(self, start_year: date, end_year: date) -> None:
        if not isinstance(start_year, date) or not isinstance(end_year, date):
            raise ValidationError("start_year and end_year must be date")
        self.start_year: date = start_year
        self.end_year: date = end_year


class Staff:
    admin: OneToOneField = OneToOneField(CustomUser)
    course: ForeignKey = ForeignKey(Course)

    def __init__(self, admin: CustomUser, course: Course) -> None:
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        self.admin_user: CustomUser = admin
        self.course_obj: Course = course


class Student:
    admin: OneToOneField = OneToOneField(CustomUser)
    course: ForeignKey = ForeignKey(Course)
    session: ForeignKey = ForeignKey(Session)

    def __init__(self, admin: CustomUser, course: Course, session: Session) -> None:
        if not isinstance(admin, CustomUser):
            raise ValidationError("admin must be a CustomUser")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        self.admin_user: CustomUser = admin
        self.course_obj: Course = course
        self.session_obj: Session = session


class Subject(BaseModel):
    course: ForeignKey = ForeignKey(Course)
    staff: ForeignKey = ForeignKey(Staff)

    def __init__(self, name: str, course: Course, staff: Staff) -> None:
        super().__init__()
        if not name or not isinstance(name, str):
            raise ValidationError("name is required")
        if not isinstance(course, Course):
            raise ValidationError("course must be a Course")
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        self.name: str = name
        self.course_obj: Course = course
        self.staff_obj: Staff = staff


class Attendance(BaseModel):
    session: ForeignKey = ForeignKey(Session)
    subject: ForeignKey = ForeignKey(Subject)

    def __init__(self, date_value: date, session: Session, subject: Subject) -> None:
        super().__init__()
        if not isinstance(date_value, date):
            raise ValidationError("date must be a date")
        if not isinstance(session, Session):
            raise ValidationError("session must be a Session")
        if not isinstance(subject, Subject):
            raise ValidationError("subject must be a Subject")
        self.date: date = date_value
        self.session_obj: Session = session
        self.subject_obj: Subject = subject


class AttendanceReport(BaseModel):
    attendance: ForeignKey = ForeignKey(Attendance)
    student: ForeignKey = ForeignKey(Student)

    def __init__(self, attendance: Attendance, student: Student, status: bool) -> None:
        super().__init__()
        if not isinstance(attendance, Attendance):
            raise ValidationError("attendance must be an Attendance")
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(status, bool):
            raise ValidationError("status must be a bool")
        self.attendance_obj: Attendance = attendance
        self.student_obj: Student = student
        self.status: bool = status


class FeedbackStaff(BaseModel):
    staff: ForeignKey = ForeignKey(Staff)

    def __init__(self, staff: Staff, feedback: str, reply: str = "") -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(feedback, str):
            raise ValidationError("feedback must be a str")
        if not isinstance(reply, str):
            raise ValidationError("reply must be a str")
        self.staff_obj: Staff = staff
        self.feedback: str = feedback
        self.reply: str = reply


class FeedbackStudent(BaseModel):
    student: ForeignKey = ForeignKey(Student)

    def __init__(self, student: Student, feedback: str, reply: str = "") -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(feedback, str):
            raise ValidationError("feedback must be a str")
        if not isinstance(reply, str):
            raise ValidationError("reply must be a str")
        self.student_obj: Student = student
        self.feedback: str = feedback
        self.reply: str = reply


class LeaveReportStaff(BaseModel):
    staff: ForeignKey = ForeignKey(Staff)

    def __init__(self, staff: Staff, date_value: str, message: str, status: int = 0) -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(date_value, str):
            raise ValidationError("date must be a str")
        if not isinstance(message, str):
            raise ValidationError("message must be a str")
        if not isinstance(status, int):
            raise ValidationError("status must be an int")
        self.staff_obj: Staff = staff
        self.date: str = date_value
        self.message: str = message
        self.status: int = status


class LeaveReportStudent(BaseModel):
    student: ForeignKey = ForeignKey(Student)

    def __init__(self, student: Student, date_value: str, message: str, status: int = 0) -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(date_value, str):
            raise ValidationError("date must be a str")
        if not isinstance(message, str):
            raise ValidationError("message must be a str")
        if not isinstance(status, int):
            raise ValidationError("status must be an int")
        self.student_obj: Student = student
        self.date: str = date_value
        self.message: str = message
        self.status: int = status


class NotificationStaff(BaseModel):
    staff: ForeignKey = ForeignKey(Staff)

    def __init__(self, staff: Staff, message: str) -> None:
        super().__init__()
        if not isinstance(staff, Staff):
            raise ValidationError("staff must be a Staff")
        if not isinstance(message, str):
            raise ValidationError("message must be a str")
        self.staff_obj: Staff = staff
        self.message: str = message


class NotificationStudent(BaseModel):
    student: ForeignKey = ForeignKey(Student)

    def __init__(self, student: Student, message: str) -> None:
        super().__init__()
        if not isinstance(student, Student):
            raise ValidationError("student must be a Student")
        if not isinstance(message, str):
            raise ValidationError("message must be a str")
        self.student_obj: Student = student
        self.message: str = message


class StudentResult(BaseModel):
    student: ForeignKey = ForeignKey(Student)
    subject: ForeignKey = ForeignKey(Subject)

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
        self.student_obj: Student = student
        self.subject_obj: Subject = subject
        self.test: float = float(test)
        self.exam: float = float(exam)