from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


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
    is_student = models.BooleanField(default=False)
    objects = CustomUserManager()

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin


class AbstractTableMeta(models.Model):
    created_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_created'
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_modified'
    )
    updated_at = models.DateField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(models.Model):
    LEVELS = ((1, '1'), (2, '2'), (3, '3'))  # placeholder levels
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar_url = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    codepen_username = models.CharField(max_length=100, blank=True)
    current_level = models.IntegerField(default=1)
    discord_name = models.CharField(max_length=100, blank=True)
    fcc_profile_url = models.CharField(max_length=255, blank=True)
    github_username = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)


class Certificate(AbstractTableMeta):
    description = models.TextField(blank=True)
    name = models.CharField(max_length=255)


class Lecture(AbstractTableMeta):
    date = models.DateField()
    description = models.TextField(blank=True)
    duration = models.IntegerField()
    lecturer_name = models.CharField(max_length=255)
    level = models.IntegerField()
    required = models.BooleanField(default=False)
    slides_url = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)


class Attendance(AbstractTableMeta):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)


class Project(AbstractTableMeta):
    desription = models.TextField(blank=True)  # matched spec typo
    level = models.IntegerField()
    required = models.BooleanField(default=False)
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)


class StudentSubmission(AbstractTableMeta):
    approved = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.CharField(max_length=255, blank=True)


class Volunteer(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    hours_available = models.TextField(blank=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class VolunteerHours(models.Model):
    end = models.DateTimeField()
    start = models.DateTimeField()
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Volunteer Hours"


class WaitlistEntry(AbstractTableMeta):
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    level = models.IntegerField()
    notes = models.TextField(blank=True)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name_plural = "Waitlist Entries"