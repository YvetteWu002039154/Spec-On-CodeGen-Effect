from datetime import date, datetime
from typing import Optional, Any


# ==================== Abstract Base ====================

class AbstractTableMetaMeta:
    abstract = True


class AbstractTableMeta:
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        self.created_at: Optional[date] = kwargs.get('created_at', None)
        self.updated_at: Optional[date] = kwargs.get('updated_at', None)
        self.created_by: Optional[Any] = kwargs.get('created_by', None)
        self.modified_by: Optional[Any] = kwargs.get('modified_by', None)


# ==================== Users ====================

class CustomUserManager:
    def __init__(self):
        self._users = []

    def create_user(self, email: str, password: str) -> 'User':
        if not email:
            raise ValueError("Users must have an email address")
        if not password:
            raise ValueError("Users must have a password")
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
        if not password:
            raise ValueError("Superusers must have a password")
        user = User(email=email)
        user.set_password(password)
        user.is_active = True
        user.is_admin = True
        user.is_staff = True
        user.is_student = False
        self._users.append(user)
        return user


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

    def check_password(self, password: str) -> bool:
        return self._password == password

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return self.is_admin

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_admin

    def __repr__(self) -> str:
        return f"User(email={self.email!r})"


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

    def __repr__(self) -> str:
        return f"UserProfile(user={self.user!r}, name={self.name!r})"


# ==================== Certificates ====================

class Certificate(AbstractTableMeta):
    def __init__(self, name: str = '', description: str = '', **kwargs):
        super().__init__(**kwargs)
        self.name: str = name
        self.description: str = description

    def __repr__(self) -> str:
        return f"Certificate(name={self.name!r})"


# ==================== Lectures ====================

class Lecture(AbstractTableMeta):
    def __init__(self, title: str = '', **kwargs):
        super().__init__(**kwargs)
        self.title: str = title
        self.description: str = kwargs.get('description', '')
        self.date: Optional[date] = kwargs.get('date', None)
        self.duration: int = kwargs.get('duration', 0)
        self.lecturer_name: str = kwargs.get('lecturer_name', '')
        self.level: int = kwargs.get('level', 1)
        self.required: bool = kwargs.get('required', False)
        self.slides_url: str = kwargs.get('slides_url', '')

    def __repr__(self) -> str:
        return f"Lecture(title={self.title!r})"


class Attendance(AbstractTableMeta):
    def __init__(self, lecture: Lecture, student: User, **kwargs):
        super().__init__(**kwargs)
        self.lecture: Lecture = lecture
        self.student: User = student

    def __repr__(self) -> str:
        return f"Attendance(lecture={self.lecture!r}, student={self.student!r})"


# ==================== Projects ====================

class Project(AbstractTableMeta):
    def __init__(self, title: str = '', **kwargs):
        super().__init__(**kwargs)
        self.title: str = title
        self.desription: str = kwargs.get('desription', '')
        self.level: int = kwargs.get('level', 1)
        self.required: bool = kwargs.get('required', False)
        self.url: str = kwargs.get('url', '')

    def __repr__(self) -> str:
        return f"Project(title={self.title!r})"


# ==================== Submissions ====================

class StudentSubmission(AbstractTableMeta):
    def __init__(self, project: Project, student: User, **kwargs):
        super().__init__(**kwargs)
        self.project: Project = project
        self.student: User = student
        self.approved: bool = kwargs.get('approved', False)
        self.feedback: str = kwargs.get('feedback', '')
        self.url: str = kwargs.get('url', '')

    def __repr__(self) -> str:
        return f"StudentSubmission(project={self.project!r}, student={self.student!r})"


# ==================== Volunteers ====================

class Volunteer:
    def __init__(self, first_name: str = '', last_name: str = '', email: str = '', **kwargs):
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.email: str = email
        self.hours_available: str = kwargs.get('hours_available', '')

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"Volunteer(email={self.email!r}, full_name={self.full_name!r})"


class VolunteerHours:
    class Meta:
        verbose_name_plural: str = 'Volunteer Hours'

    def __init__(self, volunteer: Volunteer, start: Optional[datetime] = None, end: Optional[datetime] = None, **kwargs):
        self.volunteer: Volunteer = volunteer
        self.start: Optional[datetime] = start
        self.end: Optional[datetime] = end

    def __repr__(self) -> str:
        return f"VolunteerHours(volunteer={self.volunteer!r}, start={self.start!r}, end={self.end!r})"


# ==================== Waitlist ====================

class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural: str = 'Waitlist Entries'

    def __init__(self, first_name: str = '', last_name: str = '', email: str = '', **kwargs):
        super().__init__(**kwargs)
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.email: str = email
        self.level: int = kwargs.get('level', 1)
        self.notes: str = kwargs.get('notes', '')

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"WaitlistEntry(email={self.email!r}, full_name={self.full_name()!r})"