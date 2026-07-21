# =============================================================================
# REVISED COPY — this is NOT the file under test. The pristine model output is
# generated_code.py; this copy records the minimal edits made to the original
# hackstarsj/AmazonClone *gemini* output so it runs as one self-contained Django
# app. Each edit is tagged `# [REVISED]` below. Summary of changes:
#   - moved the Django model imports below settings.configure()/django.setup()
#   - registered this module as app 'generated_code' (sys.modules + app_label)
#   - dropped the custom User(AbstractUser) and AUTH_USER_MODEL; use built-in User
#   - permission checks that used the dropped is_warehouse_manager now use is_staff
# =============================================================================

import os
import sys
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional

import django
from django.conf import settings

# [REVISED +] added block: register this module under a stable app label.
# When run as `python generated_code.py`, __name__ is '__main__', which Django
# cannot use as an app label, so alias the module to 'generated_code'.
_APP_LABEL = 'generated_code'
if __name__ == '__main__':
    sys.modules[_APP_LABEL] = sys.modules[__name__]

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='amazon-clone-secret-key-for-development',
        ROOT_URLCONF=__name__,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'amazon_clone.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            _APP_LABEL,                 # [REVISED] was `__name__`
        ],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ],
        # [REVISED -] removed `AUTH_USER_MODEL=f'{__name__}.User'` — the custom
        # User model triggered a circular startup failure during django.setup().
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )
    django.setup()

# [REVISED] these Django model imports were moved here from the top of the file
# (they must run AFTER settings.configure()/django.setup()); AbstractUser was
# replaced with the built-in User.
from django.core.management import execute_from_command_line
from django.db import models, transaction
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# [REVISED -] removed the custom `class User(AbstractUser)` (dropped its
# is_supplier / is_warehouse_manager fields); the built-in auth User is used.

class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subcategories')

    class Meta:
        app_label = 'generated_code'  # [REVISED] was `__name__` (same change on every model's Meta below)

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        app_label = 'generated_code'

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    class Meta:
        app_label = 'generated_code'

class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='products')

    class Meta:
        app_label = 'generated_code'

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_records')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'generated_code'
        unique_together = ('product', 'warehouse')

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')

    class Meta:
        app_label = 'generated_code'

    def add_item(self, product: Product, quantity: int = 1) -> 'CartItem':
        item, created = CartItem.objects.get_or_create(cart=self, product=product)
        if not created:
            item.quantity += quantity
            item.save()
        else:
            item.quantity = quantity
            item.save()
        return item

    @transaction.atomic
    def checkout(self) -> 'SalesOrder':
        items = self.items.all()
        if not items.exists():
            raise ValueError("Cart is empty")

        order = SalesOrder.objects.create(user=self.user, status='PENDING')

        for item in items:
            remaining_needed = item.quantity
            inventories = Inventory.objects.filter(product=item.product, quantity__gt=0).order_by('id')
            
            total_stock = sum(inv.quantity for inv in inventories)
            if total_stock < remaining_needed:
                raise ValueError(f"Insufficient stock for {item.product.title}")

            for inv in inventories:
                if remaining_needed <= 0:
                    break
                if inv.quantity >= remaining_needed:
                    inv.quantity -= remaining_needed
                    inv.save()
                    remaining_needed = 0
                else:
                    remaining_needed -= inv.quantity
                    inv.quantity = 0
                    inv.save()

            SalesOrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        self.items.all().delete()
        return order

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        app_label = 'generated_code'

class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_orders')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        app_label = 'generated_code'

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'

    @transaction.atomic
    def receive(self) -> None:
        if self.status == 'RECEIVED':
            raise ValueError("Purchase Order already received")
        
        for item in self.items.all():
            inventory, _ = Inventory.objects.get_or_create(
                product=item.product,
                warehouse=self.warehouse,
                defaults={'quantity': 0}
            )
            inventory.quantity += item.quantity
            inventory.save()
            
        self.status = 'RECEIVED'
        self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        app_label = 'generated_code'

def parse_json(request: HttpRequest) -> Dict[str, Any]:
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}

@csrf_exempt
@require_http_methods(["POST"])
def register_view(request: HttpRequest) -> JsonResponse:
    data = parse_json(request)
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')
    
    if not username or not password:
        return JsonResponse({'error': 'Username and password required'}, status=400)
        
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=400)
        
    user = User.objects.create_user(username=username, email=email, password=password)
    Cart.objects.create(user=user)
    return JsonResponse({'message': 'User created successfully', 'user_id': user.id}, status=201)

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request: HttpRequest) -> JsonResponse:
    data = parse_json(request)
    user = authenticate(request, username=data.get('username'), password=data.get('password'))
    if user is not None:
        login(request, user)
        return JsonResponse({'message': 'Logged in successfully'})
    return JsonResponse({'error': 'Invalid credentials'}, status=401)

@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})

@require_http_methods(["GET"])
def product_list_view(request: HttpRequest) -> JsonResponse:
    queryset = Product.objects.all()
    
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(title__icontains=search)
        
    category_id = request.GET.get('category_id')
    if category_id:
        queryset = queryset.filter(category_id=category_id)
        
    products = [{
        'id': p.id,
        'title': p.title,
        'price': str(p.price),
        'category': p.category.name
    } for p in queryset]
    
    return JsonResponse({'products': products})

@require_http_methods(["GET"])
def product_detail_view(request: HttpRequest, product_id: int) -> JsonResponse:
    try:
        p = Product.objects.get(id=product_id)
        total_stock = sum(inv.quantity for inv in p.inventory_records.all())
        data = {
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'price': str(p.price),
            'category': p.category.name,
            'supplier': p.supplier.name if p.supplier else None,
            'in_stock': total_stock > 0,
            'stock_quantity': total_stock
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def cart_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
        
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        data = parse_json(request)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id)
            cart.add_item(product, quantity)
            return JsonResponse({'message': 'Item added to cart'})
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
            
    items = [{
        'product_id': item.product.id,
        'title': item.product.title,
        'quantity': item.quantity,
        'price': str(item.product.price),
        'subtotal': str(item.product.price * item.quantity)
    } for item in cart.items.all()]
    
    total = sum(Decimal(item['subtotal']) for item in items)
    return JsonResponse({'items': items, 'total': str(total)})

@csrf_exempt
@require_http_methods(["POST"])
def checkout_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
        
    cart, _ = Cart.objects.get_or_create(user=request.user)
    try:
        order = cart.checkout()
        return JsonResponse({'message': 'Checkout successful', 'order_id': order.id})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def create_purchase_order_view(request: HttpRequest) -> JsonResponse:
    # [REVISED] was `... or not (request.user.is_staff or request.user.is_warehouse_manager)`
    if not request.user.is_authenticated or not (request.user.is_staff):
        return JsonResponse({'error': 'Admin privileges required'}, status=403)
        
    data = parse_json(request)
    supplier_id = data.get('supplier_id')
    warehouse_id = data.get('warehouse_id')
    items_data = data.get('items', [])
    
    try:
        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                supplier_id=supplier_id,
                warehouse_id=warehouse_id
            )
            for item in items_data:
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product_id=item['product_id'],
                    quantity=item['quantity']
                )
        return JsonResponse({'message': 'Purchase Order created', 'po_id': po.id}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def receive_purchase_order_view(request: HttpRequest, po_id: int) -> JsonResponse:
    # [REVISED] was `... or not (request.user.is_staff or request.user.is_warehouse_manager)`
    if not request.user.is_authenticated or not (request.user.is_staff):
        return JsonResponse({'error': 'Admin privileges required'}, status=403)
        
    try:
        po = PurchaseOrder.objects.get(id=po_id)
        po.receive()
        return JsonResponse({'message': 'Purchase Order received and inventory updated'})
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'error': 'Purchase Order not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def inventory_list_view(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Admin privileges required'}, status=403)
        
    inventories = Inventory.objects.select_related('product', 'warehouse').all()
    data = [{
        'warehouse': inv.warehouse.name,
        'product': inv.product.title,
        'quantity': inv.quantity
    } for inv in inventories]
    
    return JsonResponse({'inventory': data})

def responsive_frontend_view(request: HttpRequest) -> HttpResponse:
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon Clone</title>
    <style>
        :root { --bg: #eaeded; --nav: #131921; --nav-hover: #232f3e; --text: #0f1111; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: var(--bg); color: var(--text); }
        header { background-color: var(--nav); color: white; padding: 10px 20px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.5rem; font-weight: bold; text-decoration: none; color: white; }
        .search-bar { display: flex; flex-grow: 1; margin: 10px 20px; max-width: 800px; }
        .search-bar input { flex-grow: 1; padding: 10px; border: none; border-radius: 4px 0 0 4px; }
        .search-bar button { padding: 10px 20px; background-color: #febd69; border: none; border-radius: 0 4px 4px 0; cursor: pointer; font-weight: bold; }
        .nav-links { display: flex; gap: 15px; }
        .nav-links a { color: white; text-decoration: none; font-size: 0.9rem; display: flex; flex-direction: column; justify-content: center; }
        .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        .product-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; }
        .product-title { font-size: 1.1rem; margin: 0 0 10px 0; }
        .product-price { font-size: 1.3rem; font-weight: bold; color: #B12704; margin-bottom: 15px; }
        .add-to-cart { background-color: #ffd814; border: 1px solid #fcd200; border-radius: 20px; padding: 10px; cursor: pointer; width: 100%; font-weight: bold; margin-top: auto; }
        .add-to-cart:hover { background-color: #f7ca00; }
        @media (max-width: 768px) {
            header { flex-direction: column; align-items: stretch; }
            .search-bar { margin: 10px 0; }
            .nav-links { justify-content: space-between; margin-top: 10px; }
        }
    </style>
</head>
<body>
    <header>
        <a href="#" class="logo">Amazon Clone</a>
        <div class="search-bar">
            <input type="text" placeholder="Search products...">
            <button>Search</button>
        </div>
        <div class="nav-links">
            <a href="#"><span>Hello, sign in</span><strong>Account & Lists</strong></a>
            <a href="#"><span>Returns</span><strong>& Orders</strong></a>
            <a href="#"><strong>Cart</strong></a>
        </div>
    </header>
    <div class="container">
        <div class="product-grid" id="products-container">
            <div class="product-card">
                <h3 class="product-title">Loading products...</h3>
            </div>
        </div>
    </div>
    <script>
        fetch('/api/products/')
            .then(res => res.json())
            .then(data => {
                const container = document.getElementById('products-container');
                if(data.products && data.products.length > 0) {
                    container.innerHTML = data.products.map(p => `
                        <div class="product-card">
                            <h3 class="product-title">${p.title}</h3>
                            <div class="product-price">$${p.price}</div>
                            <button class="add-to-cart" onclick="alert('Added to cart!')">Add to Cart</button>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<p>No products found. Run migrations and add data via Django shell.</p>';
                }
            });
    </script>
</body>
</html>"""
    return HttpResponse(html)

urlpatterns = [
    path('', responsive_frontend_view),
    path('api/register/', register_view),
    path('api/login/', login_view),
    path('api/logout/', logout_view),
    path('api/products/', product_list_view),
    path('api/products/<int:product_id>/', product_detail_view),
    path('api/cart/', cart_view),
    path('api/cart/checkout/', checkout_view),
    path('api/admin/po/', create_purchase_order_view),
    path('api/admin/po/<int:po_id>/receive/', receive_purchase_order_view),
    path('api/admin/inventory/', inventory_list_view),
]

if __name__ == '__main__':
    if len(sys.argv) == 1:
        execute_from_command_line([sys.argv[0], 'migrate', '--run-syncdb'])
        execute_from_command_line([sys.argv[0], 'runserver', '0.0.0.0:8000'])
    else:
        execute_from_command_line(sys.argv)