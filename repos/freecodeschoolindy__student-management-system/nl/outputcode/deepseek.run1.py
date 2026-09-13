import os
import django
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.contrib import admin
from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# =============================================================================
# settings.py snippet (to be placed in project settings)
# =============================================================================
# AUTH_USER_MODEL = 'student_management.User'
# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': [
#         'rest_framework.authentication.SessionAuthentication',
#         'rest_framework.authentication.BasicAuthentication',
#     ],
#     'DEFAULT_PERMISSION_CLASSES': [
#         'rest_framework.permissions.IsAuthenticated',
#     ]
# }

# =============================================================================
# models.py
# =============================================================================
class UserManager(BaseUserManager):
    """Custom manager for User model."""
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
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.ORGANIZER)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    STUDENT = 'student'
    ORGANIZER = 'organizer'
    ROLE_CHOICES = [
        (STUDENT, 'Student'),
        (ORGANIZER, 'Organizer'),
    ]
    username = None  # Remove default username
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=STUDENT)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.role == self.ORGANIZER:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    full_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    github_profile = models.URLField(blank=True)
    linkedin_profile = models.URLField(blank=True)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=50, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    enrolled_since = models.DateField(null=True, blank=True)
    last_active = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Profile of {self.user.email}"

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"


class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class StudentProgress(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='progress',
        limit_choices_to={'role': User.STUDENT}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress')
    completion_percentage = models.PositiveSmallIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    outcomes = models.TextField(blank=True, help_text="Learning outcomes or achievements")
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.completion_percentage > 100:
            self.completion_percentage = 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.email} - {self.course.code}: {self.completion_percentage}%"

    class Meta:
        verbose_name = "Student Progress"
        verbose_name_plural = "Student Progress"
        unique_together = ['student', 'course']


class Volunteer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='volunteer',
        limit_choices_to={'role': User.ORGANIZER}
    )
    availability = models.TextField(blank=True, help_text="General availability schedule")
    skills = models.TextField(blank=True, help_text="Relevant skills (e.g., mentoring, tutoring)")
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Volunteer: {self.user.email}"

    class Meta:
        verbose_name = "Volunteer"
        verbose_name_plural = "Volunteers"


class WaitlistEntry(models.Model):
    PENDING = 'pending'
    NOTIFIED = 'notified'
    ENROLLED = 'enrolled'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (NOTIFIED, 'Notified'),
        (ENROLLED, 'Enrolled'),
        (REJECTED, 'Rejected'),
    ]
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='waitlist_entries',
        limit_choices_to={'role': User.STUDENT}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='waitlist')
    position = models.PositiveIntegerField(editable=False)
    added_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    class Meta:
        ordering = ['course', 'position']
        unique_together = ['student', 'course']
        verbose_name = "Waitlist Entry"
        verbose_name_plural = "Waitlist Entries"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            # Assign next available position for this course
            last = WaitlistEntry.objects.filter(course=self.course).order_by('position').last()
            self.position = last.position + 1 if last else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Waitlist #{self.position}: {self.student.email} for {self.course.code} ({self.get_status_display()})"


# Signal to create StudentProfile when a student user is created
@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created and instance.role == User.STUDENT:
        StudentProfile.objects.create(user=instance)


# =============================================================================
# admin.py
# =============================================================================
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'country', 'enrolled_since', 'last_active')
    search_fields = ('user__email', 'full_name')
    list_filter = ('country',)


class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'completion_percentage', 'last_updated')
    list_filter = ('course',)
    search_fields = ('student__email', 'course__title')


class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'joined_date')
    search_fields = ('user__email', 'skills')
    list_filter = ('is_active',)


class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('position', 'student', 'course', 'status', 'added_at')
    list_filter = ('course', 'status')
    search_fields = ('student__email', 'course__title')


class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'is_active', 'created_at')
    search_fields = ('code', 'title')


admin.site.register(User)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(StudentProgress, StudentProgressAdmin)
admin.site.register(Volunteer, VolunteerAdmin)
admin.site.register(WaitlistEntry, WaitlistEntryAdmin)


# =============================================================================
# permissions.py (custom permissions for API)
# =============================================================================
class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to view/edit.
    """
    def has_object_permission(self, request, view, obj):
        # Admin/organizer can always access
        if request.user.is_staff or request.user.role == User.ORGANIZER:
            return True
        # For student profile, check if obj.user equals request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # For other objects that have a direct user field
        if hasattr(obj, 'student'):
            return obj.student == request.user
        return False


# =============================================================================
# serializers.py
# =============================================================================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined']
        read_only_fields = ['email', 'date_joined']


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'


class StudentProgressSerializer(serializers.ModelSerializer):
    student_email = serializers.ReadOnlyField(source='student.email')
    course_code = serializers.ReadOnlyField(source='course.code')

    class Meta:
        model = StudentProgress
        fields = ['id', 'student', 'course', 'completion_percentage', 'last_updated',
                  'outcomes', 'notes', 'student_email', 'course_code']
        read_only_fields = ['student']  # student set automatically in view


class VolunteerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Volunteer
        fields = '__all__'


class WaitlistEntrySerializer(serializers.ModelSerializer):
    student_email = serializers.ReadOnlyField(source='student.email')
    course_code = serializers.ReadOnlyField(source='course.code')

    class Meta:
        model = WaitlistEntry
        fields = ['id', 'student', 'course', 'position', 'added_at', 'status',
                  'student_email', 'course_code']
        read_only_fields = ['position', 'added_at', 'student']  # student set in view


# =============================================================================
# views.py (API endpoints using Django REST Framework)
# =============================================================================
class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == User.ORGANIZER:
            return StudentProfile.objects.all()
        return StudentProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Organizers can create/update, students can read only
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()


class StudentProgressViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == User.ORGANIZER:
            return StudentProgress.objects.all()
        return StudentProgress.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        # Ensure the current user is set as student (student role)
        if self.request.user.role != User.STUDENT and not self.request.user.is_staff:
            raise permissions.PermissionDenied("Only students can create progress entries.")
        serializer.save(student=self.request.user)


class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == User.ORGANIZER:
            return Volunteer.objects.all()
        return Volunteer.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != User.ORGANIZER and not self.request.user.is_staff:
            raise permissions.PermissionDenied("Only organizers can be volunteers.")
        serializer.save(user=self.request.user)


class WaitlistEntryViewSet(viewsets.ModelViewSet):
    serializer_class = WaitlistEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role == User.ORGANIZER:
            return WaitlistEntry.objects.all()
        return WaitlistEntry.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != User.STUDENT and not self.request.user.is_staff:
            raise permissions.PermissionDenied("Only students can join a waitlist.")
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        """Custom action for admins to change waitlist status."""
        entry = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(WaitlistEntry.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        entry.status = new_status
        entry.save()
        return Response(WaitlistEntrySerializer(entry).data)


# =============================================================================
# urls.py
# =============================================================================
router = DefaultRouter()
router.register(r'profiles', StudentProfileViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'progress', StudentProgressViewSet)
router.register(r'volunteers', VolunteerViewSet)
router.register(r'waitlist', WaitlistEntryViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    # Authentication endpoints are provided by Django (e.g., /api-auth/login/)
    path('api-auth/', include('rest_framework.urls')),
]

# =============================================================================
# settings.py (relevant configuration)
# =============================================================================
# Add the following lines to your Django project's settings.py:
# INSTALLED_APPS = [
#     ...,
#     'rest_framework',
#     'student_management',  # Your app name
# ]
# AUTH_USER_MODEL = 'student_management.User'
# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'
# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': [
#         'rest_framework.authentication.SessionAuthentication',
#         'rest_framework.authentication.BasicAuthentication',
#     ],
#     'DEFAULT_PERMISSION_CLASSES': [
#         'rest_framework.permissions.IsAuthenticated',
#     ]
# }