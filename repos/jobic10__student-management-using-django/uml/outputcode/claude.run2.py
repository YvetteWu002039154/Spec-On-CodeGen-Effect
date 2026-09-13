from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email: str, password: str, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "1")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    USER_TYPE = (
        ("1", "Admin"),
        ("2", "Staff"),
        ("3", "Student"),
    )
    GENDER = [
        ("M", "Male"),
        ("F", "Female"),
    ]
    REQUIRED_FIELDS = []
    USERNAME_FIELD = "email"

    username = None
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=1, choices=USER_TYPE, default="1")
    gender = models.CharField(max_length=1, choices=GENDER, blank=True)
    profile_pic = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    address = models.TextField(blank=True)
    fcm_token = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Admin(models.Model):
    admin = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="admin_profile"
    )

    def __str__(self):
        return str(self.admin)


class Course(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Session(models.Model):
    start_year = models.DateField()
    end_year = models.DateField()

    def __str__(self):
        return f"{self.start_year} - {self.end_year}"


class Staff(models.Model):
    admin = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="staff_profile"
    )
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="staffs"
    )

    def __str__(self):
        return str(self.admin)


class Student(models.Model):
    admin = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="student_profile"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    def __str__(self):
        return str(self.admin)


class Subject(models.Model):
    name = models.CharField(max_length=255)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subjects"
    )
    staff = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="subjects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="attendances"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="attendances"
    )
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - {self.date}"


class AttendanceReport(models.Model):
    attendance = models.ForeignKey(
        Attendance, on_delete=models.CASCADE, related_name="reports"
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendance_reports"
    )
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.attendance} - {self.status}"


class FeedbackStaff(models.Model):
    staff = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="feedbacks"
    )
    feedback = models.TextField()
    reply = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feedback from {self.staff}"


class FeedbackStudent(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="feedbacks"
    )
    feedback = models.TextField()
    reply = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feedback from {self.student}"


class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="leave_reports"
    )
    date = models.CharField(max_length=255)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Leave report from {self.staff} on {self.date}"


class LeaveReportStudent(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="leave_reports"
    )
    date = models.CharField(max_length=255)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Leave report from {self.student} on {self.date}"


class NotificationStaff(models.Model):
    staff = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification for {self.staff}"


class NotificationStudent(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification for {self.student}"


class StudentResult(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="results"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="results"
    )
    test = models.FloatField(default=0.0)
    exam = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.subject} result"