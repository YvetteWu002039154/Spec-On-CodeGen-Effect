# manage.py
#!/usr/bin/env python
import os
import sys

def main():
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

# student_mgmt/__init__.py
# (empty)

# student_mgmt/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-CHANGE-ME-IN-PRODUCTION!'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

ROOT_URLCONF = 'student_mgmt.urls'

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

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# student_mgmt/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('students.urls')),
]

# student_mgmt/wsgi.py
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_mgmt.settings')
application = get_wsgi_application()

# students/__init__.py
# (empty)

# students/models.py
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    enrollment_date = models.DateField(auto_now_add=True)
    current_level = models.CharField(max_length=100, blank=True)
    progress_notes = models.TextField(blank=True)
    outcome = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer')
    availability = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Volunteer: {self.user.username}"


class WaitlistEntry(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlist_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Waitlist {self.user.username} ({self.status})"

    class Meta:
        verbose_name_plural = "Waitlist Entries"


@receiver(post_save, sender=StudentProfile)
def assign_student_group(sender, instance, created, **kwargs):
    if created:
        student_group, _ = Group.objects.get_or_create(name='Students')
        instance.user.groups.add(student_group)

@receiver(post_save, sender=Volunteer)
def assign_volunteer_group(sender, instance, created, **kwargs):
    if created:
        vol_group, _ = Group.objects.get_or_create(name='Volunteers')
        instance.user.groups.add(vol_group)

# Signal to add Organizers group manually via admin or data migration is fine.
# We create it when an admin assigns a user to that group.

# students/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import StudentProfile, Volunteer, WaitlistEntry


class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'enrollment_date', 'current_level', 'outcome_summary')
    list_filter = ('current_level', 'enrollment_date')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)

    def outcome_summary(self, obj):
        return obj.outcome[:50] if obj.outcome else '-'
    outcome_summary.short_description = 'Outcome'


class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('user', 'availability', 'skills_list')
    search_fields = ('user__username', 'skills')
    raw_id_fields = ('user',)

    def skills_list(self, obj):
        return obj.skills[:50] if obj.skills else '-'
    skills_list.short_description = 'Skills'


class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at')
    list_filter = ('status',)
    actions = ['approve_entries', 'reject_entries']
    search_fields = ('user__username',)
    raw_id_fields = ('user',)

    def approve_entries(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"{updated} entries approved.")
    approve_entries.short_description = 'Approve selected entries'

    def reject_entries(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} entries rejected.")
    reject_entries.short_description = 'Reject selected entries'


admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(Volunteer, VolunteerAdmin)
admin.site.register(WaitlistEntry, WaitlistEntryAdmin)

# Ensure Organizers group exists; we create it via admin or migration.

# students/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from .models import StudentProfile


def is_organizer(user):
    return user.groups.filter(name='Organizers').exists() or user.is_superuser


@login_required
def student_profile(request, pk=None):
    """
    Private profile view: if pk is given and user is organizer, show that student's profile.
    Otherwise show own profile (must have StudentProfile).
    """
    if pk is not None:
        # Admin viewing a specific student
        if not is_organizer(request.user):
            return HttpResponseForbidden("You do not have permission to view this profile.")
        profile = get_object_or_404(StudentProfile, pk=pk)
    else:
        # Student views own profile
        try:
            profile = StudentProfile.objects.get(user=request.user)
        except StudentProfile.DoesNotExist:
            return render(request, 'students/no_profile.html')
    context = {'profile': profile}
    return render(request, 'students/profile.html', context)


# Simple homepage
def home(request):
    return render(request, 'students/home.html')

# students/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.student_profile, name='own_profile'),
    path('profile/<int:pk>/', views.student_profile, name='student_profile'),
]

# students/templates/students/profile.html
<!DOCTYPE html>
<html>
<head>
    <title>Student Profile</title>
</head>
<body>
    <h1>Student Profile</h1>
    <p>Username: {{ profile.user.username }}</p>
    <p>Email: {{ profile.user.email }}</p>
    <p>Date of Birth: {{ profile.date_of_birth }}</p>
    <p>Enrollment Date: {{ profile.enrollment_date }}</p>
    <p>Current Level: {{ profile.current_level }}</p>
    <p>Progress Notes: {{ profile.progress_notes }}</p>
    <p>Outcome: {{ profile.outcome }}</p>
    <a href="{% url 'home' %}">Home</a> |
    <a href="{% url 'logout' %}">Logout</a>
</body>
</html>

# students/templates/students/no_profile.html
<!DOCTYPE html>
<html>
<head><title>No Profile</title></head>
<body>
    <p>You do not have a student profile. Please contact an admin.</p>
    <a href="{% url 'home' %}">Home</a>
</body>
</html>

# students/templates/students/home.html
<!DOCTYPE html>
<html>
<head><title>Student Management System</title></head>
<body>
    <h1>Welcome to the Student Management System</h1>
    {% if user.is_authenticated %}
        <p>Hello, {{ user.username }}!</p>
        {% if user.groups.all %}
            <p>Groups: {% for g in user.groups.all %}{{ g.name }}{% if not forloop.last %}, {% endif %}{% endfor %}</p>
        {% endif %}
        {% if user.student_profile %}
            <p><a href="{% url 'own_profile' %}">View my profile</a></p>
        {% endif %}
        <p><a href="{% url 'logout' %}">Logout</a></p>
    {% else %}
        <p><a href="{% url 'login' %}">Login</a></p>
    {% endif %}
</body>
</html>