from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import datetime, date


class AbstractTableMeta(models.Model):
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_%(class)s_set',
    )
    modified_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_%(class)s_set',
    )

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
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'email'

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    objects = CustomUserManager()

    def has_perm(self, perm, obj=None):
        return super().has_perm(perm, obj=obj)

    def has_module_perms(self, app_label):
        return super().has_module_perms(app_label)


class UserProfile(models.Model):
    LEVELS = (
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=255)
    preferred_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    timezone = models.CharField(max_length=100, blank=True, null=True)
    avatar_url = models.CharField(max_length=500, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    github_username = models.CharField(max_length=150, blank=True, null=True)
    codepen_username = models.CharField(max_length=150, blank=True, null=True)
    fcc_profile_url = models.CharField(max_length=500, blank=True, null=True)
    discord_name = models.CharField(max_length=150, blank=True, null=True)
    current_level = models.IntegerField(choices=LEVELS, default=1)

    def __str__(self):
        return f"Profile of {self.user.email}"


class Lecture(AbstractTableMeta):
    title = models.CharField(max_length=255)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(help_text='Duration in minutes')
    lecturer_name = models.CharField(max_length=255)
    level = models.IntegerField()
    required = models.BooleanField(default=False)
    slides_url = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.date})"


class Attendance(AbstractTableMeta):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')

    class Meta:
        unique_together = ('lecture', 'student')

    def __str__(self):
        return f"{self.student.email} - {self.lecture.title}"


class Project(AbstractTableMeta):
    title = models.CharField(max_length=255)
    desription = models.TextField(blank=True, null=True)  # note field name is 'desription' as given
    level = models.IntegerField()
    required = models.BooleanField(default=False)
    url = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.title


class StudentSubmission(AbstractTableMeta):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    url = models.CharField(max_length=500)
    feedback = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('project', 'student')

    def __str__(self):
        return f"{self.student.email} - {self.project.title}"


class Certificate(AbstractTableMeta):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Volunteer(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    hours_available = models.TextField(blank=True, null=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name or self.email


class VolunteerHours(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='hours')
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        verbose_name_plural = 'Volunteer hours'

    def __str__(self):
        return f"{self.volunteer.full_name}: {self.start} - {self.end}"


class WaitlistEntry(AbstractTableMeta):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    level = models.IntegerField()
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Waitlist entries'

    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name() or self.email