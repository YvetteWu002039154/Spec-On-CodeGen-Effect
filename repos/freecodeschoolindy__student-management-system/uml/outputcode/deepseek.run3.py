from __future__ import annotations
from datetime import date, datetime
from typing import Optional, Any

# --------------------- Field definitions ---------------------
class Field:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.name: Optional[str] = None
        self.related_model: Optional[Any] = None
        self.related_model_name: Optional[str] = None
        if args:
            if isinstance(args[0], type):
                self.related_model = args[0]
            elif isinstance(args[0], str):
                self.related_model_name = args[0]
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"

class CharField(Field):      pass
class TextField(Field):      pass
class IntegerField(Field):   pass
class BooleanField(Field):   pass
class DateField(Field):      pass
class DateTimeField(Field):  pass
class EmailField(CharField): pass
class ForeignKey(Field):     pass
class OneToOneField(Field):  pass

# --------------------- Base model ---------------------
class ModelBase(type):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> type:
        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields: dict[str, Field] = {}
        for base in bases:
            if hasattr(base, '_fields'):
                cls._fields.update(base._fields)
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                attr_value.name = attr_name
                cls._fields[attr_name] = attr_value
        return cls

class Model(metaclass=ModelBase):
    def __init__(self, **kwargs: Any) -> None:
        for field_name in self._fields:
            setattr(self, field_name, kwargs.get(field_name))
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} object>"

# --------------------- Abstract base ---------------------
class AbstractTableMeta(Model):
    created_at = DateField()
    updated_at = DateField()
    created_by = ForeignKey('User')
    modified_by = ForeignKey('User')

    class Meta:
        abstract: bool = True

# --------------------- User ---------------------
class User(Model):
    USERNAME_FIELD: str = 'email'
    email = EmailField()
    is_active = BooleanField()
    is_admin = BooleanField()
    is_staff = BooleanField()
    is_student = BooleanField()

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_staff or self.is_admin

    def has_perm(self, perm: str, obj: Optional[Any] = None) -> bool:
        return self.is_admin

    # objects will be set after manager definition

# --------------------- Custom user manager ---------------------
class CustomUserManager:
    def create_user(self, email: str, password: str) -> User:
        user = User(email=email, is_active=True, is_admin=False, is_staff=False, is_student=True)
        return user

    def create_superuser(self, email: str, password: str) -> User:
        user = User(email=email, is_active=True, is_admin=True, is_staff=True, is_student=False)
        return user

User.objects = CustomUserManager()

# --------------------- UserProfile ---------------------
class UserProfile(Model):
    LEVELS: tuple = ((0, 'Beginner'), (1, 'Intermediate'), (2, 'Advanced'))
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

# --------------------- Lecture ---------------------
class Lecture(AbstractTableMeta):
    date = DateField()
    description = TextField()
    duration = IntegerField()
    lecturer_name = CharField()
    level = IntegerField()
    required = BooleanField()
    slides_url = CharField()
    title = CharField()

# --------------------- Attendance ---------------------
class Attendance(AbstractTableMeta):
    lecture = ForeignKey('Lecture')
    student = ForeignKey('User')

# --------------------- Project ---------------------
class Project(AbstractTableMeta):
    desription = TextField()   # misspelling as per diagram
    level = IntegerField()
    required = BooleanField()
    title = CharField()
    url = CharField()

# --------------------- StudentSubmission ---------------------
class StudentSubmission(AbstractTableMeta):
    approved = BooleanField()
    feedback = TextField()
    project = ForeignKey('Project')
    student = ForeignKey('User')
    url = CharField()

# --------------------- Certificate ---------------------
class Certificate(AbstractTableMeta):
    description = TextField()
    name = CharField()

# --------------------- Volunteer ---------------------
class Volunteer(Model):
    email = EmailField()
    first_name = CharField()
    hours_available = TextField()
    last_name = CharField()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

# --------------------- VolunteerHours ---------------------
class VolunteerHours(Model):
    end = DateTimeField()
    start = DateTimeField()
    volunteer = ForeignKey('Volunteer')

    class Meta:
        verbose_name_plural: str = 'volunteer hours'

# --------------------- WaitlistEntry ---------------------
class WaitlistEntry(AbstractTableMeta):
    email = EmailField()
    first_name = CharField()
    last_name = CharField()
    level = IntegerField()
    notes = TextField()

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name_plural: str = 'waitlist entries'