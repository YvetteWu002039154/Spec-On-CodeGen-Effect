from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings


# apps.utils.models
class AbstractTableMeta(models.Model):
    created_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        editable=False,
    )
    updated_at = models.DateField(auto_now=True)

    class Meta:
        abstract = True


# apps.users.models
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
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    USERNAME_FIELD = 'email'
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_student = models.BooleanField(default=True)

    objects = CustomUserManager()

    def has_perm(self, perm, obj=None):
        return self.is_admin or (self.is_active and super().has_perm(perm, obj))

    def has_module_perms(self, app_label):
        return self.is_admin or (self.is_active and self.is_staff)

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email.split('@')[0]


class UserProfile(models.Model):
    LEVELS = (
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
        (5, 'Level 5'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar_url = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    codepen_username = models.CharField(max_length=150, blank=True)
    current_level = models.IntegerField(choices=LEVELS, default=1)
    discord_name = models.CharField(max_length=150, blank=True)
    fcc_profile_url = models.CharField(max_length=255, blank=True)
    github_username = models.CharField(max_length=150, blank=True)
    name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_name = models.CharField(max_length=150, blank=True)
    timezone = models.CharField(max_length=50, blank=True)


# apps.lectures.models
class Lecture(AbstractTableMeta):
    date = models.DateField()
    description = models.TextField()
    duration = models.IntegerField()
    lecturer_name = models.CharField(max_length=255)
    level = models.IntegerField()
    required = models.BooleanField(default=True)
    slides_url = models.CharField(max_length=255)
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Attendance(AbstractTableMeta):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student} attended {self.lecture}"


# apps.certificates.models
class Certificate(AbstractTableMeta):
    description = models.TextField()
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# apps.projects.models
class Project(AbstractTableMeta):
    desription = models.TextField()  # intentional typo from diagram
    level = models.IntegerField()
    required = models.BooleanField(default=True)
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255)

    def __str__(self):
        return self.title


# apps.submissions.models
class StudentSubmission(AbstractTableMeta):
    approved = models.BooleanField(default=False)
    feedback = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    url = models.CharField(max_length=255)

    def __str__(self):
        return f"Submission by {self.student} for {self.project}"


# apps.waitlist.models
class WaitlistEntry(AbstractTableMeta):
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    level = models.IntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Waitlist Entries'

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name()


# apps.volunteers.models
class Volunteer(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    hours_available = models.TextField()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class VolunteerHours(models.Model):
    end = models.DateTimeField()
    start = models.DateTimeField()
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Volunteer Hours'

    def __str__(self):
        return f"{self.volunteer} {self.start} - {self.end}"