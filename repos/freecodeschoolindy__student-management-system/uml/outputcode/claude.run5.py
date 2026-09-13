from datetime import date, datetime
from typing import Optional, Any


# ============================================================
# apps/utils/models.py
# ============================================================

class AbstractTableMeta:
    """Abstract base class providing audit fields."""

    class Meta:
        abstract: bool = True

    def __init__(self, *args, **kwargs):
        self.created_at: Optional[date] = kwargs.get('created_at', None)
        self.updated_at: Optional[date] = kwargs.get('updated_at', None)
        self.created_by: Optional[Any] = kwargs.get('created_by', None)
        self.modified_by: Optional[Any] = kwargs.get('modified_by', None)


# ============================================================
# apps/users/models.py
# ============================================================

class CustomUserManager:
    """Manager for User model."""

    def __init__(self):
        self._model = None

    def create_user(self, email: str, password: str) -> 'User':
        if not email:
            raise ValueError("Users must have an email address")
        user = User(email=email)
        user.set_password(password)
        user.is_active = True
        user.is_admin = False
        user.is_staff = False
        user.is_student = True
        return user

    def create_superuser(self, email: str, password: str) -> 'User':
        user = self.create_user(email=email, password=password)
        user.is_admin = True
        user.is_staff = True
        user.is_student = False
        return user


class User:
    """Custom user model using email as the username field."""

    USERNAME_FIELD: str = 'email'
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: str, **kwargs):
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

    def has_perm(self, perm: str, obj: Optional[Any] = None) -> bool:
        return self.is_admin

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_admin

    def __repr__(self) -> str:
        return f"User(email={self.email!r})"

    def __str__(self) -> str:
        return self.email


class UserProfile:
    """Profile information for a User."""

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
        return f"UserProfile(user={self.user!r})"

    def __str__(self) -> str:
        return f"Profile of {self.user}"


# ============================================================
# apps/certificates/models.py
# ============================================================

class Certificate(AbstractTableMeta):
    """Certificate model."""

    def __init__(self, name: str, description: str = '', **kwargs):
        super().__init__(**kwargs)
        self.name: str = name
        self.description: str = description

    def __repr__(self) -> str:
        return f"Certificate(name={self.name!r})"

    def __str__(self) -> str:
        return self.name


# ============================================================
# apps/lectures/models.py
# ============================================================

class Lecture(AbstractTableMeta):
    """Lecture model."""

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title: str = title
        self.date: Optional[date] = kwargs.get('date', None)
        self.description: str = kwargs.get('description', '')
        self.duration: int = kwargs.get('duration', 0)
        self.lecturer_name: str = kwargs.get('lecturer_name', '')
        self.level: int = kwargs.get('level', 1)
        self.required: bool = kwargs.get('required', False)
        self.slides_url: str = kwargs.get('slides_url', '')

    def __repr__(self) -> str:
        return f"Lecture(title={self.title!r})"

    def __str__(self) -> str:
        return self.title


class Attendance(AbstractTableMeta):
    """Attendance record linking a student to a lecture."""

    def __init__(self, lecture: Lecture, student: User, **kwargs):
        super().__init__(**kwargs)
        self.lecture: Lecture = lecture
        self.student: User = student

    def __repr__(self) -> str:
        return f"Attendance(lecture={self.lecture!r}, student={self.student!r})"

    def __str__(self) -> str:
        return f"{self.student} attended {self.lecture}"


# ============================================================
# apps/projects/models.py
# ============================================================

class Project(AbstractTableMeta):
    """Project model."""

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title: str = title
        self.desription: str = kwargs.get('desription', '')
        self.level: int = kwargs.get('level', 1)
        self.required: bool = kwargs.get('required', False)
        self.url: str = kwargs.get('url', '')

    def __repr__(self) -> str:
        return f"Project(title={self.title!r})"

    def __str__(self) -> str:
        return self.title


# ============================================================
# apps/submissions/models.py
# ============================================================

class StudentSubmission(AbstractTableMeta):
    """Student submission for a project."""

    def __init__(self, project: Project, student: User, url: str = '', **kwargs):
        super().__init__(**kwargs)
        self.project: Project = project
        self.student: User = student
        self.url: str = url
        self.approved: bool = kwargs.get('approved', False)
        self.feedback: str = kwargs.get('feedback', '')

    def __repr__(self) -> str:
        return f"StudentSubmission(project={self.project!r}, student={self.student!r})"

    def __str__(self) -> str:
        return f"{self.student} submission for {self.project}"


# ============================================================
# apps/volunteers/models.py
# ============================================================

class Volunteer:
    """Volunteer model."""

    def __init__(self, email: str, first_name: str, last_name: str, **kwargs):
        self.email: str = email
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.hours_available: str = kwargs.get('hours_available', '')

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"Volunteer(email={self.email!r})"

    def __str__(self) -> str:
        return self.full_name


class VolunteerHours:
    """Hours logged by a volunteer."""

    class Meta:
        verbose_name_plural: str = 'Volunteer Hours'

    def __init__(self, volunteer: Volunteer, start: datetime, end: datetime, **kwargs):
        self.volunteer: Volunteer = volunteer
        self.start: datetime = start
        self.end: datetime = end

    def __repr__(self) -> str:
        return f"VolunteerHours(volunteer={self.volunteer!r}, start={self.start!r}, end={self.end!r})"

    def __str__(self) -> str:
        return f"{self.volunteer} hours from {self.start} to {self.end}"


# ============================================================
# apps/waitlist/models.py
# ============================================================

class WaitlistEntry(AbstractTableMeta):
    """Waitlist entry for prospective students."""

    class Meta:
        verbose_name_plural: str = 'Waitlist Entries'

    def __init__(self, email: str, first_name: str, last_name: str, **kwargs):
        super().__init__(**kwargs)
        self.email: str = email
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.level: int = kwargs.get('level', 1)
        self.notes: str = kwargs.get('notes', '')

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"WaitlistEntry(email={self.email!r})"

    def __str__(self) -> str:
        return self.full_name()