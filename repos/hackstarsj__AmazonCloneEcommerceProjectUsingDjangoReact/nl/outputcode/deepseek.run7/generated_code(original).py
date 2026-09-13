# =============================================
# models.py
# =============================================
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import MinValueValidator
from django.utils import timezone

class User(AbstractUser):
    """
    Custom user model with additional fields for e-commerce.
    """
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_supplier = models.BooleanField(default=False)  # if the user is a supplier contact (not used for auth)

    def __str__(self):
        return self.email or self.username

class Category(models.Model):
    """
    Hierarchical product categories.
    """
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Supplier(models.Model):
    """
    External suppliers for purchase orders.
    """
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name

class Warehouse(models.Model):
    """
    Physical warehouses for inventory storage.
    """
    name = models.CharField(max_length=100)
    location = models.TextField()
    capacity = models.PositiveIntegerField(default=0)  # optional capacity

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Product sold on the platform.
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)  # optional unique identifier
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        """
        Aggregates stock across all warehouses.
        """
        return self.inventories.aggregate(total=models.Sum('quantity'))['total'] or 0

class Inventory(models.Model):
    """
    Stock quantity of a product in a specific warehouse.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name_plural = "Inventories"

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"

    def clean(self):
        if self.quantity < 0:
            raise ValidationError("Inventory quantity cannot be negative.")

class InventoryTransaction(models.Model):
    """
    Tracks all stock changes (shipsments, adjustments, etc.)
    """
    TRANSACTION_TYPES = (
        ('PURCHASE', 'Purchase Order Received'),
        ('SALE', 'Sale Order Fulfilled'),
        ('ADJUST', 'Manual Adjustment'),
        ('RETURN', 'Customer Return'),
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity_change = models.IntegerField()  # positive for in, negative for out
    reference = models.CharField(max_length=100, blank=True, null=True)  # e.g., order number
    timestamp = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.product.name} ({self.quantity_change})"

class Cart(models.Model):
    """
    Shopping cart associated with a user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    """
    Individual item in a cart.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity

class Order(models.Model):
    """
    Customer sales order.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    order_date = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):
    """
    A product line within an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)  # denormalized for history
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)  # from which warehouse the stock was deducted

    @property
    def item_total(self):
        return self.price * self.quantity

class PurchaseOrder(models.Model):
    """
    Purchase order to a supplier.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    expected_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"PO #{self.id} to {self.supplier.company_name}"

class PurchaseOrderItem(models.Model):
    """
    Line item of a purchase order.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_cost * self.quantity

# =============================================
# admin.py
# =============================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Category, Supplier, Warehouse, Product,
    Inventory, InventoryTransaction, Cart, CartItem,
    Order, OrderItem, PurchaseOrder, PurchaseOrderItem
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'address', 'is_supplier')}),
    )

class InventoryInline(admin.TabularInline):
    model = Inventory
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'total_stock', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'sku')
    inlines = [InventoryInline]

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)
admin.site.register(Product, ProductAdmin)
admin.site.register(Inventory)
admin.site.register(InventoryTransaction)
admin.site.register(Cart)
admin.site.register(CartItem)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'order_date', 'total_price')
    list_filter = ('status',)
    inlines = [OrderItemInline]

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'status', 'order_date', 'total_cost')
    inlines = [PurchaseOrderItemInline]

admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(PurchaseOrderItem)

# =============================================
# forms.py
# =============================================
from django import forms
from .models import CartItem

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']

class OrderCheckoutForm(forms.Form):
    shipping_address = forms.CharField(widget=forms.Textarea)
    payment_method = forms.ChoiceField(choices=[('dummy', 'Dummy Payment')])  # placeholder

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

# =============================================
# urls.py (store app)
# =============================================
from django.urls import path
from . import views

urlpatterns = [
    # Product browsing
    path('', views.ProductListView.as_view(), name='product_list'),
    path('category/<slug:category_slug>/', views.ProductListView.as_view(), name='product_list_by_category'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    # Checkout & orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    # Admin inventory
    path('admin/inventory/', views.InventoryListView.as_view(), name='inventory_list'),
    path('admin/inventory/<int:pk>/edit/', views.InventoryUpdateView.as_view(), name='inventory_edit'),
    # Purchase orders
    path('admin/purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('admin/purchase-orders/new/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('admin/purchase-orders/<int:po_pk>/receive/', views.receive_purchase_order, name='purchase_order_receive'),
]

# =============================================
# settings.py additions (only relevant parts)
# =============================================
INSTALLED_APPS = [
    ...
    'store',
    ...
]

AUTH_USER_MODEL = 'store.User'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Media files (for product images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# You'll need to set up static and media serving in urls.py (project level) and run migrations.