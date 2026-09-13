from django.shortcuts import render, get_object_or_404
from .models import Warehouse

def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'warehouses/warehouse_list.html', {{'warehouses': warehouses}})

def warehouse_detail(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    return render(request, 'warehouses/warehouse_detail.html', {{'warehouse': warehouse}})
