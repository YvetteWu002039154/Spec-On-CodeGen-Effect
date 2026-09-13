from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional, Tuple


class AbstractTableMeta:
    class Meta:
        abstract: bool = True

    def __init__(
        self,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        self.created_at: date = created_at if created_at is not None else date.today()
        self.updated_at: date = updated_at if updated_at is not None else self.created_at
        self.created_by: Optional["User"] = created_by
        self.modified_by: Optional["User"] = modified_by

    def touch(self, modified_by: Optional["User"] = None, when: Optional[date] = None) -> None:
        self.updated_at = when if when is not None else date.today()
        if modified_by is not None:
            self.modified_by = modified_by


class CustomUserManager:
    def create_user(self, email: str, password: str) -> "User":
        if email is None or not str(email).strip():
            raise ValueError("email is required")
        if password is None or not str(password):
            raise ValueError("password is required")
        user = User(email=email.strip().lower())
        user.set_password(password)
        user.is_active = True
        return user

    def create_superuser(self, email: str, password: str) -> "User":
        user = self.create_user(email=email, password=password)
        user.is_admin = True
        user.is_staff = True
        user.is_active = True
        return user


class User:
    USERNAME_FIELD: str = "email"
    objects: CustomUserManager = CustomUserManager()

    def __init__(
        self,
        email: str,
        is_active: bool = True,
        is_admin: bool = False,
        is_staff: bool = False,
        is_student: bool = False,
    ) -> None:
        if email is None or not str(email).strip():
            raise ValueError("email is required")
        self.email: str = email.strip().lower()
        self.is_active: bool = bool(is_active)
        self.is_admin: bool = bool(is_admin)
        self.is_staff: bool = bool(is_staff)
        self.is_student: bool = bool(is_student)
        self._password: Optional[str] = None

    def set_password(self, password: str) -> None:
        if password is None or not str(password):
            raise ValueError("password is required")
        self._password = str(password)

    def check_password(self, password: str) -> bool:
        return self._password is not None and self._password == password

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return bool(self.is_admin)

    def has_module_perms(self, app_label: str) -> bool:
        return bool(self.is_admin)


class UserProfile:
    LEVELS: Tuple[Tuple[int, str], ...] = (
        (1, "Level 1"),
        (2, "Level 2"),
        (3, "Level 3"),
        (4, "Level 4"),
        (5, "Level 5"),
    )

    def __init__(
        self,
        user: User,
        name: str = "",
        preferred_name: str = "",
        phone: str = "",
        timezone: str = "",
        discord_name: str = "",
        github_username: str = "",
        codepen_username: str = "",
        fcc_profile_url: str = "",
        avatar_url: str = "",
        bio: str = "",
        current_level: int = 1,
    ) -> None:
        if user is None:
            raise ValueError("user is required")
        self.user: User = user
        self.name: str = str(name)
        self.preferred_name: str = str(preferred_name)
        self.phone: str = str(phone)
        self.timezone: str = str(timezone)
        self.discord_name: str = str(discord_name)
        self.github_username: str = str(github_username)
        self.codepen_username: str = str(codepen_username)
        self.fcc_profile_url: str = str(fcc_profile_url)
        self.avatar_url: str = str(avatar_url)
        self.bio: str = str(bio)
        self.current_level: int = int(current_level)


class Certificate(AbstractTableMeta):
    def __init__(
        self,
        name: str,
        description: str = "",
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.name: str = str(name)
        self.description: str = str(description)


class Lecture(AbstractTableMeta):
    def __init__(
        self,
        title: str,
        date: date,
        description: str = "",
        duration: int = 0,
        lecturer_name: str = "",
        level: int = 1,
        required: bool = False,
        slides_url: str = "",
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.title: str = str(title)
        self.date: date = date
        self.description: str = str(description)
        self.duration: int = int(duration)
        self.lecturer_name: str = str(lecturer_name)
        self.level: int = int(level)
        self.required: bool = bool(required)
        self.slides_url: str = str(slides_url)


class Attendance(AbstractTableMeta):
    def __init__(
        self,
        lecture: Lecture,
        student: User,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        if lecture is None:
            raise ValueError("lecture is required")
        if student is None:
            raise ValueError("student is required")
        self.lecture: Lecture = lecture
        self.student: User = student


class Project(AbstractTableMeta):
    def __init__(
        self,
        title: str,
        url: str = "",
        desription: str = "",
        level: int = 1,
        required: bool = False,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.title: str = str(title)
        self.url: str = str(url)
        self.desription: str = str(desription)
        self.level: int = int(level)
        self.required: bool = bool(required)


class StudentSubmission(AbstractTableMeta):
    def __init__(
        self,
        project: Project,
        student: User,
        url: str = "",
        approved: bool = False,
        feedback: str = "",
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        if project is None:
            raise ValueError("project is required")
        if student is None:
            raise ValueError("student is required")
        self.project: Project = project
        self.student: User = student
        self.url: str = str(url)
        self.approved: bool = bool(approved)
        self.feedback: str = str(feedback)


class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = "Waitlist entries"

    def __init__(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        level: int = 1,
        notes: str = "",
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        if email is None or not str(email).strip():
            raise ValueError("email is required")
        self.email: str = str(email).strip().lower()
        self.first_name: str = str(first_name)
        self.last_name: str = str(last_name)
        self.level: int = int(level)
        self.notes: str = str(notes)

    def full_name(self) -> str:
        return " ".join(part for part in [self.first_name.strip(), self.last_name.strip()] if part)


class Volunteer:
    def __init__(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        hours_available: str = "",
    ) -> None:
        if email is None or not str(email).strip():
            raise ValueError("email is required")
        self.email: str = str(email).strip().lower()
        self.first_name: str = str(first_name)
        self.last_name: str = str(last_name)
        self.hours_available: str = str(hours_available)

    @property
    def full_name(self) -> str:
        return " ".join(part for part in [self.first_name.strip(), self.last_name.strip()] if part)


class VolunteerHours:
    class Meta:
        verbose_name_plural: str = "Volunteer hours"

    def __init__(self, volunteer: Volunteer, start: datetime, end: datetime) -> None:
        if volunteer is None:
            raise ValueError("volunteer is required")
        if start is None or end is None:
            raise ValueError("start and end are required")
        if end < start:
            raise ValueError("end must be after start")
        self.volunteer: Volunteer = volunteer
        self.start: datetime = start
        self.end: datetime = end