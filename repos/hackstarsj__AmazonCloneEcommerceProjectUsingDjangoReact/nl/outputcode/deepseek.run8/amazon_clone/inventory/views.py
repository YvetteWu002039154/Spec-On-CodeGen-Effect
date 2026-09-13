from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from warehouses.models import Warehouse, WarehouseStock

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def inventory_dashboard(request):
    warehouses = Warehouse.objects.prefetch_related('stocks__product')
    return render(request, 'inventory/dashboard.html', {'warehouses': warehouses})
