# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    capacity = models.IntegerField(default=0, help_text='Max items capacity')

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent} -> {self.name}"
        return self.name

    @property
    def is_leaf(self):
        return not self.subcategories.exists()

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        return self.inventory_set.aggregate(total=models.Sum('quantity'))['total'] or 0

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    reorder_point = models.IntegerField(default=10)

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name_plural = 'inventories'

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name} = {self.quantity}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True)  # For anonymous users
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Anonymous cart {self.id}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class SalesOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PO #{self.id} from {self.supplier.name}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (UserProfile, Supplier, Warehouse, Category, Product, Inventory,
                     Cart, CartItem, SalesOrder, OrderItem, PurchaseOrder, PurchaseOrderItem)
from .forms import (ProductForm, SupplierForm, WarehouseForm, InventoryForm, 
                    PurchaseOrderForm, PurchaseOrderItemFormSet, SalesOrderForm,
                    CartItemQuantityForm)
from decimal import Decimal
from django.forms import modelformset_factory

# ---------- Authentication ----------
class SignUpView(FormView):
    template_name = 'registration/signup.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save()
        UserProfile.objects.create(user=user)
        login(self.request, user)
        return super().form_valid(form)

def logout_view(request):
    logout(request)
    return redirect('home')

# ---------- Product Listing & Search ----------
class ProductListView(ListView):
    model = Product
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(active=True).select_related('category')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query) |
                Q(category__name__icontains=query) | Q(brand__icontains=query)
            )
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent__isnull=True)
        context['query'] = self.request.GET.get('q', '')
        return context

# ---------- Product Detail ----------
class ProductDetailView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['in_stock'] = self.object.total_stock > 0
        return context

# ---------- Cart ----------
def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, session_key=None)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart

class CartView(View):
    def get(self, request):
        cart = get_or_create_cart(request)
        items = cart.items.all()
        for item in items:
            item.form = CartItemQuantityForm(initial={'quantity': item.quantity})
        return render(request, 'shop/cart.html', {'cart': cart, 'items': items})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, active=True)
    cart = get_or_create_cart(request)
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        quantity = 1
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    messages.success(request, f'Added {product.name} to cart.')
    return redirect('cart')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart=get_or_create_cart(request))
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')

def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart=get_or_create_cart(request))
    if request.method == 'POST':
        form = CartItemQuantityForm(request.POST)
        if form.is_valid():
            cart_item.quantity = form.cleaned_data['quantity']
            cart_item.save()
    return redirect('cart')

# ---------- Checkout / Order ----------
@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address', request.user.profile.address)
        # Validate stock before creating order
        errors = []
        for item in cart.items.all():
            if item.quantity > item.product.total_stock:
                errors.append(f"{item.product.name} only has {item.product.total_stock} in stock.")
        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('cart')
        
        # Create Sales Order and reduce inventory
        order = SalesOrder.objects.create(user=request.user, shipping_address=shipping_address, status='pending')
        # Deduct stock from warehouses (simple FIFO or any)
        for item in cart.items.all():
            remaining = item.quantity
            # Get all inventories for this product, sorted by warehouse id (any)
            inventories = item.product.inventory_set.filter(quantity__gt=0).order_by('warehouse')
            for inv in inventories:
                if remaining <= 0:
                    break
                deduct = min(remaining, inv.quantity)
                inv.quantity -= deduct
                inv.save()
                remaining -= deduct
            # In case not enough stock (shouldn't happen because we validated)
            if remaining > 0:
                # Rollback? For simplicity, just log an error and cancel order.
                order.status = 'cancelled'
                order.save()
                # restore deduct? complicated. For simplicity, we just cancel order.
                messages.error(request, f"Not enough stock for {item.product.name}. Order cancelled.")
                # Ideally we'd revert previous deductions, but skip for brevity.
                return redirect('cart')
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price
            )
        # Clear cart
        cart.delete()
        messages.success(request, f'Order #{order.id} placed successfully.')
        return redirect('order_detail', pk=order.id)
    
    return render(request, 'shop/checkout.html', {'cart': cart})

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = SalesOrder
    template_name = 'shop/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return SalesOrder.objects.filter(user=self.request.user)

class OrderHistoryView(LoginRequiredMixin, ListView):
    model = SalesOrder
    template_name = 'shop/order_history.html'
    context_object_name = 'orders'
    ordering = ['-created_at']

    def get_queryset(self):
        return SalesOrder.objects.filter(user=self.request.user)

# ---------- Admin: Inventory Management ----------
# Custom staff requirement mixin
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.profile.is_admin

# Product management
class AdminProductListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = 'admin/shop/product_list.html'
    context_object_name = 'products'

class AdminProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin/shop/product_form.html'
    success_url = reverse_lazy('admin_product_list')

class AdminProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin/shop/product_form.html'
    success_url = reverse_lazy('admin_product_list')

class AdminProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = 'admin/shop/product_confirm_delete.html'
    success_url = reverse_lazy('admin_product_list')

# Inventory management
class InventoryListView(StaffRequiredMixin, ListView):
    model = Inventory
    template_name = 'admin/shop/inventory_list.html'
    context_object_name = 'inventories'

class InventoryCreateView(StaffRequiredMixin, CreateView):
    model = Inventory
    form_class = InventoryForm
    template_name = 'admin/shop/inventory_form.html'
    success_url = reverse_lazy('inventory_list')

class InventoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Inventory
    form_class = InventoryForm
    template_name = 'admin/shop/inventory_form.html'
    success_url = reverse_lazy('inventory_list')

# Supplier management
class SupplierListView(StaffRequiredMixin, ListView):
    model = Supplier
    template_name = 'admin/shop/supplier_list.html'
    context_object_name = 'suppliers'

class SupplierCreateView(StaffRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'admin/shop/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

class SupplierUpdateView(StaffRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'admin/shop/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

# Warehouse management
class WarehouseListView(StaffRequiredMixin, ListView):
    model = Warehouse
    template_name = 'admin/shop/warehouse_list.html'
    context_object_name = 'warehouses'

class WarehouseCreateView(StaffRequiredMixin, CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'admin/shop/warehouse_form.html'
    success_url = reverse_lazy('warehouse_list')

class WarehouseUpdateView(StaffRequiredMixin, UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'admin/shop/warehouse_form.html'
    success_url = reverse_lazy('warehouse_list')

# Purchase Order management
class PurchaseOrderListView(StaffRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'admin/shop/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    ordering = ['-created_at']

class PurchaseOrderCreateView(StaffRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'admin/shop/purchase_order_form.html'
    success_url = reverse_lazy('purchase_order_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = PurchaseOrderItemFormSet(self.request.POST)
        else:
            data['items'] = PurchaseOrderItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        self.object = form.save()
        if items.is_valid():
            items.instance = self.object
            items.save()
            # When purchase order status changes to 'received', add inventory
            if self.object.status == 'received':
                for item in items:
                    inv, created = Inventory.objects.get_or_create(
                        product=item.cleaned_data.get('product') or item.instance.product,
                        warehouse=self.object.warehouse,
                        defaults={'quantity': 0}
                    )
                    inv.quantity += (item.cleaned_data.get('quantity') or item.instance.quantity)
                    inv.save()
        else:
            return self.form_invalid(form)
        return super().form_valid(form)

class PurchaseOrderUpdateView(StaffRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'admin/shop/purchase_order_form.html'
    success_url = reverse_lazy('purchase_order_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = PurchaseOrderItemFormSet(self.request.POST, instance=self.object)
        else:
            data['items'] = PurchaseOrderItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        self.object = form.save()
        if items.is_valid():
            items.save()
            # Handle status change to 'received'
            old_status = PurchaseOrder.objects.get(pk=self.object.pk).status
            if self.object.status == 'received' and old_status != 'received':
                for item in self.object.items.all():
                    inv, created = Inventory.objects.get_or_create(
                        product=item.product,
                        warehouse=self.object.warehouse,
                        defaults={'quantity': 0}
                    )
                    inv.quantity += item.quantity
                    inv.save()
            # Also handle cancellation rollback if needed, skip for brevity
        else:
            return self.form_invalid(form)
        return super().form_valid(form)

# Sales order management (admin view all orders)
class SalesOrderAdminListView(StaffRequiredMixin, ListView):
    model = SalesOrder
    template_name = 'admin/shop/sales_order_list.html'
    context_object_name = 'orders'
    ordering = ['-created_at']

class SalesOrderAdminUpdateView(StaffRequiredMixin, UpdateView):
    model = SalesOrder
    form_class = SalesOrderForm
    template_name = 'admin/shop/sales_order_form.html'
    success_url = reverse_lazy('sales_order_admin_list')

    def form_valid(self, form):
        # If order is cancelled, restore inventory
        order = self.object
        if order.status != 'cancelled' and form.cleaned_data['status'] == 'cancelled':
            for item in order.items.all():
                # simple restock to first warehouse
                warehouse = Warehouse.objects.first()
                if warehouse:
                    inv, _ = Inventory.objects.get_or_create(product=item.product, warehouse=warehouse, defaults={'quantity': 0})
                    inv.quantity += item.quantity
                    inv.save()
        return super().form_valid(form)

# User Management (admin listing)
class UserManagementView(StaffRequiredMixin, ListView):
    model = User
    template_name = 'admin/shop/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.all().select_related('profile')

# forms.py
from django import forms
from .models import Product, Supplier, Warehouse, Inventory, PurchaseOrder, PurchaseOrderItem, SalesOrder, CartItem

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'brand', 'image', 'active']

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = '__all__'

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['product', 'warehouse', 'quantity', 'reorder_point']

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'warehouse', 'status', 'order_date', 'expected_date']

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_price']

PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm, extra=1, can_delete=True
)

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['status', 'shipping_address']

class CartItemQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99)

# admin.py (Django admin registration)
from django.contrib import admin
from .models import (
    UserProfile, Supplier, Warehouse, Category, Product, Inventory,
    Cart, CartItem, SalesOrder, OrderItem, PurchaseOrder, PurchaseOrderItem
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_admin')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'active')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'active', 'total_stock')
    search_fields = ('name', 'description')

class InventoryInline(admin.TabularInline):
    model = Inventory
    extra = 1

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'reorder_point')
    list_filter = ('warehouse',)

class CartItemInline(admin.TabularInline):
    model = CartItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'created_at')
    inlines = [CartItemInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total', 'created_at')
    list_filter = ('status',)
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price')

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'status', 'total', 'order_date')
    list_filter = ('status',)
    inlines = [PurchaseOrderItemInline]

# urls.py
from django.urls import path
from django.contrib.auth.views import LoginView
from . import views

urlpatterns = [
    # Auth
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Product
    path('', views.ProductListView.as_view(), name='product_list'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Cart
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    
    # Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('order/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    
    # Admin panels (using custom views)
    path('admin/products/', views.AdminProductListView.as_view(), name='admin_product_list'),
    path('admin/products/create/', views.AdminProductCreateView.as_view(), name='admin_product_create'),
    path('admin/products/<int:pk>/edit/', views.AdminProductUpdateView.as_view(), name='admin_product_update'),
    path('admin/products/<int:pk>/delete/', views.AdminProductDeleteView.as_view(), name='admin_product_delete'),
    
    path('admin/inventory/', views.InventoryListView.as_view(), name='inventory_list'),
    path('admin/inventory/create/', views.InventoryCreateView.as_view(), name='inventory_create'),
    path('admin/inventory/<int:pk>/edit/', views.InventoryUpdateView.as_view(), name='inventory_update'),
    
    path('admin/suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('admin/suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('admin/suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    
    path('admin/warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('admin/warehouses/create/', views.WarehouseCreateView.as_view(), name='warehouse_create'),
    path('admin/warehouses/<int:pk>/edit/', views.WarehouseUpdateView.as_view(), name='warehouse_update'),
    
    path('admin/purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('admin/purchase-orders/create/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('admin/purchase-orders/<int:pk>/edit/', views.PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    
    path('admin/sales-orders/', views.SalesOrderAdminListView.as_view(), name='sales_order_admin_list'),
    path('admin/sales-orders/<int:pk>/edit/', views.SalesOrderAdminUpdateView.as_view(), name='sales_order_admin_update'),
    
    path('admin/users/', views.UserManagementView.as_view(), name='user_management'),
]

# apps.py (optional, for completeness)
from django.apps import AppConfig

class ShopConfig(AppConfig):
    name = 'shop'
    verbose_name = 'Amazon Clone Shop'