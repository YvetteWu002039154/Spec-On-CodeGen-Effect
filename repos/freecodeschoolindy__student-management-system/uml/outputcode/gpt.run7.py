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
        self.modified_by = modified_by


class Certificate(AbstractTableMeta):
    def __init__(
        self,
        name: str,
        description: str,
        *,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
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
        updated_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.title: str = title
        self.description: str = description
        self.date: date = date
        self.duration: int = duration
        self.lecturer_name: str = lecturer_name
        self.level: int = level
        self.required: bool = required
        self.slides_url: str = slides_url


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
        updated_at: Optional[date] = None,
        created_by: Optional["User"] = None,
        modified_by: Optional["User"] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.title: str = title
        self.desription: str = desription
        self.level: int = level
        self.required: bool = required
        self.url: str = url


class User:
    USERNAME_FIELD: ClassVar[str] = "email"

    def __init__(
        self,
        email: str,
        *,
        is_active: bool = True,
        is_admin: bool = False,
        is_staff: bool = False,
        is_student: bool = False,
        password: Optional[str] = None,
    ) -> None:
        self.email: str = email
        self.is_active: bool = is_active
        self.is_admin: bool = is_admin
        self.is_staff: bool = is_staff
        self.is_student: bool = is_student
        self._password: Optional[str] = password

    def set_password(self, password: str) -> None:
        self._password = password

    def check_password(self, password: str) -> bool:
        return self._password == password

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return bool(self.is_admin)

    def has_module_perms(self, app_label: str) -> bool:
        return bool(self.is_admin)


class CustomUserManager:
    def create_user(self, email: str, password: str) -> User:
        user = User(email=email, is_active=True, is_admin=False, is_staff=False, is_student=False)
        user.set_password(password)
        return user

    def create_superuser(self, email: str, password: str) -> User:
        user = User(email=email, is_active=True, is_admin=True, is_staff=True, is_student=False)
        user.set_password(password)
        return user


User.objects = CustomUserManager()


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
        *,
        avatar_url: str = "",
        bio: str = "",
        codepen_username: str = "",
        discord_name: str = "",
        fcc_profile_url: str = "",
        github_username: str = "",
    ) -> None:
        self.user: User = user
        self.name: str = name
        self.preferred_name: str = preferred_name
        self.phone: str = phone
        self.timezone: str = timezone
        self.current_level: int = current_level
        self.avatar_url: str = avatar_url
        self.bio: str = bio
        self.codepen_username: str = codepen_username
        self.discord_name: str = discord_name
        self.fcc_profile_url: str = fcc_profile_url
        self.github_username: str = github_username


class Attendance(AbstractTableMeta):
    def __init__(
        self,
        lecture: Lecture,
        student: User,
        *,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.lecture: Lecture = lecture
        self.student: User = student


class StudentSubmission(AbstractTableMeta):
    def __init__(
        self,
        project: Project,
        student: User,
        url: str,
        *,
        approved: bool = False,
        feedback: str = "",
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
        self.project: Project = project
        self.student: User = student
        self.url: str = url
        self.approved: bool = approved
        self.feedback: str = feedback


class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = "Waitlist entries"

    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        level: int,
        notes: str,
        *,
        created_at: Optional[date] = None,
        updated_at: Optional[date] = None,
        created_by: Optional[User] = None,
        modified_by: Optional[User] = None,
    ) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at, created_by=created_by, modified_by=modified_by)
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
        verbose_name_plural: str = "Volunteer hours"

    def __init__(self, volunteer: Volunteer, start: datetime, end: datetime) -> None:
        self.volunteer: Volunteer = volunteer
        self.start: datetime = start
        self.end: datetime = end