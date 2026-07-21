from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar, List, Optional, Tuple


class AbstractTableMeta:
    class Meta:
        abstract: bool = True

    def __init__(
        self,
        created_by: Optional["User"] = None,
        modified_by: Optional["User"] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        self.created_by = created_by
        self.modified_by = modified_by
        self.created_at = created_at or date.today()
        self.updated_at = updated_at or date.today()

    def touch(self, modified_by: Optional["User"] = None) -> None:
        self.modified_by = modified_by
        self.updated_at = date.today()


class CustomUserManager:
    def __init__(self) -> None:
        self._users: List[User] = []

    def create_user(self, email: str, password: str) -> "User":
        if not email or not isinstance(email, str):
            raise ValueError("Email is required")
        if not password or not isinstance(password, str):
            raise ValueError("Password is required")
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("Email is required")
        if any(user.email == normalized_email for user in self._users):
            raise ValueError("A user with this email already exists")
        user = User(
            email=normalized_email,
            password=password,
            is_active=True,
            is_admin=False,
            is_staff=False,
            is_student=False,
        )
        self._users.append(user)
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email, password)
        user.is_admin = True
        user.is_staff = True
        user.is_active = True
        return user


class User:
    USERNAME_FIELD: ClassVar[str] = "email"
    objects: ClassVar[CustomUserManager] = CustomUserManager()

    def __init__(
        self,
        email: str,
        password: str,
        is_active: bool = True,
        is_admin: bool = False,
        is_staff: bool = False,
        is_student: bool = False,
    ) -> None:
        if not email or not isinstance(email, str):
            raise ValueError("Email is required")
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("Valid email is required")
        if not password or not isinstance(password, str):
            raise ValueError("Password is required")
        self.email = normalized_email
        self._password = password
        self.is_active = bool(is_active)
        self.is_admin = bool(is_admin)
        self.is_staff = bool(is_staff)
        self.is_student = bool(is_student)
        self.profile: Optional[UserProfile] = None

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return self.is_admin

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_admin

    def __repr__(self) -> str:
        return f"User(email={self.email!r})"


class UserProfile:
    LEVELS: ClassVar[Tuple[Tuple[int, str], ...]] = (
        (1, "Beginner"),
        (2, "Intermediate"),
        (3, "Advanced"),
    )

    def __init__(
        self,
        user: User,
        name: str,
        preferred_name: str = "",
        bio: str = "",
        avatar_url: str = "",
        codepen_username: str = "",
        current_level: int = 1,
        discord_name: str = "",
        fcc_profile_url: str = "",
        github_username: str = "",
        phone: str = "",
        timezone: str = "",
    ) -> None:
        if not isinstance(user, User):
            raise ValueError("user must be a User instance")
        if user.profile is not None:
            raise ValueError("User already has a profile")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name is required")
        valid_levels = {level for level, _ in self.LEVELS}
        if current_level not in valid_levels:
            raise ValueError("Invalid current_level")
        self.user = user
        self.name = name
        self.preferred_name = preferred_name
        self.bio = bio
        self.avatar_url = avatar_url
        self.codepen_username = codepen_username
        self.current_level = current_level
        self.discord_name = discord_name
        self.fcc_profile_url = fcc_profile_url
        self.github_username = github_username
        self.phone = phone
        self.timezone = timezone
        user.profile = self


class Certificate(AbstractTableMeta):
    def __init__(
        self,
        name: str,
        description: str,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        super().__init__(created_by, modified_by, created_at, updated_at)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name is required")
        self.name = name
        self.description = description


class Lecture(AbstractTableMeta):
    def __init__(
        self,
        title: str,
        lecturer_name: str,
        date: date,
        duration: int,
        level: int,
        required: bool,
        description: str = "",
        slides_url: str = "",
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        super().__init__(created_by, modified_by, created_at, updated_at)
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title is required")
        if not isinstance(lecturer_name, str) or not lecturer_name.strip():
            raise ValueError("lecturer_name is required")
        if not isinstance(date, type(__import__("datetime").date.today())):
            raise ValueError("date must be a date instance")
        if not isinstance(duration, int):
            raise ValueError("duration must be an integer")
        if not isinstance(level, int):
            raise ValueError("level must be an integer")
        self.title = title
        self.lecturer_name = lecturer_name
        self.date = date
        self.duration = duration
        self.level = level
        self.required = bool(required)
        self.description = description
        self.slides_url = slides_url


class Attendance(AbstractTableMeta):
    def __init__(
        self,
        lecture: Lecture,
        student: User,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        super().__init__(created_by, modified_by, created_at, updated_at)
        if not isinstance(lecture, Lecture):
            raise ValueError("lecture must be a Lecture instance")
        if not isinstance(student, User):
            raise ValueError("student must be a User instance")
        self.lecture = lecture
        self.student = student


class Project(AbstractTableMeta):
    def __init__(
        self,
        title: str,
        level: int,
        required: bool,
        url: str = "",
        desription: str = "",
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        super().__init__(created_by, modified_by, created_at, updated_at)
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title is required")
        if not isinstance(level, int):
            raise ValueError("level must be an integer")
        self.title = title
        self.level = level
        self.required = bool(required)
        self.url = url
        self.desription = desription


class StudentSubmission(AbstractTableMeta):
    def __init__(
        self,
        project: Project,
        student: User,
        url: str,
        approved: bool = False,
        feedback: str = "",
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        super().__init__(created_by, modified_by, created_at, updated_at)
        if not isinstance(project, Project):
            raise ValueError("project must be a Project instance")
        if not isinstance(student, User):
            raise ValueError("student must be a User instance")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url is required")
        self.project = project
        self.student = student
        self.url = url
        self.approved = bool(approved)
        self.feedback = feedback


class Volunteer:
    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        hours_available: str = "",
    ) -> None:
        if not email or not isinstance(email, str) or "@" not in email.strip():
            raise ValueError("Valid email is required")
        if not isinstance(first_name, str) or not first_name.strip():
            raise ValueError("first_name is required")
        if not isinstance(last_name, str) or not last_name.strip():
            raise ValueError("last_name is required")
        self.email = email.strip().lower()
        self.first_name = first_name
        self.last_name = last_name
        self.hours_available = hours_available

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class VolunteerHours:
    class Meta:
        verbose_name_plural: str = "Volunteer hours"

    def __init__(self, volunteer: Volunteer, start: datetime, end: datetime) -> None:
        if not isinstance(volunteer, Volunteer):
            raise ValueError("volunteer must be a Volunteer instance")
        if not isinstance(start, datetime):
            raise ValueError("start must be a datetime instance")
        if not isinstance(end, datetime):
            raise ValueError("end must be a datetime instance")
        if end < start:
            raise ValueError("end must be greater than or equal to start")
        self.volunteer = volunteer
        self.start = start
        self.end = end


class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = "Waitlist entries"

    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        level: int,
        notes: str = "",
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
    ) -> None:
        super().__init__(created_by, modified_by, created_at, updated_at)
        if not email or not isinstance(email, str) or "@" not in email.strip():
            raise ValueError("Valid email is required")
        if not isinstance(first_name, str) or not first_name.strip():
            raise ValueError("first_name is required")
        if not isinstance(last_name, str) or not last_name.strip():
            raise ValueError("last_name is required")
        if not isinstance(level, int):
            raise ValueError("level must be an integer")
        self.email = email.strip().lower()
        self.first_name = first_name
        self.last_name = last_name
        self.level = level
        self.notes = notes

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"