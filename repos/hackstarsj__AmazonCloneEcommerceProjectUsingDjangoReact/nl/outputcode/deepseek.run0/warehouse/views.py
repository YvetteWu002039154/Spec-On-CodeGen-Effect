# File: warehouse/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Warehouse
from inventory.models import Stock

@staff_member_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'warehouse/warehouse_list.html', {'warehouses': warehouses})

@staff_member_required
def warehouse_detail(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    stocks = Stock.objects.filter(warehouse=warehouse)
    return render(request, 'warehouse/warehouse_detail.html', {'warehouse': warehouse, 'stocks': stocks})
