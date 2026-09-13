from typing import Any, Tuple, Optional

class DateField: pass
class DateTimeField: pass
class CharField: pass
class TextField: pass
class IntegerField: pass
class BooleanField: pass
class EmailField: pass
class ForeignKey: pass
class OneToOneField: pass

class CustomUserManager:
    def create_superuser(self, email: str, password: str) -> 'User':
        pass

    def create_user(self, email: str, password: str) -> 'User':
        pass

class User:
    USERNAME_FIELD: str = 'email'
    objects: CustomUserManager = CustomUserManager()

    def __init__(self, email: EmailField, is_active: BooleanField, is_admin: BooleanField, is_staff: BooleanField, is_student: BooleanField):
        self.email = email
        self.is_active = is_active
        self.is_admin = is_admin
        self.is_staff = is_staff
        self.is_student = is_student

    def has_module_perms(self, app_label: str) -> bool:
        pass

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        pass

class AbstractTableMeta:
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField):
        self.created_at = created_at
        self.created_by = created_by
        self.modified_by = modified_by
        self.updated_at = updated_at

    class Meta:
        abstract: bool = True

class Attendance(AbstractTableMeta):
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField, lecture: ForeignKey, student: ForeignKey):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.lecture = lecture
        self.student = student

class Certificate(AbstractTableMeta):
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField, description: TextField, name: CharField):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.description = description
        self.name = name

class Lecture(AbstractTableMeta):
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField, date: DateField, description: TextField, duration: IntegerField, lecturer_name: CharField, level: IntegerField, required: BooleanField, slides_url: CharField, title: CharField):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.date = date
        self.description = description
        self.duration = duration
        self.lecturer_name = lecturer_name
        self.level = level
        self.required = required
        self.slides_url = slides_url
        self.title = title

class Project(AbstractTableMeta):
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField, desription: TextField, level: IntegerField, required: BooleanField, title: CharField, url: CharField):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.desription = desription
        self.level = level
        self.required = required
        self.title = title
        self.url = url

class StudentSubmission(AbstractTableMeta):
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField, approved: BooleanField, feedback: TextField, project: ForeignKey, student: ForeignKey, url: CharField):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.approved = approved
        self.feedback = feedback
        self.project = project
        self.student = student
        self.url = url

class UserProfile:
    LEVELS: Tuple = ()

    def __init__(self, avatar_url: CharField, bio: TextField, codepen_username: CharField, current_level: IntegerField, discord_name: CharField, fcc_profile_url: CharField, github_username: CharField, name: CharField, phone: CharField, preferred_name: CharField, timezone: CharField, user: OneToOneField):
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
        self.user = user

class Volunteer:
    def __init__(self, email: EmailField, first_name: CharField, hours_available: TextField, last_name: CharField):
        self.email = email
        self.first_name = first_name
        self.hours_available = hours_available
        self.last_name = last_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class VolunteerHours:
    def __init__(self, end: DateTimeField, start: DateTimeField, volunteer: ForeignKey):
        self.end = end
        self.start = start
        self.volunteer = volunteer

    class Meta:
        verbose_name_plural: str = "Volunteer Hours"

class WaitlistEntry(AbstractTableMeta):
    def __init__(self, created_at: DateField, created_by: ForeignKey, modified_by: ForeignKey, updated_at: DateField, email: EmailField, first_name: CharField, last_name: CharField, level: IntegerField, notes: TextField):
        super().__init__(created_at, created_by, modified_by, updated_at)
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.level = level
        self.notes = notes

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name_plural: str = "Waitlist Entries"