from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from typing import List, Optional, Any


class CustomUserManager(BaseUserManager):
    def create_user(self, email: str, password: Optional[str] = None, **extra_fields: Any) -> 'CustomUser':
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: Optional[str] = None, **extra_fields: Any) -> 'CustomUser':
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 1)  # Admin type

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    GENDER: List[tuple] = [('Male', 'Male'), ('Female', 'Female')]
    USER_TYPE: tuple = (
        (1, 'Admin'),
        (2, 'Staff'),
        (3, 'Student'),
    )
    REQUIRED_FIELDS: List[str] = ['user_type', 'gender']
    USERNAME_FIELD: str = 'email'

    email = models.EmailField(unique=True)
    username = None  # type: NoneType
    user_type = models.CharField(max_length=10, choices=USER_TYPE, default=1)
    gender = models.CharField(max_length=10, choices=GENDER)
    address = models.TextField(blank=True, null=True)
    fcm_token = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: CustomUserManager = CustomUserManager()

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return self.email

    def get_short_name(self) -> str:
        return self.email


class Session(models.Model):
    start_year = models.DateField()
    end_year = models.DateField()

    def __str__(self) -> str:
        return f"{self.start_year.year} - {self.end_year.year}"


class Course(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')

    def __str__(self) -> str:
        return self.admin.email


class Staff(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='staff_members')

    def __str__(self) -> str:
        return self.admin.email


class Student(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='students')

    def __str__(self) -> str:
        return self.admin.email


class Subject(models.Model):
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='subjects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Attendance(models.Model):
    date = models.DateField()
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendances')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.subject.name} - {self.date}"


class AttendanceReport(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='reports')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_reports')
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.student.admin.email} - {self.attendance.date} - {'Present' if self.status else 'Absent'}"


class FeedbackStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='feedbacks')
    feedback = models.TextField()
    reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Feedback from {self.staff.admin.email}"


class FeedbackStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='feedbacks')
    feedback = models.TextField()
    reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Feedback from {self.student.admin.email}"


class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='leave_reports')
    date = models.CharField(max_length=255)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)  # 0 pending, 1 approved, 2 rejected
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Leave report by {self.staff.admin.email}"


class LeaveReportStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='leave_reports')
    date = models.CharField(max_length=255)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Leave report by {self.student.admin.email}"


class NotificationStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Notification for {self.staff.admin.email}"


class NotificationStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Notification for {self.student.admin.email}"


class StudentResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_results')
    test = models.FloatField(default=0)
    exam = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.student.admin.email} - {self.subject.name} - Test: {self.test}, Exam: {self.exam}"