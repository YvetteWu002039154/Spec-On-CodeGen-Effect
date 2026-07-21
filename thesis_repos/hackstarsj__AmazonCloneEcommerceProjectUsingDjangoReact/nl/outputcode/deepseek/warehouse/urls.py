# File: warehouse/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.warehouse_list, name='warehouse_list'),
    path('<int:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
]
