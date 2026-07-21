# File: orders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from cart.cart import Cart
from .models import Order, OrderItem
from inventory.models import Stock
from products.models import Product
from .forms import CheckoutForm

@login_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart_detail')
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                user=request.user,
                shipping_address=form.cleaned_data['shipping_address'],
                total=cart.get_total_price()
            )
            for item in cart:
                product = item['product']
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    unit_price=product.price
                )
                # Deduct stock from inventory
                try:
                    stock = Stock.objects.get(product=product)
                    if stock.quantity >= item['quantity']:
                        stock.quantity -= item['quantity']
                        stock.save()
                    else:
                        messages.error(request, f'Insufficient stock for {product.name}')
                        order.delete()
                        return redirect('cart_detail')
                except Stock.DoesNotExist:
                    messages.error(request, f'No inventory record for {product.name}')
                    order.delete()
                    return redirect('cart_detail')
            cart.clear()
            messages.success(request, 'Order placed successfully.')
            return redirect('order_detail', order_id=order.id)
    else:
        form = CheckoutForm()
    return render(request, 'orders/checkout.html', {'cart': cart, 'form': form})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})
