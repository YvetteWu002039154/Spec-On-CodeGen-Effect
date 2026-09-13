# File: inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from products.models import Product
from .models import Stock
from warehouse.models import Warehouse

@staff_member_required
def inventory_list(request):
    stocks = Stock.objects.select_related('product', 'warehouse').all()
    return render(request, 'inventory/inventory_list.html', {'stocks': stocks})

@staff_member_required
def stock_adjust(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        warehouse_id = request.POST.get('warehouse')
        quantity = int(request.POST.get('quantity', 0))
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        stock, created = Stock.objects.get_or_create(product=product, warehouse=warehouse)
        stock.quantity = quantity
        stock.save()
        messages.success(request, f'Stock adjusted for {product.name}')
        return redirect('inventory_list')
    warehouses = Warehouse.objects.all()
    return render(request, 'inventory/stock_adjust.html', {'product': product, 'warehouses': warehouses})
