from typing import Any, Optional, Tuple
from datetime import date, datetime

class CustomUserManager:
    def create_user(self, email: str, password: str) -> 'User':
        return User(
            email=email,
            is_active=True,
            is_admin=False,
            is_staff=False,
            is_student=False
        )

    def create_superuser(self, email: str, password: str) -> 'User':
        return User(
            email=email,
            is_active=True,
            is_admin=True,
            is_staff=True,
            is_student=False
        )

class User:
    USERNAME_FIELD: str = 'email'
    objects: CustomUserManager = CustomUserManager()

    def __init__(
        self,
        email: str,
        is_active: bool = True,
        is_admin: bool = False,
        is_staff: bool = False,
        is_student: bool = False
    ):
        self.email = email
        self.is_active = is_active
        self.is_admin = is_admin
        self.is_staff = is_staff
        self.is_student = is_student

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_admin

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return self.is_admin

class UserProfile:
    LEVELS: Tuple[Any, ...] = ()

    def __init__(
        self,
        user: User,
        avatar_url: str,
        bio: str,
        codepen_username: str,
        current_level: int,
        discord_name: str,
        fcc_profile_url: str,
        github_username: str,
        name: str,
        phone: str,
        preferred_name: str,
        timezone: str
    ):
        self.user = user
        self.avatar_url = avatar_url
        self.bio = bio
        self.codepen_username = codepen_username
        self.current_level = current_level
        self.discord_name = discord_name
        self.fcc_profile_url = fcc_profile_url
        self.github_username = github_username
        self.name = name
        self.phone = phone
        self.preferred_name = preferred_name
        self.timezone = timezone

class AbstractTableMeta:
    class Meta:
        abstract: bool = True

    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date
    ):
        self.created_at = created_at
        self.created_by = created_by
        self.modified_by = modified_by
        self.updated_at = updated_at

class Lecture(AbstractTableMeta):
    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date,
        date_val: date,
        description: str,
        duration: int,
        lecturer_name: str,
        level: int,
        required: bool,
        slides_url: str,
        title: str
    ):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.date = date_val
        self.description = description
        self.duration = duration
        self.lecturer_name = lecturer_name
        self.level = level
        self.required = required
        self.slides_url = slides_url
        self.title = title

class Attendance(AbstractTableMeta):
    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date,
        lecture: Lecture,
        student: User
    ):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.lecture = lecture
        self.student = student

class Certificate(AbstractTableMeta):
    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date,
        description: str,
        name: str
    ):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.description = description
        self.name = name

class Project(AbstractTableMeta):
    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date,
        desription: str,
        level: int,
        required: bool,
        title: str,
        url: str
    ):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.desription = desription
        self.level = level
        self.required = required
        self.title = title
        self.url = url

class StudentSubmission(AbstractTableMeta):
    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date,
        approved: bool,
        feedback: str,
        project: Project,
        student: User,
        url: str
    ):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.approved = approved
        self.feedback = feedback
        self.project = project
        self.student = student
        self.url = url

class Volunteer:
    def __init__(
        self,
        email: str,
        first_name: str,
        last_name: str,
        hours_available: str
    ):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.hours_available = hours_available

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class VolunteerHours:
    class Meta:
        verbose_name_plural: str = "Volunteer Hours"

    def __init__(
        self,
        end: datetime,
        start: datetime,
        volunteer: Volunteer
    ):
        self.end = end
        self.start = start
        self.volunteer = volunteer

class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = "Waitlist Entries"

    def __init__(
        self,
        created_at: date,
        created_by: User,
        modified_by: User,
        updated_at: date,
        email: str,
        first_name: str,
        last_name: str,
        level: int,
        notes: str
    ):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.level = level
        self.notes = notes

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"