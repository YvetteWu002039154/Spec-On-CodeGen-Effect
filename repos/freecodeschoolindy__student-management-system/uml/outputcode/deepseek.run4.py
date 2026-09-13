from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings


class AbstractTableMeta(models.Model):
    created_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_at = models.DateField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.__class__.__name__} object ({self.pk})'


class Lecture(AbstractTableMeta):
    date = models.DateField()
    description = models.TextField()
    duration = models.IntegerField()
    lecturer_name = models.CharField(max_length=255)
    level = models.IntegerField()
    required = models.BooleanField()
    slides_url = models.CharField(max_length=255)
    title = models.CharField(max_length=255)


class Attendance(AbstractTableMeta):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendances')


class Certificate(AbstractTableMeta):
    description = models.TextField()
    name = models.CharField(max_length=255)


class Project(AbstractTableMeta):
    desription = models.TextField()
    level = models.IntegerField()
    required = models.BooleanField()
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255)


class StudentSubmission(AbstractTableMeta):
    approved = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    url = models.CharField(max_length=255)


class WaitlistEntry(AbstractTableMeta):
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    level = models.IntegerField()
    notes = models.TextField()

    class Meta:
        verbose_name_plural = "Waitlist entries"

    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class Volunteer(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    hours_available = models.TextField()

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return self.full_name


class VolunteerHours(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='volunteer_hours')

    class Meta:
        verbose_name_plural = "Volunteer hours"

    def __str__(self):
        return f'{self.volunteer.full_name} ({self.start} - {self.end})'


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_student', False)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    USERNAME_FIELD = 'email'
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
    objects = CustomUserManager()

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_staff

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    LEVELS = (
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar_url = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    codepen_username = models.CharField(max_length=255, blank=True)
    current_level = models.IntegerField(choices=LEVELS, default=1)
    discord_name = models.CharField(max_length=255, blank=True)
    fcc_profile_url = models.CharField(max_length=255, blank=True)
    github_username = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True)
    preferred_name = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.email