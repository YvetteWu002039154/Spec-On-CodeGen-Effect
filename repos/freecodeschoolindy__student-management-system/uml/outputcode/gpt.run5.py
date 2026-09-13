from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, Optional, Tuple


class AbstractTableMeta:
    class Meta:
        abstract: bool = True

    def __init__(
        self,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        self.created_at: Optional[date] = created_at
        self.created_by: Optional["User"] = created_by
        self.updated_at: Optional[date] = updated_at
        self.modified_by: Optional["User"] = modified_by


class Certificate(AbstractTableMeta):
    def __init__(
        self,
        name: str,
        description: str,
        *,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, created_by=created_by, updated_at=updated_at, modified_by=modified_by)
        self.name: str = name
        self.description: str = description


class Lecture(AbstractTableMeta):
    def __init__(
        self,
        title: str,
        description: str,
        date: date,
        duration: int,
        lecturer_name: str,
        level: int,
        required: bool,
        slides_url: str,
        *,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, created_by=created_by, updated_at=updated_at, modified_by=modified_by)
        self.title: str = title
        self.description: str = description
        self.date: date = date
        self.duration: int = duration
        self.lecturer_name: str = lecturer_name
        self.level: int = level
        self.required: bool = required
        self.slides_url: str = slides_url


class Attendance(AbstractTableMeta):
    def __init__(
        self,
        lecture: Lecture,
        student: "User",
        *,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, created_by=created_by, updated_at=updated_at, modified_by=modified_by)
        self.lecture: Lecture = lecture
        self.student: "User" = student


class Project(AbstractTableMeta):
    def __init__(
        self,
        title: str,
        desription: str,
        level: int,
        required: bool,
        url: str,
        *,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, created_by=created_by, updated_at=updated_at, modified_by=modified_by)
        self.title: str = title
        self.desription: str = desription
        self.level: int = level
        self.required: bool = required
        self.url: str = url


class StudentSubmission(AbstractTableMeta):
    def __init__(
        self,
        project: Project,
        student: "User",
        url: str,
        approved: bool,
        feedback: str,
        *,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, created_by=created_by, updated_at=updated_at, modified_by=modified_by)
        self.project: Project = project
        self.student: "User" = student
        self.url: str = url
        self.approved: bool = approved
        self.feedback: str = feedback


class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = "Waitlist Entries"

    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        level: int,
        notes: str,
        *,
        created_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        updated_at: Optional[date] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, created_by=created_by, updated_at=updated_at, modified_by=modified_by)
        self.email: str = email
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.level: int = level
        self.notes: str = notes

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Volunteer:
    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        hours_available: str,
    ) -> None:
        self.email: str = email
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.hours_available: str = hours_available

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class VolunteerHours:
    class Meta:
        verbose_name_plural: str = "Volunteer Hours"

    def __init__(
        self,
        volunteer: Volunteer,
        start: datetime,
        end: datetime,
    ) -> None:
        self.volunteer: Volunteer = volunteer
        self.start: datetime = start
        self.end: datetime = end


class CustomUserManager:
    def create_user(self, email: str, password: str) -> "User":
        return User(email=email, password=password)

    def create_superuser(self, email: str, password: str) -> "User":
        user = User(email=email, password=password)
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
        self.email: str = email
        self._password: str = password
        self.is_active: bool = is_active
        self.is_admin: bool = is_admin
        self.is_staff: bool = is_staff
        self.is_student: bool = is_student

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return bool(self.is_admin)

    def has_module_perms(self, app_label: str) -> bool:
        return True


class UserProfile:
    LEVELS: ClassVar[Tuple[Tuple[int, str], ...]] = (
        (1, "Level 1"),
        (2, "Level 2"),
        (3, "Level 3"),
        (4, "Level 4"),
        (5, "Level 5"),
    )

    def __init__(
        self,
        user: User,
        name: str,
        preferred_name: str,
        phone: str,
        timezone: str,
        current_level: int,
        bio: str,
        avatar_url: str,
        discord_name: str,
        github_username: str,
        codepen_username: str,
        fcc_profile_url: str,
    ) -> None:
        self.user: User = user
        self.name: str = name
        self.preferred_name: str = preferred_name
        self.phone: str = phone
        self.timezone: str = timezone
        self.current_level: int = current_level
        self.bio: str = bio
        self.avatar_url: str = avatar_url
        self.discord_name: str = discord_name
        self.github_username: str = github_username
        self.codepen_username: str = codepen_username
        self.fcc_profile_url: str = fcc_profile_url