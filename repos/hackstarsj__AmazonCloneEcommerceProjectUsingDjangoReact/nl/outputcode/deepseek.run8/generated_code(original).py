import os
import sys
import pathlib
from django.conf import settings
from django.core.management import call_command

BASE_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_NAME = "amazon_clone"
APPS = ["accounts", "products", "cart", "orders", "suppliers", "inventory", "warehouses"]

def create_django_project():
    proj_dir = BASE_DIR / PROJECT_NAME
    if not proj_dir.exists():
        proj_dir.mkdir(parents=True)
        (proj_dir / "__init__.py").write_text("")
        # settings.py
        settings_content = f"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-({PROJECT_NAME})'

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
    'suppliers',
    'inventory',
    'warehouses',
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

ROOT_URLCONF = '{PROJECT_NAME}.urls'

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

WSGI_APPLICATION = '{PROJECT_NAME}.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {{ 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' }},
    {{ 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator' }},
    {{ 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator' }},
    {{ 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator' }},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'accounts.CustomUser'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
"""
        (proj_dir / "settings.py").write_text(settings_content.strip())

        # urls.py
        urls_content = f"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('products/', include('products.urls', namespace='products')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('suppliers/', include('suppliers.urls', namespace='suppliers')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('warehouses/', include('warehouses.urls', namespace='warehouses')),
    path('', include('products.urls', namespace='products_root')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
        (proj_dir / "urls.py").write_text(urls_content.strip())

        # wsgi.py
        wsgi_content = f"""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{PROJECT_NAME}.settings')
application = get_wsgi_application()
"""
        (proj_dir / "wsgi.py").write_text(wsgi_content.strip())

        # manage.py
        manage_content = f"""#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{PROJECT_NAME}.settings')
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
"""
        (BASE_DIR / "manage.py").write_text(manage_content.strip())
        os.chmod(BASE_DIR / "manage.py", 0o755)

    # Create apps
    for app in APPS:
        app_dir = BASE_DIR / PROJECT_NAME / app
        if not app_dir.exists():
            app_dir.mkdir(parents=True)
            (app_dir / "__init__.py").write_text("")

    # Create templates, static, media directories
    templates_dir = BASE_DIR / PROJECT_NAME / "templates"
    static_dir = BASE_DIR / PROJECT_NAME / "static"
    media_dir = BASE_DIR / PROJECT_NAME / "media"
    for d in [templates_dir, static_dir, media_dir]:
        d.mkdir(exist_ok=True)

def write_app_code():
    # accounts
    accounts_models = f"""
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username
"""
    (BASE_DIR / PROJECT_NAME / "accounts" / "models.py").write_text(accounts_models.strip())

    accounts_forms = f"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'address')
"""
    (BASE_DIR / PROJECT_NAME / "accounts" / "forms.py").write_text(accounts_forms.strip())

    accounts_admin = f"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

admin.site.register(CustomUser, UserAdmin)
"""
    (BASE_DIR / PROJECT_NAME / "accounts" / "admin.py").write_text(accounts_admin.strip())

    accounts_urls = f"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
]
"""
    (BASE_DIR / PROJECT_NAME / "accounts" / "urls.py").write_text(accounts_urls.strip())

    accounts_views = f"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, AuthenticationForm

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('products_root:product_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {{'form': form}})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('products_root:product_list')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {{'form': form}})

def logout_view(request):
    logout(request)
    return redirect('products_root:product_list')

@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {{'user': request.user}})
"""
    (BASE_DIR / PROJECT_NAME / "accounts" / "views.py").write_text(accounts_views.strip())

    # templates for accounts
    accounts_templates = BASE_DIR / PROJECT_NAME / "templates" / "accounts"
    accounts_templates.mkdir(parents=True, exist_ok=True)
    (accounts_templates / "signup.html").write_text("""
<h2>Sign Up</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Sign Up</button>
</form>
""")
    (accounts_templates / "login.html").write_text("""
<h2>Login</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Login</button>
</form>
""")
    (accounts_templates / "profile.html").write_text("""
<h2>Profile</h2>
<p>Username: {{ user.username }}</p>
<p>Email: {{ user.email }}</p>
<p>Phone: {{ user.phone_number }}</p>
<p>Address: {{ user.address }}</p>
<a href="{% url 'products_root:product_list' %}">Home</a>
""")

    # products
    products_models = f"""
from django.db import models
from django.urls import reverse
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

class Category(MPTTModel):
    name = models.CharField(max_length=100)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    slug = models.SlugField(unique=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    supplier = models.ForeignKey('suppliers.Supplier', null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.pk])

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
"""
    (BASE_DIR / PROJECT_NAME / "products" / "models.py").write_text(products_models.strip())

    # Need mptt in INSTALLED_APPS? We'll add it. Modify settings after creation.
    # We'll update settings later to include 'mptt'.
    products_admin = f"""
from django.contrib import admin
from .models import Category, Product, ProductImage

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
"""
    (BASE_DIR / PROJECT_NAME / "products" / "admin.py").write_text(products_admin.strip())

    products_forms = f"""
from django import forms
from .models import Product, Category

class ProductSearchForm(forms.Form):
    query = forms.CharField(required=False, label='Search')
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
"""
    (BASE_DIR / PROJECT_NAME / "products" / "forms.py").write_text(products_forms.strip())

    products_urls = f"""
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('search/', views.product_search, name='product_search'),
]
"""
    (BASE_DIR / PROJECT_NAME / "products" / "urls.py").write_text(products_urls.strip())

    products_views = f"""
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category
from .forms import ProductSearchForm

def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-id')
    form = ProductSearchForm(request.GET)
    query = request.GET.get('query')
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    categories = Category.objects.all()
    return render(request, 'products/product_list.html', {{
        'products': products,
        'categories': categories,
        'form': form,
    }})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/product_detail.html', {{'product': product}})

def product_search(request):
    return product_list(request)
"""
    (BASE_DIR / PROJECT_NAME / "products" / "views.py").write_text(products_views.strip())

    products_templates = BASE_DIR / PROJECT_NAME / "templates" / "products"
    products_templates.mkdir(parents=True, exist_ok=True)
    (products_templates / "product_list.html").write_text("""
<h2>Products</h2>
<form method="get" action="{% url 'products:product_list' %}">
    {{ form.as_p }}
    <button type="submit">Search</button>
</form>
<ul>
{% for product in products %}
    <li>
        <a href="{{ product.get_absolute_url }}">{{ product.name }}</a> - ${{ product.price }}
    </li>
{% empty %}
    <li>No products found.</li>
{% endfor %}
</ul>
""")
    (products_templates / "product_detail.html").write_text("""
<h2>{{ product.name }}</h2>
<p>Price: ${{ product.price }}</p>
<p>Category: {{ product.category.name }}</p>
<p>Description: {{ product.description }}</p>
{% if product.image %}
    <img src="{{ product.image.url }}" alt="{{ product.name }}" style="max-width:300px;">
{% endif %}
<br>
<a href="{% url 'cart:add_to_cart' product.pk %}">Add to Cart</a>
<a href="{% url 'products:product_list' %}">Back to Products</a>
""")

    # cart
    cart_models = f"""
from django.db import models
from accounts.models import CustomUser
from products.models import Product

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {{self.user.username}}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{{self.quantity}} x {{self.product.name}}"

    @property
    def total_price(self):
        return self.quantity * self.product.price
"""
    (BASE_DIR / PROJECT_NAME / "cart" / "models.py").write_text(cart_models.strip())

    cart_admin = f"""
from django.contrib import admin
from .models import Cart, CartItem

admin.site.register(Cart)
admin.site.register(CartItem)
"""
    (BASE_DIR / PROJECT_NAME / "cart" / "admin.py").write_text(cart_admin.strip())

    cart_forms = f"""
from django import forms
from .models import CartItem

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)

class UpdateCartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']
"""
    (BASE_DIR / PROJECT_NAME / "cart" / "forms.py").write_text(cart_forms.strip())

    cart_urls = f"""
from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:item_id>/', views.update_cart, name='update_cart'),
]
"""
    (BASE_DIR / PROJECT_NAME / "cart" / "urls.py").write_text(cart_urls.strip())

    cart_views = f"""
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
"""
    (BASE_DIR / PROJECT_NAME / "cart" / "views.py").write_text(cart_views.strip())

    cart_templates = BASE_DIR / PROJECT_NAME / "templates" / "cart"
    cart_templates.mkdir(parents=True, exist_ok=True)
    (cart_templates / "cart_detail.html").write_text("""
<h2>Your Cart</h2>
<table>
<tr><th>Product</th><th>Quantity</th><th>Price</th><th>Total</th><th>Actions</th></tr>
{% for item in cart.items.all %}
<tr>
    <td>{{ item.product.name }}</td>
    <td>{{ item.quantity }}</td>
    <td>${{ item.product.price }}</td>
    <td>${{ item.total_price }}</td>
    <td>
        <a href="{% url 'cart:update_cart' item.pk %}">Update</a>
        <a href="{% url 'cart:remove_from_cart' item.pk %}">Remove</a>
    </td>
</tr>
{% empty %}
<tr><td colspan="5">Cart is empty</td></tr>
{% endfor %}
<tr><td colspan="3">Total</td><td>${{ cart.total_price }}</td></tr>
</table>
<a href="{% url 'orders:checkout' %}">Proceed to Checkout</a>
<a href="{% url 'products:product_list' %}">Continue Shopping</a>
""")
    (cart_templates / "add_to_cart.html").write_text("""
<h2>Add to Cart</h2>
<p>{{ product.name }} - ${{ product.price }}</p>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Add</button>
</form>
""")
    (cart_templates / "update_cart.html").write_text("""
<h2>Update Cart</h2>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Update</button>
</form>
<a href="{% url 'cart:cart_detail' %}">Back to Cart</a>
""")

    # orders
    orders_models = f"""
from django.db import models
from accounts.models import CustomUser
from products.models import Product
from suppliers.models import Supplier
from warehouses.models import Warehouse

class SalesOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('processing','Processing'),('shipped','Shipped'),('delivered','Delivered'),('cancelled','Cancelled')], default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_address = models.TextField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')

    def __str__(self):
        return f"Order {{self.id}} by {{self.user.username}}"

    def calculate_total(self):
        self.total = sum(item.total_price for item in self.items.all())
        self.save()

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.quantity * self.price

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('draft','Draft'),('ordered','Ordered'),('received','Received'),('cancelled','Cancelled')], default='draft')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"PO {{self.id}} from {{self.supplier.name}}"

    def calculate_total_cost(self):
        self.total_cost = sum(item.total_cost for item in self.items.all())
        self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost
"""
    (BASE_DIR / PROJECT_NAME / "orders" / "models.py").write_text(orders_models.strip())

    orders_admin = f"""
from django.contrib import admin
from .models import SalesOrder, SalesOrderItem, PurchaseOrder, PurchaseOrderItem

admin.site.register(SalesOrder)
admin.site.register(SalesOrderItem)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
"""
    (BASE_DIR / PROJECT_NAME / "orders" / "admin.py").write_text(orders_admin.strip())

    orders_forms = f"""
from django import forms
from .models import SalesOrder

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['shipping_address', 'warehouse']
"""
    (BASE_DIR / PROJECT_NAME / "orders" / "forms.py").write_text(orders_forms.strip())

    orders_urls = f"""
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('history/', views.order_history, name='order_history'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('purchase-order/create/', views.create_purchase_order, name='create_purchase_order'),
    path('purchase-order/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-order/<int:po_id>/receive/', views.receive_purchase_order, name='receive_purchase_order'),
]
"""
    (BASE_DIR / PROJECT_NAME / "orders" / "urls.py").write_text(orders_urls.strip())

    orders_views = f"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from cart.models import Cart, CartItem
from .models import SalesOrder, SalesOrderItem, PurchaseOrder, PurchaseOrderItem
from .forms import SalesOrderForm
from warehouses.models import Warehouse, WarehouseStock
from suppliers.models import SupplierProduct
from django.db.models import Sum

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    if cart.items.count() == 0:
        messages.error(request, 'Cart is empty')
        return redirect('cart:cart_detail')
    if request.method == 'POST':
        form = SalesOrderForm(request.POST)
        if form.is_valid():
            shipping_address = form.cleaned_data['shipping_address']
            warehouse = form.cleaned_data['warehouse']
            with transaction.atomic():
                # Check stock and allocate
                for item in cart.items.all():
                    stock_qs = WarehouseStock.objects.filter(warehouse=warehouse, product=item.product)
                    if not stock_qs.exists() or stock_qs.aggregate(Sum('quantity'))['quantity__sum'] < item.quantity:
                        messages.error(request, f"Insufficient stock for {{item.product.name}} in selected warehouse.")
                        return redirect('cart:cart_detail')
                    # Decrease stock
                    stock = stock_qs.first()
                    remaining = item.quantity
                    for stock_record in stock_qs:
                        if remaining <= 0:
                            break
                        deducted = min(stock_record.quantity, remaining)
                        stock_record.quantity -= deducted
                        stock_record.save()
                        remaining -= deducted
                # Create order
                order = SalesOrder(user=request.user, shipping_address=shipping_address, warehouse=warehouse)
                order.save()
                for item in cart.items.all():
                    SalesOrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                order.calculate_total()
                cart.delete()
                messages.success(request, 'Order placed successfully!')
                return redirect('orders:order_detail', order_id=order.pk)
    else:
        form = SalesOrderForm()
    return render(request, 'orders/checkout.html', {{'form': form, 'cart': cart}})

@login_required
def order_history(request):
    orders = SalesOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {{'orders': orders}})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(SalesOrder, pk=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {{'order': order}})

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def create_purchase_order(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        warehouse_id = request.POST.get('warehouse')
        # Process items from form
        po = PurchaseOrder.objects.create(supplier_id=supplier_id, warehouse_id=warehouse_id)
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')
        unit_costs = request.POST.getlist('unit_cost')
        for pid, qty, cost in zip(product_ids, quantities, unit_costs):
            PurchaseOrderItem.objects.create(purchase_order=po, product_id=pid, quantity=qty, unit_cost=cost)
        po.calculate_total_cost()
        return redirect('orders:purchase_order_detail', po_id=po.pk)
    else:
        from suppliers.models import Supplier
        from warehouses.models import Warehouse
        suppliers = Supplier.objects.all()
        warehouses = Warehouse.objects.all()
        return render(request, 'orders/create_purchase_order.html', {{'suppliers': suppliers, 'warehouses': warehouses}})

@user_passes_test(is_admin)
def purchase_order_detail(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    return render(request, 'orders/purchase_order_detail.html', {{'po': po}})

@user_passes_test(is_admin)
def receive_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)
    if po.status == 'received':
        messages.info(request, 'Already received')
        return redirect('orders:purchase_order_detail', po_id=po_id)
    with transaction.atomic():
        for item in po.items.all():
            stock, created = WarehouseStock.objects.get_or_create(
                warehouse=po.warehouse, product=item.product,
                defaults={{'quantity': 0, 'low_stock_threshold': 10}}
            )
            stock.quantity += item.quantity
            stock.save()
        po.status = 'received'
        po.save()
    messages.success(request, 'Purchase order received, stock updated.')
    return redirect('orders:purchase_order_detail', po_id=po_id)
"""
    (BASE_DIR / PROJECT_NAME / "orders" / "views.py").write_text(orders_views.strip())

    orders_templates = BASE_DIR / PROJECT_NAME / "templates" / "orders"
    orders_templates.mkdir(parents=True, exist_ok=True)
    (orders_templates / "checkout.html").write_text("""
<h2>Checkout</h2>
<p>Total: ${{ cart.total_price }}</p>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Place Order</button>
</form>
""")
    (orders_templates / "order_history.html").write_text("""
<h2>Order History</h2>
{% for order in orders %}
    <p><a href="{% url 'orders:order_detail' order.pk %}">Order #{{ order.id }}</a> - {{ order.created_at }} - {{ order.status }} - ${{ order.total }}</p>
{% empty %}
    <p>No orders yet.</p>
{% endfor %}
""")
    (orders_templates / "order_detail.html").write_text("""
<h2>Order #{{ order.id }}</h2>
<p>Status: {{ order.status }}</p>
<p>Total: ${{ order.total }}</p>
<p>Shipping Address: {{ order.shipping_address }}</p>
<ul>
{% for item in order.items.all %}
    <li>{{ item.product.name }} x {{ item.quantity }} @ ${{ item.price }}</li>
{% endfor %}
</ul>
""")
    (orders_templates / "create_purchase_order.html").write_text("""
<h2>Create Purchase Order</h2>
<form method="post">
    {% csrf_token %}
    <label>Supplier:</label>
    <select name="supplier">
        {% for s in suppliers %}
            <option value="{{ s.id }}">{{ s.name }}</option>
        {% endfor %}
    </select>
    <label>Warehouse:</label>
    <select name="warehouse">
        {% for w in warehouses %}
            <option value="{{ w.id }}">{{ w.name }}</option>
        {% endfor %}
    </select>
    <div id="items">
        <div>
            <label>Product ID:</label><input type="text" name="product_id" />
            <label>Quantity:</label><input type="number" name="quantity" />
            <label>Unit Cost:</label><input type="number" step="0.01" name="unit_cost" />
        </div>
    </div>
    <button type="button" onclick="addItem()">Add Item</button>
    <br><br>
    <button type="submit">Create</button>
</form>
<script>
function addItem() {
    var div = document.getElementById('items');
    var newDiv = document.createElement('div');
    newDiv.innerHTML = '<label>Product ID:</label><input type="text" name="product_id" /><label>Quantity:</label><input type="number" name="quantity" /><label>Unit Cost:</label><input type="number" step="0.01" name="unit_cost" />';
    div.appendChild(newDiv);
}
</script>
""")
    (orders_templates / "purchase_order_detail.html").write_text("""
<h2>Purchase Order #{{ po.id }}</h2>
<p>Supplier: {{ po.supplier.name }}</p>
<p>Warehouse: {{ po.warehouse.name }}</p>
<p>Status: {{ po.status }}</p>
<p>Total Cost: ${{ po.total_cost }}</p>
<ul>
{% for item in po.items.all %}
    <li>{{ item.product.name }} x {{ item.quantity }} @ ${{ item.unit_cost }}</li>
{% endfor %}
</ul>
{% if po.status != 'received' and request.user.is_superuser %}
    <a href="{% url 'orders:receive_purchase_order' po.id %}">Mark as Received</a>
{% endif %}
""")

    # suppliers
    suppliers_models = f"""
from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class SupplierProduct(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplier_products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='supplier_products')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('supplier', 'product')

    def __str__(self):
        return f"{{self.product.name}} from {{self.supplier.name}} at ${{self.unit_cost}}"
"""
    (BASE_DIR / PROJECT_NAME / "suppliers" / "models.py").write_text(suppliers_models.strip())

    suppliers_admin = f"""
from django.contrib import admin
from .models import Supplier, SupplierProduct

admin.site.register(Supplier)
admin.site.register(SupplierProduct)
"""
    (BASE_DIR / PROJECT_NAME / "suppliers" / "admin.py").write_text(suppliers_admin.strip())

    suppliers_urls = f"""
from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('', views.supplier_list, name='supplier_list'),
    path('<int:pk>/', views.supplier_detail, name='supplier_detail'),
]
"""
    (BASE_DIR / PROJECT_NAME / "suppliers" / "urls.py").write_text(suppliers_urls.strip())

    suppliers_views = f"""
from django.shortcuts import render, get_object_or_404
from .models import Supplier

def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'suppliers/supplier_list.html', {{'suppliers': suppliers}})

def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    return render(request, 'suppliers/supplier_detail.html', {{'supplier': supplier}})
"""
    (BASE_DIR / PROJECT_NAME / "suppliers" / "views.py").write_text(suppliers_views.strip())

    suppliers_templates = BASE_DIR / PROJECT_NAME / "templates" / "suppliers"
    suppliers_templates.mkdir(parents=True, exist_ok=True)
    (suppliers_templates / "supplier_list.html").write_text("""
<h2>Suppliers</h2>
<ul>
{% for s in suppliers %}
    <li><a href="{% url 'suppliers:supplier_detail' s.pk %}">{{ s.name }}</a></li>
{% endfor %}
</ul>
""")
    (suppliers_templates / "supplier_detail.html").write_text("""
<h2>{{ supplier.name }}</h2>
<p>Contact: {{ supplier.contact_name }}</p>
<p>Phone: {{ supplier.phone }}</p>
<p>Email: {{ supplier.email }}</p>
<p>Address: {{ supplier.address }}</p>
<h3>Products</h3>
<ul>
{% for sp in supplier.supplier_products.all %}
    <li>{{ sp.product.name }} - Unit Cost: ${{ sp.unit_cost }}</li>
{% empty %}
    <li>No products linked.</li>
{% endfor %}
</ul>
""")

    # warehouses
    warehouses_models = f"""
from django.db import models

class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='warehouse_stocks')
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)

    class Meta:
        unique_together = ('warehouse', 'product')

    def __str__(self):
        return f"{{self.product.name}} in {{self.warehouse.name}}: {{self.quantity}}"
"""
    (BASE_DIR / PROJECT_NAME / "warehouses" / "models.py").write_text(warehouses_models.strip())

    warehouses_admin = f"""
from django.contrib import admin
from .models import Warehouse, WarehouseStock

admin.site.register(Warehouse)
admin.site.register(WarehouseStock)
"""
    (BASE_DIR / PROJECT_NAME / "warehouses" / "admin.py").write_text(warehouses_admin.strip())

    warehouses_urls = f"""
from django.urls import path
from . import views

app_name = 'warehouses'

urlpatterns = [
    path('', views.warehouse_list, name='warehouse_list'),
    path('<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
]
"""
    (BASE_DIR / PROJECT_NAME / "warehouses" / "urls.py").write_text(warehouses_urls.strip())

    warehouses_views = f"""
from django.shortcuts import render, get_object_or_404
from .models import Warehouse

def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'warehouses/warehouse_list.html', {{'warehouses': warehouses}})

def warehouse_detail(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    return render(request, 'warehouses/warehouse_detail.html', {{'warehouse': warehouse}})
"""
    (BASE_DIR / PROJECT_NAME / "warehouses" / "views.py").write_text(warehouses_views.strip())

    warehouses_templates = BASE_DIR / PROJECT_NAME / "templates" / "warehouses"
    warehouses_templates.mkdir(parents=True, exist_ok=True)
    (warehouses_templates / "warehouse_list.html").write_text("""
<h2>Warehouses</h2>
<ul>
{% for w in warehouses %}
    <li><a href="{% url 'warehouses:warehouse_detail' w.pk %}">{{ w.name }}</a></li>
{% endfor %}
</ul>
""")
    (warehouses_templates / "warehouse_detail.html").write_text("""
<h2>{{ warehouse.name }}</h2>
<p>Location: {{ warehouse.location }}</p>
<p>Address: {{ warehouse.address }}</p>
<h3>Stock</h3>
<table>
<tr><th>Product</th><th>Quantity</th><th>Low Stock Threshold</th></tr>
{% for stock in warehouse.stocks.all %}
<tr>
    <td>{{ stock.product.name }}</td>
    <td>{{ stock.quantity }}</td>
    <td>{{ stock.low_stock_threshold }}</td>
</tr>
{% empty %}
<tr><td colspan="3">No stock</td></tr>
{% endfor %}
</table>
""")

    # inventory app (may be just for admin inventory overview)
    inventory_models = """from django.db import models
# Additional inventory models if needed, but we'll use dashboard views.
"""
    (BASE_DIR / PROJECT_NAME / "inventory" / "models.py").write_text(inventory_models.strip())

    inventory_admin = """
from django.contrib import admin
# no custom models
"""
    (BASE_DIR / PROJECT_NAME / "inventory" / "admin.py").write_text(inventory_admin.strip())

    inventory_urls = f"""
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_dashboard, name='dashboard'),
]
"""
    (BASE_DIR / PROJECT_NAME / "inventory" / "urls.py").write_text(inventory_urls.strip())

    inventory_views = """
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from warehouses.models import Warehouse, WarehouseStock

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def inventory_dashboard(request):
    warehouses = Warehouse.objects.prefetch_related('stocks__product')
    return render(request, 'inventory/dashboard.html', {'warehouses': warehouses})
"""
    (BASE_DIR / PROJECT_NAME / "inventory" / "views.py").write_text(inventory_views.strip())

    inventory_templates = BASE_DIR / PROJECT_NAME / "templates" / "inventory"
    inventory_templates.mkdir(parents=True, exist_ok=True)
    (inventory_templates / "dashboard.html").write_text("""
<h2>Inventory Dashboard</h2>
{% for warehouse in warehouses %}
    <h3>{{ warehouse.name }}</h3>
    <table border="1">
    <tr><th>Product</th><th>Quantity</th><th>Low Stock Threshold</th></tr>
    {% for stock in warehouse.stocks.all %}
        <tr>
            <td>{{ stock.product.name }}</td>
            <td>{{ stock.quantity }}</td>
            <td>{{ stock.low_stock_threshold }}</td>
        </tr>
    {% empty %}
        <tr><td colspan="3">No stock</td></tr>
    {% endfor %}
    </table>
{% endfor %}
""")

    # Install mptt and update settings
    settings_path = BASE_DIR / PROJECT_NAME / "settings.py"
    content = settings_path.read_text()
    # add 'mptt' to INSTALLED_APPS after 'accounts', or just append
    content = content.replace(
        "'warehouses',",
        "'warehouses',\n    'mptt',"
    )
    settings_path.write_text(content)

    # Also need to run migrations later; script can run them automatically
    # We'll call management commands.

if __name__ == "__main__":
    create_django_project()
    write_app_code()
    # Set up Django environment
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{PROJECT_NAME}.settings')
    import django
    django.setup()
    from django.core.management import call_command
    # Run migrations
    call_command('makemigrations', 'accounts', 'products', 'cart', 'orders', 'suppliers', 'warehouses', 'inventory', interactive=False)
    call_command('migrate', interactive=False)
    print("Project setup complete. Run 'python manage.py runserver' to start.")