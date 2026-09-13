#!/usr/bin/env python3
"""
Amazon Clone - Complete Django Implementation
A fully functional e-commerce platform with inventory management
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
    'AUTH_USER_MODEL': 'auth.User',
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
            self.rating = (self.rating + new_rating) / 2 if self.rating > 0 else new_rating
            
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
        
    def get_primary_image(self) -> str:
        for img in self.images:
            if img.get('is_primary'):
                return img['url']
        return self.images[0]['url'] if self.images else '/static/default-product.jpg'
    
    def update_rating(self, new_rating: float):
        total = self.rating * self.review_count + new_rating
        self.review_count += 1
        self.rating = total / self.review_count
        
    def __repr__(self) -> str:
        return f"Product(id={self.product_id}, name={self.name}, price={self.price})"


class ProductVariant:
    """Product variant model (size, color, etc.)"""
    
    def __init__(self, variant_id: int, product_id: int, 
                 variant_type: str, variant_value: str,
                 price_modifier: Decimal = Decimal('0.00'),
                 sku_suffix: str = ''):
        self.variant_id = variant_id
        self.product_id = product_id
        self.variant_type = variant_type  # size, color, material, etc.
        self.variant_value = variant_value
        self.price_modifier = Decimal(str(price_modifier))
        self.sku_suffix = sku_suffix
        self.is_active = True
        
    def __repr__(self) -> str:
        return f"ProductVariant(id={self.variant_id}, type={self.variant_type}, value={self.variant_value})"


class Inventory:
    """Inventory model linking products to warehouses"""
    
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
        self.location_in_warehouse = ''
        
    def get_available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self) -> bool:
        return self.get_available_quantity() <= self.reorder_point
    
    def add_stock(self, quantity: int):
        if quantity > 0:
            self.quantity += quantity
            self.last_updated = datetime.now()
            
    def remove_stock(self, quantity: int) -> bool:
        if quantity <= self.get_available_quantity():
            self.quantity -= quantity
            self.last_updated = datetime.now()
            return True
        return False
    
    def reserve_stock(self, quantity: int) -> bool:
        if quantity <= self.get_available_quantity():
            self.reserved_quantity += quantity
            return True
        return False
    
    def release_reservation(self, quantity: int):
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        
    def __repr__(self) -> str:
        return f"Inventory(product_id={self.product_id}, warehouse_id={self.warehouse_id}, qty={self.quantity})"


class PurchaseOrder:
    """Purchase order model for ordering from suppliers"""
    
    STATUS_CHOICES = ['draft', 'sent', 'confirmed', 'received', 'cancelled']
    
    def __init__(self, po_id: int, supplier_id: int, warehouse_id: int,
                 created_by: int, expected_delivery: datetime = None):
        self.po_id = po_id
        self.po_number = f"PO-{po_id:08d}"
        self.supplier_id = supplier_id
        self.warehouse_id = warehouse_id
        self.created_by = created_by
        self.status = 'draft'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.expected_delivery = expected_delivery or (datetime.now() + timedelta(days=7))
        self.received_at = None
        self.items = []
        self.notes = ''
        self.total_amount = Decimal('0.00')
        self.tax_amount = Decimal('0.00')
        self.shipping_cost = Decimal('0.00')
        
    def add_item(self, product_id: int, quantity: int, unit_price: Decimal,
                 variant_id: int = None):
        item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'received_quantity': 0,
            'subtotal': Decimal(str(unit_price)) * quantity
        }
        self.items.append(item)
        self._calculate_total()
        
    def _calculate_total(self):
        subtotal = sum(item['subtotal'] for item in self.items)
        self.total_amount = subtotal + self.tax_amount + self.shipping_cost
        
    def send_to_supplier(self) -> bool:
        if self.status == 'draft' and self.items:
            self.status = 'sent'
            self.updated_at = datetime.now()
            return True
        return False
    
    def confirm_order(self) -> bool:
        if self.status == 'sent':
            self.status = 'confirmed'
            self.updated_at = datetime.now()
            return True
        return False
    
    def receive_order(self, received_items: list = None) -> bool:
        if self.status in ['sent', 'confirmed']:
            if received_items:
                for i, item in enumerate(self.items):
                    if i < len(received_items):
                        item['received_quantity'] = received_items[i]
            else:
                for item in self.items:
                    item['received_quantity'] = item['quantity']
            self.status = 'received'
            self.received_at = datetime.now()
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel_order(self, reason: str = '') -> bool:
        if self.status in ['draft', 'sent']:
            self.status = 'cancelled'
            self.notes += f"\nCancelled: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"PurchaseOrder(po_number={self.po_number}, supplier_id={self.supplier_id}, status={self.status})"


class SalesOrder:
    """Sales order model"""
    
    STATUS_CHOICES = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
    
    def __init__(self, order_id: int, user_id: int, 
                 shipping_address: dict, billing_address: dict = None):
        self.order_id = order_id
        self.order_number = f"ORD-{order_id:010d}"
        self.user_id = user_id
        self.status = 'pending'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.shipping_address = shipping_address
        self.billing_address = billing_address or shipping_address
        self.items = []
        self.subtotal = Decimal('0.00')
        self.tax_amount = Decimal('0.00')
        self.shipping_cost = Decimal('0.00')
        self.discount_amount = Decimal('0.00')
        self.total_amount = Decimal('0.00')
        self.payment_method = ''
        self.payment_status = 'pending'
        self.payment_transaction_id = ''
        self.tracking_number = ''
        self.notes = ''
        self.estimated_delivery = None
        self.delivered_at = None
        self.warehouse_id = None
        
    def add_item(self, product_id: int, product_name: str, quantity: int,
                 unit_price: Decimal, variant_id: int = None, sku: str = ''):
        item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'product_name': product_name,
            'sku': sku,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'subtotal': Decimal(str(unit_price)) * quantity
        }
        self.items.append(item)
        self._calculate_total()
        
    def _calculate_total(self):
        self.subtotal = sum(item['subtotal'] for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        
    def confirm_order(self) -> bool:
        if self.status == 'pending':
            self.status = 'confirmed'
            self.updated_at = datetime.now()
            return True
        return False
    
    def process_order(self) -> bool:
        if self.status == 'confirmed':
            self.status = 'processing'
            self.updated_at = datetime.now()
            return True
        return False
    
    def ship_order(self, tracking_number: str, warehouse_id: int = None) -> bool:
        if self.status == 'processing':
            self.status = 'shipped'
            self.tracking_number = tracking_number
            self.warehouse_id = warehouse_id
            self.estimated_delivery = datetime.now() + timedelta(days=5)
            self.updated_at = datetime.now()
            return True
        return False
    
    def deliver_order(self) -> bool:
        if self.status == 'shipped':
            self.status = 'delivered'
            self.delivered_at = datetime.now()
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel_order(self, reason: str = '') -> bool:
        if self.status in ['pending', 'confirmed']:
            self.status = 'cancelled'
            self.notes += f"\nCancelled: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def refund_order(self, reason: str = '') -> bool:
        if self.status == 'delivered':
            self.status = 'refunded'
            self.payment_status = 'refunded'
            self.notes += f"\nRefunded: {reason}"
            self.updated_at = datetime.now()
            return True
        return False
    
    def apply_discount(self, discount_amount: Decimal):
        self.discount_amount = Decimal(str(discount_amount))
        self._calculate_total()
        
    def set_payment(self, method: str, transaction_id: str = ''):
        self.payment_method = method
        self.payment_transaction_id = transaction_id
        self.payment_status = 'paid'
        
    def __repr__(self) -> str:
        return f"SalesOrder(order_number={self.order_number}, user_id={self.user_id}, status={self.status})"


class ShoppingCart:
    """Shopping cart model"""
    
    def __init__(self, cart_id: int, user_id: int = None, session_id: str = ''):
        self.cart_id = cart_id
        self.user_id = user_id
        self.session_id = session_id
        self.items = {}  # {product_id: {quantity, price, variant_id}}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.coupon_code = ''
        self.discount_amount = Decimal('0.00')
        
    def add_item(self, product_id: int, quantity: int, price: Decimal,
                 variant_id: int = None) -> bool:
        if quantity <= 0:
            return False
        
        key = f"{product_id}_{variant_id}" if variant_id else str(product_id)
        
        if key in self.items:
            self.items[key]['quantity'] += quantity
        else:
            self.items[key] = {
                'product_id': product_id,
                'variant_id': variant_id,
                'quantity': quantity,
                'price': Decimal(str(price))
            }
        self.updated_at = datetime.now()
        return True
    
    def remove_item(self, product_id: int, variant_id: int = None) -> bool:
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
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_subtotal(self) -> Decimal:
        total = Decimal('0.00')
        for item in self.items.values():
            total += item['price'] * item['quantity']
        return total
    
    def get_total(self) -> Decimal:
        return self.get_subtotal() - self.discount_amount
    
    def get_item_count(self) -> int:
        return sum(item['quantity'] for item in self.items.values())
    
    def clear(self):
        self.items = {}
        self.discount_amount = Decimal('0.00')
        self.coupon_code = ''
        self.updated_at = datetime.now()
        
    def apply_coupon(self, coupon_code: str, discount: Decimal) -> bool:
        self.coupon_code = coupon_code
        self.discount_amount = Decimal(str(discount))
        return True
    
    def merge_with_session_cart(self, session_cart: 'ShoppingCart'):
        """Merge session cart into user cart"""
        for key, item in session_cart.items.items():
            if key in self.items:
                self.items[key]['quantity'] += item['quantity']
            else:
                self.items[key] = item.copy()
        self.updated_at = datetime.now()
        
    def __repr__(self) -> str:
        return f"ShoppingCart(id={self.cart_id}, user_id={self.user_id}, items={len(self.items)})"


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
        self.is_verified_purchase = False
        self.helpful_votes = 0
        self.is_approved = True
        
    def __repr__(self) -> str:
        return f"Review(id={self.review_id}, product_id={self.product_id}, rating={self.rating})"


class Coupon:
    """Coupon/discount model"""
    
    DISCOUNT_TYPES = ['percentage', 'fixed_amount', 'free_shipping']
    
    def __init__(self, coupon_id: int, code: str, discount_type: str,
                 discount_value: Decimal, min_order_amount: Decimal = Decimal('0.00'),
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
        return Decimal('0.00')
    
    def use_coupon(self):
        self.current_uses += 1
        
    def __repr__(self) -> str:
        return f"Coupon(code={self.code}, type={self.discount_type}, value={self.discount_value})"


class Address:
    """Address model"""
    
    def __init__(self, address_id: int, user_id: int, address_type: str,
                 street_address: str, city: str, state: str,
                 postal_code: str, country: str, is_default: bool = False):
        self.address_id = address_id
        self.user_id = user_id
        self.address_type = address_type  # shipping, billing
        self.street_address = street_address
        self.city = city
        self.state = state
        self.postal_code = postal_code
        self.country = country
        self.is_default = is_default
        self.created_at = datetime.now()
        
    def to_dict(self) -> dict:
        return {
            'street_address': self.street_address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country
        }
    
    def __repr__(self) -> str:
        return f"Address(id={self.address_id}, city={self.city}, country={self.country})"


class StockMovement:
    """Track all stock movements"""
    
    MOVEMENT_TYPES = ['purchase', 'sale', 'transfer', 'adjustment', 'return', 'damage']
    
    def __init__(self, movement_id: int, product_id: int, warehouse_id: int,
                 movement_type: str, quantity: int, reference_id: int = None,
                 notes: str = ''):
        self.movement_id = movement_id
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.movement_type = movement_type
        self.quantity = quantity  # positive for in, negative for out
        self.reference_id = reference_id  # PO ID or Order ID
        self.notes = notes
        self.created_at = datetime.now()
        self.created_by = None
        
    def __repr__(self) -> str:
        return f"StockMovement(product_id={self.product_id}, type={self.movement_type}, qty={self.quantity})"


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
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ['user_id', 'password_hash']:
                setattr(user, key, value)
        return user
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        if self._verify_password(old_password, user.password_hash):
            user.password_hash = self._hash_password(new_password)
            return True
        return False
    
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
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == password_hash


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
        return [c for c in self.categories.values() if not c.parent_id]
    
    def get_subcategories(self, parent_id: int) -> list:
        return [c for c in self.categories.values() if c.parent_id == parent_id]
    
    def get_category_tree(self) -> list:
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
        for key, value in kwargs.items():
            if hasattr(product, key) and key != 'product_id':
                setattr(product, key, value)
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
        results = [p for p in self.products.values() if p.is_active]
        
        if query:
            query_lower = query.lower()
            results = [p for p in results if 
                      query_lower in p.name.lower() or 
                      query_lower in p.description.lower() or
                      query_lower in p.brand.lower()]
        
        if category_id:
            results = [p for p in results if p.category_id == category_id]
            
        if min_price is not None:
            results = [p for p in results if p.get_discounted_price() >= Decimal(str(min_price))]
            
        if max_price is not None:
            results = [p for p in results if p.get_discounted_price() <= Decimal(str(max_price))]
            
        if brand:
            results = [p for p in results if p.brand.lower() == brand.lower()]
        
        if sort_by == 'price_asc':
            results.sort(key=lambda p: p.get_discounted_price())
        elif sort_by == 'price_desc':
            results.sort(key=lambda p: p.get_discounted_price(), reverse=True)
        elif sort_by == 'rating':
            results.sort(key=lambda p: p.rating, reverse=True)
        elif sort_by == 'newest':
            results.sort(key=lambda p: p.created_at, reverse=True)
        else:
            results.sort(key=lambda p: p.name)
            
        return results
    
    def get_featured_products(self) -> list:
        return [p for p in self.products.values() if p.is_featured and p.is_active]
    
    def get_products_by_category(self, category_id: int) -> list:
        return [p for p in self.products.values() 
                if p.category_id == category_id and p.is_active]
    
    def add_variant(self, product_id: int, variant_type: str, 
                    variant_value: str, price_modifier: Decimal = Decimal('0.00'),
                    sku_suffix: str = '') -> ProductVariant:
        variant = ProductVariant(
            variant_id=self.next_variant_id,
            product_id=product_id,
            variant_type=variant_type,
            variant_value=variant_value,
            price_modifier=price_modifier,
            sku_suffix=sku_suffix
        )
        self.variants[self.next_variant_id] = variant
        self.next_variant_id += 1
        return variant
    
    def get_product_variants(self, product_id: int) -> list:
        return [v for v in self.variants.values() if v.product_id == product_id]
    
    def add_review(self, product_id: int, rating: float):
        product = self.products.get(product_id)
        if product:
            product.update_rating(rating)


class InventoryService:
    """Inventory management service"""
    
    def __init__(self):
        self.inventory = {}
        self.stock_movements = {}
        self.next_id = 1
        self.next_movement_id = 1
        
    def create_inventory(self, product_id: int, warehouse_id: int,
                         quantity: int = 0, reorder_point: int = 10,
                         reorder_quantity: int = 50) -> Inventory:
        key = f"{product_id}_{warehouse_id}"
        if key in self.inventory:
            raise ValueError(f"Inventory already exists for product {product_id} in warehouse {warehouse_id}")
            
        inv = Inventory(
            inventory_id=self.next_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity
        )
        self.inventory[key] = inv
        self.next_id += 1
        
        if quantity > 0:
            self._record_movement(product_id, warehouse_id, 'adjustment', quantity, 
                                 notes='Initial stock')
        return inv
    
    def get_inventory(self, product_id: int, warehouse_id: int) -> Inventory:
        key = f"{product_id}_{warehouse_id}"
        return self.inventory.get(key)
    
    def get_total_stock(self, product_id: int) -> int:
        total = 0
        for key, inv in self.inventory.items():
            if inv.product_id == product_id:
                total += inv.get_available_quantity()
        return total
    
    def add_stock(self, product_id: int, warehouse_id: int, quantity: int,
                  reference_id: int = None, notes: str = '') -> bool:
        inv = self.get_inventory(product_id, warehouse_id)
        if not inv:
            inv = self.create_inventory(product_id, warehouse_id, 0)
        
        inv.add_stock(quantity)
        self._record_movement(product_id, warehouse_id, 'purchase', quantity,
                             reference_id, notes)
        return True
    
    def remove_stock(self, product_id: int, warehouse_id: int, quantity: int,
                    reference_id: int = None, notes: str = '') -> bool:
        inv = self.get_inventory(product_id, warehouse_id)
        if not inv:
            return False
        
        if inv.remove_stock(quantity):
            self._record_movement(product_id, warehouse_id, 'sale', -quantity,
                                 reference_id, notes)
            return True
        return False
    
    def transfer_stock(self, product_id: int, from_warehouse_id: int,
                      to_warehouse_id: int, quantity: int) -> bool:
        from_inv = self.get_inventory(product_id, from_warehouse_id)
        if not from_inv or from_inv.get_available_quantity() < quantity:
            return False
        
        to_inv = self.get_inventory(product_id, to_warehouse_id)
        if not to_inv:
            to_inv = self.create_inventory(product_id, to_warehouse_id, 0)
        
        from_inv.remove_stock(quantity)
        to_inv.add_stock(quantity)
        
        self._record_movement(product_id, from_warehouse_id, 'transfer', -quantity,
                             notes=f"Transfer to warehouse {to_warehouse_id}")
        self._record_movement(product_id, to_warehouse_id, 'transfer', quantity,
                             notes=f"Transfer from warehouse {from_warehouse_id}")
        return True
    
    def adjust_stock(self, product_id: int, warehouse_id: int, 
                    new_quantity: int, reason: str = '') -> bool:
        inv = self.get_inventory(product_id, warehouse_id)
        if not inv:
            return False
        
        difference = new_quantity - inv.quantity
        inv.quantity = new_quantity
        inv.last_updated = datetime.now()
        
        self._record_movement(product_id, warehouse_id, 'adjustment', difference,
                             notes=reason)
        return True
    
    def get_low_stock_items(self) -> list:
        return [inv for inv in self.inventory.values() if inv.needs_reorder()]
    
    def get_stock_movements(self, product_id: int = None, 
                           warehouse_id: int = None) -> list:
        movements = list(self.stock_movements.values())
        if product_id:
            movements = [m for m in movements if m.product_id == product_id]
        if warehouse_id:
            movements = [m for m in movements if m.warehouse_id == warehouse_id]
        return movements
    
    def _record_movement(self, product_id: int, warehouse_id: int,
                        movement_type: str, quantity: int,
                        reference_id: int = None, notes: str = ''):
        movement = StockMovement(
            movement_id=self.next_movement_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            quantity=quantity,
            reference_id=reference_id,
            notes=notes
        )
        self.stock_movements[self.next_movement_id] = movement
        self.next_movement_id += 1
        return movement
    
    def get_warehouse_inventory(self, warehouse_id: int) -> list:
        return [inv for inv in self.inventory.values() 
                if inv.warehouse_id == warehouse_id]


class WarehouseService:
    """Warehouse management service"""
    
    def __init__(self):
        self.warehouses = {}
        self.next_id = 1
        
    def create_warehouse(self, name: str, location: str, capacity: int = 0,
                         manager_id: int = None) -> Warehouse:
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
        for key, value in kwargs.items():
            if hasattr(warehouse, key) and key != 'warehouse_id':
                setattr(warehouse, key, value)
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
        for key, value in kwargs.items():
            if hasattr(supplier, key) and key != 'supplier_id':
                setattr(supplier, key, value)
        return supplier
    
    def rate_supplier(self, supplier_id: int, rating: float) -> bool:
        supplier = self.suppliers.get(supplier_id)
        if supplier:
            supplier.update_rating(rating)
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
    
    def add_item_to_po(self, po_id: int, product_id: int, quantity: int,
                       unit_price: Decimal, variant_id: int = None) -> bool:
        po = self.purchase_orders.get(po_id)
        if po and po.status == 'draft':
            po.add_item(product_id, quantity, unit_price, variant_id)
            return True
        return False
    
    def send_purchase_order(self, po_id: int) -> bool:
        po = self.purchase_orders.get(po_id)
        if po:
            return po.send_to_supplier()
        return False
    
    def confirm_purchase_order(self, po_id: int) -> bool:
        po = self.purchase_orders.get(po_id)
        if po:
            return po.confirm_order()
        return False
    
    def receive_purchase_order(self, po_id: int, 
                               received_items: list = None) -> bool:
        po = self.purchase_orders.get(po_id)
        if po and po.receive_order(received_items):
            # Update inventory
            for i, item in enumerate(po.items):
                received_qty = item.get('received_quantity', item['quantity'])
                if received_qty > 0:
                    self.inventory_service.add_stock(
                        product_id=item['product_id'],
                        warehouse_id=po.warehouse_id,
                        quantity=received_qty,
                        reference_id=po_id,
                        notes=f"Received from PO {po.po_number}"
                    )
            return True
        return False
    
    def cancel_purchase_order(self, po_id: int, reason: str = '') -> bool:
        po = self.purchase_orders.get(po_id)
        if po:
            return po.cancel_order(reason)
        return False
    
    def get_all_purchase_orders(self, status: str = None) -> list:
        orders = list(self.purchase_orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders
    
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
                           session_id: str = '') -> ShoppingCart:
        # Find existing cart
        for cart in self.carts.values():
            if user_id and cart.user_id == user_id:
                return cart
            if not user_id and session_id and cart.session_id == session_id:
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
    
    def add_to_cart(self, cart_id: int, product_id: int, quantity: int,
                    variant_id: int = None) -> tuple:
        cart = self.carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        product = self.product_service.get_product(product_id)
        if not product or not product.is_active:
            return False, "Product not available"
        
        # Check stock
        total_stock = self.inventory_service.get_total_stock(product_id)
        if total_stock < quantity:
            return False, f"Only {total_stock} items available"
        
        price = product.get_discounted_price()
        if variant_id:
            variant = self.product_service.variants.get(variant_id)
            if variant:
                price += variant.price_modifier
        
        cart.add_item(product_id, quantity, price, variant_id)
        return True, "Item added to cart"
    
    def remove_from_cart(self, cart_id: int, product_id: int,
                         variant_id: int = None) -> bool:
        cart = self.carts.get(cart_id)
        if cart:
            return cart.remove_item(product_id, variant_id)
        return False
    
    def update_cart_item(self, cart_id: int, product_id: int, quantity: int,
                         variant_id: int = None) -> tuple:
        cart = self.carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        if quantity > 0:
            total_stock = self.inventory_service.get_total_stock(product_id)
            if total_stock < quantity:
                return False, f"Only {total_stock} items available"
        
        cart.update_quantity(product_id, quantity, variant_id)
        return True, "Cart updated"
    
    def clear_cart(self, cart_id: int) -> bool:
        cart = self.carts.get(cart_id)
        if cart:
            cart.clear()
            return True
        return False
    
    def merge_carts(self, session_cart_id: int, user_cart_id: int) -> bool:
        session_cart = self.carts.get(session_cart_id)
        user_cart = self.carts.get(user_cart_id)
        if session_cart and user_cart:
            user_cart.merge_with_session_cart(session_cart)
            del self.carts[session_cart_id]
            return True
        return False
    
    def apply_coupon(self, cart_id: int, coupon: Coupon) -> tuple:
        cart = self.carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        is_valid, message = coupon.is_valid(cart.get_subtotal())
        if is_valid:
            discount = coupon.calculate_discount(cart.get_subtotal())
            cart.apply_coupon(coupon.code, discount)
            coupon.use_coupon()
            return True, f"Coupon applied. Discount: {discount}"
        return False, message


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
                               payment_method: str = 'credit_card') -> tuple:
        cart = self.cart_service.carts.get(cart_id)
        if not cart or not cart.items:
            return None, "Cart is empty"
        
        # Check stock availability
        for key, item in cart.items.items():
            stock = self.inventory_service.get_total_stock(item['product_id'])
            if stock < item['quantity']:
                return None, f"Insufficient stock for product {item['product_id']}"
        
        # Create order
        order = SalesOrder(
            order_id=self.next_id,
            user_id=user_id,
            shipping_address=shipping_address,
            billing_address=billing_address
        )
        
        # Add items
        for key, item in cart.items.items():
            product = None
            # Get product name from service if available
            order.add_item(
                product_id=item['product_id'],
                product_name=f"Product {item['product_id']}",
                quantity=item['quantity'],
                unit_price=item['price'],
                variant_id=item.get('variant_id')
            )
        
        # Apply discount
        if cart.discount_amount > 0:
            order.apply_discount(cart.discount_amount)
        
        # Calculate tax (10%)
        order.tax_amount = order.subtotal * Decimal('0.10')
        
        # Calculate shipping
        order.shipping_cost = Decimal('5.99') if order.subtotal < Decimal('50') else Decimal('0.00')
        
        order._calculate_total()
        order.set_payment(payment_method)
        
        self.orders[self.next_id] = order
        self.next_id += 1
        
        # Reserve stock
        for key, item in cart.items.items():
            # Find best warehouse
            for inv_key, inv in self.inventory_service.inventory.items():
                if inv.product_id == item['product_id']:
                    inv.reserve_stock(item['quantity'])
                    break
        
        # Clear cart
        self.cart_service.clear_cart(cart_id)
        
        return order, "Order created successfully"
    
    def create_order(self, user_id: int, items: list,
                    shipping_address: dict, billing_address: dict = None,
                    payment_method: str = 'credit_card') -> tuple:
        order = SalesOrder(
            order_id=self.next_id,
            user_id=user_id,
            shipping_address=shipping_address,
            billing_address=billing_address
        )
        
        for item in items:
            order.add_item(
                product_id=item['product_id'],
                product_name=item.get('product_name', f"Product {item['product_id']}"),
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                variant_id=item.get('variant_id'),
                sku=item.get('sku', '')
            )
        
        order.tax_amount = order.subtotal * Decimal('0.10')
        order.shipping_cost = Decimal('5.99') if order.subtotal < Decimal('50') else Decimal('0.00')
        order._calculate_total()
        order.set_payment(payment_method)
        
        self.orders[self.next_id] = order
        self.next_id += 1
        
        return order, "Order created successfully"
    
    def get_order(self, order_id: int) -> SalesOrder:
        return self.orders.get(order_id)
    
    def get_user_orders(self, user_id: int) -> list:
        return [o for o in self.orders.values() if o.user_id == user_id]
    
    def get_all_orders(self, status: str = None) -> list:
        orders = list(self.orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders
    
    def confirm_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.confirm_order()
        return False
    
    def process_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.process_order()
        return False
    
    def ship_order(self, order_id: int, tracking_number: str,
                   warehouse_id: int = None) -> bool:
        order = self.orders.get(order_id)
        if order and order.ship_order(tracking_number, warehouse_id):
            # Deduct from inventory
            for item in order.items:
                if warehouse_id:
                    self.inventory_service.remove_stock(
                        product_id=item['product_id'],
                        warehouse_id=warehouse_id,
                        quantity=item['quantity'],
                        reference_id=order_id,
                        notes=f"Shipped for order {order.order_number}"
                    )
            return True
        return False
    
    def deliver_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.deliver_order()
        return False
    
    def cancel_order(self, order_id: int, reason: str = '') -> bool:
        order = self.orders.get(order_id)
        if order and order.cancel_order(reason):
            # Release reserved stock
            for item in order.items:
                for inv_key, inv in self.inventory_service.inventory.items():
                    if inv.product_id == item['product_id']:
                        inv.release_reservation(item['quantity'])
                        break
            return True
        return False
    
    def refund_order(self, order_id: int, reason: str = '') -> bool:
        order = self.orders.get(order_id)
        if order:
            return order.refund_order(reason)
        return False
    
    def get_order_statistics(self) -> dict:
        orders = list(self.orders.values())
        total_revenue = sum(o.total_amount for o in orders 
                           if o.status not in ['cancelled', 'refunded'])
        return {
            'total_orders': len(orders),
            'pending': len([o for o in orders if o.status == 'pending']),
            'confirmed': len([o for o in orders if o.status == 'confirmed']),
            'processing': len([o for o in orders if o.status == 'processing']),
            'shipped': len([o for o in orders if o.status == 'shipped']),
            'delivered': len([o for o in orders if o.status == 'delivered']),
            'cancelled': len([o for o in orders if o.status == 'cancelled']),
            'refunded': len([o for o in orders if o.status == 'refunded']),
            'total_revenue': total_revenue
        }


class ReviewService:
    """Review management service"""
    
    def __init__(self, product_service: ProductService):
        self.reviews = {}
        self.next_id = 1
        self.product_service = product_service
        
    def add_review(self, product_id: int, user_id: int, rating: int,
                   title: str = '', body: str = '',
                   is_verified: bool = False) -> Review:
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
        self.product_service.add_review(product_id, rating)
        
        return review
    
    def get_product_reviews(self, product_id: int) -> list:
        return [r for r in self.reviews.values() 
                if r.product_id == product_id and r.is_approved]
    
    def get_user_reviews(self, user_id: int) -> list:
        return [r for r in self.reviews.values() if r.user_id == user_id]
    
    def vote_helpful(self, review_id: int) -> bool:
        review = self.reviews.get(review_id)
        if review:
            review.helpful_votes += 1
            return True
        return False
    
    def moderate_review(self, review_id: int, approve: bool) -> bool:
        review = self.reviews.get(review_id)
        if review:
            review.is_approved = approve
            return True
        return False


class AddressService:
    """Address management service"""
    
    def __init__(self):
        self.addresses = {}
        self.next_id = 1
        
    def add_address(self, user_id: int, address_type: str,
                    street_address: str, city: str, state: str,
                    postal_code: str, country: str,
                    is_default: bool = False) -> Address:
        address = Address(
            address_id=self.next_id,
            user_id=user_id,
            address_type=address_type,
            street_address=street_address,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            is_default=is_default
        )
        
        if is_default:
            # Remove default from other addresses of same type
            for addr in self.addresses.values():
                if addr.user_id == user_id and addr.address_type == address_type:
                    addr.is_default = False
        
        self.addresses[self.next_id] = address
        self.next_id += 1
        return address
    
    def get_user_addresses(self, user_id: int, 
                           address_type: str = None) -> list:
        addresses = [a for a in self.addresses.values() if a.user_id == user_id]
        if address_type:
            addresses = [a for a in addresses if a.address_type == address_type]
        return addresses
    
    def get_default_address(self, user_id: int, 
                            address_type: str = 'shipping') -> Address:
        for addr in self.addresses.values():
            if (addr.user_id == user_id and 
                addr.address_type == address_type and 
                addr.is_default):
                return addr
        return None
    
    def delete_address(self, address_id: int, user_id: int) -> bool:
        address = self.addresses.get(address_id)
        if address and address.user_id == user_id:
            del self.addresses[address_id]
            return True
        return False


class CouponService:
    """Coupon management service"""
    
    def __init__(self):
        self.coupons = {}
        self.next_id = 1
        
    def create_coupon(self, code: str, discount_type: str,
                      discount_value: Decimal, 
                      min_order_amount: Decimal = Decimal('0.00'),
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
    
    def validate_coupon(self, code: str, order_amount: Decimal) -> tuple:
        coupon = self.get_coupon_by_code(code)
        if not coupon:
            return None, "Invalid coupon code"
        return coupon.is_valid(order_amount)
    
    def deactivate_coupon(self, coupon_id: int) -> bool:
        coupon = self.coupons.get(coupon_id)
        if coupon:
            coupon.is_active = False
            return True
        return False


# ============================================================
# MAIN APPLICATION / FACADE
# ============================================================

class AmazonCloneApp:
    """Main application facade"""
    
    def __init__(self):
        # Initialize services
        self.user_service = UserService()
        self.category_service = CategoryService()
        self.product_service = ProductService()
        self.warehouse_service = WarehouseService()
        self.supplier_service = SupplierService()
        self.inventory_service = InventoryService()
        self.purchase_order_service = PurchaseOrderService(self.inventory_service)
        self.cart_service = CartService(self.product_service, self.inventory_service)
        self.order_service = OrderService(self.inventory_service, self.cart_service)
        self.review_service = ReviewService(self.product_service)
        self.address_service = AddressService()
        self.coupon_service = CouponService()
        
        # Session management
        self.sessions = {}
        
        print("Amazon Clone Application initialized successfully!")
    
    def setup_demo_data(self):
        """Setup demo data for testing"""
        print("\n=== Setting up demo data ===")
        
        # Create admin user
        admin = self.user_service.create_user(
            username='admin',
            email='admin@amazon-clone.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        print(f"Created admin user: {admin}")
        
        # Create regular user
        customer = self.user_service.create_user(
            username='john_doe',
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        print(f"Created customer: {customer}")
        
        # Create warehouse manager
        wm = self.user_service.create_user(
            username='warehouse_mgr',
            email='wm@amazon-clone.com',
            password='wm123',
            first_name='Warehouse',
            last_name='Manager',
            user_type='warehouse_manager'
        )
        print(f"Created warehouse manager: {wm}")
        
        # Create categories
        electronics = self.category_service.create_category(
            'Electronics', 'Electronic devices and accessories'
        )
        phones = self.category_service.create_category(
            'Smartphones', 'Mobile phones and accessories', 
            parent_id=electronics.category_id
        )
        laptops = self.category_service.create_category(
            'Laptops', 'Laptops and notebooks',
            parent_id=electronics.category_id
        )
        clothing = self.category_service.create_category(
            'Clothing', 'Fashion and apparel'
        )
        books = self.category_service.create_category(
            'Books', 'Books and literature'
        )
        print(f"Created categories: {electronics}, {phones}, {laptops}, {clothing}, {books}")
        
        # Create warehouses
        warehouse1 = self.warehouse_service.create_warehouse(
            'Main Warehouse', 'New York, NY', capacity=10000, 
            manager_id=wm.user_id
        )
        warehouse2 = self.warehouse_service.create_warehouse(
            'West Coast Warehouse', 'Los Angeles, CA', capacity=8000,
            manager_id=wm.user_id
        )
        print(f"Created warehouses: {warehouse1}, {warehouse2}")
        
        # Create suppliers
        supplier1 = self.supplier_service.create_supplier(
            'TechSupply Co', 'tech@supply.com', '+1-555-0100',
            '123 Tech Street, Silicon Valley, CA',
            'Bob Smith', 'TechSupply Corporation'
        )
        supplier2 = self.supplier_service.create_supplier(
            'Fashion Forward', 'fashion@forward.com', '+1-555-0200',
            '456 Fashion Ave, New York, NY',
            'Jane Doe', 'Fashion Forward Inc'
        )
        print(f"Created suppliers: {supplier1}, {supplier2}")
        
        # Create products
        iphone = self.product_service.create_product(
            'iPhone 15 Pro', 
            'Latest Apple iPhone with advanced camera system',
            Decimal('999.99'),
            phones.category_id,
            'APPLE-IP15P',
            'Apple',
            0.187
        )
        iphone.is_featured = True
        iphone.discount_percentage = 5.0
        
        samsung = self.product_service.create_product(
            'Samsung Galaxy S24',
            'Samsung flagship smartphone with AI features',
            Decimal('849.99'),
            phones.category_id,
            'SAMSUNG-GS24',
            'Samsung',
            0.167
        )
        
        macbook = self.product_service.create_product(
            'MacBook Pro 14"',
            'Apple MacBook Pro with M3 chip',
            Decimal('1999.99'),
            laptops.category_id,
            'APPLE-MBP14',
            'Apple',
            1.6
        )
        macbook.is_featured = True
        
        tshirt = self.product_service.create_product(
            'Classic Cotton T-Shirt',
            'Comfortable everyday cotton t-shirt',
            Decimal('29.99'),
            clothing.category_id,
            'CLOTH-TSHIRT-001',
            'BasicWear',
            0.2
        )
        
        python_book = self.product_service.create_product(
            'Python Programming: Complete Guide',
            'Comprehensive guide to Python programming',
            Decimal('49.99'),
            books.category_id,
            'BOOK-PYTHON-001',
            'TechPress',
            0.5
        )
        
        print(f"Created products: {iphone}, {samsung}, {macbook}, {tshirt}, {python_book}")
        
        # Add product variants
        self.product_service.add_variant(
            iphone.product_id, 'color', 'Space Black', Decimal('0.00'), 'BLK'
        )
        self.product_service.add_variant(
            iphone.product_id, 'color', 'Natural Titanium', Decimal('0.00'), 'TIT'
        )
        self.product_service.add_variant(
            iphone.product_id, 'storage', '256GB', Decimal('0.00'), '256'
        )
        self.product_service.add_variant(
            iphone.product_id, 'storage', '512GB', Decimal('100.00'), '512'
        )
        self.product_service.add_variant(
            tshirt.product_id, 'size', 'S', Decimal('0.00'), 'S'
        )
        self.product_service.add_variant(
            tshirt.product_id, 'size', 'M', Decimal('0.00'), 'M'
        )
        self.product_service.add_variant(
            tshirt.product_id, 'size', 'L', Decimal('0.00'), 'L'
        )
        
        # Setup inventory
        self.inventory_service.create_inventory(
            iphone.product_id, warehouse1.warehouse_id, 100, 20, 50
        )
        self.inventory_service.create_inventory(
            iphone.product_id, warehouse2.warehouse_id, 50, 10, 30
        )
        self.inventory_service.create_inventory(
            samsung.product_id, warehouse1.warehouse_id, 80, 15, 40
        )
        self.inventory_service.create_inventory(
            macbook.product_id, warehouse1.warehouse_id, 30, 5, 20
        )
        self.inventory_service.create_inventory(
            tshirt.product_id, warehouse1.warehouse_id, 200, 50, 100
        )
        self.inventory_service.create_inventory(
            python_book.product_id, warehouse1.warehouse_id, 150, 30, 75
        )
        
        print("Inventory setup complete")
        
        # Create a purchase order
        po = self.purchase_order_service.create_purchase_order(
            supplier_id=supplier1.supplier_id,
            warehouse_id=warehouse1.warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=7)
        )
        self.purchase_order_service.add_item_to_po(
            po.po_id, iphone.product_id, 50, Decimal('750.00')
        )
        self.purchase_order_service.add_item_to_po(
            po.po_id, samsung.product_id, 40, Decimal('600.00')
        )
        self.purchase_order_service.send_purchase_order(po.po_id)
        print(f"Created purchase order: {po}")
        
        # Add customer address
        address = self.address_service.add_address(
            user_id=customer.user_id,
            address_type='shipping',
            street_address='123 Main Street',
            city='New York',
            state='NY',
            postal_code='10001',
            country='USA',
            is_default=True
        )
        print(f"Added address: {address}")
        
        # Create coupon
        coupon = self.coupon_service.create_coupon(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('50.00'),
            max_uses=100,
            expiry_date=datetime.now() + timedelta(days=30)
        )
        print(f"Created coupon: {coupon}")
        
        # Add reviews
        self.review_service.add_review(
            product_id=iphone.product_id,
            user_id=customer.user_id,
            rating=5,
            title='Amazing phone!',
            body='Best iPhone ever. Camera is incredible.',
            is_verified=True
        )
        self.review_service.add_review(
            product_id=macbook.product_id,
            user_id=customer.user_id,
            rating=4,
            title='Great laptop',
            body='Fast and reliable. Battery life is excellent.',
            is_verified=True
        )
        
        print("\n=== Demo data setup complete ===\n")
        
        return {
            'admin': admin,
            'customer': customer,
            'warehouse_manager': wm,
            'categories': {
                'electronics': electronics,
                'phones': phones,
                'laptops': laptops,
                'clothing': clothing,
                'books': books
            },
            'warehouses': {
                'main': warehouse1,
                'west_coast': warehouse2
            },
            'suppliers': {
                'tech': supplier1,
                'fashion': supplier2
            },
            'products': {
                'iphone': iphone,
                'samsung': samsung,
                'macbook': macbook,
                'tshirt': tshirt,
                'python_book': python_book
            },
            'purchase_order': po,
            'coupon': coupon
        }
    
    def demo_shopping_flow(self, demo_data: dict):
        """Demonstrate complete shopping flow"""
        print("\n=== Demo Shopping Flow ===\n")
        
        customer = demo_data['customer']
        products = demo_data['products']
        warehouses = demo_data['warehouses']
        coupon = demo_data['coupon']
        
        # 1. User Authentication
        print("1. User Authentication")
        user = self.user_service.authenticate('john_doe', 'password123')
        print(f"   Authenticated: {user.get_full_name()}")
        
        # 2. Browse products
        print("\n2. Product Search")
        results = self.product_service.search_products('iPhone', sort_by='price_asc')
        print(f"   Search 'iPhone': Found {len(results)} products")
        
        results = self.product_service.search_products(
            category_id=demo_data['categories']['electronics'].category_id
        )
        print(f"   Electronics category: Found {len(results)} products")
        
        # 3. View product details
        print("\n3. Product Details")
        iphone = products['iphone']
        print(f"   Product: {iphone.name}")
        print(f"   Price: ${iphone.price}")
        print(f"   Discounted Price: ${iphone.get_discounted_price()}")
        print(f"   Rating: {iphone.rating:.1f}/5 ({iphone.review_count} reviews)")
        
        variants = self.product_service.get_product_variants(iphone.product_id)
        print(f"   Variants: {[(v.variant_type, v.variant_value) for v in variants]}")
        
        stock = self.inventory_service.get_total_stock(iphone.product_id)
        print(f"   Total Stock: {stock} units")
        
        # 4. Shopping Cart
        print("\n4. Shopping Cart")
        cart = self.cart_service.get_or_create_cart(user_id=customer.user_id)
        
        success, msg = self.cart_service.add_to_cart(cart.cart_id, iphone.product_id, 1)
        print(f"   Add iPhone to cart: {msg}")
        
        success, msg = self.cart_service.add_to_cart(
            cart.cart_id, products['python_book'].product_id, 2
        )
        print(f"   Add Python Book (x2) to cart: {msg}")
        
        success, msg = self.cart_service.add_to_cart(
            cart.cart_id, products['tshirt'].product_id, 1
        )
        print(f"   Add T-Shirt to cart: {msg}")
        
        print(f"   Cart items: {cart.get_item_count()}")
        print(f"   Cart subtotal: ${cart.get_subtotal()}")
        
        # Apply coupon
        coupon_obj = self.coupon_service.get_coupon_by_code('SAVE10')
        success, msg = self.cart_service.apply_coupon(cart.cart_id, coupon_obj)
        print(f"   Apply coupon SAVE10: {msg}")
        print(f"   Cart total after discount: ${cart.get_total()}")
        
        # 5. Checkout
        print("\n5. Checkout")
        shipping_address = {
            'street_address': '123 Main Street',
            'city': 'New York',
            'state': 'NY',
            'postal_code': '10001',
            'country': 'USA'
        }
        
        order, msg = self.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=customer.user_id,
            shipping_address=shipping_address,
            payment_method='credit_card'
        )
        
        if order:
            print(f"   Order created: {order.order_number}")
            print(f"   Order total: ${order.total_amount}")
            print(f"   Payment status: {order.payment_status}")
            
            # 6. Order Processing
            print("\n6. Order Processing")
            self.order_service.confirm_order(order.order_id)
            print(f"   Order confirmed: {order.status}")
            
            self.order_service.process_order(order.order_id)
            print(f"   Order processing: {order.status}")
            
            self.order_service.ship_order(
                order.order_id, 
                'TRACK-123456789',
                warehouses['main'].warehouse_id
            )
            print(f"   Order shipped: {order.status}")
            print(f"   Tracking: {order.tracking_number}")
            
            self.order_service.deliver_order(order.order_id)
            print(f"   Order delivered: {order.status}")
        
        # 7. Order History
        print("\n7. Order History")
        user_orders = self.order_service.get_user_orders(customer.user_id)
        print(f"   User has {len(user_orders)} orders")
        
        return order
    
    def demo_inventory_management(self, demo_data: dict):
        """Demonstrate inventory management"""
        print("\n=== Demo Inventory Management ===\n")
        
        admin = demo_data['admin']
        products = demo_data['products']
        warehouses = demo_data['warehouses']
        suppliers = demo_data['suppliers']
        
        # 1. Check inventory levels
        print("1. Current Inventory Levels")
        for name, product in products.items():
            stock = self.inventory_service.get_total_stock(product.product_id)
            print(f"   {product.name}: {stock} units")
        
        # 2. Low stock alerts
        print("\n2. Low Stock Alerts")
        low_stock = self.inventory_service.get_low_stock_items()
        if low_stock:
            for inv in low_stock:
                print(f"   Product {inv.product_id} in Warehouse {inv.warehouse_id}: "
                      f"{inv.get_available_quantity()} units (reorder at {inv.reorder_point})")
        else:
            print("   No low stock items")
        
        # 3. Create and process purchase order
        print("\n3. Purchase Order Management")
        po = self.purchase_order_service.create_purchase_order(
            supplier_id=suppliers['tech'].supplier_id,
            warehouse_id=warehouses['main'].warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=5)
        )
        
        self.purchase_order_service.add_item_to_po(
            po.po_id, products['macbook'].product_id, 20, Decimal('1500.00')
        )
        
        print(f"   Created PO: {po.po_number}")
        print(f"   PO Total: ${po.total_amount}")
        
        self.purchase_order_service.send_purchase_order(po.po_id)
        print(f"   PO Status: {po.status}")
        
        self.purchase_order_service.confirm_purchase_order(po.po_id)
        print(f"   PO Confirmed: {po.status}")
        
        self.purchase_order_service.receive_purchase_order(po.po_id)
        print(f"   PO Received: {po.status}")
        
        # Check updated stock
        macbook_stock = self.inventory_service.get_total_stock(
            products['macbook'].product_id
        )
        print(f"   MacBook stock after receiving: {macbook_stock} units")
        
        # 4. Stock transfer
        print("\n4. Stock Transfer")
        iphone = products['iphone']
        success = self.inventory_service.transfer_stock(
            product_id=iphone.product_id,
            from_warehouse_id=warehouses['main'].warehouse_id,
            to_warehouse_id=warehouses['west_coast'].warehouse_id,
            quantity=20
        )
        print(f"   Transfer 20 iPhones from Main to West Coast: {'Success' if success else 'Failed'}")
        
        main_inv = self.inventory_service.get_inventory(
            iphone.product_id, warehouses['main'].warehouse_id
        )
        west_inv = self.inventory_service.get_inventory(
            iphone.product_id, warehouses['west_coast'].warehouse_id
        )
        print(f"   Main Warehouse iPhone stock: {main_inv.quantity}")
        print(f"   West Coast iPhone stock: {west_inv.quantity}")
        
        # 5. Stock movements history
        print("\n5. Stock Movement History")
        movements = self.inventory_service.get_stock_movements(
            product_id=iphone.product_id
        )
        print(f"   iPhone stock movements: {len(movements)} records")
        for m in movements[-3:]:  # Show last 3
            print(f"   - {m.movement_type}: {m.quantity} units at {m.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    def demo_admin_dashboard(self, demo_data: dict):
        """Demonstrate admin dashboard features"""
        print("\n=== Admin Dashboard ===\n")
        
        # Order statistics
        print("1. Order Statistics")
        stats = self.order_service.get_order_statistics()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # User management
        print("\n2. User Management")
        all_users = self.user_service.get_all_users()
        print(f"   Total users: {len(all_users)}")
        customers = self.user_service.get_all_users('customer')
        print(f"   Customers: {len(customers)}")
        admins = self.user_service.get_all_users('admin')
        print(f"   Admins: {len(admins)}")
        
        # Product management
        print("\n3. Product Management")
        all_products = self.product_service.search_products()
        print(f"   Total active products: {len(all_products)}")
        featured = self.product_service.get_featured_products()
        print(f"   Featured products: {len(featured)}")
        
        # Warehouse overview
        print("\n4. Warehouse Overview")
        warehouses = self.warehouse_service.get_all_warehouses()
        for wh in warehouses:
            inv_items = self.inventory_service.get_warehouse_inventory(wh.warehouse_id)
            total_items = sum(inv.quantity for inv in inv_items)
            print(f"   {wh.name}: {total_items} total items across {len(inv_items)} products")
        
        # Supplier overview
        print("\n5. Supplier Overview")
        suppliers = self.supplier_service.get_all_suppliers()
        print(f"   Total suppliers: {len(suppliers)}")
        for sup in suppliers:
            orders = self.purchase_order_service.get_supplier_orders(sup.supplier_id)
            print(f"   {sup.name}: {len(orders)} purchase orders")
        
        # Purchase orders
        print("\n6. Purchase Orders")
        all_pos = self.purchase_order_service.get_all_purchase_orders()
        print(f"   Total POs: {len(all_pos)}")
        for status in ['draft', 'sent', 'confirmed', 'received', 'cancelled']:
            pos = self.purchase_order_service.get_all_purchase_orders(status)
            if pos:
                print(f"   {status.capitalize()}: {len(pos)}")
        
        # Category tree
        print("\n7. Category Tree")
        tree = self.category_service.get_category_tree()
        for node in tree:
            cat = node['category']
            print(f"   {cat.name}")
            for child_node in node['children']:
                child = child_node['category']
                print(f"     └── {child.name}")


# ============================================================
# DJANGO VIEWS (Simulated)
# ============================================================

class ViewResponse:
    """Simulated HTTP response"""
    
    def __init__(self, status_code: int, data: dict = None, 
                 message: str = '', redirect_url: str = ''):
        self.status_code = status_code
        self.data = data or {}
        self.message = message
        self.redirect_url = redirect_url
        
    def __repr__(self) -> str:
        return f"Response(status={self.status_code}, message={self.message})"


class AuthViews:
    """Authentication views"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        
    def signup(self, username: str, email: str, password: str,
               first_name: str = '', last_name: str = '') -> ViewResponse:
        try:
            user = self.app.user_service.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type='customer'
            )
            return ViewResponse(201, {'user_id': user.user_id}, 
                              'Account created successfully', '/auth/login/')
        except ValueError as e:
            return ViewResponse(400, message=str(e))
    
    def login(self, username: str, password: str) -> ViewResponse:
        user = self.app.user_service.authenticate(username, password)
        if user:
            if not user.is_active:
                return ViewResponse(403, message='Account is deactivated')
            return ViewResponse(200, {
                'user_id': user.user_id,
                'username': user.username,
                'user_type': user.user_type
            }, 'Login successful', '/')
        return ViewResponse(401, message='Invalid credentials')
    
    def logout(self, user_id: int) -> ViewResponse:
        return ViewResponse(200, message='Logged out successfully', 
                          redirect_url='/auth/login/')
    
    def change_password(self, user_id: int, old_password: str, 
                       new_password: str) -> ViewResponse:
        success = self.app.user_service.change_password(
            user_id, old_password, new_password
        )
        if success:
            return ViewResponse(200, message='Password changed successfully')
        return ViewResponse(400, message='Invalid current password')


class ProductViews:
    """Product views"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        
    def product_list(self, query: str = '', category_id: int = None,
                    min_price: float = None, max_price: float = None,
                    sort_by: str = 'name', page: int = 1, 
                    per_page: int = 20) -> ViewResponse:
        products = self.app.product_service.search_products(
            query=query,
            category_id=category_id,
            min_price=Decimal(str(min_price)) if min_price else None,
            max_price=Decimal(str(max_price)) if max_price else None,
            sort_by=sort_by
        )
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated = products[start:end]
        
        return ViewResponse(200, {
            'products': paginated,
            'total': len(products),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(products) + per_page - 1) // per_page
        })
    
    def product_detail(self, product_id: int) -> ViewResponse:
        product = self.app.product_service.get_product(product_id)
        if not product or not product.is_active:
            return ViewResponse(404, message='Product not found')
        
        variants = self.app.product_service.get_product_variants(product_id)
        reviews = self.app.review_service.get_product_reviews(product_id)
        stock = self.app.inventory_service.get_total_stock(product_id)
        
        return ViewResponse(200, {
            'product': product,
            'variants': variants,
            'reviews': reviews,
            'stock': stock,
            'in_stock': stock > 0
        })
    
    def add_review(self, product_id: int, user_id: int, rating: int,
                  title: str = '', body: str = '') -> ViewResponse:
        product = self.app.product_service.get_product(product_id)
        if not product:
            return ViewResponse(404, message='Product not found')
        
        if not 1 <= rating <= 5:
            return ViewResponse(400, message='Rating must be between 1 and 5')
        
        # Check if user purchased the product
        user_orders = self.app.order_service.get_user_orders(user_id)
        is_verified = any(
            any(item['product_id'] == product_id for item in order.items)
            for order in user_orders
            if order.status == 'delivered'
        )
        
        review = self.app.review_service.add_review(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=body,
            is_verified=is_verified
        )
        
        return ViewResponse(201, {'review_id': review.review_id},
                          'Review added successfully')


class CartViews:
    """Shopping cart views"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        
    def view_cart(self, user_id: int = None, 
                  session_id: str = '') -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id, session_id)
        
        cart_items = []
        for key, item in cart.items.items():
            product = self.app.product_service.get_product(item['product_id'])
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'price': item['price'],
                'subtotal': item['price'] * item['quantity'],
                'variant_id': item.get('variant_id')
            })
        
        return ViewResponse(200, {
            'cart': cart,
            'items': cart_items,
            'subtotal': cart.get_subtotal(),
            'discount': cart.discount_amount,
            'total': cart.get_total(),
            'item_count': cart.get_item_count()
        })
    
    def add_to_cart(self, product_id: int, quantity: int,
                   user_id: int = None, session_id: str = '',
                   variant_id: int = None) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id, session_id)
        success, msg = self.app.cart_service.add_to_cart(
            cart.cart_id, product_id, quantity, variant_id
        )
        
        if success:
            return ViewResponse(200, {
                'cart_id': cart.cart_id,
                'item_count': cart.get_item_count()
            }, msg)
        return ViewResponse(400, message=msg)
    
    def remove_from_cart(self, product_id: int, user_id: int = None,
                        session_id: str = '', 
                        variant_id: int = None) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id, session_id)
        success = self.app.cart_service.remove_from_cart(
            cart.cart_id, product_id, variant_id
        )
        
        if success:
            return ViewResponse(200, message='Item removed from cart')
        return ViewResponse(404, message='Item not found in cart')
    
    def update_cart(self, product_id: int, quantity: int,
                   user_id: int = None, session_id: str = '',
                   variant_id: int = None) -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id, session_id)
        success, msg = self.app.cart_service.update_cart_item(
            cart.cart_id, product_id, quantity, variant_id
        )
        
        if success:
            return ViewResponse(200, {
                'item_count': cart.get_item_count(),
                'total': cart.get_total()
            }, msg)
        return ViewResponse(400, message=msg)
    
    def apply_coupon(self, coupon_code: str, user_id: int = None,
                    session_id: str = '') -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id, session_id)
        coupon = self.app.coupon_service.get_coupon_by_code(coupon_code)
        
        if not coupon:
            return ViewResponse(404, message='Invalid coupon code')
        
        success, msg = self.app.cart_service.apply_coupon(cart.cart_id, coupon)
        
        if success:
            return ViewResponse(200, {
                'discount': cart.discount_amount,
                'total': cart.get_total()
            }, msg)
        return ViewResponse(400, message=msg)


class OrderViews:
    """Order views"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        
    def checkout(self, user_id: int, shipping_address: dict,
                billing_address: dict = None,
                payment_method: str = 'credit_card',
                session_id: str = '') -> ViewResponse:
        cart = self.app.cart_service.get_or_create_cart(user_id, session_id)
        
        if not cart.items:
            return ViewResponse(400, message='Cart is empty')
        
        order, msg = self.app.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=user_id,
            shipping_address=shipping_address,
            billing_address=billing_address,
            payment_method=payment_method
        )
        
        if order:
            return ViewResponse(201, {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'total': order.total_amount
            }, msg, f'/orders/{order.order_id}/')
        return ViewResponse(400, message=msg)
    
    def order_list(self, user_id: int) -> ViewResponse:
        orders = self.app.order_service.get_user_orders(user_id)
        return ViewResponse(200, {'orders': orders, 'total': len(orders)})
    
    def order_detail(self, order_id: int, user_id: int) -> ViewResponse:
        order = self.app.order_service.get_order(order_id)
        
        if not order:
            return ViewResponse(404, message='Order not found')
        
        if order.user_id != user_id:
            return ViewResponse(403, message='Access denied')
        
        return ViewResponse(200, {'order': order})
    
    def cancel_order(self, order_id: int, user_id: int,
                    reason: str = '') -> ViewResponse:
        order = self.app.order_service.get_order(order_id)
        
        if not order:
            return ViewResponse(404, message='Order not found')
        
        if order.user_id != user_id:
            return ViewResponse(403, message='Access denied')
        
        success = self.app.order_service.cancel_order(order_id, reason)
        
        if success:
            return ViewResponse(200, message='Order cancelled successfully')
        return ViewResponse(400, message='Order cannot be cancelled')


class AdminViews:
    """Admin views for inventory and order management"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        
    def _check_admin(self, user_id: int) -> bool:
        user = self.app.user_service.get_user(user_id)
        return user and user.user_type in ['admin', 'warehouse_manager']
    
    def dashboard(self, admin_user_id: int) -> ViewResponse:
        if not self._check_admin(admin_user_id):
            return ViewResponse(403, message='Access denied')
        
        stats = self.app.order_service.get_order_statistics()
        low_stock = self.app.inventory_service.get_low_stock_items()
        pending_pos = self.app.purchase_order_service.get_all_purchase_orders('sent')
        
        return ViewResponse(200, {
            'order_stats': stats,
            'low_stock_count': len(low_stock),
            'pending_purchase_orders': len(pending_pos)
        })
    
    def manage_products(self, admin_user_id: int, action: str,
                       product_data: dict = None) -> ViewResponse:
        if not self._check_admin(admin_user_id):
            return ViewResponse(403, message='Access denied')
        
        if action == 'create':
            try:
                product = self.app.product_service.create_product(**product_data)
                return ViewResponse(201, {'product_id': product.product_id},
                                  'Product created')
            except Exception as e:
                return ViewResponse(400, message=str(e))
        
        elif action == 'update':
            product_id = product_data.pop('product_id')
            try:
                product = self.app.product_service.update_product(
                    product_id, **product_data
                )
                return ViewResponse(200, {'product': product}, 'Product updated')
            except ValueError as e:
                return ViewResponse(404, message=str(e))
        
        elif action == 'delete':
            success = self.app.product_service.delete_product(
                product_data['product_id']
            )
            if success:
                return ViewResponse(200, message='Product deactivated')
            return ViewResponse(404, message='Product not found')
        
        return ViewResponse(400, message='Invalid action')
    
    def manage_inventory(self, admin_user_id: int, action: str,
                        inventory_data: dict) -> ViewResponse:
        if not self._check_admin(admin_user_id):
            return ViewResponse(403, message='Access denied')
        
        if action == 'add_stock':
            success = self.app.inventory_service.add_stock(
                product_id=inventory_data['product_id'],
                warehouse_id=inventory_data['warehouse_id'],
                quantity=inventory_data['quantity'],
                notes=inventory_data.get('notes', '')
            )
            return ViewResponse(200 if success else 400,
                              message='Stock added' if success else 'Failed')
        
        elif action == 'adjust':
            success = self.app.inventory_service.adjust_stock(
                product_id=inventory_data['product_id'],
                warehouse_id=inventory_data['warehouse_id'],
                new_quantity=inventory_data['new_quantity'],
                reason=inventory_data.get('reason', '')
            )
            return ViewResponse(200 if success else 400,
                              message='Stock adjusted' if success else 'Failed')
        
        elif action == 'transfer':
            success = self.app.inventory_service.transfer_stock(
                product_id=inventory_data['product_id'],
                from_warehouse_id=inventory_data['from_warehouse_id'],
                to_warehouse_id=inventory_data['to_warehouse_id'],
                quantity=inventory_data['quantity']
            )
            return ViewResponse(200 if success else 400,
                              message='Stock transferred' if success else 'Insufficient stock')
        
        return ViewResponse(400, message='Invalid action')
    
    def manage_orders(self, admin_user_id: int, action: str,
                     order_data: dict) -> ViewResponse:
        if not self._check_admin(admin_user_id):
            return ViewResponse(403, message='Access denied')
        
        order_id = order_data.get('order_id')
        
        if action == 'confirm':
            success = self.app.order_service.confirm_order(order_id)
        elif action == 'process':
            success = self.app.order_service.process_order(order_id)
        elif action == 'ship':
            success = self.app.order_service.ship_order(
                order_id,
                order_data.get('tracking_number', ''),
                order_data.get('warehouse_id')
            )
        elif action == 'deliver':
            success = self.app.order_service.deliver_order(order_id)
        elif action == 'cancel':
            success = self.app.order_service.cancel_order(
                order_id, order_data.get('reason', '')
            )
        elif action == 'refund':
            success = self.app.order_service.refund_order(
                order_id, order_data.get('reason', '')
            )
        else:
            return ViewResponse(400, message='Invalid action')
        
        if success:
            order = self.app.order_service.get_order(order_id)
            return ViewResponse(200, {'status': order.status},
                              f'Order {action} successful')
        return ViewResponse(400, message=f'Cannot {action} order')
    
    def manage_purchase_orders(self, admin_user_id: int, action: str,
                               po_data: dict) -> ViewResponse:
        if not self._check_admin(admin_user_id):
            return ViewResponse(403, message='Access denied')
        
        if action == 'create':
            po = self.app.purchase_order_service.create_purchase_order(
                supplier_id=po_data['supplier_id'],
                warehouse_id=po_data['warehouse_id'],
                created_by=admin_user_id,
                expected_delivery=po_data.get('expected_delivery')
            )
            return ViewResponse(201, {'po_id': po.po_id, 'po_number': po.po_number},
                              'Purchase order created')
        
        po_id = po_data.get('po_id')
        
        if action == 'send':
            success = self.app.purchase_order_service.send_purchase_order(po_id)
        elif action == 'confirm':
            success = self.app.purchase_order_service.confirm_purchase_order(po_id)
        elif action == 'receive':
            success = self.app.purchase_order_service.receive_purchase_order(
                po_id, po_data.get('received_items')
            )
        elif action == 'cancel':
            success = self.app.purchase_order_service.cancel_purchase_order(
                po_id, po_data.get('reason', '')
            )
        else:
            return ViewResponse(400, message='Invalid action')
        
        if success:
            po = self.app.purchase_order_service.get_purchase_order(po_id)
            return ViewResponse(200, {'status': po.status},
                              f'Purchase order {action} successful')
        return ViewResponse(400, message=f'Cannot {action} purchase order')
    
    def manage_users(self, admin_user_id: int, action: str,
                    user_data: dict) -> ViewResponse:
        user = self.app.user_service.get_user(admin_user_id)
        if not user or user.user_type != 'admin':
            return ViewResponse(403, message='Access denied')
        
        if action == 'list':
            users = self.app.user_service.get_all_users(
                user_data.get('user_type')
            )
            return ViewResponse(200, {'users': users, 'total': len(users)})
        
        elif action == 'deactivate':
            success = self.app.user_service.deactivate_user(user_data['user_id'])
            if success:
                return ViewResponse(200, message='User deactivated')
            return ViewResponse(404, message='User not found')
        
        elif action == 'update':
            target_user_id = user_data.pop('user_id')
            try:
                updated_user = self.app.user_service.update_user(
                    target_user_id, **user_data
                )
                return ViewResponse(200, {'user': updated_user}, 'User updated')
            except ValueError as e:
                return ViewResponse(404, message=str(e))
        
        return ViewResponse(400, message='Invalid action')


# ============================================================
# URL ROUTER (Simulated)
# ============================================================

class URLRouter:
    """Simple URL router"""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
        self.auth_views = AuthViews(app)
        self.product_views = ProductViews(app)
        self.cart_views = CartViews(app)
        self.order_views = OrderViews(app)
        self.admin_views = AdminViews(app)
        
        self.routes = {
            'POST /auth/signup/': self.auth_views.signup,
            'POST /auth/login/': self.auth_views.login,
            'POST /auth/logout/': self.auth_views.logout,
            'GET /products/': self.product_views.product_list,
            'GET /products/<id>/': self.product_views.product_detail,
            'GET /cart/': self.cart_views.view_cart,
            'POST /cart/add/': self.cart_views.add_to_cart,
            'POST /cart/remove/': self.cart_views.remove_from_cart,
            'POST /cart/update/': self.cart_views.update_cart,
            'POST /checkout/': self.order_views.checkout,
            'GET /orders/': self.order_views.order_list,
            'GET /orders/<id>/': self.order_views.order_detail,
            'GET /admin/dashboard/': self.admin_views.dashboard,
        }
    
    def get_routes(self) -> list:
        return list(self.routes.keys())


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main function to demonstrate the Amazon Clone"""
    print("=" * 60)
    print("AMAZON CLONE - COMPLETE E-COMMERCE PLATFORM")
    print("=" * 60)
    
    # Initialize application
    app = AmazonCloneApp()
    
    # Setup demo data
    demo_data = app.setup_demo_data()
    
    # Initialize URL router
    router = URLRouter(app)
    print(f"\nRegistered {len(router.get_routes())} URL routes")
    
    # Demo shopping flow
    order = app.demo_shopping_flow(demo_data)
    
    # Demo inventory management
    app.demo_inventory_management(demo_data)
    
    # Demo admin dashboard
    app.demo_admin_dashboard(demo_data)
    
    # Demo API views
    print("\n=== API Views Demo ===\n")
    
    # Test auth views
    auth_views = AuthViews(app)
    
    signup_response = auth_views.signup(
        'new_user', 'new@example.com', 'pass123', 'New', 'User'
    )
    print(f"Signup: {signup_response}")
    
    login_response = auth_views.login('new_user', 'pass123')
    print(f"Login: {login_response}")
    
    failed_login = auth_views.login('new_user', 'wrong_pass')
    print(f"Failed Login: {failed_login}")
    
    # Test product views
    product_views = ProductViews(app)
    
    list_response = product_views.product_list(query='iPhone')
    print(f"\nProduct Search: {list_response}")
    print(f"Found {len(list_response.data.get('products', []))} products")
    
    detail_response = product_views.product_detail(
        demo_data['products']['iphone'].product_id
    )
    print(f"Product Detail: {detail_response}")
    
    # Test cart views
    cart_views = CartViews(app)
    
    add_response = cart_views.add_to_cart(
        product_id=demo_data['products']['samsung'].product_id,
        quantity=1,
        user_id=demo_data['customer'].user_id
    )
    print(f"\nAdd to Cart: {add_response}")
    
    cart_response = cart_views.view_cart(user_id=demo_data['customer'].user_id)
    print(f"View Cart: {cart_response}")
    
    # Test admin views
    admin_views = AdminViews(app)
    
    dashboard_response = admin_views.dashboard(demo_data['admin'].user_id)
    print(f"\nAdmin Dashboard: {dashboard_response}")
    
    # Test inventory management via admin
    inv_response = admin_views.manage_inventory(
        admin_user_id=demo_data['admin'].user_id,
        action='add_stock',
        inventory_data={
            'product_id': demo_data['products']['samsung'].product_id,
            'warehouse_id': demo_data['warehouses']['main'].warehouse_id,
            'quantity': 25,
            'notes': 'Restocking'
        }
    )
    print(f"Add Stock: {inv_response}")
    
    # Test order management via admin
    if order:
        # Create a new order to manage
        new_order, msg = app.order_service.create_order(
            user_id=demo_data['customer'].user_id,
            items=[{
                'product_id': demo_data['products']['python_book'].product_id,
                'product_name': 'Python Programming Book',
                'quantity': 1,
                'unit_price': Decimal('49.99')
            }],
            shipping_address={
                'street_address': '456 Oak Ave',
                'city': 'Boston',
                'state': 'MA',
                'postal_code': '02101',
                'country': 'USA'
            }
        )
        
        if new_order:
            confirm_response = admin_views.manage_orders(
                admin_user_id=demo_data['admin'].user_id,
                action='confirm',
                order_data={'order_id': new_order.order_id}
            )
            print(f"Confirm Order: {confirm_response}")
    
    print("\n" + "=" * 60)
    print("AMAZON CLONE DEMO COMPLETE")
    print("=" * 60)
    
    # Summary
    print("\n=== System Summary ===")
    print(f"Total Users: {len(app.user_service.users)}")
    print(f"Total Products: {len(app.product_service.products)}")
    print(f"Total Categories: {len(app.category_service.categories)}")
    print(f"Total Warehouses: {len(app.warehouse_service.warehouses)}")
    print(f"Total Suppliers: {len(app.supplier_service.suppliers)}")
    print(f"Total Orders: {len(app.order_service.orders)}")
    print(f"Total Purchase Orders: {len(app.purchase_order_service.purchase_orders)}")
    print(f"Total Inventory Records: {len(app.inventory_service.inventory)}")
    print(f"Total Stock Movements: {len(app.inventory_service.stock_movements)}")
    print(f"Total Reviews: {len(app.review_service.reviews)}")
    print(f"Total Coupons: {len(app.coupon_service.coupons)}")
    
    return app


if __name__ == '__main__':
    app = main()