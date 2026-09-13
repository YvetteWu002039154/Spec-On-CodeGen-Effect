#!/usr/bin/env python3
"""
Amazon Clone - Complete Django Implementation
A fully functional e-commerce platform with inventory management system
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Django settings configuration
DJANGO_SETTINGS = {
    'DEBUG': True,
    'SECRET_KEY': 'amazon-clone-secret-key-change-in-production',
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'amazon_clone.db',
        }
    },
    'INSTALLED_APPS': [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ],
    'MIDDLEWARE': [
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ],
    'TEMPLATES': [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': ['templates'],
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
    ],
    'STATIC_URL': '/static/',
    'MEDIA_URL': '/media/',
    'MEDIA_ROOT': 'media/',
    'DEFAULT_AUTO_FIELD': 'django.db.models.BigAutoField',
    'AUTH_USER_MODEL': 'auth.User',
    'LOGIN_URL': '/login/',
    'LOGIN_REDIRECT_URL': '/',
    'LOGOUT_REDIRECT_URL': '/',
}


# ============================================================
# MODELS
# ============================================================

class UserProfile:
    """Extended user profile model"""
    
    def __init__(self, user_id: int, username: str, email: str, 
                 first_name: str = '', last_name: str = '',
                 phone: str = '', address: str = '',
                 user_type: str = 'customer'):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.address = address
        self.user_type = user_type  # customer, admin, supplier, warehouse_manager
        self.is_active = True
        self.date_joined = datetime.now()
        self.last_login = None
        self.password_hash = None
        
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self) -> str:
        return f"UserProfile(id={self.user_id}, username={self.username}, type={self.user_type})"


class Category:
    """Product category model"""
    
    def __init__(self, category_id: int, name: str, description: str = '',
                 parent_id: int = None, slug: str = ''):
        self.category_id = category_id
        self.name = name
        self.description = description
        self.parent_id = parent_id  # For multi-level categories
        self.slug = slug or name.lower().replace(' ', '-')
        self.is_active = True
        self.created_at = datetime.now()
        self.children = []
        
    def add_child(self, child_category: 'Category'):
        child_category.parent_id = self.category_id
        self.children.append(child_category)
        
    def get_breadcrumb(self, all_categories: dict) -> list:
        breadcrumb = [self]
        current = self
        while current.parent_id:
            parent = all_categories.get(current.parent_id)
            if parent:
                breadcrumb.insert(0, parent)
                current = parent
            else:
                break
        return breadcrumb
    
    def __repr__(self) -> str:
        return f"Category(id={self.category_id}, name={self.name})"


class Supplier:
    """Supplier model for inventory management"""
    
    def __init__(self, supplier_id: int, name: str, email: str,
                 phone: str = '', address: str = '', 
                 contact_person: str = '', company_name: str = ''):
        self.supplier_id = supplier_id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.contact_person = contact_person
        self.company_name = company_name or name
        self.is_active = True
        self.created_at = datetime.now()
        self.rating = 0.0
        self.total_orders = 0
        self.payment_terms = 'NET30'
        self.tax_id = ''
        
    def update_rating(self, new_rating: float):
        if 0 <= new_rating <= 5:
            self.rating = new_rating
            
    def __repr__(self) -> str:
        return f"Supplier(id={self.supplier_id}, name={self.name})"


class Warehouse:
    """Warehouse model for inventory management"""
    
    def __init__(self, warehouse_id: int, name: str, location: str,
                 capacity: int = 0, manager_id: int = None):
        self.warehouse_id = warehouse_id
        self.name = name
        self.location = location
        self.capacity = capacity
        self.manager_id = manager_id
        self.is_active = True
        self.created_at = datetime.now()
        self.current_stock_count = 0
        self.zones = []
        
    def add_zone(self, zone_name: str, zone_capacity: int):
        self.zones.append({
            'name': zone_name,
            'capacity': zone_capacity,
            'current_count': 0
        })
        
    def get_available_capacity(self) -> int:
        return self.capacity - self.current_stock_count
    
    def __repr__(self) -> str:
        return f"Warehouse(id={self.warehouse_id}, name={self.name}, location={self.location})"


class Product:
    """Product model"""
    
    def __init__(self, product_id: int, name: str, description: str,
                 price: Decimal, category_id: int, sku: str = '',
                 brand: str = '', weight: float = 0.0):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = Decimal(str(price))
        self.category_id = category_id
        self.sku = sku or f"SKU-{product_id:06d}"
        self.brand = brand
        self.weight = weight
        self.is_active = True
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.images = []
        self.tags = []
        self.rating = 0.0
        self.review_count = 0
        self.discount_percentage = 0.0
        self.is_featured = False
        self.meta_title = name
        self.meta_description = description[:160] if description else ''
        
    def get_discounted_price(self) -> Decimal:
        if self.discount_percentage > 0:
            discount = self.price * Decimal(str(self.discount_percentage / 100))
            return self.price - discount
        return self.price
    
    def add_image(self, image_url: str, is_primary: bool = False):
        self.images.append({'url': image_url, 'is_primary': is_primary})
        
    def add_tag(self, tag: str):
        if tag not in self.tags:
            self.tags.append(tag)
            
    def update_rating(self, new_rating: float, review_count: int):
        self.rating = new_rating
        self.review_count = review_count
        
    def __repr__(self) -> str:
        return f"Product(id={self.product_id}, name={self.name}, price={self.price})"


class ProductVariant:
    """Product variant model (size, color, etc.)"""
    
    def __init__(self, variant_id: int, product_id: int, 
                 variant_name: str, variant_value: str,
                 price_modifier: Decimal = Decimal('0'),
                 sku_suffix: str = ''):
        self.variant_id = variant_id
        self.product_id = product_id
        self.variant_name = variant_name  # e.g., 'Color', 'Size'
        self.variant_value = variant_value  # e.g., 'Red', 'XL'
        self.price_modifier = Decimal(str(price_modifier))
        self.sku_suffix = sku_suffix
        self.is_active = True
        
    def __repr__(self) -> str:
        return f"ProductVariant(id={self.variant_id}, {self.variant_name}={self.variant_value})"


class Inventory:
    """Inventory model for tracking stock"""
    
    def __init__(self, inventory_id: int, product_id: int, 
                 warehouse_id: int, quantity: int = 0,
                 reorder_point: int = 10, reorder_quantity: int = 50):
        self.inventory_id = inventory_id
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.reorder_quantity = reorder_quantity
        self.reserved_quantity = 0
        self.last_updated = datetime.now()
        self.variant_id = None
        
    def get_available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self) -> bool:
        return self.get_available_quantity() <= self.reorder_point
    
    def add_stock(self, quantity: int) -> bool:
        if quantity > 0:
            self.quantity += quantity
            self.last_updated = datetime.now()
            return True
        return False
    
    def remove_stock(self, quantity: int) -> bool:
        if quantity > 0 and self.get_available_quantity() >= quantity:
            self.quantity -= quantity
            self.last_updated = datetime.now()
            return True
        return False
    
    def reserve_stock(self, quantity: int) -> bool:
        if self.get_available_quantity() >= quantity:
            self.reserved_quantity += quantity
            return True
        return False
    
    def release_reservation(self, quantity: int):
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        
    def __repr__(self) -> str:
        return f"Inventory(product_id={self.product_id}, warehouse_id={self.warehouse_id}, qty={self.quantity})"


class InventoryTransaction:
    """Track all inventory movements"""
    
    TRANSACTION_TYPES = [
        'PURCHASE', 'SALE', 'RETURN', 'ADJUSTMENT', 
        'TRANSFER', 'DAMAGE', 'EXPIRED'
    ]
    
    def __init__(self, transaction_id: int, inventory_id: int,
                 transaction_type: str, quantity: int,
                 reference_id: int = None, notes: str = ''):
        self.transaction_id = transaction_id
        self.inventory_id = inventory_id
        self.transaction_type = transaction_type
        self.quantity = quantity  # positive for in, negative for out
        self.reference_id = reference_id
        self.notes = notes
        self.created_at = datetime.now()
        self.created_by = None
        
    def __repr__(self) -> str:
        return f"InventoryTransaction(id={self.transaction_id}, type={self.transaction_type}, qty={self.quantity})"


class PurchaseOrder:
    """Purchase order model"""
    
    STATUS_CHOICES = ['DRAFT', 'PENDING', 'APPROVED', 'ORDERED', 
                      'RECEIVED', 'CANCELLED', 'PARTIAL']
    
    def __init__(self, po_id: int, supplier_id: int, warehouse_id: int,
                 created_by: int, expected_delivery: datetime = None):
        self.po_id = po_id
        self.supplier_id = supplier_id
        self.warehouse_id = warehouse_id
        self.created_by = created_by
        self.status = 'DRAFT'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.expected_delivery = expected_delivery or (datetime.now() + timedelta(days=7))
        self.received_at = None
        self.items = []
        self.notes = ''
        self.total_amount = Decimal('0')
        self.tax_amount = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.po_number = f"PO-{po_id:08d}"
        
    def add_item(self, product_id: int, quantity: int, 
                 unit_price: Decimal, variant_id: int = None):
        item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'received_quantity': 0,
            'subtotal': Decimal(str(unit_price)) * quantity
        }
        self.items.append(item)
        self._recalculate_total()
        
    def _recalculate_total(self):
        subtotal = sum(item['subtotal'] for item in self.items)
        self.total_amount = subtotal + self.tax_amount + self.shipping_cost
        
    def approve(self, approved_by: int):
        if self.status == 'PENDING':
            self.status = 'APPROVED'
            self.updated_at = datetime.now()
            return True
        return False
    
    def receive_items(self, received_items: list):
        """Mark items as received"""
        for received in received_items:
            for item in self.items:
                if item['product_id'] == received['product_id']:
                    item['received_quantity'] += received['quantity']
        
        all_received = all(
            item['received_quantity'] >= item['quantity'] 
            for item in self.items
        )
        any_received = any(
            item['received_quantity'] > 0 
            for item in self.items
        )
        
        if all_received:
            self.status = 'RECEIVED'
            self.received_at = datetime.now()
        elif any_received:
            self.status = 'PARTIAL'
            
        self.updated_at = datetime.now()
        
    def cancel(self, reason: str = ''):
        if self.status not in ['RECEIVED', 'CANCELLED']:
            self.status = 'CANCELLED'
            self.notes = f"Cancelled: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"PurchaseOrder(id={self.po_id}, supplier={self.supplier_id}, status={self.status})"


class SalesOrder:
    """Sales order model"""
    
    STATUS_CHOICES = ['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 
                      'DELIVERED', 'CANCELLED', 'RETURNED', 'REFUNDED']
    
    def __init__(self, order_id: int, user_id: int, 
                 shipping_address: dict, billing_address: dict = None):
        self.order_id = order_id
        self.user_id = user_id
        self.status = 'PENDING'
        self.shipping_address = shipping_address
        self.billing_address = billing_address or shipping_address
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.items = []
        self.subtotal = Decimal('0')
        self.tax_amount = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.discount_amount = Decimal('0')
        self.total_amount = Decimal('0')
        self.payment_status = 'PENDING'
        self.payment_method = ''
        self.tracking_number = ''
        self.notes = ''
        self.order_number = f"ORD-{order_id:010d}"
        self.estimated_delivery = datetime.now() + timedelta(days=5)
        
    def add_item(self, product_id: int, product_name: str, 
                 quantity: int, unit_price: Decimal, 
                 variant_id: int = None):
        item = {
            'product_id': product_id,
            'product_name': product_name,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'subtotal': Decimal(str(unit_price)) * quantity,
            'returned_quantity': 0
        }
        self.items.append(item)
        self._recalculate_total()
        
    def _recalculate_total(self):
        self.subtotal = sum(item['subtotal'] for item in self.items)
        self.total_amount = (self.subtotal + self.tax_amount + 
                            self.shipping_cost - self.discount_amount)
        
    def confirm(self):
        if self.status == 'PENDING':
            self.status = 'CONFIRMED'
            self.updated_at = datetime.now()
            return True
        return False
    
    def process(self):
        if self.status == 'CONFIRMED':
            self.status = 'PROCESSING'
            self.updated_at = datetime.now()
            return True
        return False
    
    def ship(self, tracking_number: str):
        if self.status == 'PROCESSING':
            self.status = 'SHIPPED'
            self.tracking_number = tracking_number
            self.updated_at = datetime.now()
            return True
        return False
    
    def deliver(self):
        if self.status == 'SHIPPED':
            self.status = 'DELIVERED'
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel(self, reason: str = ''):
        if self.status not in ['SHIPPED', 'DELIVERED', 'CANCELLED']:
            self.status = 'CANCELLED'
            self.notes = f"Cancelled: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def return_order(self, items_to_return: list = None):
        if self.status == 'DELIVERED':
            self.status = 'RETURNED'
            if items_to_return:
                for return_item in items_to_return:
                    for item in self.items:
                        if item['product_id'] == return_item['product_id']:
                            item['returned_quantity'] += return_item['quantity']
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"SalesOrder(id={self.order_id}, user={self.user_id}, status={self.status})"


class ShoppingCart:
    """Shopping cart model"""
    
    def __init__(self, cart_id: int, user_id: int = None, session_id: str = None):
        self.cart_id = cart_id
        self.user_id = user_id
        self.session_id = session_id
        self.items = {}  # product_id -> cart_item
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.coupon_code = None
        self.discount_amount = Decimal('0')
        
    def add_item(self, product_id: int, product_name: str, 
                 price: Decimal, quantity: int = 1,
                 variant_id: int = None):
        key = f"{product_id}_{variant_id}" if variant_id else str(product_id)
        if key in self.items:
            self.items[key]['quantity'] += quantity
            self.items[key]['subtotal'] = (
                self.items[key]['unit_price'] * self.items[key]['quantity']
            )
        else:
            self.items[key] = {
                'product_id': product_id,
                'product_name': product_name,
                'variant_id': variant_id,
                'quantity': quantity,
                'unit_price': Decimal(str(price)),
                'subtotal': Decimal(str(price)) * quantity
            }
        self.updated_at = datetime.now()
        
    def remove_item(self, product_id: int, variant_id: int = None):
        key = f"{product_id}_{variant_id}" if variant_id else str(product_id)
        if key in self.items:
            del self.items[key]
            self.updated_at = datetime.now()
            return True
        return False
    
    def update_quantity(self, product_id: int, quantity: int, 
                       variant_id: int = None) -> bool:
        key = f"{product_id}_{variant_id}" if variant_id else str(product_id)
        if key in self.items:
            if quantity <= 0:
                return self.remove_item(product_id, variant_id)
            self.items[key]['quantity'] = quantity
            self.items[key]['subtotal'] = (
                self.items[key]['unit_price'] * quantity
            )
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_subtotal(self) -> Decimal:
        return sum(item['subtotal'] for item in self.items.values())
    
    def get_total(self) -> Decimal:
        return self.get_subtotal() - self.discount_amount
    
    def get_item_count(self) -> int:
        return sum(item['quantity'] for item in self.items.values())
    
    def clear(self):
        self.items = {}
        self.coupon_code = None
        self.discount_amount = Decimal('0')
        self.updated_at = datetime.now()
        
    def apply_coupon(self, coupon_code: str, discount: Decimal):
        self.coupon_code = coupon_code
        self.discount_amount = discount
        self.updated_at = datetime.now()
        
    def merge_with_session_cart(self, session_cart: 'ShoppingCart'):
        """Merge session cart with user cart on login"""
        for key, item in session_cart.items.items():
            if key in self.items:
                self.items[key]['quantity'] += item['quantity']
                self.items[key]['subtotal'] = (
                    self.items[key]['unit_price'] * self.items[key]['quantity']
                )
            else:
                self.items[key] = item.copy()
        self.updated_at = datetime.now()
        
    def __repr__(self) -> str:
        return f"ShoppingCart(id={self.cart_id}, items={len(self.items)}, total={self.get_total()})"


class Review:
    """Product review model"""
    
    def __init__(self, review_id: int, product_id: int, user_id: int,
                 rating: int, title: str = '', body: str = ''):
        self.review_id = review_id
        self.product_id = product_id
        self.user_id = user_id
        self.rating = max(1, min(5, rating))  # 1-5 stars
        self.title = title
        self.body = body
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_verified_purchase = False
        self.helpful_votes = 0
        self.is_approved = True
        
    def mark_helpful(self):
        self.helpful_votes += 1
        
    def __repr__(self) -> str:
        return f"Review(id={self.review_id}, product={self.product_id}, rating={self.rating})"


class Coupon:
    """Coupon/discount model"""
    
    DISCOUNT_TYPES = ['PERCENTAGE', 'FIXED_AMOUNT', 'FREE_SHIPPING']
    
    def __init__(self, coupon_id: int, code: str, discount_type: str,
                 discount_value: Decimal, min_order_amount: Decimal = Decimal('0'),
                 max_uses: int = None, expiry_date: datetime = None):
        self.coupon_id = coupon_id
        self.code = code.upper()
        self.discount_type = discount_type
        self.discount_value = Decimal(str(discount_value))
        self.min_order_amount = Decimal(str(min_order_amount))
        self.max_uses = max_uses
        self.current_uses = 0
        self.expiry_date = expiry_date
        self.is_active = True
        self.created_at = datetime.now()
        
    def is_valid(self, order_amount: Decimal) -> tuple:
        if not self.is_active:
            return False, "Coupon is not active"
        if self.expiry_date and datetime.now() > self.expiry_date:
            return False, "Coupon has expired"
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "Coupon usage limit reached"
        if order_amount < self.min_order_amount:
            return False, f"Minimum order amount is {self.min_order_amount}"
        return True, "Valid"
    
    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        if self.discount_type == 'PERCENTAGE':
            return order_amount * (self.discount_value / 100)
        elif self.discount_type == 'FIXED_AMOUNT':
            return min(self.discount_value, order_amount)
        return Decimal('0')
    
    def use(self):
        self.current_uses += 1
        
    def __repr__(self) -> str:
        return f"Coupon(code={self.code}, type={self.discount_type}, value={self.discount_value})"


class Payment:
    """Payment model"""
    
    STATUS_CHOICES = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED']
    PAYMENT_METHODS = ['CREDIT_CARD', 'DEBIT_CARD', 'PAYPAL', 'BANK_TRANSFER', 'COD']
    
    def __init__(self, payment_id: int, order_id: int, amount: Decimal,
                 payment_method: str, user_id: int):
        self.payment_id = payment_id
        self.order_id = order_id
        self.amount = Decimal(str(amount))
        self.payment_method = payment_method
        self.user_id = user_id
        self.status = 'PENDING'
        self.transaction_id = ''
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.gateway_response = {}
        
    def process(self, transaction_id: str, gateway_response: dict = None):
        self.transaction_id = transaction_id
        self.gateway_response = gateway_response or {}
        self.status = 'COMPLETED'
        self.updated_at = datetime.now()
        
    def fail(self, reason: str = ''):
        self.status = 'FAILED'
        self.gateway_response['failure_reason'] = reason
        self.updated_at = datetime.now()
        
    def refund(self, refund_amount: Decimal = None):
        if self.status == 'COMPLETED':
            self.status = 'REFUNDED'
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"Payment(id={self.payment_id}, order={self.order_id}, amount={self.amount}, status={self.status})"


class Address:
    """Address model"""
    
    def __init__(self, address_id: int, user_id: int, 
                 full_name: str, street_address: str,
                 city: str, state: str, postal_code: str,
                 country: str, phone: str = '',
                 address_type: str = 'SHIPPING'):
        self.address_id = address_id
        self.user_id = user_id
        self.full_name = full_name
        self.street_address = street_address
        self.city = city
        self.state = state
        self.postal_code = postal_code
        self.country = country
        self.phone = phone
        self.address_type = address_type  # SHIPPING, BILLING
        self.is_default = False
        self.created_at = datetime.now()
        
    def to_dict(self) -> dict:
        return {
            'full_name': self.full_name,
            'street_address': self.street_address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone
        }
    
    def __repr__(self) -> str:
        return f"Address(id={self.address_id}, {self.city}, {self.country})"


class Wishlist:
    """Wishlist model"""
    
    def __init__(self, wishlist_id: int, user_id: int, name: str = 'My Wishlist'):
        self.wishlist_id = wishlist_id
        self.user_id = user_id
        self.name = name
        self.items = []
        self.is_public = False
        self.created_at = datetime.now()
        
    def add_item(self, product_id: int, variant_id: int = None):
        item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'added_at': datetime.now()
        }
        if not any(i['product_id'] == product_id for i in self.items):
            self.items.append(item)
            return True
        return False
    
    def remove_item(self, product_id: int) -> bool:
        original_count = len(self.items)
        self.items = [i for i in self.items if i['product_id'] != product_id]
        return len(self.items) < original_count
    
    def __repr__(self) -> str:
        return f"Wishlist(id={self.wishlist_id}, user={self.user_id}, items={len(self.items)})"


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """User management service"""
    
    def __init__(self):
        self.users = {}
        self.next_id = 1
        self._username_index = {}
        self._email_index = {}
        
    def create_user(self, username: str, email: str, password: str,
                    first_name: str = '', last_name: str = '',
                    user_type: str = 'customer') -> UserProfile:
        if username in self._username_index:
            raise ValueError(f"Username '{username}' already exists")
        if email in self._email_index:
            raise ValueError(f"Email '{email}' already registered")
        
        user = UserProfile(
            user_id=self.next_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type
        )
        user.password_hash = self._hash_password(password)
        
        self.users[self.next_id] = user
        self._username_index[username] = self.next_id
        self._email_index[email] = self.next_id
        self.next_id += 1
        
        return user
    
    def authenticate(self, username: str, password: str) -> UserProfile:
        user_id = self._username_index.get(username)
        if not user_id:
            return None
        user = self.users.get(user_id)
        if user and self._verify_password(password, user.password_hash):
            user.last_login = datetime.now()
            return user
        return None
    
    def get_user(self, user_id: int) -> UserProfile:
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> UserProfile:
        user_id = self._username_index.get(username)
        return self.users.get(user_id) if user_id else None
    
    def update_user(self, user_id: int, **kwargs) -> UserProfile:
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        allowed_fields = ['first_name', 'last_name', 'phone', 'address', 'email']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(user, field, value)
        return user
    
    def deactivate_user(self, user_id: int) -> bool:
        user = self.users.get(user_id)
        if user:
            user.is_active = False
            return True
        return False
    
    def get_all_users(self, user_type: str = None) -> list:
        users = list(self.users.values())
        if user_type:
            users = [u for u in users if u.user_type == user_type]
        return users
    
    def _hash_password(self, password: str) -> str:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        return self._hash_password(password) == password_hash
    
    def change_password(self, user_id: int, old_password: str, 
                       new_password: str) -> bool:
        user = self.users.get(user_id)
        if user and self._verify_password(old_password, user.password_hash):
            user.password_hash = self._hash_password(new_password)
            return True
        return False


class CategoryService:
    """Category management service"""
    
    def __init__(self):
        self.categories = {}
        self.next_id = 1
        
    def create_category(self, name: str, description: str = '',
                        parent_id: int = None) -> Category:
        category = Category(
            category_id=self.next_id,
            name=name,
            description=description,
            parent_id=parent_id
        )
        self.categories[self.next_id] = category
        
        if parent_id and parent_id in self.categories:
            self.categories[parent_id].add_child(category)
        
        self.next_id += 1
        return category
    
    def get_category(self, category_id: int) -> Category:
        return self.categories.get(category_id)
    
    def get_root_categories(self) -> list:
        return [c for c in self.categories.values() if c.parent_id is None]
    
    def get_subcategories(self, parent_id: int) -> list:
        return [c for c in self.categories.values() if c.parent_id == parent_id]
    
    def get_category_tree(self) -> list:
        """Get hierarchical category tree"""
        roots = self.get_root_categories()
        return self._build_tree(roots)
    
    def _build_tree(self, categories: list) -> list:
        tree = []
        for cat in categories:
            node = {
                'category': cat,
                'children': self._build_tree(cat.children)
            }
            tree.append(node)
        return tree
    
    def get_all_categories(self) -> list:
        return list(self.categories.values())


class ProductService:
    """Product management service"""
    
    def __init__(self):
        self.products = {}
        self.variants = {}
        self.next_id = 1
        self.next_variant_id = 1
        
    def create_product(self, name: str, description: str, price: Decimal,
                       category_id: int, sku: str = '', brand: str = '',
                       weight: float = 0.0) -> Product:
        product = Product(
            product_id=self.next_id,
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            sku=sku,
            brand=brand,
            weight=weight
        )
        self.products[self.next_id] = product
        self.next_id += 1
        return product
    
    def get_product(self, product_id: int) -> Product:
        return self.products.get(product_id)
    
    def update_product(self, product_id: int, **kwargs) -> Product:
        product = self.products.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        allowed_fields = ['name', 'description', 'price', 'brand', 
                         'weight', 'discount_percentage', 'is_featured', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(product, field, value)
        product.updated_at = datetime.now()
        return product
    
    def delete_product(self, product_id: int) -> bool:
        product = self.products.get(product_id)
        if product:
            product.is_active = False
            return True
        return False
    
    def search_products(self, query: str = '', category_id: int = None,
                       min_price: Decimal = None, max_price: Decimal = None,
                       brand: str = None, sort_by: str = 'name') -> list:
        products = [p for p in self.products.values() if p.is_active]
        
        if query:
            query_lower = query.lower()
            products = [p for p in products if 
                       query_lower in p.name.lower() or 
                       query_lower in p.description.lower() or
                       query_lower in p.brand.lower()]
        
        if category_id:
            products = [p for p in products if p.category_id == category_id]
        
        if min_price is not None:
            products = [p for p in products if p.get_discounted_price() >= min_price]
        
        if max_price is not None:
            products = [p for p in products if p.get_discounted_price() <= max_price]
        
        if brand:
            products = [p for p in products if p.brand.lower() == brand.lower()]
        
        # Sorting
        if sort_by == 'price_asc':
            products.sort(key=lambda p: p.get_discounted_price())
        elif sort_by == 'price_desc':
            products.sort(key=lambda p: p.get_discounted_price(), reverse=True)
        elif sort_by == 'rating':
            products.sort(key=lambda p: p.rating, reverse=True)
        elif sort_by == 'newest':
            products.sort(key=lambda p: p.created_at, reverse=True)
        else:
            products.sort(key=lambda p: p.name)
        
        return products
    
    def get_featured_products(self) -> list:
        return [p for p in self.products.values() if p.is_featured and p.is_active]
    
    def add_variant(self, product_id: int, variant_name: str, 
                   variant_value: str, price_modifier: Decimal = Decimal('0'),
                   sku_suffix: str = '') -> ProductVariant:
        variant = ProductVariant(
            variant_id=self.next_variant_id,
            product_id=product_id,
            variant_name=variant_name,
            variant_value=variant_value,
            price_modifier=price_modifier,
            sku_suffix=sku_suffix
        )
        self.variants[self.next_variant_id] = variant
        self.next_variant_id += 1
        return variant
    
    def get_product_variants(self, product_id: int) -> list:
        return [v for v in self.variants.values() if v.product_id == product_id]
    
    def get_all_products(self, include_inactive: bool = False) -> list:
        if include_inactive:
            return list(self.products.values())
        return [p for p in self.products.values() if p.is_active]
    
    def get_products_by_category(self, category_id: int) -> list:
        return [p for p in self.products.values() 
                if p.category_id == category_id and p.is_active]


class InventoryService:
    """Inventory management service"""
    
    def __init__(self):
        self.inventory = {}
        self.transactions = {}
        self.next_inventory_id = 1
        self.next_transaction_id = 1
        
    def create_inventory(self, product_id: int, warehouse_id: int,
                        quantity: int = 0, reorder_point: int = 10,
                        reorder_quantity: int = 50) -> Inventory:
        inv = Inventory(
            inventory_id=self.next_inventory_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity
        )
        self.inventory[self.next_inventory_id] = inv
        self.next_inventory_id += 1
        return inv
    
    def get_inventory(self, product_id: int, warehouse_id: int = None) -> list:
        inventories = [inv for inv in self.inventory.values() 
                      if inv.product_id == product_id]
        if warehouse_id:
            inventories = [inv for inv in inventories 
                          if inv.warehouse_id == warehouse_id]
        return inventories
    
    def get_total_stock(self, product_id: int) -> int:
        inventories = self.get_inventory(product_id)
        return sum(inv.get_available_quantity() for inv in inventories)
    
    def add_stock(self, product_id: int, warehouse_id: int, 
                 quantity: int, reference_id: int = None,
                 transaction_type: str = 'PURCHASE') -> bool:
        inventories = self.get_inventory(product_id, warehouse_id)
        
        if not inventories:
            inv = self.create_inventory(product_id, warehouse_id, quantity)
        else:
            inv = inventories[0]
            inv.add_stock(quantity)
        
        self._record_transaction(
            inventory_id=inv.inventory_id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference_id=reference_id
        )
        return True
    
    def remove_stock(self, product_id: int, warehouse_id: int,
                    quantity: int, reference_id: int = None,
                    transaction_type: str = 'SALE') -> bool:
        inventories = self.get_inventory(product_id, warehouse_id)
        
        if not inventories:
            return False
        
        inv = inventories[0]
        if inv.remove_stock(quantity):
            self._record_transaction(
                inventory_id=inv.inventory_id,
                transaction_type=transaction_type,
                quantity=-quantity,
                reference_id=reference_id
            )
            return True
        return False
    
    def transfer_stock(self, product_id: int, from_warehouse_id: int,
                      to_warehouse_id: int, quantity: int) -> bool:
        if self.remove_stock(product_id, from_warehouse_id, quantity, 
                            transaction_type='TRANSFER'):
            self.add_stock(product_id, to_warehouse_id, quantity,
                          transaction_type='TRANSFER')
            return True
        return False
    
    def get_low_stock_items(self) -> list:
        return [inv for inv in self.inventory.values() if inv.needs_reorder()]
    
    def adjust_inventory(self, inventory_id: int, new_quantity: int,
                        reason: str = '') -> bool:
        inv = self.inventory.get(inventory_id)
        if inv:
            old_quantity = inv.quantity
            inv.quantity = new_quantity
            inv.last_updated = datetime.now()
            
            adjustment = new_quantity - old_quantity
            self._record_transaction(
                inventory_id=inventory_id,
                transaction_type='ADJUSTMENT',
                quantity=adjustment,
                notes=reason
            )
            return True
        return False
    
    def _record_transaction(self, inventory_id: int, transaction_type: str,
                           quantity: int, reference_id: int = None,
                           notes: str = ''):
        transaction = InventoryTransaction(
            transaction_id=self.next_transaction_id,
            inventory_id=inventory_id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference_id=reference_id,
            notes=notes
        )
        self.transactions[self.next_transaction_id] = transaction
        self.next_transaction_id += 1
        return transaction
    
    def get_transaction_history(self, inventory_id: int = None,
                               product_id: int = None) -> list:
        transactions = list(self.transactions.values())
        if inventory_id:
            transactions = [t for t in transactions 
                           if t.inventory_id == inventory_id]
        return sorted(transactions, key=lambda t: t.created_at, reverse=True)


class WarehouseService:
    """Warehouse management service"""
    
    def __init__(self):
        self.warehouses = {}
        self.next_id = 1
        
    def create_warehouse(self, name: str, location: str,
                        capacity: int = 0, manager_id: int = None) -> Warehouse:
        warehouse = Warehouse(
            warehouse_id=self.next_id,
            name=name,
            location=location,
            capacity=capacity,
            manager_id=manager_id
        )
        self.warehouses[self.next_id] = warehouse
        self.next_id += 1
        return warehouse
    
    def get_warehouse(self, warehouse_id: int) -> Warehouse:
        return self.warehouses.get(warehouse_id)
    
    def get_all_warehouses(self) -> list:
        return [w for w in self.warehouses.values() if w.is_active]
    
    def update_warehouse(self, warehouse_id: int, **kwargs) -> Warehouse:
        warehouse = self.warehouses.get(warehouse_id)
        if not warehouse:
            raise ValueError(f"Warehouse {warehouse_id} not found")
        
        allowed_fields = ['name', 'location', 'capacity', 'manager_id']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(warehouse, field, value)
        return warehouse
    
    def deactivate_warehouse(self, warehouse_id: int) -> bool:
        warehouse = self.warehouses.get(warehouse_id)
        if warehouse:
            warehouse.is_active = False
            return True
        return False


class SupplierService:
    """Supplier management service"""
    
    def __init__(self):
        self.suppliers = {}
        self.next_id = 1
        
    def create_supplier(self, name: str, email: str, phone: str = '',
                       address: str = '', contact_person: str = '',
                       company_name: str = '') -> Supplier:
        supplier = Supplier(
            supplier_id=self.next_id,
            name=name,
            email=email,
            phone=phone,
            address=address,
            contact_person=contact_person,
            company_name=company_name
        )
        self.suppliers[self.next_id] = supplier
        self.next_id += 1
        return supplier
    
    def get_supplier(self, supplier_id: int) -> Supplier:
        return self.suppliers.get(supplier_id)
    
    def get_all_suppliers(self) -> list:
        return [s for s in self.suppliers.values() if s.is_active]
    
    def update_supplier(self, supplier_id: int, **kwargs) -> Supplier:
        supplier = self.suppliers.get(supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")
        
        allowed_fields = ['name', 'email', 'phone', 'address', 
                         'contact_person', 'company_name', 'payment_terms']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(supplier, field, value)
        return supplier
    
    def deactivate_supplier(self, supplier_id: int) -> bool:
        supplier = self.suppliers.get(supplier_id)
        if supplier:
            supplier.is_active = False
            return True
        return False


class PurchaseOrderService:
    """Purchase order management service"""
    
    def __init__(self, inventory_service: InventoryService):
        self.purchase_orders = {}
        self.next_id = 1
        self.inventory_service = inventory_service
        
    def create_purchase_order(self, supplier_id: int, warehouse_id: int,
                             created_by: int, 
                             expected_delivery: datetime = None) -> PurchaseOrder:
        po = PurchaseOrder(
            po_id=self.next_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            created_by=created_by,
            expected_delivery=expected_delivery
        )
        self.purchase_orders[self.next_id] = po
        self.next_id += 1
        return po
    
    def get_purchase_order(self, po_id: int) -> PurchaseOrder:
        return self.purchase_orders.get(po_id)
    
    def submit_for_approval(self, po_id: int) -> bool:
        po = self.purchase_orders.get(po_id)
        if po and po.status == 'DRAFT' and po.items:
            po.status = 'PENDING'
            po.updated_at = datetime.now()
            return True
        return False
    
    def approve_purchase_order(self, po_id: int, approved_by: int) -> bool:
        po = self.purchase_orders.get(po_id)
        if po:
            return po.approve(approved_by)
        return False
    
    def receive_purchase_order(self, po_id: int, 
                              received_items: list) -> bool:
        po = self.purchase_orders.get(po_id)
        if not po or po.status not in ['APPROVED', 'ORDERED', 'PARTIAL']:
            return False
        
        po.receive_items(received_items)
        
        # Update inventory
        for item in received_items:
            self.inventory_service.add_stock(
                product_id=item['product_id'],
                warehouse_id=po.warehouse_id,
                quantity=item['quantity'],
                reference_id=po_id,
                transaction_type='PURCHASE'
            )
        
        return True
    
    def get_all_purchase_orders(self, status: str = None) -> list:
        orders = list(self.purchase_orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)
    
    def get_supplier_orders(self, supplier_id: int) -> list:
        return [o for o in self.purchase_orders.values() 
                if o.supplier_id == supplier_id]


class CartService:
    """Shopping cart service"""
    
    def __init__(self, product_service: ProductService, 
                 inventory_service: InventoryService):
        self.carts = {}
        self.next_id = 1
        self.product_service = product_service
        self.inventory_service = inventory_service
        
    def get_or_create_cart(self, user_id: int = None, 
                          session_id: str = None) -> ShoppingCart:
        # Find existing cart
        for cart in self.carts.values():
            if user_id and cart.user_id == user_id:
                return cart
            if session_id and cart.session_id == session_id:
                return cart
        
        # Create new cart
        cart = ShoppingCart(
            cart_id=self.next_id,
            user_id=user_id,
            session_id=session_id
        )
        self.carts[self.next_id] = cart
        self.next_id += 1
        return cart
    
    def add_to_cart(self, cart_id: int, product_id: int, 
                   quantity: int = 1, variant_id: int = None) -> dict:
        cart = self.carts.get(cart_id)
        if not cart:
            return {'success': False, 'message': 'Cart not found'}
        
        product = self.product_service.get_product(product_id)
        if not product or not product.is_active:
            return {'success': False, 'message': 'Product not found'}
        
        # Check stock
        available_stock = self.inventory_service.get_total_stock(product_id)
        if available_stock < quantity:
            return {'success': False, 'message': f'Only {available_stock} items available'}
        
        price = product.get_discounted_price()
        if variant_id:
            variant = self.product_service.variants.get(variant_id)
            if variant:
                price += variant.price_modifier
        
        cart.add_item(product_id, product.name, price, quantity, variant_id)
        return {'success': True, 'message': 'Item added to cart', 'cart': cart}
    
    def remove_from_cart(self, cart_id: int, product_id: int,
                        variant_id: int = None) -> bool:
        cart = self.carts.get(cart_id)
        if cart:
            return cart.remove_item(product_id, variant_id)
        return False
    
    def update_cart_item(self, cart_id: int, product_id: int,
                        quantity: int, variant_id: int = None) -> bool:
        cart = self.carts.get(cart_id)
        if cart:
            return cart.update_quantity(product_id, quantity, variant_id)
        return False
    
    def merge_carts(self, session_cart_id: int, user_cart_id: int):
        session_cart = self.carts.get(session_cart_id)
        user_cart = self.carts.get(user_cart_id)
        
        if session_cart and user_cart:
            user_cart.merge_with_session_cart(session_cart)
            del self.carts[session_cart_id]
    
    def apply_coupon(self, cart_id: int, coupon: Coupon) -> dict:
        cart = self.carts.get(cart_id)
        if not cart:
            return {'success': False, 'message': 'Cart not found'}
        
        is_valid, message = coupon.is_valid(cart.get_subtotal())
        if not is_valid:
            return {'success': False, 'message': message}
        
        discount = coupon.calculate_discount(cart.get_subtotal())
        cart.apply_coupon(coupon.code, discount)
        return {'success': True, 'message': f'Coupon applied. Discount: {discount}'}


class OrderService:
    """Sales order management service"""
    
    def __init__(self, inventory_service: InventoryService,
                 cart_service: CartService):
        self.orders = {}
        self.next_id = 1
        self.inventory_service = inventory_service
        self.cart_service = cart_service
        
    def create_order_from_cart(self, cart_id: int, user_id: int,
                              shipping_address: dict,
                              billing_address: dict = None,
                              payment_method: str = 'CREDIT_CARD') -> SalesOrder:
        cart = self.cart_service.carts.get(cart_id)
        if not cart or not cart.items:
            raise ValueError("Cart is empty or not found")
        
        order = SalesOrder(
            order_id=self.next_id,
            user_id=user_id,
            shipping_address=shipping_address,
            billing_address=billing_address
        )
        order.payment_method = payment_method
        
        # Add items from cart
        for item in cart.items.values():
            order.add_item(
                product_id=item['product_id'],
                product_name=item['product_name'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                variant_id=item.get('variant_id')
            )
        
        order.discount_amount = cart.discount_amount
        order._recalculate_total()
        
        # Calculate tax (10%)
        order.tax_amount = order.subtotal * Decimal('0.10')
        
        # Calculate shipping
        order.shipping_cost = Decimal('5.99') if order.subtotal < Decimal('50') else Decimal('0')
        order._recalculate_total()
        
        self.orders[self.next_id] = order
        self.next_id += 1
        
        # Reserve inventory
        for item in cart.items.values():
            # Find warehouse with stock
            inventories = self.inventory_service.get_inventory(item['product_id'])
            for inv in inventories:
                if inv.reserve_stock(item['quantity']):
                    break
        
        # Clear cart
        cart.clear()
        
        return order
    
    def create_order(self, user_id: int, items: list,
                    shipping_address: dict,
                    billing_address: dict = None,
                    payment_method: str = 'CREDIT_CARD') -> SalesOrder:
        order = SalesOrder(
            order_id=self.next_id,
            user_id=user_id,
            shipping_address=shipping_address,
            billing_address=billing_address
        )
        order.payment_method = payment_method
        
        for item in items:
            order.add_item(
                product_id=item['product_id'],
                product_name=item['product_name'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                variant_id=item.get('variant_id')
            )
        
        order.tax_amount = order.subtotal * Decimal('0.10')
        order.shipping_cost = Decimal('5.99') if order.subtotal < Decimal('50') else Decimal('0')
        order._recalculate_total()
        
        self.orders[self.next_id] = order
        self.next_id += 1
        return order
    
    def get_order(self, order_id: int) -> SalesOrder:
        return self.orders.get(order_id)
    
    def get_user_orders(self, user_id: int) -> list:
        return sorted(
            [o for o in self.orders.values() if o.user_id == user_id],
            key=lambda o: o.created_at,
            reverse=True
        )
    
    def confirm_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.confirm()
        return False
    
    def process_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.process()
        return False
    
    def ship_order(self, order_id: int, tracking_number: str) -> bool:
        order = self.orders.get(order_id)
        if order:
            if order.ship(tracking_number):
                # Deduct from inventory
                for item in order.items:
                    inventories = self.inventory_service.get_inventory(
                        item['product_id']
                    )
                    for inv in inventories:
                        if inv.remove_stock(item['quantity']):
                            inv.release_reservation(item['quantity'])
                            self.inventory_service._record_transaction(
                                inventory_id=inv.inventory_id,
                                transaction_type='SALE',
                                quantity=-item['quantity'],
                                reference_id=order_id
                            )
                            break
                return True
        return False
    
    def deliver_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.deliver()
        return False
    
    def cancel_order(self, order_id: int, reason: str = '') -> bool:
        order = self.orders.get(order_id)
        if order:
            if order.cancel(reason):
                # Release inventory reservations
                for item in order.items:
                    inventories = self.inventory_service.get_inventory(
                        item['product_id']
                    )
                    for inv in inventories:
                        inv.release_reservation(item['quantity'])
                return True
        return False
    
    def get_all_orders(self, status: str = None) -> list:
        orders = list(self.orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)
    
    def get_order_statistics(self) -> dict:
        orders = list(self.orders.values())
        total_revenue = sum(
            o.total_amount for o in orders 
            if o.status not in ['CANCELLED', 'REFUNDED']
        )
        return {
            'total_orders': len(orders),
            'total_revenue': total_revenue,
            'pending_orders': len([o for o in orders if o.status == 'PENDING']),
            'processing_orders': len([o for o in orders if o.status == 'PROCESSING']),
            'shipped_orders': len([o for o in orders if o.status == 'SHIPPED']),
            'delivered_orders': len([o for o in orders if o.status == 'DELIVERED']),
            'cancelled_orders': len([o for o in orders if o.status == 'CANCELLED']),
        }


class ReviewService:
    """Product review service"""
    
    def __init__(self, product_service: ProductService):
        self.reviews = {}
        self.next_id = 1
        self.product_service = product_service
        
    def add_review(self, product_id: int, user_id: int, rating: int,
                  title: str = '', body: str = '',
                  is_verified: bool = False) -> Review:
        # Check if user already reviewed this product
        existing = [r for r in self.reviews.values() 
                   if r.product_id == product_id and r.user_id == user_id]
        if existing:
            raise ValueError("User has already reviewed this product")
        
        review = Review(
            review_id=self.next_id,
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=body
        )
        review.is_verified_purchase = is_verified
        self.reviews[self.next_id] = review
        self.next_id += 1
        
        # Update product rating
        self._update_product_rating(product_id)
        
        return review
    
    def _update_product_rating(self, product_id: int):
        product_reviews = [r for r in self.reviews.values() 
                          if r.product_id == product_id and r.is_approved]
        if product_reviews:
            avg_rating = sum(r.rating for r in product_reviews) / len(product_reviews)
            product = self.product_service.get_product(product_id)
            if product:
                product.update_rating(round(avg_rating, 1), len(product_reviews))
    
    def get_product_reviews(self, product_id: int) -> list:
        return sorted(
            [r for r in self.reviews.values() 
             if r.product_id == product_id and r.is_approved],
            key=lambda r: r.created_at,
            reverse=True
        )
    
    def get_user_reviews(self, user_id: int) -> list:
        return [r for r in self.reviews.values() if r.user_id == user_id]
    
    def delete_review(self, review_id: int, user_id: int) -> bool:
        review = self.reviews.get(review_id)
        if review and review.user_id == user_id:
            del self.reviews[review_id]
            self._update_product_rating(review.product_id)
            return True
        return False


class PaymentService:
    """Payment processing service"""
    
    def __init__(self):
        self.payments = {}
        self.next_id = 1
        
    def create_payment(self, order_id: int, amount: Decimal,
                      payment_method: str, user_id: int) -> Payment:
        payment = Payment(
            payment_id=self.next_id,
            order_id=order_id,
            amount=amount,
            payment_method=payment_method,
            user_id=user_id
        )
        self.payments[self.next_id] = payment
        self.next_id += 1
        return payment
    
    def process_payment(self, payment_id: int, 
                       card_details: dict = None) -> dict:
        payment = self.payments.get(payment_id)
        if not payment:
            return {'success': False, 'message': 'Payment not found'}
        
        # Simulate payment processing
        import random
        import string
        transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        
        # Simulate 95% success rate
        if random.random() < 0.95:
            payment.process(transaction_id, {'status': 'approved'})
            return {
                'success': True, 
                'transaction_id': transaction_id,
                'message': 'Payment processed successfully'
            }
        else:
            payment.fail('Card declined')
            return {'success': False, 'message': 'Payment failed: Card declined'}
    
    def refund_payment(self, payment_id: int, 
                      refund_amount: Decimal = None) -> dict:
        payment = self.payments.get(payment_id)
        if not payment:
            return {'success': False, 'message': 'Payment not found'}
        
        if payment.refund(refund_amount):
            return {'success': True, 'message': 'Refund processed successfully'}
        return {'success': False, 'message': 'Cannot refund this payment'}
    
    def get_payment(self, payment_id: int) -> Payment:
        return self.payments.get(payment_id)
    
    def get_order_payments(self, order_id: int) -> list:
        return [p for p in self.payments.values() if p.order_id == order_id]


class WishlistService:
    """Wishlist management service"""
    
    def __init__(self):
        self.wishlists = {}
        self.next_id = 1
        
    def get_or_create_wishlist(self, user_id: int, 
                               name: str = 'My Wishlist') -> Wishlist:
        for wishlist in self.wishlists.values():
            if wishlist.user_id == user_id and wishlist.name == name:
                return wishlist
        
        wishlist = Wishlist(
            wishlist_id=self.next_id,
            user_id=user_id,
            name=name
        )
        self.wishlists[self.next_id] = wishlist
        self.next_id += 1
        return wishlist
    
    def add_to_wishlist(self, user_id: int, product_id: int,
                       variant_id: int = None) -> bool:
        wishlist = self.get_or_create_wishlist(user_id)
        return wishlist.add_item(product_id, variant_id)
    
    def remove_from_wishlist(self, user_id: int, product_id: int) -> bool:
        for wishlist in self.wishlists.values():
            if wishlist.user_id == user_id:
                return wishlist.remove_item(product_id)
        return False
    
    def get_user_wishlist(self, user_id: int) -> Wishlist:
        return self.get_or_create_wishlist(user_id)


class CouponService:
    """Coupon management service"""
    
    def __init__(self):
        self.coupons = {}
        self.next_id = 1
        
    def create_coupon(self, code: str, discount_type: str,
                     discount_value: Decimal,
                     min_order_amount: Decimal = Decimal('0'),
                     max_uses: int = None,
                     expiry_date: datetime = None) -> Coupon:
        if code.upper() in [c.code for c in self.coupons.values()]:
            raise ValueError(f"Coupon code '{code}' already exists")
        
        coupon = Coupon(
            coupon_id=self.next_id,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            min_order_amount=min_order_amount,
            max_uses=max_uses,
            expiry_date=expiry_date
        )
        self.coupons[self.next_id] = coupon
        self.next_id += 1
        return coupon
    
    def get_coupon_by_code(self, code: str) -> Coupon:
        for coupon in self.coupons.values():
            if coupon.code == code.upper():
                return coupon
        return None
    
    def validate_coupon(self, code: str, order_amount: Decimal) -> dict:
        coupon = self.get_coupon_by_code(code)
        if not coupon:
            return {'valid': False, 'message': 'Invalid coupon code'}
        
        is_valid, message = coupon.is_valid(order_amount)
        if is_valid:
            discount = coupon.calculate_discount(order_amount)
            return {
                'valid': True, 
                'coupon': coupon,
                'discount': discount,
                'message': f'Coupon applied! You save {discount}'
            }
        return {'valid': False, 'message': message}


class AddressService:
    """Address management service"""
    
    def __init__(self):
        self.addresses = {}
        self.next_id = 1
        
    def add_address(self, user_id: int, full_name: str, 
                   street_address: str, city: str, state: str,
                   postal_code: str, country: str, phone: str = '',
                   address_type: str = 'SHIPPING',
                   is_default: bool = False) -> Address:
        address = Address(
            address_id=self.next_id,
            user_id=user_id,
            full_name=full_name,
            street_address=street_address,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            phone=phone,
            address_type=address_type
        )
        
        if is_default:
            # Remove default from other addresses of same type
            for addr in self.addresses.values():
                if (addr.user_id == user_id and 
                    addr.address_type == address_type):
                    addr.is_default = False
            address.is_default = True
        
        self.addresses[self.next_id] = address
        self.next_id += 1
        return address
    
    def get_user_addresses(self, user_id: int, 
                          address_type: str = None) -> list:
        addresses = [a for a in self.addresses.values() 
                    if a.user_id == user_id]
        if address_type:
            addresses = [a for a in addresses 
                        if a.address_type == address_type]
        return addresses
    
    def get_default_address(self, user_id: int, 
                           address_type: str = 'SHIPPING') -> Address:
        for address in self.addresses.values():
            if (address.user_id == user_id and 
                address.address_type == address_type and 
                address.is_default):
                return address
        return None
    
    def delete_address(self, address_id: int, user_id: int) -> bool:
        address = self.addresses.get(address_id)
        if address and address.user_id == user_id:
            del self.addresses[address_id]
            return True
        return False


# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class AmazonClone:
    """Main application class that orchestrates all services"""
    
    def __init__(self):
        # Initialize all services
        self.user_service = UserService()
        self.category_service = CategoryService()
        self.product_service = ProductService()
        self.warehouse_service = WarehouseService()
        self.supplier_service = SupplierService()
        self.inventory_service = InventoryService()
        self.cart_service = CartService(self.product_service, self.inventory_service)
        self.order_service = OrderService(self.inventory_service, self.cart_service)
        self.purchase_order_service = PurchaseOrderService(self.inventory_service)
        self.review_service = ReviewService(self.product_service)
        self.payment_service = PaymentService()
        self.wishlist_service = WishlistService()
        self.coupon_service = CouponService()
        self.address_service = AddressService()
        
        # Session management
        self.sessions = {}
        
    def initialize_demo_data(self):
        """Initialize the application with demo data"""
        print("Initializing Amazon Clone with demo data...")
        
        # Create admin user
        admin = self.user_service.create_user(
            username='admin',
            email='admin@amazonclone.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        print(f"Created admin user: {admin}")
        
        # Create regular users
        user1 = self.user_service.create_user(
            username='john_doe',
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        
        user2 = self.user_service.create_user(
            username='jane_smith',
            email='jane@example.com',
            password='password123',
            first_name='Jane',
            last_name='Smith',
            user_type='customer'
        )
        print(f"Created customers: {user1}, {user2}")
        
        # Create categories (multi-level)
        electronics = self.category_service.create_category(
            'Electronics', 'Electronic devices and accessories'
        )
        phones = self.category_service.create_category(
            'Smartphones', 'Mobile phones and accessories', 
            parent_id=electronics.category_id
        )
        laptops = self.category_service.create_category(
            'Laptops', 'Laptops and computers',
            parent_id=electronics.category_id
        )
        clothing = self.category_service.create_category(
            'Clothing', 'Fashion and apparel'
        )
        mens_clothing = self.category_service.create_category(
            "Men's Clothing", "Men's fashion",
            parent_id=clothing.category_id
        )
        books = self.category_service.create_category(
            'Books', 'Books and literature'
        )
        print(f"Created categories: {electronics}, {phones}, {laptops}, {clothing}, {books}")
        
        # Create warehouses
        warehouse1 = self.warehouse_service.create_warehouse(
            name='Main Warehouse',
            location='New York, NY',
            capacity=10000,
            manager_id=admin.user_id
        )
        warehouse2 = self.warehouse_service.create_warehouse(
            name='West Coast Warehouse',
            location='Los Angeles, CA',
            capacity=8000
        )
        print(f"Created warehouses: {warehouse1}, {warehouse2}")
        
        # Create suppliers
        supplier1 = self.supplier_service.create_supplier(
            name='TechSupply Co',
            email='supply@techsupply.com',
            phone='+1-555-0100',
            address='123 Tech Street, Silicon Valley, CA',
            contact_person='Bob Johnson',
            company_name='TechSupply Corporation'
        )
        supplier2 = self.supplier_service.create_supplier(
            name='Fashion Wholesale',
            email='orders@fashionwholesale.com',
            phone='+1-555-0200',
            address='456 Fashion Ave, New York, NY',
            contact_person='Alice Brown'
        )
        print(f"Created suppliers: {supplier1}, {supplier2}")
        
        # Create products
        iphone = self.product_service.create_product(
            name='iPhone 15 Pro',
            description='Latest Apple iPhone with advanced camera system',
            price=Decimal('999.99'),
            category_id=phones.category_id,
            sku='APPLE-IP15P',
            brand='Apple',
            weight=0.187
        )
        iphone.is_featured = True
        iphone.add_tag('smartphone')
        iphone.add_tag('apple')
        iphone.add_tag('5G')
        
        samsung = self.product_service.create_product(
            name='Samsung Galaxy S24',
            description='Samsung flagship smartphone with AI features',
            price=Decimal('849.99'),
            category_id=phones.category_id,
            sku='SAMSUNG-GS24',
            brand='Samsung',
            weight=0.167
        )
        samsung.discount_percentage = 10.0
        
        macbook = self.product_service.create_product(
            name='MacBook Pro 14"',
            description='Apple MacBook Pro with M3 chip',
            price=Decimal('1999.99'),
            category_id=laptops.category_id,
            sku='APPLE-MBP14',
            brand='Apple',
            weight=1.6
        )
        macbook.is_featured = True
        
        tshirt = self.product_service.create_product(
            name='Classic Cotton T-Shirt',
            description='Comfortable everyday cotton t-shirt',
            price=Decimal('19.99'),
            category_id=mens_clothing.category_id,
            sku='CLOTH-TSHIRT-001',
            brand='BasicWear',
            weight=0.2
        )
        
        python_book = self.product_service.create_product(
            name='Python Programming: A Complete Guide',
            description='Comprehensive guide to Python programming',
            price=Decimal('49.99'),
            category_id=books.category_id,
            sku='BOOK-PYTHON-001',
            brand='TechBooks Publishing',
            weight=0.8
        )
        
        print(f"Created products: {iphone}, {samsung}, {macbook}, {tshirt}, {python_book}")
        
        # Add product variants
        self.product_service.add_variant(
            product_id=iphone.product_id,
            variant_name='Color',
            variant_value='Natural Titanium',
            sku_suffix='-NT'
        )
        self.product_service.add_variant(
            product_id=iphone.product_id,
            variant_name='Color',
            variant_value='Black Titanium',
            sku_suffix='-BT'
        )
        self.product_service.add_variant(
            product_id=tshirt.product_id,
            variant_name='Size',
            variant_value='S',
            sku_suffix='-S'
        )
        self.product_service.add_variant(
            product_id=tshirt.product_id,
            variant_name='Size',
            variant_value='M',
            sku_suffix='-M'
        )
        self.product_service.add_variant(
            product_id=tshirt.product_id,
            variant_name='Size',
            variant_value='L',
            price_modifier=Decimal('2.00'),
            sku_suffix='-L'
        )
        
        # Add inventory
        self.inventory_service.create_inventory(
            product_id=iphone.product_id,
            warehouse_id=warehouse1.warehouse_id,
            quantity=100,
            reorder_point=20,
            reorder_quantity=50
        )
        self.inventory_service.create_inventory(
            product_id=samsung.product_id,
            warehouse_id=warehouse1.warehouse_id,
            quantity=150,
            reorder_point=30
        )
        self.inventory_service.create_inventory(
            product_id=macbook.product_id,
            warehouse_id=warehouse1.warehouse_id,
            quantity=50,
            reorder_point=10
        )
        self.inventory_service.create_inventory(
            product_id=tshirt.product_id,
            warehouse_id=warehouse1.warehouse_id,
            quantity=500,
            reorder_point=100
        )
        self.inventory_service.create_inventory(
            product_id=python_book.product_id,
            warehouse_id=warehouse2.warehouse_id,
            quantity=200,
            reorder_point=50
        )
        print("Created inventory records")
        
        # Create purchase order
        po = self.purchase_order_service.create_purchase_order(
            supplier_id=supplier1.supplier_id,
            warehouse_id=warehouse1.warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=7)
        )
        po.add_item(
            product_id=iphone.product_id,
            quantity=50,
            unit_price=Decimal('750.00')
        )
        po.add_item(
            product_id=samsung.product_id,
            quantity=75,
            unit_price=Decimal('600.00')
        )
        self.purchase_order_service.submit_for_approval(po.po_id)
        self.purchase_order_service.approve_purchase_order(po.po_id, admin.user_id)
        print(f"Created purchase order: {po}")
        
        # Create coupons
        self.coupon_service.create_coupon(
            code='SAVE10',
            discount_type='PERCENTAGE',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('50'),
            max_uses=100,
            expiry_date=datetime.now() + timedelta(days=30)
        )
        self.coupon_service.create_coupon(
            code='FLAT20',
            discount_type='FIXED_AMOUNT',
            discount_value=Decimal('20'),
            min_order_amount=Decimal('100')
        )
        print("Created coupons")
        
        # Add addresses for users
        self.address_service.add_address(
            user_id=user1.user_id,
            full_name='John Doe',
            street_address='123 Main St',
            city='New York',
            state='NY',
            postal_code='10001',
            country='USA',
            phone='+1-555-1234',
            is_default=True
        )
        
        # Add reviews
        self.review_service.add_review(
            product_id=iphone.product_id,
            user_id=user1.user_id,
            rating=5,
            title='Amazing phone!',
            body='Best smartphone I have ever used. Camera is incredible.',
            is_verified=True
        )
        self.review_service.add_review(
            product_id=iphone.product_id,
            user_id=user2.user_id,
            rating=4,
            title='Great but expensive',
            body='Excellent phone but the price is quite high.',
            is_verified=True
        )
        
        print("\nDemo data initialization complete!")
        return {
            'admin': admin,
            'users': [user1, user2],
            'categories': [electronics, phones, laptops, clothing, books],
            'warehouses': [warehouse1, warehouse2],
            'suppliers': [supplier1, supplier2],
            'products': [iphone, samsung, macbook, tshirt, python_book],
            'purchase_order': po
        }
    
    def demo_shopping_flow(self, demo_data: dict):
        """Demonstrate a complete shopping flow"""
        print("\n" + "="*60)
        print("DEMONSTRATING SHOPPING FLOW")
        print("="*60)
        
        user = demo_data['users'][0]
        products = demo_data['products']
        
        # Create cart
        cart = self.cart_service.get_or_create_cart(user_id=user.user_id)
        print(f"\n1. Created cart for {user.username}: {cart}")
        
        # Add items to cart
        result = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=products[0].product_id,  # iPhone
            quantity=1
        )
        print(f"2. Added iPhone to cart: {result['message']}")
        
        result = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=products[4].product_id,  # Python book
            quantity=2
        )
        print(f"3. Added Python book (x2) to cart: {result['message']}")
        
        print(f"4. Cart total: ${cart.get_total()}, Items: {cart.get_item_count()}")
        
        # Apply coupon
        coupon_result = self.coupon_service.validate_coupon('SAVE10', cart.get_subtotal())
        if coupon_result['valid']:
            cart.apply_coupon('SAVE10', coupon_result['discount'])
            print(f"5. Applied coupon SAVE10: {coupon_result['message']}")
        
        # Create order
        shipping_address = {
            'full_name': 'John Doe',
            'street_address': '123 Main St',
            'city': 'New York',
            'state': 'NY',
            'postal_code': '10001',
            'country': 'USA',
            'phone': '+1-555-1234'
        }
        
        order = self.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=user.user_id,
            shipping_address=shipping_address,
            payment_method='CREDIT_CARD'
        )
        print(f"6. Created order: {order}")
        print(f"   Order total: ${order.total_amount}")
        
        # Process payment
        payment = self.payment_service.create_payment(
            order_id=order.order_id,
            amount=order.total_amount,
            payment_method='CREDIT_CARD',
            user_id=user.user_id
        )
        
        payment_result = self.payment_service.process_payment(payment.payment_id)
        print(f"7. Payment result: {payment_result['message']}")
        
        if payment_result['success']:
            # Confirm and process order
            self.order_service.confirm_order(order.order_id)
            self.order_service.process_order(order.order_id)
            self.order_service.ship_order(order.order_id, 'TRACK123456789')
            print(f"8. Order status: {order.status}")
            print(f"   Tracking number: {order.tracking_number}")
        
        return order
    
    def demo_inventory_management(self, demo_data: dict):
        """Demonstrate inventory management"""
        print("\n" + "="*60)
        print("DEMONSTRATING INVENTORY MANAGEMENT")
        print("="*60)
        
        admin = demo_data['admin']
        products = demo_data['products']
        warehouses = demo_data['warehouses']
        suppliers = demo_data['suppliers']
        
        # Check inventory levels
        print("\n1. Current Inventory Levels:")
        for product in products:
            stock = self.inventory_service.get_total_stock(product.product_id)
            print(f"   {product.name}: {stock} units")
        
        # Check low stock
        low_stock = self.inventory_service.get_low_stock_items()
        print(f"\n2. Low stock items: {len(low_stock)}")
        
        # Create new purchase order
        po = self.purchase_order_service.create_purchase_order(
            supplier_id=suppliers[0].supplier_id,
            warehouse_id=warehouses[0].warehouse_id,
            created_by=admin.user_id
        )
        po.add_item(
            product_id=products[2].product_id,  # MacBook
            quantity=20,
            unit_price=Decimal('1500.00')
        )
        print(f"\n3. Created new purchase order: {po.po_number}")
        
        # Submit and approve
        self.purchase_order_service.submit_for_approval(po.po_id)
        self.purchase_order_service.approve_purchase_order(po.po_id, admin.user_id)
        print(f"4. Purchase order approved: {po.status}")
        
        # Receive items
        received = [{'product_id': products[2].product_id, 'quantity': 20}]
        self.purchase_order_service.receive_purchase_order(po.po_id, received)
        print(f"5. Items received. PO status: {po.status}")
        
        new_stock = self.inventory_service.get_total_stock(products[2].product_id)
        print(f"6. MacBook stock after receiving: {new_stock} units")
        
        # Transfer stock between warehouses
        transfer_result = self.inventory_service.transfer_stock(
            product_id=products[0].product_id,  # iPhone
            from_warehouse_id=warehouses[0].warehouse_id,
            to_warehouse_id=warehouses[1].warehouse_id,
            quantity=20
        )
        print(f"\n7. Stock transfer (iPhone): {transfer_result}")
        
        # Inventory adjustment
        inventories = self.inventory_service.get_inventory(products[3].product_id)
        if inventories:
            self.inventory_service.adjust_inventory(
                inventory_id=inventories[0].inventory_id,
                new_quantity=480,
                reason='Physical count adjustment'
            )
            print(f"8. Inventory adjusted for T-Shirt")
        
        # Transaction history
        transactions = self.inventory_service.get_transaction_history()
        print(f"\n9. Total inventory transactions: {len(transactions)}")
    
    def demo_admin_dashboard(self, demo_data: dict):
        """Demonstrate admin dashboard features"""
        print("\n" + "="*60)
        print("ADMIN DASHBOARD OVERVIEW")
        print("="*60)
        
        # Order statistics
        stats = self.order_service.get_order_statistics()
        print("\nOrder Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # User management
        all_users = self.user_service.get_all_users()
        customers = self.user_service.get_all_users(user_type='customer')
        print(f"\nUser Management:")
        print(f"  Total users: {len(all_users)}")
        print(f"  Customers: {len(customers)}")
        
        # Product management
        all_products = self.product_service.get_all_products()
        featured = self.product_service.get_featured_products()
        print(f"\nProduct Management:")
        print(f"  Total products: {len(all_products)}")
        print(f"  Featured products: {len(featured)}")
        
        # Category tree
        category_tree = self.category_service.get_category_tree()
        print(f"\nCategory Structure:")
        for node in category_tree:
            cat = node['category']
            print(f"  - {cat.name}")
            for child_node in node['children']:
                child = child_node['category']
                print(f"    - {child.name}")
        
        # Warehouse overview
        warehouses = self.warehouse_service.get_all_warehouses()
        print(f"\nWarehouse Management:")
        for wh in warehouses:
            print(f"  {wh.name} ({wh.location}): Capacity {wh.capacity}")
        
        # Supplier overview
        suppliers = self.supplier_service.get_all_suppliers()
        print(f"\nSupplier Management:")
        for sup in suppliers:
            print(f"  {sup.name} - {sup.email}")
        
        # Purchase orders
        pos = self.purchase_order_service.get_all_purchase_orders()
        print(f"\nPurchase Orders: {len(pos)} total")
        for po in pos:
            print(f"  {po.po_number}: {po.status} - ${po.total_amount}")
        
        # Low stock alerts
        low_stock = self.inventory_service.get_low_stock_items()
        print(f"\nLow Stock Alerts: {len(low_stock)} items need reordering")
    
    def demo_search_and_browse(self):
        """Demonstrate product search and browsing"""
        print("\n" + "="*60)
        print("PRODUCT SEARCH AND BROWSING")
        print("="*60)
        
        # Search by query
        results = self.product_service.search_products(query='iPhone')
        print(f"\n1. Search 'iPhone': {len(results)} results")
        for p in results:
            print(f"   - {p.name}: ${p.get_discounted_price()}")
        
        # Search by price range
        results = self.product_service.search_products(
            min_price=Decimal('10'),
            max_price=Decimal('100')
        )
        print(f"\n2. Products $10-$100: {len(results)} results")
        for p in results:
            print(f"   - {p.name}: ${p.get_discounted_price()}")
        
        # Search by brand
        results = self.product_service.search_products(brand='Apple')
        print(f"\n3. Apple products: {len(results)} results")
        for p in results:
            print(f"   - {p.name}: ${p.price}")
        
        # Sort by price
        results = self.product_service.search_products(sort_by='price_asc')
        print(f"\n4. All products sorted by price (asc):")
        for p in results:
            print(f"   - {p.name}: ${p.get_discounted_price()}")
        
        # Featured products
        featured = self.product_service.get_featured_products()
        print(f"\n5. Featured products: {len(featured)}")
        for p in featured:
            print(f"   - {p.name}: ${p.price}")


def main():
    """Main entry point"""
    print("="*60)
    print("AMAZON CLONE - COMPLETE E-COMMERCE PLATFORM")
    print("="*60)
    
    # Initialize application
    app = AmazonClone()
    
    # Load demo data
    demo_data = app.initialize_demo_data()
    
    # Run demonstrations
    app.demo_search_and_browse()
    order = app.demo_shopping_flow(demo_data)
    app.demo_inventory_management(demo_data)
    app.demo_admin_dashboard(demo_data)
    
    print("\n" + "="*60)
    print("AMAZON CLONE DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nSystem Components:")
    print("✓ User Authentication (Sign Up, Login, Logout)")
    print("✓ Product Listing and Search")
    print("✓ Product Detail View with Variants")
    print("✓ Shopping Cart Functionality")
    print("✓ Inventory Management System")
    print("✓ Order Management (Sales Orders)")
    print("✓ Purchase Order Management")
    print("✓ Supplier Management")
    print("✓ Warehouse Management")
    print("✓ User Management (Multi-type)")
    print("✓ Multi-Level Category System")
    print("✓ Review and Rating System")
    print("✓ Coupon/Discount System")
    print("✓ Payment Processing")
    print("✓ Wishlist Management")
    print("✓ Address Management")
    print("✓ Inventory Transaction Tracking")
    
    return app


# Django Models (for actual Django deployment)
DJANGO_MODELS_CODE = '''
# models.py - Django ORM Models

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class UserProfile(models.Model):
    USER_TYPES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('supplier', 'Supplier'),
        ('warehouse_manager', 'Warehouse Manager'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"{self.user.username} ({self.user_type})"


class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='children')
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
    
    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    contact_person = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=50, default='NET30')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'suppliers'
    
    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.TextField()
    capacity = models.IntegerField(default=0)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='managed_warehouses')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'warehouses'
    
    def __str__(self):
        return f"{self.name} - {self.location}"


class Product(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, 
                                  null=True, related_name='products')
    sku = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=200, blank=True)
    weight = models.FloatField(default=0)
    discount_percentage = models.FloatField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
    
    def get_discounted_price(self):
        if self.discount_percentage > 0:
            discount = self.price * Decimal(str(self.discount_percentage / 100))
            return self.price - discount
        return self.price
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'product_images'


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    variant_name = models.CharField(max_length=100)
    variant_value = models.CharField(max_length=100)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sku_suffix = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'product_variants'
    
    def __str__(self):
        return f"{self.product.name} - {self.variant_name}: {self.variant_value}"


class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, 
                                null=True, blank=True)
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    reorder_point = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory'
        unique_together = ['product', 'warehouse', 'variant']
    
    def get_available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self):
        return self.get_available_quantity() <= self.reorder_point
    
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('SALE', 'Sale'),
        ('RETURN', 'Return'),
        ('ADJUSTMENT', 'Adjustment'),
        ('TRANSFER', 'Transfer'),
        ('DAMAGE', 'Damage'),
        ('EXPIRED', 'Expired'),
    ]
    
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, 
                                   related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    reference_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_transactions'


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
        ('PARTIAL', 'Partially Received'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                    related_name='created_purchase_orders')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='approved_purchase_orders')
    expected_delivery = models.DateTimeField()
    received_at = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
    
    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, 
                                        related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    received_quantity = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        db_table = 'purchase_order_items'


class Address(models.Model):
    ADDRESS_TYPES = [
        ('SHIPPING', 'Shipping'),
        ('BILLING', 'Billing'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=200)
    street_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='SHIPPING')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'addresses'
        verbose_name_plural = 'addresses'
    
    def __str__(self):
        return f"{self.full_name}, {self.city}, {self.country}"


class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    payment_method = models.CharField(max_length=50, blank=True)
    
    # Address fields (stored as JSON or separate fields)
    shipping_full_name = models.CharField(max_length=200)
    shipping_street = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20, blank=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_orders'
    
    def __str__(self):
        return f"{self.order_number} - {self.user.username}"


class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=500)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    returned_quantity = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'sales_order_items'


class ShoppingCart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, 
                                 null=True, blank=True, related_name='cart')
    session_id = models.CharField(max_length=100, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopping_carts'


class CartItem(models.Model):
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product', 'variant']
    
    def get_subtotal(self):
        return self.unit_price * self.quantity


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reviews'
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}/5)"


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED_AMOUNT', 'Fixed Amount'),
        ('FREE_SHIPPING', 'Free Shipping'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.IntegerField(null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'coupons'
    
    def __str__(self):
        return f"{self.code} ({self.discount_type}: {self.discount_value})"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('PAYPAL', 'PayPal'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('COD', 'Cash on Delivery'),
    ]
    
    order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
    
    def __str__(self):
        return f"Payment {self.id} - Order {self.order.order_number}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    name = models.CharField(max_length=200, default='My Wishlist')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wishlists'
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wishlist_items'
        unique_together = ['wishlist', 'product']
'''


DJANGO_VIEWS_CODE = '''
# views.py - Django Views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.utils import timezone
from .models import *
from .forms import *
import json


# ============================================================
# AUTHENTICATION VIEWS
# ============================================================

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # Merge session cart with user cart
                session_cart_id = request.session.get('cart_id')
                if session_cart_id:
                    try:
                        session_cart = ShoppingCart.objects.get(id=session_cart_id)
                        user_cart, created = ShoppingCart.objects.get_or_create(user=user)
                        # Merge items
                        for item in session_cart.items.all():
                            cart_item, created = CartItem.objects.get_or_create(
                                cart=user_cart,
                                product=item.product,
                                variant=item.variant,
                                defaults={'quantity': 0, 'unit_price': item.unit_price}
                            )
                            cart_item.quantity += item.quantity
                            cart_item.save()
                        session_cart.delete()
                        del request.session['cart_id']
                    except ShoppingCart.DoesNotExist:
                        pass
                
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect(request.GET.get('next', 'home'))
            else:
                messages.error(request, 'Invalid username or password')
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


# ============================================================
# PRODUCT VIEWS
# ============================================================

def home_view(request):
    featured_products = Product.objects.filter(is_featured=True, is_active=True)[:8]
    categories = Category.objects.filter(parent=None, is_active=True)
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'new_arrivals': new_arrivals,
    }
    return render(request, 'home.html', context)


def product_list_view(request):
    products = Product.objects.filter(is_active=True)
    
    # Search
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(brand__icontains=query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Brand filter
    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand__iexact=brand)
    
    # Sorting
    sort_by = request.GET.get('sort', 'name')
    sort_options = {
        'name': 'name',
        'price_asc': 'price',
        'price_desc': '-price',
        'rating': '-rating',
        'newest': '-created_at',
    }
    products = products.order_by(sort_options.get(sort_by, 'name'))
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    
    categories = Category.objects.filter(is_active=True)
    brands = Product.objects.filter(is_active=True).values_list('brand', flat=True).distinct()
    
    context = {
        'products': products_page,
        'categories': categories,
        'brands': brands,
        'query': query,
        'sort_by': sort_by,
    }
    return render(request, 'products/list.html', context)


def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    variants = product.variants.filter(is_active=True)
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product_id)[:4]
    
    # Check if user has reviewed
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
    
    # Get inventory
    total_stock = sum(
        inv.get_available_quantity() 
        for inv in product.inventory.all()
    )
    
    context = {
        'product': product,
        'variants': variants,
        'reviews': reviews,
        'related_products': related_products,
        'user_review': user_review,
        'total_stock': total_stock,
        'in_stock': total_stock > 0,
    }
    return render(request, 'products/detail.html', context)


# ============================================================
# CART VIEWS
# ============================================================

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = ShoppingCart.objects.get_or_create(user=request.user)
    else:
        cart_id = request.session.get('cart_id')
        if cart_id:
            try:
                cart = ShoppingCart.objects.get(id=cart_id)
            except ShoppingCart.DoesNotExist:
                cart = ShoppingCart.objects.create(session_id=request.session.session_key)
                request.session['cart_id'] = cart.id
        else:
            cart = ShoppingCart.objects.create(session_id=request.session.session_key)
            request.session['cart_id'] = cart.id
    return cart


def cart_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product', 'variant').all()
    
    subtotal = sum(item.get_subtotal() for item in cart_items)
    tax = subtotal * Decimal('0.10')
    shipping = Decimal('5.99') if subtotal < Decimal('50') else Decimal('0')
    total = subtotal + tax + shipping - cart.discount_amount
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'cart/cart.html', context)


@require_POST
def add_to_cart_view(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    variant_id = request.POST.get('variant_id')
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = get_or_create_cart(request)
    
    # Check stock
    total_stock = sum(inv.get_available_quantity() for inv in product.inventory.all())
    if total_stock < quantity:
        return JsonResponse({'success': False, 'message': f'Only {total_stock} items available'})
    
    variant = None
    price = product.get_discounted_price()
    
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        price += variant.price_modifier
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={'quantity': 0, 'unit_price': price}
    )
    
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()
    
    cart_count = sum(item.quantity for item in cart.items.all())
    
    return JsonResponse({
        'success': True, 
        'message': 'Item added to cart',
        'cart_count': cart_count
    })


@require_POST
def remove_from_cart_view(request):
    item_id = request.POST.get('item_id')
    cart = get_or_create_cart(request)
    
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
        item.delete()
        return JsonResponse({'success': True, 'message': 'Item removed'})
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'})


@require_POST
def update_cart_view(request):
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    cart = get_or_create_cart(request)
    
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return JsonResponse({'success': True})
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'})


# ============================================================
# ORDER VIEWS
# ============================================================

@login_required
def checkout_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product', 'variant').all()
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty')
        return redirect('cart')
    
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        # Process checkout
        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method', 'CREDIT_CARD')
        
        if address_id:
            address = get_object_or_404(Address, id=address_id, user=request.user)
        else:
            # Create new address from form
            address = Address.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name'),
                street_address=request.POST.get('street_address'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                postal_code=request.POST.get('postal_code'),
                country=request.POST.get('country'),
                phone=request.POST.get('phone', ''),
            )
        
        # Calculate totals
        subtotal = sum(item.get_subtotal() for item in cart_items)
        tax = subtotal * Decimal('0.10')
        shipping = Decimal('5.99') if subtotal < Decimal('50') else Decimal('0')
        discount = cart.discount_amount
        total = subtotal + tax + shipping - discount
        
        # Create order
        import random
        order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
        
        order = SalesOrder.objects.create(
            order_number=order_number,
            user=request.user,
            payment_method=payment_method,
            shipping_full_name=address.full_name,
            shipping_street=address.street_address,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=address.country,
            shipping_phone=address.phone,
            subtotal=subtotal,
            tax_amount=tax,
            shipping_cost=shipping,
            discount_amount=discount,
            total_amount=total,
            estimated_delivery=timezone.now() + timezone.timedelta(days=5)
        )
        
        # Create order items
        for item in cart_items:
            SalesOrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.get_subtotal()
            )
            
            # Reserve inventory
            for inv in item.product.inventory.all():
                if inv.get_available_quantity() >= item.quantity:
                    inv.reserved_quantity += item.quantity
                    inv.save()
                    break
        
        # Create payment
        Payment.objects.create(
            order=order,
            user=request.user,
            amount=total,
            payment_method=payment_method,
            status='PENDING'
        )
        
        # Clear cart
        cart_items.delete()
        cart.discount_amount = Decimal('0')
        cart.coupon_code = ''
        cart.save()
        
        messages.success(request, f'Order {order_number} placed successfully!')
        return redirect('order_detail', order_id=order.id)
    
    subtotal = sum(item.get_subtotal() for item in cart_items)
    tax = subtotal * Decimal('0.10')
    shipping = Decimal('5.99') if subtotal < Decimal('50') else Decimal('0')
    total = subtotal + tax + shipping - cart.discount_amount
    
    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_list_view(request):
    orders = SalesOrder.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)
    return render(request, 'orders/list.html', {'orders': orders_page})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(SalesOrder, id=order_id, user=request.user)
    items = order.items.select_related('product', 'variant').all()
    payments = order.payments.all()
    
    context = {
        'order': order,
        'items': items,
        'payments': payments,
    }
    return render(request, 'orders/detail.html', context)


@login_required
@require_POST
def cancel_order_view(request, order_id):
    order = get_object_or_404(SalesOrder, id=order_id, user=request.user)
    
    if order.status not in ['SHIPPED', 'DELIVERED', 'CANCELLED']:
        order.status = 'CANCELLED'
        order.save()
        
        # Release inventory reservations
        for item in order.items.all():
            for inv in item.product.inventory.all():
                inv.reserved_quantity = max(0, inv.reserved_quantity - item.quantity)
                inv.save()
        
        messages.success(request, 'Order cancelled successfully')
    else:
        messages.error(request, 'Cannot cancel this order')
    
    return redirect('order_detail', order_id=order_id)


# ============================================================
# REVIEW VIEWS
# ============================================================

@login_required
@require_POST
def add_review_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check if already reviewed
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.error(request, 'You have already reviewed this product')
        return redirect('product_detail', product_id=product_id)
    
    rating = int(request.POST.get('rating', 5))
    title = request.POST.get('title', '')
    body = request.POST.get('body', '')
    
    # Check if verified purchase
    is_verified = SalesOrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__status='DELIVERED'
    ).exists()
    
    Review.objects.create(
        product=product,
        user=request.user,
        rating=rating,
        title=title,
        body=body,
        is_verified_purchase=is_verified
    )
    
    # Update product rating
    avg_rating = Review.objects.filter(
        product=product, is_approved=True
    ).aggregate(Avg('rating'))['rating__avg']
    review_count = Review.objects.filter(product=product, is_approved=True).count()
    
    product.rating = round(avg_rating, 1) if avg_rating else 0
    product.review_count = review_count
    product.save()
    
    messages.success(request, 'Review added successfully!')
    return redirect('product_detail', product_id=product_id)


# ============================================================
# WISHLIST VIEWS
# ============================================================

@login_required
def wishlist_view(request):
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user,
        defaults={'name': 'My Wishlist'}
    )
    items = wishlist.items.select_related('product').all()
    return render(request, 'wishlist/wishlist.html', {'wishlist': wishlist, 'items': items})


@login_required
@require_POST
def add_to_wishlist_view(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user,
        defaults={'name': 'My Wishlist'}
    )
    
    _, created = WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        product=product
    )
    
    message = 'Added to wishlist' if created else 'Already in wishlist'
    return JsonResponse({'success': True, 'message': message})


@login_required
@require_POST
def remove_from_wishlist_view(request):
    product_id = request.POST.get('product_id')
    
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).delete()
        return JsonResponse({'success': True, 'message': 'Removed from wishlist'})
    except Wishlist.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Wishlist not found'})


# ============================================================
# COUPON VIEWS
# ============================================================

@require_POST
def apply_coupon_view(request):
    code = request.POST.get('coupon_code', '').upper()
    cart = get_or_create_cart(request)
    
    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
        cart_items = cart.items.all()
        subtotal = sum(item.get_subtotal() for item in cart_items)
        
        # Validate coupon
        if coupon.expiry_date and timezone.now() > coupon.expiry_date:
            return JsonResponse({'success': False, 'message': 'Coupon has expired'})
        
        if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
            return JsonResponse({'success': False, 'message': 'Coupon usage limit reached'})
        
        if subtotal < coupon.min_order_amount:
            return JsonResponse({
                'success': False, 
                'message': f'Minimum order amount is ${coupon.min_order_amount}'
            })
        
        # Calculate discount
        if coupon.discount_type == 'PERCENTAGE':
            discount = subtotal * (coupon.discount_value / 100)
        elif coupon.discount_type == 'FIXED_AMOUNT':
            discount = min(coupon.discount_value, subtotal)
        else:
            discount = Decimal('0')
        
        cart.coupon_code = code
        cart.discount_amount = discount
        cart.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Coupon applied! You save ${discount:.2f}',
            'discount': str(discount)
        })
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code'})


# ============================================================
# ADMIN/INVENTORY VIEWS
# ============================================================

@staff_member_required
def admin_dashboard_view(request):
    # Statistics
    total_orders = SalesOrder.objects.count()
    total_revenue = SalesOrder.objects.filter(
        status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
    ).aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    pending_orders = SalesOrder.objects.filter(status='PENDING').count()
    low_stock_items = Inventory.objects.filter(
        quantity__lte=models.F('reorder_point')
    ).count()
    
    recent_orders = SalesOrder.objects.order_by('-created_at')[:10]
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'low_stock_items': low_stock_items,
        'recent_orders': recent_orders,
    }
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def inventory_management_view(request):
    inventories = Inventory.objects.select_related(
        'product', 'warehouse'
    ).order_by('product__name')
    
    low_stock = inventories.filter(quantity__lte=models.F('reorder_point'))
    
    context = {
        'inventories': inventories,
        'low_stock': low_stock,
    }
    return render(request, 'admin/inventory.html', context)


@staff_member_required
def purchase_order_list_view(request):
    purchase_orders = PurchaseOrder.objects.select_related(
        'supplier', 'warehouse'
    ).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        purchase_orders = purchase_orders.filter(status=status_filter)
    
    return render(request, 'admin/purchase_orders.html', {
        'purchase_orders': purchase_orders
    })


@staff_member_required
def create_purchase_order_view(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier_id')
        warehouse_id = request.POST.get('warehouse_id')
        expected_delivery = request.POST.get('expected_delivery')
        
        import random
        po_number = f"PO-{timezone.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
        
        po = PurchaseOrder.objects.create(
            po_number=po_number,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            created_by=request.user,
            expected_delivery=expected_delivery,
            status='DRAFT'
        )
        
        # Add items
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_prices = request.POST.getlist('unit_price[]')
        
        total = Decimal('0')
        for pid, qty, price in zip(product_ids, quantities, unit_prices):
            subtotal = Decimal(price) * int(qty)
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product_id=pid,
                quantity=int(qty),
                unit_price=Decimal(price),
                subtotal=subtotal
            )
            total += subtotal
        
        po.total_amount = total
        po.save()
        
        messages.success(request, f'Purchase order {po_number} created!')
        return redirect('purchase_order_detail', po_id=po.id)
    
    suppliers = Supplier.objects.filter(is_active=True)
    warehouses = Warehouse.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    return render(request, 'admin/create_purchase_order.html', {
        'suppliers': suppliers,
        'warehouses': warehouses,
        'products': products,
    })


@staff_member_required
def receive_purchase_order_view(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    
    if request.method == 'POST':
        for item in po.items.all():
            received_qty = int(request.POST.get(f'received_{item.id}', 0))
            if received_qty > 0:
                item.received_quantity += received_qty
                item.save()
                
                # Update inventory
                inv, created = Inventory.objects.get_or_create(
                    product=item.product,
                    warehouse=po.warehouse,
                    defaults={'quantity': 0}
                )
                inv.quantity += received_qty
                inv.save()
                
                # Record transaction
                InventoryTransaction.objects.create(
                    inventory=inv,
                    transaction_type='PURCHASE',
                    quantity=received_qty,
                    reference_id=po.id,
                    created_by=request.user
                )
        
        # Update PO status
        all_received = all(
            item.received_quantity >= item.quantity 
            for item in po.items.all()
        )
        any_received = any(
            item.received_quantity > 0 
            for item in po.items.all()
        )
        
        if all_received:
            po.status = 'RECEIVED'
            po.received_at = timezone.now()
        elif any_received:
            po.status = 'PARTIAL'
        po.save()
        
        messages.success(request, 'Items received and inventory updated!')
        return redirect('purchase_order_detail', po_id=po_id)
    
    return render(request, 'admin/receive_purchase_order.html', {'po': po})


@staff_member_required
def warehouse_management_view(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    return render(request, 'admin/warehouses.html', {'warehouses': warehouses})


@staff_member_required
def supplier_management_view(request):
    suppliers = Supplier.objects.filter(is_active=True)
    return render(request, 'admin/suppliers.html', {'suppliers': suppliers})


@staff_member_required
def user_management_view(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    return render(request, 'admin/users.html', {'users': users_page})


@staff_member_required
def order_management_view(request):
    orders = SalesOrder.objects.select_related('user').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    paginator = Paginator(orders, 20)
    page = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)
    
    return render(request, 'admin/orders.html', {'orders': orders_page})


@staff_member_required
@require_POST
def update_order_status_view(request, order_id):
    order = get_object_or_404(SalesOrder, id=order_id)
    new_status = request.POST.get('status')
    tracking_number = request.POST.get('tracking_number', '')
    
    valid_transitions = {
        'PENDING': ['CONFIRMED', 'CANCELLED'],
        'CONFIRMED': ['PROCESSING', 'CANCELLED'],
        'PROCESSING': ['SHIPPED', 'CANCELLED'],
        'SHIPPED': ['DELIVERED'],
        'DELIVERED': ['RETURNED'],
    }
    
    if new_status in valid_transitions.get(order.status, []):
        order.status = new_status
        if tracking_number:
            order.tracking_number = tracking_number
        order.save()
        
        if new_status == 'SHIPPED':
            # Deduct from inventory
            for item in order.items.all():
                for inv in item.product.inventory.all():
                    if inv.quantity >= item.quantity:
                        inv.quantity -= item.quantity
                        inv.reserved_quantity = max(0, inv.reserved_quantity - item.quantity)
                        inv.save()
                        
                        InventoryTransaction.objects.create(
                            inventory=inv,
                            transaction_type='SALE',
                            quantity=-item.quantity,
                            reference_id=order.id,
                            created_by=request.user
                        )
                        break
        
        messages.success(request, f'Order status updated to {new_status}')
    else:
        messages.error(request, 'Invalid status transition')
    
    return redirect('admin_order_detail', order_id=order_id)
'''


DJANGO_URLS_CODE = '''
# urls.py - URL Configuration

from django.urls import path, include
from django.contrib import admin
from . import views

urlpatterns = [
    # Admin
    path('django-admin/', admin.site.urls),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Home
    path('', views.home_view, name='home'),
    
    # Products
    path('products/', views.product_list_view, name='product_list'),
    path('products/<int:product_id>/', views.product_detail_view, name='product_detail'),
    path('products/<int:product_id>/review/', views.add_review_view, name='add_review'),
    
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/remove/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/update/', views.update_cart_view, name='update_cart'),
    path('cart/coupon/', views.apply_coupon_view, name='apply_coupon'),
    
    # Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/cancel/', views.cancel_order_view, name='cancel_order'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/', views.add_to_wishlist_view, name='add_to_wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist_view, name='remove_from_wishlist'),
    
    # Admin/Management
    path('management/', views.admin_dashboard_view, name='admin_dashboard'),
    path('management/inventory/', views.inventory_management_view, name='inventory_management'),
    path('management/purchase-orders/', views.purchase_order_list_view, name='purchase_order_list'),
    path('management/purchase-orders/create/', views.create_purchase_order_view, name='create_purchase_order'),
    path('management/purchase-orders/<int:po_id>/receive/', views.receive_purchase_order_view, name='receive_purchase_order'),
    path('management/warehouses/', views.warehouse_management_view, name='warehouse_management'),
    path('management/suppliers/', views.supplier_management_view, name='supplier_management'),
    path('management/users/', views.user_management_view, name='user_management'),
    path('management/orders/', views.order_management_view, name='admin_order_list'),
    path('management/orders/<int:order_id>/status/', views.update_order_status_view, name='update_order_status'),
]
'''


DJANGO_FORMS_CODE = '''
# forms.py - Django Forms

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import *


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'sku', 
                 'brand', 'weight', 'discount_percentage', 'is_featured', 'is_active']


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'body']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'street_address', 'city', 'state', 
                 'postal_code', 'country', 'phone', 'address_type', 'is_default']


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 
                 'min_order_amount', 'max_uses', 'expiry_date', 'is_active']


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'company_name', 'email', 'phone', 'address', 
                 'contact_person', 'tax_id', 'payment_terms']


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'location', 'capacity', 'manager']


class InventoryAdjustmentForm(forms.Form):
    inventory_id = forms.IntegerField()
    new_quantity = forms.IntegerField(min_value=0)
    reason = forms.CharField(max_length=500, required=False)
'''


if __name__ == '__main__':
    app = main()
    
    print("\n" + "="*60)
    print("SYSTEM ARCHITECTURE SUMMARY")
    print("="*60)
    print("""
Models:
  - UserProfile: Extended user with roles (customer/admin/supplier/warehouse_manager)
  - Category: Multi-level hierarchical categories
  - Product: Full product with variants, images, tags
  - ProductVariant: Size, color, etc. variants
  - Inventory: Stock tracking per warehouse
  - InventoryTransaction: Complete audit trail
  - Warehouse: Physical storage locations
  - Supplier: Vendor management
  - PurchaseOrder: Procurement from suppliers
  - SalesOrder: Customer orders
  - ShoppingCart: Session/user cart
  - Review: Product ratings and reviews
  - Coupon: Discount codes
  - Payment: Payment processing
  - Address: Shipping/billing addresses
  - Wishlist: Save for later

Services:
  - UserService: Authentication, user management
  - CategoryService: Multi-level category tree
  - ProductService: CRUD, search, filtering
  - InventoryService: Stock management, transfers
  - WarehouseService: Warehouse operations
  - SupplierService: Supplier management
  - PurchaseOrderService: Procurement workflow
  - CartService: Shopping cart operations
  - OrderService: Order lifecycle management
  - ReviewService: Product reviews
  - PaymentService: Payment processing
  - WishlistService: Wishlist management
  - CouponService: Discount management
  - AddressService: Address book

Django Integration:
  - Complete Django ORM models
  - Full view implementations
  - URL routing
  - Form classes
  - Admin integration
    """)