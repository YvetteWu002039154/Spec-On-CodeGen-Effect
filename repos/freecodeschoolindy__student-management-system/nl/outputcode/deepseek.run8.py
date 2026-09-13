# fcc_school/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-this-is-a-secret-key-for-dev'

DEBUG = True

ALLOWED_HOSTS = ['*']

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

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fcc_school.urls'

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

WSGI_APPLICATION = 'fcc_school.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'students.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# fcc_school/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('students.urls')),
]

# manage.py
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcc_school.settings')
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

# students/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')

    def save(self, *args, **kwargs):
        if self.user_type in ('organizer', 'admin'):
            self.is_staff = True
        if self.user_type == 'admin':
            self.is_superuser = True
        else:
            self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    enrollment_date = models.DateField(auto_now_add=True)
    # Additional private fields
    email_verified = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.full_name


class Progress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_records')
    course_name = models.CharField(max_length=255)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.student.username} - {self.course_name}: {self.completion_percentage}%"


class Outcome(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='outcomes')
    outcome_type = models.CharField(max_length=100)  # e.g., 'certification', 'job_placement'
    description = models.TextField()
    date_achieved = models.DateField()

    def __str__(self):
        return f"{self.student.username} - {self.outcome_type}"


class Volunteer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='volunteer_profile')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    skills = models.TextField(blank=True)
    available_hours = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Waitlist(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='waitlists')
    course_name = models.CharField(max_length=255)
    position = models.PositiveIntegerField()
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course_name', 'position']

    def __str__(self):
        return f"{self.student.username} - {self.course_name} (#{self.position})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
        if instance.user_type == 'student':
            StudentProfile.objects.create(user=instance, full_name=instance.get_full_name() or instance.username)

# students/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile, Progress, Outcome, Volunteer, Waitlist


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'enrollment_date', 'email_verified')
    search_fields = ('user__username', 'full_name', 'user__email')
    list_filter = ('email_verified', 'enrollment_date')


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_name', 'completion_percentage', 'last_updated')
    list_filter = ('course_name', 'last_updated')
    search_fields = ('student__username', 'course_name')


@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = ('student', 'outcome_type', 'date_achieved')
    list_filter = ('outcome_type', 'date_achieved')


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'skills', 'available_hours')
    search_fields = ('name', 'email')


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_name', 'position', 'date_added')
    list_filter = ('course_name', 'date_added')
    ordering = ('course_name', 'position')

admin.site.register(User, CustomUserAdmin)

# students/permissions.py
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission: allow if user is admin (organizer or admin) or the owner.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.user_type in ('organizer', 'admin'):
            return True
        # Check if the object has a 'user' attribute (like StudentProfile)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # For other models that might have a student field
        if hasattr(obj, 'student'):
            return obj.student == request.user
        return False


class IsAdminOrOrganizer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff or request.user.user_type in ('organizer', 'admin')

# students/serializers.py
from rest_framework import serializers
from .models import User, StudentProfile, Progress, Outcome, Volunteer, Waitlist
from rest_framework.authtoken.models import Token


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(username=data['username'], password=data['password'])
        if user is None:
            raise serializers.ValidationError('Invalid credentials')
        if not user.is_active:
            raise serializers.ValidationError('Account disabled')
        data['user'] = user
        return data


class StudentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = StudentProfile
        fields = ['id', 'username', 'email', 'full_name', 'bio', 'enrollment_date', 'email_verified', 'phone']


class ProgressSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = Progress
        fields = '__all__'


class OutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outcome
        fields = '__all__'


class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = '__all__'


class WaitlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waitlist
        fields = '__all__'

# students/views.py
from rest_framework import status, viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from .models import StudentProfile, Progress, Outcome, Volunteer, Waitlist
from .serializers import (
    LoginSerializer, StudentProfileSerializer, ProgressSerializer,
    OutcomeSerializer, VolunteerSerializer, WaitlistSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdminOrOrganizer


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user_id': user.id, 'user_type': user.user_type})


class StudentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_object(self):
        # Allow access to own profile or any profile if admin
        if self.request.user.is_staff:
            pk = self.kwargs.get('pk')
            if pk:
                return StudentProfile.objects.get(pk=pk)
            return StudentProfile.objects.get(user=self.request.user)
        else:
            return StudentProfile.objects.get(user=self.request.user)


class StudentProgressView(generics.ListAPIView):
    serializer_class = ProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if user_id and self.request.user.is_staff:
            return Progress.objects.filter(student_id=user_id)
        else:
            return Progress.objects.filter(student=self.request.user)


class StudentOutcomeView(generics.ListAPIView):
    serializer_class = OutcomeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if user_id and self.request.user.is_staff:
            return Outcome.objects.filter(student_id=user_id)
        else:
            return Outcome.objects.filter(student=self.request.user)


class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOrganizer]


class WaitlistViewSet(viewsets.ModelViewSet):
    queryset = Waitlist.objects.all()
    serializer_class = WaitlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Waitlist.objects.all()
        return Waitlist.objects.filter(student=self.request.user)


# students/urls.py
from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'volunteers', views.VolunteerViewSet)
router.register(r'waitlists', views.WaitlistViewSet)

urlpatterns = [
    path('login/', views.login_view, name='api-login'),
    path('profile/', views.StudentProfileView.as_view(), name='student-profile-self'),
    path('profile/<int:pk>/', views.StudentProfileView.as_view(), name='student-profile-detail'),
    path('progress/', views.StudentProgressView.as_view(), name='student-progress-self'),
    path('progress/<int:user_id>/', views.StudentProgressView.as_view(), name='student-progress-admin'),
    path('outcomes/', views.StudentOutcomeView.as_view(), name='student-outcomes-self'),
    path('outcomes/<int:user_id>/', views.StudentOutcomeView.as_view(), name='student-outcomes-admin'),
]
urlpatterns += router.urls

# students/apps.py
from django.apps import AppConfig

class StudentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'students'

    def ready(self):
        import students.models  # noqa to register signals

# __init__.py (students package) may be empty

# requirements.txt (optional, but minimal)
# django>=3.2
# djangorestframework>=3.12