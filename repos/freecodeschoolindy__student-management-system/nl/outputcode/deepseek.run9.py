import os
import sys
import django
from pathlib import Path

PROJECT_NAME = 'student_management'
APP_NAME = 'core'
BASE_DIR = Path.cwd() / PROJECT_NAME

def write_file(filepath, content):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    arg = 'wb' if isinstance(content, bytes) else 'w'
    with open(filepath, arg) as f:
        f.write(content)

manage_content = """#!/usr/bin/env python
import os
import sys

def main():
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
"""

init_content = ""

settings_content = f"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-1234567890'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    '{APP_NAME}',
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

ROOT_URLCONF = '{PROJECT_NAME}.urls'

TEMPLATES = [
    {{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {{
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        }},
    }},
]

WSGI_APPLICATION = '{PROJECT_NAME}.wsgi.application'

DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }}
}

AUTH_PASSWORD_VALIDATORS = []

AUTH_USER_MODEL = '{APP_NAME}.User'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
"""

urls_content = f"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('{APP_NAME}.urls')),
]
"""

wsgi_content = """
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management.settings')
application = get_wsgi_application()
"""

apps_content = f"""
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{APP_NAME}'
"""

models_content = f"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

class UserManager(BaseUserManager):
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
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('admin', 'Admin'),
        ('volunteer', 'Volunteer'),
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    progress_summary = models.TextField(blank=True)

    def __str__(self):
        return f"Profile of {{self.user.email}}"

class StudentProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_entries')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{{self.user.email}} - {{self.title}}"

class WaitlistEntry(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=100)
    applied_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending', choices=(
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ))
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{{self.name}} <{{self.email}}>"

class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer_profile')
    skills = models.TextField(blank=True)
    availability = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Volunteer {{self.user.email}}"
"""

admin_content = f"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile, StudentProgress, WaitlistEntry, Volunteer

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {{'fields': ('email', 'password')}}),
        ('Personal info', {{'fields': ('first_name', 'last_name', 'role')}}),
        ('Permissions', {{'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}}),
        ('Important dates', {{'fields': ('last_login', 'date_joined')}}),
    )
    add_fieldsets = (
        (None, {{
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2', 'is_staff', 'is_active')}}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile)
admin.site.register(StudentProgress)
admin.site.register(WaitlistEntry)
admin.site.register(Volunteer)
"""

views_content = f"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import User, StudentProfile

@login_required
def student_profile(request, user_id=None):
    if user_id is None:
        user = request.user
    else:
        user = get_object_or_404(User, id=user_id)
    if not (request.user.is_staff or request.user == user):
        return redirect('login')

    profile = None
    try:
        profile = StudentProfile.objects.get(user=user)
    except StudentProfile.DoesNotExist:
        pass

    context = {{
        'user_profile': user,
        'profile': profile,
        'is_own': request.user == user,
    }}
    return render(request, 'core/profile.html', context)

def home(request):
    if request.user.is_authenticated and request.user.role == 'student':
        return redirect(reverse('profile'))
    return render(request, 'core/home.html')
"""

urls_app_content = f"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.student_profile, name='profile_self'),
    path('profile/<int:user_id>/', views.student_profile, name='profile_detail'),
]
"""

templates_dir = BASE_DIR / APP_NAME / 'templates' / APP_NAME
profile_template = """
<!DOCTYPE html>
<html>
<head><title>Profile</title></head>
<body>
  <h1>Student Profile</h1>
  {% if profile %}
    <p><strong>Email:</strong> {{ user_profile.email }}</p>
    <p><strong>Name:</strong> {{ user_profile.first_name }} {{ user_profile.last_name }}</p>
    <p><strong>Bio:</strong> {{ profile.bio }}</p>
    <p><strong>Progress Summary:</strong> {{ profile.progress_summary }}</p>
  {% else %}
    <p>No profile found.</p>
  {% endif %}
  {% if is_own %}
    <p><a href="{% url 'profile_self' %}">Refresh</a></p>
  {% endif %}
  <a href="/accounts/logout/">Logout</a>
</body>
</html>
"""

home_template = """
<!DOCTYPE html>
<html>
<head><title>Home</title></head>
<body>
  <h1>Welcome to freeCodeSchool Student Management</h1>
  {% if user.is_authenticated %}
    <p>Logged in as {{ user.email }} ({{ user.role }})</p>
    {% if user.role == 'student' %}
      <a href="{% url 'profile_self' %}">My Profile</a>
    {% endif %}
    <a href="/accounts/logout/">Logout</a>
  {% else %}
    <a href="/accounts/login/">Login</a>
  {% endif %}
</body>
</html>
"""

login_template = """
{% extends "registration/login.html" %}
"""

def create_project():
    write_file(BASE_DIR / 'manage.py', manage_content)
    write_file(BASE_DIR / PROJECT_NAME / '__init__.py', init_content)
    write_file(BASE_DIR / PROJECT_NAME / 'settings.py', settings_content)
    write_file(BASE_DIR / PROJECT_NAME / 'urls.py', urls_content)
    write_file(BASE_DIR / PROJECT_NAME / 'wsgi.py', wsgi_content)

    app_dir = BASE_DIR / APP_NAME
    write_file(app_dir / '__init__.py', init_content)
    write_file(app_dir / 'apps.py', apps_content)
    write_file(app_dir / 'models.py', models_content)
    write_file(app_dir / 'admin.py', admin_content)
    write_file(app_dir / 'views.py', views_content)
    write_file(app_dir / 'urls.py', urls_app_content)

    write_file(templates_dir / 'profile.html', profile_template)
    write_file(templates_dir / 'home.html', home_template)

if __name__ == '__main__':
    create_project()
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{PROJECT_NAME}.settings')
    django.setup()

    from django.core.management import call_command
    call_command('makemigrations', APP_NAME)
    call_command('migrate')

    from core.models import User
    if not User.objects.filter(email='admin@example.com').exists():
        User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
    print('Project setup complete. Run server with: python manage.py runserver')