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
    'SECRET_KEY': 'amazon-clone-secret-key-change-in-production',
    'DEBUG': True,
    'ALLOWED_HOSTS': ['*'],
    'INSTALLED_APPS': [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ],
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'amazon_clone.db',
        }
    },
    'STATIC_URL': '/static/',
    'MEDIA_URL': '/media/',
    'MEDIA_ROOT': 'media/',
    'LOGIN_URL': '/auth/login/',
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
        self._password_hash = None
        
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self) -> str:
        return f"UserProfile(id={self.user_id}, username={self.username}, type={self.user_type})"


class Category:
    """Product category model"""
    
    def __init__(self, category_id: int, name: str, 
                 parent_id: int = None, description: str = '',
                 slug: str = ''):
        self.category_id = category_id
        self.name = name
        self.parent_id = parent_id
        self.description = description
        self.slug = slug or name.lower().replace(' ', '-')
        self.is_active = True
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
                 contact_person: str = '', payment_terms: str = 'NET30'):
        self.supplier_id = supplier_id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.contact_person = contact_person
        self.payment_terms = payment_terms
        self.is_active = True
        self.created_at = datetime.now()
        self.rating = 0.0
        self.total_orders = 0
        
    def update_rating(self, new_rating: float):
        if 0 <= new_rating <= 5:
            self.rating = (self.rating * self.total_orders + new_rating) / (self.total_orders + 1)
            
    def __repr__(self) -> str:
        return f"Supplier(id={self.supplier_id}, name={self.name})"


class Warehouse:
    """Warehouse model for inventory management"""
    
    def __init__(self, warehouse_id: int, name: str, location: str,
                 capacity: int = 10000, manager_id: int = None):
        self.warehouse_id = warehouse_id
        self.name = name
        self.location = location
        self.capacity = capacity
        self.manager_id = manager_id
        self.is_active = True
        self.created_at = datetime.now()
        self.current_stock_count = 0
        self.zones = []
        
    def get_available_capacity(self) -> int:
        return self.capacity - self.current_stock_count
    
    def add_zone(self, zone_name: str):
        self.zones.append({'name': zone_name, 'items': []})
        
    def __repr__(self) -> str:
        return f"Warehouse(id={self.warehouse_id}, name={self.name}, location={self.location})"


class Product:
    """Product model"""
    
    def __init__(self, product_id: int, name: str, description: str,
                 price: Decimal, category_id: int, sku: str = '',
                 brand: str = '', weight: float = 0.0,
                 dimensions: dict = None):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = Decimal(str(price))
        self.category_id = category_id
        self.sku = sku or f"SKU-{product_id:06d}"
        self.brand = brand
        self.weight = weight
        self.dimensions = dimensions or {'length': 0, 'width': 0, 'height': 0}
        self.is_active = True
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.images = []
        self.tags = []
        self.rating = 0.0
        self.review_count = 0
        self.discount_percentage = 0.0
        
    def get_discounted_price(self) -> Decimal:
        if self.discount_percentage > 0:
            discount = self.price * Decimal(str(self.discount_percentage / 100))
            return self.price - discount
        return self.price
    
    def add_image(self, image_url: str, is_primary: bool = False):
        self.images.append({'url': image_url, 'is_primary': is_primary})
        
    def update_rating(self, new_rating: float):
        if 0 <= new_rating <= 5:
            total_rating = self.rating * self.review_count + new_rating
            self.review_count += 1
            self.rating = total_rating / self.review_count
            
    def __repr__(self) -> str:
        return f"Product(id={self.product_id}, name={self.name}, price={self.price})"


class ProductVariant:
    """Product variant model (size, color, etc.)"""
    
    def __init__(self, variant_id: int, product_id: int,
                 attributes: dict, price_modifier: Decimal = Decimal('0'),
                 sku: str = ''):
        self.variant_id = variant_id
        self.product_id = product_id
        self.attributes = attributes  # {'color': 'red', 'size': 'XL'}
        self.price_modifier = Decimal(str(price_modifier))
        self.sku = sku
        self.is_active = True
        
    def __repr__(self) -> str:
        return f"ProductVariant(id={self.variant_id}, product_id={self.product_id}, attrs={self.attributes})"


class Inventory:
    """Inventory model - tracks stock levels"""
    
    def __init__(self, inventory_id: int, product_id: int,
                 warehouse_id: int, quantity: int = 0,
                 reorder_point: int = 10, reorder_quantity: int = 100,
                 variant_id: int = None):
        self.inventory_id = inventory_id
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.reorder_quantity = reorder_quantity
        self.variant_id = variant_id
        self.reserved_quantity = 0
        self.last_updated = datetime.now()
        self.movement_history = []
        
    def get_available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self) -> bool:
        return self.get_available_quantity() <= self.reorder_point
    
    def add_stock(self, quantity: int, reason: str = 'purchase_order'):
        if quantity > 0:
            self.quantity += quantity
            self.last_updated = datetime.now()
            self._record_movement('in', quantity, reason)
            
    def remove_stock(self, quantity: int, reason: str = 'sale'):
        if quantity > 0 and self.get_available_quantity() >= quantity:
            self.quantity -= quantity
            self.last_updated = datetime.now()
            self._record_movement('out', quantity, reason)
            return True
        return False
    
    def reserve_stock(self, quantity: int) -> bool:
        if self.get_available_quantity() >= quantity:
            self.reserved_quantity += quantity
            return True
        return False
    
    def release_reservation(self, quantity: int):
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        
    def _record_movement(self, movement_type: str, quantity: int, reason: str):
        self.movement_history.append({
            'type': movement_type,
            'quantity': quantity,
            'reason': reason,
            'timestamp': datetime.now(),
            'balance': self.quantity
        })
        
    def __repr__(self) -> str:
        return f"Inventory(product_id={self.product_id}, warehouse_id={self.warehouse_id}, qty={self.quantity})"


class PurchaseOrder:
    """Purchase Order model"""
    
    STATUS_CHOICES = ['draft', 'pending', 'approved', 'ordered', 'received', 'cancelled']
    
    def __init__(self, po_id: int, supplier_id: int, warehouse_id: int,
                 created_by: int, expected_delivery: datetime = None):
        self.po_id = po_id
        self.supplier_id = supplier_id
        self.warehouse_id = warehouse_id
        self.created_by = created_by
        self.expected_delivery = expected_delivery or (datetime.now() + timedelta(days=7))
        self.status = 'draft'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.items = []
        self.notes = ''
        self.total_amount = Decimal('0')
        self.approved_by = None
        self.approved_at = None
        
    def add_item(self, product_id: int, quantity: int, unit_price: Decimal,
                 variant_id: int = None):
        item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'total_price': Decimal(str(unit_price)) * quantity,
            'received_quantity': 0
        }
        self.items.append(item)
        self._calculate_total()
        
    def _calculate_total(self):
        self.total_amount = sum(item['total_price'] for item in self.items)
        
    def approve(self, approved_by: int):
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = approved_by
            self.approved_at = datetime.now()
            self.updated_at = datetime.now()
            return True
        return False
    
    def mark_ordered(self):
        if self.status == 'approved':
            self.status = 'ordered'
            self.updated_at = datetime.now()
            return True
        return False
    
    def receive_items(self, received_items: list):
        """Mark items as received"""
        if self.status == 'ordered':
            for received in received_items:
                for item in self.items:
                    if item['product_id'] == received['product_id']:
                        item['received_quantity'] = received['quantity']
            
            all_received = all(
                item['received_quantity'] >= item['quantity'] 
                for item in self.items
            )
            if all_received:
                self.status = 'received'
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel(self, reason: str = ''):
        if self.status not in ['received', 'cancelled']:
            self.status = 'cancelled'
            self.notes = f"Cancelled: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"PurchaseOrder(id={self.po_id}, supplier_id={self.supplier_id}, status={self.status})"


class Cart:
    """Shopping cart model"""
    
    def __init__(self, cart_id: int, user_id: int = None, session_id: str = None):
        self.cart_id = cart_id
        self.user_id = user_id
        self.session_id = session_id
        self.items = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.coupon_code = None
        self.discount_amount = Decimal('0')
        
    def add_item(self, product_id: int, quantity: int, price: Decimal,
                 variant_id: int = None):
        for item in self.items:
            if item['product_id'] == product_id and item.get('variant_id') == variant_id:
                item['quantity'] += quantity
                item['total_price'] = item['unit_price'] * item['quantity']
                self.updated_at = datetime.now()
                return
                
        self.items.append({
            'product_id': product_id,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': Decimal(str(price)),
            'total_price': Decimal(str(price)) * quantity
        })
        self.updated_at = datetime.now()
        
    def remove_item(self, product_id: int, variant_id: int = None):
        self.items = [
            item for item in self.items 
            if not (item['product_id'] == product_id and item.get('variant_id') == variant_id)
        ]
        self.updated_at = datetime.now()
        
    def update_quantity(self, product_id: int, quantity: int, variant_id: int = None):
        for item in self.items:
            if item['product_id'] == product_id and item.get('variant_id') == variant_id:
                if quantity <= 0:
                    self.remove_item(product_id, variant_id)
                else:
                    item['quantity'] = quantity
                    item['total_price'] = item['unit_price'] * quantity
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_subtotal(self) -> Decimal:
        return sum(item['total_price'] for item in self.items)
    
    def get_total(self) -> Decimal:
        return self.get_subtotal() - self.discount_amount
    
    def get_item_count(self) -> int:
        return sum(item['quantity'] for item in self.items)
    
    def clear(self):
        self.items = []
        self.coupon_code = None
        self.discount_amount = Decimal('0')
        self.updated_at = datetime.now()
        
    def apply_coupon(self, coupon_code: str, discount: Decimal):
        self.coupon_code = coupon_code
        self.discount_amount = discount
        self.updated_at = datetime.now()
        
    def __repr__(self) -> str:
        return f"Cart(id={self.cart_id}, user_id={self.user_id}, items={len(self.items)})"


class Address:
    """Address model"""
    
    def __init__(self, address_id: int, user_id: int, address_type: str,
                 street: str, city: str, state: str, country: str,
                 postal_code: str, is_default: bool = False):
        self.address_id = address_id
        self.user_id = user_id
        self.address_type = address_type  # shipping, billing
        self.street = street
        self.city = city
        self.state = state
        self.country = country
        self.postal_code = postal_code
        self.is_default = is_default
        
    def get_full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"
    
    def __repr__(self) -> str:
        return f"Address(id={self.address_id}, city={self.city}, country={self.country})"


class SalesOrder:
    """Sales Order model"""
    
    STATUS_CHOICES = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
    PAYMENT_STATUS = ['pending', 'paid', 'failed', 'refunded']
    
    def __init__(self, order_id: int, user_id: int, shipping_address_id: int,
                 billing_address_id: int, payment_method: str = 'credit_card'):
        self.order_id = order_id
        self.user_id = user_id
        self.shipping_address_id = shipping_address_id
        self.billing_address_id = billing_address_id
        self.payment_method = payment_method
        self.status = 'pending'
        self.payment_status = 'pending'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.items = []
        self.subtotal = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.tax_amount = Decimal('0')
        self.discount_amount = Decimal('0')
        self.total_amount = Decimal('0')
        self.tracking_number = None
        self.notes = ''
        self.coupon_code = None
        self.order_number = f"ORD-{order_id:08d}"
        
    def add_item(self, product_id: int, quantity: int, unit_price: Decimal,
                 product_name: str, variant_id: int = None):
        item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'product_name': product_name,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'total_price': Decimal(str(unit_price)) * quantity
        }
        self.items.append(item)
        self._calculate_totals()
        
    def _calculate_totals(self):
        self.subtotal = sum(item['total_price'] for item in self.items)
        self.total_amount = self.subtotal + self.shipping_cost + self.tax_amount - self.discount_amount
        
    def set_shipping_cost(self, cost: Decimal):
        self.shipping_cost = Decimal(str(cost))
        self._calculate_totals()
        
    def set_tax(self, tax_rate: float):
        self.tax_amount = self.subtotal * Decimal(str(tax_rate))
        self._calculate_totals()
        
    def confirm(self):
        if self.status == 'pending':
            self.status = 'confirmed'
            self.updated_at = datetime.now()
            return True
        return False
    
    def process(self):
        if self.status == 'confirmed':
            self.status = 'processing'
            self.updated_at = datetime.now()
            return True
        return False
    
    def ship(self, tracking_number: str):
        if self.status == 'processing':
            self.status = 'shipped'
            self.tracking_number = tracking_number
            self.updated_at = datetime.now()
            return True
        return False
    
    def deliver(self):
        if self.status == 'shipped':
            self.status = 'delivered'
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel(self, reason: str = ''):
        if self.status not in ['shipped', 'delivered', 'cancelled']:
            self.status = 'cancelled'
            self.notes = f"Cancelled: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def refund(self):
        if self.status == 'delivered':
            self.status = 'refunded'
            self.payment_status = 'refunded'
            self.updated_at = datetime.now()
            return True
        return False
    
    def mark_paid(self, transaction_id: str = None):
        self.payment_status = 'paid'
        if transaction_id:
            self.notes += f" Transaction: {transaction_id}"
        self.updated_at = datetime.now()
        
    def __repr__(self) -> str:
        return f"SalesOrder(id={self.order_id}, user_id={self.user_id}, status={self.status})"


class Review:
    """Product review model"""
    
    def __init__(self, review_id: int, product_id: int, user_id: int,
                 rating: int, title: str, body: str):
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        self.review_id = review_id
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating
        self.title = title
        self.body = body
        self.created_at = datetime.now()
        self.is_verified_purchase = False
        self.helpful_votes = 0
        self.is_approved = True
        
    def mark_helpful(self):
        self.helpful_votes += 1
        
    def __repr__(self) -> str:
        return f"Review(id={self.review_id}, product_id={self.product_id}, rating={self.rating})"


class Coupon:
    """Coupon/Discount model"""
    
    DISCOUNT_TYPES = ['percentage', 'fixed_amount', 'free_shipping']
    
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
        if self.discount_type == 'percentage':
            return order_amount * (self.discount_value / 100)
        elif self.discount_type == 'fixed_amount':
            return min(self.discount_value, order_amount)
        return Decimal('0')
    
    def use(self):
        self.current_uses += 1
        
    def __repr__(self) -> str:
        return f"Coupon(code={self.code}, type={self.discount_type}, value={self.discount_value})"


class Wishlist:
    """Wishlist model"""
    
    def __init__(self, wishlist_id: int, user_id: int, name: str = 'My Wishlist'):
        self.wishlist_id = wishlist_id
        self.user_id = user_id
        self.name = name
        self.items = []
        self.created_at = datetime.now()
        self.is_public = False
        
    def add_item(self, product_id: int, variant_id: int = None):
        for item in self.items:
            if item['product_id'] == product_id and item.get('variant_id') == variant_id:
                return False  # Already in wishlist
        self.items.append({
            'product_id': product_id,
            'variant_id': variant_id,
            'added_at': datetime.now()
        })
        return True
    
    def remove_item(self, product_id: int, variant_id: int = None):
        self.items = [
            item for item in self.items
            if not (item['product_id'] == product_id and item.get('variant_id') == variant_id)
        ]
        
    def __repr__(self) -> str:
        return f"Wishlist(id={self.wishlist_id}, user_id={self.user_id}, items={len(self.items)})"


class Notification:
    """Notification model"""
    
    TYPES = ['order_update', 'price_drop', 'back_in_stock', 'promotion', 'system']
    
    def __init__(self, notification_id: int, user_id: int, 
                 notification_type: str, title: str, message: str):
        self.notification_id = notification_id
        self.user_id = user_id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.is_read = False
        self.created_at = datetime.now()
        
    def mark_read(self):
        self.is_read = True
        
    def __repr__(self) -> str:
        return f"Notification(id={self.notification_id}, type={self.notification_type})"


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """User management service"""
    
    def __init__(self):
        self._users = {}
        self._next_id = 1
        self._email_index = {}
        self._username_index = {}
        
    def register(self, username: str, email: str, password: str,
                 first_name: str = '', last_name: str = '',
                 user_type: str = 'customer') -> tuple:
        """Register a new user"""
        if username in self._username_index:
            return None, "Username already exists"
        if email in self._email_index:
            return None, "Email already registered"
        if len(password) < 8:
            return None, "Password must be at least 8 characters"
            
        user = UserProfile(
            user_id=self._next_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type
        )
        import hashlib
        user._password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        self._users[self._next_id] = user
        self._email_index[email] = self._next_id
        self._username_index[username] = self._next_id
        self._next_id += 1
        
        return user, "Registration successful"
    
    def login(self, username: str, password: str) -> tuple:
        """Authenticate user"""
        import hashlib
        user_id = self._username_index.get(username)
        if not user_id:
            return None, "Invalid credentials"
            
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return None, "Account not found or inactive"
            
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user._password_hash != password_hash:
            return None, "Invalid credentials"
            
        user.last_login = datetime.now()
        return user, "Login successful"
    
    def get_user(self, user_id: int) -> UserProfile:
        return self._users.get(user_id)
    
    def update_profile(self, user_id: int, **kwargs) -> tuple:
        user = self._users.get(user_id)
        if not user:
            return None, "User not found"
            
        allowed_fields = ['first_name', 'last_name', 'phone', 'address']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(user, field, value)
                
        return user, "Profile updated"
    
    def deactivate_user(self, user_id: int) -> bool:
        user = self._users.get(user_id)
        if user:
            user.is_active = False
            return True
        return False
    
    def get_all_users(self, user_type: str = None) -> list:
        users = list(self._users.values())
        if user_type:
            users = [u for u in users if u.user_type == user_type]
        return users
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple:
        import hashlib
        user = self._users.get(user_id)
        if not user:
            return False, "User not found"
            
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        if user._password_hash != old_hash:
            return False, "Current password is incorrect"
            
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"
            
        user._password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        return True, "Password changed successfully"


class ProductService:
    """Product management service"""
    
    def __init__(self):
        self._products = {}
        self._categories = {}
        self._variants = {}
        self._reviews = {}
        self._next_product_id = 1
        self._next_category_id = 1
        self._next_variant_id = 1
        self._next_review_id = 1
        
    def create_product(self, name: str, description: str, price: Decimal,
                       category_id: int, **kwargs) -> Product:
        product = Product(
            product_id=self._next_product_id,
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            **kwargs
        )
        self._products[self._next_product_id] = product
        self._next_product_id += 1
        return product
    
    def create_category(self, name: str, parent_id: int = None,
                        description: str = '') -> Category:
        category = Category(
            category_id=self._next_category_id,
            name=name,
            parent_id=parent_id,
            description=description
        )
        self._categories[self._next_category_id] = category
        
        if parent_id and parent_id in self._categories:
            self._categories[parent_id].add_child(category)
            
        self._next_category_id += 1
        return category
    
    def add_variant(self, product_id: int, attributes: dict,
                    price_modifier: Decimal = Decimal('0'),
                    sku: str = '') -> ProductVariant:
        variant = ProductVariant(
            variant_id=self._next_variant_id,
            product_id=product_id,
            attributes=attributes,
            price_modifier=price_modifier,
            sku=sku
        )
        self._variants[self._next_variant_id] = variant
        self._next_variant_id += 1
        return variant
    
    def search_products(self, query: str = '', category_id: int = None,
                        min_price: Decimal = None, max_price: Decimal = None,
                        brand: str = None, sort_by: str = 'relevance') -> list:
        products = [p for p in self._products.values() if p.is_active]
        
        if query:
            query_lower = query.lower()
            products = [
                p for p in products
                if query_lower in p.name.lower() or 
                   query_lower in p.description.lower() or
                   query_lower in p.brand.lower()
            ]
            
        if category_id:
            products = [p for p in products if p.category_id == category_id]
            
        if min_price is not None:
            products = [p for p in products if p.get_discounted_price() >= min_price]
            
        if max_price is not None:
            products = [p for p in products if p.get_discounted_price() <= max_price]
            
        if brand:
            products = [p for p in products if p.brand.lower() == brand.lower()]
            
        if sort_by == 'price_asc':
            products.sort(key=lambda p: p.get_discounted_price())
        elif sort_by == 'price_desc':
            products.sort(key=lambda p: p.get_discounted_price(), reverse=True)
        elif sort_by == 'rating':
            products.sort(key=lambda p: p.rating, reverse=True)
        elif sort_by == 'newest':
            products.sort(key=lambda p: p.created_at, reverse=True)
            
        return products
    
    def get_product(self, product_id: int) -> Product:
        return self._products.get(product_id)
    
    def update_product(self, product_id: int, **kwargs) -> tuple:
        product = self._products.get(product_id)
        if not product:
            return None, "Product not found"
            
        allowed_fields = ['name', 'description', 'price', 'brand', 
                          'discount_percentage', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(product, field, value)
        product.updated_at = datetime.now()
        return product, "Product updated"
    
    def add_review(self, product_id: int, user_id: int, rating: int,
                   title: str, body: str) -> tuple:
        product = self._products.get(product_id)
        if not product:
            return None, "Product not found"
            
        review = Review(
            review_id=self._next_review_id,
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=body
        )
        
        if product_id not in self._reviews:
            self._reviews[product_id] = []
        self._reviews[product_id].append(review)
        product.update_rating(rating)
        
        self._next_review_id += 1
        return review, "Review added"
    
    def get_product_reviews(self, product_id: int) -> list:
        return self._reviews.get(product_id, [])
    
    def get_category_tree(self) -> list:
        root_categories = [
            c for c in self._categories.values() 
            if c.parent_id is None
        ]
        return root_categories
    
    def get_featured_products(self, limit: int = 10) -> list:
        products = [p for p in self._products.values() if p.is_active]
        products.sort(key=lambda p: p.rating * p.review_count, reverse=True)
        return products[:limit]


class InventoryService:
    """Inventory management service"""
    
    def __init__(self):
        self._inventory = {}
        self._warehouses = {}
        self._suppliers = {}
        self._purchase_orders = {}
        self._next_inventory_id = 1
        self._next_warehouse_id = 1
        self._next_supplier_id = 1
        self._next_po_id = 1
        
    def create_warehouse(self, name: str, location: str,
                         capacity: int = 10000,
                         manager_id: int = None) -> Warehouse:
        warehouse = Warehouse(
            warehouse_id=self._next_warehouse_id,
            name=name,
            location=location,
            capacity=capacity,
            manager_id=manager_id
        )
        self._warehouses[self._next_warehouse_id] = warehouse
        self._next_warehouse_id += 1
        return warehouse
    
    def create_supplier(self, name: str, email: str, **kwargs) -> Supplier:
        supplier = Supplier(
            supplier_id=self._next_supplier_id,
            name=name,
            email=email,
            **kwargs
        )
        self._suppliers[self._next_supplier_id] = supplier
        self._next_supplier_id += 1
        return supplier
    
    def add_inventory(self, product_id: int, warehouse_id: int,
                      quantity: int = 0, reorder_point: int = 10,
                      reorder_quantity: int = 100,
                      variant_id: int = None) -> Inventory:
        # Check if inventory already exists
        for inv in self._inventory.values():
            if (inv.product_id == product_id and 
                inv.warehouse_id == warehouse_id and
                inv.variant_id == variant_id):
                inv.add_stock(quantity)
                return inv
                
        inventory = Inventory(
            inventory_id=self._next_inventory_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity,
            variant_id=variant_id
        )
        self._inventory[self._next_inventory_id] = inventory
        
        warehouse = self._warehouses.get(warehouse_id)
        if warehouse:
            warehouse.current_stock_count += quantity
            
        self._next_inventory_id += 1
        return inventory
    
    def get_product_inventory(self, product_id: int, 
                               warehouse_id: int = None) -> list:
        inventories = [
            inv for inv in self._inventory.values()
            if inv.product_id == product_id
        ]
        if warehouse_id:
            inventories = [inv for inv in inventories if inv.warehouse_id == warehouse_id]
        return inventories
    
    def get_total_stock(self, product_id: int, variant_id: int = None) -> int:
        inventories = self.get_product_inventory(product_id)
        if variant_id:
            inventories = [inv for inv in inventories if inv.variant_id == variant_id]
        return sum(inv.get_available_quantity() for inv in inventories)
    
    def reserve_stock(self, product_id: int, quantity: int,
                      warehouse_id: int = None,
                      variant_id: int = None) -> bool:
        inventories = self.get_product_inventory(product_id)
        if warehouse_id:
            inventories = [inv for inv in inventories if inv.warehouse_id == warehouse_id]
        if variant_id:
            inventories = [inv for inv in inventories if inv.variant_id == variant_id]
            
        remaining = quantity
        for inv in inventories:
            available = inv.get_available_quantity()
            if available > 0:
                reserve_amount = min(available, remaining)
                inv.reserve_stock(reserve_amount)
                remaining -= reserve_amount
                if remaining <= 0:
                    return True
        return remaining <= 0
    
    def fulfill_order(self, product_id: int, quantity: int,
                      variant_id: int = None) -> bool:
        inventories = self.get_product_inventory(product_id)
        if variant_id:
            inventories = [inv for inv in inventories if inv.variant_id == variant_id]
            
        remaining = quantity
        for inv in inventories:
            if inv.quantity > 0:
                deduct = min(inv.quantity, remaining)
                inv.remove_stock(deduct, 'sale')
                inv.release_reservation(deduct)
                remaining -= deduct
                if remaining <= 0:
                    return True
        return remaining <= 0
    
    def create_purchase_order(self, supplier_id: int, warehouse_id: int,
                               created_by: int,
                               expected_delivery: datetime = None) -> PurchaseOrder:
        po = PurchaseOrder(
            po_id=self._next_po_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            created_by=created_by,
            expected_delivery=expected_delivery
        )
        self._purchase_orders[self._next_po_id] = po
        self._next_po_id += 1
        return po
    
    def receive_purchase_order(self, po_id: int, received_items: list) -> tuple:
        po = self._purchase_orders.get(po_id)
        if not po:
            return False, "Purchase order not found"
            
        if po.receive_items(received_items):
            for item in received_items:
                self.add_inventory(
                    product_id=item['product_id'],
                    warehouse_id=po.warehouse_id,
                    quantity=item['quantity'],
                    variant_id=item.get('variant_id')
                )
            return True, "Items received and inventory updated"
        return False, "Cannot receive items for this order"
    
    def get_low_stock_items(self) -> list:
        return [inv for inv in self._inventory.values() if inv.needs_reorder()]
    
    def transfer_stock(self, product_id: int, from_warehouse_id: int,
                       to_warehouse_id: int, quantity: int,
                       variant_id: int = None) -> tuple:
        from_inventories = [
            inv for inv in self._inventory.values()
            if inv.product_id == product_id and 
               inv.warehouse_id == from_warehouse_id and
               inv.variant_id == variant_id
        ]
        
        if not from_inventories:
            return False, "Source inventory not found"
            
        from_inv = from_inventories[0]
        if from_inv.get_available_quantity() < quantity:
            return False, "Insufficient stock in source warehouse"
            
        from_inv.remove_stock(quantity, 'transfer_out')
        self.add_inventory(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            quantity=quantity,
            variant_id=variant_id
        )
        return True, "Stock transferred successfully"
    
    def get_inventory_report(self) -> dict:
        report = {
            'total_products': len(set(inv.product_id for inv in self._inventory.values())),
            'total_warehouses': len(self._warehouses),
            'total_stock_value': Decimal('0'),
            'low_stock_items': len(self.get_low_stock_items()),
            'out_of_stock_items': len([inv for inv in self._inventory.values() if inv.quantity == 0]),
            'warehouses': {}
        }
        
        for warehouse_id, warehouse in self._warehouses.items():
            warehouse_inventories = [
                inv for inv in self._inventory.values()
                if inv.warehouse_id == warehouse_id
            ]
            report['warehouses'][warehouse.name] = {
                'total_items': sum(inv.quantity for inv in warehouse_inventories),
                'unique_products': len(set(inv.product_id for inv in warehouse_inventories)),
                'capacity_used': f"{warehouse.current_stock_count}/{warehouse.capacity}"
            }
            
        return report


class CartService:
    """Shopping cart service"""
    
    def __init__(self, inventory_service: InventoryService):
        self._carts = {}
        self._coupons = {}
        self._next_cart_id = 1
        self._next_coupon_id = 1
        self.inventory_service = inventory_service
        
    def get_or_create_cart(self, user_id: int = None, 
                            session_id: str = None) -> Cart:
        # Find existing cart
        for cart in self._carts.values():
            if user_id and cart.user_id == user_id:
                return cart
            if session_id and cart.session_id == session_id:
                return cart
                
        # Create new cart
        cart = Cart(
            cart_id=self._next_cart_id,
            user_id=user_id,
            session_id=session_id
        )
        self._carts[self._next_cart_id] = cart
        self._next_cart_id += 1
        return cart
    
    def add_to_cart(self, cart_id: int, product_id: int, quantity: int,
                    price: Decimal, variant_id: int = None) -> tuple:
        cart = self._carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
            
        # Check stock availability
        available = self.inventory_service.get_total_stock(product_id, variant_id)
        if available < quantity:
            return False, f"Only {available} items available in stock"
            
        cart.add_item(product_id, quantity, price, variant_id)
        return True, "Item added to cart"
    
    def remove_from_cart(self, cart_id: int, product_id: int,
                          variant_id: int = None) -> bool:
        cart = self._carts.get(cart_id)
        if cart:
            cart.remove_item(product_id, variant_id)
            return True
        return False
    
    def update_cart_item(self, cart_id: int, product_id: int,
                          quantity: int, variant_id: int = None) -> tuple:
        cart = self._carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
            
        if quantity > 0:
            available = self.inventory_service.get_total_stock(product_id, variant_id)
            if available < quantity:
                return False, f"Only {available} items available"
                
        cart.update_quantity(product_id, quantity, variant_id)
        return True, "Cart updated"
    
    def apply_coupon(self, cart_id: int, coupon_code: str) -> tuple:
        cart = self._carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
            
        coupon = self._coupons.get(coupon_code.upper())
        if not coupon:
            return False, "Invalid coupon code"
            
        is_valid, message = coupon.is_valid(cart.get_subtotal())
        if not is_valid:
            return False, message
            
        discount = coupon.calculate_discount(cart.get_subtotal())
        cart.apply_coupon(coupon_code, discount)
        return True, f"Coupon applied. Discount: {discount}"
    
    def create_coupon(self, code: str, discount_type: str,
                      discount_value: Decimal, **kwargs) -> Coupon:
        coupon = Coupon(
            coupon_id=self._next_coupon_id,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            **kwargs
        )
        self._coupons[code.upper()] = coupon
        self._next_coupon_id += 1
        return coupon
    
    def merge_carts(self, session_cart_id: int, user_cart_id: int) -> Cart:
        """Merge session cart into user cart after login"""
        session_cart = self._carts.get(session_cart_id)
        user_cart = self._carts.get(user_cart_id)
        
        if session_cart and user_cart:
            for item in session_cart.items:
                user_cart.add_item(
                    item['product_id'],
                    item['quantity'],
                    item['unit_price'],
                    item.get('variant_id')
                )
            del self._carts[session_cart_id]
            
        return user_cart


class OrderService:
    """Order management service"""
    
    def __init__(self, inventory_service: InventoryService,
                 cart_service: CartService):
        self._orders = {}
        self._addresses = {}
        self._next_order_id = 1
        self._next_address_id = 1
        self.inventory_service = inventory_service
        self.cart_service = cart_service
        
    def add_address(self, user_id: int, address_type: str,
                    street: str, city: str, state: str,
                    country: str, postal_code: str,
                    is_default: bool = False) -> Address:
        address = Address(
            address_id=self._next_address_id,
            user_id=user_id,
            address_type=address_type,
            street=street,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            is_default=is_default
        )
        
        if is_default:
            # Remove default from other addresses
            for addr in self._addresses.values():
                if addr.user_id == user_id and addr.address_type == address_type:
                    addr.is_default = False
                    
        self._addresses[self._next_address_id] = address
        self._next_address_id += 1
        return address
    
    def get_user_addresses(self, user_id: int, 
                            address_type: str = None) -> list:
        addresses = [
            addr for addr in self._addresses.values()
            if addr.user_id == user_id
        ]
        if address_type:
            addresses = [addr for addr in addresses if addr.address_type == address_type]
        return addresses
    
    def create_order_from_cart(self, cart_id: int, user_id: int,
                                shipping_address_id: int,
                                billing_address_id: int,
                                payment_method: str = 'credit_card',
                                product_service: 'ProductService' = None) -> tuple:
        cart = self.cart_service._carts.get(cart_id)
        if not cart or not cart.items:
            return None, "Cart is empty"
            
        # Verify addresses
        shipping_addr = self._addresses.get(shipping_address_id)
        billing_addr = self._addresses.get(billing_address_id)
        
        if not shipping_addr or not billing_addr:
            return None, "Invalid address"
            
        # Check stock and reserve
        for item in cart.items:
            available = self.inventory_service.get_total_stock(
                item['product_id'], item.get('variant_id')
            )
            if available < item['quantity']:
                product_name = item['product_id']
                if product_service:
                    product = product_service.get_product(item['product_id'])
                    if product:
                        product_name = product.name
                return None, f"Insufficient stock for product {product_name}"
                
        # Create order
        order = SalesOrder(
            order_id=self._next_order_id,
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id,
            payment_method=payment_method
        )
        
        for item in cart.items:
            product_name = f"Product {item['product_id']}"
            if product_service:
                product = product_service.get_product(item['product_id'])
                if product:
                    product_name = product.name
                    
            order.add_item(
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                product_name=product_name,
                variant_id=item.get('variant_id')
            )
            
        # Apply cart discount
        if cart.discount_amount > 0:
            order.discount_amount = cart.discount_amount
            order.coupon_code = cart.coupon_code
            order._calculate_totals()
            
        # Calculate shipping
        shipping_cost = self._calculate_shipping(order.subtotal)
        order.set_shipping_cost(shipping_cost)
        
        # Calculate tax
        order.set_tax(0.08)  # 8% tax
        
        # Reserve inventory
        for item in cart.items:
            self.inventory_service.reserve_stock(
                item['product_id'],
                item['quantity'],
                variant_id=item.get('variant_id')
            )
            
        self._orders[self._next_order_id] = order
        self._next_order_id += 1
        
        # Clear cart
        cart.clear()
        
        return order, "Order created successfully"
    
    def _calculate_shipping(self, subtotal: Decimal) -> Decimal:
        if subtotal >= Decimal('50'):
            return Decimal('0')  # Free shipping over $50
        return Decimal('5.99')
    
    def confirm_payment(self, order_id: int, 
                         transaction_id: str = None) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
            
        order.mark_paid(transaction_id)
        order.confirm()
        return True, "Payment confirmed"
    
    def process_order(self, order_id: int) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
            
        if order.process():
            # Fulfill inventory
            for item in order.items:
                self.inventory_service.fulfill_order(
                    item['product_id'],
                    item['quantity'],
                    item.get('variant_id')
                )
            return True, "Order is being processed"
        return False, "Cannot process order in current status"
    
    def ship_order(self, order_id: int, tracking_number: str) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
            
        if order.ship(tracking_number):
            return True, f"Order shipped with tracking: {tracking_number}"
        return False, "Cannot ship order in current status"
    
    def deliver_order(self, order_id: int) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
            
        if order.deliver():
            return True, "Order delivered"
        return False, "Cannot mark order as delivered"
    
    def cancel_order(self, order_id: int, reason: str = '') -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
            
        if order.cancel(reason):
            # Release reserved inventory
            for item in order.items:
                inventories = self.inventory_service.get_product_inventory(
                    item['product_id']
                )
                for inv in inventories:
                    inv.release_reservation(item['quantity'])
            return True, "Order cancelled"
        return False, "Cannot cancel order in current status"
    
    def get_user_orders(self, user_id: int, status: str = None) -> list:
        orders = [o for o in self._orders.values() if o.user_id == user_id]
        if status:
            orders = [o for o in orders if o.status == status]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders
    
    def get_order(self, order_id: int) -> SalesOrder:
        return self._orders.get(order_id)
    
    def get_all_orders(self, status: str = None) -> list:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders
    
    def get_order_statistics(self) -> dict:
        orders = list(self._orders.values())
        total_revenue = sum(
            o.total_amount for o in orders 
            if o.payment_status == 'paid'
        )
        return {
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o.status == 'pending']),
            'processing_orders': len([o for o in orders if o.status == 'processing']),
            'shipped_orders': len([o for o in orders if o.status == 'shipped']),
            'delivered_orders': len([o for o in orders if o.status == 'delivered']),
            'cancelled_orders': len([o for o in orders if o.status == 'cancelled']),
            'total_revenue': total_revenue,
            'average_order_value': total_revenue / len(orders) if orders else Decimal('0')
        }


class WishlistService:
    """Wishlist management service"""
    
    def __init__(self):
        self._wishlists = {}
        self._next_id = 1
        
    def get_or_create_wishlist(self, user_id: int, 
                                name: str = 'My Wishlist') -> Wishlist:
        for wishlist in self._wishlists.values():
            if wishlist.user_id == user_id and wishlist.name == name:
                return wishlist
                
        wishlist = Wishlist(
            wishlist_id=self._next_id,
            user_id=user_id,
            name=name
        )
        self._wishlists[self._next_id] = wishlist
        self._next_id += 1
        return wishlist
    
    def add_to_wishlist(self, user_id: int, product_id: int,
                         variant_id: int = None) -> tuple:
        wishlist = self.get_or_create_wishlist(user_id)
        if wishlist.add_item(product_id, variant_id):
            return True, "Added to wishlist"
        return False, "Already in wishlist"
    
    def remove_from_wishlist(self, user_id: int, product_id: int,
                              variant_id: int = None) -> bool:
        for wishlist in self._wishlists.values():
            if wishlist.user_id == user_id:
                wishlist.remove_item(product_id, variant_id)
                return True
        return False
    
    def get_user_wishlists(self, user_id: int) -> list:
        return [w for w in self._wishlists.values() if w.user_id == user_id]


class NotificationService:
    """Notification service"""
    
    def __init__(self):
        self._notifications = {}
        self._next_id = 1
        
    def send_notification(self, user_id: int, notification_type: str,
                           title: str, message: str) -> Notification:
        notification = Notification(
            notification_id=self._next_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message
        )
        
        if user_id not in self._notifications:
            self._notifications[user_id] = []
        self._notifications[user_id].append(notification)
        self._next_id += 1
        return notification
    
    def get_user_notifications(self, user_id: int, 
                                unread_only: bool = False) -> list:
        notifications = self._notifications.get(user_id, [])
        if unread_only:
            notifications = [n for n in notifications if not n.is_read]
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)
    
    def mark_all_read(self, user_id: int):
        for notification in self._notifications.get(user_id, []):
            notification.mark_read()
    
    def send_order_notification(self, user_id: int, order: SalesOrder):
        status_messages = {
            'confirmed': f"Your order {order.order_number} has been confirmed!",
            'processing': f"Your order {order.order_number} is being processed.",
            'shipped': f"Your order {order.order_number} has been shipped! Tracking: {order.tracking_number}",
            'delivered': f"Your order {order.order_number} has been delivered!",
            'cancelled': f"Your order {order.order_number} has been cancelled."
        }
        
        message = status_messages.get(order.status, f"Order {order.order_number} status updated.")
        self.send_notification(
            user_id=user_id,
            notification_type='order_update',
            title=f"Order Update - {order.order_number}",
            message=message
        )


# ============================================================
# MAIN APPLICATION
# ============================================================

class AmazonCloneApp:
    """Main application class that orchestrates all services"""
    
    def __init__(self):
        self.user_service = UserService()
        self.product_service = ProductService()
        self.inventory_service = InventoryService()
        self.cart_service = CartService(self.inventory_service)
        self.order_service = OrderService(self.inventory_service, self.cart_service)
        self.wishlist_service = WishlistService()
        self.notification_service = NotificationService()
        self._current_user = None
        self._session_id = None
        
    def initialize_demo_data(self):
        """Initialize the application with demo data"""
        print("Initializing Amazon Clone with demo data...")
        
        # Create admin user
        admin, msg = self.user_service.register(
            username='admin',
            email='admin@amazonclone.com',
            password='Admin@1234',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        print(f"Admin created: {admin}")
        
        # Create regular users
        user1, _ = self.user_service.register(
            username='john_doe',
            email='john@example.com',
            password='John@1234',
            first_name='John',
            last_name='Doe'
        )
        
        user2, _ = self.user_service.register(
            username='jane_smith',
            email='jane@example.com',
            password='Jane@1234',
            first_name='Jane',
            last_name='Smith'
        )
        
        # Create supplier user
        supplier_user, _ = self.user_service.register(
            username='supplier1',
            email='supplier@techcorp.com',
            password='Supplier@1234',
            first_name='Tech',
            last_name='Corp',
            user_type='supplier'
        )
        
        # Create categories
        electronics = self.product_service.create_category(
            'Electronics', description='Electronic devices and accessories'
        )
        phones = self.product_service.create_category(
            'Smartphones', parent_id=electronics.category_id,
            description='Mobile phones and accessories'
        )
        laptops = self.product_service.create_category(
            'Laptops', parent_id=electronics.category_id,
            description='Laptops and notebooks'
        )
        clothing = self.product_service.create_category(
            'Clothing', description='Fashion and apparel'
        )
        mens = self.product_service.create_category(
            "Men's Clothing", parent_id=clothing.category_id
        )
        womens = self.product_service.create_category(
            "Women's Clothing", parent_id=clothing.category_id
        )
        books = self.product_service.create_category(
            'Books', description='Books and literature'
        )
        
        # Create products
        iphone = self.product_service.create_product(
            name='iPhone 15 Pro',
            description='Latest Apple iPhone with advanced camera system',
            price=Decimal('999.99'),
            category_id=phones.category_id,
            brand='Apple',
            weight=0.187
        )
        iphone.discount_percentage = 5.0
        
        samsung = self.product_service.create_product(
            name='Samsung Galaxy S24',
            description='Samsung flagship smartphone with AI features',
            price=Decimal('899.99'),
            category_id=phones.category_id,
            brand='Samsung',
            weight=0.167
        )
        
        macbook = self.product_service.create_product(
            name='MacBook Pro 14"',
            description='Apple MacBook Pro with M3 chip',
            price=Decimal('1999.99'),
            category_id=laptops.category_id,
            brand='Apple',
            weight=1.6
        )
        macbook.discount_percentage = 10.0
        
        dell_laptop = self.product_service.create_product(
            name='Dell XPS 15',
            description='Dell premium laptop for professionals',
            price=Decimal('1499.99'),
            category_id=laptops.category_id,
            brand='Dell',
            weight=1.86
        )
        
        tshirt = self.product_service.create_product(
            name='Classic Cotton T-Shirt',
            description='Comfortable everyday cotton t-shirt',
            price=Decimal('29.99'),
            category_id=mens.category_id,
            brand='BasicWear'
        )
        
        python_book = self.product_service.create_product(
            name='Python Programming: A Complete Guide',
            description='Comprehensive guide to Python programming',
            price=Decimal('49.99'),
            category_id=books.category_id,
            brand='TechBooks'
        )
        
        # Add product variants
        self.product_service.add_variant(
            product_id=iphone.product_id,
            attributes={'color': 'Natural Titanium', 'storage': '128GB'},
            sku='IPHONE15PRO-NT-128'
        )
        self.product_service.add_variant(
            product_id=iphone.product_id,
            attributes={'color': 'Black Titanium', 'storage': '256GB'},
            price_modifier=Decimal('100'),
            sku='IPHONE15PRO-BT-256'
        )
        
        self.product_service.add_variant(
            product_id=tshirt.product_id,
            attributes={'color': 'White', 'size': 'M'},
            sku='TSHIRT-W-M'
        )
        self.product_service.add_variant(
            product_id=tshirt.product_id,
            attributes={'color': 'Black', 'size': 'L'},
            sku='TSHIRT-B-L'
        )
        
        # Create warehouses
        main_warehouse = self.inventory_service.create_warehouse(
            name='Main Distribution Center',
            location='Seattle, WA',
            capacity=50000,
            manager_id=admin.user_id
        )
        
        east_warehouse = self.inventory_service.create_warehouse(
            name='East Coast Fulfillment',
            location='New York, NY',
            capacity=30000
        )
        
        # Create suppliers
        apple_supplier = self.inventory_service.create_supplier(
            name='Apple Inc.',
            email='supply@apple.com',
            phone='+1-800-275-2273',
            address='One Apple Park Way, Cupertino, CA',
            contact_person='Tim Cook',
            payment_terms='NET30'
        )
        
        samsung_supplier = self.inventory_service.create_supplier(
            name='Samsung Electronics',
            email='supply@samsung.com',
            phone='+1-800-726-7864',
            address='85 Challenger Road, Ridgefield Park, NJ',
            contact_person='Supply Manager',
            payment_terms='NET45'
        )
        
        # Add inventory
        self.inventory_service.add_inventory(
            product_id=iphone.product_id,
            warehouse_id=main_warehouse.warehouse_id,
            quantity=500,
            reorder_point=50,
            reorder_quantity=200
        )
        
        self.inventory_service.add_inventory(
            product_id=samsung.product_id,
            warehouse_id=main_warehouse.warehouse_id,
            quantity=300,
            reorder_point=30,
            reorder_quantity=150
        )
        
        self.inventory_service.add_inventory(
            product_id=macbook.product_id,
            warehouse_id=main_warehouse.warehouse_id,
            quantity=100,
            reorder_point=10,
            reorder_quantity=50
        )
        
        self.inventory_service.add_inventory(
            product_id=dell_laptop.product_id,
            warehouse_id=east_warehouse.warehouse_id,
            quantity=150,
            reorder_point=15,
            reorder_quantity=75
        )
        
        self.inventory_service.add_inventory(
            product_id=tshirt.product_id,
            warehouse_id=main_warehouse.warehouse_id,
            quantity=1000,
            reorder_point=100,
            reorder_quantity=500
        )
        
        self.inventory_service.add_inventory(
            product_id=python_book.product_id,
            warehouse_id=main_warehouse.warehouse_id,
            quantity=200,
            reorder_point=20,
            reorder_quantity=100
        )
        
        # Add reviews
        self.product_service.add_review(
            product_id=iphone.product_id,
            user_id=user1.user_id,
            rating=5,
            title='Amazing phone!',
            body='Best iPhone ever. Camera is incredible.'
        )
        
        self.product_service.add_review(
            product_id=iphone.product_id,
            user_id=user2.user_id,
            rating=4,
            title='Great but expensive',
            body='Excellent phone but the price is steep.'
        )
        
        self.product_service.add_review(
            product_id=macbook.product_id,
            user_id=user1.user_id,
            rating=5,
            title='Best laptop ever',
            body='M3 chip is blazing fast. Battery life is incredible.'
        )
        
        # Create coupons
        self.cart_service.create_coupon(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('50'),
            max_uses=1000
        )
        
        self.cart_service.create_coupon(
            code='WELCOME20',
            discount_type='fixed_amount',
            discount_value=Decimal('20'),
            min_order_amount=Decimal('100'),
            max_uses=500
        )
        
        # Create a purchase order
        po = self.inventory_service.create_purchase_order(
            supplier_id=apple_supplier.supplier_id,
            warehouse_id=main_warehouse.warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=14)
        )
        po.add_item(
            product_id=iphone.product_id,
            quantity=200,
            unit_price=Decimal('750.00')
        )
        po.status = 'pending'
        
        print("Demo data initialized successfully!")
        print(f"Products created: {len(self.product_service._products)}")
        print(f"Categories created: {len(self.product_service._categories)}")
        print(f"Warehouses created: {len(self.inventory_service._warehouses)}")
        print(f"Suppliers created: {len(self.inventory_service._suppliers)}")
        
        return {
            'admin': admin,
            'users': [user1, user2],
            'products': {
                'iphone': iphone,
                'samsung': samsung,
                'macbook': macbook,
                'dell_laptop': dell_laptop,
                'tshirt': tshirt,
                'python_book': python_book
            },
            'warehouses': {
                'main': main_warehouse,
                'east': east_warehouse
            },
            'suppliers': {
                'apple': apple_supplier,
                'samsung': samsung_supplier
            }
        }
    
    def demo_user_flow(self, demo_data: dict):
        """Demonstrate user registration and authentication flow"""
        print("\n" + "="*60)
        print("USER AUTHENTICATION DEMO")
        print("="*60)
        
        # Register new user
        new_user, msg = self.user_service.register(
            username='new_customer',
            email='customer@example.com',
            password='Customer@1234',
            first_name='New',
            last_name='Customer'
        )
        print(f"Registration: {msg}")
        print(f"New user: {new_user}")
        
        # Login
        logged_user, msg = self.user_service.login('new_customer', 'Customer@1234')
        print(f"Login: {msg}")
        
        # Failed login
        _, msg = self.user_service.login('new_customer', 'wrongpassword')
        print(f"Failed login: {msg}")
        
        # Update profile
        updated_user, msg = self.user_service.update_profile(
            new_user.user_id,
            phone='+1-555-0123',
            address='123 Main St, Seattle, WA'
        )
        print(f"Profile update: {msg}")
        
        return new_user
    
    def demo_product_search(self):
        """Demonstrate product search and filtering"""
        print("\n" + "="*60)
        print("PRODUCT SEARCH DEMO")
        print("="*60)
        
        # Search all products
        all_products = self.product_service.search_products()
        print(f"Total products: {len(all_products)}")
        
        # Search by query
        apple_products = self.product_service.search_products(query='apple')
        print(f"Apple products: {[p.name for p in apple_products]}")
        
        # Search by price range
        budget_products = self.product_service.search_products(
            max_price=Decimal('100')
        )
        print(f"Products under $100: {[p.name for p in budget_products]}")
        
        # Search and sort by price
        sorted_products = self.product_service.search_products(sort_by='price_asc')
        print(f"Products by price (asc): {[(p.name, p.get_discounted_price()) for p in sorted_products]}")
        
        # Featured products
        featured = self.product_service.get_featured_products(3)
        print(f"Featured products: {[p.name for p in featured]}")
        
        # Category tree
        tree = self.product_service.get_category_tree()
        print(f"Root categories: {[c.name for c in tree]}")
        for cat in tree:
            if cat.children:
                print(f"  {cat.name} -> {[c.name for c in cat.children]}")
    
    def demo_shopping_cart(self, user: UserProfile, demo_data: dict):
        """Demonstrate shopping cart functionality"""
        print("\n" + "="*60)
        print("SHOPPING CART DEMO")
        print("="*60)
        
        products = demo_data['products']
        
        # Create cart
        cart = self.cart_service.get_or_create_cart(user_id=user.user_id)
        print(f"Cart created: {cart}")
        
        # Add items
        success, msg = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=products['iphone'].product_id,
            quantity=1,
            price=products['iphone'].get_discounted_price()
        )
        print(f"Add iPhone: {msg}")
        
        success, msg = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=products['macbook'].product_id,
            quantity=1,
            price=products['macbook'].get_discounted_price()
        )
        print(f"Add MacBook: {msg}")
        
        success, msg = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=products['tshirt'].product_id,
            quantity=2,
            price=products['tshirt'].price
        )
        print(f"Add T-Shirt x2: {msg}")
        
        print(f"Cart items: {cart.get_item_count()}")
        print(f"Cart subtotal: ${cart.get_subtotal()}")
        
        # Apply coupon
        success, msg = self.cart_service.apply_coupon(cart.cart_id, 'SAVE10')
        print(f"Apply coupon SAVE10: {msg}")
        print(f"Cart total after discount: ${cart.get_total()}")
        
        # Update quantity
        success, msg = self.cart_service.update_cart_item(
            cart_id=cart.cart_id,
            product_id=products['tshirt'].product_id,
            quantity=3
        )
        print(f"Update T-Shirt quantity to 3: {msg}")
        
        # Remove item
        self.cart_service.remove_from_cart(
            cart_id=cart.cart_id,
            product_id=products['tshirt'].product_id
        )
        print(f"Removed T-Shirt. Items remaining: {cart.get_item_count()}")
        
        return cart
    
    def demo_order_flow(self, user: UserProfile, cart: Cart, demo_data: dict):
        """Demonstrate order creation and management"""
        print("\n" + "="*60)
        print("ORDER MANAGEMENT DEMO")
        print("="*60)
        
        # Add address
        shipping_addr = self.order_service.add_address(
            user_id=user.user_id,
            address_type='shipping',
            street='456 Oak Avenue',
            city='Seattle',
            state='WA',
            country='USA',
            postal_code='98101',
            is_default=True
        )
        print(f"Shipping address: {shipping_addr.get_full_address()}")
        
        billing_addr = self.order_service.add_address(
            user_id=user.user_id,
            address_type='billing',
            street='456 Oak Avenue',
            city='Seattle',
            state='WA',
            country='USA',
            postal_code='98101',
            is_default=True
        )
        
        # Create order from cart
        order, msg = self.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=user.user_id,
            shipping_address_id=shipping_addr.address_id,
            billing_address_id=billing_addr.address_id,
            payment_method='credit_card',
            product_service=self.product_service
        )
        
        if order:
            print(f"Order created: {order.order_number}")
            print(f"Order status: {order.status}")
            print(f"Subtotal: ${order.subtotal}")
            print(f"Shipping: ${order.shipping_cost}")
            print(f"Tax: ${order.tax_amount:.2f}")
            print(f"Discount: ${order.discount_amount}")
            print(f"Total: ${order.total_amount:.2f}")
            
            # Process payment
            success, msg = self.order_service.confirm_payment(
                order.order_id, 'TXN-123456789'
            )
            print(f"Payment: {msg}")
            
            # Process order
            success, msg = self.order_service.process_order(order.order_id)
            print(f"Processing: {msg}")
            
            # Ship order
            success, msg = self.order_service.ship_order(
                order.order_id, 'TRACK-987654321'
            )
            print(f"Shipping: {msg}")
            
            # Send notification
            self.notification_service.send_order_notification(user.user_id, order)
            
            # Deliver order
            success, msg = self.order_service.deliver_order(order.order_id)
            print(f"Delivery: {msg}")
            
            # Send notification
            self.notification_service.send_order_notification(user.user_id, order)
            
            print(f"Final order status: {order.status}")
            
        else:
            print(f"Order creation failed: {msg}")
            
        return order
    
    def demo_inventory_management(self, demo_data: dict):
        """Demonstrate inventory management"""
        print("\n" + "="*60)
        print("INVENTORY MANAGEMENT DEMO")
        print("="*60)
        
        products = demo_data['products']
        warehouses = demo_data['warehouses']
        suppliers = demo_data['suppliers']
        admin = demo_data['admin']
        
        # Check stock levels
        iphone_stock = self.inventory_service.get_total_stock(
            products['iphone'].product_id
        )
        print(f"iPhone stock: {iphone_stock}")
        
        macbook_stock = self.inventory_service.get_total_stock(
            products['macbook'].product_id
        )
        print(f"MacBook stock: {macbook_stock}")
        
        # Create purchase order
        po = self.inventory_service.create_purchase_order(
            supplier_id=suppliers['apple'].supplier_id,
            warehouse_id=warehouses['main'].warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=7)
        )
        
        po.add_item(
            product_id=products['macbook'].product_id,
            quantity=50,
            unit_price=Decimal('1500.00')
        )
        po.add_item(
            product_id=products['iphone'].product_id,
            quantity=100,
            unit_price=Decimal('750.00')
        )
        
        print(f"Purchase Order created: PO-{po.po_id}")
        print(f"PO Total: ${po.total_amount}")
        
        # Approve PO
        po.status = 'pending'
        po.approve(admin.user_id)
        print(f"PO Status after approval: {po.status}")
        
        # Mark as ordered
        po.mark_ordered()
        print(f"PO Status after ordering: {po.status}")
        
        # Receive items
        success, msg = self.inventory_service.receive_purchase_order(
            po_id=po.po_id,
            received_items=[
                {'product_id': products['macbook'].product_id, 'quantity': 50},
                {'product_id': products['iphone'].product_id, 'quantity': 100}
            ]
        )
        print(f"Receive PO: {msg}")
        
        # Check updated stock
        new_macbook_stock = self.inventory_service.get_total_stock(
            products['macbook'].product_id
        )
        print(f"MacBook stock after receiving: {new_macbook_stock}")
        
        # Stock transfer
        success, msg = self.inventory_service.transfer_stock(
            product_id=products['iphone'].product_id,
            from_warehouse_id=warehouses['main'].warehouse_id,
            to_warehouse_id=warehouses['east'].warehouse_id,
            quantity=50
        )
        print(f"Stock transfer: {msg}")
        
        # Low stock report
        low_stock = self.inventory_service.get_low_stock_items()
        print(f"Low stock items: {len(low_stock)}")
        
        # Inventory report
        report = self.inventory_service.get_inventory_report()
        print(f"Inventory Report:")
        print(f"  Total products: {report['total_products']}")
        print(f"  Total warehouses: {report['total_warehouses']}")
        print(f"  Low stock items: {report['low_stock_items']}")
        print(f"  Out of stock: {report['out_of_stock_items']}")
        for wh_name, wh_data in report['warehouses'].items():
            print(f"  {wh_name}: {wh_data['total_items']} items, {wh_data['unique_products']} products")
    
    def demo_wishlist(self, user: UserProfile, demo_data: dict):
        """Demonstrate wishlist functionality"""
        print("\n" + "="*60)
        print("WISHLIST DEMO")
        print("="*60)
        
        products = demo_data['products']
        
        # Add to wishlist
        success, msg = self.wishlist_service.add_to_wishlist(
            user_id=user.user_id,
            product_id=products['samsung'].product_id
        )
        print(f"Add Samsung to wishlist: {msg}")
        
        success, msg = self.wishlist_service.add_to_wishlist(
            user_id=user.user_id,
            product_id=products['dell_laptop'].product_id
        )
        print(f"Add Dell to wishlist: {msg}")
        
        # Try adding duplicate
        success, msg = self.wishlist_service.add_to_wishlist(
            user_id=user.user_id,
            product_id=products['samsung'].product_id
        )
        print(f"Add Samsung again: {msg}")
        
        # Get wishlist
        wishlists = self.wishlist_service.get_user_wishlists(user.user_id)
        for wl in wishlists:
            print(f"Wishlist '{wl.name}': {len(wl.items)} items")
    
    def demo_notifications(self, user: UserProfile):
        """Demonstrate notification system"""
        print("\n" + "="*60)
        print("NOTIFICATIONS DEMO")
        print("="*60)
        
        # Send various notifications
        self.notification_service.send_notification(
            user_id=user.user_id,
            notification_type='promotion',
            title='Flash Sale!',
            message='50% off on all electronics today only!'
        )
        
        self.notification_service.send_notification(
            user_id=user.user_id,
            notification_type='back_in_stock',
            title='Item Back in Stock',
            message='The item in your wishlist is now available!'
        )
        
        # Get notifications
        notifications = self.notification_service.get_user_notifications(user.user_id)
        print(f"Total notifications: {len(notifications)}")
        
        unread = self.notification_service.get_user_notifications(
            user.user_id, unread_only=True
        )
        print(f"Unread notifications: {len(unread)}")
        
        # Mark all as read
        self.notification_service.mark_all_read(user.user_id)
        unread_after = self.notification_service.get_user_notifications(
            user.user_id, unread_only=True
        )
        print(f"Unread after marking all read: {len(unread_after)}")
    
    def demo_admin_dashboard(self, demo_data: dict):
        """Demonstrate admin dashboard functionality"""
        print("\n" + "="*60)
        print("ADMIN DASHBOARD DEMO")
        print("="*60)
        
        # Order statistics
        stats = self.order_service.get_order_statistics()
        print("Order Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # User management
        all_users = self.user_service.get_all_users()
        print(f"\nTotal users: {len(all_users)}")
        
        customers = self.user_service.get_all_users(user_type='customer')
        print(f"Customers: {len(customers)}")
        
        # All orders
        all_orders = self.order_service.get_all_orders()
        print(f"\nTotal orders: {len(all_orders)}")
        
        # Product management
        all_products = self.product_service.search_products()
        print(f"Total active products: {len(all_products)}")
        
        # Inventory report
        inv_report = self.inventory_service.get_inventory_report()
        print(f"\nInventory Summary:")
        print(f"  Products tracked: {inv_report['total_products']}")
        print(f"  Active warehouses: {inv_report['total_warehouses']}")
        print(f"  Low stock alerts: {inv_report['low_stock_items']}")
    
    def run_demo(self):
        """Run complete application demo"""
        print("="*60)
        print("AMAZON CLONE - COMPLETE DEMO")
        print("="*60)
        
        # Initialize demo data
        demo_data = self.initialize_demo_data()
        
        # User flow demo
        new_user = self.demo_user_flow(demo_data)
        
        # Product search demo
        self.demo_product_search()
        
        # Shopping cart demo
        cart = self.demo_shopping_cart(new_user, demo_data)
        
        # Order flow demo
        order = self.demo_order_flow(new_user, cart, demo_data)
        
        # Inventory management demo
        self.demo_inventory_management(demo_data)
        
        # Wishlist demo
        self.demo_wishlist(new_user, demo_data)
        
        # Notifications demo
        self.demo_notifications(new_user)
        
        # Admin dashboard demo
        self.demo_admin_dashboard(demo_data)
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        return True


# ============================================================
# DJANGO VIEWS (Simulated)
# ============================================================

class ViewResponse:
    """Simulated HTTP response"""
    
    def __init__(self, status_code: int, data: dict = None, 
                 redirect_url: str = None):
        self.status_code = status_code
        self.data = data or {}
        self.redirect_url = redirect_url
        
    def __repr__(self) -> str:
        return f"Response(status={self.status_code}, data_keys={list(self.data.keys())})"


class BaseView:
    """Base view class"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        
    def get_context(self, user_id: int = None) -> dict:
        context = {}
        if user_id:
            user = self.app.user_service.get_user(user_id)
            if user:
                context['user'] = user
                cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
                context['cart_count'] = cart.get_item_count()
                unread_notifications = self.app.notification_service.get_user_notifications(
                    user_id, unread_only=True
                )
                context['unread_notifications'] = len(unread_notifications)
        return context


class AuthView(BaseView):
    """Authentication views"""
    
    def register(self, username: str, email: str, password: str,
                 confirm_password: str, first_name: str = '',
                 last_name: str = '') -> ViewResponse:
        if password != confirm_password:
            return ViewResponse(400, {'error': 'Passwords do not match'})
            
        user, msg = self.app.user_service.register(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        if user:
            self.app.notification_service.send_notification(
                user_id=user.user_id,
                notification_type='system',
                title='Welcome to Amazon Clone!',
                message=f'Welcome {user.get_full_name() or username}! Start shopping now.'
            )
            return ViewResponse(201, {'user': user, 'message': msg}, 
                              redirect_url='/')
        return ViewResponse(400, {'error': msg})
    
    def login(self, username: str, password: str) -> ViewResponse:
        user, msg = self.app.user_service.login(username, password)
        if user:
            return ViewResponse(200, {'user': user, 'message': msg},
                              redirect_url='/')
        return ViewResponse(401, {'error': msg})
    
    def logout(self, user_id: int) -> ViewResponse:
        return ViewResponse(200, {'message': 'Logged out successfully'},
                          redirect_url='/auth/login/')
    
    def change_password(self, user_id: int, old_password: str,
                         new_password: str, confirm_password: str) -> ViewResponse:
        if new_password != confirm_password:
            return ViewResponse(400, {'error': 'Passwords do not match'})
            
        success, msg = self.app.user_service.change_password(
            user_id, old_password, new_password
        )
        if success:
            return ViewResponse(200, {'message': msg})
        return ViewResponse(400, {'error': msg})


class ProductView(BaseView):
    """Product views"""
    
    def list_products(self, query: str = '', category_id: int = None,
                       min_price: float = None, max_price: float = None,
                       brand: str = None, sort_by: str = 'relevance',
                       page: int = 1, per_page: int = 20,
                       user_id: int = None) -> ViewResponse:
        products = self.app.product_service.search_products(
            query=query,
            category_id=category_id,
            min_price=Decimal(str(min_price)) if min_price else None,
            max_price=Decimal(str(max_price)) if max_price else None,
            brand=brand,
            sort_by=sort_by
        )
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_products = products[start:end]
        
        context = self.get_context(user_id)
        context.update({
            'products': paginated_products,
            'total_count': len(products),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(products) + per_page - 1) // per_page,
            'categories': self.app.product_service.get_category_tree(),
            'query': query
        })
        
        return ViewResponse(200, context)
    
    def product_detail(self, product_id: int, 
                        user_id: int = None) -> ViewResponse:
        product = self.app.product_service.get_product(product_id)
        if not product:
            return ViewResponse(404, {'error': 'Product not found'})
            
        reviews = self.app.product_service.get_product_reviews(product_id)
        stock = self.app.inventory_service.get_total_stock(product_id)
        
        context = self.get_context(user_id)
        context.update({
            'product': product,
            'reviews': reviews,
            'stock': stock,
            'in_stock': stock > 0,
            'related_products': self.app.product_service.search_products(
                category_id=product.category_id
            )[:4]
        })
        
        return ViewResponse(200, context)
    
    def add_review(self, product_id: int, user_id: int, rating: int,
                    title: str, body: str) -> ViewResponse:
        review, msg = self.app.product_service.add_review(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=body
        )
        
        if review:
            return ViewResponse(201, {'review': review, 'message': msg})
        return ViewResponse(400, {'error': msg})


class CartView(BaseView):
    """Cart views"""
    
    def view_cart(self, user_id: int) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        
        # Enrich cart items with product details
        enriched_items = []
        for item in cart.items:
            product = self.app.product_service.get_product(item['product_id'])
            if product:
                enriched_items.append({
                    **item,
                    'product_name': product.name,
                    'product_image': product.images[0]['url'] if product.images else None
                })
        
        context = self.get_context(user_id)
        context.update({
            'cart': cart,
            'items': enriched_items,
            'subtotal': cart.get_subtotal(),
            'total': cart.get_total(),
            'discount': cart.discount_amount
        })
        
        return ViewResponse(200, context)
    
    def add_to_cart(self, user_id: int, product_id: int, quantity: int,
                     variant_id: int = None) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        product = self.app.product_service.get_product(product_id)
        
        if not product:
            return ViewResponse(404, {'error': 'Product not found'})
            
        success, msg = self.app.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=product_id,
            quantity=quantity,
            price=product.get_discounted_price(),
            variant_id=variant_id
        )
        
        if success:
            return ViewResponse(200, {
                'message': msg,
                'cart_count': cart.get_item_count()
            })
        return ViewResponse(400, {'error': msg})
    
    def update_cart(self, user_id: int, product_id: int, quantity: int,
                     variant_id: int = None) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        success, msg = self.app.cart_service.update_cart_item(
            cart_id=cart.cart_id,
            product_id=product_id,
            quantity=quantity,
            variant_id=variant_id
        )
        
        if success:
            return ViewResponse(200, {
                'message': msg,
                'cart_total': cart.get_total(),
                'cart_count': cart.get_item_count()
            })
        return ViewResponse(400, {'error': msg})
    
    def remove_from_cart(self, user_id: int, product_id: int,
                          variant_id: int = None) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        self.app.cart_service.remove_from_cart(
            cart_id=cart.cart_id,
            product_id=product_id,
            variant_id=variant_id
        )
        return ViewResponse(200, {
            'message': 'Item removed',
            'cart_count': cart.get_item_count()
        })
    
    def apply_coupon(self, user_id: int, coupon_code: str) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        success, msg = self.app.cart_service.apply_coupon(cart.cart_id, coupon_code)
        
        if success:
            return ViewResponse(200, {
                'message': msg,
                'discount': cart.discount_amount,
                'total': cart.get_total()
            })
        return ViewResponse(400, {'error': msg})


class OrderView(BaseView):
    """Order views"""
    
    def checkout(self, user_id: int, shipping_address_id: int,
                  billing_address_id: int,
                  payment_method: str = 'credit_card') -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        
        if not cart.items:
            return ViewResponse(400, {'error': 'Cart is empty'})
            
        order, msg = self.app.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id,
            payment_method=payment_method,
            product_service=self.app.product_service
        )
        
        if order:
            return ViewResponse(201, {
                'order': order,
                'message': msg,
                'order_number': order.order_number
            }, redirect_url=f'/orders/{order.order_id}/')
        return ViewResponse(400, {'error': msg})
    
    def order_list(self, user_id: int, status: str = None) -> ViewResponse:
        orders = self.app.order_service.get_user_orders(user_id, status)
        context = self.get_context(user_id)
        context['orders'] = orders
        return ViewResponse(200, context)
    
    def order_detail(self, user_id: int, order_id: int) -> ViewResponse:
        order = self.app.order_service.get_order(order_id)
        
        if not order:
            return ViewResponse(404, {'error': 'Order not found'})
            
        if order.user_id != user_id:
            return ViewResponse(403, {'error': 'Access denied'})
            
        context = self.get_context(user_id)
        context.update({
            'order': order,
            'shipping_address': self.app.order_service._addresses.get(
                order.shipping_address_id
            ),
            'billing_address': self.app.order_service._addresses.get(
                order.billing_address_id
            )
        })
        
        return ViewResponse(200, context)
    
    def cancel_order(self, user_id: int, order_id: int,
                      reason: str = '') -> ViewResponse:
        order = self.app.order_service.get_order(order_id)
        
        if not order:
            return ViewResponse(404, {'error': 'Order not found'})
            
        if order.user_id != user_id:
            return ViewResponse(403, {'error': 'Access denied'})
            
        success, msg = self.app.order_service.cancel_order(order_id, reason)
        
        if success:
            self.app.notification_service.send_order_notification(user_id, order)
            return ViewResponse(200, {'message': msg})
        return ViewResponse(400, {'error': msg})


class AdminView(BaseView):
    """Admin views"""
    
    def _check_admin(self, user_id: int) -> bool:
        user = self.app.user_service.get_user(user_id)
        return user and user.user_type == 'admin'
    
    def dashboard(self, admin_id: int) -> ViewResponse:
        if not self._check_admin(admin_id):
            return ViewResponse(403, {'error': 'Admin access required'})
            
        order_stats = self.app.order_service.get_order_statistics()
        inv_report = self.app.inventory_service.get_inventory_report()
        
        return ViewResponse(200, {
            'order_stats': order_stats,
            'inventory_report': inv_report,
            'total_users': len(self.app.user_service.get_all_users()),
            'total_products': len(self.app.product_service.search_products()),
            'low_stock_alerts': len(self.app.inventory_service.get_low_stock_items())
        })
    
    def manage_products(self, admin_id: int, action: str,
                         product_data: dict = None,
                         product_id: int = None) -> ViewResponse:
        if not self._check_admin(admin_id):
            return ViewResponse(403, {'error': 'Admin access required'})
            
        if action == 'create' and product_data:
            product = self.app.product_service.create_product(**product_data)
            return ViewResponse(201, {'product': product})
            
        elif action == 'update' and product_id and product_data:
            product, msg = self.app.product_service.update_product(
                product_id, **product_data
            )
            if product:
                return ViewResponse(200, {'product': product, 'message': msg})
            return ViewResponse(404, {'error': msg})
            
        elif action == 'delete' and product_id:
            product, msg = self.app.product_service.update_product(
                product_id, is_active=False
            )
            if product:
                return ViewResponse(200, {'message': 'Product deactivated'})
            return ViewResponse(404, {'error': msg})
            
        return ViewResponse(400, {'error': 'Invalid action'})
    
    def manage_orders(self, admin_id: int, action: str,
                       order_id: int, **kwargs) -> ViewResponse:
        if not self._check_admin(admin_id):
            return ViewResponse(403, {'error': 'Admin access required'})
            
        if action == 'process':
            success, msg = self.app.order_service.process_order(order_id)
        elif action == 'ship':
            tracking = kwargs.get('tracking_number', 'TRACK-000000')
            success, msg = self.app.order_service.ship_order(order_id, tracking)
        elif action == 'deliver':
            success, msg = self.app.order_service.deliver_order(order_id)
        elif action == 'cancel':
            reason = kwargs.get('reason', '')
            success, msg = self.app.order_service.cancel_order(order_id, reason)
        else:
            return ViewResponse(400, {'error': 'Invalid action'})
            
        if success:
            order = self.app.order_service.get_order(order_id)
            if order:
                self.app.notification_service.send_order_notification(
                    order.user_id, order
                )
            return ViewResponse(200, {'message': msg})
        return ViewResponse(400, {'error': msg})
    
    def manage_inventory(self, admin_id: int, action: str,
                          **kwargs) -> ViewResponse:
        if not self._check_admin(admin_id):
            return ViewResponse(403, {'error': 'Admin access required'})
            
        if action == 'add_stock':
            inventory = self.app.inventory_service.add_inventory(
                product_id=kwargs['product_id'],
                warehouse_id=kwargs['warehouse_id'],
                quantity=kwargs['quantity']
            )
            return ViewResponse(200, {'inventory': inventory})
            
        elif action == 'transfer':
            success, msg = self.app.inventory_service.transfer_stock(
                product_id=kwargs['product_id'],
                from_warehouse_id=kwargs['from_warehouse_id'],
                to_warehouse_id=kwargs['to_warehouse_id'],
                quantity=kwargs['quantity']
            )
            if success:
                return ViewResponse(200, {'message': msg})
            return ViewResponse(400, {'error': msg})
            
        elif action == 'report':
            report = self.app.inventory_service.get_inventory_report()
            return ViewResponse(200, {'report': report})
            
        return ViewResponse(400, {'error': 'Invalid action'})
    
    def manage_users(self, admin_id: int, action: str,
                      user_id: int = None, **kwargs) -> ViewResponse:
        if not self._check_admin(admin_id):
            return ViewResponse(403, {'error': 'Admin access required'})
            
        if action == 'list':
            users = self.app.user_service.get_all_users(
                user_type=kwargs.get('user_type')
            )
            return ViewResponse(200, {'users': users})
            
        elif action == 'deactivate' and user_id:
            success = self.app.user_service.deactivate_user(user_id)
            if success:
                return ViewResponse(200, {'message': 'User deactivated'})
            return ViewResponse(404, {'error': 'User not found'})
            
        elif action == 'get' and user_id:
            user = self.app.user_service.get_user(user_id)
            if user:
                return ViewResponse(200, {'user': user})
            return ViewResponse(404, {'error': 'User not found'})
            
        return ViewResponse(400, {'error': 'Invalid action'})


# ============================================================
# URL ROUTER (Simulated)
# ============================================================

class URLRouter:
    """Simple URL router"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        self.auth_view = AuthView(app)
        self.product_view = ProductView(app)
        self.cart_view = CartView(app)
        self.order_view = OrderView(app)
        self.admin_view = AdminView(app)
        
        self.routes = {
            'GET /': self._home,
            'POST /auth/register/': self._register,
            'POST /auth/login/': self._login,
            'POST /auth/logout/': self._logout,
            'GET /products/': self._product_list,
            'GET /products/{id}/': self._product_detail,
            'POST /products/{id}/review/': self._add_review,
            'GET /cart/': self._view_cart,
            'POST /cart/add/': self._add_to_cart,
            'POST /cart/update/': self._update_cart,
            'POST /cart/remove/': self._remove_from_cart,
            'POST /cart/coupon/': self._apply_coupon,
            'POST /checkout/': self._checkout,
            'GET /orders/': self._order_list,
            'GET /orders/{id}/': self._order_detail,
            'POST /orders/{id}/cancel/': self._cancel_order,
            'GET /admin/dashboard/': self._admin_dashboard,
            'GET /admin/orders/': self._admin_orders,
            'POST /admin/orders/{id}/': self._admin_manage_order,
            'GET /admin/inventory/': self._admin_inventory,
            'GET /admin/users/': self._admin_users,
        }
    
    def _home(self, **kwargs) -> ViewResponse:
        featured = self.app.product_service.get_featured_products(8)
        categories = self.app.product_service.get_category_tree()
        return ViewResponse(200, {
            'featured_products': featured,
            'categories': categories,
            'page_title': 'Amazon Clone - Home'
        })
    
    def _register(self, **kwargs) -> ViewResponse:
        return self.auth_view.register(**kwargs)
    
    def _login(self, **kwargs) -> ViewResponse:
        return self.auth_view.login(**kwargs)
    
    def _logout(self, **kwargs) -> ViewResponse:
        return self.auth_view.logout(**kwargs)
    
    def _product_list(self, **kwargs) -> ViewResponse:
        return self.product_view.list_products(**kwargs)
    
    def _product_detail(self, **kwargs) -> ViewResponse:
        return self.product_view.product_detail(**kwargs)
    
    def _add_review(self, **kwargs) -> ViewResponse:
        return self.product_view.add_review(**kwargs)
    
    def _view_cart(self, **kwargs) -> ViewResponse:
        return self.cart_view.view_cart(**kwargs)
    
    def _add_to_cart(self, **kwargs) -> ViewResponse:
        return self.cart_view.add_to_cart(**kwargs)
    
    def _update_cart(self, **kwargs) -> ViewResponse:
        return self.cart_view.update_cart(**kwargs)
    
    def _remove_from_cart(self, **kwargs) -> ViewResponse:
        return self.cart_view.remove_from_cart(**kwargs)
    
    def _apply_coupon(self, **kwargs) -> ViewResponse:
        return self.cart_view.apply_coupon(**kwargs)
    
    def _checkout(self, **kwargs) -> ViewResponse:
        return self.order_view.checkout(**kwargs)
    
    def _order_list(self, **kwargs) -> ViewResponse:
        return self.order_view.order_list(**kwargs)
    
    def _order_detail(self, **kwargs) -> ViewResponse:
        return self.order_view.order_detail(**kwargs)
    
    def _cancel_order(self, **kwargs) -> ViewResponse:
        return self.order_view.cancel_order(**kwargs)
    
    def _admin_dashboard(self, **kwargs) -> ViewResponse:
        return self.admin_view.dashboard(**kwargs)
    
    def _admin_orders(self, admin_id: int, **kwargs) -> ViewResponse:
        orders = self.app.order_service.get_all_orders()
        return ViewResponse(200, {'orders': orders})
    
    def _admin_manage_order(self, **kwargs) -> ViewResponse:
        return self.admin_view.manage_orders(**kwargs)
    
    def _admin_inventory(self, admin_id: int, **kwargs) -> ViewResponse:
        return self.admin_view.manage_inventory(admin_id, action='report')
    
    def _admin_users(self, admin_id: int, **kwargs) -> ViewResponse:
        return self.admin_view.manage_users(admin_id, action='list')
    
    def dispatch(self, method: str, path: str, **kwargs) -> ViewResponse:
        route_key = f"{method} {path}"
        handler = self.routes.get(route_key)
        
        if handler:
            return handler(**kwargs)
        
        # Try pattern matching
        for route, handler in self.routes.items():
            if '{id}' in route:
                pattern = route.replace('{id}', '')
                if route_key.startswith(pattern.split('{')[0]):
                    return handler(**kwargs)
        
        return ViewResponse(404, {'error': 'Page not found'})


# ============================================================
# MULTI-LEVEL ECOMMERCE FEATURES
# ============================================================

class MultiLevelEcommerce:
    """Multi-level e-commerce features"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        self._seller_accounts = {}
        self._seller_products = {}
        self._commissions = {}
        self._next_seller_id = 1
        
    def register_seller(self, user_id: int, store_name: str,
                         description: str = '',
                         commission_rate: float = 0.15) -> dict:
        """Register a user as a seller"""
        user = self.app.user_service.get_user(user_id)
        if not user:
            return None
            
        seller = {
            'seller_id': self._next_seller_id,
            'user_id': user_id,
            'store_name': store_name,
            'description': description,
            'commission_rate': commission_rate,
            'is_active': True,
            'is_verified': False,
            'created_at': datetime.now(),
            'total_sales': Decimal('0'),
            'rating': 0.0,
            'products': []
        }
        
        self._seller_accounts[self._next_seller_id] = seller
        self._next_seller_id += 1
        
        # Update user type
        user.user_type = 'seller'
        
        return seller
    
    def add_seller_product(self, seller_id: int, product_id: int,
                            seller_price: Decimal) -> dict:
        """Add a product listing for a seller"""
        seller = self._seller_accounts.get(seller_id)
        if not seller:
            return None
            
        listing = {
            'seller_id': seller_id,
            'product_id': product_id,
            'seller_price': Decimal(str(seller_price)),
            'created_at': datetime.now(),
            'is_active': True
        }
        
        if seller_id not in self._seller_products:
            self._seller_products[seller_id] = []
        self._seller_products[seller_id].append(listing)
        seller['products'].append(product_id)
        
        return listing
    
    def get_product_sellers(self, product_id: int) -> list:
        """Get all sellers for a product"""
        sellers = []
        for seller_id, listings in self._seller_products.items():
            for listing in listings:
                if listing['product_id'] == product_id and listing['is_active']:
                    seller = self._seller_accounts.get(seller_id)
                    if seller and seller['is_active']:
                        sellers.append({
                            'seller': seller,
                            'price': listing['seller_price']
                        })
        
        sellers.sort(key=lambda s: s['price'])
        return sellers
    
    def calculate_commission(self, seller_id: int, 
                              sale_amount: Decimal) -> Decimal:
        """Calculate platform commission"""
        seller = self._seller_accounts.get(seller_id)
        if not seller:
            return Decimal('0')
            
        commission = sale_amount * Decimal(str(seller['commission_rate']))
        return commission
    
    def get_seller_dashboard(self, seller_id: int) -> dict:
        """Get seller dashboard data"""
        seller = self._seller_accounts.get(seller_id)
        if not seller:
            return {}
            
        listings = self._seller_products.get(seller_id, [])
        
        return {
            'seller': seller,
            'total_listings': len(listings),
            'active_listings': len([l for l in listings if l['is_active']]),
            'total_sales': seller['total_sales'],
            'rating': seller['rating']
        }
    
    def verify_seller(self, seller_id: int, admin_id: int) -> bool:
        """Admin verifies a seller"""
        admin = self.app.user_service.get_user(admin_id)
        if not admin or admin.user_type != 'admin':
            return False
            
        seller = self._seller_accounts.get(seller_id)
        if seller:
            seller['is_verified'] = True
            return True
        return False


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Main entry point"""
    print("Starting Amazon Clone Application...")
    print("="*60)
    
    # Create application
    app = AmazonCloneApp()
    
    # Run demo
    app.run_demo()
    
    # Demonstrate URL routing
    print("\n" + "="*60)
    print("URL ROUTING DEMO")
    print("="*60)
    
    router = URLRouter(app)
    
    # Home page
    response = router.dispatch('GET', '/')
    print(f"Home page: {response}")
    print(f"Featured products: {len(response.data.get('featured_products', []))}")
    
    # Register user
    response = router.dispatch('POST', '/auth/register/',
                               username='test_user',
                               email='test@example.com',
                               password='Test@1234',
                               confirm_password='Test@1234',
                               first_name='Test',
                               last_name='User')
    print(f"Register: Status {response.status_code}")
    
    # Login
    response = router.dispatch('POST', '/auth/login/',
                               username='test_user',
                               password='Test@1234')
    print(f"Login: Status {response.status_code}")
    
    if response.status_code == 200:
        user = response.data['user']
        
        # Product list
        response = router.dispatch('GET', '/products/',
                                   user_id=user.user_id)
        print(f"Product list: {len(response.data.get('products', []))} products")
        
        # Admin dashboard
        admin_user, _ = app.user_service.login('admin', 'Admin@1234')
        if admin_user:
            response = router.dispatch('GET', '/admin/dashboard/',
                                       admin_id=admin_user.user_id)
            print(f"Admin dashboard: Status {response.status_code}")
            if response.status_code == 200:
                stats = response.data.get('order_stats', {})
                print(f"  Total orders: {stats.get('total_orders', 0)}")
    
    # Multi-level ecommerce demo
    print("\n" + "="*60)
    print("MULTI-LEVEL ECOMMERCE DEMO")
    print("="*60)
    
    ml_ecommerce = MultiLevelEcommerce(app)
    
    # Register a seller
    user1 = app.user_service.get_user(2)  # john_doe
    if user1:
        seller = ml_ecommerce.register_seller(
            user_id=user1.user_id,
            store_name="John's Electronics",
            description="Quality electronics at great prices",
            commission_rate=0.12
        )
        print(f"Seller registered: {seller['store_name']}")
        
        # Add product listing
        products = list(app.product_service._products.values())
        if products:
            listing = ml_ecommerce.add_seller_product(
                seller_id=seller['seller_id'],
                product_id=products[0].product_id,
                seller_price=products[0].price * Decimal('0.95')
            )
            print(f"Product listed at: ${listing['seller_price']}")
        
        # Get seller dashboard
        dashboard = ml_ecommerce.get_seller_dashboard(seller['seller_id'])
        print(f"Seller dashboard: {dashboard['total_listings']} listings")
        
        # Verify seller (admin)
        admin_user, _ = app.user_service.login('admin', 'Admin@1234')
        if admin_user:
            verified = ml_ecommerce.verify_seller(
                seller['seller_id'], admin_user.user_id
            )
            print(f"Seller verified: {verified}")
    
    print("\n" + "="*60)
    print("APPLICATION DEMO COMPLETE!")
    print("="*60)
    print("\nSystem Summary:")
    print(f"  Users: {len(app.user_service._users)}")
    print(f"  Products: {len(app.product_service._products)}")
    print(f"  Categories: {len(app.product_service._categories)}")
    print(f"  Orders: {len(app.order_service._orders)}")
    print(f"  Warehouses: {len(app.inventory_service._warehouses)}")
    print(f"  Suppliers: {len(app.inventory_service._suppliers)}")
    print(f"  Inventory Records: {len(app.inventory_service._inventory)}")
    print(f"  Purchase Orders: {len(app.inventory_service._purchase_orders)}")
    
    return app


if __name__ == '__main__':
    app = main()