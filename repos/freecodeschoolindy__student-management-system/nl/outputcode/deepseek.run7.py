#!/usr/bin/env python3
"""Student Management System bootstrapper for Django.
Run this script to create a complete Django project.
"""

import os
import sys
import shutil
import subprocess

BASE_DIR = "student_mgmt"
PROJECT_NAME = "student_mgmt"
APP_NAME = "core"

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

def run_command(cmd, cwd=None):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, cwd=cwd, check=True)

def create_directory_structure():
    if os.path.exists(BASE_DIR):
        print(f"Directory '{BASE_DIR}' already exists. Aborting to prevent overwriting.")
        sys.exit(1)
    os.makedirs(BASE_DIR, exist_ok=True)
    # Create templates directory
    os.makedirs(TEMPLATE_DIR, exist_ok=True)

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Django project settings
settings_py = '''
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-in-production-!@#$%^&*()_+'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

ROOT_URLCONF = 'student_mgmt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'student_mgmt.wsgi.application'

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

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
'''

urls_py = '''
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
'''

wsgi_py = '''
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_mgmt.settings')
application = get_wsgi_application()
'''

manage_py = '''
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_mgmt.settings')
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
'''

# Core app files
core_models_py = '''
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('admin', 'Admin'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='student')
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class StudentProgress(models.Model):
    OUTCOME_CHOICES = (
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'profile__role': 'student'}, related_name='progress_entries')
    course_name = models.CharField(max_length=200)
    progress_percentage = models.IntegerField(default=0)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='in_progress')
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Student Progress"

    def __str__(self):
        return f"{self.student.username} - {self.course_name} ({self.progress_percentage}%)"

class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer_profile')
    bio = models.TextField(blank=True)
    availability = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

class Waitlist(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'profile__role': 'student'})
    course_name = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True)
    position = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.student.username} - {self.course_name} (Position {self.position})"
'''

core_admin_py = '''
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, StudentProgress, Volunteer, Waitlist

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_name', 'progress_percentage', 'outcome', 'updated_at')
    list_filter = ('outcome', 'course_name')
    search_fields = ('student__username', 'course_name')

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'is_active')

@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('student', 'course_name', 'position', 'date_added', 'is_active')
    list_filter = ('course_name', 'is_active')
'''

core_forms_py = '''
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
'''

core_views_py = '''
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import SignUpForm
from .models import StudentProgress, Volunteer, Waitlist, UserProfile

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.role = 'student'  # default role student
            user.profile.save()
            login(request, user)
            return redirect('profile')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def profile(request):
    user = request.user
    # Only show if staff or the user themselves
    if request.user.is_staff or request.user == user:
        profile = user.profile
        progress_entries = StudentProgress.objects.filter(student=user)
        return render(request, 'core/profile.html', {
            'profile': profile,
            'progress_entries': progress_entries,
            'show_private': True,
            'page_user': user,
        })
    else:
        # For others, show public info (but we don't have public view, so redirect)
        return redirect('dashboard')

@staff_member_required
def dashboard(request):
    # Admin dashboard with summary
    student_count = UserProfile.objects.filter(role='student').count()
    volunteer_count = Volunteer.objects.filter(is_active=True).count()
    waitlist_count = Waitlist.objects.filter(is_active=True).count()
    recent_progress = StudentProgress.objects.select_related('student').order_by('-updated_at')[:10]
    volunteers = Volunteer.objects.filter(is_active=True).select_related('user')
    waitlist_entries = Waitlist.objects.filter(is_active=True).select_related('student')[:10]
    return render(request, 'core/dashboard.html', {
        'student_count': student_count,
        'volunteer_count': volunteer_count,
        'waitlist_count': waitlist_count,
        'recent_progress': recent_progress,
        'volunteers': volunteers,
        'waitlist_entries': waitlist_entries,
    })

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        else:
            return redirect('profile')
    return render(request, 'core/home.html')
'''

core_urls_py = '''
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
'''

# Templates
# Base template
base_template = '''<!DOCTYPE html>
<html>
<head>
    <title>Student Management System</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        nav a { margin-right: 15px; }
        .errorlist { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
    </style>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        {% if user.is_authenticated %}
            <a href="{% url 'profile' %}">My Profile</a>
            {% if user.is_staff %}
                <a href="{% url 'dashboard' %}">Dashboard</a>
            {% endif %}
            <a href="{% url 'logout' %}">Logout</a>
            <span style="float:right;">Logged in as {{ user.username }} ({{ user.profile.role }})</span>
        {% else %}
            <a href="{% url 'login' %}">Login</a>
            <a href="{% url 'signup' %}">Sign Up</a>
        {% endif %}
    </nav>
    <hr>
    {% block content %}{% endblock %}
</body>
</html>
'''

home_template = '''{% extends "base.html" %}
{% block content %}
<h1>Welcome to the Student Management System</h1>
<p>Please login or sign up to continue.</p>
{% endblock %}
'''

login_template = '''{% extends "base.html" %}
{% block content %}
<h2>Login</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Login</button>
</form>
<p>No account? <a href="{% url 'signup' %}">Sign up</a></p>
{% endblock %}
'''

signup_template = '''{% extends "base.html" %}
{% block content %}
<h2>Sign Up</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Sign Up</button>
</form>
<p>Already have an account? <a href="{% url 'login' %}">Login</a></p>
{% endblock %}
'''

profile_template = '''{% extends "base.html" %}
{% block content %}
<h1>Profile: {{ page_user.username }}</h1>
{% if show_private %}
    <p><strong>Role:</strong> {{ profile.get_role_display }}</p>
    <p><strong>Email:</strong> {{ page_user.email }}</p>
    <p><strong>Bio:</strong> {{ profile.bio }}</p>
    <p><strong>Phone:</strong> {{ profile.phone }}</p>

    <h2>Your Progress</h2>
    {% if progress_entries %}
        <table>
            <tr><th>Course</th><th>Progress</th><th>Outcome</th><th>Updated</th></tr>
            {% for entry in progress_entries %}
            <tr>
                <td>{{ entry.course_name }}</td>
                <td>{{ entry.progress_percentage }}%</td>
                <td>{{ entry.get_outcome_display }}</td>
                <td>{{ entry.updated_at }}</td>
            </tr>
            {% endfor %}
        </table>
    {% else %}
        <p>No progress records yet.</p>
    {% endif %}
{% else %}
    <p>This profile is private.</p>
{% endif %}
{% endblock %}
'''

dashboard_template = '''{% extends "base.html" %}
{% block content %}
<h1>Admin Dashboard</h1>
<div>
    <p>Total Students: {{ student_count }}</p>
    <p>Active Volunteers: {{ volunteer_count }}</p>
    <p>Active Waitlist Entries: {{ waitlist_count }}</p>
</div>

<h2>Recent Student Progress</h2>
<table>
    <tr><th>Student</th><th>Course</th><th>Progress</th><th>Outcome</th><th>Updated</th></tr>
    {% for entry in recent_progress %}
    <tr>
        <td>{{ entry.student.username }}</td>
        <td>{{ entry.course_name }}</td>
        <td>{{ entry.progress_percentage }}%</td>
        <td>{{ entry.get_outcome_display }}</td>
        <td>{{ entry.updated_at }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="5">No progress records.</td></tr>
    {% endfor %}
</table>

<h2>Active Volunteers</h2>
<table>
    <tr><th>Username</th><th>Bio</th><th>Availability</th><th>Skills</th></tr>
    {% for v in volunteers %}
    <tr>
        <td>{{ v.user.username }}</td>
        <td>{{ v.bio }}</td>
        <td>{{ v.availability }}</td>
        <td>{{ v.skills }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4">No active volunteers.</td></tr>
    {% endfor %}
</table>

<h2>Waitlist (active, top 10)</h2>
<table>
    <tr><th>Student</th><th>Course</th><th>Position</th><th>Added</th></tr>
    {% for w in waitlist_entries %}
    <tr>
        <td>{{ w.student.username }}</td>
        <td>{{ w.course_name }}</td>
        <td>{{ w.position }}</td>
        <td>{{ w.date_added }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4">No waitlist entries.</td></tr>
    {% endfor %}
</table>

<p><a href="/admin/">Go to Django Admin</a></p>
{% endblock %}
'''

def main():
    create_directory_structure()
    project_dir = os.path.join(BASE_DIR, PROJECT_NAME)
    app_dir = os.path.join(project_dir, APP_NAME)
    templates_registration = os.path.join(BASE_DIR, 'templates', 'registration')
    templates_core = os.path.join(BASE_DIR, 'templates', 'core')
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(templates_registration, exist_ok=True)
    os.makedirs(templates_core, exist_ok=True)

    # Write files
    write_file(os.path.join(BASE_DIR, 'manage.py'), manage_py)
    os.chmod(os.path.join(BASE_DIR, 'manage.py'), 0o755)

    write_file(os.path.join(project_dir, '__init__.py'), '')
    write_file(os.path.join(project_dir, 'settings.py'), settings_py)
    write_file(os.path.join(project_dir, 'urls.py'), urls_py)
    write_file(os.path.join(project_dir, 'wsgi.py'), wsgi_py)

    write_file(os.path.join(app_dir, '__init__.py'), '')
    write_file(os.path.join(app_dir, 'models.py'), core_models_py)
    write_file(os.path.join(app_dir, 'admin.py'), core_admin_py)
    write_file(os.path.join(app_dir, 'forms.py'), core_forms_py)
    write_file(os.path.join(app_dir, 'views.py'), core_views_py)
    write_file(os.path.join(app_dir, 'urls.py'), core_urls_py)

    # Templates
    write_file(os.path.join(BASE_DIR, 'templates', 'base.html'), base_template)
    write_file(os.path.join(BASE_DIR, 'templates', 'core', 'home.html'), home_template)
    write_file(os.path.join(BASE_DIR, 'templates', 'core', 'profile.html'), profile_template)
    write_file(os.path.join(BASE_DIR, 'templates', 'core', 'dashboard.html'), dashboard_template)
    write_file(os.path.join(templates_registration, 'login.html'), login_template)
    write_file(os.path.join(templates_registration, 'signup.html'), signup_template)

    print("Project scaffold created.")
    print("Next steps:")
    print(f"  cd {BASE_DIR}")
    print("  python manage.py makemigrations")
    print("  python manage.py migrate")
    print("  python manage.py createsuperuser")
    print("  python manage.py runserver")
    print("\nThen visit http://localhost:8000/")

if __name__ == "__main__":
    main()