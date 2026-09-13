from django.urls import path
from . import views

app_name = 'inventory'
urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/<int:inv_id>/update/', views.inventory_update, name='inventory_update'),
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:po_id>/receive/', views.purchase_order_receive, name='purchase_order_receive'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
]

# Create a separate admin.py for inventory to register models in Django admin
