# File: manage.py
#!/usr/bin/env python
import os
import sys

def main():
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

# File: amazon_clone/__init__.py

# File: amazon_clone/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-xyz_replace_with_secure_key'

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
    'products',
    'cart',
    'orders',
    'inventory',
    'suppliers',
    'warehouse',
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# File: amazon_clone/urls.py
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
    path('inventory/', include('inventory.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('warehouse/', include('warehouse.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# File: amazon_clone/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amazon_clone.settings')
application = get_wsgi_application()

# File: accounts/__init__.py

# File: accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

# File: accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'phone', 'password1', 'password2')

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email')

# File: accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', authentication_form=CustomAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
]

# File: accounts/views.py
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

# File: accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

admin.site.register(CustomUser, UserAdmin)

# File: products/__init__.py

# File: products/models.py
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', args=[self.slug])

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

# File: products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product_list'),
    path('search/', views.product_search, name='product_search'),
    path('category/<slug:category_slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
]

# File: products/views.py
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Product, Category

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent=None)
        return context

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'products/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        # products in this category and subcategories
        subcategories = category.children.all()
        products = Product.objects.filter(category__in=[category] + list(subcategories), is_active=True)
        context['products'] = products
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

def product_search(request):
    query = request.GET.get('q', '')
    results = Product.objects.filter(is_active=True)
    if query:
        results = results.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query))
    return render(request, 'products/search_results.html', {'query': query, 'products': results})

# File: products/admin.py
from django.contrib import admin
from .models import Category, Product

admin.site.register(Category)
admin.site.register(Product)

# File: cart/__init__.py

# File: cart/cart.py
from decimal import Decimal
from products.models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product_id, quantity=1, override_quantity=False):
        product_id = str(product_id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(Product.objects.get(id=int(product_id)).price)}
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session['cart']
        self.save()

# File: cart/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('clear/', views.cart_clear, name='cart_clear'),
]

# File: cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from products.models import Product
from .cart import Cart

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/cart_detail.html', {'cart': cart})

def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product_id=product.id, quantity=quantity, override_quantity=False)
    messages.success(request, f'{product.name} added to cart.')
    return redirect('cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product.id)
    return redirect('cart_detail')

def cart_update(request, product_id):
    cart = Cart(request)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart.add(product_id=product_id, quantity=quantity, override_quantity=True)
        else:
            cart.remove(product_id)
    return redirect('cart_detail')

def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return redirect('cart_detail')

# File: orders/__init__.py

# File: orders/models.py
from django.db import models
from accounts.models import CustomUser
from products.models import Product
from warehouse.models import Warehouse
from django.core.validators import MinValueValidator

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f'Order {self.id} by {self.user.email}'

    def update_total(self):
        self.total = sum(item.subtotal for item in self.items.all())
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

# File: orders/forms.py
from django import forms

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(widget=forms.Textarea)

# File: orders/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('history/', views.order_history, name='order_history'),
]

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

# File: orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total', 'created_at']
    list_filter = ['status']
    inlines = [OrderItemInline]
    actions = ['mark_shipped', 'mark_delivered']

    def mark_shipped(self, request, queryset):
        queryset.update(status='shipped')
    mark_shipped.short_description = 'Mark selected as shipped'

    def mark_delivered(self, request, queryset):
        queryset.update(status='delivered')
    mark_delivered.short_description = 'Mark selected as delivered'

# File: inventory/__init__.py

# File: inventory/models.py
from django.db import models
from products.models import Product
from warehouse.models import Warehouse

class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f'{self.product.name} - {self.quantity} @ {self.warehouse.name}'

    def needs_reorder(self):
        return self.quantity <= self.reorder_level

# File: inventory/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('adjust/<int:product_id>/', views.stock_adjust, name='stock_adjust'),
]

# File: inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from products.models import Product
from .models import Stock
from warehouse.models import Warehouse

@staff_member_required
def inventory_list(request):
    stocks = Stock.objects.select_related('product', 'warehouse').all()
    return render(request, 'inventory/inventory_list.html', {'stocks': stocks})

@staff_member_required
def stock_adjust(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        warehouse_id = request.POST.get('warehouse')
        quantity = int(request.POST.get('quantity', 0))
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        stock, created = Stock.objects.get_or_create(product=product, warehouse=warehouse)
        stock.quantity = quantity
        stock.save()
        messages.success(request, f'Stock adjusted for {product.name}')
        return redirect('inventory_list')
    warehouses = Warehouse.objects.all()
    return render(request, 'inventory/stock_adjust.html', {'product': product, 'warehouses': warehouses})

# File: inventory/admin.py
from django.contrib import admin
from .models import Stock

admin.site.register(Stock)

# File: suppliers/__init__.py

# File: suppliers/models.py
from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f'PO-{self.id} {self.supplier.name}'

    def update_total(self):
        self.total = sum(item.subtotal for item in self.items.all())
        self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

# File: suppliers/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.supplier_list, name='supplier_list'),
    path('purchase_orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase_order/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
]

# File: suppliers/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Supplier, PurchaseOrder

@staff_member_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'suppliers/supplier_list.html', {'suppliers': suppliers})

@staff_member_required
def purchase_order_list(request):
    orders = PurchaseOrder.objects.all()
    return render(request, 'suppliers/purchase_order_list.html', {'orders': orders})

@staff_member_required
def purchase_order_detail(request, po_id):
    order = get_object_or_404(PurchaseOrder, id=po_id)
    return render(request, 'suppliers/purchase_order_detail.html', {'order': order})

# File: suppliers/admin.py
from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'status', 'total', 'created_at']
    list_filter = ['status']
    inlines = [PurchaseOrderItemInline]
    actions = ['mark_received']

    def mark_received(self, request, queryset):
        for po in queryset:
            po.status = 'received'
            po.save()
            # Increase stock for each item
            from inventory.models import Stock
            for item in po.items.all():
                stock, created = Stock.objects.get_or_create(product=item.product, warehouse=warehouse)  # warehouse fix
    mark_received.short_description = 'Mark selected as received and increase stock'

admin.site.register(Supplier)

# File: warehouse/__init__.py

# File: warehouse/models.py
from django.db import models

class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    manager = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

# File: warehouse/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.warehouse_list, name='warehouse_list'),
    path('<int:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
]

# File: warehouse/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Warehouse
from inventory.models import Stock

@staff_member_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'warehouse/warehouse_list.html', {'warehouses': warehouses})

@staff_member_required
def warehouse_detail(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    stocks = Stock.objects.filter(warehouse=warehouse)
    return render(request, 'warehouse/warehouse_detail.html', {'warehouse': warehouse, 'stocks': stocks})

# File: warehouse/admin.py
from django.contrib import admin
from .models import Warehouse

admin.site.register(Warehouse)

# File: templates/base.html (minimal)
# Note: This is a minimal HTML template to make the system functional
# since the prompt is about Python, but I include it for completeness.
"""
<!DOCTYPE html>
<html>
<head>
    <title>Amazon Clone</title>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        {% if user.is_authenticated %}
            <a href="{% url 'cart_detail' %}">Cart</a>
            <a href="{% url 'order_history' %}">Orders</a>
            <a href="{% url 'profile' %}">Profile</a>
            <a href="{% url 'logout' %}">Logout</a>
        {% else %}
            <a href="{% url 'login' %}">Login</a>
            <a href="{% url 'signup' %}">Sign Up</a>
        {% endif %}
    </nav>
    <div>
        {% if messages %}
            <ul>
                {% for message in messages %}
                    <li>{{ message }}</li>
                {% endfor %}
            </ul>
        {% endif %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# The templates are not part of Python, so I'll skip full HTML files.
# The above base template is just for reference.

# Requirements.txt (for dependencies, not Python but needed)
"""
Django>=4.2,<5.0
Pillow
"""