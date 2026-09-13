from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('history/', views.order_history, name='order_history'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('purchase-order/create/', views.create_purchase_order, name='create_purchase_order'),
    path('purchase-order/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-order/<int:po_id>/receive/', views.receive_purchase_order, name='receive_purchase_order'),
]
