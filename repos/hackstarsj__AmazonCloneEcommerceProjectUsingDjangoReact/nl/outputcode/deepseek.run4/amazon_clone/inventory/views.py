from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Inventory, Warehouse, Supplier, PurchaseOrder, PurchaseOrderItem
from store.models import Product, Category
from orders.models import Order

def is_staff(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    low_stock = Inventory.objects.filter(quantity__lt=10)
    pending_pos = PurchaseOrder.objects.filter(status='pending')
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'low_stock_count': low_stock.count(),
        'pending_po_count': pending_pos.count(),
        'recent_orders': Order.objects.all()[:5],
    }
    return render(request, 'inventory/admin_dashboard.html', context)

@login_required
@user_passes_test(is_staff)
def inventory_list(request):
    inventories = Inventory.objects.select_related('product', 'warehouse').all()
    return render(request, 'inventory/inventory_list.html', {'inventories': inventories})

@login_required
@user_passes_test(is_staff)
def inventory_update(request, inv_id):
    inv = get_object_or_404(Inventory, id=inv_id)
    if request.method == 'POST':
        new_qty = int(request.POST.get('quantity'))
        if new_qty >= 0:
            inv.quantity = new_qty
            inv.save()
            messages.success(request, 'Inventory updated.')
            return redirect('inventory:inventory_list')
    return redirect('inventory:inventory_list')

@login_required
@user_passes_test(is_staff)
def purchase_order_list(request):
    pos = PurchaseOrder.objects.all()
    return render(request, 'inventory/purchase_order_list.html', {'purchase_orders': pos})

@login_required
@user_passes_test(is_staff)
def purchase_order_create(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        warehouse_id = request.POST.get('warehouse')
        expected_delivery = request.POST.get('expected_delivery')
        notes = request.POST.get('notes', '')
        po = PurchaseOrder.objects.create(
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            expected_delivery=expected_delivery,
            notes=notes,
        )
        # process items
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')
        for pid, qty, price in zip(product_ids, quantities, unit_prices):
            if pid and qty:
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product_id=pid,
                    quantity=int(qty),
                    unit_price=float(price)
                )
        messages.success(request, 'Purchase order created.')
        return redirect('inventory:purchase_order_list')
    suppliers = Supplier.objects.all()
    warehouses = Warehouse.objects.all()
    products = Product.objects.all()
    return render(request, 'inventory/purchase_order_create.html', {
        'suppliers': suppliers,
        'warehouses': warehouses,
        'products': products,
    })

@login_required
@user_passes_test(is_staff)
def purchase_order_detail(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    return render(request, 'inventory/purchase_order_detail.html', {'po': po})

@login_required
@user_passes_test(is_staff)
def purchase_order_receive(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    if po.status != 'pending':
        messages.error(request, 'This PO is not pending.')
        return redirect('inventory:purchase_order_detail', po_id=po.id)
    for item in po.items.all():
        Inventory.increase_stock(item.product, po.warehouse, item.quantity)
    po.status = 'received'
    po.save()
    messages.success(request, 'PO received and inventory updated.')
    return redirect('inventory:purchase_order_list')

@login_required
@user_passes_test(is_staff)
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@login_required
@user_passes_test(is_staff)
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'inventory/warehouse_list.html', {'warehouses': warehouses})

