#!/usr/bin/env python3
"""
Amazon Clone - Complete Django Implementation
"""

# =============================================================================
# REVISED COPY — this is NOT the file under test. The pristine model output is
# generated_code.py; this copy records the minimal edits made to the original
# hackstarsj/AmazonClone *claude* output so it runs as one self-contained Django
# app. Each edit is tagged `# [REVISED]` below. Summary of changes:
#   - registered this module as app 'generated_code' (sys.modules + INSTALLED_APPS)
#   - pop DJANGO_SETTINGS_MODULE so settings.configure() always runs
#   - added `app_label = 'generated_code'` to every model's Meta (20 lines / 13
#     new Meta classes) so single-file models resolve to this app
#   - rewrote create_tables() to build the schema via the schema editor
# =============================================================================

import os
import sys
import django
from django.conf import settings

# [REVISED +] added block: register this module under a stable app label
# ('__main__' can't be a Django app label) and clear any inherited settings.
_APP_LABEL = 'generated_code'
if __name__ == '__main__':
    sys.modules[_APP_LABEL] = sys.modules[__name__]

# Clear any env-level settings module so settings.configure() always runs
os.environ.pop('DJANGO_SETTINGS_MODULE', None)

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='amazon-clone-secret-key-change-in-production',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'amazon_clone.db',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'generated_code',                 # [REVISED +] register this module as an app
        ],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ],
        ROOT_URLCONF=__name__,
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }],
        STATIC_URL='/static/',
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        AUTH_USER_MODEL='auth.User',
    )

django.setup()

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid


# ============================================================
# MODELS
# ============================================================

class Category(models.Model):
    """Product category with multi-level support"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        related_name='children', on_delete=models.CASCADE
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'  # [REVISED +] added to every model's Meta below (new Meta added where absent)
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_full_path(self) -> str:
        """Get full category path including parents"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

    def get_all_children(self) -> List['Category']:
        """Get all descendant categories"""
        children = list(self.children.all())
        for child in list(children):
            children.extend(child.get_all_children())
        return children


class Supplier(models.Model):
    """Supplier/Vendor model"""
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    contact_person = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)
    lead_time_days = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(
        max_digits=3, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=Decimal('0.00')
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return self.name

    def get_total_orders(self) -> int:
        """Get total number of purchase orders"""
        return self.purchase_orders.count()

    def get_total_spend(self) -> Decimal:
        """Get total amount spent with supplier"""
        total = self.purchase_orders.filter(
            status='received'
        ).aggregate(
            total=models.Sum('total_amount')
        )['total']
        return total or Decimal('0.00')


class Warehouse(models.Model):
    """Warehouse/Storage location model"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    manager = models.ForeignKey(
        User, null=True, blank=True,
        related_name='managed_warehouses', on_delete=models.SET_NULL
    )
    capacity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_total_inventory_value(self) -> Decimal:
        """Calculate total inventory value in warehouse"""
        total = Decimal('0.00')
        for inventory in self.inventory_items.all():
            total += inventory.quantity * inventory.product.cost_price
        return total

    def get_available_capacity(self) -> int:
        """Get available capacity"""
        used = self.inventory_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        return self.capacity - used


class Product(models.Model):
    """Product model"""
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('refurbished', 'Refurbished'),
    ]

    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    short_description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, related_name='products', on_delete=models.CASCADE
    )
    brand = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    weight = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    dimensions = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True,
        related_name='created_products', on_delete=models.SET_NULL
    )

    class Meta:
        app_label = 'generated_code'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_effective_price(self) -> Decimal:
        """Get current selling price"""
        if self.sale_price and self.sale_price < self.price:
            return self.sale_price
        return self.price

    def get_discount_percentage(self) -> Optional[int]:
        """Calculate discount percentage"""
        if self.sale_price and self.sale_price < self.price:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return int(discount)
        return None

    def get_total_stock(self) -> int:
        """Get total stock across all warehouses"""
        total = self.inventory_items.aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or 0

    def is_in_stock(self) -> bool:
        """Check if product is in stock"""
        return self.get_total_stock() > 0

    def get_average_rating(self) -> float:
        """Get average product rating"""
        avg = self.reviews.aggregate(
            avg=models.Avg('rating')
        )['avg']
        return round(avg, 1) if avg else 0.0

    def get_review_count(self) -> int:
        """Get total number of reviews"""
        return self.reviews.count()


class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductAttribute(models.Model):
    """Product attributes (color, size, etc.)"""
    product = models.ForeignKey(
        Product, related_name='attributes', on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=200)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"


class Inventory(models.Model):
    """Inventory tracking per product per warehouse"""
    product = models.ForeignKey(
        Product, related_name='inventory_items', on_delete=models.CASCADE
    )
    warehouse = models.ForeignKey(
        Warehouse, related_name='inventory_items', on_delete=models.CASCADE
    )
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    reserved_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    reorder_point = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    max_stock_level = models.IntegerField(default=1000)
    location_in_warehouse = models.CharField(max_length=100, blank=True)
    last_counted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'
        unique_together = ['product', 'warehouse']
        verbose_name_plural = 'inventories'

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"

    def get_available_quantity(self) -> int:
        """Get quantity available for sale"""
        return self.quantity - self.reserved_quantity

    def needs_reorder(self) -> bool:
        """Check if product needs reordering"""
        return self.quantity <= self.reorder_point

    def reserve_stock(self, quantity: int) -> bool:
        """Reserve stock for an order"""
        if self.get_available_quantity() >= quantity:
            self.reserved_quantity += quantity
            self.save()
            return True
        return False

    def release_reservation(self, quantity: int) -> None:
        """Release reserved stock"""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        self.save()

    def deduct_stock(self, quantity: int) -> bool:
        """Deduct stock after order fulfillment"""
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.reserved_quantity = max(0, self.reserved_quantity - quantity)
            self.save()
            return True
        return False

    def add_stock(self, quantity: int) -> None:
        """Add stock to inventory"""
        self.quantity += quantity
        self.save()


class InventoryTransaction(models.Model):
    """Track all inventory movements"""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase Receipt'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
        ('damage', 'Damage/Loss'),
    ]

    inventory = models.ForeignKey(
        Inventory, related_name='transactions', on_delete=models.CASCADE
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"{self.transaction_type} - {self.inventory.product.name}: {self.quantity}"


class PurchaseOrder(models.Model):
    """Purchase orders from suppliers"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('partial', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier, related_name='purchase_orders', on_delete=models.CASCADE
    )
    warehouse = models.ForeignKey(
        Warehouse, related_name='purchase_orders', on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True,
        related_name='created_purchase_orders', on_delete=models.SET_NULL
    )
    approved_by = models.ForeignKey(
        User, null=True, blank=True,
        related_name='approved_purchase_orders', on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"PO-{self.order_number}"

    def calculate_total(self) -> Decimal:
        """Calculate total order amount"""
        subtotal = sum(
            item.quantity * item.unit_price
            for item in self.items.all()
        )
        return subtotal + self.tax_amount + self.shipping_cost

    def submit(self) -> bool:
        """Submit purchase order for approval"""
        if self.status == 'draft':
            self.status = 'submitted'
            self.save()
            return True
        return False

    def approve(self, user: User) -> bool:
        """Approve purchase order"""
        if self.status == 'submitted':
            self.status = 'approved'
            self.approved_by = user
            self.save()
            return True
        return False

    def receive_items(self) -> None:
        """Update status based on received items"""
        total_items = self.items.count()
        received_items = self.items.filter(received_quantity__gt=0).count()
        fully_received = self.items.filter(
            received_quantity__gte=models.F('quantity')
        ).count()

        if fully_received == total_items:
            self.status = 'received'
            self.actual_delivery_date = timezone.now().date()
        elif received_items > 0:
            self.status = 'partial'
        self.save()


class PurchaseOrderItem(models.Model):
    """Items in a purchase order"""
    purchase_order = models.ForeignKey(
        PurchaseOrder, related_name='items', on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, related_name='purchase_order_items', on_delete=models.CASCADE
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self) -> Decimal:
        return self.quantity * self.unit_price

    def get_remaining_quantity(self) -> int:
        return self.quantity - self.received_quantity

    def receive(self, quantity: int, warehouse: Warehouse, user: User) -> bool:
        """Receive items and update inventory"""
        if quantity <= 0 or quantity > self.get_remaining_quantity():
            return False

        self.received_quantity += quantity
        self.save()

        # Update inventory
        inventory, created = Inventory.objects.get_or_create(
            product=self.product,
            warehouse=warehouse,
            defaults={'quantity': 0}
        )

        quantity_before = inventory.quantity
        inventory.add_stock(quantity)

        # Record transaction
        InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type='purchase',
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=inventory.quantity,
            reference_number=self.purchase_order.order_number,
            performed_by=user
        )

        # Update PO status
        self.purchase_order.receive_items()
        return True


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_seller = models.BooleanField(default=False)
    is_warehouse_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"Profile of {self.user.username}"

    def get_full_name(self) -> str:
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username


class Address(models.Model):
    """User addresses"""
    ADDRESS_TYPES = [
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
        ('both', 'Both'),
    ]

    user = models.ForeignKey(User, related_name='addresses', on_delete=models.CASCADE)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='both')
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=300)
    address_line2 = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.country}"

    def get_full_address(self) -> str:
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.extend([self.city, self.state, self.zip_code, self.country])
        return ', '.join(parts)


class Cart(models.Model):
    """Shopping cart"""
    user = models.OneToOneField(
        User, null=True, blank=True,
        related_name='cart', on_delete=models.CASCADE
    )
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Anonymous Cart {self.session_key}"

    def get_total_items(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    def get_subtotal(self) -> Decimal:
        """Get cart subtotal"""
        return sum(item.get_total_price() for item in self.items.all())

    def get_total(self) -> Decimal:
        """Get cart total including tax and shipping"""
        return self.get_subtotal()

    def add_item(self, product: Product, quantity: int = 1) -> 'CartItem':
        """Add item to cart"""
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        return cart_item

    def remove_item(self, product: Product) -> None:
        """Remove item from cart"""
        self.items.filter(product=product).delete()

    def clear(self) -> None:
        """Clear all items from cart"""
        self.items.all().delete()

    def update_item_quantity(self, product: Product, quantity: int) -> bool:
        """Update item quantity"""
        try:
            item = self.items.get(product=product)
            if quantity <= 0:
                item.delete()
            else:
                item.quantity = quantity
                item.save()
            return True
        except CartItem.DoesNotExist:
            return False


class CartItem(models.Model):
    """Items in shopping cart"""
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='cart_items', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self) -> Decimal:
        return self.product.get_effective_price() * self.quantity


class Order(models.Model):
    """Sales orders"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('returned', 'Returned'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending'
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True
    )

    # Shipping address
    shipping_full_name = models.CharField(max_length=200)
    shipping_phone = models.CharField(max_length=20)
    shipping_address_line1 = models.CharField(max_length=300)
    shipping_address_line2 = models.CharField(max_length=300, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100)
    shipping_zip_code = models.CharField(max_length=20)

    # Billing address
    billing_full_name = models.CharField(max_length=200, blank=True)
    billing_address_line1 = models.CharField(max_length=300, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)
    billing_zip_code = models.CharField(max_length=20, blank=True)

    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    # Timestamps
    ordered_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'
        ordering = ['-ordered_at']

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"Order #{self.order_number}"

    def get_total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())

    def can_cancel(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']

    def cancel(self, reason: str = '') -> bool:
        """Cancel the order"""
        if not self.can_cancel():
            return False

        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.admin_notes = f"Cancelled: {reason}"
        self.save()

        # Release inventory reservations
        for item in self.items.all():
            for inventory in item.product.inventory_items.all():
                inventory.release_reservation(item.quantity)

        return True

    def confirm(self) -> bool:
        """Confirm the order"""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            return True
        return False

    def ship(self, tracking_number: str, carrier: str) -> bool:
        """Mark order as shipped"""
        if self.status in ['confirmed', 'processing']:
            self.status = 'shipped'
            self.tracking_number = tracking_number
            self.carrier = carrier
            self.shipped_at = timezone.now()
            self.save()
            return True
        return False

    def deliver(self) -> bool:
        """Mark order as delivered"""
        if self.status == 'shipped':
            self.status = 'delivered'
            self.delivered_at = timezone.now()
            self.save()

            # Deduct inventory
            for item in self.items.all():
                for inventory in item.product.inventory_items.all():
                    inventory.deduct_stock(item.quantity)

            return True
        return False

    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number"""
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"


class OrderItem(models.Model):
    """Items in an order"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    product_name = models.CharField(max_length=500)  # Snapshot of product name
    product_sku = models.CharField(max_length=100)  # Snapshot of SKU

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Review(models.Model):
    """Product reviews"""
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    order = models.ForeignKey(
        Order, null=True, blank=True,
        related_name='reviews', on_delete=models.SET_NULL
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    helpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"


class Wishlist(models.Model):
    """User wishlist"""
    user = models.OneToOneField(User, related_name='wishlist', on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='wishlisted_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return f"Wishlist of {self.user.username}"

    def add_product(self, product: Product) -> None:
        self.products.add(product)

    def remove_product(self, product: Product) -> None:
        self.products.remove(product)

    def has_product(self, product: Product) -> bool:
        return self.products.filter(pk=product.pk).exists()


class Coupon(models.Model):
    """Discount coupons"""
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    max_uses = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    applicable_categories = models.ManyToManyField(Category, blank=True)
    applicable_products = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'

    def __str__(self):
        return self.code

    def is_valid(self) -> bool:
        """Check if coupon is currently valid"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        """Calculate discount amount"""
        if not self.is_valid():
            return Decimal('0.00')

        if order_amount < self.minimum_order_amount:
            return Decimal('0.00')

        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
        else:
            discount = min(self.discount_value, order_amount)

        return discount

    def apply(self) -> None:
        """Mark coupon as used"""
        self.used_count += 1
        self.save()


class Notification(models.Model):
    """User notifications"""
    NOTIFICATION_TYPES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('low_stock', 'Low Stock Alert'),
        ('price_drop', 'Price Drop'),
        ('back_in_stock', 'Back in Stock'),
    ]

    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL
    )
    related_product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'generated_code'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"

    def mark_as_read(self) -> None:
        self.is_read = True
        self.save()


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """Service for user management operations"""

    @staticmethod
    def register_user(
        username: str,
        email: str,
        password: str,
        first_name: str = '',
        last_name: str = '',
        phone: str = ''
    ) -> User:
        """Register a new user"""
        if User.objects.filter(username=username).exists():
            raise ValueError(f"Username '{username}' already exists")
        if User.objects.filter(email=email).exists():
            raise ValueError(f"Email '{email}' already registered")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create profile
        UserProfile.objects.create(user=user, phone=phone)

        # Create cart
        Cart.objects.create(user=user)

        # Create wishlist
        Wishlist.objects.create(user=user)

        return user

    @staticmethod
    def get_user_stats(user: User) -> Dict[str, Any]:
        """Get user statistics"""
        orders = user.orders.all()
        return {
            'total_orders': orders.count(),
            'total_spent': orders.filter(
                payment_status='paid'
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.00'),
            'pending_orders': orders.filter(status='pending').count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'wishlist_count': user.wishlist.products.count() if hasattr(user, 'wishlist') else 0,
            'review_count': user.reviews.count(),
        }


class ProductService:
    """Service for product operations"""

    @staticmethod
    def search_products(
        query: str = '',
        category_id: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        brand: str = '',
        in_stock_only: bool = False,
        sort_by: str = 'relevance'
    ):
        """Search and filter products"""
        queryset = Product.objects.filter(is_active=True)

        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(brand__icontains=query) |
                models.Q(sku__icontains=query)
            )

        if category_id:
            try:
                category = Category.objects.get(pk=category_id)
                category_ids = [category.pk] + [c.pk for c in category.get_all_children()]
                queryset = queryset.filter(category_id__in=category_ids)
            except Category.DoesNotExist:
                pass

        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)

        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        if in_stock_only:
            queryset = queryset.filter(
                inventory_items__quantity__gt=0
            ).distinct()

        sort_options = {
            'price_asc': 'price',
            'price_desc': '-price',
            'newest': '-created_at',
            'name': 'name',
            'relevance': '-created_at',
        }
        queryset = queryset.order_by(sort_options.get(sort_by, '-created_at'))

        return queryset

    @staticmethod
    def get_featured_products(limit: int = 10):
        """Get featured products"""
        return Product.objects.filter(
            is_active=True, is_featured=True
        ).order_by('-created_at')[:limit]

    @staticmethod
    def get_related_products(product: Product, limit: int = 5):
        """Get related products from same category"""
        return Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(pk=product.pk)[:limit]

    @staticmethod
    def create_product(data: Dict[str, Any], user: User) -> Product:
        """Create a new product"""
        product = Product.objects.create(
            created_by=user,
            **data
        )
        return product

    @staticmethod
    def update_product_price(product: Product, new_price: Decimal, sale_price: Optional[Decimal] = None) -> None:
        """Update product pricing"""
        product.price = new_price
        product.sale_price = sale_price
        product.save()


class CartService:
    """Service for cart operations"""

    @staticmethod
    def get_or_create_cart(user: Optional[User] = None, session_key: str = '') -> Cart:
        """Get or create cart for user or session"""
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=user)
            return cart
        elif session_key:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
            return cart
        raise ValueError("Either user or session_key must be provided")

    @staticmethod
    def merge_carts(session_cart: Cart, user_cart: Cart) -> Cart:
        """Merge session cart into user cart on login"""
        for item in session_cart.items.all():
            user_cart.add_item(item.product, item.quantity)
        session_cart.delete()
        return user_cart

    @staticmethod
    def validate_cart(cart: Cart) -> List[str]:
        """Validate cart items for checkout"""
        errors = []
        for item in cart.items.all():
            if not item.product.is_active:
                errors.append(f"Product '{item.product.name}' is no longer available")
            elif not item.product.is_in_stock():
                errors.append(f"Product '{item.product.name}' is out of stock")
            elif item.product.get_total_stock() < item.quantity:
                errors.append(
                    f"Only {item.product.get_total_stock()} units of '{item.product.name}' available"
                )
        return errors


class OrderService:
    """Service for order management"""

    @staticmethod
    def create_order_from_cart(
        cart: Cart,
        user: User,
        shipping_address: Address,
        payment_method: str,
        coupon: Optional[Coupon] = None,
        notes: str = ''
    ) -> Order:
        """Create order from shopping cart"""
        # Validate cart
        errors = CartService.validate_cart(cart)
        if errors:
            raise ValueError('\n'.join(errors))

        if cart.items.count() == 0:
            raise ValueError("Cart is empty")

        # Calculate amounts
        subtotal = cart.get_subtotal()
        tax_rate = Decimal('0.10')  # 10% tax
        tax_amount = subtotal * tax_rate
        shipping_cost = Decimal('5.99') if subtotal < Decimal('50.00') else Decimal('0.00')
        discount_amount = Decimal('0.00')

        if coupon and coupon.is_valid():
            discount_amount = coupon.calculate_discount(subtotal)
            coupon.apply()

        total_amount = subtotal + tax_amount + shipping_cost - discount_amount

        # Create order
        order = Order.objects.create(
            order_number=Order.generate_order_number(),
            user=user,
            payment_method=payment_method,
            shipping_full_name=shipping_address.full_name,
            shipping_phone=shipping_address.phone,
            shipping_address_line1=shipping_address.address_line1,
            shipping_address_line2=shipping_address.address_line2,
            shipping_city=shipping_address.city,
            shipping_state=shipping_address.state,
            shipping_country=shipping_address.country,
            shipping_zip_code=shipping_address.zip_code,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            discount_amount=discount_amount,
            total_amount=total_amount,
            notes=notes
        )

        # Create order items and reserve inventory
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.get_effective_price(),
                total_price=cart_item.get_total_price(),
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku
            )

            # Reserve inventory
            for inventory in cart_item.product.inventory_items.all():
                inventory.reserve_stock(cart_item.quantity)
                break  # Reserve from first available warehouse

        # Clear cart
        cart.clear()

        # Send notification
        Notification.objects.create(
            user=user,
            notification_type='order_placed',
            title='Order Placed Successfully',
            message=f'Your order #{order.order_number} has been placed successfully.',
            related_order=order
        )

        return order

    @staticmethod
    def get_order_statistics() -> Dict[str, Any]:
        """Get overall order statistics"""
        orders = Order.objects.all()
        return {
            'total_orders': orders.count(),
            'pending_orders': orders.filter(status='pending').count(),
            'processing_orders': orders.filter(status='processing').count(),
            'shipped_orders': orders.filter(status='shipped').count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
            'total_revenue': orders.filter(
                payment_status='paid'
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.00'),
            'average_order_value': orders.filter(
                payment_status='paid'
            ).aggregate(
                avg=models.Avg('total_amount')
            )['avg'] or Decimal('0.00'),
        }


class InventoryService:
    """Service for inventory management"""

    @staticmethod
    def get_low_stock_products(threshold: Optional[int] = None):
        """Get products with low stock"""
        if threshold:
            return Inventory.objects.filter(quantity__lte=threshold)
        return Inventory.objects.filter(
            quantity__lte=models.F('reorder_point')
        )

    @staticmethod
    def get_out_of_stock_products():
        """Get products that are out of stock"""
        return Inventory.objects.filter(quantity=0)

    @staticmethod
    def adjust_inventory(
        inventory: Inventory,
        quantity_change: int,
        reason: str,
        user: User
    ) -> InventoryTransaction:
        """Adjust inventory quantity"""
        quantity_before = inventory.quantity
        inventory.quantity = max(0, inventory.quantity + quantity_change)
        inventory.save()

        transaction = InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type='adjustment',
            quantity=quantity_change,
            quantity_before=quantity_before,
            quantity_after=inventory.quantity,
            notes=reason,
            performed_by=user
        )

        # Check if low stock notification needed
        if inventory.needs_reorder():
            Notification.objects.create(
                user=user,
                notification_type='low_stock',
                title='Low Stock Alert',
                message=f'Product "{inventory.product.name}" at {inventory.warehouse.name} '
                       f'has only {inventory.quantity} units remaining.',
                related_product=inventory.product
            )

        return transaction

    @staticmethod
    def transfer_inventory(
        product: Product,
        from_warehouse: Warehouse,
        to_warehouse: Warehouse,
        quantity: int,
        user: User
    ) -> bool:
        """Transfer inventory between warehouses"""
        try:
            from_inventory = Inventory.objects.get(
                product=product, warehouse=from_warehouse
            )
        except Inventory.DoesNotExist:
            return False

        if from_inventory.get_available_quantity() < quantity:
            return False

        # Deduct from source
        quantity_before = from_inventory.quantity
        from_inventory.quantity -= quantity
        from_inventory.save()

        InventoryTransaction.objects.create(
            inventory=from_inventory,
            transaction_type='transfer',
            quantity=-quantity,
            quantity_before=quantity_before,
            quantity_after=from_inventory.quantity,
            reference_number=f"TRANSFER-{uuid.uuid4().hex[:8].upper()}",
            notes=f"Transfer to {to_warehouse.name}",
            performed_by=user
        )

        # Add to destination
        to_inventory, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=to_warehouse,
            defaults={'quantity': 0}
        )
        quantity_before_dest = to_inventory.quantity
        to_inventory.quantity += quantity
        to_inventory.save()

        InventoryTransaction.objects.create(
            inventory=to_inventory,
            transaction_type='transfer',
            quantity=quantity,
            quantity_before=quantity_before_dest,
            quantity_after=to_inventory.quantity,
            notes=f"Transfer from {from_warehouse.name}",
            performed_by=user
        )

        return True

    @staticmethod
    def get_inventory_report() -> Dict[str, Any]:
        """Generate inventory report"""
        inventories = Inventory.objects.select_related('product', 'warehouse')
        total_value = sum(
            inv.quantity * inv.product.cost_price
            for inv in inventories
        )
        return {
            'total_products': Product.objects.filter(is_active=True).count(),
            'total_inventory_value': total_value,
            'low_stock_count': inventories.filter(
                quantity__lte=models.F('reorder_point')
            ).count(),
            'out_of_stock_count': inventories.filter(quantity=0).count(),
            'total_warehouses': Warehouse.objects.filter(is_active=True).count(),
        }


class PurchaseOrderService:
    """Service for purchase order management"""

    @staticmethod
    def create_purchase_order(
        supplier: Supplier,
        warehouse: Warehouse,
        items: List[Dict[str, Any]],
        user: User,
        expected_delivery_date=None,
        notes: str = ''
    ) -> PurchaseOrder:
        """Create a new purchase order"""
        po = PurchaseOrder.objects.create(
            order_number=f"PO-{uuid.uuid4().hex[:8].upper()}",
            supplier=supplier,
            warehouse=warehouse,
            expected_delivery_date=expected_delivery_date,
            notes=notes,
            created_by=user
        )

        total = Decimal('0.00')
        for item_data in items:
            product = item_data['product']
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=product,
                quantity=quantity,
                unit_price=unit_price
            )
            total += quantity * unit_price

        po.total_amount = total
        po.save()

        return po

    @staticmethod
    def get_pending_orders():
        """Get all pending purchase orders"""
        return PurchaseOrder.objects.filter(
            status__in=['draft', 'submitted', 'approved', 'ordered']
        ).order_by('-created_at')

    @staticmethod
    def get_supplier_performance(supplier: Supplier) -> Dict[str, Any]:
        """Get supplier performance metrics"""
        orders = supplier.purchase_orders.all()
        on_time_deliveries = orders.filter(
            status='received',
            actual_delivery_date__lte=models.F('expected_delivery_date')
        ).count()
        total_received = orders.filter(status='received').count()

        return {
            'total_orders': orders.count(),
            'total_spend': supplier.get_total_spend(),
            'on_time_delivery_rate': (
                (on_time_deliveries / total_received * 100)
                if total_received > 0 else 0
            ),
            'average_lead_time': supplier.lead_time_days,
            'rating': float(supplier.rating),
        }


class ReportingService:
    """Service for generating reports"""

    @staticmethod
    def get_sales_report(
        start_date=None,
        end_date=None
    ) -> Dict[str, Any]:
        """Generate sales report"""
        orders = Order.objects.filter(payment_status='paid')

        if start_date:
            orders = orders.filter(ordered_at__gte=start_date)
        if end_date:
            orders = orders.filter(ordered_at__lte=end_date)

        total_revenue = orders.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')

        top_products = OrderItem.objects.filter(
            order__in=orders
        ).values(
            'product__name', 'product_id'
        ).annotate(
            total_quantity=models.Sum('quantity'),
            total_revenue=models.Sum('total_price')
        ).order_by('-total_revenue')[:10]

        return {
            'total_orders': orders.count(),
            'total_revenue': total_revenue,
            'average_order_value': (
                total_revenue / orders.count()
                if orders.count() > 0 else Decimal('0.00')
            ),
            'top_products': list(top_products),
        }

    @staticmethod
    def get_customer_report() -> Dict[str, Any]:
        """Generate customer report"""
        users = User.objects.filter(is_staff=False)
        return {
            'total_customers': users.count(),
            'new_customers_this_month': users.filter(
                date_joined__month=timezone.now().month,
                date_joined__year=timezone.now().year
            ).count(),
            'customers_with_orders': users.filter(
                orders__isnull=False
            ).distinct().count(),
        }


# ============================================================
# ADMIN INTERFACE
# ============================================================

from django.contrib import admin


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'city', 'country', 'is_active', 'rating']
    list_filter = ['is_active', 'country']
    search_fields = ['name', 'email', 'contact_person']


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'country', 'capacity', 'is_active']
    list_filter = ['is_active', 'country']
    search_fields = ['name', 'code']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price', 'sale_price', 'is_active', 'is_featured']
    list_filter = ['is_active', 'is_featured', 'category', 'condition']
    search_fields = ['name', 'sku', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'is_featured', 'price']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'reserved_quantity', 'reorder_point']
    list_filter = ['warehouse']
    search_fields = ['product__name', 'product__sku']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier', 'warehouse', 'status', 'total_amount', 'order_date']
    list_filter = ['status', 'supplier', 'warehouse']
    search_fields = ['order_number', 'supplier__name']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'payment_status', 'total_amount', 'ordered_at']
    list_filter = ['status', 'payment_status', 'payment_method']
    search_fields = ['order_number', 'user__username', 'user__email']
    readonly_fields = ['order_number', 'ordered_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'is_approved']
    search_fields = ['product__name', 'user__username']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'is_seller', 'is_warehouse_staff']
    list_filter = ['is_seller', 'is_warehouse_staff']
    search_fields = ['user__username', 'user__email']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_until', 'is_active', 'used_count']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']


# ============================================================
# URL CONFIGURATION
# ============================================================

from django.urls import path
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
import json


def api_response(data: Any, status: int = 200) -> JsonResponse:
    """Helper to create API responses"""
    return JsonResponse(data, status=status, safe=False)


def error_response(message: str, status: int = 400) -> JsonResponse:
    """Helper to create error responses"""
    return JsonResponse({'error': message}, status=status)


# Authentication Views
@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = UserService.register_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                phone=data.get('phone', '')
            )
            return api_response({
                'message': 'User registered successfully',
                'user_id': user.id,
                'username': user.username
            }, 201)
        except ValueError as e:
            return error_response(str(e))
        except KeyError as e:
            return error_response(f"Missing field: {e}")
    return error_response('Method not allowed', 405)


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = authenticate(
                request,
                username=data['username'],
                password=data['password']
            )
            if user:
                login(request, user)
                return api_response({
                    'message': 'Login successful',
                    'user_id': user.id,
                    'username': user.username,
                    'is_staff': user.is_staff
                })
            return error_response('Invalid credentials', 401)
        except KeyError as e:
            return error_response(f"Missing field: {e}")
    return error_response('Method not allowed', 405)


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return api_response({'message': 'Logged out successfully'})
    return error_response('Method not allowed', 405)


# Product Views
def product_list_view(request):
    if request.method == 'GET':
        query = request.GET.get('q', '')
        category_id = request.GET.get('category')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        brand = request.GET.get('brand', '')
        in_stock = request.GET.get('in_stock', 'false').lower() == 'true'
        sort_by = request.GET.get('sort', 'relevance')

        products = ProductService.search_products(
            query=query,
            category_id=int(category_id) if category_id else None,
            min_price=Decimal(min_price) if min_price else None,
            max_price=Decimal(max_price) if max_price else None,
            brand=brand,
            in_stock_only=in_stock,
            sort_by=sort_by
        )

        data = [{
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'sku': p.sku,
            'price': str(p.price),
            'sale_price': str(p.sale_price) if p.sale_price else None,
            'effective_price': str(p.get_effective_price()),
            'discount_percentage': p.get_discount_percentage(),
            'brand': p.brand,
            'category': p.category.name,
            'is_in_stock': p.is_in_stock(),
            'average_rating': p.get_average_rating(),
            'review_count': p.get_review_count(),
        } for p in products]

        return api_response(data)
    return error_response('Method not allowed', 405)


def product_detail_view(request, product_id):
    if request.method == 'GET':
        try:
            product = Product.objects.get(pk=product_id, is_active=True)
            data = {
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'sku': product.sku,
                'description': product.description,
                'short_description': product.short_description,
                'price': str(product.price),
                'sale_price': str(product.sale_price) if product.sale_price else None,
                'effective_price': str(product.get_effective_price()),
                'discount_percentage': product.get_discount_percentage(),
                'brand': product.brand,
                'condition': product.condition,
                'weight': str(product.weight),
                'dimensions': product.dimensions,
                'category': {
                    'id': product.category.id,
                    'name': product.category.name,
                    'path': product.category.get_full_path()
                },
                'total_stock': product.get_total_stock(),
                'is_in_stock': product.is_in_stock(),
                'average_rating': product.get_average_rating(),
                'review_count': product.get_review_count(),
                'attributes': [
                    {'name': a.name, 'value': a.value}
                    for a in product.attributes.all()
                ],
                'reviews': [
                    {
                        'user': r.user.username,
                        'rating': r.rating,
                        'title': r.title,
                        'body': r.body,
                        'is_verified': r.is_verified_purchase,
                        'created_at': r.created_at.isoformat()
                    }
                    for r in product.reviews.filter(is_approved=True)[:10]
                ]
            }
            return api_response(data)
        except Product.DoesNotExist:
            return error_response('Product not found', 404)
    return error_response('Method not allowed', 405)


# Cart Views
@csrf_exempt
def cart_view(request):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    cart = CartService.get_or_create_cart(user=request.user)

    if request.method == 'GET':
        data = {
            'id': cart.id,
            'total_items': cart.get_total_items(),
            'subtotal': str(cart.get_subtotal()),
            'items': [
                {
                    'product_id': item.product.id,
                    'product_name': item.product.name,
                    'product_sku': item.product.sku,
                    'quantity': item.quantity,
                    'unit_price': str(item.product.get_effective_price()),
                    'total_price': str(item.get_total_price()),
                    'is_in_stock': item.product.is_in_stock()
                }
                for item in cart.items.all()
            ]
        }
        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product = Product.objects.get(pk=data['product_id'], is_active=True)
            quantity = int(data.get('quantity', 1))

            if quantity <= 0:
                return error_response('Quantity must be positive')

            if product.get_total_stock() < quantity:
                return error_response('Insufficient stock')

            cart_item = cart.add_item(product, quantity)
            return api_response({
                'message': 'Item added to cart',
                'cart_item_id': cart_item.id,
                'quantity': cart_item.quantity
            }, 201)
        except Product.DoesNotExist:
            return error_response('Product not found', 404)
        except (KeyError, ValueError) as e:
            return error_response(str(e))

    elif request.method == 'DELETE':
        cart.clear()
        return api_response({'message': 'Cart cleared'})

    return error_response('Method not allowed', 405)


@csrf_exempt
def cart_item_view(request, product_id):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    cart = CartService.get_or_create_cart(user=request.user)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            quantity = int(data['quantity'])
            product = Product.objects.get(pk=product_id)

            if quantity > product.get_total_stock():
                return error_response('Insufficient stock')

            success = cart.update_item_quantity(product, quantity)
            if success:
                return api_response({'message': 'Cart updated', 'quantity': quantity})
            return error_response('Item not found in cart', 404)
        except (Product.DoesNotExist, KeyError, ValueError) as e:
            return error_response(str(e))

    elif request.method == 'DELETE':
        try:
            product = Product.objects.get(pk=product_id)
            cart.remove_item(product)
            return api_response({'message': 'Item removed from cart'})
        except Product.DoesNotExist:
            return error_response('Product not found', 404)

    return error_response('Method not allowed', 405)


# Order Views
@csrf_exempt
def order_list_view(request):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    if request.method == 'GET':
        orders = request.user.orders.all()
        data = [{
            'id': o.id,
            'order_number': o.order_number,
            'status': o.status,
            'payment_status': o.payment_status,
            'total_amount': str(o.total_amount),
            'total_items': o.get_total_items(),
            'ordered_at': o.ordered_at.isoformat(),
        } for o in orders]
        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart = CartService.get_or_create_cart(user=request.user)
            address = Address.objects.get(
                pk=data['address_id'],
                user=request.user
            )
            payment_method = data['payment_method']

            coupon = None
            if data.get('coupon_code'):
                try:
                    coupon = Coupon.objects.get(code=data['coupon_code'])
                except Coupon.DoesNotExist:
                    pass

            order = OrderService.create_order_from_cart(
                cart=cart,
                user=request.user,
                shipping_address=address,
                payment_method=payment_method,
                coupon=coupon,
                notes=data.get('notes', '')
            )

            return api_response({
                'message': 'Order created successfully',
                'order_id': order.id,
                'order_number': order.order_number,
                'total_amount': str(order.total_amount)
            }, 201)

        except Address.DoesNotExist:
            return error_response('Address not found', 404)
        except ValueError as e:
            return error_response(str(e))
        except KeyError as e:
            return error_response(f"Missing field: {e}")

    return error_response('Method not allowed', 405)


def order_detail_view(request, order_id):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    try:
        if request.user.is_staff:
            order = Order.objects.get(pk=order_id)
        else:
            order = Order.objects.get(pk=order_id, user=request.user)

        data = {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'payment_status': order.payment_status,
            'payment_method': order.payment_method,
            'subtotal': str(order.subtotal),
            'tax_amount': str(order.tax_amount),
            'shipping_cost': str(order.shipping_cost),
            'discount_amount': str(order.discount_amount),
            'total_amount': str(order.total_amount),
            'tracking_number': order.tracking_number,
            'carrier': order.carrier,
            'notes': order.notes,
            'ordered_at': order.ordered_at.isoformat(),
            'shipping_address': {
                'full_name': order.shipping_full_name,
                'phone': order.shipping_phone,
                'address': order.shipping_address_line1,
                'city': order.shipping_city,
                'state': order.shipping_state,
                'country': order.shipping_country,
                'zip_code': order.shipping_zip_code,
            },
            'items': [
                {
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'product_sku': item.product_sku,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'total_price': str(item.total_price),
                }
                for item in order.items.all()
            ]
        }
        return api_response(data)

    except Order.DoesNotExist:
        return error_response('Order not found', 404)


@csrf_exempt
def order_cancel_view(request, order_id):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    if request.method == 'POST':
        try:
            order = Order.objects.get(pk=order_id, user=request.user)
            data = json.loads(request.body) if request.body else {}
            reason = data.get('reason', '')

            if order.cancel(reason):
                return api_response({'message': 'Order cancelled successfully'})
            return error_response('Order cannot be cancelled in its current status')

        except Order.DoesNotExist:
            return error_response('Order not found', 404)

    return error_response('Method not allowed', 405)


# Inventory Management Views (Admin)
def inventory_list_view(request):
    if not request.user.is_staff:
        return error_response('Admin access required', 403)

    if request.method == 'GET':
        inventories = Inventory.objects.select_related(
            'product', 'warehouse'
        ).all()

        data = [{
            'id': inv.id,
            'product_id': inv.product.id,
            'product_name': inv.product.name,
            'product_sku': inv.product.sku,
            'warehouse_id': inv.warehouse.id,
            'warehouse_name': inv.warehouse.name,
            'quantity': inv.quantity,
            'reserved_quantity': inv.reserved_quantity,
            'available_quantity': inv.get_available_quantity(),
            'reorder_point': inv.reorder_point,
            'needs_reorder': inv.needs_reorder(),
        } for inv in inventories]

        return api_response(data)

    return error_response('Method not allowed', 405)


def inventory_report_view(request):
    if not request.user.is_staff:
        return error_response('Admin access required', 403)

    if request.method == 'GET':
        report = InventoryService.get_inventory_report()
        report['total_inventory_value'] = str(report['total_inventory_value'])
        return api_response(report)

    return error_response('Method not allowed', 405)


# Purchase Order Views (Admin)
@csrf_exempt
def purchase_order_list_view(request):
    if not request.user.is_staff:
        return error_response('Admin access required', 403)

    if request.method == 'GET':
        orders = PurchaseOrder.objects.select_related(
            'supplier', 'warehouse'
        ).all().order_by('-created_at')

        data = [{
            'id': po.id,
            'order_number': po.order_number,
            'supplier': po.supplier.name,
            'warehouse': po.warehouse.name,
            'status': po.status,
            'total_amount': str(po.total_amount),
            'order_date': po.order_date.isoformat(),
            'expected_delivery': po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
        } for po in orders]

        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            supplier = Supplier.objects.get(pk=data['supplier_id'])
            warehouse = Warehouse.objects.get(pk=data['warehouse_id'])

            items = []
            for item_data in data['items']:
                product = Product.objects.get(pk=item_data['product_id'])
                items.append({
                    'product': product,
                    'quantity': item_data['quantity'],
                    'unit_price': Decimal(str(item_data['unit_price']))
                })

            po = PurchaseOrderService.create_purchase_order(
                supplier=supplier,
                warehouse=warehouse,
                items=items,
                user=request.user,
                notes=data.get('notes', '')
            )

            return api_response({
                'message': 'Purchase order created',
                'order_id': po.id,
                'order_number': po.order_number,
                'total_amount': str(po.total_amount)
            }, 201)

        except (Supplier.DoesNotExist, Warehouse.DoesNotExist, Product.DoesNotExist) as e:
            return error_response(f"Resource not found: {e}", 404)
        except KeyError as e:
            return error_response(f"Missing field: {e}")

    return error_response('Method not allowed', 405)


# Supplier Views (Admin)
@csrf_exempt
def supplier_list_view(request):
    if not request.user.is_staff:
        return error_response('Admin access required', 403)

    if request.method == 'GET':
        suppliers = Supplier.objects.filter(is_active=True)
        data = [{
            'id': s.id,
            'name': s.name,
            'email': s.email,
            'phone': s.phone,
            'city': s.city,
            'country': s.country,
            'contact_person': s.contact_person,
            'lead_time_days': s.lead_time_days,
            'rating': str(s.rating),
            'total_orders': s.get_total_orders(),
        } for s in suppliers]
        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            supplier = Supplier.objects.create(**data)
            return api_response({
                'message': 'Supplier created',
                'supplier_id': supplier.id,
                'name': supplier.name
            }, 201)
        except Exception as e:
            return error_response(str(e))

    return error_response('Method not allowed', 405)


# Warehouse Views (Admin)
@csrf_exempt
def warehouse_list_view(request):
    if not request.user.is_staff:
        return error_response('Admin access required', 403)

    if request.method == 'GET':
        warehouses = Warehouse.objects.filter(is_active=True)
        data = [{
            'id': w.id,
            'name': w.name,
            'code': w.code,
            'city': w.city,
            'country': w.country,
            'capacity': w.capacity,
            'available_capacity': w.get_available_capacity(),
            'total_inventory_value': str(w.get_total_inventory_value()),
        } for w in warehouses]
        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            warehouse = Warehouse.objects.create(**data)
            return api_response({
                'message': 'Warehouse created',
                'warehouse_id': warehouse.id,
                'name': warehouse.name
            }, 201)
        except Exception as e:
            return error_response(str(e))

    return error_response('Method not allowed', 405)


# Dashboard/Reports Views (Admin)
def admin_dashboard_view(request):
    if not request.user.is_staff:
        return error_response('Admin access required', 403)

    if request.method == 'GET':
        order_stats = OrderService.get_order_statistics()
        inventory_report = InventoryService.get_inventory_report()
        customer_report = ReportingService.get_customer_report()
        sales_report = ReportingService.get_sales_report()

        data = {
            'orders': {
                'total': order_stats['total_orders'],
                'pending': order_stats['pending_orders'],
                'processing': order_stats['processing_orders'],
                'shipped': order_stats['shipped_orders'],
                'delivered': order_stats['delivered_orders'],
                'cancelled': order_stats['cancelled_orders'],
                'total_revenue': str(order_stats['total_revenue']),
                'average_order_value': str(order_stats['average_order_value']),
            },
            'inventory': {
                'total_products': inventory_report['total_products'],
                'total_value': str(inventory_report['total_inventory_value']),
                'low_stock_count': inventory_report['low_stock_count'],
                'out_of_stock_count': inventory_report['out_of_stock_count'],
                'total_warehouses': inventory_report['total_warehouses'],
            },
            'customers': customer_report,
            'sales': {
                'total_orders': sales_report['total_orders'],
                'total_revenue': str(sales_report['total_revenue']),
                'average_order_value': str(sales_report['average_order_value']),
            }
        }
        return api_response(data)

    return error_response('Method not allowed', 405)


# User Management Views
def user_profile_view(request):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    if request.method == 'GET':
        user = request.user
        profile = user.profile if hasattr(user, 'profile') else None
        stats = UserService.get_user_stats(user)

        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat(),
            'profile': {
                'phone': profile.phone if profile else '',
                'is_seller': profile.is_seller if profile else False,
            } if profile else None,
            'stats': {
                'total_orders': stats['total_orders'],
                'total_spent': str(stats['total_spent']),
                'pending_orders': stats['pending_orders'],
                'delivered_orders': stats['delivered_orders'],
                'wishlist_count': stats['wishlist_count'],
                'review_count': stats['review_count'],
            }
        }
        return api_response(data)

    return error_response('Method not allowed', 405)


def address_list_view(request):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    if request.method == 'GET':
        addresses = request.user.addresses.all()
        data = [{
            'id': a.id,
            'address_type': a.address_type,
            'full_name': a.full_name,
            'phone': a.phone,
            'address_line1': a.address_line1,
            'address_line2': a.address_line2,
            'city': a.city,
            'state': a.state,
            'country': a.country,
            'zip_code': a.zip_code,
            'is_default': a.is_default,
        } for a in addresses]
        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            address = Address.objects.create(
                user=request.user,
                **{k: v for k, v in data.items() if k != 'user'}
            )
            return api_response({
                'message': 'Address added',
                'address_id': address.id
            }, 201)
        except Exception as e:
            return error_response(str(e))

    return error_response('Method not allowed', 405)


def wishlist_view(request):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        data = {
            'products': [{
                'id': p.id,
                'name': p.name,
                'price': str(p.price),
                'effective_price': str(p.get_effective_price()),
                'is_in_stock': p.is_in_stock(),
            } for p in wishlist.products.all()]
        }
        return api_response(data)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product = Product.objects.get(pk=data['product_id'])
            wishlist.add_product(product)
            return api_response({'message': 'Product added to wishlist'})
        except Product.DoesNotExist:
            return error_response('Product not found', 404)

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            product = Product.objects.get(pk=data['product_id'])
            wishlist.remove_product(product)
            return api_response({'message': 'Product removed from wishlist'})
        except Product.DoesNotExist:
            return error_response('Product not found', 404)

    return error_response('Method not allowed', 405)


def notification_list_view(request):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 401)

    if request.method == 'GET':
        notifications = request.user.notifications.all()[:20]
        data = [{
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        } for n in notifications]
        return api_response(data)

    return error_response('Method not allowed', 405)


def category_list_view(request):
    if request.method == 'GET':
        categories = Category.objects.filter(is_active=True, parent=None)
        data = [{
            'id': c.id,
            'name': c.name,
            'slug': c.slug,
            'description': c.description,
            'children': [{
                'id': child.id,
                'name': child.name,
                'slug': child.slug,
            } for child in c.children.filter(is_active=True)]
        } for c in categories]
        return api_response(data)

    return error_response('Method not allowed', 405)


def health_check_view(request):
    return api_response({
        'status': 'healthy',
        'service': 'Amazon Clone API',
        'version': '1.0.0'
    })


# URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check_view),
    path('api/auth/register/', register_view),
    path('api/auth/login/', login_view),
    path('api/auth/logout/', logout_view),
    path('api/products/', product_list_view),
    path('api/products/<int:product_id>/', product_detail_view),
    path('api/categories/', category_list_view),
    path('api/cart/', cart_view),
    path('api/cart/<int:product_id>/', cart_item_view),
    path('api/orders/', order_list_view),
    path('api/orders/<int:order_id>/', order_detail_view),
    path('api/orders/<int:order_id>/cancel/', order_cancel_view),
    path('api/profile/', user_profile_view),
    path('api/addresses/', address_list_view),
    path('api/wishlist/', wishlist_view),
    path('api/notifications/', notification_list_view),
    path('api/admin/dashboard/', admin_dashboard_view),
    path('api/admin/inventory/', inventory_list_view),
    path('api/admin/inventory/report/', inventory_report_view),
    path('api/admin/purchase-orders/', purchase_order_list_view),
    path('api/admin/suppliers/', supplier_list_view),
    path('api/admin/warehouses/', warehouse_list_view),
]


# ============================================================
# DATABASE SETUP AND DEMO DATA
# ============================================================

def create_tables():
    """Create database tables"""
    # [REVISED] rewrote this function. The original used
    # `setup_test_environment()` + `migrate --run-syncdb`, which skips a
    # single-file app whose models_module is None (so no tables were built).
    # Now: run standard migrations, then create the generated_code app's tables
    # directly via the schema editor.
    from django.core.management import call_command
    from django.db import connection
    from django.apps import apps

    # Run standard migrations (auth, sessions, contenttypes, admin)
    call_command('migrate', verbosity=0)

    # syncdb skips single-file apps whose models_module is None,
    # so manually create tables for the generated_code app.
    app_config = apps.get_app_config('generated_code')
    existing_tables = connection.introspection.table_names()
    with connection.schema_editor() as editor:
        for model in app_config.get_models():
            if model._meta.db_table not in existing_tables:
                editor.create_model(model)

    print("Database tables created successfully.")


def create_demo_data():
    """Create demo data for testing"""
    print("Creating demo data...")

    # Create admin user
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@amazon-clone.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        UserProfile.objects.get_or_create(user=admin)
        print(f"Admin user created: admin/admin123")

    # Create regular user
    if not User.objects.filter(username='john_doe').exists():
        user = UserService.register_user(
            username='john_doe',
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            phone='+1234567890'
        )
        print(f"Regular user created: john_doe/password123")

        # Add address for user
        Address.objects.create(
            user=user,
            address_type='both',
            full_name='John Doe',
            phone='+1234567890',
            address_line1='123 Main Street',
            city='New York',
            state='NY',
            country='USA',
            zip_code='10001',
            is_default=True
        )

    # Create categories
    electronics, _ = Category.objects.get_or_create(
        slug='electronics',
        defaults={'name': 'Electronics', 'description': 'Electronic devices and accessories'}
    )
    phones, _ = Category.objects.get_or_create(
        slug='smartphones',
        defaults={'name': 'Smartphones', 'parent': electronics, 'description': 'Mobile phones'}
    )
    laptops, _ = Category.objects.get_or_create(
        slug='laptops',
        defaults={'name': 'Laptops', 'parent': electronics, 'description': 'Laptop computers'}
    )
    clothing, _ = Category.objects.get_or_create(
        slug='clothing',
        defaults={'name': 'Clothing', 'description': 'Fashion and apparel'}
    )
    books, _ = Category.objects.get_or_create(
        slug='books',
        defaults={'name': 'Books', 'description': 'Books and literature'}
    )
    print("Categories created.")

    # Create supplier
    supplier, _ = Supplier.objects.get_or_create(
        email='supplier@techcorp.com',
        defaults={
            'name': 'TechCorp Supplies',
            'phone': '+1-800-TECH',
            'address': '456 Tech Avenue',
            'city': 'San Francisco',
            'state': 'CA',
            'country': 'USA',
            'zip_code': '94102',
            'contact_person': 'Jane Smith',
            'lead_time_days': 5,
            'rating': Decimal('4.5')
        }
    )
    print("Supplier created.")

    # Create warehouse
    warehouse, _ = Warehouse.objects.get_or_create(
        code='WH-001',
        defaults={
            'name': 'Main Warehouse',
            'address': '789 Warehouse Blvd',
            'city': 'Chicago',
            'state': 'IL',
            'country': 'USA',
            'zip_code': '60601',
            'capacity': 10000
        }
    )
    print("Warehouse created.")

    # Create products
    products_data = [
        {
            'name': 'iPhone 15 Pro',
            'slug': 'iphone-15-pro',
            'sku': 'APPL-IP15P-001',
            'description': 'Latest iPhone with advanced camera system and A17 Pro chip.',
            'short_description': 'Apple iPhone 15 Pro - 256GB',
            'category': phones,
            'brand': 'Apple',
            'price': Decimal('999.99'),
            'cost_price': Decimal('650.00'),
            'sale_price': Decimal('949.99'),
            'weight': Decimal('0.187'),
            'is_featured': True,
        },
        {
            'name': 'Samsung Galaxy S24',
            'slug': 'samsung-galaxy-s24',
            'sku': 'SAMS-GS24-001',
            'description': 'Samsung flagship smartphone with AI features.',
            'short_description': 'Samsung Galaxy S24 - 128GB',
            'category': phones,
            'brand': 'Samsung',
            'price': Decimal('799.99'),
            'cost_price': Decimal('500.00'),
            'weight': Decimal('0.167'),
            'is_featured': True,
        },
        {
            'name': 'MacBook Pro 14"',
            'slug': 'macbook-pro-14',
            'sku': 'APPL-MBP14-001',
            'description': 'Powerful laptop with M3 Pro chip for professionals.',
            'short_description': 'Apple MacBook Pro 14" M3 Pro',
            'category': laptops,
            'brand': 'Apple',
            'price': Decimal('1999.99'),
            'cost_price': Decimal('1300.00'),
            'weight': Decimal('1.6'),
            'is_featured': True,
        },
        {
            'name': 'Python Programming Book',
            'slug': 'python-programming-book',
            'sku': 'BOOK-PY-001',
            'description': 'Comprehensive guide to Python programming.',
            'short_description': 'Learn Python Programming',
            'category': books,
            'brand': 'Tech Publishers',
            'price': Decimal('49.99'),
            'cost_price': Decimal('15.00'),
            'weight': Decimal('0.5'),
        },
        {
            'name': 'Classic T-Shirt',
            'slug': 'classic-t-shirt',
            'sku': 'CLTH-TS-001',
            'description': 'Comfortable cotton t-shirt for everyday wear.',
            'short_description': 'Classic Cotton T-Shirt',
            'category': clothing,
            'brand': 'BasicWear',
            'price': Decimal('19.99'),
            'cost_price': Decimal('5.00'),
            'sale_price': Decimal('14.99'),
            'weight': Decimal('0.2'),
        },
    ]

    admin_user = User.objects.get(username='admin')
    for prod_data in products_data:
        product, created = Product.objects.get_or_create(
            sku=prod_data['sku'],
            defaults={**prod_data, 'created_by': admin_user}
        )
        if created:
            # Add inventory
            Inventory.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                defaults={
                    'quantity': 100,
                    'reorder_point': 10,
                    'reorder_quantity': 50
                }
            )

    print("Products and inventory created.")

    # Create a coupon
    from django.utils import timezone
    Coupon.objects.get_or_create(
        code='SAVE10',
        defaults={
            'discount_type': 'percentage',
            'discount_value': Decimal('10.00'),
            'minimum_order_amount': Decimal('50.00'),
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timezone.timedelta(days=365),
            'max_uses': 1000,
            'is_active': True
        }
    )
    print("Coupon SAVE10 created (10% off orders over $50).")

    print("\nDemo data creation complete!")
    print("\nLogin credentials:")
    print("  Admin: admin / admin123")
    print("  User: john_doe / password123")


def run_demo():
    """Run a demonstration of the system"""
    print("\n" + "="*60)
    print("AMAZON CLONE - SYSTEM DEMONSTRATION")
    print("="*60)

    # Test user registration
    print("\n1. USER REGISTRATION")
    try:
        test_user = UserService.register_user(
            username='test_customer',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Customer'
        )
        print(f"   ✓ User registered: {test_user.username}")
    except ValueError:
        test_user = User.objects.get(username='test_customer')
        print(f"   ✓ User already exists: {test_user.username}")

    # Test product search
    print("\n2. PRODUCT SEARCH")
    products = ProductService.search_products(query='iPhone')
    print(f"   ✓ Found {products.count()} products matching 'iPhone'")

    products_in_stock = ProductService.search_products(in_stock_only=True)
    print(f"   ✓ Found {products_in_stock.count()} products in stock")

    # Test cart operations
    print("\n3. CART OPERATIONS")
    cart = CartService.get_or_create_cart(user=test_user)
    product = Product.objects.filter(is_active=True).first()
    if product:
        cart.add_item(product, 2)
        print(f"   ✓ Added {product.name} x2 to cart")
        print(f"   ✓ Cart total: ${cart.get_subtotal()}")
        print(f"   ✓ Cart items: {cart.get_total_items()}")

    # Test inventory
    print("\n4. INVENTORY MANAGEMENT")
    inventory_report = InventoryService.get_inventory_report()
    print(f"   ✓ Total products: {inventory_report['total_products']}")
    print(f"   ✓ Total inventory value: ${inventory_report['total_inventory_value']}")
    print(f"   ✓ Low stock items: {inventory_report['low_stock_count']}")
    print(f"   ✓ Out of stock items: {inventory_report['out_of_stock_count']}")

    # Test order statistics
    print("\n5. ORDER STATISTICS")
    order_stats = OrderService.get_order_statistics()
    print(f"   ✓ Total orders: {order_stats['total_orders']}")
    print(f"   ✓ Total revenue: ${order_stats['total_revenue']}")

    # Test supplier performance
    print("\n6. SUPPLIER MANAGEMENT")
    suppliers = Supplier.objects.filter(is_active=True)
    print(f"   ✓ Active suppliers: {suppliers.count()}")
    for supplier in suppliers:
        perf = PurchaseOrderService.get_supplier_performance(supplier)
        print(f"   ✓ {supplier.name}: {perf['total_orders']} orders, ${perf['total_spend']} total spend")

    # Test warehouse management
    print("\n7. WAREHOUSE MANAGEMENT")
    warehouses = Warehouse.objects.filter(is_active=True)
    print(f"   ✓ Active warehouses: {warehouses.count()}")
    for warehouse in warehouses:
        print(f"   ✓ {warehouse.name}: {warehouse.get_available_capacity()} capacity available")
        print(f"     Total inventory value: ${warehouse.get_total_inventory_value()}")

    # Test category hierarchy
    print("\n8. CATEGORY HIERARCHY")
    root_categories = Category.objects.filter(parent=None, is_active=True)
    for cat in root_categories:
        children = cat.children.filter(is_active=True)
        print(f"   ✓ {cat.name} ({children.count()} subcategories)")
        for child in children:
            print(f"     - {child.get_full_path()}")

    # Test coupon
    print("\n9. COUPON SYSTEM")
    try:
        coupon = Coupon.objects.get(code='SAVE10')
        test_amount = Decimal('100.00')
        discount = coupon.calculate_discount(test_amount)
        print(f"   ✓ Coupon SAVE10: {discount} discount on ${test_amount} order")
        print(f"   ✓ Coupon valid: {coupon.is_valid()}")
    except Coupon.DoesNotExist:
        print("   ✗ No coupons found")

    # Test featured products
    print("\n10. FEATURED PRODUCTS")
    featured = ProductService.get_featured_products()
    print(f"   ✓ Featured products: {featured.count()}")
    for p in featured:
        print(f"     - {p.name}: ${p.get_effective_price()} (discount: {p.get_discount_percentage()}%)")

    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nAPI Endpoints Available:")
    print("  POST /api/auth/register/     - User registration")
    print("  POST /api/auth/login/        - User login")
    print("  POST /api/auth/logout/       - User logout")
    print("  GET  /api/products/          - List/search products")
    print("  GET  /api/products/<id>/     - Product detail")
    print("  GET  /api/categories/        - Category list")
    print("  GET/POST /api/cart/          - Cart management")
    print("  PUT/DELETE /api/cart/<id>/   - Cart item management")
    print("  GET/POST /api/orders/        - Order management")
    print("  GET  /api/orders/<id>/       - Order detail")
    print("  POST /api/orders/<id>/cancel/ - Cancel order")
    print("  GET  /api/profile/           - User profile")
    print("  GET/POST /api/addresses/     - Address management")
    print("  GET/POST/DELETE /api/wishlist/ - Wishlist")
    print("  GET  /api/notifications/     - Notifications")
    print("  GET  /api/admin/dashboard/   - Admin dashboard")
    print("  GET  /api/admin/inventory/   - Inventory management")
    print("  GET  /api/admin/inventory/report/ - Inventory report")
    print("  GET/POST /api/admin/purchase-orders/ - Purchase orders")
    print("  GET/POST /api/admin/suppliers/ - Supplier management")
    print("  GET/POST /api/admin/warehouses/ - Warehouse management")


# ============================================================
# WSGI APPLICATION
# ============================================================

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    print("Amazon Clone - Django Application")
    print("="*40)

    # Setup database
    print("\nSetting up database...")
    create_tables()

    # Create demo data
    create_demo_data()

    # Run demonstration
    run_demo()

    # Start development server if requested
    if '--server' in sys.argv:
        from django.core.management import call_command
        print("\nStarting development server on http://127.0.0.1:8000/")
        print("Admin panel: http://127.0.0.1:8000/admin/")
        call_command('runserver', '127.0.0.1:8000')
    else:
        print("\nTo start the development server, run:")
        print("  python solution.py --server")
        print("\nOr use Django's manage.py:")
        print("  python -c \"import solution; from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', 'runserver'])\"")