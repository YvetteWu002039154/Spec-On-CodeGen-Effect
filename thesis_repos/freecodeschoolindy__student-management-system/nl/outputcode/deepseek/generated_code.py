from django.db import models
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.urls import path
from django.conf import settings
from django.core.wsgi import get_wsgi_application
import os

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    progress = models.TextField(blank=True, help_text='Student progress details')
    outcomes = models.TextField(blank=True, help_text='Learning outcomes achieved')

    def __str__(self):
        return self.full_name

class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer_profile')
    skills = models.TextField(help_text='Skills and experience')
    availability = models.CharField(max_length=255, help_text='Availability schedule')

    def __str__(self):
        return f"Volunteer: {self.user.username}"

class WaitlistEntry(models.Model):
    WAITLIST_STATUS = [
        ('waiting', 'Waiting'),
        ('contacted', 'Contacted'),
        ('enrolled', 'Enrolled'),
    ]
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=WAITLIST_STATUS, default='waiting')

    def __str__(self):
        return self.name

# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )

admin.site.register(User, UserAdmin)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'email')
    search_fields = ('full_name', 'email', 'user__username')
    readonly_fields = ('user',)

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('user', 'skills')

@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status', 'created_at')
    list_filter = ('status',)

# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------
@login_required
def student_profile_view(request):
    if request.user.role != 'student':
        return HttpResponseForbidden("Only students can access this page.")
    profile = get_object_or_404(StudentProfile, user=request.user)
    return render(request, 'student/profile.html', {'profile': profile})

@login_required
@user_passes_test(lambda u: u.is_staff or u.role == 'organizer')
def student_detail_view(request, user_id):
    profile = get_object_or_404(StudentProfile, user__id=user_id)
    return render(request, 'student/detail.html', {'profile': profile})

# --------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------
urlpatterns = [
    path('profile/', student_profile_view, name='student-profile'),
    path('student/<int:user_id>/', student_detail_view, name='student-detail'),
]

# --------------------------------------------------------------------------
# App configuration (if used as standalone app inside a Django project)
# --------------------------------------------------------------------------
from django.apps import AppConfig

class StudentMgmtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'student_mgmt'