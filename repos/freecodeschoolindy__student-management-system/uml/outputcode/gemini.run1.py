from typing import Any, Tuple

class Field:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

class DateField(Field): pass
class DateTimeField(Field): pass
class TextField(Field): pass
class CharField(Field): pass
class IntegerField(Field): pass
class BooleanField(Field): pass
class EmailField(Field): pass
class ForeignKey(Field): pass
class OneToOneField(Field): pass

class CustomUserManager:
    def create_user(self, email: str, password: str) -> 'User':
        user = User()
        return user

    def create_superuser(self, email: str, password: str) -> 'User':
        user = self.create_user(email, password)
        return user

class User:
    USERNAME_FIELD: str = 'email'
    email = EmailField()
    is_active = BooleanField()
    is_admin = BooleanField()
    is_staff = BooleanField()
    is_student = BooleanField()
    
    objects = CustomUserManager()

    def has_module_perms(self, app_label: str) -> bool:
        return True

    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return True

class AbstractTableMeta:
    created_at = DateField()
    created_by = ForeignKey('User')
    modified_by = ForeignKey('User')
    updated_at = DateField()

    class Meta:
        abstract: bool = True

class Attendance(AbstractTableMeta):
    lecture = ForeignKey('Lecture')
    student = ForeignKey('User')

class Certificate(AbstractTableMeta):
    description = TextField()
    name = CharField()

class Lecture(AbstractTableMeta):
    date = DateField()
    description = TextField()
    duration = IntegerField()
    lecturer_name = CharField()
    level = IntegerField()
    required = BooleanField()
    slides_url = CharField()
    title = CharField()

class Project(AbstractTableMeta):
    desription = TextField()
    level = IntegerField()
    required = BooleanField()
    title = CharField()
    url = CharField()

class StudentSubmission(AbstractTableMeta):
    approved = BooleanField()
    feedback = TextField()
    project = ForeignKey('Project')
    student = ForeignKey('User')
    url = CharField()

class UserProfile:
    LEVELS: Tuple = ()
    avatar_url = CharField()
    bio = TextField()
    codepen_username = CharField()
    current_level = IntegerField()
    discord_name = CharField()
    fcc_profile_url = CharField()
    github_username = CharField()
    name = CharField()
    phone = CharField()
    preferred_name = CharField()
    timezone = CharField()
    user = OneToOneField('User')

class Volunteer:
    email = EmailField()
    first_name = CharField()
    hours_available = TextField()
    last_name = CharField()

    @property
    def full_name(self) -> str:
        return f"{getattr(self, 'first_name', '')} {getattr(self, 'last_name', '')}".strip()

class VolunteerHours:
    end = DateTimeField()
    start = DateTimeField()
    volunteer = ForeignKey('Volunteer')

    class Meta:
        verbose_name_plural: str = "Volunteer Hours"

class WaitlistEntry(AbstractTableMeta):
    email = EmailField()
    first_name = CharField()
    last_name = CharField()
    level = IntegerField()
    notes = TextField()

    class Meta:
        verbose_name_plural: str = "Waitlist Entries"

    def full_name(self) -> str:
        return f"{getattr(self, 'first_name', '')} {getattr(self, 'last_name', '')}".strip()