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
