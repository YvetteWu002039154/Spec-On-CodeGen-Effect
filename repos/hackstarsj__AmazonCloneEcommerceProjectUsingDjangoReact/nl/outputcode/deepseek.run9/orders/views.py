from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from cart.models import Cart, CartItem
from .models import Order, OrderItem
from .forms import OrderCreateForm
from inventory.models import Inventory, Warehouse


@login_required
def order_create(request):
    cart = get_object_or_404(Cart, user=request.user)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            with transaction.atomic():
                order.save()
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity
                    )
                    # Decrease inventory from default warehouse (assuming first warehouse is default)
                    warehouse = Warehouse.objects.first()
                    if warehouse:
                        inv = Inventory.objects.filter(product=item.product, warehouse=warehouse).first()
                        if inv and inv.quantity >= item.quantity:
                            inv.quantity -= item.quantity
                            inv.save()
                        else:
                            # If insufficient stock, we should handle properly; here we just log
                            messages.warning(request, f'Insufficient stock for {item.product.name}')
                    else:
                        messages.warning(request, 'No warehouse configured; stock not decreased.')
                order.update_total()
                cart.items.all().delete()  # clear cart
                cart.delete()
            return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'address': request.user.profile.address,
        })
    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order/detail.html', {'order': order})

