#!/usr/bin/env python3
"""
Amazon Clone - Complete Django Implementation
A fully functional e-commerce platform with inventory management system.
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
    'LOGIN_URL': '/accounts/login/',
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
        
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self) -> str:
        return f"UserProfile(username={self.username}, type={self.user_type})"


class Category:
    """Product category model"""
    
    _id_counter = 1
    
    def __init__(self, name: str, description: str = '', 
                 parent_id: int = None, slug: str = ''):
        self.id = Category._id_counter
        Category._id_counter += 1
        self.name = name
        self.description = description
        self.parent_id = parent_id
        self.slug = slug or name.lower().replace(' ', '-')
        self.is_active = True
        self.created_at = datetime.now()
        
    def __repr__(self) -> str:
        return f"Category(id={self.id}, name={self.name})"


class Supplier:
    """Supplier model for inventory management"""
    
    _id_counter = 1
    
    def __init__(self, name: str, email: str, phone: str,
                 address: str = '', contact_person: str = '',
                 payment_terms: int = 30):
        self.id = Supplier._id_counter
        Supplier._id_counter += 1
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.contact_person = contact_person
        self.payment_terms = payment_terms  # days
        self.is_active = True
        self.rating = 0.0
        self.created_at = datetime.now()
        self.purchase_orders = []
        
    def get_total_orders(self) -> int:
        return len(self.purchase_orders)
    
    def __repr__(self) -> str:
        return f"Supplier(id={self.id}, name={self.name})"


class Warehouse:
    """Warehouse model for inventory management"""
    
    _id_counter = 1
    
    def __init__(self, name: str, location: str, 
                 capacity: int = 10000, manager_id: int = None):
        self.id = Warehouse._id_counter
        Warehouse._id_counter += 1
        self.name = name
        self.location = location
        self.capacity = capacity
        self.manager_id = manager_id
        self.is_active = True
        self.created_at = datetime.now()
        self.inventory_items = {}  # product_id -> quantity
        
    def get_available_space(self) -> int:
        used = sum(self.inventory_items.values())
        return self.capacity - used
    
    def add_stock(self, product_id: int, quantity: int) -> bool:
        if self.get_available_space() >= quantity:
            self.inventory_items[product_id] = \
                self.inventory_items.get(product_id, 0) + quantity
            return True
        return False
    
    def remove_stock(self, product_id: int, quantity: int) -> bool:
        current = self.inventory_items.get(product_id, 0)
        if current >= quantity:
            self.inventory_items[product_id] = current - quantity
            return True
        return False
    
    def get_stock(self, product_id: int) -> int:
        return self.inventory_items.get(product_id, 0)
    
    def __repr__(self) -> str:
        return f"Warehouse(id={self.id}, name={self.name}, location={self.location})"


class Product:
    """Product model"""
    
    _id_counter = 1
    
    def __init__(self, name: str, description: str, price: Decimal,
                 category_id: int, sku: str = '', brand: str = '',
                 weight: float = 0.0, dimensions: str = '',
                 image_url: str = '', is_featured: bool = False):
        self.id = Product._id_counter
        Product._id_counter += 1
        self.name = name
        self.description = description
        self.price = Decimal(str(price))
        self.category_id = category_id
        self.sku = sku or f"SKU-{self.id:06d}"
        self.brand = brand
        self.weight = weight
        self.dimensions = dimensions
        self.image_url = image_url
        self.is_featured = is_featured
        self.is_active = True
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.reviews = []
        self.total_stock = 0
        self.reserved_stock = 0
        
    @property
    def available_stock(self) -> int:
        return self.total_stock - self.reserved_stock
    
    @property
    def average_rating(self) -> float:
        if not self.reviews:
            return 0.0
        return sum(r.rating for r in self.reviews) / len(self.reviews)
    
    def update_price(self, new_price: Decimal) -> None:
        self.price = Decimal(str(new_price))
        self.updated_at = datetime.now()
    
    def is_in_stock(self) -> bool:
        return self.available_stock > 0
    
    def __repr__(self) -> str:
        return f"Product(id={self.id}, name={self.name}, price={self.price})"


class ProductVariant:
    """Product variant model (size, color, etc.)"""
    
    _id_counter = 1
    
    def __init__(self, product_id: int, variant_type: str, 
                 variant_value: str, price_modifier: Decimal = Decimal('0'),
                 stock: int = 0, sku: str = ''):
        self.id = ProductVariant._id_counter
        ProductVariant._id_counter += 1
        self.product_id = product_id
        self.variant_type = variant_type  # size, color, etc.
        self.variant_value = variant_value
        self.price_modifier = Decimal(str(price_modifier))
        self.stock = stock
        self.sku = sku or f"VAR-{self.id:06d}"
        self.is_active = True
        
    def __repr__(self) -> str:
        return f"ProductVariant(product_id={self.product_id}, {self.variant_type}={self.variant_value})"


class InventoryItem:
    """Inventory item tracking model"""
    
    _id_counter = 1
    
    def __init__(self, product_id: int, warehouse_id: int,
                 quantity: int = 0, reorder_point: int = 10,
                 reorder_quantity: int = 100):
        self.id = InventoryItem._id_counter
        InventoryItem._id_counter += 1
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.quantity = quantity
        self.reorder_point = reorder_point
        self.reorder_quantity = reorder_quantity
        self.last_updated = datetime.now()
        self.transactions = []
        
    def needs_reorder(self) -> bool:
        return self.quantity <= self.reorder_point
    
    def add_stock(self, quantity: int, reason: str = '') -> None:
        self.quantity += quantity
        self.last_updated = datetime.now()
        self.transactions.append({
            'type': 'add',
            'quantity': quantity,
            'reason': reason,
            'timestamp': datetime.now()
        })
    
    def remove_stock(self, quantity: int, reason: str = '') -> bool:
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.last_updated = datetime.now()
            self.transactions.append({
                'type': 'remove',
                'quantity': quantity,
                'reason': reason,
                'timestamp': datetime.now()
            })
            return True
        return False
    
    def __repr__(self) -> str:
        return f"InventoryItem(product_id={self.product_id}, warehouse_id={self.warehouse_id}, qty={self.quantity})"


class PurchaseOrder:
    """Purchase order model"""
    
    _id_counter = 1
    STATUS_CHOICES = ['draft', 'pending', 'approved', 'ordered', 'received', 'cancelled']
    
    def __init__(self, supplier_id: int, warehouse_id: int,
                 created_by: int, expected_delivery: datetime = None):
        self.id = PurchaseOrder._id_counter
        PurchaseOrder._id_counter += 1
        self.order_number = f"PO-{self.id:08d}"
        self.supplier_id = supplier_id
        self.warehouse_id = warehouse_id
        self.created_by = created_by
        self.status = 'draft'
        self.items = []
        self.expected_delivery = expected_delivery or (datetime.now() + timedelta(days=7))
        self.actual_delivery = None
        self.notes = ''
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.approved_by = None
        self.approved_at = None
        
    @property
    def total_amount(self) -> Decimal:
        return sum(item['quantity'] * item['unit_price'] for item in self.items)
    
    def add_item(self, product_id: int, quantity: int, 
                 unit_price: Decimal, product_name: str = '') -> None:
        self.items.append({
            'product_id': product_id,
            'product_name': product_name,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'received_quantity': 0
        })
        self.updated_at = datetime.now()
    
    def approve(self, approved_by: int) -> bool:
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = approved_by
            self.approved_at = datetime.now()
            self.updated_at = datetime.now()
            return True
        return False
    
    def submit(self) -> bool:
        if self.status == 'draft' and self.items:
            self.status = 'pending'
            self.updated_at = datetime.now()
            return True
        return False
    
    def mark_ordered(self) -> bool:
        if self.status == 'approved':
            self.status = 'ordered'
            self.updated_at = datetime.now()
            return True
        return False
    
    def receive(self, received_items: dict = None) -> bool:
        if self.status == 'ordered':
            self.status = 'received'
            self.actual_delivery = datetime.now()
            self.updated_at = datetime.now()
            if received_items:
                for item in self.items:
                    if item['product_id'] in received_items:
                        item['received_quantity'] = received_items[item['product_id']]
            return True
        return False
    
    def cancel(self) -> bool:
        if self.status in ['draft', 'pending', 'approved']:
            self.status = 'cancelled'
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"PurchaseOrder(id={self.id}, number={self.order_number}, status={self.status})"


class Address:
    """Address model"""
    
    _id_counter = 1
    
    def __init__(self, user_id: int, address_line1: str, city: str,
                 state: str, country: str, postal_code: str,
                 address_line2: str = '', is_default: bool = False,
                 address_type: str = 'shipping'):
        self.id = Address._id_counter
        Address._id_counter += 1
        self.user_id = user_id
        self.address_line1 = address_line1
        self.address_line2 = address_line2
        self.city = city
        self.state = state
        self.country = country
        self.postal_code = postal_code
        self.is_default = is_default
        self.address_type = address_type  # shipping, billing
        
    def __repr__(self) -> str:
        return f"Address({self.address_line1}, {self.city}, {self.state})"


class Cart:
    """Shopping cart model"""
    
    _id_counter = 1
    
    def __init__(self, user_id: int = None, session_id: str = ''):
        self.id = Cart._id_counter
        Cart._id_counter += 1
        self.user_id = user_id
        self.session_id = session_id
        self.items = {}  # product_id -> CartItem
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.coupon_code = None
        self.discount_amount = Decimal('0')
        
    def add_item(self, product_id: int, quantity: int, 
                 price: Decimal, product_name: str = '',
                 variant_id: int = None) -> None:
        key = (product_id, variant_id)
        if key in self.items:
            self.items[key]['quantity'] += quantity
        else:
            self.items[key] = {
                'product_id': product_id,
                'variant_id': variant_id,
                'product_name': product_name,
                'quantity': quantity,
                'price': Decimal(str(price)),
                'added_at': datetime.now()
            }
        self.updated_at = datetime.now()
    
    def remove_item(self, product_id: int, variant_id: int = None) -> bool:
        key = (product_id, variant_id)
        if key in self.items:
            del self.items[key]
            self.updated_at = datetime.now()
            return True
        return False
    
    def update_quantity(self, product_id: int, quantity: int,
                        variant_id: int = None) -> bool:
        key = (product_id, variant_id)
        if key in self.items:
            if quantity <= 0:
                return self.remove_item(product_id, variant_id)
            self.items[key]['quantity'] = quantity
            self.updated_at = datetime.now()
            return True
        return False
    
    def clear(self) -> None:
        self.items = {}
        self.coupon_code = None
        self.discount_amount = Decimal('0')
        self.updated_at = datetime.now()
    
    @property
    def subtotal(self) -> Decimal:
        return sum(
            item['price'] * item['quantity'] 
            for item in self.items.values()
        )
    
    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount_amount
    
    @property
    def item_count(self) -> int:
        return sum(item['quantity'] for item in self.items.values())
    
    def apply_coupon(self, coupon_code: str, discount: Decimal) -> None:
        self.coupon_code = coupon_code
        self.discount_amount = Decimal(str(discount))
        self.updated_at = datetime.now()
    
    def __repr__(self) -> str:
        return f"Cart(id={self.id}, items={len(self.items)}, total={self.total})"


class Order:
    """Sales order model"""
    
    _id_counter = 1
    STATUS_CHOICES = [
        'pending', 'confirmed', 'processing', 'shipped', 
        'delivered', 'cancelled', 'refunded', 'returned'
    ]
    PAYMENT_STATUS = ['pending', 'paid', 'failed', 'refunded']
    
    def __init__(self, user_id: int, shipping_address_id: int,
                 billing_address_id: int = None, payment_method: str = 'card'):
        self.id = Order._id_counter
        Order._id_counter += 1
        self.order_number = f"ORD-{self.id:010d}"
        self.user_id = user_id
        self.shipping_address_id = shipping_address_id
        self.billing_address_id = billing_address_id or shipping_address_id
        self.payment_method = payment_method
        self.status = 'pending'
        self.payment_status = 'pending'
        self.items = []
        self.subtotal = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.tax_amount = Decimal('0')
        self.discount_amount = Decimal('0')
        self.total_amount = Decimal('0')
        self.coupon_code = None
        self.notes = ''
        self.tracking_number = ''
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.shipped_at = None
        self.delivered_at = None
        self.cancelled_at = None
        self.status_history = []
        
    def add_item(self, product_id: int, product_name: str,
                 quantity: int, unit_price: Decimal,
                 variant_id: int = None) -> None:
        self.items.append({
            'product_id': product_id,
            'product_name': product_name,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'total_price': Decimal(str(unit_price)) * quantity,
            'status': 'pending'
        })
    
    def calculate_totals(self, shipping_cost: Decimal = Decimal('0'),
                         tax_rate: Decimal = Decimal('0.1'),
                         discount: Decimal = Decimal('0')) -> None:
        self.subtotal = sum(item['total_price'] for item in self.items)
        self.shipping_cost = Decimal(str(shipping_cost))
        self.tax_amount = self.subtotal * Decimal(str(tax_rate))
        self.discount_amount = Decimal(str(discount))
        self.total_amount = (self.subtotal + self.shipping_cost + 
                            self.tax_amount - self.discount_amount)
        self.updated_at = datetime.now()
    
    def update_status(self, new_status: str, note: str = '') -> bool:
        if new_status in self.STATUS_CHOICES:
            old_status = self.status
            self.status = new_status
            self.updated_at = datetime.now()
            self.status_history.append({
                'from_status': old_status,
                'to_status': new_status,
                'note': note,
                'timestamp': datetime.now()
            })
            if new_status == 'shipped':
                self.shipped_at = datetime.now()
            elif new_status == 'delivered':
                self.delivered_at = datetime.now()
            elif new_status == 'cancelled':
                self.cancelled_at = datetime.now()
            return True
        return False
    
    def mark_paid(self, transaction_id: str = '') -> None:
        self.payment_status = 'paid'
        self.updated_at = datetime.now()
        if self.status == 'pending':
            self.update_status('confirmed', 'Payment received')
    
    def cancel(self, reason: str = '') -> bool:
        if self.status in ['pending', 'confirmed', 'processing']:
            return self.update_status('cancelled', reason)
        return False
    
    def __repr__(self) -> str:
        return f"Order(id={self.id}, number={self.order_number}, status={self.status})"


class Review:
    """Product review model"""
    
    _id_counter = 1
    
    def __init__(self, product_id: int, user_id: int, 
                 rating: int, title: str = '', body: str = ''):
        self.id = Review._id_counter
        Review._id_counter += 1
        self.product_id = product_id
        self.user_id = user_id
        self.rating = max(1, min(5, rating))  # 1-5 stars
        self.title = title
        self.body = body
        self.is_verified_purchase = False
        self.helpful_votes = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def __repr__(self) -> str:
        return f"Review(product_id={self.product_id}, rating={self.rating})"


class Coupon:
    """Coupon/discount model"""
    
    _id_counter = 1
    
    def __init__(self, code: str, discount_type: str, 
                 discount_value: Decimal, min_order_amount: Decimal = Decimal('0'),
                 max_uses: int = None, valid_from: datetime = None,
                 valid_until: datetime = None):
        self.id = Coupon._id_counter
        Coupon._id_counter += 1
        self.code = code.upper()
        self.discount_type = discount_type  # percentage, fixed
        self.discount_value = Decimal(str(discount_value))
        self.min_order_amount = Decimal(str(min_order_amount))
        self.max_uses = max_uses
        self.current_uses = 0
        self.valid_from = valid_from or datetime.now()
        self.valid_until = valid_until
        self.is_active = True
        self.created_at = datetime.now()
        
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        now = datetime.now()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        if not self.is_valid():
            return Decimal('0')
        if order_amount < self.min_order_amount:
            return Decimal('0')
        if self.discount_type == 'percentage':
            return order_amount * (self.discount_value / 100)
        else:  # fixed
            return min(self.discount_value, order_amount)
    
    def use(self) -> bool:
        if self.is_valid():
            self.current_uses += 1
            return True
        return False
    
    def __repr__(self) -> str:
        return f"Coupon(code={self.code}, type={self.discount_type}, value={self.discount_value})"


class Wishlist:
    """Wishlist model"""
    
    _id_counter = 1
    
    def __init__(self, user_id: int, name: str = 'My Wishlist'):
        self.id = Wishlist._id_counter
        Wishlist._id_counter += 1
        self.user_id = user_id
        self.name = name
        self.items = []
        self.is_public = False
        self.created_at = datetime.now()
        
    def add_item(self, product_id: int) -> bool:
        if product_id not in self.items:
            self.items.append(product_id)
            return True
        return False
    
    def remove_item(self, product_id: int) -> bool:
        if product_id in self.items:
            self.items.remove(product_id)
            return True
        return False
    
    def __repr__(self) -> str:
        return f"Wishlist(user_id={self.user_id}, items={len(self.items)})"


class Notification:
    """Notification model"""
    
    _id_counter = 1
    
    def __init__(self, user_id: int, title: str, message: str,
                 notification_type: str = 'info'):
        self.id = Notification._id_counter
        Notification._id_counter += 1
        self.user_id = user_id
        self.title = title
        self.message = message
        self.notification_type = notification_type  # info, success, warning, error
        self.is_read = False
        self.created_at = datetime.now()
        
    def mark_read(self) -> None:
        self.is_read = True
        
    def __repr__(self) -> str:
        return f"Notification(user_id={self.user_id}, title={self.title})"


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """User management service"""
    
    def __init__(self):
        self.users = {}
        self.user_counter = 1
        
    def create_user(self, username: str, email: str, password: str,
                    first_name: str = '', last_name: str = '',
                    user_type: str = 'customer') -> UserProfile:
        if username in self.users:
            raise ValueError(f"Username '{username}' already exists")
        
        user = UserProfile(
            user_id=self.user_counter,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type
        )
        self.users[username] = user
        self.user_counter += 1
        return user
    
    def authenticate(self, username: str, password: str) -> UserProfile:
        user = self.users.get(username)
        if user and user.is_active:
            user.last_login = datetime.now()
            return user
        return None
    
    def get_user(self, username: str) -> UserProfile:
        return self.users.get(username)
    
    def get_user_by_id(self, user_id: int) -> UserProfile:
        for user in self.users.values():
            if user.user_id == user_id:
                return user
        return None
    
    def update_user(self, username: str, **kwargs) -> UserProfile:
        user = self.users.get(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        return user
    
    def deactivate_user(self, username: str) -> bool:
        user = self.users.get(username)
        if user:
            user.is_active = False
            return True
        return False
    
    def get_all_users(self, user_type: str = None) -> list:
        if user_type:
            return [u for u in self.users.values() if u.user_type == user_type]
        return list(self.users.values())


class CategoryService:
    """Category management service"""
    
    def __init__(self):
        self.categories = {}
        
    def create_category(self, name: str, description: str = '',
                        parent_id: int = None) -> Category:
        category = Category(name=name, description=description, parent_id=parent_id)
        self.categories[category.id] = category
        return category
    
    def get_category(self, category_id: int) -> Category:
        return self.categories.get(category_id)
    
    def get_all_categories(self, active_only: bool = True) -> list:
        if active_only:
            return [c for c in self.categories.values() if c.is_active]
        return list(self.categories.values())
    
    def get_subcategories(self, parent_id: int) -> list:
        return [c for c in self.categories.values() if c.parent_id == parent_id]
    
    def get_root_categories(self) -> list:
        return [c for c in self.categories.values() if c.parent_id is None]


class ProductService:
    """Product management service"""
    
    def __init__(self):
        self.products = {}
        self.variants = {}
        
    def create_product(self, name: str, description: str, price: Decimal,
                       category_id: int, **kwargs) -> Product:
        product = Product(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            **kwargs
        )
        self.products[product.id] = product
        return product
    
    def get_product(self, product_id: int) -> Product:
        return self.products.get(product_id)
    
    def update_product(self, product_id: int, **kwargs) -> Product:
        product = self.products.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        for key, value in kwargs.items():
            if hasattr(product, key):
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
                        in_stock_only: bool = False,
                        sort_by: str = 'name') -> list:
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
            results = [p for p in results if p.price >= Decimal(str(min_price))]
        
        if max_price is not None:
            results = [p for p in results if p.price <= Decimal(str(max_price))]
        
        if in_stock_only:
            results = [p for p in results if p.is_in_stock()]
        
        if sort_by == 'price_asc':
            results.sort(key=lambda p: p.price)
        elif sort_by == 'price_desc':
            results.sort(key=lambda p: p.price, reverse=True)
        elif sort_by == 'rating':
            results.sort(key=lambda p: p.average_rating, reverse=True)
        elif sort_by == 'newest':
            results.sort(key=lambda p: p.created_at, reverse=True)
        else:
            results.sort(key=lambda p: p.name)
        
        return results
    
    def get_featured_products(self) -> list:
        return [p for p in self.products.values() if p.is_featured and p.is_active]
    
    def add_variant(self, product_id: int, variant_type: str,
                    variant_value: str, price_modifier: Decimal = Decimal('0'),
                    stock: int = 0) -> ProductVariant:
        variant = ProductVariant(
            product_id=product_id,
            variant_type=variant_type,
            variant_value=variant_value,
            price_modifier=price_modifier,
            stock=stock
        )
        self.variants[variant.id] = variant
        return variant
    
    def get_product_variants(self, product_id: int) -> list:
        return [v for v in self.variants.values() if v.product_id == product_id]
    
    def add_review(self, product_id: int, user_id: int, rating: int,
                   title: str = '', body: str = '') -> Review:
        product = self.products.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        review = Review(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=body
        )
        product.reviews.append(review)
        return review
    
    def get_all_products(self, active_only: bool = True) -> list:
        if active_only:
            return [p for p in self.products.values() if p.is_active]
        return list(self.products.values())


class InventoryService:
    """Inventory management service"""
    
    def __init__(self):
        self.inventory_items = {}
        self.warehouses = {}
        self.suppliers = {}
        self.purchase_orders = {}
        
    def add_warehouse(self, name: str, location: str,
                      capacity: int = 10000) -> Warehouse:
        warehouse = Warehouse(name=name, location=location, capacity=capacity)
        self.warehouses[warehouse.id] = warehouse
        return warehouse
    
    def get_warehouse(self, warehouse_id: int) -> Warehouse:
        return self.warehouses.get(warehouse_id)
    
    def add_supplier(self, name: str, email: str, phone: str,
                     **kwargs) -> Supplier:
        supplier = Supplier(name=name, email=email, phone=phone, **kwargs)
        self.suppliers[supplier.id] = supplier
        return supplier
    
    def get_supplier(self, supplier_id: int) -> Supplier:
        return self.suppliers.get(supplier_id)
    
    def create_inventory_item(self, product_id: int, warehouse_id: int,
                              quantity: int = 0, reorder_point: int = 10,
                              reorder_quantity: int = 100) -> InventoryItem:
        key = (product_id, warehouse_id)
        if key in self.inventory_items:
            return self.inventory_items[key]
        
        item = InventoryItem(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity
        )
        self.inventory_items[key] = item
        return item
    
    def get_inventory_item(self, product_id: int, 
                           warehouse_id: int) -> InventoryItem:
        return self.inventory_items.get((product_id, warehouse_id))
    
    def get_total_stock(self, product_id: int) -> int:
        total = 0
        for (pid, wid), item in self.inventory_items.items():
            if pid == product_id:
                total += item.quantity
        return total
    
    def add_stock(self, product_id: int, warehouse_id: int,
                  quantity: int, reason: str = '') -> bool:
        item = self.get_inventory_item(product_id, warehouse_id)
        if not item:
            item = self.create_inventory_item(product_id, warehouse_id)
        item.add_stock(quantity, reason)
        
        warehouse = self.warehouses.get(warehouse_id)
        if warehouse:
            warehouse.add_stock(product_id, quantity)
        return True
    
    def remove_stock(self, product_id: int, warehouse_id: int,
                     quantity: int, reason: str = '') -> bool:
        item = self.get_inventory_item(product_id, warehouse_id)
        if not item:
            return False
        
        if item.remove_stock(quantity, reason):
            warehouse = self.warehouses.get(warehouse_id)
            if warehouse:
                warehouse.remove_stock(product_id, quantity)
            return True
        return False
    
    def transfer_stock(self, product_id: int, from_warehouse_id: int,
                       to_warehouse_id: int, quantity: int) -> bool:
        if self.remove_stock(product_id, from_warehouse_id, quantity, 'Transfer out'):
            self.add_stock(product_id, to_warehouse_id, quantity, 'Transfer in')
            return True
        return False
    
    def get_low_stock_items(self) -> list:
        return [item for item in self.inventory_items.values() 
                if item.needs_reorder()]
    
    def create_purchase_order(self, supplier_id: int, warehouse_id: int,
                              created_by: int,
                              expected_delivery: datetime = None) -> PurchaseOrder:
        po = PurchaseOrder(
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            created_by=created_by,
            expected_delivery=expected_delivery
        )
        self.purchase_orders[po.id] = po
        
        supplier = self.suppliers.get(supplier_id)
        if supplier:
            supplier.purchase_orders.append(po.id)
        
        return po
    
    def get_purchase_order(self, po_id: int) -> PurchaseOrder:
        return self.purchase_orders.get(po_id)
    
    def receive_purchase_order(self, po_id: int, 
                               received_items: dict = None) -> bool:
        po = self.purchase_orders.get(po_id)
        if not po:
            return False
        
        if po.receive(received_items):
            for item in po.items:
                qty = item.get('received_quantity', item['quantity'])
                self.add_stock(
                    item['product_id'], 
                    po.warehouse_id, 
                    qty,
                    f"Purchase Order {po.order_number}"
                )
            return True
        return False
    
    def get_all_purchase_orders(self, status: str = None) -> list:
        if status:
            return [po for po in self.purchase_orders.values() 
                    if po.status == status]
        return list(self.purchase_orders.values())
    
    def get_warehouse_inventory(self, warehouse_id: int) -> list:
        return [item for (pid, wid), item in self.inventory_items.items()
                if wid == warehouse_id]
    
    def get_inventory_report(self) -> dict:
        report = {
            'total_products': len(set(pid for pid, _ in self.inventory_items.keys())),
            'total_warehouses': len(self.warehouses),
            'total_suppliers': len(self.suppliers),
            'low_stock_items': len(self.get_low_stock_items()),
            'pending_purchase_orders': len(self.get_all_purchase_orders('pending')),
            'warehouse_summary': {}
        }
        
        for wid, warehouse in self.warehouses.items():
            items = self.get_warehouse_inventory(wid)
            report['warehouse_summary'][warehouse.name] = {
                'total_items': len(items),
                'total_quantity': sum(i.quantity for i in items),
                'available_space': warehouse.get_available_space()
            }
        
        return report


class CartService:
    """Shopping cart service"""
    
    def __init__(self):
        self.carts = {}
        self.coupons = {}
        
    def get_or_create_cart(self, user_id: int = None, 
                           session_id: str = '') -> Cart:
        key = user_id or session_id
        if key not in self.carts:
            self.carts[key] = Cart(user_id=user_id, session_id=session_id)
        return self.carts[key]
    
    def add_to_cart(self, cart: Cart, product: Product, quantity: int,
                    variant_id: int = None) -> bool:
        if not product.is_in_stock():
            return False
        if quantity > product.available_stock:
            quantity = product.available_stock
        
        cart.add_item(
            product_id=product.id,
            quantity=quantity,
            price=product.price,
            product_name=product.name,
            variant_id=variant_id
        )
        return True
    
    def apply_coupon(self, cart: Cart, coupon_code: str) -> dict:
        coupon = self.coupons.get(coupon_code.upper())
        if not coupon:
            return {'success': False, 'message': 'Invalid coupon code'}
        
        if not coupon.is_valid():
            return {'success': False, 'message': 'Coupon is expired or invalid'}
        
        if cart.subtotal < coupon.min_order_amount:
            return {
                'success': False, 
                'message': f'Minimum order amount is {coupon.min_order_amount}'
            }
        
        discount = coupon.calculate_discount(cart.subtotal)
        cart.apply_coupon(coupon_code, discount)
        return {
            'success': True, 
            'message': f'Coupon applied! Discount: {discount}',
            'discount': discount
        }
    
    def add_coupon(self, code: str, discount_type: str,
                   discount_value: Decimal, **kwargs) -> Coupon:
        coupon = Coupon(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            **kwargs
        )
        self.coupons[coupon.code] = coupon
        return coupon
    
    def merge_carts(self, session_cart: Cart, user_cart: Cart) -> Cart:
        for key, item in session_cart.items.items():
            user_cart.add_item(
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price'],
                product_name=item['product_name'],
                variant_id=item['variant_id']
            )
        return user_cart


class OrderService:
    """Order management service"""
    
    def __init__(self, inventory_service: InventoryService):
        self.orders = {}
        self.inventory_service = inventory_service
        self.addresses = {}
        
    def create_address(self, user_id: int, address_line1: str, city: str,
                       state: str, country: str, postal_code: str,
                       **kwargs) -> Address:
        address = Address(
            user_id=user_id,
            address_line1=address_line1,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            **kwargs
        )
        self.addresses[address.id] = address
        return address
    
    def get_user_addresses(self, user_id: int) -> list:
        return [a for a in self.addresses.values() if a.user_id == user_id]
    
    def create_order_from_cart(self, cart: Cart, user_id: int,
                               shipping_address_id: int,
                               billing_address_id: int = None,
                               payment_method: str = 'card',
                               warehouse_id: int = 1) -> Order:
        if not cart.items:
            raise ValueError("Cart is empty")
        
        order = Order(
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id,
            payment_method=payment_method
        )
        
        for key, item in cart.items.items():
            order.add_item(
                product_id=item['product_id'],
                product_name=item['product_name'],
                quantity=item['quantity'],
                unit_price=item['price'],
                variant_id=item['variant_id']
            )
        
        shipping_cost = self._calculate_shipping(cart.subtotal)
        order.calculate_totals(
            shipping_cost=shipping_cost,
            discount=cart.discount_amount
        )
        order.coupon_code = cart.coupon_code
        
        self.orders[order.id] = order
        return order
    
    def _calculate_shipping(self, subtotal: Decimal) -> Decimal:
        if subtotal >= Decimal('50'):
            return Decimal('0')  # Free shipping over $50
        return Decimal('9.99')
    
    def process_payment(self, order: Order, 
                        payment_details: dict) -> dict:
        # Simulate payment processing
        order.mark_paid(transaction_id=f"TXN-{order.id:010d}")
        return {
            'success': True,
            'transaction_id': f"TXN-{order.id:010d}",
            'message': 'Payment processed successfully'
        }
    
    def fulfill_order(self, order_id: int, 
                      warehouse_id: int = 1) -> bool:
        order = self.orders.get(order_id)
        if not order or order.status != 'confirmed':
            return False
        
        # Reserve stock
        for item in order.items:
            success = self.inventory_service.remove_stock(
                item['product_id'],
                warehouse_id,
                item['quantity'],
                f"Order {order.order_number}"
            )
            if not success:
                return False
        
        order.update_status('processing', 'Order being processed')
        return True
    
    def ship_order(self, order_id: int, 
                   tracking_number: str = '') -> bool:
        order = self.orders.get(order_id)
        if not order or order.status != 'processing':
            return False
        
        order.tracking_number = tracking_number
        order.update_status('shipped', f'Tracking: {tracking_number}')
        return True
    
    def deliver_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if not order or order.status != 'shipped':
            return False
        
        order.update_status('delivered', 'Order delivered')
        return True
    
    def cancel_order(self, order_id: int, reason: str = '',
                     warehouse_id: int = 1) -> bool:
        order = self.orders.get(order_id)
        if not order:
            return False
        
        if order.cancel(reason):
            # Restore stock if order was being processed
            if order.status in ['processing']:
                for item in order.items:
                    self.inventory_service.add_stock(
                        item['product_id'],
                        warehouse_id,
                        item['quantity'],
                        f"Cancelled Order {order.order_number}"
                    )
            return True
        return False
    
    def get_order(self, order_id: int) -> Order:
        return self.orders.get(order_id)
    
    def get_user_orders(self, user_id: int) -> list:
        return [o for o in self.orders.values() if o.user_id == user_id]
    
    def get_all_orders(self, status: str = None) -> list:
        if status:
            return [o for o in self.orders.values() if o.status == status]
        return list(self.orders.values())
    
    def get_order_statistics(self) -> dict:
        orders = list(self.orders.values())
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
            'total_revenue': total_revenue
        }


class WishlistService:
    """Wishlist management service"""
    
    def __init__(self):
        self.wishlists = {}
        
    def get_or_create_wishlist(self, user_id: int) -> Wishlist:
        if user_id not in self.wishlists:
            self.wishlists[user_id] = Wishlist(user_id=user_id)
        return self.wishlists[user_id]
    
    def add_to_wishlist(self, user_id: int, product_id: int) -> bool:
        wishlist = self.get_or_create_wishlist(user_id)
        return wishlist.add_item(product_id)
    
    def remove_from_wishlist(self, user_id: int, product_id: int) -> bool:
        wishlist = self.wishlists.get(user_id)
        if wishlist:
            return wishlist.remove_item(product_id)
        return False
    
    def get_wishlist(self, user_id: int) -> Wishlist:
        return self.wishlists.get(user_id)


class NotificationService:
    """Notification management service"""
    
    def __init__(self):
        self.notifications = {}
        
    def send_notification(self, user_id: int, title: str, 
                          message: str, notification_type: str = 'info') -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        if user_id not in self.notifications:
            self.notifications[user_id] = []
        self.notifications[user_id].append(notification)
        return notification
    
    def get_user_notifications(self, user_id: int, 
                               unread_only: bool = False) -> list:
        notifications = self.notifications.get(user_id, [])
        if unread_only:
            return [n for n in notifications if not n.is_read]
        return notifications
    
    def mark_all_read(self, user_id: int) -> None:
        for notification in self.notifications.get(user_id, []):
            notification.mark_read()
    
    def get_unread_count(self, user_id: int) -> int:
        return len(self.get_user_notifications(user_id, unread_only=True))


# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class AmazonClone:
    """Main Amazon Clone application"""
    
    def __init__(self):
        self.user_service = UserService()
        self.category_service = CategoryService()
        self.product_service = ProductService()
        self.inventory_service = InventoryService()
        self.cart_service = CartService()
        self.order_service = OrderService(self.inventory_service)
        self.wishlist_service = WishlistService()
        self.notification_service = NotificationService()
        
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize sample data for demonstration"""
        
        # Create admin user
        admin = self.user_service.create_user(
            username='admin',
            email='admin@amazonclone.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        
        # Create sample customers
        customer1 = self.user_service.create_user(
            username='john_doe',
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        
        customer2 = self.user_service.create_user(
            username='jane_smith',
            email='jane@example.com',
            password='password123',
            first_name='Jane',
            last_name='Smith',
            user_type='customer'
        )
        
        # Create warehouse manager
        wm = self.user_service.create_user(
            username='warehouse_mgr',
            email='wm@amazonclone.com',
            password='password123',
            first_name='Warehouse',
            last_name='Manager',
            user_type='warehouse_manager'
        )
        
        # Create categories
        electronics = self.category_service.create_category(
            'Electronics', 'Electronic devices and accessories'
        )
        books = self.category_service.create_category(
            'Books', 'Books and literature'
        )
        clothing = self.category_service.create_category(
            'Clothing', 'Clothing and apparel'
        )
        home = self.category_service.create_category(
            'Home & Garden', 'Home and garden products'
        )
        
        # Subcategories
        phones = self.category_service.create_category(
            'Smartphones', 'Mobile phones', parent_id=electronics.id
        )
        laptops = self.category_service.create_category(
            'Laptops', 'Laptop computers', parent_id=electronics.id
        )
        
        # Create warehouses
        warehouse1 = self.inventory_service.add_warehouse(
            'Main Warehouse', 'New York, NY', capacity=50000
        )
        warehouse2 = self.inventory_service.add_warehouse(
            'West Coast Warehouse', 'Los Angeles, CA', capacity=30000
        )
        
        # Create suppliers
        supplier1 = self.inventory_service.add_supplier(
            name='TechSupplies Inc',
            email='orders@techsupplies.com',
            phone='+1-555-0100',
            address='123 Tech Street, San Jose, CA',
            contact_person='Bob Johnson',
            payment_terms=30
        )
        
        supplier2 = self.inventory_service.add_supplier(
            name='Global Electronics',
            email='supply@globalelec.com',
            phone='+1-555-0200',
            address='456 Electronics Ave, Austin, TX',
            contact_person='Alice Chen',
            payment_terms=45
        )
        
        # Create products
        iphone = self.product_service.create_product(
            name='iPhone 15 Pro',
            description='Latest Apple iPhone with advanced features',
            price=Decimal('999.99'),
            category_id=phones.id,
            brand='Apple',
            weight=0.187,
            is_featured=True
        )
        
        samsung = self.product_service.create_product(
            name='Samsung Galaxy S24',
            description='Samsung flagship smartphone',
            price=Decimal('899.99'),
            category_id=phones.id,
            brand='Samsung',
            weight=0.195,
            is_featured=True
        )
        
        macbook = self.product_service.create_product(
            name='MacBook Pro 14"',
            description='Apple MacBook Pro with M3 chip',
            price=Decimal('1999.99'),
            category_id=laptops.id,
            brand='Apple',
            weight=1.6,
            is_featured=True
        )
        
        python_book = self.product_service.create_product(
            name='Python Programming',
            description='Complete guide to Python programming',
            price=Decimal('49.99'),
            category_id=books.id,
            brand='Tech Books',
            weight=0.5
        )
        
        tshirt = self.product_service.create_product(
            name='Classic T-Shirt',
            description='Comfortable cotton t-shirt',
            price=Decimal('19.99'),
            category_id=clothing.id,
            brand='BasicWear',
            weight=0.2
        )
        
        # Add product variants
        self.product_service.add_variant(
            iphone.id, 'storage', '128GB', Decimal('0'), 50
        )
        self.product_service.add_variant(
            iphone.id, 'storage', '256GB', Decimal('100'), 30
        )
        self.product_service.add_variant(
            iphone.id, 'color', 'Black', Decimal('0'), 40
        )
        self.product_service.add_variant(
            iphone.id, 'color', 'White', Decimal('0'), 40
        )
        
        self.product_service.add_variant(
            tshirt.id, 'size', 'S', Decimal('0'), 100
        )
        self.product_service.add_variant(
            tshirt.id, 'size', 'M', Decimal('0'), 150
        )
        self.product_service.add_variant(
            tshirt.id, 'size', 'L', Decimal('0'), 120
        )
        
        # Add inventory
        products_to_stock = [
            (iphone.id, 100),
            (samsung.id, 80),
            (macbook.id, 50),
            (python_book.id, 200),
            (tshirt.id, 500)
        ]
        
        for product_id, quantity in products_to_stock:
            self.inventory_service.add_stock(
                product_id, warehouse1.id, quantity, 'Initial stock'
            )
            product = self.product_service.get_product(product_id)
            if product:
                product.total_stock = quantity
        
        # Add some stock to warehouse 2
        self.inventory_service.add_stock(
            iphone.id, warehouse2.id, 50, 'Initial stock'
        )
        
        # Create purchase order
        po = self.inventory_service.create_purchase_order(
            supplier_id=supplier1.id,
            warehouse_id=warehouse1.id,
            created_by=admin.user_id
        )
        po.add_item(iphone.id, 200, Decimal('750.00'), 'iPhone 15 Pro')
        po.add_item(samsung.id, 150, Decimal('650.00'), 'Samsung Galaxy S24')
        po.submit()
        po.approve(admin.user_id)
        
        # Add coupons
        self.cart_service.add_coupon(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('50')
        )
        
        self.cart_service.add_coupon(
            code='FLAT20',
            discount_type='fixed',
            discount_value=Decimal('20'),
            min_order_amount=Decimal('100')
        )
        
        # Add reviews
        self.product_service.add_review(
            iphone.id, customer1.user_id, 5,
            'Amazing phone!', 'Best iPhone ever made.'
        )
        self.product_service.add_review(
            iphone.id, customer2.user_id, 4,
            'Great phone', 'Very good but expensive.'
        )
        
        # Create sample order
        address = self.order_service.create_address(
            user_id=customer1.user_id,
            address_line1='123 Main St',
            city='New York',
            state='NY',
            country='USA',
            postal_code='10001',
            is_default=True
        )
        
        cart = self.cart_service.get_or_create_cart(user_id=customer1.user_id)
        self.cart_service.add_to_cart(cart, iphone, 1)
        self.cart_service.add_to_cart(cart, python_book, 2)
        
        order = self.order_service.create_order_from_cart(
            cart=cart,
            user_id=customer1.user_id,
            shipping_address_id=address.id,
            payment_method='card'
        )
        
        self.order_service.process_payment(order, {'card_number': '****1234'})
        cart.clear()
        
        # Send notification
        self.notification_service.send_notification(
            user_id=customer1.user_id,
            title='Order Confirmed',
            message=f'Your order {order.order_number} has been confirmed!',
            notification_type='success'
        )
    
    def register_user(self, username: str, email: str, password: str,
                      first_name: str = '', last_name: str = '') -> dict:
        try:
            user = self.user_service.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            self.notification_service.send_notification(
                user_id=user.user_id,
                title='Welcome!',
                message=f'Welcome to Amazon Clone, {user.get_full_name() or username}!',
                notification_type='success'
            )
            return {'success': True, 'user': user, 'message': 'Registration successful'}
        except ValueError as e:
            return {'success': False, 'message': str(e)}
    
    def login(self, username: str, password: str) -> dict:
        user = self.user_service.authenticate(username, password)
        if user:
            return {'success': True, 'user': user, 'message': 'Login successful'}
        return {'success': False, 'message': 'Invalid credentials'}
    
    def search_products(self, query: str = '', **kwargs) -> list:
        return self.product_service.search_products(query=query, **kwargs)
    
    def get_product_detail(self, product_id: int) -> dict:
        product = self.product_service.get_product(product_id)
        if not product:
            return None
        
        variants = self.product_service.get_product_variants(product_id)
        total_stock = self.inventory_service.get_total_stock(product_id)
        product.total_stock = total_stock
        
        return {
            'product': product,
            'variants': variants,
            'reviews': product.reviews,
            'average_rating': product.average_rating,
            'in_stock': product.is_in_stock()
        }
    
    def add_to_cart(self, user_id: int, product_id: int, 
                    quantity: int = 1, variant_id: int = None) -> dict:
        product = self.product_service.get_product(product_id)
        if not product:
            return {'success': False, 'message': 'Product not found'}
        
        cart = self.cart_service.get_or_create_cart(user_id=user_id)
        success = self.cart_service.add_to_cart(cart, product, quantity, variant_id)
        
        if success:
            return {
                'success': True, 
                'message': 'Added to cart',
                'cart_count': cart.item_count
            }
        return {'success': False, 'message': 'Product out of stock'}
    
    def checkout(self, user_id: int, shipping_address_id: int,
                 payment_method: str = 'card',
                 coupon_code: str = None) -> dict:
        cart = self.cart_service.get_or_create_cart(user_id=user_id)
        
        if not cart.items:
            return {'success': False, 'message': 'Cart is empty'}
        
        if coupon_code:
            coupon_result = self.cart_service.apply_coupon(cart, coupon_code)
            if not coupon_result['success']:
                return coupon_result
        
        try:
            order = self.order_service.create_order_from_cart(
                cart=cart,
                user_id=user_id,
                shipping_address_id=shipping_address_id,
                payment_method=payment_method
            )
            
            payment_result = self.order_service.process_payment(
                order, {'method': payment_method}
            )
            
            if payment_result['success']:
                cart.clear()
                self.notification_service.send_notification(
                    user_id=user_id,
                    title='Order Placed!',
                    message=f'Order {order.order_number} placed successfully. Total: ${order.total_amount}',
                    notification_type='success'
                )
                return {
                    'success': True,
                    'order': order,
                    'message': f'Order {order.order_number} placed successfully'
                }
            else:
                return {'success': False, 'message': 'Payment failed'}
                
        except ValueError as e:
            return {'success': False, 'message': str(e)}
    
    def get_dashboard_stats(self) -> dict:
        order_stats = self.order_service.get_order_statistics()
        inventory_report = self.inventory_service.get_inventory_report()
        
        all_products = self.product_service.get_all_products()
        all_users = self.user_service.get_all_users()
        
        return {
            'orders': order_stats,
            'inventory': inventory_report,
            'total_products': len(all_products),
            'total_users': len(all_users),
            'total_customers': len(self.user_service.get_all_users('customer')),
            'featured_products': len(self.product_service.get_featured_products()),
            'low_stock_alerts': len(self.inventory_service.get_low_stock_items())
        }
    
    def get_admin_inventory_report(self) -> dict:
        return self.inventory_service.get_inventory_report()
    
    def manage_purchase_order(self, action: str, po_id: int = None,
                              **kwargs) -> dict:
        if action == 'create':
            po = self.inventory_service.create_purchase_order(**kwargs)
            return {'success': True, 'purchase_order': po}
        
        elif action == 'add_item':
            po = self.inventory_service.get_purchase_order(po_id)
            if po:
                po.add_item(**kwargs)
                return {'success': True, 'purchase_order': po}
            return {'success': False, 'message': 'Purchase order not found'}
        
        elif action == 'submit':
            po = self.inventory_service.get_purchase_order(po_id)
            if po and po.submit():
                return {'success': True, 'message': 'Purchase order submitted'}
            return {'success': False, 'message': 'Cannot submit purchase order'}
        
        elif action == 'approve':
            po = self.inventory_service.get_purchase_order(po_id)
            approved_by = kwargs.get('approved_by')
            if po and po.approve(approved_by):
                return {'success': True, 'message': 'Purchase order approved'}
            return {'success': False, 'message': 'Cannot approve purchase order'}
        
        elif action == 'receive':
            success = self.inventory_service.receive_purchase_order(
                po_id, kwargs.get('received_items')
            )
            if success:
                return {'success': True, 'message': 'Purchase order received'}
            return {'success': False, 'message': 'Cannot receive purchase order'}
        
        elif action == 'cancel':
            po = self.inventory_service.get_purchase_order(po_id)
            if po and po.cancel():
                return {'success': True, 'message': 'Purchase order cancelled'}
            return {'success': False, 'message': 'Cannot cancel purchase order'}
        
        return {'success': False, 'message': 'Invalid action'}


# ============================================================
# URL PATTERNS (Simulated)
# ============================================================

URL_PATTERNS = {
    # Authentication
    'accounts/login/': 'LoginView',
    'accounts/logout/': 'LogoutView',
    'accounts/register/': 'RegisterView',
    'accounts/profile/': 'ProfileView',
    'accounts/profile/edit/': 'EditProfileView',
    'accounts/addresses/': 'AddressListView',
    'accounts/addresses/add/': 'AddAddressView',
    
    # Products
    '': 'HomeView',
    'products/': 'ProductListView',
    'products/<int:pk>/': 'ProductDetailView',
    'products/search/': 'ProductSearchView',
    'products/category/<int:category_id>/': 'CategoryProductView',
    
    # Cart
    'cart/': 'CartView',
    'cart/add/<int:product_id>/': 'AddToCartView',
    'cart/remove/<int:product_id>/': 'RemoveFromCartView',
    'cart/update/': 'UpdateCartView',
    'cart/apply-coupon/': 'ApplyCouponView',
    
    # Checkout
    'checkout/': 'CheckoutView',
    'checkout/payment/': 'PaymentView',
    'checkout/success/<int:order_id>/': 'OrderSuccessView',
    
    # Orders
    'orders/': 'OrderListView',
    'orders/<int:order_id>/': 'OrderDetailView',
    'orders/<int:order_id>/cancel/': 'CancelOrderView',
    'orders/<int:order_id>/track/': 'TrackOrderView',
    
    # Wishlist
    'wishlist/': 'WishlistView',
    'wishlist/add/<int:product_id>/': 'AddToWishlistView',
    'wishlist/remove/<int:product_id>/': 'RemoveFromWishlistView',
    
    # Admin - Inventory
    'admin/inventory/': 'InventoryDashboardView',
    'admin/inventory/products/': 'AdminProductListView',
    'admin/inventory/products/add/': 'AdminAddProductView',
    'admin/inventory/products/<int:pk>/edit/': 'AdminEditProductView',
    'admin/inventory/warehouses/': 'WarehouseListView',
    'admin/inventory/warehouses/add/': 'AddWarehouseView',
    'admin/inventory/suppliers/': 'SupplierListView',
    'admin/inventory/suppliers/add/': 'AddSupplierView',
    'admin/inventory/purchase-orders/': 'PurchaseOrderListView',
    'admin/inventory/purchase-orders/create/': 'CreatePurchaseOrderView',
    'admin/inventory/purchase-orders/<int:pk>/': 'PurchaseOrderDetailView',
    'admin/inventory/stock/': 'StockManagementView',
    'admin/inventory/stock/transfer/': 'StockTransferView',
    'admin/inventory/reports/': 'InventoryReportView',
    
    # Admin - Orders
    'admin/orders/': 'AdminOrderListView',
    'admin/orders/<int:order_id>/': 'AdminOrderDetailView',
    'admin/orders/<int:order_id>/update/': 'UpdateOrderStatusView',
    
    # Admin - Users
    'admin/users/': 'AdminUserListView',
    'admin/users/<int:user_id>/': 'AdminUserDetailView',
    'admin/users/<int:user_id>/edit/': 'AdminEditUserView',
    
    # Admin - Dashboard
    'admin/dashboard/': 'AdminDashboardView',
    'admin/reports/sales/': 'SalesReportView',
    'admin/reports/inventory/': 'InventoryReportView',
}


# ============================================================
# VIEWS (Simulated)
# ============================================================

class BaseView:
    """Base view class"""
    
    def __init__(self, app: AmazonClone):
        self.app = app
    
    def get(self, request: dict) -> dict:
        return {'status': 200, 'data': {}}
    
    def post(self, request: dict) -> dict:
        return {'status': 200, 'data': {}}


class HomeView(BaseView):
    """Home page view"""
    
    def get(self, request: dict) -> dict:
        featured_products = self.app.product_service.get_featured_products()
        categories = self.app.category_service.get_root_categories()
        
        return {
            'status': 200,
            'template': 'home.html',
            'data': {
                'featured_products': featured_products,
                'categories': categories,
                'title': 'Amazon Clone - Online Shopping'
            }
        }


class ProductListView(BaseView):
    """Product listing view"""
    
    def get(self, request: dict) -> dict:
        query = request.get('query', '')
        category_id = request.get('category_id')
        min_price = request.get('min_price')
        max_price = request.get('max_price')
        sort_by = request.get('sort_by', 'name')
        
        products = self.app.search_products(
            query=query,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by
        )
        
        return {
            'status': 200,
            'template': 'products/list.html',
            'data': {
                'products': products,
                'query': query,
                'total_count': len(products)
            }
        }


class ProductDetailView(BaseView):
    """Product detail view"""
    
    def get(self, request: dict) -> dict:
        product_id = request.get('product_id')
        detail = self.app.get_product_detail(product_id)
        
        if not detail:
            return {'status': 404, 'message': 'Product not found'}
        
        return {
            'status': 200,
            'template': 'products/detail.html',
            'data': detail
        }


class CartView(BaseView):
    """Shopping cart view"""
    
    def get(self, request: dict) -> dict:
        user_id = request.get('user_id')
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        
        return {
            'status': 200,
            'template': 'cart/cart.html',
            'data': {
                'cart': cart,
                'subtotal': cart.subtotal,
                'total': cart.total,
                'item_count': cart.item_count
            }
        }
    
    def post(self, request: dict) -> dict:
        action = request.get('action')
        user_id = request.get('user_id')
        product_id = request.get('product_id')
        quantity = request.get('quantity', 1)
        
        if action == 'add':
            result = self.app.add_to_cart(user_id, product_id, quantity)
            return {'status': 200 if result['success'] else 400, 'data': result}
        
        elif action == 'remove':
            cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
            cart.remove_item(product_id)
            return {'status': 200, 'data': {'message': 'Item removed'}}
        
        elif action == 'update':
            cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
            cart.update_quantity(product_id, quantity)
            return {'status': 200, 'data': {'message': 'Cart updated'}}
        
        return {'status': 400, 'data': {'message': 'Invalid action'}}


class CheckoutView(BaseView):
    """Checkout view"""
    
    def get(self, request: dict) -> dict:
        user_id = request.get('user_id')
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        addresses = self.app.order_service.get_user_addresses(user_id)
        
        return {
            'status': 200,
            'template': 'checkout/checkout.html',
            'data': {
                'cart': cart,
                'addresses': addresses
            }
        }
    
    def post(self, request: dict) -> dict:
        user_id = request.get('user_id')
        shipping_address_id = request.get('shipping_address_id')
        payment_method = request.get('payment_method', 'card')
        coupon_code = request.get('coupon_code')
        
        result = self.app.checkout(
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            payment_method=payment_method,
            coupon_code=coupon_code
        )
        
        return {
            'status': 200 if result['success'] else 400,
            'data': result
        }


class OrderListView(BaseView):
    """Order list view"""
    
    def get(self, request: dict) -> dict:
        user_id = request.get('user_id')
        orders = self.app.order_service.get_user_orders(user_id)
        
        return {
            'status': 200,
            'template': 'orders/list.html',
            'data': {'orders': orders}
        }


class AdminDashboardView(BaseView):
    """Admin dashboard view"""
    
    def get(self, request: dict) -> dict:
        stats = self.app.get_dashboard_stats()
        
        return {
            'status': 200,
            'template': 'admin/dashboard.html',
            'data': stats
        }


class InventoryDashboardView(BaseView):
    """Inventory management dashboard"""
    
    def get(self, request: dict) -> dict:
        report = self.app.get_admin_inventory_report()
        low_stock = self.app.inventory_service.get_low_stock_items()
        warehouses = list(self.app.inventory_service.warehouses.values())
        suppliers = list(self.app.inventory_service.suppliers.values())
        pending_pos = self.app.inventory_service.get_all_purchase_orders('pending')
        
        return {
            'status': 200,
            'template': 'admin/inventory/dashboard.html',
            'data': {
                'report': report,
                'low_stock_items': low_stock,
                'warehouses': warehouses,
                'suppliers': suppliers,
                'pending_purchase_orders': pending_pos
            }
        }


class PurchaseOrderView(BaseView):
    """Purchase order management view"""
    
    def get(self, request: dict) -> dict:
        status = request.get('status')
        orders = self.app.inventory_service.get_all_purchase_orders(status)
        
        return {
            'status': 200,
            'template': 'admin/inventory/purchase_orders.html',
            'data': {'purchase_orders': orders}
        }
    
    def post(self, request: dict) -> dict:
        action = request.get('action')
        po_id = request.get('po_id')
        
        result = self.app.manage_purchase_order(action, po_id, **request)
        return {
            'status': 200 if result['success'] else 400,
            'data': result
        }


# ============================================================
# DJANGO MODELS (String representation for Django integration)
# ============================================================

DJANGO_MODELS_CODE = '''
# models.py - Django Models

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class UserProfile(models.Model):
    USER_TYPES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('supplier', 'Supplier'),
        ('warehouse_manager', 'Warehouse Manager'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, 
                                on_delete=models.SET_NULL, related_name='children')
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    payment_terms = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300)
    capacity = models.IntegerField(default=10000)
    manager = models.ForeignKey(User, null=True, blank=True, 
                                 on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.location}"


class Product(models.Model):
    name = models.CharField(max_length=300)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, 
                                  related_name='products')
    sku = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    weight = models.FloatField(default=0)
    dimensions = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='products/', blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(r.rating for r in reviews) / reviews.count()
    
    @property
    def total_stock(self):
        return sum(item.quantity for item in self.inventory_items.all())


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, 
                                 related_name='variants')
    variant_type = models.CharField(max_length=50)
    variant_value = models.CharField(max_length=100)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.variant_type}: {self.variant_value}"


class InventoryItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, 
                                 related_name='inventory_items')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                   related_name='inventory_items')
    quantity = models.IntegerField(default=0)
    reorder_point = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=100)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'warehouse')
    
    def needs_reorder(self):
        return self.quantity <= self.reorder_point
    
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, 
                                  related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, 
                                    related_name='created_purchase_orders')
    approved_by = models.ForeignKey(User, null=True, blank=True, 
                                     on_delete=models.SET_NULL,
                                     related_name='approved_purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    expected_delivery = models.DateTimeField()
    actual_delivery = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"PO-{self.order_number}"
    
    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, 
                                        related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.IntegerField(default=0)
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Address(models.Model):
    ADDRESS_TYPES = [
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_line1 = models.CharField(max_length=300)
    address_line2 = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES, 
                                     default='shipping')
    
    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.state}"


class Cart(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, 
                                 on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total(self):
        return self.subtotal - self.discount_amount
    
    def __str__(self):
        return f"Cart for {self.user or self.session_id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, 
                                 on_delete=models.SET_NULL)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def total_price(self):
        return self.price * self.quantity
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Order(models.Model):
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
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    shipping_address = models.ForeignKey(Address, on_delete=models.CASCADE, 
                                          related_name='shipping_orders')
    billing_address = models.ForeignKey(Address, on_delete=models.CASCADE, 
                                         related_name='billing_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, 
                                       default='pending')
    payment_method = models.CharField(max_length=50)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=50, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Order {self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, 
                                 on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=300)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, 
                                 related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.IntegerField(null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.code


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    name = models.CharField(max_length=200, default='My Wishlist')
    products = models.ManyToManyField(Product, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.name}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, 
                              related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, 
                                          choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
'''


# ============================================================
# DEMO / TEST RUNNER
# ============================================================

def run_demo():
    """Run a demonstration of the Amazon Clone system"""
    
    print("=" * 70)
    print("AMAZON CLONE - SYSTEM DEMONSTRATION")
    print("=" * 70)
    
    # Initialize application
    app = AmazonClone()
    print("\n✓ Application initialized with sample data")
    
    # ---- USER AUTHENTICATION ----
    print("\n" + "=" * 50)
    print("1. USER AUTHENTICATION")
    print("=" * 50)
    
    # Register new user
    reg_result = app.register_user(
        username='new_customer',
        email='new@example.com',
        password='securepass123',
        first_name='New',
        last_name='Customer'
    )
    print(f"\nRegistration: {reg_result['message']}")
    
    # Login
    login_result = app.login('john_doe', 'password123')
    print(f"Login: {login_result['message']}")
    user = login_result['user']
    print(f"Logged in as: {user.get_full_name()} ({user.user_type})")
    
    # Failed login
    failed_login = app.login('john_doe', 'wrongpassword')
    print(f"Failed login: {failed_login['message']}")
    
    # ---- PRODUCT SEARCH ----
    print("\n" + "=" * 50)
    print("2. PRODUCT SEARCH & LISTING")
    print("=" * 50)
    
    # Search all products
    all_products = app.search_products()
    print(f"\nTotal products: {len(all_products)}")
    
    # Search by query
    phone_results = app.search_products(query='iPhone')
    print(f"Search 'iPhone': {len(phone_results)} results")
    for p in phone_results:
        print(f"  - {p.name}: ${p.price}")
    
    # Search with filters
    budget_products = app.search_products(
        max_price=Decimal('100'), 
        sort_by='price_asc'
    )
    print(f"\nProducts under $100: {len(budget_products)}")
    for p in budget_products:
        print(f"  - {p.name}: ${p.price}")
    
    # ---- PRODUCT DETAIL ----
    print("\n" + "=" * 50)
    print("3. PRODUCT DETAIL VIEW")
    print("=" * 50)
    
    product_detail = app.get_product_detail(1)  # iPhone
    if product_detail:
        product = product_detail['product']
        print(f"\nProduct: {product.name}")
        print(f"Price: ${product.price}")
        print(f"Brand: {product.brand}")
        print(f"Average Rating: {product_detail['average_rating']:.1f}/5")
        print(f"Reviews: {len(product_detail['reviews'])}")
        print(f"Variants: {len(product_detail['variants'])}")
        print(f"In Stock: {product_detail['in_stock']}")
    
    # ---- SHOPPING CART ----
    print("\n" + "=" * 50)
    print("4. SHOPPING CART")
    print("=" * 50)
    
    user_id = 2  # john_doe
    
    # Add items to cart
    result1 = app.add_to_cart(user_id, 2, 1)  # Samsung
    result2 = app.add_to_cart(user_id, 4, 3)  # Python book
    result3 = app.add_to_cart(user_id, 5, 2)  # T-shirt
    
    print(f"\nAdded Samsung: {result1['message']}")
    print(f"Added Python Book (x3): {result2['message']}")
    print(f"Added T-Shirt (x2): {result3['message']}")
    
    cart = app.cart_service.get_or_create_cart(user_id=user_id)
    print(f"\nCart Summary:")
    print(f"  Items: {cart.item_count}")
    print(f"  Subtotal: ${cart.subtotal}")
    
    # Apply coupon
    coupon_result = app.cart_service.apply_coupon(cart, 'SAVE10')
    print(f"\nApply coupon SAVE10: {coupon_result['message']}")
    print(f"  Discount: ${cart.discount_amount}")
    print(f"  Total: ${cart.total}")
    
    # ---- ORDER MANAGEMENT ----
    print("\n" + "=" * 50)
    print("5. ORDER MANAGEMENT")
    print("=" * 50)
    
    # Create address
    address = app.order_service.create_address(
        user_id=user_id,
        address_line1='456 Oak Avenue',
        city='Los Angeles',
        state='CA',
        country='USA',
        postal_code='90001',
        is_default=True
    )
    print(f"\nShipping address created: {address}")
    
    # Checkout
    checkout_result = app.checkout(
        user_id=user_id,
        shipping_address_id=address.id,
        payment_method='card',
        coupon_code='SAVE10'
    )
    print(f"\nCheckout: {checkout_result['message']}")
    
    if checkout_result['success']:
        order = checkout_result['order']
        print(f"Order Number: {order.order_number}")
        print(f"Status: {order.status}")
        print(f"Payment Status: {order.payment_status}")
        print(f"Total: ${order.total_amount}")
        print(f"Items: {len(order.items)}")
    
    # View user orders
    user_orders = app.order_service.get_user_orders(user_id)
    print(f"\nUser orders: {len(user_orders)}")
    for o in user_orders:
        print(f"  - {o.order_number}: {o.status} (${o.total_amount})")
    
    # ---- INVENTORY MANAGEMENT ----
    print("\n" + "=" * 50)
    print("6. INVENTORY MANAGEMENT")
    print("=" * 50)
    
    # Inventory report
    inv_report = app.get_admin_inventory_report()
    print(f"\nInventory Report:")
    print(f"  Total Products: {inv_report['total_products']}")
    print(f"  Total Warehouses: {inv_report['total_warehouses']}")
    print(f"  Total Suppliers: {inv_report['total_suppliers']}")
    print(f"  Low Stock Items: {inv_report['low_stock_items']}")
    print(f"  Pending POs: {inv_report['pending_purchase_orders']}")
    
    print("\nWarehouse Summary:")
    for name, summary in inv_report['warehouse_summary'].items():
        print(f"  {name}:")
        print(f"    Items: {summary['total_items']}")
        print(f"    Quantity: {summary['total_quantity']}")
        print(f"    Available Space: {summary['available_space']}")
    
    # Stock management
    print("\nStock Operations:")
    
    # Add stock
    app.inventory_service.add_stock(1, 1, 50, 'Restock')
    stock = app.inventory_service.get_total_stock(1)
    print(f"  iPhone total stock after restock: {stock}")
    
    # Transfer stock
    transfer = app.inventory_service.transfer_stock(1, 1, 2, 20)
    print(f"  Stock transfer (WH1 -> WH2): {'Success' if transfer else 'Failed'}")
    
    # ---- PURCHASE ORDERS ----
    print("\n" + "=" * 50)
    print("7. PURCHASE ORDERS")
    print("=" * 50)
    
    # Create new PO
    new_po = app.inventory_service.create_purchase_order(
        supplier_id=2,
        warehouse_id=1,
        created_by=1,
        expected_delivery=datetime.now() + timedelta(days=14)
    )
    new_po.add_item(3, 100, Decimal('1500.00'), 'MacBook Pro 14"')
    new_po.add_item(4, 500, Decimal('30.00'), 'Python Programming Book')
    
    print(f"\nNew PO created: {new_po.order_number}")
    print(f"Items: {len(new_po.items)}")
    print(f"Total: ${new_po.total_amount}")
    
    # Submit and approve
    new_po.submit()
    print(f"Status after submit: {new_po.status}")
    
    new_po.approve(1)
    print(f"Status after approve: {new_po.status}")
    
    new_po.mark_ordered()
    print(f"Status after order: {new_po.status}")
    
    # Receive PO
    received = app.inventory_service.receive_purchase_order(
        new_po.id,
        {3: 100, 4: 500}
    )
    print(f"PO received: {'Success' if received else 'Failed'}")
    print(f"Status: {new_po.status}")
    
    # ---- ADMIN DASHBOARD ----
    print("\n" + "=" * 50)
    print("8. ADMIN DASHBOARD")
    print("=" * 50)
    
    stats = app.get_dashboard_stats()
    print(f"\nDashboard Statistics:")
    print(f"  Total Products: {stats['total_products']}")
    print(f"  Total Users: {stats['total_users']}")
    print(f"  Total Customers: {stats['total_customers']}")
    print(f"  Featured Products: {stats['featured_products']}")
    print(f"  Low Stock Alerts: {stats['low_stock_alerts']}")
    
    print(f"\nOrder Statistics:")
    order_stats = stats['orders']
    for key, value in order_stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # ---- WISHLIST ----
    print("\n" + "=" * 50)
    print("9. WISHLIST")
    print("=" * 50)
    
    app.wishlist_service.add_to_wishlist(user_id, 1)  # iPhone
    app.wishlist_service.add_to_wishlist(user_id, 3)  # MacBook
    app.wishlist_service.add_to_wishlist(user_id, 1)  # iPhone (duplicate)
    
    wishlist = app.wishlist_service.get_wishlist(user_id)
    print(f"\nWishlist items: {len(wishlist.items)}")
    print(f"Product IDs: {wishlist.items}")
    
    # Remove from wishlist
    app.wishlist_service.remove_from_wishlist(user_id, 3)
    print(f"After removal: {len(wishlist.items)} items")
    
    # ---- NOTIFICATIONS ----
    print("\n" + "=" * 50)
    print("10. NOTIFICATIONS")
    print("=" * 50)
    
    notifications = app.notification_service.get_user_notifications(user_id)
    unread = app.notification_service.get_unread_count(user_id)
    
    print(f"\nTotal notifications: {len(notifications)}")
    print(f"Unread: {unread}")
    
    for notif in notifications[:3]:
        print(f"  [{notif.notification_type.upper()}] {notif.title}")
        print(f"    {notif.message}")
    
    app.notification_service.mark_all_read(user_id)
    print(f"\nAfter marking all read: {app.notification_service.get_unread_count(user_id)} unread")
    
    # ---- CATEGORIES ----
    print("\n" + "=" * 50)
    print("11. CATEGORY MANAGEMENT")
    print("=" * 50)
    
    root_cats = app.category_service.get_root_categories()
    print(f"\nRoot categories: {len(root_cats)}")
    for cat in root_cats:
        subcats = app.category_service.get_subcategories(cat.id)
        print(f"  {cat.name} ({len(subcats)} subcategories)")
        for sub in subcats:
            print(f"    - {sub.name}")
    
    # ---- URL PATTERNS ----
    print("\n" + "=" * 50)
    print("12. URL PATTERNS")
    print("=" * 50)
    
    print(f"\nTotal URL patterns: {len(URL_PATTERNS)}")
    print("\nSample URLs:")
    sample_urls = list(URL_PATTERNS.items())[:10]
    for url, view in sample_urls:
        print(f"  /{url} -> {view}")
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nSystem Components:")
    print("  ✓ User Authentication (Register, Login, Logout)")
    print("  ✓ Product Listing and Search")
    print("  ✓ Product Detail View with Reviews")
    print("  ✓ Shopping Cart with Coupon Support")
    print("  ✓ Checkout and Order Processing")
    print("  ✓ Order Management (Sales Orders)")
    print("  ✓ Purchase Order Management")
    print("  ✓ Inventory Management System")
    print("  ✓ Warehouse Management")
    print("  ✓ Supplier Management")
    print("  ✓ User Management (Multi-level)")
    print("  ✓ Wishlist")
    print("  ✓ Notifications")
    print("  ✓ Category Management")
    print("  ✓ Admin Dashboard")
    print("  ✓ Django Models (Code Generated)")
    print("  ✓ URL Patterns Defined")
    
    return app


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == '__main__':
    app = run_demo()
    
    print("\n" + "=" * 70)
    print("DJANGO MODELS CODE PREVIEW")
    print("=" * 70)
    print("\nThe following Django models code has been generated:")
    print("(First 50 lines shown)")
    lines = DJANGO_MODELS_CODE.strip().split('\n')
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3}: {line}")
    print(f"... ({len(lines) - 50} more lines)")
    
    print("\n" + "=" * 70)
    print("APPLICATION READY")
    print("=" * 70)
    print("\nTo integrate with Django:")
    print("1. Copy the DJANGO_MODELS_CODE to your models.py")
    print("2. Configure settings.py with DJANGO_SETTINGS")
    print("3. Create views using the View classes as templates")
    print("4. Configure urls.py using URL_PATTERNS")
    print("5. Run: python manage.py makemigrations && python manage.py migrate")
    print("6. Run: python manage.py runserver")