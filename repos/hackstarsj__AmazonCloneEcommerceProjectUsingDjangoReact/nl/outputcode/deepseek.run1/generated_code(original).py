# file: manage.py
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

# file: amazon_clone/__init__.py

# file: amazon_clone/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production!@#$%^&*()'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Custom apps
    'accounts',
    'products',
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
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# file: amazon_clone/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# file: amazon_clone/wsgi.py
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amazon_clone.settings')
application = get_wsgi_application()

# file: amazon_clone/asgi.py
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amazon_clone.settings')
application = get_asgi_application()

# file: accounts/__init__.py

# file: accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# file: accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    city = forms.CharField(max_length=100, required=False)
    postal_code = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
                city=self.cleaned_data['city'],
                postal_code=self.cleaned_data['postal_code']
            )
        return user

# file: accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm

def signup(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            messages.success(request, f'Account created for {username}!')
            return redirect('product_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

# file: accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
]

# file: accounts/admin.py
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city')

# file: products/__init__.py

# file: products/models.py
from django.db import models
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    @property
    def available_quantity(self):
        """Total stock across all warehouses."""
        from inventory.models import Stock
        return Stock.objects.filter(product=self).aggregate(models.Sum('quantity'))['quantity__sum'] or 0

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"

# file: products/forms.py (optional)

# file: products/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product

def product_list(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    products = Product.objects.all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category__in=category.get_descendants(include_self=True))
    categories = Category.objects.filter(parent=None)
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_slug,
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'products/product_detail.html', {'product': product})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category__in=category.get_descendants(include_self=True))
    return render(request, 'products/category_detail.html', {'category': category, 'products': products})

# Helper method on Category model (added via monkey patching or model method)
def get_descendants(self, include_self=False):
    descendants = []
    if include_self:
        descendants.append(self)
    for child in self.children.all():
        descendants.extend(child.get_descendants(include_self=True))
    return descendants

# Monkey-patch
Category.get_descendants = get_descendants

# file: products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
]

# file: products/admin.py
from django.contrib import admin
from .models import Category, Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'available_quantity')
    inlines = [ProductImageInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

# file: cart/__init__.py

# file: cart/models.py
from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def total_price(self):
        return self.product.price * self.quantity

# file: cart/forms.py
from django import forms
from .models import CartItem

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']

# file: cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Cart, CartItem

@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'cart/cart_detail.html', {'cart': cart})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f'{product.name} added to cart.')
    return redirect('product_list')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} removed from cart.')
    return redirect('cart_detail')

@login_required
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
    return redirect('cart_detail')

# file: cart/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:item_id>/', views.update_cart, name='update_cart'),
]

# file: cart/admin.py
from django.contrib import admin
from .models import Cart, CartItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    pass

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    pass

# file: orders/__init__.py

# file: orders/models.py
from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (order {self.order.id})"

# file: orders/views.py
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

# file: orders/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('history/', views.order_history, name='order_history'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
]

# file: orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total', 'created_at')
    list_filter = ('status',)
    inlines = [OrderItemInline]

# file: inventory/__init__.py

# file: inventory/models.py
from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.TextField()
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_warehouses')

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class ProductSupplier(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='product_suppliers')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    lead_time_days = models.PositiveIntegerField(default=7)

    class Meta:
        unique_together = ('product', 'supplier')

    def __str__(self):
        return f"{self.supplier.name} supplies {self.product.name}"

class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"PO #{self.id} - {self.supplier.name}"

    def receive(self):
        """Mark as received and update stock."""
        if self.status != 'ordered':
            raise ValueError("Only ordered POs can be received.")
        warehouse = self.warehouse
        if not warehouse:
            raise ValueError("Warehouse must be set to receive inventory.")
        for item in self.items.all():
            stock, _ = Stock.objects.get_or_create(product=item.product, warehouse=warehouse, defaults={'quantity': 0})
            stock.quantity += item.quantity
            stock.save()
        self.status = 'received'
        self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ {self.unit_cost}"

# file: inventory/admin.py
from django.contrib import admin
from .models import Warehouse, Supplier, ProductSupplier, Stock, PurchaseOrder, PurchaseOrderItem

class StockInline(admin.TabularInline):
    model = Stock

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'manager')
    inlines = [StockInline]

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    pass

@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'cost_price', 'lead_time_days')

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'warehouse', 'status', 'total_cost', 'order_date')
    list_filter = ('status', 'supplier')
    inlines = [PurchaseOrderItemInline]
    actions = ['mark_as_received']

    def mark_as_received(self, request, queryset):
        for po in queryset.filter(status='ordered'):
            try:
                po.receive()
                self.message_user(request, f"PO #{po.id} received.")
            except ValueError as e:
                self.message_user(request, f"Error receiving PO #{po.id}: {e}", level='error')
    mark_as_received.short_description = "Mark selected purchase orders as received"

# file: static/css/base.css (optional)

# file: templates/base.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Amazon Clone{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
        <a class="navbar-brand" href="{% url 'product_list' %}">Amazon Clone</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
                <li class="nav-item">
                    <a class="nav-link" href="{% url 'product_list' %}">Home</a>
                </li>
            </ul>
            <ul class="navbar-nav">
                {% if user.is_authenticated %}
                    <li class="nav-item"><a class="nav-link" href="{% url 'cart_detail' %}">Cart</a></li>
                    <li class="nav-item"><a class="nav-link" href="{% url 'order_history' %}">Orders</a></li>
                    <li class="nav-item"><a class="nav-link" href="{% url 'profile' %}">Profile</a></li>
                    <li class="nav-item"><a class="nav-link" href="{% url 'logout' %}">Logout</a></li>
                {% else %}
                    <li class="nav-item"><a class="nav-link" href="{% url 'login' %}">Login</a></li>
                    <li class="nav-item"><a class="nav-link" href="{% url 'signup' %}">Sign Up</a></li>
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
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        {% endfor %}
    {% endif %}
    {% block content %}{% endblock %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

# file: templates/accounts/login.html
{% extends 'base.html' %}
{% block title %}Login{% endblock %}
{% block content %}
<h2>Login</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Login</button>
</form>
<p>Don't have an account? <a href="{% url 'signup' %}">Sign up</a></p>
{% endblock %}

# file: templates/accounts/signup.html
{% extends 'base.html' %}
{% block title %}Sign Up{% endblock %}
{% block content %}
<h2>Sign Up</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Sign Up</button>
</form>
{% endblock %}

# file: templates/accounts/profile.html
{% extends 'base.html' %}
{% block title %}Profile{% endblock %}
{% block content %}
<h2>Profile</h2>
<p>Username: {{ user.username }}</p>
<p>Email: {{ user.email }}</p>
<p>Phone: {{ user.profile.phone }}</p>
<p>Address: {{ user.profile.address }}, {{ user.profile.city }} {{ user.profile.postal_code }}</p>
{% endblock %}

# file: templates/products/product_list.html
{% extends 'base.html' %}
{% block title %}Products{% endblock %}
{% block content %}
<div class="row">
    <div class="col-md-3">
        <h4>Categories</h4>
        <ul class="list-group">
            {% for cat in categories %}
                <li class="list-group-item"><a href="{% url 'category_detail' cat.slug %}">{{ cat.name }}</a></li>
            {% endfor %}
        </ul>
    </div>
    <div class="col-md-9">
        <form method="get" class="mb-3">
            <div class="input-group">
                <input type="text" name="q" class="form-control" placeholder="Search products..." value="{{ query }}">
                <button class="btn btn-outline-secondary" type="submit">Search</button>
            </div>
        </form>
        <div class="row">
            {% for product in products %}
                <div class="col-md-4 mb-3">
                    <div class="card">
                        {% if product.images.first %}
                            <img src="{{ product.images.first.image.url }}" class="card-img-top" alt="{{ product.images.first.alt_text }}">
                        {% endif %}
                        <div class="card-body">
                            <h5 class="card-title">{{ product.name }}</h5>
                            <p class="card-text">${{ product.price }}</p>
                            <a href="{% url 'product_detail' product.slug %}" class="btn btn-primary">View</a>
                            <a href="{% url 'add_to_cart' product.id %}" class="btn btn-success">Add to Cart</a>
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

# file: templates/products/product_detail.html
{% extends 'base.html' %}
{% block title %}{{ product.name }}{% endblock %}
{% block content %}
<div class="row">
    <div class="col-md-6">
        {% if product.images.first %}
            <img src="{{ product.images.first.image.url }}" class="img-fluid" alt="{{ product.images.first.alt_text }}">
        {% endif %}
    </div>
    <div class="col-md-6">
        <h1>{{ product.name }}</h1>
        <p class="lead">${{ product.price }}</p>
        <p>{{ product.description }}</p>
        <p>Available stock: {{ product.available_quantity }}</p>
        {% if user.is_authenticated %}
            <a href="{% url 'add_to_cart' product.id %}" class="btn btn-success">Add to Cart</a>
        {% else %}
            <a href="{% url 'login' %}" class="btn btn-warning">Login to buy</a>
        {% endif %}
    </div>
</div>
{% endblock %}

# file: templates/products/category_detail.html
{% extends 'base.html' %}
{% block title %}{{ category.name }}{% endblock %}
{% block content %}
<h1>{{ category.name }}</h1>
{% if category.description %}<p>{{ category.description }}</p>{% endif %}
{% if category.children.all %}
<h4>Subcategories:</h4>
<ul>
    {% for child in category.children.all %}
        <li><a href="{% url 'category_detail' child.slug %}">{{ child.name }}</a></li>
    {% endfor %}
</ul>
{% endif %}
<h3>Products</h3>
<div class="row">
    {% for product in products %}
        <div class="col-md-4 mb-3">
            <div class="card">
                {% if product.images.first %}
                    <img src="{{ product.images.first.image.url }}" class="card-img-top" alt="{{ product.images.first.alt_text }}">
                {% endif %}
                <div class="card-body">
                    <h5 class="card-title">{{ product.name }}</h5>
                    <p class="card-text">${{ product.price }}</p>
                    <a href="{% url 'product_detail' product.slug %}" class="btn btn-primary">View</a>
                </div>
            </div>
        </div>
    {% empty %}
        <p>No products in this category.</p>
    {% endfor %}
</div>
{% endblock %}

# file: templates/cart/cart_detail.html
{% extends 'base.html' %}
{% block title %}Shopping Cart{% endblock %}
{% block content %}
<h1>Shopping Cart</h1>
{% if cart.items.all %}
<table class="table">
    <thead>
        <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Quantity</th>
            <th>Total</th>
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for item in cart.items.all %}
        <tr>
            <td>{{ item.product.name }}</td>
            <td>${{ item.product.price }}</td>
            <td>
                <form method="post" action="{% url 'update_cart' item.id %}" class="d-inline">
                    {% csrf_token %}
                    <input type="number" name="quantity" value="{{ item.quantity }}" min="1" class="form-control d-inline" style="width:80px;">
                    <button type="submit" class="btn btn-sm btn-secondary">Update</button>
                </form>
            </td>
            <td>${{ item.total_price }}</td>
            <td><a href="{% url 'remove_from_cart' item.id %}" class="btn btn-sm btn-danger">Remove</a></td>
        </tr>
        {% endfor %}
    </tbody>
    <tfoot>
        <tr>
            <th colspan="3" class="text-end">Total:</th>
            <th>${{ cart.total_price }}</th>
            <th></th>
        </tr>
    </tfoot>
</table>
<a href="{% url 'checkout' %}" class="btn btn-primary">Proceed to Checkout</a>
{% else %}
<p>Your cart is empty.</p>
{% endif %}
<a href="{% url 'product_list' %}">Continue Shopping</a>
{% endblock %}

# file: templates/orders/checkout.html
{% extends 'base.html' %}
{% block title %}Checkout{% endblock %}
{% block content %}
<h1>Checkout</h1>
<div class="row">
    <div class="col-md-6">
        <h3>Order Summary</h3>
        <table class="table">
            <thead>
                <tr><th>Product</th><th>Quantity</th><th>Price</th></tr>
            </thead>
            <tbody>
                {% for item in cart.items.all %}
                <tr>
                    <td>{{ item.product.name }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>${{ item.total_price }}</td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr><th colspan="2">Total</th><th>${{ cart.total_price }}</th></tr>
            </tfoot>
        </table>
    </div>
    <div class="col-md-6">
        <h3>Shipping Address</h3>
        <form method="post">
            {% csrf_token %}
            <div class="mb-3">
                <label class="form-label">Shipping Address</label>
                <textarea name="shipping_address" class="form-control" required>{{ shipping_address }}</textarea>
            </div>
            <button type="submit" class="btn btn-success">Place Order</button>
        </form>
    </div>
</div>
{% endblock %}

# file: templates/orders/confirmation.html
{% extends 'base.html' %}
{% block title %}Order Confirmed{% endblock %}
{% block content %}
<h1>Thank you for your order!</h1>
<p>Order #{{ order.id }} has been placed. Status: {{ order.status }}</p>
<p>Total: ${{ order.total }}</p>
<a href="{% url 'product_list' %}">Continue Shopping</a>
{% endblock %}

# file: templates/orders/history.html
{% extends 'base.html' %}
{% block title %}Order History{% endblock %}
{% block content %}
<h1>Your Orders</h1>
{% if orders %}
<table class="table">
    <thead>
        <tr>
            <th>Order ID</th>
            <th>Date</th>
            <th>Status</th>
            <th>Total</th>
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for order in orders %}
        <tr>
            <td>{{ order.id }}</td>
            <td>{{ order.created_at|date:"Y-m-d H:i" }}</td>
            <td>{{ order.get_status_display }}</td>
            <td>${{ order.total }}</td>
            <td><a href="{% url 'order_detail' order.id %}" class="btn btn-sm btn-primary">View</a></td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<p>No orders yet.</p>
{% endif %}
{% endblock %}

# file: templates/orders/detail.html
{% extends 'base.html' %}
{% block title %}Order #{{ order.id }}{% endblock %}
{% block content %}
<h1>Order #{{ order.id }}</h1>
<p>Status: {{ order.get_status_display }}</p>
<p>Total: ${{ order.total }}</p>
<p>Shipping Address: {{ order.shipping_address }}</p>
<h3>Items</h3>
<table class="table">
    <thead>
        <tr><th>Product</th><th>Quantity</th><th>Price</th></tr>
    </thead>
    <tbody>
        {% for item in order.items.all %}
        <tr>
            <td>{{ item.product.name }}</td>
            <td>{{ item.quantity }}</td>
            <td>${{ item.price }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<a href="{% url 'order_history' %}">Back to Orders</a>
{% endblock %}