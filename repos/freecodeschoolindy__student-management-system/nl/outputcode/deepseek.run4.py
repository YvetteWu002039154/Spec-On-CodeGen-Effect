import os
import sys

def create_project():
    base_dir = "student_management_project"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    # Create manage.py
    manage_py = """#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_management.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
"""
    with open(os.path.join(base_dir, "manage.py"), "w") as f:
        f.write(manage_py)
    # Create requirements.txt
    req = """Django>=4.2,<5.0
"""
    with open(os.path.join(base_dir, "requirements.txt"), "w") as f:
        f.write(req)

    # Create project directory
    proj_dir = os.path.join(base_dir, "student_management")
    os.makedirs(proj_dir, exist_ok=True)
    # __init__.py
    open(os.path.join(proj_dir, "__init__.py"), "w").close()

    # settings.py
    settings_py = """import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-in-production-12345'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'school',
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

ROOT_URLCONF = 'student_management.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

LOGIN_REDIRECT_URL = 'profile'
LOGIN_URL = 'accounts/login/'
LOGOUT_REDIRECT_URL = 'accounts/login/'
"""
    with open(os.path.join(proj_dir, "settings.py"), "w") as f:
        f.write(settings_py)

    # urls.py
    urls_py = """from django.contrib import admin
from django.urls import path, include
from school import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/profile/', views.profile, name='profile'),
    path('', views.home, name='home'),
]
"""
    with open(os.path.join(proj_dir, "urls.py"), "w") as f:
        f.write(urls_py)

    # wsgi.py
    wsgi_py = """import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management.settings')
application = get_wsgi_application()
"""
    with open(os.path.join(proj_dir, "wsgi.py"), "w") as f:
        f.write(wsgi_py)

    # Create school app
    app_dir = os.path.join(base_dir, "school")
    os.makedirs(app_dir, exist_ok=True)
    open(os.path.join(app_dir, "__init__.py"), "w").close()

    # models.py
    models_py = """from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    bio = models.TextField(blank=True, help_text="Short bio or background information")
    progress = models.TextField(blank=True, help_text="General progress notes (JSON formatted if needed)")
    outcomes = models.TextField(blank=True, help_text="Student outcomes or achievements")

    def __str__(self):
        return f"Profile of {self.user.username}"

class Volunteer(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='volunteer_profile')
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class WaitlistEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlist_entries')
    position = models.PositiveIntegerField(default=0, help_text="Position in the waitlist queue")
    date_added = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['position']
        verbose_name_plural = "Waitlist entries"

    def __str__(self):
        return f"Waitlist #{self.position}: {self.user.username}"

class ProgressEntry(models.Model):
    COURSE_STATUSES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='progress_entries')
    course = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=COURSE_STATUSES, default='not_started')
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Progress entries"

    def __str__(self):
        return f"{self.student.user.username} - {self.course} ({self.get_status_display()})"

class Outcome(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='outcomes')
    description = models.TextField()
    date_achieved = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Outcome for {self.student.user.username}: {self.description[:50]}"

# Signal to create StudentProfile automatically when a new User is created
@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    if hasattr(instance, 'student_profile'):
        instance.student_profile.save()
"""
    with open(os.path.join(app_dir, "models.py"), "w") as f:
        f.write(models_py)

    # admin.py
    admin_py = """from django.contrib import admin
from .models import StudentProfile, Volunteer, WaitlistEntry, ProgressEntry, Outcome

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio_preview', 'progress_preview')
    search_fields = ('user__username', 'user__email', 'bio')
    list_filter = ('user__is_active',)

    def bio_preview(self, obj):
        return obj.bio[:50] + "..." if len(obj.bio) > 50 else obj.bio

    def progress_preview(self, obj):
        return obj.progress[:50] + "..." if len(obj.progress) > 50 else obj.progress

class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'user', 'is_active')
    search_fields = ('name', 'email')
    list_filter = ('is_active',)

class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('position', 'user', 'date_added')
    search_fields = ('user__username', 'user__email')
    list_filter = ('date_added',)

class ProgressEntryAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'last_updated')
    search_fields = ('student__user__username', 'course')
    list_filter = ('status', 'last_updated')

class OutcomeAdmin(admin.ModelAdmin):
    list_display = ('student', 'description_preview', 'date_achieved')
    search_fields = ('student__user__username', 'description')

    def description_preview(self, obj):
        return obj.description[:60] + "..." if len(obj.description) > 60 else obj.description

admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(Volunteer, VolunteerAdmin)
admin.site.register(WaitlistEntry, WaitlistEntryAdmin)
admin.site.register(ProgressEntry, ProgressEntryAdmin)
admin.site.register(Outcome, OutcomeAdmin)
"""
    with open(os.path.join(app_dir, "admin.py"), "w") as f:
        f.write(admin_py)

    # apps.py
    apps_py = """from django.apps import AppConfig

class SchoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'school'
"""
    with open(os.path.join(app_dir, "apps.py"), "w") as f:
        f.write(apps_py)

    # views.py
    views_py = """from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from .models import StudentProfile, ProgressEntry, Outcome

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin:index')
        return redirect('profile')
    return redirect('accounts/login/')

@login_required
def profile(request):
    # Fetch the student profile with related data
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        # If somehow profile missing, create one (should not happen due to signal)
        profile = StudentProfile.objects.create(user=request.user)
    # Prefetch related progress and outcomes for efficiency
    progress = profile.progress_entries.all()
    outcomes = profile.outcomes.all()
    context = {
        'profile': profile,
        'progress_entries': progress,
        'outcomes': outcomes,
    }
    return render(request, 'school/profile.html', context)
"""
    with open(os.path.join(app_dir, "views.py"), "w") as f:
        f.write(views_py)

    # Create migrations directory and __init__.py
    migrations_dir = os.path.join(app_dir, "migrations")
    os.makedirs(migrations_dir, exist_ok=True)
    open(os.path.join(migrations_dir, "__init__.py"), "w").close()

    # Templates directory
    templates_dir = os.path.join(base_dir, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    # Base template
    base_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Student Management{% endblock %}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; }
        nav { margin-bottom: 1em; }
        nav a { margin-right: 1em; }
    </style>
</head>
<body>
    <nav>
        <a href="{% url 'home' %}">Home</a>
        {% if user.is_authenticated %}
            <a href="{% url 'profile' %}">My Profile</a>
            <a href="{% url 'logout' %}">Logout</a>
        {% else %}
            <a href="{% url 'login' %}">Login</a>
        {% endif %}
    </nav>
    {% block content %}{% endblock %}
</body>
</html>
"""
    with open(os.path.join(templates_dir, "base.html"), "w") as f:
        f.write(base_html)

    # Registration login template (override Django's default)
    registration_dir = os.path.join(templates_dir, "registration")
    os.makedirs(registration_dir, exist_ok=True)
    login_html = """{% extends 'base.html' %}

{% block title %}Login{% endblock %}

{% block content %}
<h2>Login</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Login</button>
</form>
<p><a href="{% url 'password_reset' %}">Forgot password?</a></p>
{% endblock %}
"""
    with open(os.path.join(registration_dir, "login.html"), "w") as f:
        f.write(login_html)

    # Profile template
    school_templates_dir = os.path.join(app_dir, "templates", "school")
    os.makedirs(school_templates_dir, exist_ok=True)
    profile_html = """{% extends 'base.html' %}

{% block title %}My Profile{% endblock %}

{% block content %}
<h2>{{ profile.user.username }}'s Profile</h2>
<div>
    <h3>Bio</h3>
    <p>{{ profile.bio|default:"No bio provided." }}</p>
</div>
<div>
    <h3>Progress</h3>
    <p>{{ profile.progress|default:"No progress recorded." }}</p>
    {% if progress_entries %}
        <h4>Course Progress</h4>
        <ul>
        {% for entry in progress_entries %}
            <li>{{ entry.course }} - {{ entry.get_status_display }}</li>
        {% endfor %}
        </ul>
    {% endif %}
</div>
<div>
    <h3>Outcomes</h3>
    {% if outcomes %}
        <ul>
        {% for outcome in outcomes %}
            <li>{{ outcome.description }} {% if outcome.date_achieved %} (achieved {{ outcome.date_achieved }}){% endif %}</li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No outcomes recorded yet.</p>
    {% endif %}
</div>
{% endblock %}
"""
    with open(os.path.join(school_templates_dir, "profile.html"), "w") as f:
        f.write(profile_html)

    print(f"Project created at '{base_dir}'.")
    print("To start:")
    print(f"  cd {base_dir}")
    print("  pip install -r requirements.txt")
    print("  python manage.py migrate")
    print("  python manage.py createsuperuser")
    print("  python manage.py runserver")

if __name__ == "__main__":
    create_project()