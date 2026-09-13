from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class AbstractTableMeta(models.Model):
    created_at = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    modified_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
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

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    LEVELS = (
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
        (5, 'Level 5'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar_url = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    codepen_username = models.CharField(max_length=100, blank=True)
    current_level = models.IntegerField(choices=LEVELS, default=1)
    discord_name = models.CharField(max_length=100, blank=True)
    fcc_profile_url = models.CharField(max_length=255, blank=True)
    github_username = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.email} Profile"


class Volunteer(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    hours_available = models.TextField(blank=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class VolunteerHours(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='hours')
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        verbose_name_plural = 'volunteer hours'

    def __str__(self):
        return f"{self.volunteer.full_name} {self.start} - {self.end}"


class WaitlistEntry(AbstractTableMeta):
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    level = models.IntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'waitlist entries'

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name()


class Lecture(AbstractTableMeta):
    date = models.DateField()
    description = models.TextField(blank=True)
    duration = models.IntegerField()
    lecturer_name = models.CharField(max_length=200)
    level = models.IntegerField()
    required = models.BooleanField(default=False)
    slides_url = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Attendance(AbstractTableMeta):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='attendees')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')

    class Meta:
        unique_together = ('lecture', 'student')

    def __str__(self):
        return f"{self.student.email} @ {self.lecture.title}"


class Project(AbstractTableMeta):
    desription = models.TextField(blank=True)
    level = models.IntegerField()
    required = models.BooleanField(default=False)
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class StudentSubmission(AbstractTableMeta):
    approved = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    url = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.student.email} - {self.project.title}"


class Certificate(AbstractTableMeta):
    description = models.TextField(blank=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name