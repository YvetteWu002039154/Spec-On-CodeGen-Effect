from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, ProfileView, CourseViewSet, EnrollmentViewSet, WaitlistViewSet, VolunteerViewSet

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'waitlist', WaitlistViewSet)
router.register(r'volunteers', VolunteerViewSet)

urlpatterns = [
    path('login/', LoginView.as_view(), name='api-login'),
    path('profile/', ProfileView.as_view(), name='api-profile'),
    path('', include(router.urls)),
]
