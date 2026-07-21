# File: suppliers/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.supplier_list, name='supplier_list'),
    path('purchase_orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase_order/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
]
