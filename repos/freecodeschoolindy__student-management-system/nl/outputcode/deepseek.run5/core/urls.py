from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.StudentProfileDetail.as_view(), name='student-profile'),
    path('students/', views.StudentList.as_view(), name='student-list'),
    path('students/<int:pk>/', views.StudentDetail.as_view(), name='student-detail'),
    path('enrollments/', views.StudentEnrollmentListCreate.as_view(), name='enrollment-list'),
    path('placements/', views.StudentJobPlacementListCreate.as_view(), name='placement-list'),
    path('volunteers/', views.VolunteerListCreate.as_view(), name='volunteer-list'),
    path('volunteers/<int:pk>/', views.VolunteerDetail.as_view(), name='volunteer-detail'),
    path('waitlist/', views.WaitlistListCreate.as_view(), name='waitlist-list'),
    path('waitlist/<int:pk>/', views.WaitlistDetail.as_view(), name='waitlist-detail'),
]

