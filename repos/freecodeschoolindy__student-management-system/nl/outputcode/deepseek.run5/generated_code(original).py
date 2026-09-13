# file: manage.py
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

# file: student_management_system/__init__.py
# (empty)

# file: student_management_system/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-in-production-^d$vx9&*9!%r2q)@_j(2kbk7nc6-w2k4i7@!%o$_l0@q3k5s'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'student_management_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'student_management_system.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# file: student_management_system/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
]

# file: student_management_system/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
application = get_wsgi_application()

# file: core/__init__.py
# (empty)

# file: core/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return self.username

class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        limit_choices_to={'role': 'student'},
    )
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    )
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='enrolled')
    enrolled_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student_profile', 'course')

    def __str__(self):
        return f"{self.student_profile.user.username} - {self.course.name}"

class JobPlacement(models.Model):
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='placements'
    )
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student_profile.user.username} at {self.company}"

class Volunteer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='volunteer_profile',
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    skills = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class WaitlistEntry(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    message = models.TextField(blank=True)
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.name} ({self.email})"

# file: core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    StudentProfile,
    Course,
    Enrollment,
    JobPlacement,
    Volunteer,
    WaitlistEntry,
)

class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role',)}),
    )

class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0

class JobPlacementInline(admin.TabularInline):
    model = JobPlacement
    extra = 0

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'github_url', 'linkedin_url')
    search_fields = ('user__username', 'user__email', 'phone')
    inlines = [EnrollmentInline, JobPlacementInline]

class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')
    search_fields = ('name',)

class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'active')
    search_fields = ('name', 'email')
    list_filter = ('active',)

class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status', 'date_applied')
    list_filter = ('status',)
    search_fields = ('name', 'email')

admin.site.register(User, UserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Enrollment)
admin.site.register(JobPlacement)
admin.site.register(Volunteer, VolunteerAdmin)
admin.site.register(WaitlistEntry, WaitlistEntryAdmin)

# file: core/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    StudentProfile,
    Course,
    Enrollment,
    JobPlacement,
    Volunteer,
    WaitlistEntry,
)
from django.contrib.auth import authenticate

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

class StudentProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ('user',)

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), source='course', write_only=True
    )

    class Meta:
        model = Enrollment
        fields = ('id', 'student_profile', 'course', 'course_id', 'status', 'enrolled_date')
        read_only_fields = ('student_profile', 'enrolled_date')

class JobPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPlacement
        fields = '__all__'
        read_only_fields = ('student_profile',)

class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = '__all__'

class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = '__all__'
        read_only_fields = ('date_applied',)

# file: core/permissions.py
from rest_framework import permissions

class IsOwnerOrOrganizer(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or organizers to view/edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Organizers can view/edit any object
        if request.user.role == 'organizer' or request.user.is_staff:
            return True
        # Object must have a 'user' attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

class IsOrganizer(permissions.BasePermission):
    """
    Allows access only to organizers.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'organizer' or request.user.is_staff)

# file: core/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .models import (
    StudentProfile,
    Enrollment,
    JobPlacement,
    Volunteer,
    WaitlistEntry,
)
from .serializers import (
    LoginSerializer,
    StudentProfileSerializer,
    EnrollmentSerializer,
    JobPlacementSerializer,
    VolunteerSerializer,
    WaitlistEntrySerializer,
)
from .permissions import IsOwnerOrOrganizer, IsOrganizer

User = get_user_model()

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'role': user.role,
        })

class StudentProfileDetail(generics.RetrieveUpdateAPIView):
    """
    Get/Update the authenticated student's own profile.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOrganizer]

    def get_object(self):
        # Return the profile of the authenticated user (if student)
        try:
            return StudentProfile.objects.get(user=self.request.user)
        except StudentProfile.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class StudentList(generics.ListAPIView):
    """
    List all student profiles. Organizers only.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsOrganizer]
    queryset = StudentProfile.objects.all()

class StudentDetail(generics.RetrieveAPIView):
    """
    Retrieve any student profile. Organizers only.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsOrganizer]
    queryset = StudentProfile.objects.all()

class StudentEnrollmentListCreate(generics.ListCreateAPIView):
    """
    List/create enrollments for a student profile. Organizers can manage any;
    students see only their own.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'organizer' or user.is_staff:
            return Enrollment.objects.all()
        # student: only own enrollments
        return Enrollment.objects.filter(student_profile__user=user)

    def perform_create(self, serializer):
        # If student creating, ensure student_profile is theirs
        if self.request.user.role == 'student' and not self.request.user.is_staff:
            # Might need to enforce; but serializer has student_profile field anyway.
            # For safety, set the student_profile automatically based on request.user
            profile = StudentProfile.objects.get(user=self.request.user)
            serializer.save(student_profile=profile)
        else:
            serializer.save()

class StudentJobPlacementListCreate(generics.ListCreateAPIView):
    serializer_class = JobPlacementSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'organizer' or user.is_staff:
            return JobPlacement.objects.all()
        return JobPlacement.objects.filter(student_profile__user=user)

    def perform_create(self, serializer):
        if self.request.user.role == 'student' and not self.request.user.is_staff:
            profile = StudentProfile.objects.get(user=self.request.user)
            serializer.save(student_profile=profile)
        else:
            serializer.save()

class VolunteerListCreate(generics.ListCreateAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [IsOrganizer]

class VolunteerDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [IsOrganizer]

class WaitlistListCreate(generics.ListCreateAPIView):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [IsOrganizer]

class WaitlistDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [IsOrganizer]

# file: core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.StudentProfileDetail.as_view(), name='student-profile'),
    path('students/', views.StudentList.as_view(), name='student-list'),
    path('students/<int:pk>/', views.StudentDetail.as_view(), name='student-detail'),
    path('enrollments/', views.StudentEnrollmentListCreate.as_view(), name='enrollment-list'),
    path('placements/', views.StudentJobPlacementListCreate.as_view(), name='placement-list'),
    path('volunteers/', views.VolunteerListCreate.as_view(), name='volunteer-list'),
    path('volunteers/<int:pk>/', views.VolunteerDetail.as_view(), name='volunteer-detail'),
    path('waitlist/', views.WaitlistListCreate.as_view(), name='waitlist-list'),
    path('waitlist/<int:pk>/', views.WaitlistDetail.as_view(), name='waitlist-detail'),
]

# file: requirements.txt
Django>=4.2,<5.0
djangorestframework>=3.14,<4.0