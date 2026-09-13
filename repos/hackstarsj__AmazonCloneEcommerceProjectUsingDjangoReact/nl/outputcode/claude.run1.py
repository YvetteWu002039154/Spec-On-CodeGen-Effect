#!/usr/bin/env python3
"""
Amazon Clone - Complete Django Implementation
A fully functional e-commerce platform with inventory management system.
"""

import os
import sys
import django
from django.conf import settings

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
        ROOT_URLCONF='__main__',
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
from django.contrib.auth.models import User, AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q, Sum, F
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid
import json
from datetime import datetime, timedelta


# ============================================================
# MODELS
# ============================================================

class UserProfile(models.Model):
    """Extended user profile for the Amazon clone."""
    
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('warehouse_manager', 'Warehouse Manager'),
        ('supplier', 'Supplier'),
        ('seller', 'Seller'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()


class Address(models.Model):
    """User address model."""
    
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    full_name = models.CharField(max_length=100)
    street_address1 = models.CharField(max_length=200)
    street_address2 = models.CharField(max_length=200, blank=True)
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
    
    def get_full_address(self):
        parts = [self.street_address1]
        if self.street_address2:
            parts.append(self.street_address2)
        parts.extend([self.city, self.state, self.postal_code, self.country])
        return ', '.join(parts)


class Category(models.Model):
    """Product category with multi-level support."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        verbose_name_plural = 'Categories'
    
    def __str__(self):
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
        for child in self.children.filter(is_active=True):
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_level(self):
        """Get the depth level of this category."""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level


class Brand(models.Model):
    """Product brand model."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Supplier model for inventory management."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    contact_person = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payment_terms = models.CharField(max_length=100, blank=True)
    lead_time_days = models.IntegerField(default=7)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_total_orders(self):
        return self.purchase_orders.count()
    
    def get_active_orders(self):
        return self.purchase_orders.filter(status__in=['pending', 'confirmed', 'shipped']).count()


class Warehouse(models.Model):
    """Warehouse model for inventory management."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_warehouses'
    )
    capacity = models.IntegerField(default=0, help_text="Total capacity in units")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_total_inventory(self):
        return self.inventory_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
    
    def get_utilization_percentage(self):
        if self.capacity == 0:
            return 0
        total = self.get_total_inventory()
        return min(100, (total / self.capacity) * 100)


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
    short_description = models.CharField(max_length=500, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.name
    
    def get_discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            discount = ((self.compare_price - self.price) / self.compare_price) * 100
            return round(discount, 1)
        return 0
    
    def get_average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return reviews.aggregate(avg=models.Avg('rating'))['avg']
        return 0
    
    def get_review_count(self):
        return self.reviews.filter(is_approved=True).count()
    
    def get_total_stock(self):
        return self.inventory_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
    
    def is_in_stock(self):
        return self.get_total_stock() > 0
    
    def get_primary_image(self):
        image = self.images.filter(is_primary=True).first()
        if not image:
            image = self.images.first()
        return image


class ProductVariant(models.Model):
    """Product variant model (size, color, etc.)."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    attributes = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
    def get_effective_price(self):
        return self.price if self.price else self.product.price


class ProductImage(models.Model):
    """Product image model."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductReview(models.Model):
    """Product review model."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    helpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}/5)"


class Inventory(models.Model):
    """Inventory model tracking stock levels per warehouse."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_items')
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='inventory_items'
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_items')
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
        app_label = 'auth'
        unique_together = ['product', 'variant', 'warehouse']
        verbose_name_plural = 'Inventories'
    
    def __str__(self):
        return f"{self.product.name} at {self.warehouse.name}: {self.quantity}"
    
    def get_available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)
    
    def needs_reorder(self):
        return self.quantity <= self.reorder_point
    
    def reserve_stock(self, quantity: int) -> bool:
        """Reserve stock for an order."""
        if self.get_available_quantity() >= quantity:
            self.reserved_quantity += quantity
            self.save()
            return True
        return False
    
    def release_reservation(self, quantity: int):
        """Release reserved stock."""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        self.save()
    
    def deduct_stock(self, quantity: int) -> bool:
        """Deduct stock after order fulfillment."""
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.reserved_quantity = max(0, self.reserved_quantity - quantity)
            self.save()
            return True
        return False
    
    def add_stock(self, quantity: int):
        """Add stock to inventory."""
        self.quantity += quantity
        self.save()


class InventoryTransaction(models.Model):
    """Track all inventory movements."""
    
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase Receipt'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Manual Adjustment'),
        ('transfer', 'Warehouse Transfer'),
        ('damage', 'Damage/Loss'),
        ('count', 'Stock Count'),
    ]
    
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.transaction_type} - {self.quantity} units - {self.created_at}"


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
            return f"Cart for {self.user.username}"
        return f"Anonymous Cart {self.session_key}"
    
    def get_total_items(self):
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    def get_subtotal(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.get_total_price()
        return total
    
    def get_total_with_tax(self):
        subtotal = self.get_subtotal()
        tax = sum(
            item.product.tax_rate * item.get_total_price() / 100 
            for item in self.items.all()
        )
        return subtotal + Decimal(str(tax))
    
    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    """Cart item model."""
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
        unique_together = ['cart', 'product', 'variant']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    def get_unit_price(self):
        if self.variant and self.variant.price:
            return self.variant.price
        return self.product.price
    
    def get_total_price(self):
        return self.get_unit_price() * self.quantity


class Coupon(models.Model):
    """Discount coupon model."""
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    per_user_limit = models.IntegerField(default=1)
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
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        return True, "Valid"
    
    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        if order_amount < self.minimum_order_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = order_amount * self.discount_value / 100
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
        elif self.discount_type == 'fixed':
            discount = min(self.discount_value, order_amount)
        else:
            discount = Decimal('0.00')
        
        return discount


class Order(models.Model):
    """Sales order model."""
    
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
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Address
    shipping_address = models.ForeignKey(
        Address, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='shipping_orders'
    )
    billing_address = models.ForeignKey(
        Address, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='billing_orders'
    )
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Coupon
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Shipping
    shipping_method = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        import random
        import string
        prefix = 'ORD'
        timestamp = datetime.now().strftime('%Y%m%d')
        random_part = ''.join(random.choices(string.digits, k=6))
        return f"{prefix}-{timestamp}-{random_part}"
    
    def get_item_count(self):
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    def can_cancel(self):
        return self.status in ['pending', 'confirmed']
    
    def can_return(self):
        return self.status == 'delivered'
    
    def update_status(self, new_status: str, user=None):
        old_status = self.status
        self.status = new_status
        
        now = timezone.now()
        if new_status == 'confirmed':
            self.confirmed_at = now
        elif new_status == 'shipped':
            self.shipped_at = now
        elif new_status == 'delivered':
            self.delivered_at = now
        elif new_status == 'cancelled':
            self.cancelled_at = now
        
        self.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=user
        )


class OrderItem(models.Model):
    """Order item model."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=500)
    product_sku = models.CharField(max_length=100)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        verbose_name_plural = 'Order Status Histories'
    
    def __str__(self):
        return f"Order #{self.order.order_number}: {self.old_status} -> {self.new_status}"


class Payment(models.Model):
    """Payment model."""
    
    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('wallet', 'Digital Wallet'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"Payment {self.transaction_id} for Order #{self.order.order_number}"


class PurchaseOrder(models.Model):
    """Purchase order model for inventory replenishment."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed by Supplier'),
        ('shipped', 'Shipped'),
        ('partially_received', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Dates
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    # References
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Approval
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_pos')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_pos')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PO #{self.po_number}"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = self.generate_po_number()
        self.calculate_totals()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_po_number():
        import random
        import string
        prefix = 'PO'
        timestamp = datetime.now().strftime('%Y%m%d')
        random_part = ''.join(random.choices(string.digits, k=6))
        return f"{prefix}-{timestamp}-{random_part}"
    
    def calculate_totals(self):
        items = self.items.all() if self.pk else []
        self.subtotal = sum(item.total_price for item in items)
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost
    
    def approve(self, user):
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def receive_items(self, received_items: Dict[int, int], user=None):
        """Process received items from supplier."""
        all_received = True
        
        for item_id, received_qty in received_items.items():
            try:
                po_item = self.items.get(id=item_id)
                po_item.received_quantity += received_qty
                po_item.save()
                
                # Update inventory
                inventory, created = Inventory.objects.get_or_create(
                    product=po_item.product,
                    variant=po_item.variant,
                    warehouse=self.warehouse,
                    defaults={
                        'quantity': 0,
                        'reorder_point': 10,
                        'reorder_quantity': 50,
                    }
                )
                
                old_qty = inventory.quantity
                inventory.add_stock(received_qty)
                
                # Record transaction
                InventoryTransaction.objects.create(
                    inventory=inventory,
                    transaction_type='purchase',
                    quantity=received_qty,
                    quantity_before=old_qty,
                    quantity_after=inventory.quantity,
                    reference_id=self.po_number,
                    reference_type='purchase_order',
                    performed_by=user
                )
                
                if po_item.received_quantity < po_item.quantity:
                    all_received = False
                    
            except PurchaseOrderItem.DoesNotExist:
                continue
        
        if all_received:
            self.status = 'received'
            self.actual_delivery_date = timezone.now().date()
        else:
            self.status = 'partially_received'
        
        self.save()


class PurchaseOrderItem(models.Model):
    """Purchase order line item."""
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    received_quantity = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_cost * self.quantity
        super().save(*args, **kwargs)
    
    def get_pending_quantity(self):
        return self.quantity - self.received_quantity


class Wishlist(models.Model):
    """User wishlist model."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"Wishlist for {self.user.username}"


class WishlistItem(models.Model):
    """Wishlist item model."""
    
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        unique_together = ['wishlist', 'product']
    
    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.username}'s wishlist"


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
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    reference_id = models.CharField(max_length=100, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"


class ShippingMethod(models.Model):
    """Shipping method model."""
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True)
    base_cost = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_delivery_days = models.IntegerField(default=1)
    max_delivery_days = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return self.name
    
    def calculate_cost(self, weight: Decimal = Decimal('0')) -> Decimal:
        return self.base_cost + (self.cost_per_kg * weight)


class ReturnRequest(models.Model):
    """Return request model."""
    
    REASON_CHOICES = [
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_as_described', 'Not as Described'),
        ('changed_mind', 'Changed Mind'),
        ('damaged', 'Damaged in Shipping'),
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
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'auth'
    
    def __str__(self):
        return f"Return Request for Order #{self.order.order_number}"


# ============================================================
# SERVICE CLASSES
# ============================================================

class UserService:
    """Service class for user management operations."""
    
    @staticmethod
    def create_user(
        username: str,
        email: str,
        password: str,
        first_name: str = '',
        last_name: str = '',
        role: str = 'customer'
    ) -> User:
        """Create a new user with profile."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        UserProfile.objects.create(
            user=user,
            role=role
        )
        
        # Create empty cart and wishlist
        Cart.objects.create(user=user)
        Wishlist.objects.create(user=user)
        
        return user
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        from django.contrib.auth import authenticate
        return authenticate(username=username, password=password)
    
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
    def add_address(user: User, address_data: Dict) -> Address:
        """Add a new address for user."""
        if address_data.get('is_default'):
            user.addresses.update(is_default=False)
        
        return Address.objects.create(user=user, **address_data)
    
    @staticmethod
    def get_user_orders(user: User) -> List:
        """Get all orders for a user."""
        return list(user.orders.all().order_by('-created_at'))
    
    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> bool:
        """Change user password."""
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            return True
        return False


class ProductService:
    """Service class for product operations."""
    
    @staticmethod
    def create_product(product_data: Dict) -> Product:
        """Create a new product."""
        return Product.objects.create(**product_data)
    
    @staticmethod
    def search_products(
        query: str = '',
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        in_stock: bool = False,
        sort_by: str = 'relevance',
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """Search and filter products."""
        queryset = Product.objects.filter(status='active')
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__icontains=query)
            )
        
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                category_ids = [category.id] + [c.id for c in category.get_descendants()]
                queryset = queryset.filter(category_id__in=category_ids)
            except Category.DoesNotExist:
                pass
        
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        
        # Sort
        sort_options = {
            'price_asc': 'price',
            'price_desc': '-price',
            'newest': '-created_at',
            'name': 'name',
            'relevance': '-is_featured',
        }
        queryset = queryset.order_by(sort_options.get(sort_by, '-is_featured'))
        
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        return {
            'products': list(queryset[start:end]),
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
    @staticmethod
    def get_product_detail(product_id: int) -> Optional[Product]:
        """Get product with all related data."""
        try:
            return Product.objects.get(id=product_id, status='active')
        except Product.DoesNotExist:
            return None
    
    @staticmethod
    def get_featured_products(limit: int = 10) -> List[Product]:
        """Get featured products."""
        return list(Product.objects.filter(
            status='active',
            is_featured=True
        ).order_by('-created_at')[:limit])
    
    @staticmethod
    def get_related_products(product: Product, limit: int = 5) -> List[Product]:
        """Get related products based on category."""
        return list(Product.objects.filter(
            category=product.category,
            status='active'
        ).exclude(id=product.id)[:limit])
    
    @staticmethod
    def add_review(
        product: Product,
        user: User,
        rating: int,
        title: str,
        body: str
    ) -> ProductReview:
        """Add a product review."""
        # Check if user purchased the product
        is_verified = OrderItem.objects.filter(
            order__user=user,
            product=product,
            order__status='delivered'
        ).exists()
        
        review, created = ProductReview.objects.update_or_create(
            product=product,
            user=user,
            defaults={
                'rating': rating,
                'title': title,
                'body': body,
                'is_verified_purchase': is_verified
            }
        )
        return review
    
    @staticmethod
    def update_product_status(product: Product, status: str) -> Product:
        """Update product status."""
        product.status = status
        product.save()
        return product


class CartService:
    """Service class for shopping cart operations."""
    
    @staticmethod
    def get_or_create_cart(user: Optional[User] = None, session_key: str = '') -> Cart:
        """Get or create a cart for user or session."""
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=user)
        else:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart
    
    @staticmethod
    def add_to_cart(
        cart: Cart,
        product: Product,
        quantity: int = 1,
        variant: Optional[ProductVariant] = None
    ) -> CartItem:
        """Add item to cart."""
        if product.status != 'active':
            raise ValueError("Product is not available")
        
        # Check stock
        available_stock = product.get_total_stock()
        if available_stock < quantity:
            raise ValueError(f"Only {available_stock} items available in stock")
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > available_stock:
                raise ValueError(f"Cannot add more items. Only {available_stock} available")
            cart_item.quantity = new_quantity
            cart_item.save()
        
        return cart_item
    
    @staticmethod
    def update_cart_item(cart_item: CartItem, quantity: int) -> CartItem:
        """Update cart item quantity."""
        if quantity <= 0:
            cart_item.delete()
            return None
        
        available_stock = cart_item.product.get_total_stock()
        if quantity > available_stock:
            raise ValueError(f"Only {available_stock} items available")
        
        cart_item.quantity = quantity
        cart_item.save()
        return cart_item
    
    @staticmethod
    def remove_from_cart(cart_item: CartItem):
        """Remove item from cart."""
        cart_item.delete()
    
    @staticmethod
    def apply_coupon(cart: Cart, coupon_code: str) -> Dict:
        """Apply coupon to cart."""
        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            return {'success': False, 'message': 'Invalid coupon code'}
        
        is_valid, message = coupon.is_valid()
        if not is_valid:
            return {'success': False, 'message': message}
        
        subtotal = cart.get_subtotal()
        if subtotal < coupon.minimum_order_amount:
            return {
                'success': False,
                'message': f'Minimum order amount is ${coupon.minimum_order_amount}'
            }
        
        discount = coupon.calculate_discount(subtotal)
        return {
            'success': True,
            'coupon': coupon,
            'discount': discount,
            'message': f'Coupon applied! You save ${discount}'
        }
    
    @staticmethod
    def merge_carts(anonymous_cart: Cart, user_cart: Cart):
        """Merge anonymous cart into user cart after login."""
        for item in anonymous_cart.items.all():
            try:
                CartService.add_to_cart(user_cart, item.product, item.quantity, item.variant)
            except ValueError:
                pass
        anonymous_cart.delete()


class OrderService:
    """Service class for order management."""
    
    @staticmethod
    def create_order(
        user: User,
        cart: Cart,
        shipping_address: Address,
        billing_address: Address,
        shipping_method: ShippingMethod,
        coupon: Optional[Coupon] = None,
        customer_notes: str = ''
    ) -> Order:
        """Create an order from cart."""
        if not cart.items.exists():
            raise ValueError("Cart is empty")
        
        subtotal = cart.get_subtotal()
        shipping_cost = shipping_method.calculate_cost()
        
        # Calculate tax
        tax_amount = Decimal('0.00')
        for item in cart.items.all():
            tax_amount += item.product.tax_rate * item.get_total_price() / 100
        
        # Apply coupon
        discount_amount = Decimal('0.00')
        if coupon:
            is_valid, _ = coupon.is_valid()
            if is_valid:
                discount_amount = coupon.calculate_discount(subtotal)
        
        total_amount = subtotal + shipping_cost + tax_amount - discount_amount
        
        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            billing_address=billing_address,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            coupon=coupon,
            shipping_method=shipping_method.name,
            customer_notes=customer_notes,
            estimated_delivery=timezone.now().date() + timedelta(days=shipping_method.max_delivery_days)
        )
        
        # Create order items and reserve inventory
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                quantity=cart_item.quantity,
                unit_price=cart_item.get_unit_price()
            )
            
            # Reserve inventory
            inventory_items = cart_item.product.inventory_items.filter(
                quantity__gte=cart_item.quantity
            ).order_by('-quantity')
            
            remaining = cart_item.quantity
            for inv in inventory_items:
                if remaining <= 0:
                    break
                to_reserve = min(remaining, inv.get_available_quantity())
                if to_reserve > 0:
                    inv.reserve_stock(to_reserve)
                    remaining -= to_reserve
        
        # Update coupon usage
        if coupon:
            coupon.usage_count += 1
            coupon.save()
        
        # Clear cart
        cart.clear()
        
        # Send notification
        Notification.objects.create(
            user=user,
            notification_type='order_update',
            title='Order Placed Successfully',
            message=f'Your order #{order.order_number} has been placed successfully.',
            reference_id=str(order.id),
            reference_type='order'
        )
        
        return order
    
    @staticmethod
    def cancel_order(order: Order, user: User, reason: str = '') -> bool:
        """Cancel an order."""
        if not order.can_cancel():
            return False
        
        # Release inventory reservations
        for item in order.items.all():
            inventory_items = item.product.inventory_items.all()
            for inv in inventory_items:
                inv.release_reservation(item.quantity)
        
        order.update_status('cancelled', user)
        
        # Notify user
        Notification.objects.create(
            user=order.user,
            notification_type='order_update',
            title='Order Cancelled',
            message=f'Your order #{order.order_number} has been cancelled.',
            reference_id=str(order.id),
            reference_type='order'
        )
        
        return True
    
    @staticmethod
    def process_payment(order: Order, payment_method: str, amount: Decimal) -> Payment:
        """Process payment for an order."""
        import random
        import string
        
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        
        payment = Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount,
            status='completed',
            transaction_id=transaction_id
        )
        
        order.payment_status = 'paid'
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        order.save()
        
        return payment
    
    @staticmethod
    def fulfill_order(order: Order, user: User) -> bool:
        """Fulfill an order - deduct inventory."""
        if order.status not in ['confirmed', 'processing']:
            return False
        
        for item in order.items.all():
            inventory_items = item.product.inventory_items.filter(
                reserved_quantity__gte=item.quantity
            )
            
            remaining = item.quantity
            for inv in inventory_items:
                if remaining <= 0:
                    break
                to_deduct = min(remaining, inv.reserved_quantity)
                if inv.deduct_stock(to_deduct):
                    old_qty = inv.quantity + to_deduct
                    InventoryTransaction.objects.create(
                        inventory=inv,
                        transaction_type='sale',
                        quantity=-to_deduct,
                        quantity_before=old_qty,
                        quantity_after=inv.quantity,
                        reference_id=order.order_number,
                        reference_type='sales_order',
                        performed_by=user
                    )
                    remaining -= to_deduct
        
        order.update_status('processing', user)
        return True
    
    @staticmethod
    def ship_order(order: Order, tracking_number: str, user: User) -> bool:
        """Mark order as shipped."""
        if order.status != 'processing':
            return False
        
        order.tracking_number = tracking_number
        order.save()
        order.update_status('shipped', user)
        
        Notification.objects.create(
            user=order.user,
            notification_type='order_update',
            title='Order Shipped',
            message=f'Your order #{order.order_number} has been shipped. Tracking: {tracking_number}',
            reference_id=str(order.id),
            reference_type='order'
        )
        
        return True
    
    @staticmethod
    def create_return_request(
        order: Order,
        order_item: OrderItem,
        user: User,
        reason: str,
        description: str,
        quantity: int
    ) -> ReturnRequest:
        """Create a return request."""
        if not order.can_return():
            raise ValueError("Order cannot be returned")
        
        if quantity > order_item.quantity:
            raise ValueError("Return quantity exceeds ordered quantity")
        
        return ReturnRequest.objects.create(
            order=order,
            order_item=order_item,
            user=user,
            reason=reason,
            description=description,
            quantity=quantity,
            refund_amount=order_item.unit_price * quantity
        )


class InventoryService:
    """Service class for inventory management."""
    
    @staticmethod
    def create_inventory(
        product: Product,
        warehouse: Warehouse,
        quantity: int = 0,
        variant: Optional[ProductVariant] = None,
        **kwargs
    ) -> Inventory:
        """Create inventory record."""
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            variant=variant,
            defaults={'quantity': quantity, **kwargs}
        )
        
        if not created and quantity > 0:
            inventory.add_stock(quantity)
        
        return inventory
    
    @staticmethod
    def adjust_inventory(
        inventory: Inventory,
        adjustment: int,
        reason: str,
        user: User,
        notes: str = ''
    ) -> InventoryTransaction:
        """Manually adjust inventory."""
        old_qty = inventory.quantity
        new_qty = max(0, old_qty + adjustment)
        inventory.quantity = new_qty
        inventory.save()
        
        return InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type='adjustment',
            quantity=adjustment,
            quantity_before=old_qty,
            quantity_after=new_qty,
            notes=f"{reason}: {notes}",
            performed_by=user
        )
    
    @staticmethod
    def transfer_inventory(
        product: Product,
        from_warehouse: Warehouse,
        to_warehouse: Warehouse,
        quantity: int,
        user: User,
        variant: Optional[ProductVariant] = None
    ) -> bool:
        """Transfer inventory between warehouses."""
        try:
            from_inventory = Inventory.objects.get(
                product=product,
                warehouse=from_warehouse,
                variant=variant
            )
        except Inventory.DoesNotExist:
            return False
        
        if from_inventory.get_available_quantity() < quantity:
            return False
        
        # Deduct from source
        old_from_qty = from_inventory.quantity
        from_inventory.quantity -= quantity
        from_inventory.save()
        
        InventoryTransaction.objects.create(
            inventory=from_inventory,
            transaction_type='transfer',
            quantity=-quantity,
            quantity_before=old_from_qty,
            quantity_after=from_inventory.quantity,
            reference_id=f"TRANSFER-{from_warehouse.code}-{to_warehouse.code}",
            reference_type='warehouse_transfer',
            performed_by=user
        )
        
        # Add to destination
        to_inventory, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=to_warehouse,
            variant=variant,
            defaults={'quantity': 0}
        )
        
        old_to_qty = to_inventory.quantity
        to_inventory.quantity += quantity
        to_inventory.save()
        
        InventoryTransaction.objects.create(
            inventory=to_inventory,
            transaction_type='transfer',
            quantity=quantity,
            quantity_before=old_to_qty,
            quantity_after=to_inventory.quantity,
            reference_id=f"TRANSFER-{from_warehouse.code}-{to_warehouse.code}",
            reference_type='warehouse_transfer',
            performed_by=user
        )
        
        return True
    
    @staticmethod
    def get_low_stock_items(threshold: Optional[int] = None) -> List[Inventory]:
        """Get items that need reordering."""
        if threshold:
            return list(Inventory.objects.filter(quantity__lte=threshold))
        return list(Inventory.objects.filter(
            quantity__lte=models.F('reorder_point')
        ))
    
    @staticmethod
    def perform_stock_count(
        warehouse: Warehouse,
        count_data: Dict[int, int],
        user: User
    ) -> List[InventoryTransaction]:
        """Perform a physical stock count."""
        transactions = []
        
        for inventory_id, actual_count in count_data.items():
            try:
                inventory = Inventory.objects.get(id=inventory_id, warehouse=warehouse)
                old_qty = inventory.quantity
                
                if old_qty != actual_count:
                    adjustment = actual_count - old_qty
                    inventory.quantity = actual_count
                    inventory.last_counted_at = timezone.now()
                    inventory.save()
                    
                    transaction = InventoryTransaction.objects.create(
                        inventory=inventory,
                        transaction_type='count',
                        quantity=adjustment,
                        quantity_before=old_qty,
                        quantity_after=actual_count,
                        notes=f"Stock count adjustment",
                        performed_by=user
                    )
                    transactions.append(transaction)
                    
            except Inventory.DoesNotExist:
                continue
        
        return transactions
    
    @staticmethod
    def create_purchase_order(
        supplier: Supplier,
        warehouse: Warehouse,
        items: List[Dict],
        created_by: User,
        expected_delivery_date=None,
        notes: str = ''
    ) -> PurchaseOrder:
        """Create a purchase order."""
        po = PurchaseOrder.objects.create(
            supplier=supplier,
            warehouse=warehouse,
            created_by=created_by,
            expected_delivery_date=expected_delivery_date,
            notes=notes
        )
        
        for item_data in items:
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=item_data['product'],
                variant=item_data.get('variant'),
                quantity=item_data['quantity'],
                unit_cost=item_data['unit_cost']
            )
        
        po.calculate_totals()
        po.save()
        
        return po
    
    @staticmethod
    def get_inventory_report(warehouse: Optional[Warehouse] = None) -> Dict:
        """Generate inventory report."""
        queryset = Inventory.objects.all()
        if warehouse:
            queryset = queryset.filter(warehouse=warehouse)
        
        total_items = queryset.count()
        total_quantity = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        low_stock_count = queryset.filter(quantity__lte=models.F('reorder_point')).count()
        out_of_stock_count = queryset.filter(quantity=0).count()
        
        return {
            'total_items': total_items,
            'total_quantity': total_quantity,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'low_stock_items': list(queryset.filter(
                quantity__lte=models.F('reorder_point')
            ).select_related('product', 'warehouse')[:20])
        }


class AdminDashboardService:
    """Service class for admin dashboard operations."""
    
    @staticmethod
    def get_sales_summary(days: int = 30) -> Dict:
        """Get sales summary for the last N days."""
        start_date = timezone.now() - timedelta(days=days)
        
        orders = Order.objects.filter(
            created_at__gte=start_date,
            status__in=['confirmed', 'processing', 'shipped', 'delivered']
        )
        
        total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        total_orders = orders.count()
        avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
        
        return {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'average_order_value': avg_order_value,
            'period_days': days
        }
    
    @staticmethod
    def get_top_products(limit: int = 10) -> List[Dict]:
        """Get top selling products."""
        from django.db.models import Count
        
        top_items = OrderItem.objects.values(
            'product__id',
            'product__name'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_sold')[:limit]
        
        return list(top_items)
    
    @staticmethod
    def get_user_statistics() -> Dict:
        """Get user statistics."""
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_today = User.objects.filter(
            date_joined__date=timezone.now().date()
        ).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users_today': new_users_today
        }
    
    @staticmethod
    def get_order_statistics() -> Dict:
        """Get order statistics."""
        from django.db.models import Count
        
        stats = Order.objects.values('status').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        return {item['status']: {'count': item['count'], 'total': item['total']} 
                for item in stats}
    
    @staticmethod
    def get_inventory_alerts() -> Dict:
        """Get inventory alerts."""
        low_stock = Inventory.objects.filter(
            quantity__lte=models.F('reorder_point'),
            quantity__gt=0
        ).count()
        
        out_of_stock = Inventory.objects.filter(quantity=0).count()
        
        pending_pos = PurchaseOrder.objects.filter(
            status__in=['pending', 'approved', 'sent']
        ).count()
        
        return {
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
            'pending_purchase_orders': pending_pos
        }


class WishlistService:
    """Service class for wishlist operations."""
    
    @staticmethod
    def add_to_wishlist(user: User, product: Product) -> WishlistItem:
        """Add product to wishlist."""
        wishlist, _ = Wishlist.objects.get_or_create(user=user)
        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product
        )
        return item
    
    @staticmethod
    def remove_from_wishlist(user: User, product: Product) -> bool:
        """Remove product from wishlist."""
        try:
            wishlist = user.wishlist
            WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()
            return True
        except Wishlist.DoesNotExist:
            return False
    
    @staticmethod
    def get_wishlist(user: User) -> List[WishlistItem]:
        """Get user's wishlist items."""
        try:
            return list(user.wishlist.items.select_related('product').all())
        except Wishlist.DoesNotExist:
            return []
    
    @staticmethod
    def move_to_cart(user: User, product: Product) -> bool:
        """Move wishlist item to cart."""
        try:
            cart = user.cart
            CartService.add_to_cart(cart, product)
            WishlistService.remove_from_wishlist(user, product)
            return True
        except (Cart.DoesNotExist, ValueError):
            return False


class NotificationService:
    """Service class for notifications."""
    
    @staticmethod
    def send_notification(
        user: User,
        notification_type: str,
        title: str,
        message: str,
        reference_id: str = '',
        reference_type: str = ''
    ) -> Notification:
        """Send a notification to a user."""
        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            reference_id=reference_id,
            reference_type=reference_type
        )
    
    @staticmethod
    def mark_as_read(notification: Notification):
        """Mark notification as read."""
        notification.is_read = True
        notification.save()
    
    @staticmethod
    def mark_all_as_read(user: User):
        """Mark all notifications as read."""
        user.notifications.filter(is_read=False).update(is_read=True)
    
    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get unread notification count."""
        return user.notifications.filter(is_read=False).count()


# ============================================================
# DEMO / TESTING
# ============================================================

def create_tables():
    """Create all database tables."""
    from django.db import connection
    
    models_to_create = [
        UserProfile,
        Address,
        Category,
        Brand,
        Supplier,
        Warehouse,
        Product,
        ProductVariant,
        ProductImage,
        ProductReview,
        Inventory,
        InventoryTransaction,
        Cart,
        CartItem,
        Coupon,
        Order,
        OrderItem,
        OrderStatusHistory,
        Payment,
        PurchaseOrder,
        PurchaseOrderItem,
        Wishlist,
        WishlistItem,
        Notification,
        ShippingMethod,
        ReturnRequest,
    ]
    
    with connection.schema_editor() as schema_editor:
        for model in models_to_create:
            try:
                schema_editor.create_model(model)
                print(f"Created table for {model.__name__}")
            except Exception as e:
                if 'already exists' not in str(e).lower():
                    print(f"Error creating {model.__name__}: {e}")


def run_demo():
    """Run a comprehensive demo of the Amazon clone system."""
    print("=" * 60)
    print("AMAZON CLONE - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    # Create tables
    print("\n[1] Creating database tables...")
    create_tables()
    
    # ---- User Management ----
    print("\n[2] User Management Demo")
    print("-" * 40)
    
    # Create admin user
    try:
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@amazonclone.com',
            password='admin123'
        )
        UserProfile.objects.create(user=admin_user, role='admin')
        Cart.objects.create(user=admin_user)
        Wishlist.objects.create(user=admin_user)
        print(f"Created admin user: {admin_user.username}")
    except Exception:
        admin_user = User.objects.get(username='admin')
        print(f"Admin user already exists: {admin_user.username}")
    
    # Create customer
    try:
        customer = UserService.create_user(
            username='john_doe',
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            role='customer'
        )
        print(f"Created customer: {customer.username}")
    except Exception:
        customer = User.objects.get(username='john_doe')
        print(f"Customer already exists: {customer.username}")
    
    # Create seller
    try:
        seller = UserService.create_user(
            username='seller_jane',
            email='jane@seller.com',
            password='password123',
            first_name='Jane',
            last_name='Smith',
            role='seller'
        )
        print(f"Created seller: {seller.username}")
    except Exception:
        seller = User.objects.get(username='seller_jane')
        print(f"Seller already exists: {seller.username}")
    
    # Add address
    try:
        address = UserService.add_address(customer, {
            'address_type': 'home',
            'full_name': 'John Doe',
            'street_address1': '123 Main Street',
            'city': 'New York',
            'state': 'NY',
            'postal_code': '10001',
            'country': 'United States',
            'phone': '555-1234',
            'is_default': True
        })
        print(f"Added address: {address.get_full_address()}")
    except Exception as e:
        address = customer.addresses.first()
        if address:
            print(f"Address already exists: {address.get_full_address()}")
    
    # ---- Category Setup ----
    print("\n[3] Category Setup")
    print("-" * 40)
    
    categories_data = [
        {'name': 'Electronics', 'slug': 'electronics'},
        {'name': 'Books', 'slug': 'books'},
        {'name': 'Clothing', 'slug': 'clothing'},
        {'name': 'Home & Garden', 'slug': 'home-garden'},
    ]
    
    categories = {}
    for cat_data in categories_data:
        cat, created = Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        categories[cat_data['slug']] = cat
        if created:
            print(f"Created category: {cat.name}")
    
    # Sub-categories
    sub_cats_data = [
        {'name': 'Smartphones', 'slug': 'smartphones', 'parent': categories['electronics']},
        {'name': 'Laptops', 'slug': 'laptops', 'parent': categories['electronics']},
        {'name': 'Fiction', 'slug': 'fiction', 'parent': categories['books']},
        {'name': 'Men\'s Clothing', 'slug': 'mens-clothing', 'parent': categories['clothing']},
    ]
    
    for sub_data in sub_cats_data:
        sub, created = Category.objects.get_or_create(
            slug=sub_data['slug'],
            defaults=sub_data
        )
        if created:
            print(f"Created sub-category: {sub.name} (Level {sub.get_level()})")
    
    # ---- Brand Setup ----
    print("\n[4] Brand Setup")
    print("-" * 40)
    
    brands_data = [
        {'name': 'Apple', 'slug': 'apple'},
        {'name': 'Samsung', 'slug': 'samsung'},
        {'name': 'Sony', 'slug': 'sony'},
        {'name': 'Nike', 'slug': 'nike'},
    ]
    
    brands = {}
    for brand_data in brands_data:
        brand, created = Brand.objects.get_or_create(
            slug=brand_data['slug'],
            defaults=brand_data
        )
        brands[brand_data['slug']] = brand
        if created:
            print(f"Created brand: {brand.name}")
    
    # ---- Supplier Setup ----
    print("\n[5] Supplier Setup")
    print("-" * 40)
    
    try:
        supplier = Supplier.objects.create(
            name='Tech Supplies Inc.',
            code='TSI-001',
            email='orders@techsupplies.com',
            phone='555-9876',
            address='456 Industrial Ave',
            city='San Francisco',
            state='CA',
            country='United States',
            postal_code='94102',
            contact_person='Bob Johnson',
            payment_terms='Net 30',
            lead_time_days=5
        )
        print(f"Created supplier: {supplier.name}")
    except Exception:
        supplier = Supplier.objects.get(code='TSI-001')
        print(f"Supplier already exists: {supplier.name}")
    
    # ---- Warehouse Setup ----
    print("\n[6] Warehouse Setup")
    print("-" * 40)
    
    try:
        warehouse = Warehouse.objects.create(
            name='Main Distribution Center',
            code='WH-MAIN',
            address='789 Warehouse Blvd',
            city='Chicago',
            state='IL',
            country='United States',
            postal_code='60601',
            manager=admin_user,
            capacity=100000,
            phone='555-5678',
            email='warehouse@amazonclone.com'
        )
        print(f"Created warehouse: {warehouse.name}")
    except Exception:
        warehouse = Warehouse.objects.get(code='WH-MAIN')
        print(f"Warehouse already exists: {warehouse.name}")
    
    try:
        warehouse2 = Warehouse.objects.create(
            name='East Coast Fulfillment Center',
            code='WH-EAST',
            address='321 Fulfillment Dr',
            city='Newark',
            state='NJ',
            country='United States',
            postal_code='07101',
            capacity=75000
        )
        print(f"Created warehouse: {warehouse2.name}")
    except Exception:
        warehouse2 = Warehouse.objects.get(code='WH-EAST')
        print(f"Warehouse already exists: {warehouse2.name}")
    
    # ---- Product Setup ----
    print("\n[7] Product Setup")
    print("-" * 40)
    
    smartphones_cat = Category.objects.get(slug='smartphones')
    laptops_cat = Category.objects.get(slug='laptops')
    
    products_data = [
        {
            'name': 'iPhone 15 Pro',
            'slug': 'iphone-15-pro',
            'sku': 'APPL-IP15P-001',
            'description': 'The latest iPhone with A17 Pro chip, titanium design, and advanced camera system.',
            'short_description': 'Apple iPhone 15 Pro - 256GB',
            'category': smartphones_cat,
            'brand': brands['apple'],
            'seller': seller,
            'price': Decimal('999.99'),
            'compare_price': Decimal('1099.99'),
            'cost_price': Decimal('650.00'),
            'weight': Decimal('0.187'),
            'status': 'active',
            'is_featured': True,
            'tax_rate': Decimal('8.5'),
        },
        {
            'name': 'Samsung Galaxy S24 Ultra',
            'slug': 'samsung-galaxy-s24-ultra',
            'sku': 'SAMS-GS24U-001',
            'description': 'Samsung\'s flagship smartphone with S Pen, 200MP camera, and AI features.',
            'short_description': 'Samsung Galaxy S24 Ultra - 512GB',
            'category': smartphones_cat,
            'brand': brands['samsung'],
            'seller': seller,
            'price': Decimal('1199.99'),
            'compare_price': Decimal('1299.99'),
            'cost_price': Decimal('750.00'),
            'weight': Decimal('0.232'),
            'status': 'active',
            'is_featured': True,
            'tax_rate': Decimal('8.5'),
        },
        {
            'name': 'MacBook Pro 14"',
            'slug': 'macbook-pro-14',
            'sku': 'APPL-MBP14-001',
            'description': 'MacBook Pro with M3 Pro chip, Liquid Retina XDR display.',
            'short_description': 'Apple MacBook Pro 14" M3 Pro',
            'category': laptops_cat,
            'brand': brands['apple'],
            'seller': seller,
            'price': Decimal('1999.99'),
            'compare_price': Decimal('2199.99'),
            'cost_price': Decimal('1300.00'),
            'weight': Decimal('1.55'),
            'status': 'active',
            'is_featured': True,
            'tax_rate': Decimal('8.5'),
        },
    ]
    
    products = {}
    for prod_data in products_data:
        prod, created = Product.objects.get_or_create(
            sku=prod_data['sku'],
            defaults=prod_data
        )
        products[prod_data['sku']] = prod
        if created:
            print(f"Created product: {prod.name} - ${prod.price}")
            
            # Add product image
            ProductImage.objects.create(
                product=prod,
                image_url=f"https://example.com/images/{prod.slug}.jpg",
                alt_text=prod.name,
                is_primary=True
            )
    
    # ---- Inventory Setup ----
    print("\n[8] Inventory Setup")
    print("-" * 40)
    
    for sku, product in products.items():
        inv = InventoryService.create_inventory(
            product=product,
            warehouse=warehouse,
            quantity=100,
            reorder_point=20,
            reorder_quantity=50,
            max_stock_level=500
        )
        print(f"Inventory for {product.name}: {inv.quantity} units at {warehouse.name}")
        
        # Also add to second warehouse
        inv2 = InventoryService.create_inventory(
            product=product,
            warehouse=warehouse2,
            quantity=50,
            reorder_point=10,
            reorder_quantity=30
        )
        print(f"Inventory for {product.name}: {inv2.quantity} units at {warehouse2.name}")
    
    # ---- Purchase Order Demo ----
    print("\n[9] Purchase Order Demo")
    print("-" * 40)
    
    iphone = products.get('APPL-IP15P-001')
    samsung = products.get('SAMS-GS24U-001')
    
    if iphone and samsung:
        po = InventoryService.create_purchase_order(
            supplier=supplier,
            warehouse=warehouse,
            items=[
                {'product': iphone, 'quantity': 50, 'unit_cost': Decimal('650.00')},
                {'product': samsung, 'quantity': 30, 'unit_cost': Decimal('750.00')},
            ],
            created_by=admin_user,
            expected_delivery_date=(timezone.now() + timedelta(days=7)).date(),
            notes='Regular stock replenishment'
        )
        print(f"Created Purchase Order: {po.po_number}")
        print(f"  Supplier: {po.supplier.name}")
        print(f"  Total Amount: ${po.total_amount}")
        print(f"  Status: {po.status}")
        
        # Approve PO
        po.approve(admin_user)
        print(f"  Approved by: {po.approved_by.username}")
        
        # Receive items
        items = list(po.items.all())
        if items:
            received = {items[0].id: 25, items[1].id: 15}
            po.receive_items(received, admin_user)
            print(f"  Partially received items. New status: {po.status}")
    
    # ---- Shopping Cart Demo ----
    print("\n[10] Shopping Cart Demo")
    print("-" * 40)
    
    cart = CartService.get_or_create_cart(user=customer)
    
    if iphone:
        cart_item = CartService.add_to_cart(cart, iphone, quantity=1)
        print(f"Added to cart: {cart_item.product.name} x{cart_item.quantity}")
    
    if samsung:
        cart_item2 = CartService.add_to_cart(cart, samsung, quantity=2)
        print(f"Added to cart: {cart_item2.product.name} x{cart_item2.quantity}")
    
    print(f"Cart total items: {cart.get_total_items()}")
    print(f"Cart subtotal: ${cart.get_subtotal()}")
    
    # ---- Coupon Demo ----
    print("\n[11] Coupon Demo")
    print("-" * 40)
    
    coupon, created = Coupon.objects.get_or_create(
        code='SAVE10',
        defaults={
            'description': '10% off on all orders',
            'discount_type': 'percentage',
            'discount_value': Decimal('10'),
            'minimum_order_amount': Decimal('100'),
            'usage_limit': 1000,
            'per_user_limit': 1,
            'valid_from': timezone.now() - timedelta(days=1),
            'valid_until': timezone.now() + timedelta(days=30),
        }
    )
    
    if created:
        print(f"Created coupon: {coupon.code} - {coupon.discount_value}% off")
    
    coupon_result = CartService.apply_coupon(cart, 'SAVE10')
    print(f"Coupon application: {coupon_result['message']}")
    if coupon_result['success']:
        print(f"Discount amount: ${coupon_result['discount']}")
    
    # ---- Shipping Method ----
    print("\n[12] Shipping Methods")
    print("-" * 40)
    
    shipping_methods_data = [
        {
            'name': 'Standard Shipping',
            'code': 'STANDARD',
            'base_cost': Decimal('5.99'),
            'min_delivery_days': 5,
            'max_delivery_days': 7
        },
        {
            'name': 'Express Shipping',
            'code': 'EXPRESS',
            'base_cost': Decimal('14.99'),
            'min_delivery_days': 2,
            'max_delivery_days': 3
        },
        {
            'name': 'Same Day Delivery',
            'code': 'SAMEDAY',
            'base_cost': Decimal('29.99'),
            'min_delivery_days': 0,
            'max_delivery_days': 1
        },
    ]
    
    shipping_methods = {}
    for sm_data in shipping_methods_data:
        sm, created = ShippingMethod.objects.get_or_create(
            code=sm_data['code'],
            defaults=sm_data
        )
        shipping_methods[sm_data['code']] = sm
        if created:
            print(f"Created shipping method: {sm.name} - ${sm.base_cost}")
    
    # ---- Order Creation Demo ----
    print("\n[13] Order Creation Demo")
    print("-" * 40)
    
    customer_address = customer.addresses.first()
    
    if customer_address and cart.items.exists():
        try:
            order = OrderService.create_order(
                user=customer,
                cart=cart,
                shipping_address=customer_address,
                billing_address=customer_address,
                shipping_method=shipping_methods['EXPRESS'],
                coupon=coupon,
                customer_notes='Please leave at the door'
            )
            
            print(f"Created Order: {order.order_number}")
            print(f"  Status: {order.status}")
            print(f"  Subtotal: ${order.subtotal}")
            print(f"  Shipping: ${order.shipping_cost}")
            print(f"  Tax: ${order.tax_amount}")
            print(f"  Discount: ${order.discount_amount}")
            print(f"  Total: ${order.total_amount}")
            print(f"  Items: {order.get_item_count()}")
            
            # Process payment
            payment = OrderService.process_payment(
                order=order,
                payment_method='credit_card',
                amount=order.total_amount
            )
            print(f"  Payment processed: {payment.transaction_id}")
            print(f"  Payment status: {payment.status}")
            
            # Fulfill order
            OrderService.fulfill_order(order, admin_user)
            print(f"  Order fulfilled. Status: {order.status}")
            
            # Ship order
            OrderService.ship_order(order, 'TRACK123456789', admin_user)
            order.refresh_from_db()
            print(f"  Order shipped. Tracking: {order.tracking_number}")
            
        except Exception as e:
            print(f"Order creation error: {e}")
    else:
        print("No address or cart items found for order creation")
    
    # ---- Product Review Demo ----
    print("\n[14] Product Review Demo")
    print("-" * 40)
    
    if iphone:
        review = ProductService.add_review(
            product=iphone,
            user=customer,
            rating=5,
            title='Amazing phone!',
            body='The iPhone 15 Pro is absolutely incredible. The camera is outstanding and the performance is top-notch.'
        )
        print(f"Added review: {review.title} ({review.rating}/5)")
        print(f"Average rating: {iphone.get_average_rating():.1f}/5")
    
    # ---- Wishlist Demo ----
    print("\n[15] Wishlist Demo")
    print("-" * 40)
    
    macbook = products.get('APPL-MBP14-001')
    if macbook:
        wishlist_item = WishlistService.add_to_wishlist(customer, macbook)
        print(f"Added to wishlist: {wishlist_item.product.name}")
    
    wishlist_items = WishlistService.get_wishlist(customer)
    print(f"Wishlist items: {len(wishlist_items)}")
    for item in wishlist_items:
        print(f"  - {item.product.name} (${item.product.price})")
    
    # ---- Inventory Transfer Demo ----
    print("\n[16] Inventory Transfer Demo")
    print("-" * 40)
    
    if iphone:
        success = InventoryService.transfer_inventory(
            product=iphone,
            from_warehouse=warehouse,
            to_warehouse=warehouse2,
            quantity=10,
            user=admin_user
        )
        print(f"Transfer 10 units of {iphone.name}: {'Success' if success else 'Failed'}")
        
        main_inv = Inventory.objects.get(product=iphone, warehouse=warehouse)
        east_inv = Inventory.objects.get(product=iphone, warehouse=warehouse2)
        print(f"  Main warehouse: {main_inv.quantity} units")
        print(f"  East warehouse: {east_inv.quantity} units")
    
    # ---- Inventory Report ----
    print("\n[17] Inventory Report")
    print("-" * 40)
    
    report = InventoryService.get_inventory_report()
    print(f"Total inventory items: {report['total_items']}")
    print(f"Total quantity: {report['total_quantity']}")
    print(f"Low stock items: {report['low_stock_count']}")
    print(f"Out of stock items: {report['out_of_stock_count']}")
    
    # ---- Admin Dashboard ----
    print("\n[18] Admin Dashboard")
    print("-" * 40)
    
    sales_summary = AdminDashboardService.get_sales_summary(30)
    print(f"Sales Summary (Last 30 days):")
    print(f"  Total Revenue: ${sales_summary['total_revenue']}")
    print(f"  Total Orders: {sales_summary['total_orders']}")
    print(f"  Avg Order Value: ${sales_summary['average_order_value']:.2f}")
    
    user_stats = AdminDashboardService.get_user_statistics()
    print(f"\nUser Statistics:")
    print(f"  Total Users: {user_stats['total_users']}")
    print(f"  Active Users: {user_stats['active_users']}")
    print(f"  New Today: {user_stats['new_users_today']}")
    
    order_stats = AdminDashboardService.get_order_statistics()
    print(f"\nOrder Statistics by Status:")
    for status, data in order_stats.items():
        print(f"  {status}: {data['count']} orders (${data['total'] or 0})")
    
    inventory_alerts = AdminDashboardService.get_inventory_alerts()
    print(f"\nInventory Alerts:")
    print(f"  Low Stock: {inventory_alerts['low_stock_count']}")
    print(f"  Out of Stock: {inventory_alerts['out_of_stock_count']}")
    print(f"  Pending POs: {inventory_alerts['pending_purchase_orders']}")
    
    # ---- Notification Demo ----
    print("\n[19] Notification Demo")
    print("-" * 40)
    
    notification = NotificationService.send_notification(
        user=customer,
        notification_type='promotion',
        title='Special Offer!',
        message='Get 20% off on all electronics this weekend!',
    )
    print(f"Sent notification: {notification.title}")
    
    unread_count = NotificationService.get_unread_count(customer)
    print(f"Unread notifications: {unread_count}")
    
    NotificationService.mark_all_as_read(customer)
    unread_count = NotificationService.get_unread_count(customer)
    print(f"After marking all read: {unread_count}")
    
    # ---- Product Search Demo ----
    print("\n[20] Product Search Demo")
    print("-" * 40)
    
    search_results = ProductService.search_products(
        query='iPhone',
        sort_by='price_asc'
    )
    print(f"Search 'iPhone': {search_results['total']} results")
    for prod in search_results['products']:
        print(f"  - {prod.name} (${prod.price})")
    
    search_results2 = ProductService.search_products(
        category_id=smartphones_cat.id,
        min_price=Decimal('500'),
        max_price=Decimal('1500')
    )
    print(f"\nSmartphones $500-$1500: {search_results2['total']} results")
    for prod in search_results2['products']:
        print(f"  - {prod.name} (${prod.price})")
    
    # ---- Top Products ----
    print("\n[21] Top Products")
    print("-" * 40)
    
    top_products = AdminDashboardService.get_top_products(5)
    print("Top Selling Products:")
    for item in top_products:
        print(f"  - {item['product__name']}: {item['total_sold']} sold (${item['total_revenue']})")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nSystem Summary:")
    print(f"  Users: {User.objects.count()}")
    print(f"  Products: {Product.objects.count()}")
    print(f"  Categories: {Category.objects.count()}")
    print(f"  Brands: {Brand.objects.count()}")
    print(f"  Suppliers: {Supplier.objects.count()}")
    print(f"  Warehouses: {Warehouse.objects.count()}")
    print(f"  Inventory Records: {Inventory.objects.count()}")
    print(f"  Orders: {Order.objects.count()}")
    print(f"  Purchase Orders: {PurchaseOrder.objects.count()}")
    print(f"  Reviews: {ProductReview.objects.count()}")
    print(f"  Notifications: {Notification.objects.count()}")


# ============================================================
# URL PATTERNS (for reference)
# ============================================================

urlpatterns_reference = """
URL Patterns for Amazon Clone:

# Authentication
/auth/signup/          - User registration
/auth/login/           - User login
/auth/logout/          - User logout
/auth/profile/         - User profile
/auth/profile/edit/    - Edit profile
/auth/addresses/       - Manage addresses
/auth/change-password/ - Change password

# Products
/                      - Home page with featured products
/products/             - Product listing
/products/search/      - Product search
/products/<slug>/      - Product detail
/products/<slug>/review/ - Add review
/categories/           - Category listing
/categories/<slug>/    - Category products

# Cart
/cart/                 - View cart
/cart/add/             - Add to cart
/cart/update/          - Update cart item
/cart/remove/          - Remove from cart
/cart/apply-coupon/    - Apply coupon
/cart/checkout/        - Checkout

# Orders
/orders/               - Order history
/orders/<id>/          - Order detail
/orders/<id>/cancel/   - Cancel order
/orders/<id>/return/   - Return request
/orders/<id>/track/    - Track order

# Wishlist
/wishlist/             - View wishlist
/wishlist/add/         - Add to wishlist
/wishlist/remove/      - Remove from wishlist
/wishlist/move-to-cart/ - Move to cart

# Admin
/admin/dashboard/      - Admin dashboard
/admin/products/       - Product management
/admin/orders/         - Order management
/admin/inventory/      - Inventory management
/admin/warehouses/     - Warehouse management
/admin/suppliers/      - Supplier management
/admin/purchase-orders/ - Purchase order management
/admin/users/          - User management
/admin/reports/        - Reports and analytics
"""


if __name__ == '__main__':
    run_demo()