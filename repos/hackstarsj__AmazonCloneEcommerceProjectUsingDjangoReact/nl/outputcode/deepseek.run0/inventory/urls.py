# File: inventory/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('adjust/<int:product_id>/', views.stock_adjust, name='stock_adjust'),
]
