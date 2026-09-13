from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.student_profile, name='own_profile'),
    path('profile/<int:pk>/', views.student_profile, name='student_profile'),
]

