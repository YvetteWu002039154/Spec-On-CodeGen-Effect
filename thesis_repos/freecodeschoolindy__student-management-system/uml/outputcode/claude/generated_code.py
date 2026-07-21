from datetime import date, datetime
from typing import Optional, Any


# Abstract base for table metadata
class AbstractTableMeta:
    class Meta:
        abstract: bool = True

    def __init__(self, *args, **kwargs):
        self.created_at: Optional[date] = kwargs.get('created_at', None)
        self.updated_at: Optional[date] = kwargs.get('updated_at', None)
        self.created_by: Optional[Any] = kwargs.get('created_by', None)
        self.modified_by: Optional[Any] = kwargs.get('modified_by', None)


# Custom User Manager
class CustomUserManager:
    def __init__(self):
        self._users = []

    def create_user(self, email: str, password: str) -> 'User':
        if not email:
            raise ValueError("Users must have an email address")
        user = User(email=email)
        user.set_password(password)
        user.is_active = True
        user.is_admin = False
        user.is_staff = False
        user.is_student = True
        self._users.append(user)
        return user

    def create_superuser(self, email: str, password: str) -> 'User':
        if not email:
            raise ValueError("Superusers must have an email address")
        user = User(email=email)
        user.set_password(password)
        user.is_active = True
        user.is_admin = True
        user.is_staff = True
        user.is_student = False
        self._users.append(user)
        return user


# User model
class User:
    USERNAME_FIELD: str = 'email'
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: str = '', **kwargs):
        self.email: str = email
        self.is_active: bool = kwargs.get('is_active', True)
        self.is_admin: bool = kwargs.get('is_admin', False)
        self.is_staff: bool = kwargs.get('is_staff', False)
        self.is_student: bool = kwargs.get('is_student', True)
        self._password: Optional[str] = None

    def set_password(self, password: str) -> None:
        self._password = password

    def has_perm(self, perm: str, obj: Optional[Any] = None) -> bool:
        return self.is_admin

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_admin


# User Profile
class UserProfile:
    LEVELS: tuple = (
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
        (5, 'Level 5'),
    )

    def __init__(self, user: User, **kwargs):
        self.user: User = user
        self.name: str = kwargs.get('name', '')
        self.preferred_name: str = kwargs.get('preferred_name', '')
        self.avatar_url: str = kwargs.get('avatar_url', '')
        self.bio: str = kwargs.get('bio', '')
        self.codepen_username: str = kwargs.get('codepen_username', '')
        self.current_level: int = kwargs.get('current_level', 1)
        self.discord_name: str = kwargs.get('discord_name', '')
        self.fcc_profile_url: str = kwargs.get('fcc_profile_url', '')
        self.github_username: str = kwargs.get('github_username', '')
        self.phone: str = kwargs.get('phone', '')
        self.timezone: str = kwargs.get('timezone', '')


# Certificate
class Certificate(AbstractTableMeta):
    def __init__(self, name: str = '', description: str = '', **kwargs):
        super().__init__(**kwargs)
        self.name: str = name
        self.description: str = description


# Lecture
class Lecture(AbstractTableMeta):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title: str = kwargs.get('title', '')
        self.description: str = kwargs.get('description', '')
        self.date: Optional[date] = kwargs.get('date', None)
        self.duration: int = kwargs.get('duration', 0)
        self.lecturer_name: str = kwargs.get('lecturer_name', '')
        self.level: int = kwargs.get('level', 1)
        self.required: bool = kwargs.get('required', False)
        self.slides_url: str = kwargs.get('slides_url', '')


# Attendance
class Attendance(AbstractTableMeta):
    def __init__(self, lecture: Optional[Lecture] = None, student: Optional[User] = None, **kwargs):
        super().__init__(**kwargs)
        self.lecture: Optional[Lecture] = lecture
        self.student: Optional[User] = student


# Project
class Project(AbstractTableMeta):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title: str = kwargs.get('title', '')
        self.desription: str = kwargs.get('desription', '')
        self.level: int = kwargs.get('level', 1)
        self.required: bool = kwargs.get('required', False)
        self.url: str = kwargs.get('url', '')


# Student Submission
class StudentSubmission(AbstractTableMeta):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project: Optional[Project] = kwargs.get('project', None)
        self.student: Optional[User] = kwargs.get('student', None)
        self.url: str = kwargs.get('url', '')
        self.approved: bool = kwargs.get('approved', False)
        self.feedback: str = kwargs.get('feedback', '')


# Volunteer
class Volunteer:
    def __init__(self, **kwargs):
        self.first_name: str = kwargs.get('first_name', '')
        self.last_name: str = kwargs.get('last_name', '')
        self.email: str = kwargs.get('email', '')
        self.hours_available: str = kwargs.get('hours_available', '')

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# Volunteer Hours
class VolunteerHours:
    class Meta:
        verbose_name_plural: str = 'Volunteer Hours'

    def __init__(self, volunteer: Optional[Volunteer] = None, **kwargs):
        self.volunteer: Optional[Volunteer] = volunteer
        self.start: Optional[datetime] = kwargs.get('start', None)
        self.end: Optional[datetime] = kwargs.get('end', None)


# Waitlist Entry
class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = 'Waitlist Entries'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_name: str = kwargs.get('first_name', '')
        self.last_name: str = kwargs.get('last_name', '')
        self.email: str = kwargs.get('email', '')
        self.level: int = kwargs.get('level', 1)
        self.notes: str = kwargs.get('notes', '')

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()