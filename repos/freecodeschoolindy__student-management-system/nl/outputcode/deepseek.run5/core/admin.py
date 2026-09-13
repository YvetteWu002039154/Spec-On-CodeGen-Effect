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

