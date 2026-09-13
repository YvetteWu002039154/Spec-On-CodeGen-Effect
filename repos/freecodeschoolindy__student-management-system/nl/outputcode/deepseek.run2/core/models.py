from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')

    def save(self, *args, **kwargs):
        if self.user_type in ['organizer', 'admin']:
            self.is_staff = True
        if self.user_type == 'admin':
            self.is_superuser = True
        super().save(*args, **kwargs)

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    bio = models.TextField(blank=True)
    organization = models.CharField(max_length=100, blank=True)
    skills = models.TextField(blank=True)
    enrollment_status = models.CharField(max_length=50, blank=True, help_text="e.g., active, paused, completed")

    def __str__(self):
        return f"Profile of {self.user.username}"

class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    grade = models.CharField(max_length=10, blank=True)
    enrollment_date = models.DateTimeField(default=timezone.now)
    completion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} - {self.course.name} ({self.status})"

class Waitlist(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlist_entries')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='waitlist_entries')
    date_joined = models.DateTimeField(auto_now_add=True)
    position = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"Waitlist: {self.student.username} for {self.course.name}"

class Volunteer(models.Model):
    ROLE_CHOICES = (
        ('mentor', 'Mentor'),
        ('grader', 'Grader'),
        ('instructor', 'Instructor'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteer_roles')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='volunteers', null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='mentor')
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.role} ({self.course.name if self.course else 'N/A'})"
