from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from cart.models import Cart, CartItem
from .models import SalesOrder, SalesOrderItem, PurchaseOrder, PurchaseOrderItem
from .forms import SalesOrderForm
from warehouses.models import Warehouse, WarehouseStock
from suppliers.models import SupplierProduct
from django.db.models import Sum

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    if cart.items.count() == 0:
        messages.error(request, 'Cart is empty')
        return redirect('cart:cart_detail')
    if request.method == 'POST':
        form = SalesOrderForm(request.POST)
        if form.is_valid():
            shipping_address = form.cleaned_data['shipping_address']
            warehouse = form.cleaned_data['warehouse']
            with transaction.atomic():
                # Check stock and allocate
                for item in cart.items.all():
                    stock_qs = WarehouseStock.objects.filter(warehouse=warehouse, product=item.product)
                    if not stock_qs.exists() or stock_qs.aggregate(Sum('quantity'))['quantity__sum'] < item.quantity:
                        messages.error(request, f"Insufficient stock for {{item.product.name}} in selected warehouse.")
                        return redirect('cart:cart_detail')
                    # Decrease stock
                    stock = stock_qs.first()
                    remaining = item.quantity
                    for stock_record in stock_qs:
                        if remaining <= 0:
                            break
                        deducted = min(stock_record.quantity, remaining)
                        stock_record.quantity -= deducted
                        stock_record.save()
                        remaining -= deducted
                # Create order
                order = SalesOrder(user=request.user, shipping_address=shipping_address, warehouse=warehouse)
                order.save()
                for item in cart.items.all():
                    SalesOrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                order.calculate_total()
                cart.delete()
                messages.success(request, 'Order placed successfully!')
                return redirect('orders:order_detail', order_id=order.pk)
    else:
        form = SalesOrderForm()
    return render(request, 'orders/checkout.html', {{'form': form, 'cart': cart}})

@login_required
def order_history(request):
    orders = SalesOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {{'orders': orders}})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(SalesOrder, pk=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {{'order': order}})

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def create_purchase_order(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        warehouse_id = request.POST.get('warehouse')
        # Process items from form
        po = PurchaseOrder.objects.create(supplier_id=supplier_id, warehouse_id=warehouse_id)
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        unit_costs = request.POST.getlist('unit_cost')
        for pid, qty, cost in zip(product_ids, quantities, unit_costs):
            PurchaseOrderItem.objects.create(purchase_order=po, product_id=pid, quantity=qty, unit_cost=cost)
        po.calculate_total_cost()
        return redirect('orders:purchase_order_detail', po_id=po.pk)
    else:
        from suppliers.models import Supplier
        from warehouses.models import Warehouse
        suppliers = Supplier.objects.all()
        warehouses = Warehouse.objects.all()
        return render(request, 'orders/create_purchase_order.html', {{'suppliers': suppliers, 'warehouses': warehouses}})

@user_passes_test(is_admin)
def purchase_order_detail(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    return render(request, 'orders/purchase_order_detail.html', {{'po': po}})

@user_passes_test(is_admin)
def receive_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    if po.status == 'received':
        messages.info(request, 'Already received')
        return redirect('orders:purchase_order_detail', po_id=po_id)
    with transaction.atomic():
        for item in po.items.all():
            stock, created = WarehouseStock.objects.get_or_create(
                warehouse=po.warehouse, product=item.product,
                defaults={{'quantity': 0, 'low_stock_threshold': 10}}
            )
            stock.quantity += item.quantity
            stock.save()
        po.status = 'received'
        po.save()
    messages.success(request, 'Purchase order received, stock updated.')
    return redirect('orders:purchase_order_detail', po_id=po_id)
