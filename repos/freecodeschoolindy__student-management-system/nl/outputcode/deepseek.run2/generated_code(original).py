import os
import sys

BASE_DIR = "student_management_system"
APP_NAME = "core"
PROJECT_NAME = "student_management_system"

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    project_dir = os.path.join(BASE_DIR, PROJECT_NAME)
    os.makedirs(project_dir, exist_ok=True)
    app_dir = os.path.join(BASE_DIR, APP_NAME)
    os.makedirs(app_dir, exist_ok=True)
    template_dir = os.path.join(app_dir, "templates", "core")
    os.makedirs(template_dir, exist_ok=True)

    # manage.py
    write_file(os.path.join(BASE_DIR, "manage.py"), """#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_management_system.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
""")

    # requirements.txt
    write_file(os.path.join(BASE_DIR, "requirements.txt"), """django>=4.2
djangorestframework
djangorestframework-simplejwt
""")

    # settings.py
    settings_content = f"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production'

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

AUTH_USER_MODEL = 'core.User'
"""
    write_file(os.path.join(project_dir, "settings.py"), settings_content)

    # wsgi.py
    write_file(os.path.join(project_dir, "wsgi.py"), """
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
application = get_wsgi_application()
""")

    # urls.py (project)
    write_file(os.path.join(project_dir, "urls.py"), """
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('core.urls')),
]
""")

    # core/__init__.py
    write_file(os.path.join(app_dir, "__init__.py"), "")

    # core/models.py
    models_content = """
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
"""
    write_file(os.path.join(app_dir, "models.py"), models_content)

    # core/serializers.py
    serializers_content = """
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, StudentProfile, Course, Enrollment, Waitlist, Volunteer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'user_type')

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'

class WaitlistSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Waitlist
        fields = '__all__'

class VolunteerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Volunteer
        fields = '__all__'

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if user and user.is_active:
            return user
        raise serializers.ValidationError('Invalid credentials')
"""
    write_file(os.path.join(app_dir, "serializers.py"), serializers_content)

    # core/views.py
    views_content = """
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from .models import StudentProfile, Course, Enrollment, Waitlist, Volunteer, User
from .serializers import (
    StudentProfileSerializer, CourseSerializer, EnrollmentSerializer,
    WaitlistSerializer, VolunteerSerializer, UserSerializer, LoginSerializer
)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user': UserSerializer(user).data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    def get(self, request):
        if request.user.user_type == 'student':
            profile, created = StudentProfile.objects.get_or_create(user=request.user)
            serializer = StudentProfileSerializer(profile)
            return Response(serializer.data)
        return Response({'detail': 'Not a student'}, status=403)

    def put(self, request):
        if request.user.user_type == 'student':
            profile, created = StudentProfile.objects.get_or_create(user=request.user)
            serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        return Response({'detail': 'Not a student'}, status=403)

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Enrollment.objects.all()
        return Enrollment.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class WaitlistViewSet(viewsets.ModelViewSet):
    serializer_class = WaitlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Waitlist.objects.all()
        return Waitlist.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class VolunteerViewSet(viewsets.ModelViewSet):
    serializer_class = VolunteerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Volunteer.objects.all()
        return Volunteer.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
"""
    write_file(os.path.join(app_dir, "views.py"), views_content)

    # core/urls.py
    urls_content = """
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, ProfileView, CourseViewSet, EnrollmentViewSet, WaitlistViewSet, VolunteerViewSet

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'waitlist', WaitlistViewSet)
router.register(r'volunteers', VolunteerViewSet)

urlpatterns = [
    path('login/', LoginView.as_view(), name='api-login'),
    path('profile/', ProfileView.as_view(), name='api-profile'),
    path('', include(router.urls)),
]
"""
    write_file(os.path.join(app_dir, "urls.py"), urls_content)

    # core/admin.py
    admin_content = """
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudentProfile, Course, Enrollment, Waitlist, Volunteer

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'

class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')
    inlines = [StudentProfileInline]
    readonly_fields = ('user_type',)

admin.site.register(User, CustomUserAdmin)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'enrollment_status')
    search_fields = ('user__username', 'user__email', 'organization')

class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    inlines = [EnrollmentInline]

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'grade', 'enrollment_date')
    list_filter = ('status', 'course')
    search_fields = ('student__username', 'course__name')

@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'position', 'date_joined', 'active')
    list_filter = ('active', 'course')
    search_fields = ('student__username',)

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'role', 'active')
    list_filter = ('role', 'active', 'course')
    search_fields = ('user__username',)
"""
    write_file(os.path.join(app_dir, "admin.py"), admin_content)

    # core/templates/core/login.html
    login_html = """<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
<h1>Login</h1>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Login</button>
</form>
</body>
</html>"""
    write_file(os.path.join(template_dir, "login.html"), login_html)

    # core/templates/core/profile.html (student profile page)
    profile_html = """<!DOCTYPE html>
<html>
<head><title>Profile</title></head>
<body>
<h1>Welcome, {{ user.username }}</h1>
<p>Email: {{ user.email }}</p>
<p>User Type: {{ user.user_type }}</p>
{% if profile %}
    <p>Bio: {{ profile.bio }}</p>
    <p>Organization: {{ profile.organization }}</p>
    <p>Skills: {{ profile.skills }}</p>
    <p>Status: {{ profile.enrollment_status }}</p>
{% endif %}
</body>
</html>"""
    write_file(os.path.join(template_dir, "profile.html"), profile_html)

    # Make manage.py executable
    manage_path = os.path.join(BASE_DIR, "manage.py")
    st = os.stat(manage_path)
    os.chmod(manage_path, st.st_mode | stat.S_IEXEC)

    print(f"Project created at {os.path.abspath(BASE_DIR)}")
    print("Next steps:")
    print("  cd student_management_system")
    print("  pip install -r requirements.txt")
    print("  python manage.py makemigrations core")
    print("  python manage.py migrate")
    print("  python manage.py createsuperuser")
    print("  python manage.py runserver")

if __name__ == "__main__":
    main()