import datetime
from typing import Optional, Any


class AbstractTableMeta:
    class Meta:
        abstract = True

    def __init__(self, created_by: Optional['User'] = None, modified_by: Optional['User'] = None):
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
        self.created_by = created_by
        self.modified_by = modified_by


class CustomUserManager:
    def create_user(self, email: str, password: str) -> 'User':
        user = User(email=email)
        user.password = password
        user.is_student = True
        user.is_active = True
        user.is_admin = False
        user.is_staff = False
        return user

    def create_superuser(self, email: str, password: str) -> 'User':
        user = User(email=email)
        user.password = password
        user.is_admin = True
        user.is_staff = True
        user.is_student = False
        user.is_active = True
        return user


class User:
    USERNAME_FIELD = 'email'
    objects = CustomUserManager()

    def __init__(self, email: str = '', is_active: bool = True, is_admin: bool = False, is_staff: bool = False, is_student: bool = False):
        self.email = email
        self.is_active = is_active
        self.is_admin = is_admin
        self.is_staff = is_staff
        self.is_student = is_student
        self.password = ''

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return self.is_admin

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_staff or self.is_admin


class UserProfile:
    LEVELS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

    def __init__(self, user: User, name: str = '', preferred_name: str = '', avatar_url: str = '', bio: str = '',
                 codepen_username: str = '', current_level: int = 1, discord_name: str = '', fcc_profile_url: str = '',
                 github_username: str = '', phone: str = '', timezone: str = ''):
        self.user = user
        self.name = name
        self.preferred_name = preferred_name
        self.avatar_url = avatar_url
        self.bio = bio
        self.codepen_username = codepen_username
        self.current_level = current_level
        self.discord_name = discord_name
        self.fcc_profile_url = fcc_profile_url
        self.github_username = github_username
        self.phone = phone
        self.timezone = timezone


class Certificate(AbstractTableMeta):
    def __init__(self, name: str = '', description: str = '', **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.description = description


class Lecture(AbstractTableMeta):
    def __init__(self, title: str = '', description: str = '', lecturer_name: str = '', slides_url: str = '',
                 date: Optional[datetime.date] = None, duration: int = 0, level: int = 1, required: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.lecturer_name = lecturer_name
        self.slides_url = slides_url
        self.date = date or datetime.date.today()
        self.duration = duration
        self.level = level
        self.required = required


class Attendance(AbstractTableMeta):
    def __init__(self, lecture: Optional[Lecture] = None, student: Optional[User] = None, **kwargs):
        super().__init__(**kwargs)
        self.lecture = lecture
        self.student = student


class Project(AbstractTableMeta):
    def __init__(self, title: str = '', desription: str = '', url: str = '', level: int = 1, required: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.desription = desription
        self.url = url
        self.level = level
        self.required = required


class StudentSubmission(AbstractTableMeta):
    def __init__(self, student: Optional[User] = None, project: Optional[Project] = None, url: str = '',
                 approved: bool = False, feedback: str = '', **kwargs):
        super().__init__(**kwargs)
        self.student = student
        self.project = project
        self.url = url
        self.approved = approved
        self.feedback = feedback


class Volunteer:
    def __init__(self, email: str = '', first_name: str = '', last_name: str = '', hours_available: str = ''):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.hours_available = hours_available

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class VolunteerHours:
    class Meta:
        verbose_name_plural = "Volunteer hours"

    def __init__(self, volunteer: Optional[Volunteer] = None, start: Optional[datetime.datetime] = None, end: Optional[datetime.datetime] = None):
        self.volunteer = volunteer
        self.start = start or datetime.datetime.now()
        self.end = end or datetime.datetime.now()


class WaitlistEntry(AbstractTableMeta):
    class Meta:
        verbose_name_plural = "Waitlist entries"

    def __init__(self, email: str = '', first_name: str = '', last_name: str = '', level: int = 1, notes: str = '', **kwargs):
        super().__init__(**kwargs)
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.level = level
        self.notes = notes

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"