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

