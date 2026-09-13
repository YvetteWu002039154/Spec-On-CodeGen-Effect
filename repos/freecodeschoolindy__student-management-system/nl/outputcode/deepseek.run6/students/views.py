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

