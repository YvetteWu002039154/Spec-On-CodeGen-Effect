from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Cart, CartItem
from .forms import AddToCartForm, UpdateCartItemForm

@login_required
def get_or_create_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return cart

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = get_or_create_cart(request)
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            # Check stock
            stock = product.warehouse_stocks.aggregate(total=models.Sum('quantity'))['total'] or 0
            if stock < quantity:
                messages.error(request, 'Not enough stock')
                return redirect('products:product_detail', pk=product_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={{'quantity': 0}})
            cart_item.quantity += quantity
            cart_item.save()
            messages.success(request, 'Added to cart')
            return redirect('cart:cart_detail')
    else:
        form = AddToCartForm()
    return render(request, 'cart/add_to_cart.html', {{'product': product, 'form': form}})

@login_required
def cart_detail(request):
    cart = get_or_create_cart(request)
    return render(request, 'cart/cart_detail.html', {{'cart': cart}})

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Removed from cart')
    return redirect('cart:cart_detail')

@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    if request.method == 'POST':
        form = UpdateCartItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cart updated')
            return redirect('cart:cart_detail')
    else:
        form = UpdateCartItemForm(instance=item)
    return render(request, 'cart/update_cart.html', {{'form': form, 'item': item}})
