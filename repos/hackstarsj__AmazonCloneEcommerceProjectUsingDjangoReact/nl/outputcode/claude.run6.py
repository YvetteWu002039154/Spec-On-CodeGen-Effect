#!/usr/bin/env python3
"""
Amazon Clone - Complete Django Implementation
A fully functional e-commerce platform with inventory management system.
"""

import os
import sys
import django
from django.conf import settings

# ============================================================
# DJANGO SETTINGS CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='amazon-clone-secret-key-change-in-production-xyz123',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'amazon_clone.db'),
            }
        },
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
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
        }],
        STATIC_URL='/static/',
        MEDIA_URL='/media/',
        MEDIA_ROOT=os.path.join(BASE_DIR, 'media'),
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        AUTH_USER_MODEL='auth.User',
        LOGIN_URL='/login/',
        LOGIN_REDIRECT_URL='/',
        LOGOUT_REDIRECT_URL='/',
    )

django.setup()

# ============================================================
# MODELS
# ============================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid


class UserProfile(models.Model):
    """Extended user profile for customers and staff."""
    
    USER_TYPES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('supplier', 'Supplier'),
        ('warehouse_manager', 'Warehouse Manager'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


class Address(models.Model):
    """User address model."""
    
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    full_name = models.CharField(max_length=200)
    street_address1 = models.CharField(max_length=255)
    street_address2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        verbose_name_plural = 'Addresses'
    
    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.state}"


class Category(models.Model):
    """Product category with multi-level support."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def get_ancestors(self):
        """Get all ancestor categories."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors
    
    def get_descendants(self):
        """Get all descendant categories."""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Supplier(models.Model):
    """Supplier model for inventory management."""
    
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.name
    
    def get_total_orders(self):
        return self.purchase_orders.count()
    
    def get_pending_orders(self):
        return self.purchase_orders.filter(status='pending').count()


class Warehouse(models.Model):
    """Warehouse model for inventory storage."""
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_warehouses')
    capacity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_total_inventory_value(self):
        total = Decimal('0.00')
        for inventory in self.inventories.all():
            total += inventory.quantity * inventory.product.cost_price
        return total
    
    def get_total_items(self):
        return sum(inv.quantity for inv in self.inventories.all())


class Brand(models.Model):
    """Product brand model."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Main product model."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    name = models.CharField(max_length=500)
    slug = models.SlugField(unique=True, max_length=500)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    short_description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.name
    
    def get_discounted_price(self):
        if self.discount_percentage > 0:
            discount = self.price * (self.discount_percentage / 100)
            return self.price - discount
        return self.price
    
    def get_total_stock(self):
        return sum(inv.quantity for inv in self.inventories.all())
    
    def is_in_stock(self):
        return self.get_total_stock() > 0
    
    def get_average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / len(reviews)
        return 0
    
    def get_review_count(self):
        return self.reviews.count()
    
    def get_profit_margin(self):
        if self.cost_price > 0:
            return ((self.price - self.cost_price) / self.price) * 100
        return 0


class ProductVariant(models.Model):
    """Product variant (size, color, etc.)."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    attributes = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
    def get_price(self):
        return self.product.price + self.price_modifier


class ProductImage(models.Model):
    """Product images."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.order}"


class Inventory(models.Model):
    """Inventory tracking per product per warehouse."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventories')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    reorder_point = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    max_stock_level = models.IntegerField(default=1000)
    location_in_warehouse = models.CharField(max_length=100, blank=True)
    last_counted = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
        unique_together = ['product', 'warehouse', 'variant']
        verbose_name_plural = 'Inventories'
    
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"
    
    def get_available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self):
        return self.quantity <= self.reorder_point
    
    def is_overstocked(self):
        return self.quantity > self.max_stock_level


class InventoryTransaction(models.Model):
    """Track all inventory movements."""
    
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
        ('damage', 'Damage'),
        ('expired', 'Expired'),
    ]
    
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.transaction_type} - {self.inventory.product.name}: {self.quantity}"


class PurchaseOrder(models.Model):
    """Purchase order from suppliers."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('partial', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"PO-{self.order_number}"
    
    def calculate_totals(self):
        subtotal = sum(item.total_price for item in self.items.all())
        self.subtotal = subtotal
        self.total_amount = subtotal + self.tax_amount + self.shipping_cost
        self.save()
    
    def can_be_approved(self):
        return self.status == 'pending'
    
    def approve(self, user):
        if self.can_be_approved():
            self.status = 'approved'
            self.approved_by = user
            self.save()
            return True
        return False


class PurchaseOrderItem(models.Model):
    """Items in a purchase order."""
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=500, blank=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)
    
    def get_remaining_quantity(self):
        return self.quantity_ordered - self.quantity_received
    
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered


class Cart(models.Model):
    """Shopping cart model."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        if self.user:
            return f"Cart - {self.user.username}"
        return f"Cart - Session {self.session_key}"
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    def get_subtotal(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    def get_tax_amount(self):
        return sum(item.get_tax_amount() for item in self.items.all())
    
    def get_total(self):
        return self.get_subtotal() + self.get_tax_amount()
    
    def clear(self):
        self.items.all().delete()
    
    def merge_with_session_cart(self, session_cart):
        """Merge session cart with user cart after login."""
        for item in session_cart.items.all():
            existing = self.items.filter(product=item.product, variant=item.variant).first()
            if existing:
                existing.quantity += item.quantity
                existing.save()
            else:
                item.cart = self
                item.save()
        session_cart.delete()


class CartItem(models.Model):
    """Items in shopping cart."""
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        unique_together = ['cart', 'product', 'variant']
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_unit_price(self):
        if self.variant:
            return self.variant.get_price()
        return self.product.get_discounted_price()
    
    def get_total_price(self):
        return self.get_unit_price() * self.quantity
    
    def get_tax_amount(self):
        return self.get_total_price() * (self.product.tax_rate / 100)


class Coupon(models.Model):
    """Discount coupon model."""
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    maximum_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    applicable_categories = models.ManyToManyField(Category, blank=True)
    applicable_products = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is not active"
        if now < self.valid_from:
            return False, "Coupon is not yet valid"
        if now > self.valid_until:
            return False, "Coupon has expired"
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        return True, "Valid"
    
    def calculate_discount(self, order_amount):
        valid, message = self.is_valid()
        if not valid:
            return Decimal('0.00')
        
        if order_amount < self.minimum_order_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
            return discount
        elif self.discount_type == 'fixed':
            return min(self.discount_value, order_amount)
        return Decimal('0.00')


class Order(models.Model):
    """Sales order model."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
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
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('gift_card', 'Gift Card'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, blank=True)
    
    # Shipping address
    shipping_full_name = models.CharField(max_length=200)
    shipping_street_address1 = models.CharField(max_length=255)
    shipping_street_address2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20)
    
    # Billing address
    billing_full_name = models.CharField(max_length=200)
    billing_street_address1 = models.CharField(max_length=255)
    billing_street_address2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_postal_code = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def can_cancel(self):
        return self.status in ['pending', 'confirmed']
    
    def can_return(self):
        return self.status == 'delivered'
    
    def get_status_display_class(self):
        status_classes = {
            'pending': 'warning',
            'confirmed': 'info',
            'processing': 'primary',
            'shipped': 'info',
            'out_for_delivery': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
            'refunded': 'secondary',
            'returned': 'secondary',
        }
        return status_classes.get(self.status, 'secondary')


class OrderItem(models.Model):
    """Items in a sales order."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=500)
    product_sku = models.CharField(max_length=100)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.order.order_number} - {self.product_name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Review(models.Model):
    """Product review model."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"{self.product.name} - {self.user.username} ({self.rating}/5)"


class Wishlist(models.Model):
    """User wishlist."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.user.username}'s Wishlist"
    
    def add_product(self, product):
        self.products.add(product)
    
    def remove_product(self, product):
        self.products.remove(product)
    
    def has_product(self, product):
        return self.products.filter(id=product.id).exists()


class Notification(models.Model):
    """User notification model."""
    
    NOTIFICATION_TYPES = [
        ('order_update', 'Order Update'),
        ('price_drop', 'Price Drop'),
        ('back_in_stock', 'Back in Stock'),
        ('promotion', 'Promotion'),
        ('system', 'System'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()


class StockAlert(models.Model):
    """Low stock alerts."""
    
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('overstock', 'Overstock'),
    ]
    
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.alert_type} - {self.inventory.product.name}"
    
    def resolve(self, user):
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()


class ShippingMethod(models.Model):
    """Available shipping methods."""
    
    name = models.CharField(max_length=100)
    carrier = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_cost = models.DecimalField(max_digits=8, decimal_places=2)
    cost_per_kg = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    estimated_days_min = models.IntegerField(default=1)
    estimated_days_max = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.name} - {self.carrier}"
    
    def calculate_cost(self, weight=0, order_amount=Decimal('0.00')):
        if self.free_shipping_threshold and order_amount >= self.free_shipping_threshold:
            return Decimal('0.00')
        return self.base_cost + (self.cost_per_kg * Decimal(str(weight)))


class PaymentTransaction(models.Model):
    """Payment transaction records."""
    
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions')
    transaction_id = models.CharField(max_length=200, unique=True)
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    gateway_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.transaction_id} - {self.status}"


class ReturnRequest(models.Model):
    """Product return requests."""
    
    RETURN_REASONS = [
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_as_described', 'Not as Described'),
        ('changed_mind', 'Changed Mind'),
        ('damaged_shipping', 'Damaged During Shipping'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('received', 'Item Received'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=30, choices=RETURN_REASONS)
    description = models.TextField()
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_returns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"Return - {self.order.order_number} - {self.order_item.product_name}"


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password: str, 
                    first_name: str = '', last_name: str = '',
                    user_type: str = 'customer') -> User:
        """Create a new user with profile."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        UserProfile.objects.create(user=user, user_type=user_type)
        Cart.objects.create(user=user)
        Wishlist.objects.create(user=user)
        return user
    
    @staticmethod
    def get_user_by_email(email: str):
        """Get user by email."""
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def update_profile(user: User, **kwargs) -> UserProfile:
        """Update user profile."""
        profile = user.profile
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.save()
        return profile
    
    @staticmethod
    def add_address(user: User, **address_data) -> Address:
        """Add address to user."""
        if address_data.get('is_default'):
            user.addresses.update(is_default=False)
        return Address.objects.create(user=user, **address_data)
    
    @staticmethod
    def get_user_stats(user: User) -> dict:
        """Get user statistics."""
        orders = user.orders.all()
        return {
            'total_orders': orders.count(),
            'total_spent': sum(o.total_amount for o in orders.filter(payment_status='paid')),
            'pending_orders': orders.filter(status='pending').count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'wishlist_count': user.wishlist.products.count() if hasattr(user, 'wishlist') else 0,
            'review_count': user.reviews.count(),
        }


class ProductService:
    """Service class for product operations."""
    
    @staticmethod
    def create_product(name: str, sku: str, price: Decimal, 
                       category_id: int, **kwargs) -> Product:
        """Create a new product."""
        import re
        slug = re.sub(r'[^a-z0-9-]', '-', name.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return Product.objects.create(
            name=name,
            slug=slug,
            sku=sku,
            price=price,
            category_id=category_id,
            **kwargs
        )
    
    @staticmethod
    def search_products(query: str, category_id: int = None, 
                        min_price: Decimal = None, max_price: Decimal = None,
                        sort_by: str = 'relevance') -> list:
        """Search products with filters."""
        from django.db.models import Q
        
        queryset = Product.objects.filter(status='active')
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query) |
                Q(sku__icontains=query)
            )
        
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                category_ids = [category.id] + [c.id for c in category.get_descendants()]
                queryset = queryset.filter(category_id__in=category_ids)
            except Category.DoesNotExist:
                pass
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        
        sort_options = {
            'price_asc': 'price',
            'price_desc': '-price',
            'newest': '-created_at',
            'popular': '-view_count',
            'relevance': '-view_count',
        }
        
        queryset = queryset.order_by(sort_options.get(sort_by, '-view_count'))
        return list(queryset)
    
    @staticmethod
    def get_featured_products(limit: int = 10) -> list:
        """Get featured products."""
        return list(Product.objects.filter(
            status='active', is_featured=True
        ).order_by('-created_at')[:limit])
    
    @staticmethod
    def get_related_products(product: Product, limit: int = 5) -> list:
        """Get related products."""
        return list(Product.objects.filter(
            category=product.category,
            status='active'
        ).exclude(id=product.id)[:limit])
    
    @staticmethod
    def increment_view_count(product: Product):
        """Increment product view count."""
        Product.objects.filter(id=product.id).update(
            view_count=models.F('view_count') + 1
        )
    
    @staticmethod
    def update_product_status_based_on_stock(product: Product):
        """Update product status based on inventory."""
        if product.get_total_stock() == 0:
            if product.status == 'active':
                product.status = 'out_of_stock'
                product.save()
        elif product.status == 'out_of_stock':
            product.status = 'active'
            product.save()


class CartService:
    """Service class for shopping cart operations."""
    
    @staticmethod
    def get_or_create_cart(user=None, session_key=None) -> Cart:
        """Get or create cart for user or session."""
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=user)
            return cart
        elif session_key:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
            return cart
        return None
    
    @staticmethod
    def add_item(cart: Cart, product: Product, quantity: int = 1, 
                 variant: ProductVariant = None) -> CartItem:
        """Add item to cart."""
        if not product.is_in_stock():
            raise ValueError("Product is out of stock")
        
        available_stock = product.get_total_stock()
        
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': 0}
        )
        
        new_quantity = item.quantity + quantity
        if new_quantity > available_stock:
            raise ValueError(f"Only {available_stock} items available in stock")
        
        item.quantity = new_quantity
        item.save()
        return item
    
    @staticmethod
    def update_item_quantity(cart: Cart, item_id: int, quantity: int) -> CartItem:
        """Update cart item quantity."""
        try:
            item = cart.items.get(id=item_id)
            if quantity <= 0:
                item.delete()
                return None
            
            available_stock = item.product.get_total_stock()
            if quantity > available_stock:
                raise ValueError(f"Only {available_stock} items available")
            
            item.quantity = quantity
            item.save()
            return item
        except CartItem.DoesNotExist:
            raise ValueError("Cart item not found")
    
    @staticmethod
    def remove_item(cart: Cart, item_id: int):
        """Remove item from cart."""
        cart.items.filter(id=item_id).delete()
    
    @staticmethod
    def apply_coupon(cart: Cart, coupon_code: str) -> dict:
        """Apply coupon to cart."""
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            valid, message = coupon.is_valid()
            if not valid:
                return {'success': False, 'message': message}
            
            subtotal = cart.get_subtotal()
            if subtotal < coupon.minimum_order_amount:
                return {
                    'success': False, 
                    'message': f"Minimum order amount is ${coupon.minimum_order_amount}"
                }
            
            discount = coupon.calculate_discount(subtotal)
            return {
                'success': True,
                'coupon': coupon,
                'discount': discount,
                'message': f"Coupon applied! You save ${discount}"
            }
        except Coupon.DoesNotExist:
            return {'success': False, 'message': "Invalid coupon code"}
    
    @staticmethod
    def get_cart_summary(cart: Cart, coupon: Coupon = None, 
                         shipping_method: ShippingMethod = None) -> dict:
        """Get complete cart summary."""
        subtotal = cart.get_subtotal()
        tax = cart.get_tax_amount()
        shipping = Decimal('0.00')
        discount = Decimal('0.00')
        
        if shipping_method:
            total_weight = sum(
                (item.product.weight or 0) * item.quantity 
                for item in cart.items.all()
            )
            shipping = shipping_method.calculate_cost(total_weight, subtotal)
        
        if coupon:
            discount = coupon.calculate_discount(subtotal)
        
        total = subtotal + tax + shipping - discount
        
        return {
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'discount': discount,
            'total': total,
            'item_count': cart.get_total_items(),
        }


class OrderService:
    """Service class for order management."""
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number."""
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"{timestamp}{random_suffix}"
    
    @staticmethod
    def create_order_from_cart(cart: Cart, user: User, 
                                shipping_address: Address,
                                billing_address: Address,
                                payment_method: str,
                                shipping_method: ShippingMethod = None,
                                coupon: Coupon = None) -> Order:
        """Create order from cart."""
        if not cart.items.exists():
            raise ValueError("Cart is empty")
        
        summary = CartService.get_cart_summary(cart, coupon, shipping_method)
        
        order = Order.objects.create(
            order_number=OrderService.generate_order_number(),
            user=user,
            payment_method=payment_method,
            
            shipping_full_name=shipping_address.full_name,
            shipping_street_address1=shipping_address.street_address1,
            shipping_street_address2=shipping_address.street_address2,
            shipping_city=shipping_address.city,
            shipping_state=shipping_address.state,
            shipping_postal_code=shipping_address.postal_code,
            shipping_country=shipping_address.country,
            shipping_phone=shipping_address.phone,
            
            billing_full_name=billing_address.full_name,
            billing_street_address1=billing_address.street_address1,
            billing_street_address2=billing_address.street_address2,
            billing_city=billing_address.city,
            billing_state=billing_address.state,
            billing_postal_code=billing_address.postal_code,
            billing_country=billing_address.country,
            
            subtotal=summary['subtotal'],
            tax_amount=summary['tax'],
            shipping_cost=summary['shipping'],
            discount_amount=summary['discount'],
            total_amount=summary['total'],
            coupon=coupon,
        )
        
        # Create order items and update inventory
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                quantity=cart_item.quantity,
                unit_price=cart_item.get_unit_price(),
                total_price=cart_item.get_total_price(),
                tax_amount=cart_item.get_tax_amount(),
            )
            
            # Update inventory
            InventoryService.deduct_stock(
                cart_item.product, 
                cart_item.quantity,
                cart_item.variant,
                reference=order.order_number
            )
        
        # Update coupon usage
        if coupon:
            coupon.used_count += 1
            coupon.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes='Order created',
            changed_by=user
        )
        
        # Clear cart
        cart.clear()
        
        # Send notification
        NotificationService.send_order_notification(user, order, 'order_placed')
        
        return order
    
    @staticmethod
    def update_order_status(order: Order, new_status: str, 
                             user: User, notes: str = '') -> Order:
        """Update order status."""
        old_status = order.status
        order.status = new_status
        
        if new_status == 'delivered':
            order.actual_delivery = timezone.now()
        
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            notes=notes or f"Status changed from {old_status} to {new_status}",
            changed_by=user
        )
        
        NotificationService.send_order_notification(order.user, order, 'status_update')
        
        return order
    
    @staticmethod
    def cancel_order(order: Order, user: User, reason: str = '') -> Order:
        """Cancel an order."""
        if not order.can_cancel():
            raise ValueError("Order cannot be cancelled at this stage")
        
        # Restore inventory
        for item in order.items.all():
            InventoryService.restore_stock(
                item.product,
                item.quantity,
                item.variant,
                reference=order.order_number
            )
        
        return OrderService.update_order_status(
            order, 'cancelled', user, 
            reason or 'Order cancelled by user'
        )
    
    @staticmethod
    def get_order_analytics() -> dict:
        """Get order analytics."""
        from django.db.models import Sum, Count, Avg
        
        orders = Order.objects.all()
        today = timezone.now().date()
        
        return {
            'total_orders': orders.count(),
            'total_revenue': orders.filter(payment_status='paid').aggregate(
                total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'today_orders': orders.filter(created_at__date=today).count(),
            'today_revenue': orders.filter(
                created_at__date=today, payment_status='paid'
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'pending_orders': orders.filter(status='pending').count(),
            'processing_orders': orders.filter(status='processing').count(),
            'average_order_value': orders.filter(payment_status='paid').aggregate(
                avg=Avg('total_amount'))['avg'] or Decimal('0.00'),
        }


class InventoryService:
    """Service class for inventory management."""
    
    @staticmethod
    def add_stock(product: Product, quantity: int, warehouse: Warehouse,
                  variant: ProductVariant = None, reference: str = '',
                  performed_by: User = None) -> Inventory:
        """Add stock to inventory."""
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            variant=variant,
            defaults={'quantity': 0}
        )
        
        quantity_before = inventory.quantity
        inventory.quantity += quantity
        inventory.save()
        
        InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type='purchase',
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=inventory.quantity,
            reference_number=reference,
            performed_by=performed_by
        )
        
        # Check and resolve stock alerts
        InventoryService.check_stock_alerts(inventory)
        
        # Update product status
        ProductService.update_product_status_based_on_stock(product)
        
        return inventory
    
    @staticmethod
    def deduct_stock(product: Product, quantity: int,
                     variant: ProductVariant = None, reference: str = '',
                     performed_by: User = None) -> bool:
        """Deduct stock from inventory (uses first available warehouse)."""
        inventories = Inventory.objects.filter(
            product=product,
            variant=variant
        ).order_by('-quantity')
        
        remaining = quantity
        for inventory in inventories:
            if remaining <= 0:
                break
            
            available = inventory.get_available_quantity()
            deduct = min(available, remaining)
            
            if deduct > 0:
                quantity_before = inventory.quantity
                inventory.quantity -= deduct
                inventory.save()
                remaining -= deduct
                
                InventoryTransaction.objects.create(
                    inventory=inventory,
                    transaction_type='sale',
                    quantity=-deduct,
                    quantity_before=quantity_before,
                    quantity_after=inventory.quantity,
                    reference_number=reference,
                    performed_by=performed_by
                )
                
                InventoryService.check_stock_alerts(inventory)
        
        ProductService.update_product_status_based_on_stock(product)
        return remaining == 0
    
    @staticmethod
    def restore_stock(product: Product, quantity: int,
                      variant: ProductVariant = None, reference: str = '',
                      performed_by: User = None):
        """Restore stock (for cancellations/returns)."""
        inventory = Inventory.objects.filter(
            product=product, variant=variant
        ).first()
        
        if inventory:
            quantity_before = inventory.quantity
            inventory.quantity += quantity
            inventory.save()
            
            InventoryTransaction.objects.create(
                inventory=inventory,
                transaction_type='return',
                quantity=quantity,
                quantity_before=quantity_before,
                quantity_after=inventory.quantity,
                reference_number=reference,
                performed_by=performed_by
            )
            
            ProductService.update_product_status_based_on_stock(product)
    
    @staticmethod
    def transfer_stock(from_warehouse: Warehouse, to_warehouse: Warehouse,
                       product: Product, quantity: int,
                       variant: ProductVariant = None,
                       performed_by: User = None) -> bool:
        """Transfer stock between warehouses."""
        try:
            from_inventory = Inventory.objects.get(
                product=product, warehouse=from_warehouse, variant=variant
            )
        except Inventory.DoesNotExist:
            raise ValueError("Source inventory not found")
        
        if from_inventory.get_available_quantity() < quantity:
            raise ValueError("Insufficient stock in source warehouse")
        
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
            notes=f"Transfer to {to_warehouse.name}",
            performed_by=performed_by
        )
        
        # Add to destination
        to_inventory, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=to_warehouse,
            variant=variant,
            defaults={'quantity': 0}
        )
        
        quantity_before = to_inventory.quantity
        to_inventory.quantity += quantity
        to_inventory.save()
        
        InventoryTransaction.objects.create(
            inventory=to_inventory,
            transaction_type='transfer',
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=to_inventory.quantity,
            notes=f"Transfer from {from_warehouse.name}",
            performed_by=performed_by
        )
        
        return True
    
    @staticmethod
    def adjust_stock(inventory: Inventory, new_quantity: int,
                     reason: str = '', performed_by: User = None):
        """Adjust stock to a specific quantity."""
        quantity_before = inventory.quantity
        difference = new_quantity - quantity_before
        
        inventory.quantity = new_quantity
        inventory.last_counted = timezone.now()
        inventory.save()
        
        InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type='adjustment',
            quantity=difference,
            quantity_before=quantity_before,
            quantity_after=new_quantity,
            notes=reason,
            performed_by=performed_by
        )
        
        InventoryService.check_stock_alerts(inventory)
        ProductService.update_product_status_based_on_stock(inventory.product)
    
    @staticmethod
    def check_stock_alerts(inventory: Inventory):
        """Check and create stock alerts if needed."""
        if inventory.quantity == 0:
            StockAlert.objects.get_or_create(
                inventory=inventory,
                alert_type='out_of_stock',
                is_resolved=False,
                defaults={'message': f"{inventory.product.name} is out of stock at {inventory.warehouse.name}"}
            )
        elif inventory.needs_reorder():
            StockAlert.objects.get_or_create(
                inventory=inventory,
                alert_type='low_stock',
                is_resolved=False,
                defaults={'message': f"{inventory.product.name} is low on stock at {inventory.warehouse.name}"}
            )
        elif inventory.is_overstocked():
            StockAlert.objects.get_or_create(
                inventory=inventory,
                alert_type='overstock',
                is_resolved=False,
                defaults={'message': f"{inventory.product.name} is overstocked at {inventory.warehouse.name}"}
            )
    
    @staticmethod
    def get_inventory_report() -> dict:
        """Generate inventory report."""
        from django.db.models import Sum, Count
        
        inventories = Inventory.objects.all()
        
        return {
            'total_products': Product.objects.filter(status='active').count(),
            'total_stock_value': sum(
                inv.quantity * inv.product.cost_price 
                for inv in inventories
            ),
            'low_stock_items': inventories.filter(
                quantity__lte=models.F('reorder_point')
            ).count(),
            'out_of_stock_items': inventories.filter(quantity=0).count(),
            'total_warehouses': Warehouse.objects.filter(is_active=True).count(),
            'pending_alerts': StockAlert.objects.filter(is_resolved=False).count(),
        }
    
    @staticmethod
    def get_products_needing_reorder() -> list:
        """Get products that need reordering."""
        return list(Inventory.objects.filter(
            quantity__lte=models.F('reorder_point')
        ).select_related('product', 'warehouse'))


class PurchaseOrderService:
    """Service class for purchase order management."""
    
    @staticmethod
    def create_purchase_order(supplier: Supplier, warehouse: Warehouse,
                               items: list, created_by: User,
                               expected_delivery=None, notes: str = '') -> PurchaseOrder:
        """Create a new purchase order."""
        import random
        import string
        
        order_number = f"PO-{timezone.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=6))}"
        
        po = PurchaseOrder.objects.create(
            order_number=order_number,
            supplier=supplier,
            warehouse=warehouse,
            created_by=created_by,
            expected_delivery=expected_delivery,
            notes=notes,
            status='draft'
        )
        
        for item_data in items:
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=item_data['product'],
                variant=item_data.get('variant'),
                quantity_ordered=item_data['quantity'],
                unit_price=item_data['unit_price'],
            )
        
        po.calculate_totals()
        return po
    
    @staticmethod
    def receive_items(purchase_order: PurchaseOrder, 
                      received_items: list, received_by: User) -> PurchaseOrder:
        """Process received items from purchase order."""
        all_received = True
        
        for received in received_items:
            try:
                po_item = purchase_order.items.get(id=received['item_id'])
                quantity = received['quantity']
                
                if quantity > po_item.get_remaining_quantity():
                    raise ValueError(f"Cannot receive more than ordered for {po_item.product.name}")
                
                po_item.quantity_received += quantity
                po_item.save()
                
                # Add to inventory
                InventoryService.add_stock(
                    po_item.product,
                    quantity,
                    purchase_order.warehouse,
                    po_item.variant,
                    reference=purchase_order.order_number,
                    performed_by=received_by
                )
                
                if not po_item.is_fully_received():
                    all_received = False
                    
            except PurchaseOrderItem.DoesNotExist:
                raise ValueError(f"Purchase order item not found")
        
        # Update PO status
        if all_received:
            purchase_order.status = 'received'
            purchase_order.actual_delivery = timezone.now().date()
        else:
            purchase_order.status = 'partial'
        
        purchase_order.save()
        return purchase_order
    
    @staticmethod
    def get_purchase_order_analytics() -> dict:
        """Get purchase order analytics."""
        from django.db.models import Sum
        
        pos = PurchaseOrder.objects.all()
        
        return {
            'total_orders': pos.count(),
            'pending_orders': pos.filter(status='pending').count(),
            'total_value': pos.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'received_this_month': pos.filter(
                status='received',
                actual_delivery__month=timezone.now().month
            ).count(),
        }


class NotificationService:
    """Service class for notifications."""
    
    @staticmethod
    def send_order_notification(user: User, order: Order, event_type: str):
        """Send order-related notification."""
        messages = {
            'order_placed': f"Your order #{order.order_number} has been placed successfully!",
            'status_update': f"Your order #{order.order_number} status has been updated to {order.get_status_display()}.",
            'shipped': f"Your order #{order.order_number} has been shipped! Tracking: {order.tracking_number}",
            'delivered': f"Your order #{order.order_number} has been delivered!",
        }
        
        message = messages.get(event_type, f"Update on order #{order.order_number}")
        
        Notification.objects.create(
            user=user,
            notification_type='order_update',
            title=f"Order Update - #{order.order_number}",
            message=message,
            link=f"/orders/{order.id}/"
        )
    
    @staticmethod
    def send_stock_alert_notification(inventory: Inventory, admin_users: list):
        """Send stock alert to admin users."""
        for user in admin_users:
            Notification.objects.create(
                user=user,
                notification_type='system',
                title=f"Stock Alert - {inventory.product.name}",
                message=f"Stock level for {inventory.product.name} at {inventory.warehouse.name} is {inventory.quantity} units.",
                link=f"/admin/inventory/{inventory.id}/"
            )
    
    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get unread notification count."""
        return user.notifications.filter(is_read=False).count()
    
    @staticmethod
    def mark_all_as_read(user: User):
        """Mark all notifications as read."""
        user.notifications.filter(is_read=False).update(is_read=True)


class ReviewService:
    """Service class for product reviews."""
    
    @staticmethod
    def create_review(user: User, product: Product, rating: int,
                      title: str, body: str, order_item: OrderItem = None) -> Review:
        """Create a product review."""
        if Review.objects.filter(user=user, product=product).exists():
            raise ValueError("You have already reviewed this product")
        
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        is_verified = False
        if order_item:
            is_verified = order_item.order.user == user and \
                         order_item.order.status == 'delivered'
        
        return Review.objects.create(
            user=user,
            product=product,
            order_item=order_item,
            rating=rating,
            title=title,
            body=body,
            is_verified_purchase=is_verified
        )
    
    @staticmethod
    def get_product_rating_breakdown(product: Product) -> dict:
        """Get rating breakdown for a product."""
        reviews = product.reviews.filter(is_approved=True)
        total = reviews.count()
        
        if total == 0:
            return {str(i): 0 for i in range(1, 6)}
        
        breakdown = {}
        for i in range(1, 6):
            count = reviews.filter(rating=i).count()
            breakdown[str(i)] = {
                'count': count,
                'percentage': (count / total) * 100
            }
        
        return breakdown


class WarehouseService:
    """Service class for warehouse management."""
    
    @staticmethod
    def create_warehouse(name: str, code: str, address: str,
                          city: str, state: str, country: str,
                          postal_code: str, phone: str, email: str,
                          manager: User = None, capacity: int = 0) -> Warehouse:
        """Create a new warehouse."""
        return Warehouse.objects.create(
            name=name,
            code=code,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            phone=phone,
            email=email,
            manager=manager,
            capacity=capacity
        )
    
    @staticmethod
    def get_warehouse_inventory_summary(warehouse: Warehouse) -> dict:
        """Get inventory summary for a warehouse."""
        inventories = warehouse.inventories.all()
        
        return {
            'total_products': inventories.count(),
            'total_items': sum(inv.quantity for inv in inventories),
            'total_value': sum(inv.quantity * inv.product.cost_price for inv in inventories),
            'low_stock_items': inventories.filter(
                quantity__lte=models.F('reorder_point')
            ).count(),
            'out_of_stock': inventories.filter(quantity=0).count(),
        }
    
    @staticmethod
    def get_all_warehouses_summary() -> list:
        """Get summary for all warehouses."""
        warehouses = Warehouse.objects.filter(is_active=True)
        summaries = []
        
        for warehouse in warehouses:
            summary = WarehouseService.get_warehouse_inventory_summary(warehouse)
            summary['warehouse'] = warehouse
            summaries.append(summary)
        
        return summaries


class SupplierService:
    """Service class for supplier management."""
    
    @staticmethod
    def create_supplier(name: str, contact_person: str, email: str,
                         phone: str, address: str, city: str,
                         state: str, country: str, postal_code: str,
                         **kwargs) -> Supplier:
        """Create a new supplier."""
        return Supplier.objects.create(
            name=name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            **kwargs
        )
    
    @staticmethod
    def get_supplier_performance(supplier: Supplier) -> dict:
        """Get supplier performance metrics."""
        pos = supplier.purchase_orders.all()
        
        on_time_deliveries = pos.filter(
            status='received',
            actual_delivery__lte=models.F('expected_delivery')
        ).count()
        
        total_received = pos.filter(status='received').count()
        on_time_rate = (on_time_deliveries / total_received * 100) if total_received > 0 else 0
        
        return {
            'total_orders': pos.count(),
            'completed_orders': total_received,
            'pending_orders': pos.filter(status__in=['pending', 'approved', 'ordered']).count(),
            'on_time_delivery_rate': on_time_rate,
            'total_products': supplier.products.count(),
        }


# ============================================================
# ADMIN INTERFACE
# ============================================================

from django.contrib import admin

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'phone', 'is_verified', 'created_at']
    list_filter = ['user_type', 'is_verified']
    search_fields = ['user__username', 'user__email', 'phone']


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'status', 'category', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'category']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['status', 'is_featured']


class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'reserved_quantity', 'reorder_point']
    list_filter = ['warehouse']
    search_fields = ['product__name', 'warehouse__name']


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'payment_status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_status']
    search_fields = ['order_number', 'user__username']
    readonly_fields = ['order_number', 'created_at']


class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier', 'warehouse', 'status', 'total_amount', 'order_date']
    list_filter = ['status', 'supplier', 'warehouse']
    search_fields = ['order_number', 'supplier__name']


class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'is_active', 'rating']
    list_filter = ['is_active', 'country']
    search_fields = ['name', 'email', 'contact_person']


class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'state', 'manager', 'is_active']
    list_filter = ['is_active', 'country']
    search_fields = ['name', 'code', 'city']


class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'is_approved']
    search_fields = ['product__name', 'user__username']


class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'used_count', 'is_active', 'valid_until']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']


class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['inventory', 'alert_type', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'is_resolved']


# Register models with admin
try:
    admin.site.register(UserProfile, UserProfileAdmin)
    admin.site.register(Address)
    admin.site.register(Category, CategoryAdmin)
    admin.site.register(Brand)
    admin.site.register(Supplier, SupplierAdmin)
    admin.site.register(Warehouse, WarehouseAdmin)
    admin.site.register(Product, ProductAdmin)
    admin.site.register(ProductVariant)
    admin.site.register(ProductImage)
    admin.site.register(Inventory, InventoryAdmin)
    admin.site.register(InventoryTransaction)
    admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
    admin.site.register(PurchaseOrderItem)
    admin.site.register(Cart)
    admin.site.register(CartItem)
    admin.site.register(Coupon, CouponAdmin)
    admin.site.register(Order, OrderAdmin)
    admin.site.register(OrderItem)
    admin.site.register(OrderStatusHistory)
    admin.site.register(Review, ReviewAdmin)
    admin.site.register(Wishlist)
    admin.site.register(Notification)
    admin.site.register(StockAlert, StockAlertAdmin)
    admin.site.register(ShippingMethod)
    admin.site.register(PaymentTransaction)
    admin.site.register(ReturnRequest)
except Exception:
    pass


# ============================================================
# URL CONFIGURATION
# ============================================================

from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView


def home_view(request):
    """Home page view."""
    featured_products = ProductService.get_featured_products(8)
    categories = Category.objects.filter(parent=None, is_active=True)
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
    }
    
    html = generate_home_html(context)
    return HttpResponse(html)


def product_list_view(request):
    """Product listing view."""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'relevance')
    
    products = ProductService.search_products(
        query=query,
        category_id=int(category_id) if category_id else None,
        min_price=Decimal(min_price) if min_price else None,
        max_price=Decimal(max_price) if max_price else None,
        sort_by=sort_by
    )
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'total_results': len(products),
    }
    
    html = generate_product_list_html(context)
    return HttpResponse(html)


def product_detail_view(request, slug):
    """Product detail view."""
    try:
        product = Product.objects.get(slug=slug, status='active')
        ProductService.increment_view_count(product)
        
        related_products = ProductService.get_related_products(product)
        reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
        rating_breakdown = ReviewService.get_product_rating_breakdown(product)
        
        context = {
            'product': product,
            'related_products': related_products,
            'reviews': reviews,
            'rating_breakdown': rating_breakdown,
            'average_rating': product.get_average_rating(),
            'review_count': product.get_review_count(),
            'in_stock': product.is_in_stock(),
            'total_stock': product.get_total_stock(),
        }
        
        html = generate_product_detail_html(context)
        return HttpResponse(html)
    except Product.DoesNotExist:
        return HttpResponse("<h1>Product not found</h1>", status=404)


def cart_view(request):
    """Shopping cart view."""
    if request.user.is_authenticated:
        cart = CartService.get_or_create_cart(user=request.user)
    else:
        session_key = request.session.session_key or request.session.create()
        cart = CartService.get_or_create_cart(session_key=session_key)
    
    summary = CartService.get_cart_summary(cart)
    
    context = {
        'cart': cart,
        'items': cart.items.all() if cart else [],
        'summary': summary,
    }
    
    html = generate_cart_html(context)
    return HttpResponse(html)


def add_to_cart_view(request, product_id):
    """Add product to cart."""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            quantity = int(request.POST.get('quantity', 1))
            variant_id = request.POST.get('variant_id')
            variant = None
            
            if variant_id:
                variant = ProductVariant.objects.get(id=variant_id)
            
            if request.user.is_authenticated:
                cart = CartService.get_or_create_cart(user=request.user)
            else:
                session_key = request.session.session_key
                if not session_key:
                    request.session.create()
                    session_key = request.session.session_key
                cart = CartService.get_or_create_cart(session_key=session_key)
            
            CartService.add_item(cart, product, quantity, variant)
            
            return JsonResponse({
                'success': True,
                'message': f"{product.name} added to cart",
                'cart_count': cart.get_total_items()
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def remove_from_cart_view(request, item_id):
    """Remove item from cart."""
    if request.method == 'POST':
        if request.user.is_authenticated:
            cart = CartService.get_or_create_cart(user=request.user)
        else:
            session_key = request.session.session_key
            cart = CartService.get_or_create_cart(session_key=session_key)
        
        if cart:
            CartService.remove_item(cart, item_id)
            return JsonResponse({'success': True, 'message': 'Item removed from cart'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def update_cart_view(request, item_id):
    """Update cart item quantity."""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if request.user.is_authenticated:
            cart = CartService.get_or_create_cart(user=request.user)
        else:
            session_key = request.session.session_key
            cart = CartService.get_or_create_cart(session_key=session_key)
        
        if cart:
            try:
                CartService.update_item_quantity(cart, item_id, quantity)
                return JsonResponse({
                    'success': True,
                    'cart_total': str(cart.get_total()),
                    'cart_count': cart.get_total_items()
                })
            except ValueError as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def checkout_view(request):
    """Checkout view."""
    if not request.user.is_authenticated:
        return HttpResponse('<script>window.location="/login/?next=/checkout/"</script>')
    
    cart = CartService.get_or_create_cart(user=request.user)
    
    if not cart or not cart.items.exists():
        return HttpResponse('<script>window.location="/cart/"</script>')
    
    addresses = request.user.addresses.all()
    shipping_methods = ShippingMethod.objects.filter(is_active=True)
    summary = CartService.get_cart_summary(cart)
    
    context = {
        'cart': cart,
        'addresses': addresses,
        'shipping_methods': shipping_methods,
        'summary': summary,
    }
    
    html = generate_checkout_html(context)
    return HttpResponse(html)


def place_order_view(request):
    """Place order view."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    
    if request.method == 'POST':
        try:
            cart = CartService.get_or_create_cart(user=request.user)
            
            if not cart or not cart.items.exists():
                return JsonResponse({'success': False, 'message': 'Cart is empty'})
            
            shipping_address_id = request.POST.get('shipping_address_id')
            billing_address_id = request.POST.get('billing_address_id', shipping_address_id)
            payment_method = request.POST.get('payment_method', 'credit_card')
            shipping_method_id = request.POST.get('shipping_method_id')
            coupon_code = request.POST.get('coupon_code', '')
            
            shipping_address = Address.objects.get(id=shipping_address_id, user=request.user)
            billing_address = Address.objects.get(id=billing_address_id, user=request.user)
            
            shipping_method = None
            if shipping_method_id:
                shipping_method = ShippingMethod.objects.get(id=shipping_method_id)
            
            coupon = None
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                except Coupon.DoesNotExist:
                    pass
            
            order = OrderService.create_order_from_cart(
                cart=cart,
                user=request.user,
                shipping_address=shipping_address,
                billing_address=billing_address,
                payment_method=payment_method,
                shipping_method=shipping_method,
                coupon=coupon
            )
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'redirect_url': f'/orders/{order.id}/'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def order_list_view(request):
    """User order list view."""
    if not request.user.is_authenticated:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    orders = request.user.orders.all().order_by('-created_at')
    
    context = {'orders': orders}
    html = generate_order_list_html(context)
    return HttpResponse(html)


def order_detail_view(request, order_id):
    """Order detail view."""
    if not request.user.is_authenticated:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        context = {
            'order': order,
            'items': order.items.all(),
            'status_history': order.status_history.all(),
        }
        html = generate_order_detail_html(context)
        return HttpResponse(html)
    except Order.DoesNotExist:
        return HttpResponse("<h1>Order not found</h1>", status=404)


def cancel_order_view(request, order_id):
    """Cancel order view."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            reason = request.POST.get('reason', 'Cancelled by customer')
            OrderService.cancel_order(order, request.user, reason)
            return JsonResponse({'success': True, 'message': 'Order cancelled successfully'})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def signup_view(request):
    """User signup view."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if User.objects.filter(username=username).exists():
            return HttpResponse(generate_signup_html({'error': 'Username already exists'}))
        
        if User.objects.filter(email=email).exists():
            return HttpResponse(generate_signup_html({'error': 'Email already registered'}))
        
        try:
            user = UserService.create_user(username, email, password, first_name, last_name)
            from django.contrib.auth import login
            login(request, user)
            return HttpResponse('<script>window.location="/"</script>')
        except Exception as e:
            return HttpResponse(generate_signup_html({'error': str(e)}))
    
    return HttpResponse(generate_signup_html({}))


def profile_view(request):
    """User profile view."""
    if not request.user.is_authenticated:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    stats = UserService.get_user_stats(request.user)
    addresses = request.user.addresses.all()
    
    context = {
        'user': request.user,
        'stats': stats,
        'addresses': addresses,
    }
    
    html = generate_profile_html(context)
    return HttpResponse(html)


def wishlist_view(request):
    """Wishlist view."""
    if not request.user.is_authenticated:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    context = {'wishlist': wishlist, 'products': wishlist.products.all()}
    html = generate_wishlist_html(context)
    return HttpResponse(html)


def toggle_wishlist_view(request, product_id):
    """Toggle product in wishlist."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    
    try:
        product = Product.objects.get(id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        if wishlist.has_product(product):
            wishlist.remove_product(product)
            in_wishlist = False
            message = "Removed from wishlist"
        else:
            wishlist.add_product(product)
            in_wishlist = True
            message = "Added to wishlist"
        
        return JsonResponse({'success': True, 'in_wishlist': in_wishlist, 'message': message})
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)


def add_review_view(request, product_id):
    """Add product review."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            rating = int(request.POST.get('rating', 5))
            title = request.POST.get('title', '')
            body = request.POST.get('body', '')
            
            review = ReviewService.create_review(
                request.user, product, rating, title, body
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Review submitted successfully',
                'review_id': review.id
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def notifications_view(request):
    """User notifications view."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)
    
    notifications = request.user.notifications.all()[:20]
    unread_count = NotificationService.get_unread_count(request.user)
    
    return JsonResponse({
        'notifications': [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'link': n.link,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications
        ],
        'unread_count': unread_count
    })


# Admin views
def admin_dashboard_view(request):
    """Admin dashboard view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    order_analytics = OrderService.get_order_analytics()
    inventory_report = InventoryService.get_inventory_report()
    po_analytics = PurchaseOrderService.get_purchase_order_analytics()
    
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    low_stock_items = InventoryService.get_products_needing_reorder()[:10]
    
    context = {
        'order_analytics': order_analytics,
        'inventory_report': inventory_report,
        'po_analytics': po_analytics,
        'recent_orders': recent_orders,
        'low_stock_items': low_stock_items,
    }
    
    html = generate_admin_dashboard_html(context)
    return HttpResponse(html)


def admin_inventory_view(request):
    """Admin inventory management view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    inventories = Inventory.objects.all().select_related('product', 'warehouse')
    warehouses = Warehouse.objects.filter(is_active=True)
    alerts = StockAlert.objects.filter(is_resolved=False)
    
    context = {
        'inventories': inventories,
        'warehouses': warehouses,
        'alerts': alerts,
        'report': InventoryService.get_inventory_report(),
    }
    
    html = generate_admin_inventory_html(context)
    return HttpResponse(html)


def admin_orders_view(request):
    """Admin orders management view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    status_filter = request.GET.get('status', '')
    orders = Order.objects.all().order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'analytics': OrderService.get_order_analytics(),
    }
    
    html = generate_admin_orders_html(context)
    return HttpResponse(html)


def admin_purchase_orders_view(request):
    """Admin purchase orders view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    purchase_orders = PurchaseOrder.objects.all().order_by('-order_date')
    suppliers = Supplier.objects.filter(is_active=True)
    warehouses = Warehouse.objects.filter(is_active=True)
    
    context = {
        'purchase_orders': purchase_orders,
        'suppliers': suppliers,
        'warehouses': warehouses,
        'analytics': PurchaseOrderService.get_purchase_order_analytics(),
    }
    
    html = generate_admin_purchase_orders_html(context)
    return HttpResponse(html)


def admin_suppliers_view(request):
    """Admin suppliers management view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    suppliers = Supplier.objects.all()
    
    context = {'suppliers': suppliers}
    html = generate_admin_suppliers_html(context)
    return HttpResponse(html)


def admin_warehouses_view(request):
    """Admin warehouses management view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    warehouse_summaries = WarehouseService.get_all_warehouses_summary()
    
    context = {'warehouse_summaries': warehouse_summaries}
    html = generate_admin_warehouses_html(context)
    return HttpResponse(html)


def admin_users_view(request):
    """Admin user management view."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse('<script>window.location="/login/"</script>')
    
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    
    context = {'users': users}
    html = generate_admin_users_html(context)
    return HttpResponse(html)


def update_order_status_view(request, order_id):
    """Update order status (admin)."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
    
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            new_status = request.POST.get('status')
            notes = request.POST.get('notes', '')
            
            OrderService.update_order_status(order, new_status, request.user, notes)
            
            return JsonResponse({'success': True, 'message': f'Order status updated to {new_status}'})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def api_products_view(request):
    """API endpoint for products."""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    limit = int(request.GET.get('limit', 20))
    
    products = ProductService.search_products(
        query=query,
        category_id=int(category_id) if category_id else None
    )[:limit]
    
    return JsonResponse({
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'slug': p.slug,
                'price': str(p.price),
                'discounted_price': str(p.get_discounted_price()),
                'category': p.category.name if p.category else None,
                'in_stock': p.is_in_stock(),
                'rating': p.get_average_rating(),
                'review_count': p.get_review_count(),
            }
            for p in products
        ],
        'total': len(products)
    })


def api_inventory_view(request):
    """API endpoint for inventory."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
    
    report = InventoryService.get_inventory_report()
    return JsonResponse(report, default=str)


# ============================================================
# HTML GENERATORS
# ============================================================

def get_base_html(title: str, content: str, user=None) -> str:
    """Generate base HTML template."""
    nav_links = ""
    if user and user.is_authenticated:
        nav_links = f"""
        <a href="/profile/" style="color:white;text-decoration:none;margin:0 10px;">Hello, {user.first_name or user.username}</a>
        <a href="/orders/" style="color:white;text-decoration:none;margin:0 10px;">Orders</a>
        <a href="/wishlist/" style="color:white;text-decoration:none;margin:0 10px;">Wishlist</a>
        <a href="/cart/" style="color:white;text-decoration:none;margin:0 10px;">Cart</a>
        <a href="/logout/" style="color:white;text-decoration:none;margin:0 10px;">Sign Out</a>
        """
        if user.is_staff:
            nav_links += '<a href="/admin-dashboard/" style="color:#ff9900;text-decoration:none;margin:0 10px;">Admin</a>'
    else:
        nav_links = """
        <a href="/login/" style="color:white;text-decoration:none;margin:0 10px;">Sign In</a>
        <a href="/signup/" style="color:white;text-decoration:none;margin:0 10px;">Sign Up</a>
        <a href="/cart/" style="color:white;text-decoration:none;margin:0 10px;">Cart</a>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - Amazon Clone</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: Arial, sans-serif; background: #f3f3f3; }}
            .navbar {{ background: #131921; padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; }}
            .navbar-brand {{ color: white; font-size: 24px; font-weight: bold; text-decoration: none; }}
            .navbar-brand span {{ color: #ff9900; }}
            .search-bar {{ flex: 1; margin: 0 20px; display: flex; }}
            .search-bar input {{ flex: 1; padding: 8px; border: none; border-radius: 4px 0 0 4px; }}
            .search-bar button {{ padding: 8px 15px; background: #ff9900; border: none; border-radius: 0 4px 4px 0; cursor: pointer; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
            .card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }}
            .btn-primary {{ background: #ff9900; color: white; }}
            .btn-secondary {{ background: #232f3e; color: white; }}
            .btn-danger {{ background: #dc3545; color: white; }}
            .btn-success {{ background: #28a745; color: white; }}
            .product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
            .product-card {{ background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .product-card:hover {{ box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
            .price {{ color: #b12704; font-size: 18px; font-weight: bold; }}
            .original-price {{ text-decoration: line-through; color: #999; font-size: 14px; }}
            .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 12px; }}
            .badge-success {{ background: #d4edda; color: #155724; }}
            .badge-warning {{ background: #fff3cd; color: #856404; }}
            .badge-danger {{ background: #f8d7da; color: #721c24; }}
            .badge-info {{ background: #d1ecf1; color: #0c5460; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            .form-group {{ margin-bottom: 15px; }}
            .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            .form-group input, .form-group select, .form-group textarea {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            .alert {{ padding: 10px 15px; border-radius: 4px; margin-bottom: 15px; }}
            .alert-success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .alert-danger {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .alert-warning {{ background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }}
            .stat-card {{ background: white; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: #ff9900; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
            .sidebar {{ width: 250px; float: left; margin-right: 20px; }}
            .main-content {{ overflow: hidden; }}
            .rating {{ color: #ff9900; }}
            .footer {{ background: #131921; color: white; padding: 30px 20px; margin-top: 40px; text-align: center; }}
        </style>
    </head>
    <body>
        <nav class="navbar">
            <a href="/" class="navbar-brand">amazon<span>.clone</span></a>
            <form class="search-bar" action="/products/" method="GET">
                <input type="text" name="q" placeholder="Search products...">
                <button type="submit">🔍</button>
            </form>
            <div>{nav_links}</div>
        </nav>
        
        <div class="container">
            {content}
        </div>
        
        <footer class="footer">
            <p>&copy; 2024 Amazon Clone. All rights reserved.</p>
            <p style="margin-top:10px;color:#999;">Built with Django | Complete E-Commerce Platform</p>
        </footer>
    </body>
    </html>
    """


def generate_home_html(context: dict) -> str:
    """Generate home page HTML."""
    featured_html = ""
    for product in context.get('featured_products', []):
        featured_html += f"""
        <div class="product-card">
            <h3 style="font-size:14px;margin-bottom:8px;">{product.name[:50]}...</h3>
            <div class="price">${product.get_discounted_price()}</div>
            {'<div class="original-price">$' + str(product.price) + '</div>' if product.discount_percentage > 0 else ''}
            <div style="margin-top:5px;font-size:12px;color:#666;">
                {'⭐' * int(product.get_average_rating())} ({product.get_review_count()} reviews)
            </div>
            <div style="margin-top:10px;">
                <a href="/products/{product.slug}/" class="btn btn-primary" style="text-decoration:none;display:inline-block;">View Details</a>
            </div>
        </div>
        """
    
    categories_html = ""
    for cat in context.get('categories', []):
        categories_html += f'<a href="/products/?category={cat.id}" style="display:inline-block;margin:5px;padding:8px 15px;background:#232f3e;color:white;text-decoration:none;border-radius:4px;">{cat.name}</a>'
    
    content = f"""
    <div class="card" style="background:linear-gradient(135deg,#131921,#232f3e);color:white;text-align:center;padding:40px;">
        <h1 style="font-size:36px;margin-bottom:10px;">Welcome to Amazon Clone</h1>
        <p style="font-size:18px;color:#ccc;">Discover millions of products at great prices</p>
        <a href="/products/" class="btn btn-primary" style="text-decoration:none;display:inline-block;margin-top:20px;padding:12px 30px;font-size:16px;">Shop Now</a>
    </div>
    
    <div class="card">
        <h2 style="margin-bottom:15px;">Shop by Category</h2>
        {categories_html}
    </div>
    
    <div class="card">
        <h2 style="margin-bottom:15px;">Featured Products</h2>
        <div class="product-grid">
            {featured_html}
        </div>
    </div>
    """
    
    return get_base_html("Home", content)


def generate_product_list_html(context: dict) -> str:
    """Generate product list HTML."""
    products_html = ""
    for product in context.get('products', []):
        products_html += f"""
        <div class="product-card">
            <h3 style="font-size:14px;margin-bottom:8px;">{product.name[:60]}</h3>
            <div class="price">${product.get_discounted_price()}</div>
            {'<div class="original-price">$' + str(product.price) + '</div>' if product.discount_percentage > 0 else ''}
            <div style="margin-top:5px;font-size:12px;color:#666;">
                {'⭐' * int(product.get_average_rating())} ({product.get_review_count()})
            </div>
            <div style="margin-top:5px;">
                {'<span class="badge badge-success">In Stock</span>' if product.is_in_stock() else '<span class="badge badge-danger">Out of Stock</span>'}
            </div>
            <div style="margin-top:10px;">
                <a href="/products/{product.slug}/" class="btn btn-primary" style="text-decoration:none;display:inline-block;">View</a>
            </div>
        </div>
        """
    
    if not products_html:
        products_html = '<p style="text-align:center;color:#666;padding:40px;">No products found.</p>'
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Products ({context.get('total_results', 0)} results)</h1>
        <form method="GET" action="/products/" style="display:flex;gap:10px;">
            <input type="hidden" name="q" value="{context.get('query', '')}">
            <select name="sort" onchange="this.form.submit()">
                <option value="relevance">Sort by Relevance</option>
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="newest">Newest First</option>
                <option value="popular">Most Popular</option>
            </select>
        </form>
    </div>
    
    <div class="card">
        <form method="GET" action="/products/" style="display:flex;gap:10px;flex-wrap:wrap;">
            <input type="text" name="q" value="{context.get('query', '')}" placeholder="Search products..." style="flex:1;padding:8px;border:1px solid #ddd;border-radius:4px;">
            <input type="number" name="min_price" placeholder="Min Price" style="width:120px;padding:8px;border:1px solid #ddd;border-radius:4px;">
            <input type="number" name="max_price" placeholder="Max Price" style="width:120px;padding:8px;border:1px solid #ddd;border-radius:4px;">
            <button type="submit" class="btn btn-primary">Search</button>
        </form>
    </div>
    
    <div class="product-grid">
        {products_html}
    </div>
    """
    
    return get_base_html("Products", content)


def generate_product_detail_html(context: dict) -> str:
    """Generate product detail HTML."""
    product = context['product']
    
    reviews_html = ""
    for review in context.get('reviews', [])[:5]:
        reviews_html += f"""
        <div style="border-bottom:1px solid #eee;padding:15px 0;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <strong>{review.user.username}</strong>
                <span class="rating">{'⭐' * review.rating}</span>
                {'<span class="badge badge-success">Verified Purchase</span>' if review.is_verified_purchase else ''}
            </div>
            <h4>{review.title}</h4>
            <p style="color:#666;margin-top:5px;">{review.body}</p>
            <small style="color:#999;">{review.created_at.strftime('%B %d, %Y')}</small>
        </div>
        """
    
    content = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:30px;">
        <div class="card">
            <div style="background:#f8f9fa;height:300px;display:flex;align-items:center;justify-content:center;border-radius:8px;font-size:80px;">
                📦
            </div>
        </div>
        
        <div class="card">
            <h1 style="font-size:22px;margin-bottom:10px;">{product.name}</h1>
            <div style="margin-bottom:10px;">
                <span class="rating">{'⭐' * int(context['average_rating'])}</span>
                <span style="color:#666;font-size:14px;"> ({context['review_count']} reviews)</span>
            </div>
            
            <div style="margin-bottom:15px;">
                <span class="price" style="font-size:28px;">${product.get_discounted_price()}</span>
                {'<span class="original-price" style="margin-left:10px;">$' + str(product.price) + '</span>' if product.discount_percentage > 0 else ''}
                {'<span class="badge badge-danger" style="margin-left:10px;">' + str(product.discount_percentage) + '% OFF</span>' if product.discount_percentage > 0 else ''}
            </div>
            
            <div style="margin-bottom:15px;">
                {'<span class="badge badge-success">✓ In Stock (' + str(context["total_stock"]) + ' available)</span>' if context['in_stock'] else '<span class="badge badge-danger">✗ Out of Stock</span>'}
            </div>
            
            <div style="margin-bottom:15px;">
                <p><strong>SKU:</strong> {product.sku}</p>
                {'<p><strong>Brand:</strong> ' + product.brand.name + '</p>' if product.brand else ''}
                {'<p><strong>Category:</strong> ' + product.category.name + '</p>' if product.category else ''}
            </div>
            
            <div style="margin-bottom:20px;">
                <label><strong>Quantity:</strong></label>
                <input type="number" id="quantity" value="1" min="1" max="{context['total_stock']}" style="width:80px;padding:8px;border:1px solid #ddd;border-radius:4px;margin-left:10px;">
            </div>
            
            <div style="display:flex;gap:10px;">
                <button onclick="addToCart({product.id})" class="btn btn-primary" style="flex:1;padding:12px;" {'disabled' if not context['in_stock'] else ''}>
                    🛒 Add to Cart
                </button>
                <button onclick="toggleWishlist({product.id})" class="btn btn-secondary" style="padding:12px;">
                    ♡ Wishlist
                </button>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2 style="margin-bottom:15px;">Product Description</h2>
        <p>{product.description}</p>
    </div>
    
    <div class="card">
        <h2 style="margin-bottom:15px;">Customer Reviews</h2>
        {reviews_html if reviews_html else '<p style="color:#666;">No reviews yet. Be the first to review!</p>'}
        
        <div style="margin-top:20px;padding-top:20px;border-top:1px solid #eee;">
            <h3>Write a Review</h3>
            <form onsubmit="submitReview(event, {product.id})">
                <div class="form-group">
                    <label>Rating</label>
                    <select name="rating" required>
                        <option value="5">⭐⭐⭐⭐⭐ (5 stars)</option>
                        <option value="4">⭐⭐⭐⭐ (4 stars)</option>
                        <option value="3">⭐⭐⭐ (3 stars)</option>
                        <option value="2">⭐⭐ (2 stars)</option>
                        <option value="1">⭐ (1 star)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Title</label>
                    <input type="text" name="title" required placeholder="Review title">
                </div>
                <div class="form-group">
                    <label>Review</label>
                    <textarea name="body" rows="4" required placeholder="Write your review..."></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Submit Review</button>
            </form>
        </div>
    </div>
    
    <script>
    function addToCart(productId) {{
        const quantity = document.getElementById('quantity').value;
        fetch('/cart/add/' + productId + '/', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCookie('csrftoken')}},
            body: 'quantity=' + quantity
        }}).then(r => r.json()).then(data => {{
            alert(data.message);
        }});
    }}
    
    function toggleWishlist(productId) {{
        fetch('/wishlist/toggle/' + productId + '/', {{
            method: 'POST',
            headers: {{'X-CSRFToken': getCookie('csrftoken')}}
        }}).then(r => r.json()).then(data => {{
            alert(data.message);
        }});
    }}
    
    function submitReview(event, productId) {{
        event.preventDefault();
        const form = event.target;
        const data = new FormData(form);
        fetch('/products/' + productId + '/review/', {{
            method: 'POST',
            headers: {{'X-CSRFToken': getCookie('csrftoken')}},
            body: new URLSearchParams(data)
        }}).then(r => r.json()).then(data => {{
            alert(data.message);
            if (data.success) form.reset();
        }});
    }}
    
    function getCookie(name) {{
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {{
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {{
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }}
            }}
        }}
        return cookieValue;
    }}
    </script>
    """
    
    return get_base_html(product.name, content)


def generate_cart_html(context: dict) -> str:
    """Generate cart HTML."""
    cart = context.get('cart')
    items = context.get('items', [])
    summary = context.get('summary', {})
    
    items_html = ""
    for item in items:
        items_html += f"""
        <tr>
            <td>
                <strong>{item.product.name}</strong>
                {'<br><small style="color:#666;">' + item.variant.name + '</small>' if item.variant else ''}
            </td>
            <td>${item.get_unit_price()}</td>
            <td>
                <input type="number" value="{item.quantity}" min="1" 
                       onchange="updateCart({item.id}, this.value)"
                       style="width:60px;padding:5px;border:1px solid #ddd;border-radius:4px;">
            </td>
            <td>${item.get_total_price()}</td>
            <td>
                <button onclick="removeFromCart({item.id})" class="btn btn-danger" style="padding:5px 10px;">Remove</button>
            </td>
        </tr>
        """
    
    if not items_html:
        content = """
        <div class="card" style="text-align:center;padding:60px;">
            <div style="font-size:80px;margin-bottom:20px;">🛒</div>
            <h2>Your cart is empty</h2>
            <p style="color:#666;margin:15px 0;">Add some products to get started!</p>
            <a href="/products/" class="btn btn-primary" style="text-decoration:none;display:inline-block;padding:12px 30px;">Continue Shopping</a>
        </div>
        """
    else:
        content = f"""
        <h1 style="margin-bottom:20px;">Shopping Cart</h1>
        
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;">
            <div class="card">
                <table>
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
                        {items_html}
                    </tbody>
                </table>
            </div>
            
            <div>
                <div class="card">
                    <h3 style="margin-bottom:15px;">Order Summary</h3>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Subtotal ({summary.get('item_count', 0)} items):</span>
                        <strong>${summary.get('subtotal', 0)}</strong>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Tax:</span>
                        <strong>${summary.get('tax', 0)}</strong>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Shipping:</span>
                        <strong>${summary.get('shipping', 0)}</strong>
                    </div>
                    <hr style="margin:10px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:18px;font-weight:bold;">
                        <span>Total:</span>
                        <span class="price">${summary.get('total', 0)}</span>
                    </div>
                    
                    <div style="margin-top:15px;">
                        <input type="text" id="coupon-code" placeholder="Coupon code" 
                               style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;margin-bottom:8px;">
                        <button onclick="applyCoupon()" class="btn btn-secondary" style="width:100%;">Apply Coupon</button>
                    </div>
                    
                    <a href="/checkout/" class="btn btn-primary" 
                       style="display:block;text-align:center;text-decoration:none;margin-top:15px;padding:12px;font-size:16px;">
                        Proceed to Checkout
                    </a>
                </div>
            </div>
        </div>
        
        <script>
        function updateCart(itemId, quantity) {{
            fetch('/cart/update/' + itemId + '/', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCookie('csrftoken')}},
                body: 'quantity=' + quantity
            }}).then(r => r.json()).then(data => {{
                if (data.success) location.reload();
                else alert(data.message);
            }});
        }}
        
        function removeFromCart(itemId) {{
            if (confirm('Remove this item from cart?')) {{
                fetch('/cart/remove/' + itemId + '/', {{
                    method: 'POST',
                    headers: {{'X-CSRFToken': getCookie('csrftoken')}}
                }}).then(r => r.json()).then(data => {{
                    if (data.success) location.reload();
                }});
            }}
        }}
        
        function applyCoupon() {{
            const code = document.getElementById('coupon-code').value;
            alert('Coupon: ' + code + ' - Feature available at checkout');
        }}
        
        function getCookie(name) {{
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {{
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {{
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }}
                }}
            }}
            return cookieValue;
        }}
        </script>
        """
    
    return get_base_html("Shopping Cart", content)


def generate_checkout_html(context: dict) -> str:
    """Generate checkout HTML."""
    addresses = context.get('addresses', [])
    shipping_methods = context.get('shipping_methods', [])
    summary = context.get('summary', {})
    
    addresses_html = ""
    for addr in addresses:
        addresses_html += f"""
        <div style="border:1px solid #ddd;border-radius:4px;padding:10px;margin-bottom:10px;">
            <input type="radio" name="shipping_address_id" value="{addr.id}" {'checked' if addr.is_default else ''}>
            <strong>{addr.full_name}</strong> ({addr.address_type})<br>
            {addr.street_address1}, {addr.city}, {addr.state} {addr.postal_code}<br>
            {addr.country} | {addr.phone}
        </div>
        """
    
    if not addresses_html:
        addresses_html = """
        <div class="alert alert-warning">
            No addresses found. <a href="/profile/">Add an address</a> to continue.
        </div>
        """
    
    shipping_html = ""
    for method in shipping_methods:
        shipping_html += f"""
        <div style="border:1px solid #ddd;border-radius:4px;padding:10px;margin-bottom:10px;">
            <input type="radio" name="shipping_method_id" value="{method.id}">
            <strong>{method.name}</strong> - {method.carrier}<br>
            <small style="color:#666;">{method.estimated_days_min}-{method.estimated_days_max} business days | ${method.base_cost}</small>
        </div>
        """
    
    content = f"""
    <h1 style="margin-bottom:20px;">Checkout</h1>
    
    <form id="checkout-form">
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;">
            <div>
                <div class="card">
                    <h3 style="margin-bottom:15px;">Shipping Address</h3>
                    {addresses_html}
                </div>
                
                <div class="card">
                    <h3 style="margin-bottom:15px;">Shipping Method</h3>
                    {shipping_html if shipping_html else '<p style="color:#666;">Standard shipping will be applied.</p>'}
                </div>
                
                <div class="card">
                    <h3 style="margin-bottom:15px;">Payment Method</h3>
                    <div style="display:flex;flex-direction:column;gap:10px;">
                        <label><input type="radio" name="payment_method" value="credit_card" checked> 💳 Credit Card</label>
                        <label><input type="radio" name="payment_method" value="debit_card"> 💳 Debit Card</label>
                        <label><input type="radio" name="payment_method" value="paypal"> 🅿️ PayPal</label>
                        <label><input type="radio" name="payment_method" value="cash_on_delivery"> 💵 Cash on Delivery</label>
                    </div>
                </div>
                
                <div class="card">
                    <h3 style="margin-bottom:15px;">Coupon Code</h3>
                    <div style="display:flex;gap:10px;">
                        <input type="text" name="coupon_code" placeholder="Enter coupon code" 
                               style="flex:1;padding:8px;border:1px solid #ddd;border-radius:4px;">
                        <button type="button" class="btn btn-secondary">Apply</button>
                    </div>
                </div>
            </div>
            
            <div>
                <div class="card">
                    <h3 style="margin-bottom:15px;">Order Summary</h3>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Subtotal:</span>
                        <strong>${summary.get('subtotal', 0)}</strong>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Tax:</span>
                        <strong>${summary.get('tax', 0)}</strong>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Shipping:</span>
                        <strong>${summary.get('shipping', 0)}</strong>
                    </div>
                    <hr style="margin:10px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:18px;font-weight:bold;">
                        <span>Total:</span>
                        <span class="price">${summary.get('total', 0)}</span>
                    </div>
                    
                    <button type="button" onclick="placeOrder()" 
                            class="btn btn-primary" 
                            style="width:100%;margin-top:20px;padding:15px;font-size:16px;">
                        Place Order
                    </button>
                </div>
            </div>
        </div>
    </form>
    
    <script>
    function placeOrder() {{
        const form = document.getElementById('checkout-form');
        const data = new FormData(form);
        
        fetch('/orders/place/', {{
            method: 'POST',
            headers: {{'X-CSRFToken': getCookie('csrftoken')}},
            body: new URLSearchParams(data)
        }}).then(r => r.json()).then(data => {{
            if (data.success) {{
                alert('Order placed successfully! Order #' + data.order_number);
                window.location = data.redirect_url;
            }} else {{
                alert('Error: ' + data.message);
            }}
        }});
    }}
    
    function getCookie(name) {{
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {{
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {{
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }}
            }}
        }}
        return cookieValue;
    }}
    </script>
    """
    
    return get_base_html("Checkout", content)


def generate_order_list_html(context: dict) -> str:
    """Generate order list HTML."""
    orders = context.get('orders', [])
    
    orders_html = ""
    for order in orders:
        status_colors = {
            'pending': '#856404', 'confirmed': '#0c5460', 'processing': '#004085',
            'shipped': '#0c5460', 'delivered': '#155724', 'cancelled': '#721c24',
        }
        color = status_colors.get(order.status, '#666')
        
        orders_html += f"""
        <tr>
            <td><a href="/orders/{order.id}/" style="color:#0066c0;text-decoration:none;">{order.order_number}</a></td>
            <td>{order.created_at.strftime('%b %d, %Y')}</td>
            <td><span style="color:{color};font-weight:bold;">{order.get_status_display()}</span></td>
            <td>{order.items.count()} items</td>
            <td class="price">${order.total_amount}</td>
            <td>
                <a href="/orders/{order.id}/" class="btn btn-secondary" style="text-decoration:none;padding:5px 10px;">View</a>
                {'<button onclick="cancelOrder(' + str(order.id) + ')" class="btn btn-danger" style="padding:5px 10px;margin-left:5px;">Cancel</button>' if order.can_cancel() else ''}
            </td>
        </tr>
        """
    
    if not orders_html:
        orders_html = '<tr><td colspan="6" style="text-align:center;padding:40px;color:#666;">No orders found.</td></tr>'
    
    content = f"""
    <h1 style="margin-bottom:20px;">My Orders</h1>
    
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>Order #</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Items</th>
                    <th>Total</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {orders_html}
            </tbody>
        </table>
    </div>
    
    <script>
    function cancelOrder(orderId) {{
        if (confirm('Are you sure you want to cancel this order?')) {{
            fetch('/orders/' + orderId + '/cancel/', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCookie('csrftoken')}},
                body: 'reason=Cancelled by customer'
            }}).then(r => r.json()).then(data => {{
                alert(data.message);
                if (data.success) location.reload();
            }});
        }}
    }}
    
    function getCookie(name) {{
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {{
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {{
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }}
            }}
        }}
        return cookieValue;
    }}
    </script>
    """
    
    return get_base_html("My Orders", content)


def generate_order_detail_html(context: dict) -> str:
    """Generate order detail HTML."""
    order = context['order']
    items = context.get('items', [])
    status_history = context.get('status_history', [])
    
    items_html = ""
    for item in items:
        items_html += f"""
        <tr>
            <td>{item.product_name}</td>
            <td>{item.product_sku}</td>
            <td>{item.quantity}</td>
            <td>${item.unit_price}</td>
            <td>${item.total_price}</td>
        </tr>
        """
    
    history_html = ""
    for history in status_history:
        history_html += f"""
        <div style="display:flex;gap:15px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #eee;">
            <div style="color:#666;font-size:12px;min-width:150px;">{history.created_at.strftime('%b %d, %Y %H:%M')}</div>
            <div>
                <strong>{history.status.replace('_', ' ').title()}</strong>
                {('<br><small style="color:#666;">' + history.notes + '</small>') if history.notes else ''}
            </div>
        </div>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Order #{order.order_number}</h1>
        <a href="/orders/" style="color:#0066c0;text-decoration:none;">← Back to Orders</a>
    </div>
    
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;">
        <div>
            <div class="card">
                <h3 style="margin-bottom:15px;">Order Items</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>SKU</th>
                            <th>Qty</th>
                            <th>Unit Price</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <div style="margin-top:15px;text-align:right;">
                    <p>Subtotal: <strong>${order.subtotal}</strong></p>
                    <p>Tax: <strong>${order.tax_amount}</strong></p>
                    <p>Shipping: <strong>${order.shipping_cost}</strong></p>
                    {'<p>Discount: <strong style="color:green;">-$' + str(order.discount_amount) + '</strong></p>' if order.discount_amount > 0 else ''}
                    <p style="font-size:18px;">Total: <strong class="price">${order.total_amount}</strong></p>
                </div>
            </div>
            
            <div class="card">
                <h3 style="margin-bottom:15px;">Order Status History</h3>
                {history_html}
            </div>
        </div>
        
        <div>
            <div class="card">
                <h3 style="margin-bottom:15px;">Order Status</h3>
                <p><strong>Status:</strong> <span style="color:#ff9900;">{order.get_status_display()}</span></p>
                <p><strong>Payment:</strong> {order.payment_status.replace('_', ' ').title()}</p>
                <p><strong>Payment Method:</strong> {order.payment_method.replace('_', ' ').title()}</p>
                <p><strong>Order Date:</strong> {order.created_at.strftime('%b %d, %Y')}</p>
                {('<p><strong>Tracking:</strong> ' + order.tracking_number + '</p>') if order.tracking_number else ''}
                {('<p><strong>Carrier:</strong> ' + order.carrier + '</p>') if order.carrier else ''}
                
                {'<button onclick="cancelOrder(' + str(order.id) + ')" class="btn btn-danger" style="margin-top:10px;width:100%;">Cancel Order</button>' if order.can_cancel() else ''}
            </div>
            
            <div class="card">
                <h3 style="margin-bottom:15px;">Shipping Address</h3>
                <p>{order.shipping_full_name}</p>
                <p>{order.shipping_street_address1}</p>
                {('<p>' + order.shipping_street_address2 + '</p>') if order.shipping_street_address2 else ''}
                <p>{order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}</p>
                <p>{order.shipping_country}</p>
                <p>{order.shipping_phone}</p>
            </div>
        </div>
    </div>
    
    <script>
    function cancelOrder(orderId) {{
        if (confirm('Are you sure you want to cancel this order?')) {{
            fetch('/orders/' + orderId + '/cancel/', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCookie('csrftoken')}},
                body: 'reason=Cancelled by customer'
            }}).then(r => r.json()).then(data => {{
                alert(data.message);
                if (data.success) location.reload();
            }});
        }}
    }}
    
    function getCookie(name) {{
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {{
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {{
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }}
            }}
        }}
        return cookieValue;
    }}
    </script>
    """
    
    return get_base_html(f"Order #{order.order_number}", content)


def generate_signup_html(context: dict) -> str:
    """Generate signup HTML."""
    error_html = f'<div class="alert alert-danger">{context["error"]}</div>' if context.get('error') else ''
    
    content = f"""
    <div style="max-width:400px;margin:40px auto;">
        <div class="card">
            <h2 style="text-align:center;margin-bottom:20px;">Create Account</h2>
            {error_html}
            <form method="POST" action="/signup/">
                <div class="form-group">
                    <label>First Name</label>
                    <input type="text" name="first_name" placeholder="First name">
                </div>
                <div class="form-group">
                    <label>Last Name</label>
                    <input type="text" name="last_name" placeholder="Last name">
                </div>
                <div class="form-group">
                    <label>Username *</label>
                    <input type="text" name="username" required placeholder="Choose a username">
                </div>
                <div class="form-group">
                    <label>Email *</label>
                    <input type="email" name="email" required placeholder="Your email address">
                </div>
                <div class="form-group">
                    <label>Password *</label>
                    <input type="password" name="password" required placeholder="Create a password">
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;padding:12px;font-size:16px;">
                    Create Account
                </button>
            </form>
            <p style="text-align:center;margin-top:15px;color:#666;">
                Already have an account? <a href="/login/" style="color:#0066c0;">Sign In</a>
            </p>
        </div>
    </div>
    """
    
    return get_base_html("Sign Up", content)


def generate_profile_html(context: dict) -> str:
    """Generate profile HTML."""
    user = context['user']
    stats = context.get('stats', {})
    addresses = context.get('addresses', [])
    
    addresses_html = ""
    for addr in addresses:
        addresses_html += f"""
        <div style="border:1px solid #ddd;border-radius:4px;padding:15px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;">
                <strong>{addr.full_name}</strong>
                <span class="badge badge-info">{addr.address_type.title()}</span>
                {'<span class="badge badge-success" style="margin-left:5px;">Default</span>' if addr.is_default else ''}
            </div>
            <p style="margin-top:5px;color:#666;">
                {addr.street_address1}, {addr.city}, {addr.state} {addr.postal_code}, {addr.country}
            </p>
            <p style="color:#666;">{addr.phone}</p>
        </div>
        """
    
    content = f"""
    <h1 style="margin-bottom:20px;">My Account</h1>
    
    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card">
            <div class="stat-number">{stats.get('total_orders', 0)}</div>
            <div class="stat-label">Total Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.get('total_spent', 0)}</div>
            <div class="stat-label">Total Spent</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{stats.get('pending_orders', 0)}</div>
            <div class="stat-label">Pending Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{stats.get('wishlist_count', 0)}</div>
            <div class="stat-label">Wishlist Items</div>
        </div>
    </div>
    
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
        <div class="card">
            <h3 style="margin-bottom:15px;">Account Information</h3>
            <p><strong>Name:</strong> {user.get_full_name() or user.username}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Username:</strong> {user.username}</p>
            <p><strong>Member Since:</strong> {user.date_joined.strftime('%B %Y')}</p>
            <div style="margin-top:15px;">
                <a href="/orders/" class="btn btn-primary" style="text-decoration:none;display:inline-block;">View Orders</a>
                <a href="/wishlist/" class="btn btn-secondary" style="text-decoration:none;display:inline-block;margin-left:10px;">Wishlist</a>
            </div>
        </div>
        
        <div class="card">
            <h3 style="margin-bottom:15px;">Saved Addresses</h3>
            {addresses_html if addresses_html else '<p style="color:#666;">No addresses saved yet.</p>'}
            <button class="btn btn-secondary" style="margin-top:10px;" onclick="alert('Add address form - implement in full version')">
                + Add New Address
            </button>
        </div>
    </div>
    """
    
    return get_base_html("My Account", content)


def generate_wishlist_html(context: dict) -> str:
    """Generate wishlist HTML."""
    products = context.get('products', [])
    
    products_html = ""
    for product in products:
        products_html += f"""
        <div class="product-card">
            <h3 style="font-size:14px;margin-bottom:8px;">{product.name[:50]}</h3>
            <div class="price">${product.get_discounted_price()}</div>
            <div style="margin-top:10px;display:flex;gap:5px;">
                <a href="/products/{product.slug}/" class="btn btn-primary" style="text-decoration:none;flex:1;text-align:center;">View</a>
                <button onclick="toggleWishlist({product.id})" class="btn btn-danger" style="padding:8px;">Remove</button>
            </div>
        </div>
        """
    
    if not products_html:
        products_html = """
        <div style="text-align:center;padding:60px;color:#666;">
            <div style="font-size:60px;margin-bottom:15px;">♡</div>
            <h3>Your wishlist is empty</h3>
            <p style="margin:10px 0;">Save items you love to your wishlist</p>
            <a href="/products/" class="btn btn-primary" style="text-decoration:none;display:inline-block;margin-top:10px;">Browse Products</a>
        </div>
        """
    
    content = f"""
    <h1 style="margin-bottom:20px;">My Wishlist</h1>
    <div class="product-grid">
        {products_html}
    </div>
    
    <script>
    function toggleWishlist(productId) {{
        fetch('/wishlist/toggle/' + productId + '/', {{
            method: 'POST',
            headers: {{'X-CSRFToken': getCookie('csrftoken')}}
        }}).then(r => r.json()).then(data => {{
            if (data.success) location.reload();
        }});
    }}
    
    function getCookie(name) {{
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {{
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {{
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }}
            }}
        }}
        return cookieValue;
    }}
    </script>
    """
    
    return get_base_html("My Wishlist", content)


def generate_admin_dashboard_html(context: dict) -> str:
    """Generate admin dashboard HTML."""
    analytics = context.get('order_analytics', {})
    inventory = context.get('inventory_report', {})
    po_analytics = context.get('po_analytics', {})
    recent_orders = context.get('recent_orders', [])
    low_stock = context.get('low_stock_items', [])
    
    recent_orders_html = ""
    for order in recent_orders:
        recent_orders_html += f"""
        <tr>
            <td><a href="/orders/{order.id}/" style="color:#0066c0;">{order.order_number}</a></td>
            <td>{order.user.username}</td>
            <td>{order.status.replace('_', ' ').title()}</td>
            <td>${order.total_amount}</td>
            <td>{order.created_at.strftime('%b %d, %Y')}</td>
        </tr>
        """
    
    low_stock_html = ""
    for inv in low_stock:
        low_stock_html += f"""
        <tr>
            <td>{inv.product.name}</td>
            <td>{inv.warehouse.name}</td>
            <td style="color:{'red' if inv.quantity == 0 else 'orange'};">{inv.quantity}</td>
            <td>{inv.reorder_point}</td>
        </tr>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Admin Dashboard</h1>
        <div>
            <a href="/admin-inventory/" class="btn btn-secondary" style="text-decoration:none;margin-right:10px;">Inventory</a>
            <a href="/admin-orders/" class="btn btn-secondary" style="text-decoration:none;margin-right:10px;">Orders</a>
            <a href="/admin-purchase-orders/" class="btn btn-secondary" style="text-decoration:none;margin-right:10px;">Purchase Orders</a>
            <a href="/admin-suppliers/" class="btn btn-secondary" style="text-decoration:none;margin-right:10px;">Suppliers</a>
            <a href="/admin-warehouses/" class="btn btn-secondary" style="text-decoration:none;margin-right:10px;">Warehouses</a>
            <a href="/admin-users/" class="btn btn-secondary" style="text-decoration:none;">Users</a>
        </div>
    </div>
    
    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card">
            <div class="stat-number">{analytics.get('total_orders', 0)}</div>
            <div class="stat-label">Total Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${analytics.get('total_revenue', 0)}</div>
            <div class="stat-label">Total Revenue</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{analytics.get('today_orders', 0)}</div>
            <div class="stat-label">Today's Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${analytics.get('today_revenue', 0)}</div>
            <div class="stat-label">Today's Revenue</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{analytics.get('pending_orders', 0)}</div>
            <div class="stat-label">Pending Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{inventory.get('total_products', 0)}</div>
            <div class="stat-label">Total Products</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color:orange;">{inventory.get('low_stock_items', 0)}</div>
            <div class="stat-label">Low Stock Items</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color:red;">{inventory.get('out_of_stock_items', 0)}</div>
            <div class="stat-label">Out of Stock</div>
        </div>
    </div>
    
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
        <div class="card">
            <h3 style="margin-bottom:15px;">Recent Orders</h3>
            <table>
                <thead>
                    <tr><th>Order #</th><th>Customer</th><th>Status</th><th>Total</th><th>Date</th></tr>
                </thead>
                <tbody>
                    {recent_orders_html if recent_orders_html else '<tr><td colspan="5" style="text-align:center;color:#666;">No orders yet</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h3 style="margin-bottom:15px;">Low Stock Alerts</h3>
            <table>
                <thead>
                    <tr><th>Product</th><th>Warehouse</th><th>Stock</th><th>Reorder At</th></tr>
                </thead>
                <tbody>
                    {low_stock_html if low_stock_html else '<tr><td colspan="4" style="text-align:center;color:#666;">No low stock items</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    """
    
    return get_base_html("Admin Dashboard", content)


def generate_admin_inventory_html(context: dict) -> str:
    """Generate admin inventory HTML."""
    inventories = context.get('inventories', [])
    alerts = context.get('alerts', [])
    report = context.get('report', {})
    
    inventory_html = ""
    for inv in inventories[:50]:
        status_color = 'red' if inv.quantity == 0 else ('orange' if inv.needs_reorder() else 'green')
        inventory_html += f"""
        <tr>
            <td>{inv.product.name[:40]}</td>
            <td>{inv.product.sku}</td>
            <td>{inv.warehouse.name}</td>
            <td style="color:{status_color};font-weight:bold;">{inv.quantity}</td>
            <td>{inv.reserved_quantity}</td>
            <td>{inv.get_available_quantity()}</td>
            <td>{inv.reorder_point}</td>
            <td>
                {'<span class="badge badge-danger">Out of Stock</span>' if inv.quantity == 0 else ''}
                {'<span class="badge badge-warning">Low Stock</span>' if inv.needs_reorder() and inv.quantity > 0 else ''}
                {'<span class="badge badge-success">OK</span>' if not inv.needs_reorder() and inv.quantity > 0 else ''}
            </td>
        </tr>
        """
    
    alerts_html = ""
    for alert in alerts[:10]:
        alerts_html += f"""
        <div class="alert alert-warning" style="margin-bottom:10px;">
            <strong>{alert.alert_type.replace('_', ' ').title()}:</strong> {alert.message}
            <small style="float:right;color:#666;">{alert.created_at.strftime('%b %d, %Y')}</small>
        </div>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Inventory Management</h1>
        <a href="/admin-dashboard/" style="color:#0066c0;text-decoration:none;">← Dashboard</a>
    </div>
    
    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card">
            <div class="stat-number">{report.get('total_products', 0)}</div>
            <div class="stat-label">Total Products</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${report.get('total_stock_value', 0)}</div>
            <div class="stat-label">Stock Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color:orange;">{report.get('low_stock_items', 0)}</div>
            <div class="stat-label">Low Stock</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color:red;">{report.get('out_of_stock_items', 0)}</div>
            <div class="stat-label">Out of Stock</div>
        </div>
    </div>
    
    {('<div class="card"><h3 style="margin-bottom:15px;">Active Alerts</h3>' + alerts_html + '</div>') if alerts_html else ''}
    
    <div class="card">
        <h3 style="margin-bottom:15px;">Inventory Overview</h3>
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th>Warehouse</th>
                    <th>Quantity</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>Reorder Point</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {inventory_html if inventory_html else '<tr><td colspan="8" style="text-align:center;color:#666;">No inventory records</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    return get_base_html("Inventory Management", content)


def generate_admin_orders_html(context: dict) -> str:
    """Generate admin orders HTML."""
    orders = context.get('orders', [])
    analytics = context.get('analytics', {})
    
    orders_html = ""
    for order in orders[:50]:
        orders_html += f"""
        <tr>
            <td><a href="/orders/{order.id}/" style="color:#0066c0;">{order.order_number}</a></td>
            <td>{order.user.username}</td>
            <td>{order.status.replace('_', ' ').title()}</td>
            <td>{order.payment_status.replace('_', ' ').title()}</td>
            <td>${order.total_amount}</td>
            <td>{order.created_at.strftime('%b %d, %Y')}</td>
            <td>
                <select onchange="updateStatus({order.id}, this.value)" style="padding:4px;border:1px solid #ddd;border-radius:4px;">
                    <option value="">Update Status</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="processing">Processing</option>
                    <option value="shipped">Shipped</option>
                    <option value="delivered">Delivered</option>
                    <option value="cancelled">Cancelled</option>
                </select>
            </td>
        </tr>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Order Management</h1>
        <a href="/admin-dashboard/" style="color:#0066c0;text-decoration:none;">← Dashboard</a>
    </div>
    
    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card">
            <div class="stat-number">{analytics.get('total_orders', 0)}</div>
            <div class="stat-label">Total Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${analytics.get('total_revenue', 0)}</div>
            <div class="stat-label">Revenue</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{analytics.get('pending_orders', 0)}</div>
            <div class="stat-label">Pending</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${analytics.get('average_order_value', 0)}</div>
            <div class="stat-label">Avg Order Value</div>
        </div>
    </div>
    
    <div class="card">
        <div style="margin-bottom:15px;">
            <a href="/admin-orders/" class="btn btn-secondary" style="text-decoration:none;margin-right:5px;">All</a>
            <a href="/admin-orders/?status=pending" class="btn btn-secondary" style="text-decoration:none;margin-right:5px;">Pending</a>
            <a href="/admin-orders/?status=processing" class="btn btn-secondary" style="text-decoration:none;margin-right:5px;">Processing</a>
            <a href="/admin-orders/?status=shipped" class="btn btn-secondary" style="text-decoration:none;margin-right:5px;">Shipped</a>
            <a href="/admin-orders/?status=delivered" class="btn btn-secondary" style="text-decoration:none;">Delivered</a>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Order #</th>
                    <th>Customer</th>
                    <th>Status</th>
                    <th>Payment</th>
                    <th>Total</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {orders_html if orders_html else '<tr><td colspan="7" style="text-align:center;color:#666;">No orders found</td></tr>'}
            </tbody>
        </table>
    </div>
    
    <script>
    function updateStatus(orderId, status) {{
        if (!status) return;
        fetch('/admin/orders/' + orderId + '/update-status/', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCookie('csrftoken')}},
            body: 'status=' + status
        }}).then(r => r.json()).then(data => {{
            alert(data.message);
            if (data.success) location.reload();
        }});
    }}
    
    function getCookie(name) {{
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {{
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {{
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }}
            }}
        }}
        return cookieValue;
    }}
    </script>
    """
    
    return get_base_html("Order Management", content)


def generate_admin_purchase_orders_html(context: dict) -> str:
    """Generate admin purchase orders HTML."""
    purchase_orders = context.get('purchase_orders', [])
    analytics = context.get('po_analytics', {})
    
    po_html = ""
    for po in purchase_orders[:50]:
        po_html += f"""
        <tr>
            <td>{po.order_number}</td>
            <td>{po.supplier.name}</td>
            <td>{po.warehouse.name}</td>
            <td>{po.status.replace('_', ' ').title()}</td>
            <td>${po.total_amount}</td>
            <td>{po.order_date.strftime('%b %d, %Y')}</td>
            <td>{po.expected_delivery or 'N/A'}</td>
        </tr>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Purchase Orders</h1>
        <a href="/admin-dashboard/" style="color:#0066c0;text-decoration:none;">← Dashboard</a>
    </div>
    
    <div class="stats-grid" style="margin-bottom:20px;">
        <div class="stat-card">
            <div class="stat-number">{analytics.get('total_orders', 0)}</div>
            <div class="stat-label">Total POs</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{analytics.get('pending_orders', 0)}</div>
            <div class="stat-label">Pending</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${analytics.get('total_value', 0)}</div>
            <div class="stat-label">Total Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{analytics.get('received_this_month', 0)}</div>
            <div class="stat-label">Received This Month</div>
        </div>
    </div>
    
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>PO Number</th>
                    <th>Supplier</th>
                    <th>Warehouse</th>
                    <th>Status</th>
                    <th>Total</th>
                    <th>Order Date</th>
                    <th>Expected Delivery</th>
                </tr>
            </thead>
            <tbody>
                {po_html if po_html else '<tr><td colspan="7" style="text-align:center;color:#666;">No purchase orders found</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    return get_base_html("Purchase Orders", content)


def generate_admin_suppliers_html(context: dict) -> str:
    """Generate admin suppliers HTML."""
    suppliers = context.get('suppliers', [])
    
    suppliers_html = ""
    for supplier in suppliers:
        suppliers_html += f"""
        <tr>
            <td>{supplier.name}</td>
            <td>{supplier.contact_person}</td>
            <td>{supplier.email}</td>
            <td>{supplier.phone}</td>
            <td>{supplier.country}</td>
            <td>{'<span class="badge badge-success">Active</span>' if supplier.is_active else '<span class="badge badge-danger">Inactive</span>'}</td>
            <td>{'⭐' * int(supplier.rating)}</td>
            <td>{supplier.get_total_orders()}</td>
        </tr>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Supplier Management</h1>
        <a href="/admin-dashboard/" style="color:#0066c0;text-decoration:none;">← Dashboard</a>
    </div>
    
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Contact</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Country</th>
                    <th>Status</th>
                    <th>Rating</th>
                    <th>Orders</th>
                </tr>
            </thead>
            <tbody>
                {suppliers_html if suppliers_html else '<tr><td colspan="8" style="text-align:center;color:#666;">No suppliers found</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    return get_base_html("Supplier Management", content)


def generate_admin_warehouses_html(context: dict) -> str:
    """Generate admin warehouses HTML."""
    warehouse_summaries = context.get('warehouse_summaries', [])
    
    warehouses_html = ""
    for summary in warehouse_summaries:
        wh = summary['warehouse']
        warehouses_html += f"""
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                <h3>{wh.name} ({wh.code})</h3>
                <span class="badge badge-success">Active</span>
            </div>
            <p><strong>Location:</strong> {wh.city}, {wh.state}, {wh.country}</p>
            <p><strong>Manager:</strong> {wh.manager.username if wh.manager else 'N/A'}</p>
            <div class="stats-grid" style="margin-top:15px;">
                <div class="stat-card" style="padding:10px;">
                    <div class="stat-number" style="font-size:20px;">{summary['total_products']}</div>
                    <div class="stat-label" style="font-size:12px;">Products</div>
                </div>
                <div class="stat-card" style="padding:10px;">
                    <div class="stat-number" style="font-size:20px;">{summary['total_items']}</div>
                    <div class="stat-label" style="font-size:12px;">Total Items</div>
                </div>
                <div class="stat-card" style="padding:10px;">
                    <div class="stat-number" style="font-size:20px;">${summary['total_value']}</div>
                    <div class="stat-label" style="font-size:12px;">Value</div>
                </div>
                <div class="stat-card" style="padding:10px;">
                    <div class="stat-number" style="font-size:20px;color:orange;">{summary['low_stock_items']}</div>
                    <div class="stat-label" style="font-size:12px;">Low Stock</div>
                </div>
            </div>
        </div>
        """
    
    if not warehouses_html:
        warehouses_html = '<div class="card"><p style="text-align:center;color:#666;padding:40px;">No warehouses found</p></div>'
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>Warehouse Management</h1>
        <a href="/admin-dashboard/" style="color:#0066c0;text-decoration:none;">← Dashboard</a>
    </div>
    
    {warehouses_html}
    """
    
    return get_base_html("Warehouse Management", content)


def generate_admin_users_html(context: dict) -> str:
    """Generate admin users HTML."""
    users = context.get('users', [])
    
    users_html = ""
    for user in users[:50]:
        user_type = getattr(getattr(user, 'profile', None), 'user_type', 'customer')
        users_html += f"""
        <tr>
            <td>{user.username}</td>
            <td>{user.get_full_name() or '-'}</td>
            <td>{user.email}</td>
            <td>{user_type.replace('_', ' ').title()}</td>
            <td>{'<span class="badge badge-success">Active</span>' if user.is_active else '<span class="badge badge-danger">Inactive</span>'}</td>
            <td>{'<span class="badge badge-warning">Staff</span>' if user.is_staff else ''}</td>
            <td>{user.date_joined.strftime('%b %d, %Y')}</td>
            <td>{user.orders.count() if hasattr(user, 'orders') else 0}</td>
        </tr>
        """
    
    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1>User Management</h1>
        <a href="/admin-dashboard/" style="color:#0066c0;text-decoration:none;">← Dashboard</a>
    </div>
    
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>Username</th>
                    <th>Full Name</th>
                    <th>Email</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Role</th>
                    <th>Joined</th>
                    <th>Orders</th>
                </tr>
            </thead>
            <tbody>
                {users_html if users_html else '<tr><td colspan="8" style="text-align:center;color:#666;">No users found</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    
    return get_base_html("User Management", content)


# ============================================================
# URL PATTERNS
# ============================================================

urlpatterns = [
    path('', home_view, name='home'),
    path('products/', product_list_view, name='product_list'),
    path('products/<slug:slug>/', product_detail_view, name='product_detail'),
    path('products/<int:product_id>/review/', add_review_view, name='add_review'),
    
    path('cart/', cart_view, name='cart'),
    path('cart/add/<int:product_id>/', add_to_cart_view, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', remove_from_cart_view, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', update_cart_view, name='update_cart'),
    
    path('checkout/', checkout_view, name='checkout'),
    path('orders/place/', place_order_view, name='place_order'),
    path('orders/', order_list_view, name='order_list'),
    path('orders/<int:order_id>/', order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/cancel/', cancel_order_view, name='cancel_order'),
    
    path('signup/', signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(
        template_name=None,
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('profile/', profile_view, name='profile'),
    path('wishlist/', wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', toggle_wishlist_view, name='toggle_wishlist'),
    path('notifications/', notifications_view, name='notifications'),
    
    # Admin views
    path('admin-dashboard/', admin_dashboard_view, name='admin_dashboard'),
    path('admin-inventory/', admin_inventory_view, name='admin_inventory'),
    path('admin-orders/', admin_orders_view, name='admin_orders'),
    path('admin-purchase-orders/', admin_purchase_orders_view, name='admin_purchase_orders'),
    path('admin-suppliers/', admin_suppliers_view, name='admin_suppliers'),
    path('admin-warehouses/', admin_warehouses_view, name='admin_warehouses'),
    path('admin-users/', admin_users_view, name='admin_users'),
    path('admin/orders/<int:order_id>/update-status/', update_order_status_view, name='update_order_status'),
    
    # API endpoints
    path('api/products/', api_products_view, name='api_products'),
    path('api/inventory/', api_inventory_view, name='api_inventory'),
    
    # Django admin
    path('django-admin/', admin.site.urls),
]


# ============================================================
# DATABASE SETUP AND SAMPLE DATA
# ============================================================

def create_tables():
    """Create all database tables."""
    from django.db import connection
    from django.core.management import call_command
    
    try:
        call_command('migrate', '--run-syncdb', verbosity=0, interactive=False)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"Database setup: {e}")
        try:
            from django.db import connection
            with connection.schema_editor() as schema_editor:
                models_to_create = [
                    UserProfile, Address, Category, Brand, Supplier, Warehouse,
                    Product, ProductVariant, ProductImage, Inventory, InventoryTransaction,
                    PurchaseOrder, PurchaseOrderItem, Cart, CartItem, Coupon,
                    Order, OrderItem, OrderStatusHistory, Review, Wishlist,
                    Notification, StockAlert, ShippingMethod, PaymentTransaction, ReturnRequest
                ]
                for model in models_to_create:
                    try:
                        schema_editor.create_model(model)
                    except Exception:
                        pass
            print("✓ Tables created via schema editor")
        except Exception as e2:
            print(f"Schema editor error: {e2}")


def create_sample_data():
    """Create sample data for demonstration."""
    import re
    
    print("Creating sample data...")
    
    # Create admin user
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        UserProfile.objects.get_or_create(user=admin_user, defaults={'user_type': 'admin'})
        Cart.objects.get_or_create(user=admin_user)
        Wishlist.objects.get_or_create(user=admin_user)
        print("✓ Admin user created (username: admin, password: admin123)")
    
    # Create test customer
    if not User.objects.filter(username='customer1').exists():
        customer = User.objects.create_user('customer1', 'customer@example.com', 'customer123', 
                                             first_name='John', last_name='Doe')
        UserProfile.objects.get_or_create(user=customer, defaults={'user_type': 'customer'})
        Cart.objects.get_or_create(user=customer)
        Wishlist.objects.get_or_create(user=customer)
        
        Address.objects.create(
            user=customer,
            full_name='John Doe',
            street_address1='123 Main Street',
            city='New York',
            state='NY',
            postal_code='10001',
            country='United States',
            phone='+1-555-0100',
            is_default=True
        )
        print("✓ Customer user created (username: customer1, password: customer123)")
    
    # Create categories
    categories_data = [
        ('Electronics', 'electronics'),
        ('Clothing', 'clothing'),
        ('Books', 'books'),
        ('Home & Garden', 'home-garden'),
        ('Sports', 'sports'),
        ('Toys', 'toys'),
    ]
    
    categories = {}
    for name, slug in categories_data:
        cat, created = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'description': f'{name} products', 'is_active': True}
        )
        categories[slug] = cat
    
    # Sub-categories
    sub_cats = [
        ('Smartphones', 'smartphones', 'electronics'),
        ('Laptops', 'laptops', 'electronics'),
        ('Men\'s Clothing', 'mens-clothing', 'clothing'),
        ('Women\'s Clothing', 'womens-clothing', 'clothing'),
    ]
    
    for name, slug, parent_slug in sub_cats:
        Category.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'parent': categories.get(parent_slug),
                'is_active': True
            }
        )
    
    print("✓ Categories created")
    
    # Create brands
    brands_data = [
        ('Apple', 'apple'),
        ('Samsung', 'samsung'),
        ('Nike', 'nike'),
        ('Sony', 'sony'),
        ('Amazon Basics', 'amazon-basics'),
    ]
    
    brands = {}
    for name, slug in brands_data:
        brand, created = Brand.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'is_active': True}
        )
        brands[slug] = brand
    
    print("✓ Brands created")
    
    # Create supplier
    supplier, created = Supplier.objects.get_or_create(
        email='supplier@techcorp.com',
        defaults={
            'name': 'TechCorp Supplies',
            'contact_person': 'Jane Smith',
            'phone': '+1-555-0200',
            'address': '456 Business Ave',
            'city': 'San Francisco',
            'state': 'CA',
            'country': 'United States',
            'postal_code': '94102',
            'payment_terms': 'Net 30',
            'is_active': True,
            'rating': Decimal('4.5'),
        }
    )
    
    print("✓ Supplier created")
    
    # Create warehouse
    admin_user = User.objects.get(username='admin')
    warehouse, created = Warehouse.objects.get_or_create(
        code='WH-001',
        defaults={
            'name': 'Main Warehouse',
            'address': '789 Warehouse Blvd',
            'city': 'Chicago',
            'state': 'IL',
            'country': 'United States',
            'postal_code': '60601',
            'phone': '+1-555-0300',
            'email': 'warehouse@example.com',
            'manager': admin_user,
            'capacity': 10000,
            'is_active': True,
        }
    )
    
    print("✓ Warehouse created")
    
    # Create products
    products_data = [
        {
            'name': 'iPhone 15 Pro Max',
            'sku': 'APPLE-IP15PM-256',
            'price': Decimal('1199.99'),
            'cost_price': Decimal('800.00'),
            'description': 'The latest iPhone with A17 Pro chip, titanium design, and advanced camera system.',
            'category': categories.get('electronics'),
            'brand': brands.get('apple'),
            'discount_percentage': Decimal('5.00'),
            'is_featured': True,
            'stock': 50,
        },
        {
            'name': 'Samsung Galaxy S24 Ultra',
            'sku': 'SAMSUNG-S24U-256',
            'price': Decimal('1099.99'),
            'cost_price': Decimal('700.00'),
            'description': 'Samsung\'s flagship with S Pen, 200MP camera, and AI features.',
            'category': categories.get('electronics'),
            'brand': brands.get('samsung'),
            'discount_percentage': Decimal('10.00'),
            'is_featured': True,
            'stock': 35,
        },
        {
            'name': 'Sony WH-1000XM5 Headphones',
            'sku': 'SONY-WH1000XM5-BLK',
            'price': Decimal('349.99'),
            'cost_price': Decimal('180.00'),
            'description': 'Industry-leading noise canceling wireless headphones.',
            'category': categories.get('electronics'),
            'brand': brands.get('sony'),
            'discount_percentage': Decimal('15.00'),
            'is_featured': True,
            'stock': 100,
        },
        {
            'name': 'Nike Air Max 270',
            'sku': 'NIKE-AM270-BLK-10',
            'price': Decimal('149.99'),
            'cost_price': Decimal('60.00'),
            'description': 'Nike\'s biggest Air unit yet for all-day comfort.',
            'category': categories.get('sports'),
            'brand': brands.get('nike'),
            'discount_percentage': Decimal('0.00'),
            'is_featured': True,
            'stock': 75,
        },
        {
            'name': 'MacBook Pro 14-inch M3',
            'sku': 'APPLE-MBP14-M3-512',
            'price': Decimal('1999.99'),
            'cost_price': Decimal('1400.00'),
            'description': 'Supercharged by M3 Pro or M3 Max chip for pro workflows.',
            'category': categories.get('electronics'),
            'brand': brands.get('apple'),
            'discount_percentage': Decimal('0.00'),
            'is_featured': True,
            'stock': 25,
        },
        {
            'name': 'Amazon Basics USB-C Cable',
            'sku': 'AMZ-USBC-6FT',
            'price': Decimal('12.99'),
            'cost_price': Decimal('3.00'),
            'description': 'High-speed USB-C to USB-C cable, 6 feet.',
            'category': categories.get('electronics'),
            'brand': brands.get('amazon-basics'),
            'discount_percentage': Decimal('0.00'),
            'is_featured': False,
            'stock': 500,
        },
        {
            'name': 'Classic Fit Oxford Shirt',
            'sku': 'SHIRT-OXFORD-BLU-M',
            'price': Decimal('49.99'),
            'cost_price': Decimal('15.00'),
            'description': 'Classic fit oxford shirt in premium cotton.',
            'category': categories.get('clothing'),
            'brand': None,
            'discount_percentage': Decimal('20.00'),
            'is_featured': False,
            'stock': 200,
        },
        {
            'name': 'Python Programming: Complete Guide',
            'sku': 'BOOK-PYTHON-2024',
            'price': Decimal('39.99'),
            'cost_price': Decimal('10.00'),
            'description': 'Comprehensive guide to Python programming for beginners and experts.',
            'category': categories.get('books'),
            'brand': None,
            'discount_percentage': Decimal('0.00'),
            'is_featured': False,
            'stock': 150,
        },
    ]
    
    for prod_data in products_data:
        stock = prod_data.pop('stock')
        slug = re.sub(r'[^a-z0-9-]', '-', prod_data['name'].lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        product, created = Product.objects.get_or_create(
            sku=prod_data['sku'],
            defaults={**prod_data, 'slug': slug, 'status': 'active'}
        )
        
        if created:
            # Add inventory
            inventory, _ = Inventory.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                defaults={
                    'quantity': stock,
                    'reorder_point': 10,
                    'reorder_quantity': 50,
                }
            )
    
    print("✓ Products created with inventory")
    
    # Create shipping methods
    shipping_data = [
        {
            'name': 'Standard Shipping',
            'carrier': 'USPS',
            'base_cost': Decimal('5.99'),
            'estimated_days_min': 5,
            'estimated_days_max': 7,
            'free_shipping_threshold': Decimal('35.00'),
        },
        {
            'name': 'Express Shipping',
            'carrier': 'UPS',
            'base_cost': Decimal('14.99'),
            'estimated_days_min': 2,
            'estimated_days_max': 3,
        },
        {
            'name': 'Overnight Shipping',
            'carrier': 'FedEx',
            'base_cost': Decimal('29.99'),
            'estimated_days_min': 1,
            'estimated_days_max': 1,
        },
    ]
    
    for ship_data in shipping_data:
        ShippingMethod.objects.get_or_create(
            name=ship_data['name'],
            defaults={**ship_data, 'is_active': True}
        )
    
    print("✓ Shipping methods created")
    
    # Create sample coupon
    if not Coupon.objects.filter(code='SAVE10').exists():
        Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            minimum_order_amount=Decimal('50.00'),
            valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=365),
            is_active=True,
            usage_limit=1000,
        )
    
    if not Coupon.objects.filter(code='FREESHIP').exists():
        Coupon.objects.create(
            code='FREESHIP',
            discount_type='free_shipping',
            discount_value=Decimal('0.00'),
            minimum_order_amount=Decimal('25.00'),
            valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=365),
            is_active=True,
        )
    
    print("✓ Coupons created (SAVE10, FREESHIP)")
    
    # Create sample reviews
    customer = User.objects.filter(username='customer1').first()
    if customer:
        products = Product.objects.all()[:3]
        for i, product in enumerate(products):
            if not Review.objects.filter(user=customer, product=product).exists():
                Review.objects.create(
                    user=customer,
                    product=product,
                    rating=5 - i,
                    title=f"Great product!",
                    body=f"This is an excellent product. Highly recommended!",
                    is_verified_purchase=False,
                    is_approved=True,
                )
    
    print("✓ Sample reviews created")
    print("\n✅ Sample data creation complete!")
    print("\nLogin credentials:")
    print("  Admin: username=admin, password=admin123")
    print("  Customer: username=customer1, password=customer123")


# ============================================================
# WSGI APPLICATION
# ============================================================

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("Amazon Clone - Django E-Commerce Platform")
    print("=" * 60)
    
    # Setup database
    print("\n📦 Setting up database...")
    create_tables()
    
    # Create sample data
    print("\n🌱 Creating sample data...")
    try:
        create_sample_data()
    except Exception as e:
        print(f"Sample data error: {e}")
    
    # Start server
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    print(f"\n🚀 Starting Amazon Clone server...")
    print(f"\n📌 Access the application at:")
    print(f"   Home:           http://localhost:{port}/")
    print(f"   Products:       http://localhost:{port}/products/")
    print(f"   Cart:           http://localhost:{port}/cart/")
    print(f"   Login:          http://localhost:{port}/login/")
    print(f"   Sign Up:        http://localhost:{port}/signup/")
    print(f"   Admin Panel:    http://localhost:{port}/admin-dashboard/")
    print(f"   Django Admin:   http://localhost:{port}/django-admin/")
    print(f"   API Products:   http://localhost:{port}/api/products/")
    print(f"\n🔑 Login: admin/admin123 or customer1/customer123")
    print(f"\n{'=' * 60}")
    
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])