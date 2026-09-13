from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils import timezone


class AbstractTableMeta(models.Model):
    created_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='+',
        null=True,  # typically set during save, but we can allow null
        blank=True,
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='+',
        null=True,
        blank=True,
    )
    updated_at = models.DateField(auto_now=True)

    class Meta:
        abstract = True


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_admin', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'email'
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_student = models.BooleanField(default=True)

    objects = CustomUserManager()

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin


class UserProfile(models.Model):
    LEVELS = (
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar_url = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    codepen_username = models.CharField(max_length=100, blank=True)
    current_level = models.IntegerField(choices=LEVELS, default=1)
    discord_name = models.CharField(max_length=100, blank=True)
    fcc_profile_url = models.CharField(max_length=200, blank=True)
    github_username = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)


class Lecture(AbstractTableMeta):
    date = models.DateField()
    description = models.TextField()
    duration = models.IntegerField()
    lecturer_name = models.CharField(max_length=200)
    level = models.IntegerField()
    required = models.BooleanField()
    slides_url = models.CharField(max_length=200)
    title = models.CharField(max_length=200)


class Attendance(AbstractTableMeta):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


class Project(AbstractTableMeta):
    description = models.TextField()  # corrected from 'desription'
    level = models.IntegerField()
    required = models.BooleanField()
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=200)


class Certificate(AbstractTableMeta):
    description = models.TextField()
    name = models.CharField(max_length=200)


class StudentSubmission(AbstractTableMeta):
    approved = models.BooleanField()
    feedback = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    url = models.CharField(max_length=200)


class Volunteer(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    hours_available = models.TextField()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class VolunteerHours(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Volunteer hours"


class WaitlistEntry(AbstractTableMeta):
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    level = models.IntegerField()
    notes = models.TextField()

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name_plural = "Waitlist entries"