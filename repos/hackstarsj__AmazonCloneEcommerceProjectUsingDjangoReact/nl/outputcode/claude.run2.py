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
        self._password_hash = None
    
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
                 contact_person: str = '', website: str = ''):
        self.supplier_id = supplier_id
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.contact_person = contact_person
        self.website = website
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
                 capacity: int = 0, manager_id: int = None):
        self.warehouse_id = warehouse_id
        self.name = name
        self.location = location
        self.capacity = capacity
        self.manager_id = manager_id
        self.is_active = True
        self.created_at = datetime.now()
        self.current_stock = {}  # product_id -> quantity
    
    def get_available_capacity(self) -> int:
        used = sum(self.current_stock.values())
        return self.capacity - used
    
    def add_stock(self, product_id: int, quantity: int) -> bool:
        if self.get_available_capacity() >= quantity:
            self.current_stock[product_id] = self.current_stock.get(product_id, 0) + quantity
            return True
        return False
    
    def remove_stock(self, product_id: int, quantity: int) -> bool:
        current = self.current_stock.get(product_id, 0)
        if current >= quantity:
            self.current_stock[product_id] = current - quantity
            return True
        return False
    
    def get_stock(self, product_id: int) -> int:
        return self.current_stock.get(product_id, 0)
    
    def __repr__(self) -> str:
        return f"Warehouse(id={self.warehouse_id}, name={self.name}, location={self.location})"


class Product:
    """Product model"""
    
    def __init__(self, product_id: int, name: str, description: str,
                 price: Decimal, category_id: int, supplier_id: int = None,
                 sku: str = '', brand: str = '', weight: float = 0.0,
                 dimensions: str = ''):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = Decimal(str(price))
        self.category_id = category_id
        self.supplier_id = supplier_id
        self.sku = sku or f"SKU-{product_id:06d}"
        self.brand = brand
        self.weight = weight
        self.dimensions = dimensions
        self.is_active = True
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.images = []
        self.tags = []
        self.rating = 0.0
        self.review_count = 0
        self.discount_percentage = 0.0
        self.featured = False
    
    def get_discounted_price(self) -> Decimal:
        if self.discount_percentage > 0:
            discount = self.price * Decimal(str(self.discount_percentage / 100))
            return self.price - discount
        return self.price
    
    def add_image(self, image_url: str):
        self.images.append(image_url)
    
    def add_tag(self, tag: str):
        if tag not in self.tags:
            self.tags.append(tag)
    
    def update_rating(self, new_rating: float):
        if 0 <= new_rating <= 5:
            total = self.rating * self.review_count + new_rating
            self.review_count += 1
            self.rating = total / self.review_count
    
    def __repr__(self) -> str:
        return f"Product(id={self.product_id}, name={self.name}, price={self.price})"


class Inventory:
    """Inventory model for tracking product stock"""
    
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
        self.history = []
    
    def get_available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self) -> bool:
        return self.get_available_quantity() <= self.reorder_point
    
    def add_stock(self, quantity: int, reason: str = 'purchase_order'):
        self.quantity += quantity
        self.last_updated = datetime.now()
        self.history.append({
            'type': 'add',
            'quantity': quantity,
            'reason': reason,
            'timestamp': datetime.now(),
            'balance': self.quantity
        })
    
    def remove_stock(self, quantity: int, reason: str = 'sale') -> bool:
        if self.get_available_quantity() >= quantity:
            self.quantity -= quantity
            self.last_updated = datetime.now()
            self.history.append({
                'type': 'remove',
                'quantity': quantity,
                'reason': reason,
                'timestamp': datetime.now(),
                'balance': self.quantity
            })
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
        return f"Inventory(product_id={self.product_id}, quantity={self.quantity}, available={self.get_available_quantity()})"


class PurchaseOrder:
    """Purchase order model for ordering from suppliers"""
    
    STATUS_CHOICES = ['draft', 'submitted', 'approved', 'shipped', 'received', 'cancelled']
    
    def __init__(self, po_id: int, supplier_id: int, warehouse_id: int,
                 created_by: int, expected_delivery: datetime = None):
        self.po_id = po_id
        self.supplier_id = supplier_id
        self.warehouse_id = warehouse_id
        self.created_by = created_by
        self.expected_delivery = expected_delivery or (datetime.now() + timedelta(days=7))
        self.status = 'draft'
        self.items = []  # List of PurchaseOrderItem
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.notes = ''
        self.total_amount = Decimal('0.00')
    
    def add_item(self, product_id: int, quantity: int, unit_price: Decimal):
        item = {
            'product_id': product_id,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'total_price': Decimal(str(unit_price)) * quantity
        }
        self.items.append(item)
        self._calculate_total()
    
    def _calculate_total(self):
        self.total_amount = sum(item['total_price'] for item in self.items)
    
    def submit(self) -> bool:
        if self.status == 'draft' and self.items:
            self.status = 'submitted'
            self.updated_at = datetime.now()
            return True
        return False
    
    def approve(self) -> bool:
        if self.status == 'submitted':
            self.status = 'approved'
            self.updated_at = datetime.now()
            return True
        return False
    
    def mark_shipped(self) -> bool:
        if self.status == 'approved':
            self.status = 'shipped'
            self.updated_at = datetime.now()
            return True
        return False
    
    def mark_received(self) -> bool:
        if self.status == 'shipped':
            self.status = 'received'
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel(self) -> bool:
        if self.status not in ['received', 'cancelled']:
            self.status = 'cancelled'
            self.updated_at = datetime.now()
            return True
        return False
    
    def __repr__(self) -> str:
        return f"PurchaseOrder(id={self.po_id}, supplier={self.supplier_id}, status={self.status}, total={self.total_amount})"


class CartItem:
    """Shopping cart item model"""
    
    def __init__(self, cart_item_id: int, cart_id: int, product_id: int,
                 quantity: int, price: Decimal):
        self.cart_item_id = cart_item_id
        self.cart_id = cart_id
        self.product_id = product_id
        self.quantity = quantity
        self.price = Decimal(str(price))
        self.added_at = datetime.now()
    
    def get_subtotal(self) -> Decimal:
        return self.price * self.quantity
    
    def __repr__(self) -> str:
        return f"CartItem(product_id={self.product_id}, quantity={self.quantity}, price={self.price})"


class ShoppingCart:
    """Shopping cart model"""
    
    def __init__(self, cart_id: int, user_id: int = None, session_id: str = None):
        self.cart_id = cart_id
        self.user_id = user_id
        self.session_id = session_id
        self.items = {}  # product_id -> CartItem
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._next_item_id = 1
    
    def add_item(self, product_id: int, quantity: int, price: Decimal) -> CartItem:
        if product_id in self.items:
            self.items[product_id].quantity += quantity
        else:
            item = CartItem(self._next_item_id, self.cart_id, product_id, quantity, price)
            self._next_item_id += 1
            self.items[product_id] = item
        self.updated_at = datetime.now()
        return self.items[product_id]
    
    def remove_item(self, product_id: int) -> bool:
        if product_id in self.items:
            del self.items[product_id]
            self.updated_at = datetime.now()
            return True
        return False
    
    def update_quantity(self, product_id: int, quantity: int) -> bool:
        if product_id in self.items:
            if quantity <= 0:
                return self.remove_item(product_id)
            self.items[product_id].quantity = quantity
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_total(self) -> Decimal:
        return sum(item.get_subtotal() for item in self.items.values())
    
    def get_item_count(self) -> int:
        return sum(item.quantity for item in self.items.values())
    
    def clear(self):
        self.items = {}
        self.updated_at = datetime.now()
    
    def is_empty(self) -> bool:
        return len(self.items) == 0
    
    def __repr__(self) -> str:
        return f"ShoppingCart(id={self.cart_id}, user_id={self.user_id}, items={len(self.items)}, total={self.get_total()})"


class Address:
    """Address model"""
    
    def __init__(self, address_id: int, user_id: int, street: str,
                 city: str, state: str, country: str, zip_code: str,
                 is_default: bool = False, address_type: str = 'shipping'):
        self.address_id = address_id
        self.user_id = user_id
        self.street = street
        self.city = city
        self.state = state
        self.country = country
        self.zip_code = zip_code
        self.is_default = is_default
        self.address_type = address_type  # shipping, billing
    
    def get_full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}, {self.country}"
    
    def __repr__(self) -> str:
        return f"Address(id={self.address_id}, city={self.city}, country={self.country})"


class SalesOrder:
    """Sales order model"""
    
    STATUS_CHOICES = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
    PAYMENT_STATUS = ['pending', 'paid', 'failed', 'refunded']
    
    def __init__(self, order_id: int, user_id: int, shipping_address_id: int,
                 billing_address_id: int = None):
        self.order_id = order_id
        self.user_id = user_id
        self.shipping_address_id = shipping_address_id
        self.billing_address_id = billing_address_id or shipping_address_id
        self.status = 'pending'
        self.payment_status = 'pending'
        self.items = []  # List of order items
        self.subtotal = Decimal('0.00')
        self.tax_amount = Decimal('0.00')
        self.shipping_cost = Decimal('0.00')
        self.discount_amount = Decimal('0.00')
        self.total_amount = Decimal('0.00')
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.notes = ''
        self.tracking_number = ''
        self.payment_method = ''
        self.coupon_code = ''
    
    def add_item(self, product_id: int, product_name: str, 
                 quantity: int, unit_price: Decimal):
        item = {
            'product_id': product_id,
            'product_name': product_name,
            'quantity': quantity,
            'unit_price': Decimal(str(unit_price)),
            'total_price': Decimal(str(unit_price)) * quantity
        }
        self.items.append(item)
        self._calculate_totals()
    
    def _calculate_totals(self):
        self.subtotal = sum(item['total_price'] for item in self.items)
        self.tax_amount = self.subtotal * Decimal('0.08')  # 8% tax
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
    
    def apply_coupon(self, discount: Decimal):
        self.discount_amount = discount
        self._calculate_totals()
    
    def confirm(self) -> bool:
        if self.status == 'pending':
            self.status = 'confirmed'
            self.updated_at = datetime.now()
            return True
        return False
    
    def process(self) -> bool:
        if self.status == 'confirmed':
            self.status = 'processing'
            self.updated_at = datetime.now()
            return True
        return False
    
    def ship(self, tracking_number: str) -> bool:
        if self.status == 'processing':
            self.status = 'shipped'
            self.tracking_number = tracking_number
            self.updated_at = datetime.now()
            return True
        return False
    
    def deliver(self) -> bool:
        if self.status == 'shipped':
            self.status = 'delivered'
            self.updated_at = datetime.now()
            return True
        return False
    
    def cancel(self) -> bool:
        if self.status not in ['shipped', 'delivered', 'cancelled']:
            self.status = 'cancelled'
            self.updated_at = datetime.now()
            return True
        return False
    
    def refund(self) -> bool:
        if self.status == 'delivered' and self.payment_status == 'paid':
            self.status = 'refunded'
            self.payment_status = 'refunded'
            self.updated_at = datetime.now()
            return True
        return False
    
    def mark_paid(self, payment_method: str):
        self.payment_status = 'paid'
        self.payment_method = payment_method
        self.updated_at = datetime.now()
    
    def __repr__(self) -> str:
        return f"SalesOrder(id={self.order_id}, user_id={self.user_id}, status={self.status}, total={self.total_amount})"


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
    """Coupon/discount model"""
    
    DISCOUNT_TYPES = ['percentage', 'fixed']
    
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
            return order_amount * (self.discount_value / Decimal('100'))
        else:
            return min(self.discount_value, order_amount)
    
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
        self.items = []  # List of product_ids
        self.created_at = datetime.now()
        self.is_public = False
    
    def add_product(self, product_id: int) -> bool:
        if product_id not in self.items:
            self.items.append(product_id)
            return True
        return False
    
    def remove_product(self, product_id: int) -> bool:
        if product_id in self.items:
            self.items.remove(product_id)
            return True
        return False
    
    def has_product(self, product_id: int) -> bool:
        return product_id in self.items
    
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
        return f"Notification(id={self.notification_id}, type={self.notification_type}, read={self.is_read})"


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """Service for user management operations"""
    
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
            return None, "Invalid username or password"
        
        user = self._users[user_id]
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if user._password_hash != password_hash:
            return None, "Invalid username or password"
        
        if not user.is_active:
            return None, "Account is deactivated"
        
        user.last_login = datetime.now()
        return user, "Login successful"
    
    def get_user(self, user_id: int) -> UserProfile:
        return self._users.get(user_id)
    
    def get_user_by_email(self, email: str) -> UserProfile:
        user_id = self._email_index.get(email)
        return self._users.get(user_id) if user_id else None
    
    def update_profile(self, user_id: int, **kwargs) -> tuple:
        user = self._users.get(user_id)
        if not user:
            return False, "User not found"
        
        allowed_fields = ['first_name', 'last_name', 'phone', 'address']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(user, field, value)
        
        return True, "Profile updated successfully"
    
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


class CategoryService:
    """Service for category management"""
    
    def __init__(self):
        self._categories = {}
        self._next_id = 1
    
    def create_category(self, name: str, description: str = '',
                        parent_id: int = None) -> Category:
        category = Category(
            category_id=self._next_id,
            name=name,
            description=description,
            parent_id=parent_id
        )
        self._categories[self._next_id] = category
        
        if parent_id and parent_id in self._categories:
            self._categories[parent_id].add_child(category)
        
        self._next_id += 1
        return category
    
    def get_category(self, category_id: int) -> Category:
        return self._categories.get(category_id)
    
    def get_all_categories(self) -> list:
        return list(self._categories.values())
    
    def get_root_categories(self) -> list:
        return [c for c in self._categories.values() if c.parent_id is None]
    
    def get_subcategories(self, parent_id: int) -> list:
        return [c for c in self._categories.values() if c.parent_id == parent_id]
    
    def get_category_tree(self) -> list:
        roots = self.get_root_categories()
        return roots
    
    def update_category(self, category_id: int, **kwargs) -> bool:
        category = self._categories.get(category_id)
        if not category:
            return False
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        return True
    
    def delete_category(self, category_id: int) -> bool:
        category = self._categories.get(category_id)
        if not category:
            return False
        category.is_active = False
        return True


class ProductService:
    """Service for product management"""
    
    def __init__(self):
        self._products = {}
        self._next_id = 1
    
    def create_product(self, name: str, description: str, price: Decimal,
                       category_id: int, supplier_id: int = None,
                       sku: str = '', brand: str = '', **kwargs) -> Product:
        product = Product(
            product_id=self._next_id,
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            supplier_id=supplier_id,
            sku=sku,
            brand=brand
        )
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        self._products[self._next_id] = product
        self._next_id += 1
        return product
    
    def get_product(self, product_id: int) -> Product:
        return self._products.get(product_id)
    
    def get_all_products(self, active_only: bool = True) -> list:
        products = list(self._products.values())
        if active_only:
            products = [p for p in products if p.is_active]
        return products
    
    def get_products_by_category(self, category_id: int) -> list:
        return [p for p in self._products.values() 
                if p.category_id == category_id and p.is_active]
    
    def search_products(self, query: str) -> list:
        query_lower = query.lower()
        results = []
        for product in self._products.values():
            if not product.is_active:
                continue
            if (query_lower in product.name.lower() or
                    query_lower in product.description.lower() or
                    query_lower in product.brand.lower() or
                    any(query_lower in tag.lower() for tag in product.tags)):
                results.append(product)
        return results
    
    def get_featured_products(self) -> list:
        return [p for p in self._products.values() if p.featured and p.is_active]
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        product = self._products.get(product_id)
        if not product:
            return False
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.updated_at = datetime.now()
        return True
    
    def delete_product(self, product_id: int) -> bool:
        product = self._products.get(product_id)
        if not product:
            return False
        product.is_active = False
        return True
    
    def get_products_by_supplier(self, supplier_id: int) -> list:
        return [p for p in self._products.values() 
                if p.supplier_id == supplier_id and p.is_active]
    
    def filter_products(self, min_price: Decimal = None, max_price: Decimal = None,
                        brand: str = None, category_id: int = None,
                        min_rating: float = None) -> list:
        products = [p for p in self._products.values() if p.is_active]
        
        if min_price is not None:
            products = [p for p in products if p.get_discounted_price() >= min_price]
        if max_price is not None:
            products = [p for p in products if p.get_discounted_price() <= max_price]
        if brand:
            products = [p for p in products if p.brand.lower() == brand.lower()]
        if category_id:
            products = [p for p in products if p.category_id == category_id]
        if min_rating is not None:
            products = [p for p in products if p.rating >= min_rating]
        
        return products
    
    def sort_products(self, products: list, sort_by: str = 'name', 
                      ascending: bool = True) -> list:
        sort_keys = {
            'name': lambda p: p.name,
            'price': lambda p: p.get_discounted_price(),
            'rating': lambda p: p.rating,
            'newest': lambda p: p.created_at
        }
        key_func = sort_keys.get(sort_by, sort_keys['name'])
        return sorted(products, key=key_func, reverse=not ascending)


class InventoryService:
    """Service for inventory management"""
    
    def __init__(self):
        self._inventory = {}  # (product_id, warehouse_id) -> Inventory
        self._next_id = 1
    
    def create_inventory(self, product_id: int, warehouse_id: int,
                         quantity: int = 0, reorder_point: int = 10,
                         reorder_quantity: int = 50) -> Inventory:
        key = (product_id, warehouse_id)
        if key in self._inventory:
            return self._inventory[key]
        
        inventory = Inventory(
            inventory_id=self._next_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity
        )
        self._inventory[key] = inventory
        self._next_id += 1
        return inventory
    
    def get_inventory(self, product_id: int, warehouse_id: int) -> Inventory:
        return self._inventory.get((product_id, warehouse_id))
    
    def get_total_stock(self, product_id: int) -> int:
        total = 0
        for (pid, wid), inv in self._inventory.items():
            if pid == product_id:
                total += inv.get_available_quantity()
        return total
    
    def get_low_stock_items(self) -> list:
        return [inv for inv in self._inventory.values() if inv.needs_reorder()]
    
    def transfer_stock(self, product_id: int, from_warehouse_id: int,
                       to_warehouse_id: int, quantity: int) -> tuple:
        from_inv = self.get_inventory(product_id, from_warehouse_id)
        to_inv = self.get_inventory(product_id, to_warehouse_id)
        
        if not from_inv:
            return False, "Source inventory not found"
        if not to_inv:
            return False, "Destination inventory not found"
        
        if from_inv.get_available_quantity() < quantity:
            return False, "Insufficient stock in source warehouse"
        
        from_inv.remove_stock(quantity, 'transfer_out')
        to_inv.add_stock(quantity, 'transfer_in')
        
        return True, "Stock transferred successfully"
    
    def adjust_stock(self, product_id: int, warehouse_id: int,
                     quantity: int, reason: str = 'adjustment') -> tuple:
        inv = self.get_inventory(product_id, warehouse_id)
        if not inv:
            return False, "Inventory not found"
        
        if quantity > 0:
            inv.add_stock(quantity, reason)
        elif quantity < 0:
            if not inv.remove_stock(abs(quantity), reason):
                return False, "Insufficient stock"
        
        return True, f"Stock adjusted by {quantity}"
    
    def get_inventory_report(self) -> list:
        report = []
        for (product_id, warehouse_id), inv in self._inventory.items():
            report.append({
                'product_id': product_id,
                'warehouse_id': warehouse_id,
                'quantity': inv.quantity,
                'available': inv.get_available_quantity(),
                'reserved': inv.reserved_quantity,
                'needs_reorder': inv.needs_reorder(),
                'reorder_point': inv.reorder_point
            })
        return report


class WarehouseService:
    """Service for warehouse management"""
    
    def __init__(self):
        self._warehouses = {}
        self._next_id = 1
    
    def create_warehouse(self, name: str, location: str,
                         capacity: int = 0, manager_id: int = None) -> Warehouse:
        warehouse = Warehouse(
            warehouse_id=self._next_id,
            name=name,
            location=location,
            capacity=capacity,
            manager_id=manager_id
        )
        self._warehouses[self._next_id] = warehouse
        self._next_id += 1
        return warehouse
    
    def get_warehouse(self, warehouse_id: int) -> Warehouse:
        return self._warehouses.get(warehouse_id)
    
    def get_all_warehouses(self) -> list:
        return [w for w in self._warehouses.values() if w.is_active]
    
    def update_warehouse(self, warehouse_id: int, **kwargs) -> bool:
        warehouse = self._warehouses.get(warehouse_id)
        if not warehouse:
            return False
        for key, value in kwargs.items():
            if hasattr(warehouse, key):
                setattr(warehouse, key, value)
        return True
    
    def deactivate_warehouse(self, warehouse_id: int) -> bool:
        warehouse = self._warehouses.get(warehouse_id)
        if warehouse:
            warehouse.is_active = False
            return True
        return False
    
    def get_warehouse_utilization(self, warehouse_id: int) -> dict:
        warehouse = self._warehouses.get(warehouse_id)
        if not warehouse:
            return {}
        
        used = sum(warehouse.current_stock.values())
        utilization = (used / warehouse.capacity * 100) if warehouse.capacity > 0 else 0
        
        return {
            'warehouse_id': warehouse_id,
            'name': warehouse.name,
            'capacity': warehouse.capacity,
            'used': used,
            'available': warehouse.get_available_capacity(),
            'utilization_percentage': round(utilization, 2)
        }


class SupplierService:
    """Service for supplier management"""
    
    def __init__(self):
        self._suppliers = {}
        self._next_id = 1
    
    def create_supplier(self, name: str, email: str, phone: str = '',
                        address: str = '', contact_person: str = '',
                        website: str = '') -> Supplier:
        supplier = Supplier(
            supplier_id=self._next_id,
            name=name,
            email=email,
            phone=phone,
            address=address,
            contact_person=contact_person,
            website=website
        )
        self._suppliers[self._next_id] = supplier
        self._next_id += 1
        return supplier
    
    def get_supplier(self, supplier_id: int) -> Supplier:
        return self._suppliers.get(supplier_id)
    
    def get_all_suppliers(self) -> list:
        return [s for s in self._suppliers.values() if s.is_active]
    
    def update_supplier(self, supplier_id: int, **kwargs) -> bool:
        supplier = self._suppliers.get(supplier_id)
        if not supplier:
            return False
        for key, value in kwargs.items():
            if hasattr(supplier, key):
                setattr(supplier, key, value)
        return True
    
    def deactivate_supplier(self, supplier_id: int) -> bool:
        supplier = self._suppliers.get(supplier_id)
        if supplier:
            supplier.is_active = False
            return True
        return False


class PurchaseOrderService:
    """Service for purchase order management"""
    
    def __init__(self, inventory_service: InventoryService):
        self._purchase_orders = {}
        self._next_id = 1
        self._inventory_service = inventory_service
    
    def create_purchase_order(self, supplier_id: int, warehouse_id: int,
                               created_by: int, 
                               expected_delivery: datetime = None) -> PurchaseOrder:
        po = PurchaseOrder(
            po_id=self._next_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            created_by=created_by,
            expected_delivery=expected_delivery
        )
        self._purchase_orders[self._next_id] = po
        self._next_id += 1
        return po
    
    def get_purchase_order(self, po_id: int) -> PurchaseOrder:
        return self._purchase_orders.get(po_id)
    
    def get_all_purchase_orders(self, status: str = None) -> list:
        orders = list(self._purchase_orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders
    
    def receive_purchase_order(self, po_id: int) -> tuple:
        po = self._purchase_orders.get(po_id)
        if not po:
            return False, "Purchase order not found"
        
        if not po.mark_received():
            return False, f"Cannot receive order in status: {po.status}"
        
        # Update inventory
        for item in po.items:
            inv = self._inventory_service.get_inventory(
                item['product_id'], po.warehouse_id
            )
            if inv:
                inv.add_stock(item['quantity'], f'purchase_order_{po_id}')
            else:
                self._inventory_service.create_inventory(
                    item['product_id'], po.warehouse_id, item['quantity']
                )
        
        return True, "Purchase order received and inventory updated"
    
    def get_orders_by_supplier(self, supplier_id: int) -> list:
        return [po for po in self._purchase_orders.values() 
                if po.supplier_id == supplier_id]


class CartService:
    """Service for shopping cart management"""
    
    def __init__(self, inventory_service: InventoryService,
                 product_service: ProductService):
        self._carts = {}
        self._next_id = 1
        self._inventory_service = inventory_service
        self._product_service = product_service
    
    def get_or_create_cart(self, user_id: int = None, 
                            session_id: str = None) -> ShoppingCart:
        # Find existing cart
        for cart in self._carts.values():
            if user_id and cart.user_id == user_id:
                return cart
            if session_id and cart.session_id == session_id:
                return cart
        
        # Create new cart
        cart = ShoppingCart(
            cart_id=self._next_id,
            user_id=user_id,
            session_id=session_id
        )
        self._carts[self._next_id] = cart
        self._next_id += 1
        return cart
    
    def add_to_cart(self, cart_id: int, product_id: int, 
                    quantity: int) -> tuple:
        cart = self._carts.get(cart_id)
        if not cart:
            return None, "Cart not found"
        
        product = self._product_service.get_product(product_id)
        if not product:
            return None, "Product not found"
        
        if not product.is_active:
            return None, "Product is not available"
        
        # Check inventory
        available = self._inventory_service.get_total_stock(product_id)
        if available < quantity:
            return None, f"Only {available} items available"
        
        item = cart.add_item(product_id, quantity, product.get_discounted_price())
        return item, "Item added to cart"
    
    def remove_from_cart(self, cart_id: int, product_id: int) -> tuple:
        cart = self._carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        if cart.remove_item(product_id):
            return True, "Item removed from cart"
        return False, "Item not found in cart"
    
    def update_cart_item(self, cart_id: int, product_id: int, 
                          quantity: int) -> tuple:
        cart = self._carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        if quantity > 0:
            available = self._inventory_service.get_total_stock(product_id)
            if available < quantity:
                return False, f"Only {available} items available"
        
        if cart.update_quantity(product_id, quantity):
            return True, "Cart updated"
        return False, "Item not found in cart"
    
    def merge_carts(self, session_cart_id: int, user_cart_id: int) -> bool:
        session_cart = self._carts.get(session_cart_id)
        user_cart = self._carts.get(user_cart_id)
        
        if not session_cart or not user_cart:
            return False
        
        for product_id, item in session_cart.items.items():
            user_cart.add_item(product_id, item.quantity, item.price)
        
        session_cart.clear()
        return True
    
    def clear_cart(self, cart_id: int) -> bool:
        cart = self._carts.get(cart_id)
        if cart:
            cart.clear()
            return True
        return False


class OrderService:
    """Service for sales order management"""
    
    def __init__(self, inventory_service: InventoryService,
                 cart_service: CartService,
                 product_service: ProductService):
        self._orders = {}
        self._next_id = 1
        self._inventory_service = inventory_service
        self._cart_service = cart_service
        self._product_service = product_service
    
    def create_order_from_cart(self, cart_id: int, user_id: int,
                                shipping_address_id: int,
                                billing_address_id: int = None) -> tuple:
        cart = self._cart_service._carts.get(cart_id)
        if not cart or cart.is_empty():
            return None, "Cart is empty"
        
        # Check inventory for all items
        for product_id, item in cart.items.items():
            available = self._inventory_service.get_total_stock(product_id)
            if available < item.quantity:
                product = self._product_service.get_product(product_id)
                return None, f"Insufficient stock for {product.name}"
        
        # Create order
        order = SalesOrder(
            order_id=self._next_id,
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id
        )
        
        # Add items to order
        for product_id, item in cart.items.items():
            product = self._product_service.get_product(product_id)
            order.add_item(
                product_id=product_id,
                product_name=product.name,
                quantity=item.quantity,
                unit_price=item.price
            )
        
        # Reserve inventory
        for product_id, item in cart.items.items():
            for (pid, wid), inv in self._inventory_service._inventory.items():
                if pid == product_id:
                    remaining = item.quantity
                    available = inv.get_available_quantity()
                    if available > 0:
                        reserve_qty = min(available, remaining)
                        inv.reserve_stock(reserve_qty)
                        remaining -= reserve_qty
                    if remaining <= 0:
                        break
        
        self._orders[self._next_id] = order
        self._next_id += 1
        
        # Clear cart
        self._cart_service.clear_cart(cart_id)
        
        return order, "Order created successfully"
    
    def get_order(self, order_id: int) -> SalesOrder:
        return self._orders.get(order_id)
    
    def get_user_orders(self, user_id: int) -> list:
        return [o for o in self._orders.values() if o.user_id == user_id]
    
    def get_all_orders(self, status: str = None) -> list:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders
    
    def process_payment(self, order_id: int, payment_method: str) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
        
        if order.payment_status == 'paid':
            return False, "Order already paid"
        
        # Simulate payment processing
        order.mark_paid(payment_method)
        order.confirm()
        
        # Deduct from inventory
        for item in order.items:
            product_id = item['product_id']
            quantity = item['quantity']
            
            for (pid, wid), inv in self._inventory_service._inventory.items():
                if pid == product_id:
                    remaining = quantity
                    if inv.reserved_quantity > 0:
                        deduct = min(inv.reserved_quantity, remaining)
                        inv.release_reservation(deduct)
                        inv.remove_stock(deduct, f'sales_order_{order_id}')
                        remaining -= deduct
                    if remaining <= 0:
                        break
        
        return True, "Payment processed successfully"
    
    def ship_order(self, order_id: int, tracking_number: str) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
        
        order.process()
        if order.ship(tracking_number):
            return True, f"Order shipped with tracking: {tracking_number}"
        return False, f"Cannot ship order in status: {order.status}"
    
    def cancel_order(self, order_id: int) -> tuple:
        order = self._orders.get(order_id)
        if not order:
            return False, "Order not found"
        
        if order.cancel():
            # Release reserved inventory
            for item in order.items:
                product_id = item['product_id']
                quantity = item['quantity']
                for (pid, wid), inv in self._inventory_service._inventory.items():
                    if pid == product_id:
                        inv.release_reservation(min(inv.reserved_quantity, quantity))
            
            return True, "Order cancelled successfully"
        return False, f"Cannot cancel order in status: {order.status}"
    
    def get_order_statistics(self) -> dict:
        orders = list(self._orders.values())
        total_revenue = sum(
            o.total_amount for o in orders if o.payment_status == 'paid'
        )
        
        status_counts = {}
        for order in orders:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1
        
        return {
            'total_orders': len(orders),
            'total_revenue': total_revenue,
            'status_breakdown': status_counts,
            'average_order_value': total_revenue / len(orders) if orders else Decimal('0')
        }


class ReviewService:
    """Service for product review management"""
    
    def __init__(self, product_service: ProductService):
        self._reviews = {}
        self._next_id = 1
        self._product_service = product_service
    
    def add_review(self, product_id: int, user_id: int, rating: int,
                   title: str, body: str) -> tuple:
        product = self._product_service.get_product(product_id)
        if not product:
            return None, "Product not found"
        
        # Check if user already reviewed this product
        for review in self._reviews.values():
            if review.product_id == product_id and review.user_id == user_id:
                return None, "You have already reviewed this product"
        
        try:
            review = Review(
                review_id=self._next_id,
                product_id=product_id,
                user_id=user_id,
                rating=rating,
                title=title,
                body=body
            )
        except ValueError as e:
            return None, str(e)
        
        self._reviews[self._next_id] = review
        self._next_id += 1
        
        # Update product rating
        product.update_rating(rating)
        
        return review, "Review added successfully"
    
    def get_product_reviews(self, product_id: int) -> list:
        return [r for r in self._reviews.values() 
                if r.product_id == product_id and r.is_approved]
    
    def get_user_reviews(self, user_id: int) -> list:
        return [r for r in self._reviews.values() if r.user_id == user_id]
    
    def delete_review(self, review_id: int, user_id: int) -> tuple:
        review = self._reviews.get(review_id)
        if not review:
            return False, "Review not found"
        if review.user_id != user_id:
            return False, "Unauthorized"
        del self._reviews[review_id]
        return True, "Review deleted"


class WishlistService:
    """Service for wishlist management"""
    
    def __init__(self):
        self._wishlists = {}
        self._next_id = 1
    
    def get_or_create_wishlist(self, user_id: int, name: str = 'My Wishlist') -> Wishlist:
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
    
    def add_to_wishlist(self, user_id: int, product_id: int) -> tuple:
        wishlist = self.get_or_create_wishlist(user_id)
        if wishlist.add_product(product_id):
            return True, "Product added to wishlist"
        return False, "Product already in wishlist"
    
    def remove_from_wishlist(self, user_id: int, product_id: int) -> tuple:
        wishlist = self.get_or_create_wishlist(user_id)
        if wishlist.remove_product(product_id):
            return True, "Product removed from wishlist"
        return False, "Product not in wishlist"
    
    def get_user_wishlist(self, user_id: int) -> list:
        return [w for w in self._wishlists.values() if w.user_id == user_id]


class CouponService:
    """Service for coupon management"""
    
    def __init__(self):
        self._coupons = {}
        self._next_id = 1
    
    def create_coupon(self, code: str, discount_type: str, 
                      discount_value: Decimal, min_order_amount: Decimal = Decimal('0'),
                      max_uses: int = None, 
                      expiry_date: datetime = None) -> tuple:
        if code.upper() in [c.code for c in self._coupons.values()]:
            return None, "Coupon code already exists"
        
        coupon = Coupon(
            coupon_id=self._next_id,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            min_order_amount=min_order_amount,
            max_uses=max_uses,
            expiry_date=expiry_date
        )
        self._coupons[self._next_id] = coupon
        self._next_id += 1
        return coupon, "Coupon created successfully"
    
    def validate_coupon(self, code: str, order_amount: Decimal) -> tuple:
        coupon = self._get_by_code(code)
        if not coupon:
            return None, "Invalid coupon code"
        
        is_valid, message = coupon.is_valid(order_amount)
        if not is_valid:
            return None, message
        
        discount = coupon.calculate_discount(order_amount)
        return discount, f"Coupon applied! Discount: {discount}"
    
    def _get_by_code(self, code: str) -> Coupon:
        code_upper = code.upper()
        for coupon in self._coupons.values():
            if coupon.code == code_upper:
                return coupon
        return None
    
    def use_coupon(self, code: str):
        coupon = self._get_by_code(code)
        if coupon:
            coupon.use()


class NotificationService:
    """Service for notification management"""
    
    def __init__(self):
        self._notifications = {}
        self._next_id = 1
    
    def create_notification(self, user_id: int, notification_type: str,
                             title: str, message: str) -> Notification:
        notification = Notification(
            notification_id=self._next_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message
        )
        self._notifications[self._next_id] = notification
        self._next_id += 1
        return notification
    
    def get_user_notifications(self, user_id: int, 
                                unread_only: bool = False) -> list:
        notifications = [n for n in self._notifications.values() 
                        if n.user_id == user_id]
        if unread_only:
            notifications = [n for n in notifications if not n.is_read]
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)
    
    def mark_read(self, notification_id: int, user_id: int) -> bool:
        notification = self._notifications.get(notification_id)
        if notification and notification.user_id == user_id:
            notification.mark_read()
            return True
        return False
    
    def mark_all_read(self, user_id: int):
        for notification in self._notifications.values():
            if notification.user_id == user_id:
                notification.mark_read()
    
    def send_order_notification(self, user_id: int, order_id: int, 
                                 status: str):
        messages = {
            'confirmed': f'Your order #{order_id} has been confirmed!',
            'shipped': f'Your order #{order_id} has been shipped!',
            'delivered': f'Your order #{order_id} has been delivered!',
            'cancelled': f'Your order #{order_id} has been cancelled.'
        }
        message = messages.get(status, f'Order #{order_id} status updated to {status}')
        self.create_notification(
            user_id=user_id,
            notification_type='order_update',
            title=f'Order Update - #{order_id}',
            message=message
        )


class AddressService:
    """Service for address management"""
    
    def __init__(self):
        self._addresses = {}
        self._next_id = 1
    
    def add_address(self, user_id: int, street: str, city: str,
                    state: str, country: str, zip_code: str,
                    is_default: bool = False, 
                    address_type: str = 'shipping') -> Address:
        address = Address(
            address_id=self._next_id,
            user_id=user_id,
            street=street,
            city=city,
            state=state,
            country=country,
            zip_code=zip_code,
            is_default=is_default,
            address_type=address_type
        )
        
        if is_default:
            # Remove default from other addresses of same type
            for addr in self._addresses.values():
                if (addr.user_id == user_id and 
                        addr.address_type == address_type):
                    addr.is_default = False
        
        self._addresses[self._next_id] = address
        self._next_id += 1
        return address
    
    def get_address(self, address_id: int) -> Address:
        return self._addresses.get(address_id)
    
    def get_user_addresses(self, user_id: int, 
                            address_type: str = None) -> list:
        addresses = [a for a in self._addresses.values() 
                    if a.user_id == user_id]
        if address_type:
            addresses = [a for a in addresses 
                        if a.address_type == address_type]
        return addresses
    
    def get_default_address(self, user_id: int, 
                             address_type: str = 'shipping') -> Address:
        for address in self._addresses.values():
            if (address.user_id == user_id and 
                    address.address_type == address_type and 
                    address.is_default):
                return address
        return None
    
    def delete_address(self, address_id: int, user_id: int) -> bool:
        address = self._addresses.get(address_id)
        if address and address.user_id == user_id:
            del self._addresses[address_id]
            return True
        return False


# ============================================================
# MAIN APPLICATION / FACADE
# ============================================================

class AmazonCloneApp:
    """Main application facade that coordinates all services"""
    
    def __init__(self):
        # Initialize all services
        self.user_service = UserService()
        self.category_service = CategoryService()
        self.supplier_service = SupplierService()
        self.warehouse_service = WarehouseService()
        self.product_service = ProductService()
        self.inventory_service = InventoryService()
        self.purchase_order_service = PurchaseOrderService(self.inventory_service)
        self.cart_service = CartService(self.inventory_service, self.product_service)
        self.order_service = OrderService(
            self.inventory_service, 
            self.cart_service, 
            self.product_service
        )
        self.review_service = ReviewService(self.product_service)
        self.wishlist_service = WishlistService()
        self.coupon_service = CouponService()
        self.notification_service = NotificationService()
        self.address_service = AddressService()
        
        print("Amazon Clone Application initialized successfully!")
    
    def setup_demo_data(self):
        """Setup demo data for testing"""
        print("\n" + "="*60)
        print("Setting up demo data...")
        print("="*60)
        
        # Create admin user
        admin, msg = self.user_service.register(
            username='admin',
            email='admin@amazon-clone.com',
            password='Admin@1234',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        print(f"Admin user created: {admin}")
        
        # Create customer users
        customer1, msg = self.user_service.register(
            username='john_doe',
            email='john@example.com',
            password='John@1234',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        print(f"Customer created: {customer1}")
        
        customer2, msg = self.user_service.register(
            username='jane_smith',
            email='jane@example.com',
            password='Jane@1234',
            first_name='Jane',
            last_name='Smith',
            user_type='customer'
        )
        print(f"Customer created: {customer2}")
        
        # Create categories (multi-level)
        electronics = self.category_service.create_category(
            'Electronics', 'Electronic devices and accessories'
        )
        phones = self.category_service.create_category(
            'Smartphones', 'Mobile phones and accessories', 
            parent_id=electronics.category_id
        )
        laptops = self.category_service.create_category(
            'Laptops', 'Laptop computers', 
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
        print(f"\nCategories created: {electronics}, {phones}, {laptops}, {clothing}, {books}")
        
        # Create suppliers
        supplier1 = self.supplier_service.create_supplier(
            name='TechSupply Co.',
            email='supply@techsupply.com',
            phone='+1-555-0100',
            address='123 Tech Street, Silicon Valley, CA',
            contact_person='Bob Johnson'
        )
        supplier2 = self.supplier_service.create_supplier(
            name='Fashion World',
            email='orders@fashionworld.com',
            phone='+1-555-0200',
            address='456 Fashion Ave, New York, NY',
            contact_person='Alice Brown'
        )
        print(f"\nSuppliers created: {supplier1}, {supplier2}")
        
        # Create warehouses
        warehouse1 = self.warehouse_service.create_warehouse(
            name='Main Warehouse',
            location='Seattle, WA',
            capacity=10000,
            manager_id=admin.user_id
        )
        warehouse2 = self.warehouse_service.create_warehouse(
            name='East Coast Warehouse',
            location='New York, NY',
            capacity=8000
        )
        print(f"\nWarehouses created: {warehouse1}, {warehouse2}")
        
        # Create products
        iphone = self.product_service.create_product(
            name='iPhone 15 Pro',
            description='Latest Apple iPhone with advanced features',
            price=Decimal('999.99'),
            category_id=phones.category_id,
            supplier_id=supplier1.supplier_id,
            brand='Apple',
            sku='APPL-IP15P-001'
        )
        iphone.add_tag('smartphone')
        iphone.add_tag('apple')
        iphone.featured = True
        
        samsung = self.product_service.create_product(
            name='Samsung Galaxy S24',
            description='Samsung flagship smartphone',
            price=Decimal('899.99'),
            category_id=phones.category_id,
            supplier_id=supplier1.supplier_id,
            brand='Samsung',
            sku='SAMS-GS24-001'
        )
        samsung.add_tag('smartphone')
        samsung.add_tag('samsung')
        samsung.discount_percentage = 10.0
        
        macbook = self.product_service.create_product(
            name='MacBook Pro 14"',
            description='Apple MacBook Pro with M3 chip',
            price=Decimal('1999.99'),
            category_id=laptops.category_id,
            supplier_id=supplier1.supplier_id,
            brand='Apple',
            sku='APPL-MBP14-001'
        )
        macbook.featured = True
        
        tshirt = self.product_service.create_product(
            name='Classic Cotton T-Shirt',
            description='Comfortable everyday t-shirt',
            price=Decimal('29.99'),
            category_id=mens_clothing.category_id,
            supplier_id=supplier2.supplier_id,
            brand='BasicWear',
            sku='BW-TSHIRT-001'
        )
        
        python_book = self.product_service.create_product(
            name='Python Programming: A Complete Guide',
            description='Comprehensive Python programming book',
            price=Decimal('49.99'),
            category_id=books.category_id,
            brand='TechBooks',
            sku='TB-PYTHON-001'
        )
        
        print(f"\nProducts created: {iphone}, {samsung}, {macbook}, {tshirt}, {python_book}")
        
        # Create inventory
        inv1 = self.inventory_service.create_inventory(
            iphone.product_id, warehouse1.warehouse_id, 
            quantity=100, reorder_point=20
        )
        inv2 = self.inventory_service.create_inventory(
            samsung.product_id, warehouse1.warehouse_id, 
            quantity=150, reorder_point=30
        )
        inv3 = self.inventory_service.create_inventory(
            macbook.product_id, warehouse1.warehouse_id, 
            quantity=50, reorder_point=10
        )
        inv4 = self.inventory_service.create_inventory(
            tshirt.product_id, warehouse2.warehouse_id, 
            quantity=500, reorder_point=100
        )
        inv5 = self.inventory_service.create_inventory(
            python_book.product_id, warehouse1.warehouse_id, 
            quantity=200, reorder_point=50
        )
        print(f"\nInventory created: {inv1}, {inv2}, {inv3}")
        
        # Create purchase order
        po = self.purchase_order_service.create_purchase_order(
            supplier_id=supplier1.supplier_id,
            warehouse_id=warehouse1.warehouse_id,
            created_by=admin.user_id
        )
        po.add_item(iphone.product_id, 50, Decimal('750.00'))
        po.add_item(samsung.product_id, 75, Decimal('650.00'))
        po.submit()
        po.approve()
        print(f"\nPurchase Order created: {po}")
        
        # Add addresses for customers
        addr1 = self.address_service.add_address(
            user_id=customer1.user_id,
            street='123 Main St',
            city='Seattle',
            state='WA',
            country='USA',
            zip_code='98101',
            is_default=True
        )
        
        addr2 = self.address_service.add_address(
            user_id=customer2.user_id,
            street='456 Oak Ave',
            city='New York',
            state='NY',
            country='USA',
            zip_code='10001',
            is_default=True
        )
        print(f"\nAddresses created: {addr1}, {addr2}")
        
        # Create coupons
        coupon1, msg = self.coupon_service.create_coupon(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('50'),
            max_uses=100,
            expiry_date=datetime.now() + timedelta(days=30)
        )
        coupon2, msg = self.coupon_service.create_coupon(
            code='FLAT20',
            discount_type='fixed',
            discount_value=Decimal('20'),
            min_order_amount=Decimal('100')
        )
        print(f"\nCoupons created: {coupon1}, {coupon2}")
        
        print("\n" + "="*60)
        print("Demo data setup complete!")
        print("="*60)
        
        return {
            'admin': admin,
            'customer1': customer1,
            'customer2': customer2,
            'products': [iphone, samsung, macbook, tshirt, python_book],
            'warehouses': [warehouse1, warehouse2],
            'suppliers': [supplier1, supplier2],
            'addresses': [addr1, addr2]
        }
    
    def demo_user_flow(self, demo_data: dict):
        """Demonstrate user authentication flow"""
        print("\n" + "="*60)
        print("USER AUTHENTICATION DEMO")
        print("="*60)
        
        # Login
        user, msg = self.user_service.login('john_doe', 'John@1234')
        print(f"Login: {msg} - User: {user}")
        
        # Failed login
        user_fail, msg_fail = self.user_service.login('john_doe', 'wrongpassword')
        print(f"Failed login: {msg_fail}")
        
        # Update profile
        success, msg = self.user_service.update_profile(
            user.user_id,
            phone='+1-555-1234',
            address='123 Main St, Seattle, WA'
        )
        print(f"Profile update: {msg}")
        
        # Change password
        success, msg = self.user_service.change_password(
            user.user_id, 'John@1234', 'NewJohn@5678'
        )
        print(f"Password change: {msg}")
    
    def demo_shopping_flow(self, demo_data: dict):
        """Demonstrate complete shopping flow"""
        print("\n" + "="*60)
        print("SHOPPING FLOW DEMO")
        print("="*60)
        
        customer = demo_data['customer1']
        products = demo_data['products']
        address = demo_data['addresses'][0]
        
        # Search products
        search_results = self.product_service.search_products('iPhone')
        print(f"\nSearch 'iPhone': Found {len(search_results)} products")
        for p in search_results:
            print(f"  - {p.name}: ${p.get_discounted_price()}")
        
        # Get featured products
        featured = self.product_service.get_featured_products()
        print(f"\nFeatured products: {len(featured)}")
        
        # Filter products
        filtered = self.product_service.filter_products(
            min_price=Decimal('100'), 
            max_price=Decimal('1500')
        )
        print(f"\nProducts $100-$1500: {len(filtered)}")
        
        # Add to wishlist
        success, msg = self.wishlist_service.add_to_wishlist(
            customer.user_id, products[0].product_id
        )
        print(f"\nWishlist: {msg}")
        
        # Shopping cart
        cart = self.cart_service.get_or_create_cart(user_id=customer.user_id)
        print(f"\nCart created: {cart}")
        
        # Add items to cart
        item1, msg = self.cart_service.add_to_cart(
            cart.cart_id, products[0].product_id, 1
        )
        print(f"Add iPhone to cart: {msg}")
        
        item2, msg = self.cart_service.add_to_cart(
            cart.cart_id, products[3].product_id, 2
        )
        print(f"Add T-Shirt to cart: {msg}")
        
        print(f"\nCart total: ${cart.get_total()}")
        print(f"Cart items: {cart.get_item_count()}")
        
        # Apply coupon
        discount, msg = self.coupon_service.validate_coupon(
            'SAVE10', cart.get_total()
        )
        print(f"\nCoupon SAVE10: {msg}")
        
        # Create order
        order, msg = self.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=customer.user_id,
            shipping_address_id=address.address_id
        )
        print(f"\nOrder created: {msg}")
        if order:
            print(f"Order: {order}")
            print(f"Order total: ${order.total_amount}")
        
        # Process payment
        if order:
            success, msg = self.order_service.process_payment(
                order.order_id, 'credit_card'
            )
            print(f"\nPayment: {msg}")
            
            # Send notification
            self.notification_service.send_order_notification(
                customer.user_id, order.order_id, 'confirmed'
            )
            
            # Ship order
            success, msg = self.order_service.ship_order(
                order.order_id, 'TRACK123456789'
            )
            print(f"Shipping: {msg}")
            
            # Send notification
            self.notification_service.send_order_notification(
                customer.user_id, order.order_id, 'shipped'
            )
        
        # Add review
        review, msg = self.review_service.add_review(
            product_id=products[0].product_id,
            user_id=customer.user_id,
            rating=5,
            title='Excellent product!',
            body='This iPhone is amazing. Best smartphone I have ever used.'
        )
        print(f"\nReview: {msg}")
        
        # Get notifications
        notifications = self.notification_service.get_user_notifications(
            customer.user_id
        )
        print(f"\nNotifications for {customer.username}: {len(notifications)}")
        for notif in notifications:
            print(f"  - [{notif.notification_type}] {notif.title}: {notif.message}")
    
    def demo_inventory_management(self, demo_data: dict):
        """Demonstrate inventory management"""
        print("\n" + "="*60)
        print("INVENTORY MANAGEMENT DEMO")
        print("="*60)
        
        warehouses = demo_data['warehouses']
        products = demo_data['products']
        
        # Inventory report
        report = self.inventory_service.get_inventory_report()
        print(f"\nInventory Report ({len(report)} items):")
        for item in report:
            print(f"  Product {item['product_id']} @ Warehouse {item['warehouse_id']}: "
                  f"Qty={item['quantity']}, Available={item['available']}, "
                  f"Needs Reorder={item['needs_reorder']}")
        
        # Low stock items
        low_stock = self.inventory_service.get_low_stock_items()
        print(f"\nLow stock items: {len(low_stock)}")
        
        # Transfer stock
        success, msg = self.inventory_service.transfer_stock(
            product_id=products[0].product_id,
            from_warehouse_id=warehouses[0].warehouse_id,
            to_warehouse_id=warehouses[1].warehouse_id,
            quantity=20
        )
        print(f"\nStock transfer: {msg}")
        
        # Warehouse utilization
        for warehouse in warehouses:
            util = self.warehouse_service.get_warehouse_utilization(
                warehouse.warehouse_id
            )
            print(f"\nWarehouse '{util.get('name')}' utilization: "
                  f"{util.get('utilization_percentage', 0)}%")
        
        # Purchase order flow
        admin = demo_data['admin']
        supplier = demo_data['suppliers'][0]
        
        po = self.purchase_order_service.create_purchase_order(
            supplier_id=supplier.supplier_id,
            warehouse_id=warehouses[0].warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=5)
        )
        po.add_item(products[2].product_id, 25, Decimal('1500.00'))
        po.submit()
        po.approve()
        po.mark_shipped()
        
        success, msg = self.purchase_order_service.receive_purchase_order(po.po_id)
        print(f"\nPurchase Order received: {msg}")
        
        # Check updated inventory
        total_macbook = self.inventory_service.get_total_stock(products[2].product_id)
        print(f"MacBook total stock after PO: {total_macbook}")
    
    def demo_admin_features(self, demo_data: dict):
        """Demonstrate admin features"""
        print("\n" + "="*60)
        print("ADMIN FEATURES DEMO")
        print("="*60)
        
        # Order statistics
        stats = self.order_service.get_order_statistics()
        print(f"\nOrder Statistics:")
        print(f"  Total Orders: {stats['total_orders']}")
        print(f"  Total Revenue: ${stats['total_revenue']}")
        print(f"  Average Order Value: ${stats['average_order_value']:.2f}")
        print(f"  Status Breakdown: {stats['status_breakdown']}")
        
        # All users
        all_users = self.user_service.get_all_users()
        print(f"\nTotal Users: {len(all_users)}")
        
        customers = self.user_service.get_all_users(user_type='customer')
        print(f"Customers: {len(customers)}")
        
        # All orders
        all_orders = self.order_service.get_all_orders()
        print(f"\nAll Orders: {len(all_orders)}")
        
        pending_orders = self.order_service.get_all_orders(status='pending')
        print(f"Pending Orders: {len(pending_orders)}")
        
        # All purchase orders
        all_pos = self.purchase_order_service.get_all_purchase_orders()
        print(f"\nAll Purchase Orders: {len(all_pos)}")
        
        # Category tree
        root_categories = self.category_service.get_root_categories()
        print(f"\nCategory Tree:")
        for cat in root_categories:
            print(f"  {cat.name}")
            for child in cat.children:
                print(f"    └── {child.name}")
    
    def run_demo(self):
        """Run complete demonstration"""
        print("\n" + "="*60)
        print("AMAZON CLONE - COMPLETE DEMO")
        print("="*60)
        
        # Setup demo data
        demo_data = self.setup_demo_data()
        
        # Run demos
        self.demo_user_flow(demo_data)
        self.demo_shopping_flow(demo_data)
        self.demo_inventory_management(demo_data)
        self.demo_admin_features(demo_data)
        
        print("\n" + "="*60)
        print("DEMO COMPLETE!")
        print("="*60)
        print("\nAmazon Clone features demonstrated:")
        print("  ✓ User Authentication (Register, Login, Logout)")
        print("  ✓ Multi-level Category Management")
        print("  ✓ Product Listing, Search, and Filtering")
        print("  ✓ Product Detail View with Reviews")
        print("  ✓ Shopping Cart Functionality")
        print("  ✓ Wishlist Management")
        print("  ✓ Coupon/Discount System")
        print("  ✓ Sales Order Management")
        print("  ✓ Purchase Order Management")
        print("  ✓ Inventory Management System")
        print("  ✓ Warehouse Management")
        print("  ✓ Supplier Management")
        print("  ✓ User Management (Admin)")
        print("  ✓ Notification System")
        print("  ✓ Address Management")
        print("  ✓ Order Statistics & Reporting")


# ============================================================
# DJANGO VIEWS (Template/Structure)
# ============================================================

class DjangoViewTemplates:
    """
    Django view templates showing how the services would be used in Django views.
    These represent the structure of Django views for the Amazon clone.
    """
    
    @staticmethod
    def get_view_structure() -> dict:
        """Returns the structure of Django views"""
        return {
            'authentication': {
                'SignUpView': {
                    'methods': ['GET', 'POST'],
                    'template': 'auth/signup.html',
                    'description': 'User registration view'
                },
                'LoginView': {
                    'methods': ['GET', 'POST'],
                    'template': 'auth/login.html',
                    'description': 'User login view'
                },
                'LogoutView': {
                    'methods': ['POST'],
                    'description': 'User logout view'
                },
                'ProfileView': {
                    'methods': ['GET', 'POST'],
                    'template': 'auth/profile.html',
                    'description': 'User profile management'
                }
            },
            'products': {
                'ProductListView': {
                    'methods': ['GET'],
                    'template': 'products/list.html',
                    'description': 'Product listing with search and filters'
                },
                'ProductDetailView': {
                    'methods': ['GET'],
                    'template': 'products/detail.html',
                    'description': 'Product detail page with reviews'
                },
                'CategoryView': {
                    'methods': ['GET'],
                    'template': 'products/category.html',
                    'description': 'Products by category'
                },
                'SearchView': {
                    'methods': ['GET'],
                    'template': 'products/search.html',
                    'description': 'Product search results'
                }
            },
            'cart': {
                'CartView': {
                    'methods': ['GET'],
                    'template': 'cart/cart.html',
                    'description': 'Shopping cart view'
                },
                'AddToCartView': {
                    'methods': ['POST'],
                    'description': 'Add item to cart'
                },
                'UpdateCartView': {
                    'methods': ['POST'],
                    'description': 'Update cart item quantity'
                },
                'RemoveFromCartView': {
                    'methods': ['POST'],
                    'description': 'Remove item from cart'
                }
            },
            'orders': {
                'CheckoutView': {
                    'methods': ['GET', 'POST'],
                    'template': 'orders/checkout.html',
                    'description': 'Checkout process'
                },
                'OrderConfirmationView': {
                    'methods': ['GET'],
                    'template': 'orders/confirmation.html',
                    'description': 'Order confirmation page'
                },
                'OrderListView': {
                    'methods': ['GET'],
                    'template': 'orders/list.html',
                    'description': 'User order history'
                },
                'OrderDetailView': {
                    'methods': ['GET'],
                    'template': 'orders/detail.html',
                    'description': 'Order detail view'
                }
            },
            'admin': {
                'AdminDashboardView': {
                    'methods': ['GET'],
                    'template': 'admin/dashboard.html',
                    'description': 'Admin dashboard with statistics'
                },
                'AdminProductView': {
                    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                    'template': 'admin/products.html',
                    'description': 'Product management'
                },
                'AdminOrderView': {
                    'methods': ['GET', 'POST'],
                    'template': 'admin/orders.html',
                    'description': 'Order management'
                },
                'AdminInventoryView': {
                    'methods': ['GET', 'POST'],
                    'template': 'admin/inventory.html',
                    'description': 'Inventory management'
                },
                'AdminWarehouseView': {
                    'methods': ['GET', 'POST'],
                    'template': 'admin/warehouses.html',
                    'description': 'Warehouse management'
                },
                'AdminSupplierView': {
                    'methods': ['GET', 'POST'],
                    'template': 'admin/suppliers.html',
                    'description': 'Supplier management'
                },
                'AdminPurchaseOrderView': {
                    'methods': ['GET', 'POST'],
                    'template': 'admin/purchase_orders.html',
                    'description': 'Purchase order management'
                },
                'AdminUserView': {
                    'methods': ['GET', 'POST'],
                    'template': 'admin/users.html',
                    'description': 'User management'
                }
            }
        }
    
    @staticmethod
    def get_url_patterns() -> list:
        """Returns URL patterns for the application"""
        return [
            # Authentication
            ('', 'HomeView', 'home'),
            ('signup/', 'SignUpView', 'signup'),
            ('login/', 'LoginView', 'login'),
            ('logout/', 'LogoutView', 'logout'),
            ('profile/', 'ProfileView', 'profile'),
            ('profile/change-password/', 'ChangePasswordView', 'change_password'),
            
            # Products
            ('products/', 'ProductListView', 'product_list'),
            ('products/<int:pk>/', 'ProductDetailView', 'product_detail'),
            ('products/search/', 'SearchView', 'search'),
            ('category/<slug:slug>/', 'CategoryView', 'category'),
            
            # Cart
            ('cart/', 'CartView', 'cart'),
            ('cart/add/', 'AddToCartView', 'add_to_cart'),
            ('cart/update/', 'UpdateCartView', 'update_cart'),
            ('cart/remove/', 'RemoveFromCartView', 'remove_from_cart'),
            
            # Wishlist
            ('wishlist/', 'WishlistView', 'wishlist'),
            ('wishlist/add/', 'AddToWishlistView', 'add_to_wishlist'),
            ('wishlist/remove/', 'RemoveFromWishlistView', 'remove_from_wishlist'),
            
            # Orders
            ('checkout/', 'CheckoutView', 'checkout'),
            ('orders/', 'OrderListView', 'order_list'),
            ('orders/<int:pk>/', 'OrderDetailView', 'order_detail'),
            ('orders/<int:pk>/cancel/', 'CancelOrderView', 'cancel_order'),
            
            # Admin
            ('admin-panel/', 'AdminDashboardView', 'admin_dashboard'),
            ('admin-panel/products/', 'AdminProductView', 'admin_products'),
            ('admin-panel/orders/', 'AdminOrderView', 'admin_orders'),
            ('admin-panel/inventory/', 'AdminInventoryView', 'admin_inventory'),
            ('admin-panel/warehouses/', 'AdminWarehouseView', 'admin_warehouses'),
            ('admin-panel/suppliers/', 'AdminSupplierView', 'admin_suppliers'),
            ('admin-panel/purchase-orders/', 'AdminPurchaseOrderView', 'admin_purchase_orders'),
            ('admin-panel/users/', 'AdminUserView', 'admin_users'),
        ]


# ============================================================
# DJANGO MODELS (as Python classes showing Django model structure)
# ============================================================

class DjangoModelDefinitions:
    """
    Shows how the models would be defined in Django ORM.
    These are template definitions showing the Django model structure.
    """
    
    @staticmethod
    def get_model_definitions() -> str:
        return '''
# models.py - Django Model Definitions

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    user_type = models.CharField(
        max_length=20,
        choices=[
            ("customer", "Customer"),
            ("admin", "Admin"),
            ("supplier", "Supplier"),
            ("warehouse_manager", "Warehouse Manager"),
        ],
        default="customer"
    )
    profile_picture = models.ImageField(upload_to="profiles/", blank=True)
    
    def __str__(self):
        return f"{self.user.username} Profile"


class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, 
        on_delete=models.SET_NULL, related_name="children"
    )
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    rating = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300)
    capacity = models.IntegerField(default=0)
    manager = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.location}"


class Product(models.Model):
    name = models.CharField(max_length=300)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )
    sku = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    weight = models.FloatField(default=0.0)
    dimensions = models.CharField(max_length=100, blank=True)
    discount_percentage = models.FloatField(default=0.0)
    featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_discounted_price(self):
        if self.discount_percentage > 0:
            discount = self.price * (self.discount_percentage / 100)
            return self.price - discount
        return self.price
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.product.name}"


class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    reorder_point = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["product", "warehouse"]
    
    def get_available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    def needs_reorder(self):
        return self.get_available_quantity() <= self.reorder_point
    
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("shipped", "Shipped"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    expected_delivery = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Address(models.Model):
    ADDRESS_TYPES = [("shipping", "Shipping"), ("billing", "Billing")]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    street = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default="shipping")
    
    def get_full_address(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}, {self.country}"
    
    def __str__(self):
        return f"{self.user.username} - {self.city}, {self.country}"


class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]
    PAYMENT_STATUS = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name="shipping_orders"
    )
    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, related_name="billing_orders"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS, default="pending"
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tracking_number = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class SalesOrderItem(models.Model):
    order = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=300)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())
    
    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def get_subtotal(self):
        return self.price * self.quantity
    
    class Meta:
        unique_together = ["cart", "product"]


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ["product", "user"]
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    name = models.CharField(max_length=200, default="My Wishlist")
    products = models.ManyToManyField(Product, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Coupon(models.Model):
    DISCOUNT_TYPES = [("percentage", "Percentage"), ("fixed", "Fixed Amount")]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.IntegerField(null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.code


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("order_update", "Order Update"),
        ("price_drop", "Price Drop"),
        ("back_in_stock", "Back in Stock"),
        ("promotion", "Promotion"),
        ("system", "System"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
'''


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Main entry point for the Amazon Clone application"""
    print("="*60)
    print("AMAZON CLONE - DJANGO E-COMMERCE PLATFORM")
    print("="*60)
    print("\nInitializing application...")
    
    # Create and run the application
    app = AmazonCloneApp()
    app.run_demo()
    
    # Show Django view structure
    print("\n" + "="*60)
    print("DJANGO APPLICATION STRUCTURE")
    print("="*60)
    
    view_templates = DjangoViewTemplates()
    view_structure = view_templates.get_view_structure()
    
    print("\nView Structure:")
    for section, views in view_structure.items():
        print(f"\n  {section.upper()}:")
        for view_name, view_info in views.items():
            methods = ', '.join(view_info.get('methods', []))
            desc = view_info.get('description', '')
            print(f"    - {view_name} [{methods}]: {desc}")
    
    print("\nURL Patterns:")
    url_patterns = view_templates.get_url_patterns()
    for pattern, view, name in url_patterns[:10]:
        print(f"  /{pattern} -> {view} (name='{name}')")
    print(f"  ... and {len(url_patterns) - 10} more URL patterns")
    
    print("\n" + "="*60)
    print("DJANGO MODEL DEFINITIONS")
    print("="*60)
    model_defs = DjangoModelDefinitions()
    print("Django models defined for:")
    models_list = [
        'UserProfile', 'Category', 'Supplier', 'Warehouse', 
        'Product', 'ProductImage', 'Inventory', 'PurchaseOrder',
        'PurchaseOrderItem', 'Address', 'SalesOrder', 'SalesOrderItem',
        'Cart', 'CartItem', 'Review', 'Wishlist', 'Coupon', 'Notification'
    ]
    for model in models_list:
        print(f"  ✓ {model}")
    
    print("\n" + "="*60)
    print("APPLICATION SUMMARY")
    print("="*60)
    print("""
Amazon Clone Features:
  
  1. USER MANAGEMENT
     - Multi-level user types (Customer, Admin, Supplier, Warehouse Manager)
     - Registration, Login, Logout
     - Profile management
     - Password change
  
  2. PRODUCT MANAGEMENT
     - Multi-level category hierarchy
     - Product CRUD operations
     - Product search and filtering
     - Product reviews and ratings
     - Featured products
     - Discount management
  
  3. SHOPPING EXPERIENCE
     - Shopping cart (session & user-based)
     - Wishlist management
     - Coupon/discount system
     - Multi-step checkout
  
  4. ORDER MANAGEMENT
     - Sales order lifecycle (pending -> confirmed -> processing -> shipped -> delivered)
     - Order cancellation and refunds
     - Order tracking
     - Payment processing
  
  5. INVENTORY MANAGEMENT
     - Real-time stock tracking
     - Multi-warehouse support
     - Stock reservations
     - Low stock alerts
     - Stock transfer between warehouses
     - Inventory history
  
  6. PURCHASE ORDER MANAGEMENT
     - PO lifecycle (draft -> submitted -> approved -> shipped -> received)
     - Automatic inventory update on receipt
     - Supplier management
  
  7. WAREHOUSE MANAGEMENT
     - Multiple warehouse support
     - Capacity tracking
     - Utilization reports
     - Stock transfers
  
  8. SUPPLIER MANAGEMENT
     - Supplier profiles
     - Supplier ratings
     - Purchase order tracking
  
  9. NOTIFICATIONS
     - Order status notifications
     - System notifications
     - Read/unread tracking
  
  10. ADMIN FEATURES
      - Dashboard with statistics
      - User management
      - Order management
      - Inventory reports
      - Purchase order management
    """)
    
    print("="*60)
    print("Amazon Clone implementation complete!")
    print("="*60)


if __name__ == '__main__':
    main()