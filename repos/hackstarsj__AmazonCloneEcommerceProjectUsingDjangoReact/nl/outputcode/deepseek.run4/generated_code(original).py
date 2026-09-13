# amazon_clone/manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amazon_clone.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

# amazon_clone/amazon_clone/__init__.py
# empty

# amazon_clone/amazon_clone/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-in-production'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'store',
    'cart',
    'orders',
    'inventory',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'amazon_clone.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'amazon_clone.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'accounts.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# amazon_clone/amazon_clone/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('store/', include('store.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('inventory/', include('inventory.urls')),
    path('', include('store.urls')),  # root homepage
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else '')

# amazon_clone/amazon_clone/wsgi.py
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amazon_clone.settings')
application = get_wsgi_application()

# amazon_clone/accounts/__init__.py
# empty

# amazon_clone/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_seller = models.BooleanField(default=False)

    def __str__(self):
        return self.username

# amazon_clone/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = User

# amazon_clone/accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('store:product_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('store:product_list')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('store:product_list')

# amazon_clone/accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]

# amazon_clone/store/__init__.py
# empty

# amazon_clone/store/models.py
from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def total_stock(self):
        from inventory.models import Inventory
        return Inventory.objects.filter(product=self).aggregate(total=models.Sum('quantity'))['total'] or 0

# amazon_clone/store/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Product, Category
from cart.cart import Cart

def product_list(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    products = Product.objects.all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # include subcategories
        descendants = category.get_descendants(include_self=True)
        products = products.filter(category__in=descendants)
    categories = Category.objects.filter(parent=None)
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'query': query
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'store/product_detail.html', {'product': product})

# amazon_clone/store/urls.py
from django.urls import path
from . import views

app_name = 'store'
urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
]

# amazon_clone/store/admin.py
from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug', 'parent')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug', 'category', 'price', 'created_at')
    search_fields = ('name', 'description')

# amazon_clone/cart/__init__.py
# empty

# amazon_clone/cart/cart.py
from decimal import Decimal
from django.conf import settings
from store.models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart_copy = self.cart.copy()
        for product in products:
            cart_copy[str(product.id)]['product'] = product
        for item in cart_copy.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def save(self):
        self.session.modified = True

# amazon_clone/cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from store.models import Product
from .cart import Cart
from .forms import CartAddProductForm

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product,
                 quantity=cd['quantity'],
                 override_quantity=cd['override'])
    return redirect('cart:cart_detail')

@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})

# amazon_clone/cart/forms.py
from django import forms

PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 21)]

class CartAddProductForm(forms.Form):
    quantity = forms.TypedChoiceField(choices=PRODUCT_QUANTITY_CHOICES, coerce=int)
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

# amazon_clone/cart/urls.py
from django.urls import path
from . import views

app_name = 'cart'
urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
]

# amazon_clone/cart/context_processors.py
from .cart import Cart

def cart_processor(request):
    return {'cart': Cart(request)}

# add to settings templates context_processors:
# 'cart.context_processors.cart_processor'

# amazon_clone/orders/__init__.py
# empty

# amazon_clone/orders/models.py
from django.db import models
from django.conf import settings
from store.models import Product

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'Order {self.id}'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity}x {self.product.name}'

    def get_cost(self):
        return self.price * self.quantity

# amazon_clone/orders/forms.py
from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'address', 'phone', 'city']

# amazon_clone/orders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from inventory.models import Inventory

@login_required
def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total = cart.get_total_price()
            order.save()
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
                # Deduct from default warehouse (first warehouse)
                warehouse = Inventory.get_default_warehouse()
                if warehouse:
                    Inventory.decrease_stock(item['product'], warehouse, item['quantity'])
            cart.clear()
            return render(request, 'orders/created.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'orders/create.html', {'cart': cart, 'form': form})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/detail.html', {'order': order})

# amazon_clone/orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'
urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('history/', views.order_history, name='order_history'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
]

# amazon_clone/inventory/__init__.py
# empty

# amazon_clone/inventory/models.py
from django.db import models
from django.core.exceptions import ValidationError
from store.models import Product

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_records')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name_plural = 'inventories'

    def __str__(self):
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}'

    @staticmethod
    def get_default_warehouse():
        return Warehouse.objects.first()

    @staticmethod
    def decrease_stock(product, warehouse, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        inv = Inventory.objects.filter(product=product, warehouse=warehouse).first()
        if not inv:
            raise ValidationError(f"No inventory for {product.name} in {warehouse.name}")
        if inv.quantity < quantity:
            raise ValidationError(f"Insufficient stock for {product.name}")
        inv.quantity -= quantity
        inv.save()

    @staticmethod
    def increase_stock(product, warehouse, quantity):
        inv, created = Inventory.objects.get_or_create(product=product, warehouse=warehouse)
        inv.quantity += quantity
        inv.save()

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'PO-{self.id} ({self.supplier.name})'

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def total_price(self):
        return self.quantity * self.unit_price

# amazon_clone/inventory/views.py
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

# amazon_clone/inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'
urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/<int:inv_id>/update/', views.inventory_update, name='inventory_update'),
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:po_id>/receive/', views.purchase_order_receive, name='purchase_order_receive'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
]

# Create a separate admin.py for inventory to register models in Django admin
# amazon_clone/inventory/admin.py
from django.contrib import admin
from .models import Warehouse, Supplier, Inventory, PurchaseOrder, PurchaseOrderItem

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone')

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity')
    list_filter = ('warehouse',)

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    inlines = [PurchaseOrderItemInline]
    list_display = ('id', 'supplier', 'warehouse', 'order_date', 'expected_delivery', 'status')

# Templates:
# base.html
# amazon_clone/templates/base.html
<!DOCTYPE html>
<html>
<head>
    <title>Amazon Clone</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
      <a class="navbar-brand" href="{% url 'store:product_list' %}">AmazonClone</a>
      <div class="collapse navbar-collapse">
        <ul class="navbar-nav me-auto">
          <li class="nav-item"><a class="nav-link" href="{% url 'store:product_list' %}">Home</a></li>
          {% if user.is_staff %}
          <li class="nav-item"><a class="nav-link" href="{% url 'inventory:admin_dashboard' %}">Admin</a></li>
          {% endif %}
        </ul>
        <ul class="navbar-nav">
          <li class="nav-item"><a class="nav-link" href="{% url 'cart:cart_detail' %}">Cart ({{ cart|length }})</a></li>
          {% if user.is_authenticated %}
          <li class="nav-item"><a class="nav-link" href="{% url 'orders:order_history' %}">My Orders</a></li>
          <li class="nav-item"><a class="nav-link" href="{% url 'accounts:logout' %}">Logout</a></li>
          {% else %}
          <li class="nav-item"><a class="nav-link" href="{% url 'accounts:login' %}">Login</a></li>
          <li class="nav-item"><a class="nav-link" href="{% url 'accounts:signup' %}">Sign Up</a></li>
          {% endif %}
        </ul>
      </div>
    </div>
  </nav>
  <div class="container mt-4">
    {% if messages %}
      {% for message in messages %}
        <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endif %}
    {% block content %}
    {% endblock %}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

# accounts/signup.html
{% extends 'base.html' %}
{% block content %}
<h2>Sign Up</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Sign Up</button>
</form>
{% endblock %}

# accounts/login.html
{% extends 'base.html' %}
{% block content %}
<h2>Login</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Login</button>
</form>
{% endblock %}

# store/product_list.html
{% extends 'base.html' %}
{% block content %}
<div class="row">
  <div class="col-md-3">
    <h5>Categories</h5>
    <ul class="list-group">
      <li class="list-group-item {% if not selected_category %}active{% endif %}">
        <a href="{% url 'store:product_list' %}" class="text-decoration-none">All</a>
      </li>
      {% for cat in categories %}
        <li class="list-group-item {% if selected_category == cat.slug %}active{% endif %}">
          <a href="?category={{ cat.slug }}" class="text-decoration-none">{{ cat.name }}</a>
        </li>
      {% endfor %}
    </ul>
  </div>
  <div class="col-md-9">
    <form class="mb-3">
      <input type="text" name="q" class="form-control" placeholder="Search products..." value="{{ query }}">
      <button class="btn btn-outline-secondary mt-2" type="submit">Search</button>
    </form>
    <div class="row">
      {% for product in products %}
        <div class="col-md-4 mb-4">
          <div class="card h-100">
            {% if product.image %}
              <img src="{{ product.image.url }}" class="card-img-top" alt="{{ product.name }}">
            {% endif %}
            <div class="card-body">
              <h5 class="card-title">{{ product.name }}</h5>
              <p class="card-text">${{ product.price }}</p>
              <a href="{{ product.get_absolute_url }}" class="btn btn-primary">View Details</a>
            </div>
          </div>
        </div>
      {% empty %}
        <p>No products found.</p>
      {% endfor %}
    </div>
  </div>
</div>
{% endblock %}

# store/product_detail.html
{% extends 'base.html' %}
{% block content %}
<div class="row">
  <div class="col-md-6">
    {% if product.image %}
      <img src="{{ product.image.url }}" class="img-fluid" alt="{{ product.name }}">
    {% endif %}
  </div>
  <div class="col-md-6">
    <h1>{{ product.name }}</h1>
    <p class="lead">${{ product.price }}</p>
    <p>{{ product.description }}</p>
    <p><strong>Category:</strong> {{ product.category.name }}</p>
    <p><strong>In Stock:</strong> {{ product.total_stock }}</p>
    <form action="{% url 'cart:cart_add' product.id %}" method="post">
      {% csrf_token %}
      {{ cart_add_form.as_p }}
      <button type="submit" class="btn btn-success">Add to Cart</button>
    </form>
  </div>
</div>
{% endblock %}

# cart/detail.html
{% extends 'base.html' %}
{% block content %}
<h2>Your Shopping Cart</h2>
{% if cart|length == 0 %}
  <p>Your cart is empty.</p>
{% else %}
  <table class="table">
    <thead>
      <tr>
        <th>Product</th>
        <th>Price</th>
        <th>Quantity</th>
        <th>Total</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {% for item in cart %}
        <tr>
          <td>{{ item.product.name }}</td>
          <td>${{ item.price }}</td>
          <td>{{ item.quantity }}</td>
          <td>${{ item.total_price }}</td>
          <td>
            <form action="{% url 'cart:cart_remove' item.product.id %}" method="post">
              {% csrf_token %}
              <button class="btn btn-danger btn-sm">Remove</button>
            </form>
          </td>
        </tr>
      {% endfor %}
    </tbody>
    <tfoot>
      <tr>
        <td colspan="4"><strong>Total</strong></td>
        <td>${{ cart.get_total_price }}</td>
      </tr>
    </tfoot>
  </table>
  <a href="{% url 'orders:order_create' %}" class="btn btn-primary">Proceed to Checkout</a>
{% endif %}
{% endblock %}

# orders/create.html
{% extends 'base.html' %}
{% block content %}
<h2>Checkout</h2>
<div class="row">
  <div class="col-md-8">
    <form method="post">
      {% csrf_token %}
      {{ form.as_p }}
      <button type="submit" class="btn btn-success">Place Order</button>
    </form>
  </div>
  <div class="col-md-4">
    <h4>Order Summary</h4>
    <ul class="list-group">
      {% for item in cart %}
        <li class="list-group-item d-flex justify-content-between">
          <span>{{ item.product.name }} (x{{ item.quantity }})</span>
          <span>${{ item.total_price }}</span>
        </li>
      {% endfor %}
      <li class="list-group-item d-flex justify-content-between">
        <strong>Total</strong>
        <strong>${{ cart.get_total_price }}</strong>
      </li>
    </ul>
  </div>
</div>
{% endblock %}

# orders/created.html
{% extends 'base.html' %}
{% block content %}
<div class="alert alert-success">
  <h2>Order placed successfully!</h2>
  <p>Your order ID is <strong>#{{ order.id }}</strong>.</p>
  <a href="{% url 'orders:order_history' %}" class="btn btn-primary">View Orders</a>
</div>
{% endblock %}

# orders/history.html
{% extends 'base.html' %}
{% block content %}
<h2>Order History</h2>
{% if orders %}
  <table class="table">
    <thead>
      <tr>
        <th>Order ID</th>
        <th>Date</th>
        <th>Status</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
      {% for order in orders %}
        <tr>
          <td><a href="{% url 'orders:order_detail' order.id %}">#{{ order.id }}</a></td>
          <td>{{ order.created }}</td>
          <td>{{ order.get_status_display }}</td>
          <td>${{ order.total }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <p>No orders yet.</p>
{% endif %}
{% endblock %}

# orders/detail.html
{% extends 'base.html' %}
{% block content %}
<h2>Order #{{ order.id }}</h2>
<p>Status: {{ order.get_status_display }}</p>
<p>Date: {{ order.created }}</p>
<p>Total: ${{ order.total }}</p>
<h4>Items:</h4>
<ul>
  {% for item in order.items.all %}
    <li>{{ item.product.name }} - {{ item.quantity }} x ${{ item.price }}</li>
  {% endfor %}
</ul>
{% endblock %}

# inventory/admin_dashboard.html
{% extends 'base.html' %}
{% block content %}
<h2>Admin Dashboard</h2>
<div class="row">
  <div class="col-md-3">
    <div class="card text-white bg-primary mb-3">
      <div class="card-body">
        <h5 class="card-title">Total Products</h5>
        <p class="card-text">{{ total_products }}</p>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card text-white bg-success mb-3">
      <div class="card-body">
        <h5 class="card-title">Total Orders</h5>
        <p class="card-text">{{ total_orders }}</p>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card text-white bg-warning mb-3">
      <div class="card-body">
        <h5 class="card-title">Low Stock Items</h5>
        <p class="card-text">{{ low_stock_count }}</p>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card text-white bg-info mb-3">
      <div class="card-body">
        <h5 class="card-title">Pending POs</h5>
        <p class="card-text">{{ pending_po_count }}</p>
      </div>
    </div>
  </div>
</div>
<h4>Recent Orders</h4>
<table class="table table-striped">
  <thead>
    <tr><th>ID</th><th>User</th><th>Date</th><th>Total</th><th>Status</th></tr>
  </thead>
  <tbody>
    {% for order in recent_orders %}
      <tr>
        <td>#{{ order.id }}</td>
        <td>{{ order.user.username }}</td>
        <td>{{ order.created }}</td>
        <td>${{ order.total }}</td>
        <td>{{ order.get_status_display }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}

# inventory/inventory_list.html
{% extends 'base.html' %}
{% block content %}
<h2>Inventory Management</h2>
<table class="table">
  <thead>
    <tr><th>Product</th><th>Warehouse</th><th>Quantity</th><th>Update</th></tr>
  </thead>
  <tbody>
    {% for inv in inventories %}
      <tr>
        <td>{{ inv.product.name }}</td>
        <td>{{ inv.warehouse.name }}</td>
        <td>{{ inv.quantity }}</td>
        <td>
          <form method="post" action="{% url 'inventory:inventory_update' inv.id %}">
            {% csrf_token %}
            <input type="number" name="quantity" value="{{ inv.quantity }}" min="0" class="form-control form-control-sm d-inline-block" style="width:80px;">
            <button type="submit" class="btn btn-sm btn-primary">Update</button>
          </form>
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}

# inventory/purchase_order_list.html
{% extends 'base.html' %}
{% block content %}
<h2>Purchase Orders</h2>
<a href="{% url 'inventory:purchase_order_create' %}" class="btn btn-primary mb-3">Create New PO</a>
<table class="table">
  <thead>
    <tr><th>ID</th><th>Supplier</th><th>Warehouse</th><th>Status</th><th>Date</th><th>Actions</th></tr>
  </thead>
  <tbody>
    {% for po in purchase_orders %}
      <tr>
        <td>#{{ po.id }}</td>
        <td>{{ po.supplier.name }}</td>
        <td>{{ po.warehouse.name }}</td>
        <td>{{ po.get_status_display }}</td>
        <td>{{ po.order_date }}</td>
        <td>
          <a href="{% url 'inventory:purchase_order_detail' po.id %}" class="btn btn-sm btn-info">View</a>
          {% if po.status == 'pending' %}
            <a href="{% url 'inventory:purchase_order_receive' po.id %}" class="btn btn-sm btn-success">Receive</a>
          {% endif %}
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}

# inventory/purchase_order_create.html
{% extends 'base.html' %}
{% block content %}
<h2>Create Purchase Order</h2>
<form method="post">
  {% csrf_token %}
  <div class="mb-3">
    <label>Supplier</label>
    <select name="supplier" class="form-select" required>
      <option value="">--</option>
      {% for s in suppliers %}
        <option value="{{ s.id }}">{{ s.name }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label>Warehouse</label>
    <select name="warehouse" class="form-select" required>
      <option value="">--</option>
      {% for w in warehouses %}
        <option value="{{ w.id }}">{{ w.name }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="mb-3">
    <label>Expected Delivery</label>
    <input type="date" name="expected_delivery" class="form-control">
  </div>
  <div class="mb-3">
    <label>Notes</label>
    <textarea name="notes" class="form-control"></textarea>
  </div>
  <h5>Items</h5>
  <div id="items-container">
    <div class="row mb-2 item-row">
      <div class="col">
        <select name="product" class="form-select" required>
          <option value="">--</option>
          {% for p in products %}
            <option value="{{ p.id }}">{{ p.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col">
        <input type="number" name="quantity" placeholder="Qty" class="form-control" min="1" required>
      </div>
      <div class="col">
        <input type="number" step="0.01" name="unit_price" placeholder="Unit Price" class="form-control" required>
      </div>
    </div>
  </div>
  <button type="button" id="add-item" class="btn btn-sm btn-secondary mb-3">Add Item</button>
  <br>
  <button type="submit" class="btn btn-primary">Create Purchase Order</button>
</form>
<script>
  document.getElementById('add-item').addEventListener('click', function(){
    var container = document.getElementById('items-container');
    var row = container.querySelector('.item-row').cloneNode(true);
    container.appendChild(row);
  });
</script>
{% endblock %}

# inventory/purchase_order_detail.html
{% extends 'base.html' %}
{% block content %}
<h2>Purchase Order #{{ po.id }}</h2>
<p>Supplier: {{ po.supplier.name }}</p>
<p>Warehouse: {{ po.warehouse.name }}</p>
<p>Status: {{ po.get_status_display }}</p>
<p>Date: {{ po.order_date }}</p>
<p>Expected Delivery: {{ po.expected_delivery }}</p>
<p>Notes: {{ po.notes }}</p>
<h4>Items</h4>
<table class="table">
  <thead>
    <tr><th>Product</th><th>Quantity</th><th>Unit Price</th><th>Total</th></tr>
  </thead>
  <tbody>
    {% for item in po.items.all %}
      <tr>
        <td>{{ item.product.name }}</td>
        <td>{{ item.quantity }}</td>
        <td>${{ item.unit_price }}</td>
        <td>${{ item.total_price }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% if po.status == 'pending' %}
  <a href="{% url 'inventory:purchase_order_receive' po.id %}" class="btn btn-success">Receive</a>
{% endif %}
{% endblock %}

# inventory/supplier_list.html
{% extends 'base.html' %}
{% block content %}
<h2>Suppliers</h2>
<table class="table">
  <thead><tr><th>Name</th><th>Contact</th><th>Email</th><th>Phone</th></tr></thead>
  <tbody>
    {% for supplier in suppliers %}
      <tr>
        <td>{{ supplier.name }}</td>
        <td>{{ supplier.contact_person }}</td>
        <td>{{ supplier.email }}</td>
        <td>{{ supplier.phone }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}

# inventory/warehouse_list.html
{% extends 'base.html' %}
{% block content %}
<h2>Warehouses</h2>
<ul class="list-group">
  {% for wh in warehouses %}
    <li class="list-group-item">{{ wh.name }} - {{ wh.location }}</li>
  {% endfor %}
</ul>
{% endblock %}