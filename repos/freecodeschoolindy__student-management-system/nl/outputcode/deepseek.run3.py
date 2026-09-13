# manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management.settings')
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

# student_management/__init__.py
# student_management/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-in-production-!@#$%^&*()'

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
    'students',
]

AUTH_USER_MODEL = 'students.CustomUser'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'student_management.urls'

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

WSGI_APPLICATION = 'student_management.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# student_management/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('students.urls')),
]

# student_management/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management.settings')
application = get_wsgi_application()

# students/__init__.py
# students/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('admin', 'Admin'),
    )
    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.user_type == 'admin':
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    enrollment_date = models.DateField(auto_now_add=True)
    current_status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('on_hold', 'On Hold'), ('completed', 'Completed')],
        default='active'
    )
    is_private = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"


class Progress(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='progress_entries')
    course_or_module = models.CharField(max_length=100)
    completion_percentage = models.PositiveIntegerField(default=0)
    date_updated = models.DateField(auto_now=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.user.email} - {self.course_or_module}: {self.completion_percentage}%"


class Outcome(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='outcomes')
    outcome = models.CharField(max_length=100)
    date = models.DateField()
    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.user.email}: {self.outcome}"


class Volunteer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='volunteer_profile')
    skills = models.TextField(blank=True)
    availability = models.CharField(max_length=100, blank=True)
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Volunteer: {self.user.email}"


class WaitlistEntry(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='waitlist_entries')
    date_applied = models.DateField(auto_now_add=True)
    position = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('waiting', 'Waiting'), ('contacted', 'Contacted'), ('enrolled', 'Enrolled')],
        default='waiting'
    )

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"Waitlist #{self.position}: {self.user.email}"

# students/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, StudentProfile, Progress, Outcome, Volunteer, WaitlistEntry


class CustomUserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'user_type')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type'),
        }),
    )
    list_display = ('email', 'user_type', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(StudentProfile)
admin.site.register(Progress)
admin.site.register(Outcome)
admin.site.register(Volunteer)
admin.site.register(WaitlistEntry)

# students/serializers.py
from rest_framework import serializers
from .models import CustomUser, StudentProfile, Progress, Outcome, Volunteer, WaitlistEntry


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'user_type', 'first_name', 'last_name')
        read_only_fields = ('id',)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'password', 'user_type', 'first_name', 'last_name')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ('user', 'enrollment_date')


class ProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Progress
        fields = '__all__'
        read_only_fields = ('student', 'date_updated')


class OutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outcome
        fields = '__all__'
        read_only_fields = ('student',)


class VolunteerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Volunteer
        fields = '__all__'
        read_only_fields = ('user', 'joined_date')


class WaitlistEntrySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WaitlistEntry
        fields = '__all__'
        read_only_fields = ('date_applied',)


class DashboardSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    active_students = serializers.IntegerField()
    total_volunteers = serializers.IntegerField()
    waitlist_count = serializers.IntegerField()
    recent_outcomes = OutcomeSerializer(many=True)

# students/permissions.py
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.user == request.user:
            return True
        if request.user.user_type in ['organizer', 'admin']:
            return True
        return False

class IsAdminOrOrganizer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type in ['admin', 'organizer']

# students/views.py
from rest_framework import viewsets, status, generics, permissions, views
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .models import CustomUser, StudentProfile, Progress, Outcome, Volunteer, WaitlistEntry
from .serializers import (
    UserSerializer, RegisterSerializer, StudentProfileSerializer,
    ProgressSerializer, OutcomeSerializer, VolunteerSerializer,
    WaitlistEntrySerializer, DashboardSummarySerializer
)
from .permissions import IsOwnerOrAdmin, IsAdminOrOrganizer


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(views.APIView):
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_200_OK)


class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsAdminOrOrganizer]
        else:
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        try:
            profile = StudentProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ProgressViewSet(viewsets.ModelViewSet):
    queryset = Progress.objects.all()
    serializer_class = ProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def perform_create(self, serializer):
        student_profile = self.request.user.student_profile
        serializer.save(student=student_profile)

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Progress.objects.all()
        return Progress.objects.filter(student__user=user)


class OutcomeViewSet(viewsets.ModelViewSet):
    queryset = Outcome.objects.all()
    serializer_class = OutcomeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminOrOrganizer]
        else:
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Outcome.objects.all()
        return Outcome.objects.filter(student__user=user)

    def perform_create(self, serializer):
        # assume student is provided
        serializer.save()


class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [IsAdminOrOrganizer]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WaitlistViewSet(viewsets.ModelViewSet):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer

    def get_permissions(self):
        if self.action in ['create']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [IsAdminOrOrganizer]
        return super().get_permissions()

    def perform_create(self, serializer):
        # auto-assign position
        last = WaitlistEntry.objects.last()
        position = 1 if not last else last.position + 1
        serializer.save(position=position)


class DashboardView(views.APIView):
    permission_classes = [IsAdminOrOrganizer]

    def get(self, request):
        total_students = StudentProfile.objects.count()
        active_students = StudentProfile.objects.filter(current_status='active').count()
        total_volunteers = Volunteer.objects.count()
        waitlist_count = WaitlistEntry.objects.filter(status='waiting').count()
        recent_outcomes = Outcome.objects.order_by('-date')[:5]
        data = {
            'total_students': total_students,
            'active_students': active_students,
            'total_volunteers': total_volunteers,
            'waitlist_count': waitlist_count,
            'recent_outcomes': OutcomeSerializer(recent_outcomes, many=True).data,
        }
        return Response(data)

# students/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework.authtoken.views import obtain_auth_token

router = DefaultRouter()
router.register(r'students/profile', views.StudentProfileViewSet)
router.register(r'students/progress', views.ProgressViewSet)
router.register(r'students/outcomes', views.OutcomeViewSet)
router.register(r'volunteers', views.VolunteerViewSet)
router.register(r'waitlist', views.WaitlistViewSet)

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', obtain_auth_token, name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('', include(router.urls)),
]