# =============================================
# urls.py (store app)
# =============================================
from django.urls import path
from . import views

urlpatterns = [
    # Product browsing
    path('', views.ProductListView.as_view(), name='product_list'),
    path('category/<slug:category_slug>/', views.ProductListView.as_view(), name='product_list_by_category'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    # Checkout & orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    # Admin inventory
    path('admin/inventory/', views.InventoryListView.as_view(), name='inventory_list'),
    path('admin/inventory/<int:pk>/edit/', views.InventoryUpdateView.as_view(), name='inventory_edit'),
    # Purchase orders
    path('admin/purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('admin/purchase-orders/new/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('admin/purchase-orders/<int:po_pk>/receive/', views.receive_purchase_order, name='purchase_order_receive'),
]
