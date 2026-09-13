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

