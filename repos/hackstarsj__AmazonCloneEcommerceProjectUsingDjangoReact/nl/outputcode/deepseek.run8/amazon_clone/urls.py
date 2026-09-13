from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('products/', include('products.urls', namespace='products')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('suppliers/', include('suppliers.urls', namespace='suppliers')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('warehouses/', include('warehouses.urls', namespace='warehouses')),
    path('', include('products.urls', namespace='products_root')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
