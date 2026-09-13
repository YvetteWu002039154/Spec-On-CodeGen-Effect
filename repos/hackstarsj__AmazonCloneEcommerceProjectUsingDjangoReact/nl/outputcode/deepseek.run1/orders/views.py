from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from cart.models import Cart
from .models import Order, OrderItem
from inventory.models import Stock

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart_detail')

    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address', request.user.profile.address)
        billing_address = request.POST.get('billing_address', request.user.profile.address)

        # Check stock availability and reserve (deduct) from warehouses
        # Simple allocation: iterate items and subtract from warehouses with enough stock
        insufficient_items = []
        for item in cart.items.all():
            required = item.quantity
            stocks = Stock.objects.filter(product=item.product).order_by('-quantity')
            available_total = sum(s.quantity for s in stocks)
            if available_total < required:
                insufficient_items.append(item.product.name)

        if insufficient_items:
            messages.error(request, f"Insufficient stock for: {', '.join(insufficient_items)}")
            return render(request, 'orders/checkout.html', {'cart': cart, 'shipping_address': shipping_address})

        # Proceed to create order and allocate stock
        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address,
            billing_address=billing_address,
            total=cart.total_price
        )
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            # Deduct stock from warehouses (allocate)
            to_fulfill = item.quantity
            for stock in Stock.objects.filter(product=item.product).order_by('-quantity'):
                if to_fulfill <= 0:
                    break
                deduct = min(stock.quantity, to_fulfill)
                stock.quantity -= deduct
                stock.save()
                to_fulfill -= deduct

        # Clear cart
        cart.items.all().delete()
        messages.success(request, 'Order placed successfully!')
        return redirect('order_confirmation', order_id=order.id)

    # GET: prefill address from profile
    shipping_address = request.user.profile.address if request.user.profile else ''
    return render(request, 'orders/checkout.html', {'cart': cart, 'shipping_address': shipping_address})

@login_required
def order_confirmation(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'orders/confirmation.html', {'order': order})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'orders/detail.html', {'order': order})

