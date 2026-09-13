# =============================================
# views.py
# =============================================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from .models import (
    User, Category, Product, Cart, CartItem,
    Order, OrderItem, Inventory, InventoryTransaction, Warehouse
)
from .forms import CartItemForm, OrderCheckoutForm

# ---------- Public views ----------
class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    queryset = Product.objects.filter(is_active=True)

    def get_queryset(self):
        qs = super().get_queryset()
        cat_slug = self.kwargs.get('category_slug')
        if cat_slug:
            category = get_object_or_404(Category, slug=cat_slug)
            # Include all subcategories
            descendants = category.get_descendants(include_self=True)  # need MPTT or implement manually
            # For simplicity, just filter direct category
            qs = qs.filter(category=category)
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(description__icontains=query)
        return qs.distinct()

class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    queryset = Product.objects.filter(is_active=True)

# ---------- Cart views ----------
@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart_detail.html', {'cart': cart})

@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item.quantity = 1
        cart_item.save()
    messages.success(request, f'Added {product.name} to cart.')
    return redirect('cart_detail')

@login_required
def cart_remove(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    CartItem.objects.filter(cart=cart, product=product).delete()
    messages.success(request, f'Removed {product.name} from cart.')
    return redirect('cart_detail')

@login_required
def cart_update(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    if request.method == 'POST':
        form = CartItemForm(request.POST, instance=cart_item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cart updated.')
    return redirect('cart_detail')

# ---------- Checkout & Orders ----------
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart_detail')
    if request.method == 'POST':
        form = OrderCheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=form.cleaned_data['shipping_address'],
                    total_price=cart.total_price,
                    status='PENDING'
                )
                # Create order items and deduct stock from one of the warehouses
                for ci in cart.items.all():
                    product = ci.product
                    # Find warehouse with sufficient stock (naive: pick first with enough).
                    # Real logic: choose warehouse based on proximity or policy.
                    inventories = product.inventories.filter(quantity__gte=ci.quantity).order_by('warehouse')
                    if not inventories.exists():
                        # Not enough stock anywhere; abort.
                        raise Exception(f"Not enough stock for {product.name}")
                    inv = inventories.first()
                    # Deduct stock
                    inv.quantity -= ci.quantity
                    inv.save()
                    # Record transaction
                    InventoryTransaction.objects.create(
                        transaction_type='SALE',
                        product=product,
                        warehouse=inv.warehouse,
                        quantity_change=-ci.quantity,
                        reference=f"Order #{order.id}",
                        performed_by=request.user
                    )
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        price=product.price,
                        quantity=ci.quantity,
                        warehouse=inv.warehouse
                    )
                # Clear cart
                cart.items.all().delete()
            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderCheckoutForm()
    return render(request, 'store/checkout.html', {'cart': cart, 'form': form})

@login_required
def order_list(request):
    orders = request.user.orders.all().order_by('-order_date')
    return render(request, 'store/order_list.html', {'orders': orders})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})

# ---------- Inventory Management for Admin (views requiring staff) ----------
class InventoryListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Inventory
    template_name = 'admin/inventory_list.html'
    context_object_name = 'inventories'
    def test_func(self):
        return self.request.user.is_staff

class InventoryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Inventory
    fields = ['quantity']
    template_name = 'admin/inventory_form.html'
    success_url = reverse_lazy('inventory_list')
    def test_func(self):
        return self.request.user.is_staff

# Purchase order handling
class PurchaseOrderListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = PurchaseOrder
    template_name = 'admin/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    def test_func(self):
        return self.request.user.is_staff

class PurchaseOrderCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = PurchaseOrder
    fields = ['supplier', 'expected_warehouse']
    template_name = 'admin/purchase_order_form.html'
    def test_func(self):
        return self.request.user.is_staff

# Receive a purchase order (update stock)
def receive_purchase_order(request, po_pk):
    if not request.user.is_staff:
        return redirect('login')
    po = get_object_or_404(PurchaseOrder, pk=po_pk)
    if request.method == 'POST':
        with transaction.atomic():
            if po.status != 'SUBMITTED':
                messages.error(request, 'Can only receive submitted orders.')
                return redirect('purchase_order_detail', pk=po.pk)
            warehouse = po.expected_warehouse
            for poi in po.items.all():
                # Add stock to inventory
                inv, created = Inventory.objects.get_or_create(
                    product=poi.product, warehouse=warehouse,
                    defaults={'quantity': 0}
                )
                inv.quantity += poi.quantity
                inv.save()
                InventoryTransaction.objects.create(
                    transaction_type='PURCHASE',
                    product=poi.product,
                    warehouse=warehouse,
                    quantity_change=poi.quantity,
                    reference=f"PO #{po.id}",
                    performed_by=request.user
                )
            po.status = 'RECEIVED'
            po.save()
        messages.success(request, 'Purchase order received and inventory updated.')
        return redirect('purchase_order_list')
    return render(request, 'admin/purchase_order_receive.html', {'po': po})
