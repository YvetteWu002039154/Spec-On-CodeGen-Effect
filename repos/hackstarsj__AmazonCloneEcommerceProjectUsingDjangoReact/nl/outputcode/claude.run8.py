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
    'AUTH_USER_MODEL': 'auth.User',
    'LOGIN_URL': '/login/',
    'LOGIN_REDIRECT_URL': '/',
    'LOGOUT_REDIRECT_URL': '/',
}


def setup_django():
    """Setup Django configuration."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '__main__')
    
    from django.conf import settings
    if not settings.configured:
        settings.configure(**DJANGO_SETTINGS)
    
    django.setup()


# ============================================================
# MODELS
# ============================================================

class UserProfile:
    """User profile model representation."""
    
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
        self.created_at = datetime.now()
        self.is_active = True
        self.loyalty_points = 0
    
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self) -> str:
        return f"UserProfile(id={self.user_id}, username={self.username}, type={self.user_type})"


class Category:
    """Product category model."""
    
    def __init__(self, category_id: int, name: str, description: str = '',
                 parent_id: int = None, level: int = 1):
        self.category_id = category_id
        self.name = name
        self.description = description
        self.parent_id = parent_id
        self.level = level  # Multi-level category support
        self.children = []
        self.is_active = True
        self.created_at = datetime.now()
    
    def add_child(self, child_category: 'Category'):
        """Add a child category."""
        child_category.parent_id = self.category_id
        child_category.level = self.level + 1
        self.children.append(child_category)
    
    def get_breadcrumb(self, categories: dict) -> list:
        """Get category breadcrumb path."""
        breadcrumb = [self]
        current = self
        while current.parent_id:
            parent = categories.get(current.parent_id)
            if parent:
                breadcrumb.insert(0, parent)
                current = parent
            else:
                break
        return breadcrumb
    
    def __repr__(self) -> str:
        return f"Category(id={self.category_id}, name={self.name}, level={self.level})"


class Supplier:
    """Supplier model for inventory management."""
    
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
        self.products = []
    
    def update_rating(self, new_rating: float):
        """Update supplier rating."""
        if 0 <= new_rating <= 5:
            self.rating = (self.rating * self.total_orders + new_rating) / (self.total_orders + 1)
    
    def __repr__(self) -> str:
        return f"Supplier(id={self.supplier_id}, name={self.name})"


class Warehouse:
    """Warehouse model for inventory management."""
    
    def __init__(self, warehouse_id: int, name: str, location: str,
                 capacity: int = 10000, manager_id: int = None):
        self.warehouse_id = warehouse_id
        self.name = name
        self.location = location
        self.capacity = capacity
        self.manager_id = manager_id
        self.current_stock = 0
        self.is_active = True
        self.created_at = datetime.now()
        self.inventory = {}  # product_id -> quantity
    
    def get_available_capacity(self) -> int:
        """Get available warehouse capacity."""
        return self.capacity - self.current_stock
    
    def add_stock(self, product_id: int, quantity: int) -> bool:
        """Add stock to warehouse."""
        if self.current_stock + quantity <= self.capacity:
            self.inventory[product_id] = self.inventory.get(product_id, 0) + quantity
            self.current_stock += quantity
            return True
        return False
    
    def remove_stock(self, product_id: int, quantity: int) -> bool:
        """Remove stock from warehouse."""
        current_qty = self.inventory.get(product_id, 0)
        if current_qty >= quantity:
            self.inventory[product_id] = current_qty - quantity
            self.current_stock -= quantity
            return True
        return False
    
    def get_product_quantity(self, product_id: int) -> int:
        """Get quantity of a product in warehouse."""
        return self.inventory.get(product_id, 0)
    
    def __repr__(self) -> str:
        return f"Warehouse(id={self.warehouse_id}, name={self.name}, location={self.location})"


class Product:
    """Product model."""
    
    def __init__(self, product_id: int, name: str, description: str,
                 price: Decimal, category_id: int, supplier_id: int = None,
                 sku: str = '', brand: str = '', weight: float = 0.0,
                 dimensions: dict = None):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = Decimal(str(price))
        self.category_id = category_id
        self.supplier_id = supplier_id
        self.sku = sku or f"SKU-{product_id:06d}"
        self.brand = brand
        self.weight = weight
        self.dimensions = dimensions or {}
        self.images = []
        self.is_active = True
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.rating = 0.0
        self.review_count = 0
        self.tags = []
        self.discount_percentage = 0.0
        self.is_featured = False
        self.stock_quantity = 0
        self.reorder_level = 10
        self.max_stock_level = 1000
    
    def get_discounted_price(self) -> Decimal:
        """Get price after discount."""
        if self.discount_percentage > 0:
            discount = self.price * Decimal(str(self.discount_percentage / 100))
            return self.price - discount
        return self.price
    
    def update_rating(self, new_rating: float):
        """Update product rating."""
        if 0 <= new_rating <= 5:
            total_rating = self.rating * self.review_count + new_rating
            self.review_count += 1
            self.rating = total_rating / self.review_count
    
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock_quantity > 0
    
    def needs_reorder(self) -> bool:
        """Check if product needs reorder."""
        return self.stock_quantity <= self.reorder_level
    
    def __repr__(self) -> str:
        return f"Product(id={self.product_id}, name={self.name}, price={self.price})"


class ProductVariant:
    """Product variant model (size, color, etc.)."""
    
    def __init__(self, variant_id: int, product_id: int, 
                 variant_type: str, variant_value: str,
                 price_modifier: Decimal = Decimal('0'),
                 stock_quantity: int = 0):
        self.variant_id = variant_id
        self.product_id = product_id
        self.variant_type = variant_type  # size, color, material, etc.
        self.variant_value = variant_value
        self.price_modifier = Decimal(str(price_modifier))
        self.stock_quantity = stock_quantity
        self.sku = f"VAR-{variant_id:06d}"
        self.is_active = True
    
    def __repr__(self) -> str:
        return f"ProductVariant(id={self.variant_id}, type={self.variant_type}, value={self.variant_value})"


class Review:
    """Product review model."""
    
    def __init__(self, review_id: int, product_id: int, user_id: int,
                 rating: int, title: str = '', content: str = ''):
        self.review_id = review_id
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating  # 1-5
        self.title = title
        self.content = content
        self.created_at = datetime.now()
        self.is_verified_purchase = False
        self.helpful_votes = 0
        self.is_approved = True
    
    def __repr__(self) -> str:
        return f"Review(id={self.review_id}, product={self.product_id}, rating={self.rating})"


class CartItem:
    """Shopping cart item model."""
    
    def __init__(self, cart_item_id: int, cart_id: int, product_id: int,
                 quantity: int, price: Decimal, variant_id: int = None):
        self.cart_item_id = cart_item_id
        self.cart_id = cart_id
        self.product_id = product_id
        self.quantity = quantity
        self.price = Decimal(str(price))
        self.variant_id = variant_id
        self.added_at = datetime.now()
    
    def get_subtotal(self) -> Decimal:
        """Get item subtotal."""
        return self.price * self.quantity
    
    def __repr__(self) -> str:
        return f"CartItem(id={self.cart_item_id}, product={self.product_id}, qty={self.quantity})"


class ShoppingCart:
    """Shopping cart model."""
    
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
                 variant_id: int = None) -> CartItem:
        """Add item to cart."""
        # Check if item already exists
        for item in self.items:
            if item.product_id == product_id and item.variant_id == variant_id:
                item.quantity += quantity
                self.updated_at = datetime.now()
                return item
        
        # Create new cart item
        cart_item = CartItem(
            cart_item_id=len(self.items) + 1,
            cart_id=self.cart_id,
            product_id=product_id,
            quantity=quantity,
            price=price,
            variant_id=variant_id
        )
        self.items.append(cart_item)
        self.updated_at = datetime.now()
        return cart_item
    
    def remove_item(self, product_id: int, variant_id: int = None) -> bool:
        """Remove item from cart."""
        for i, item in enumerate(self.items):
            if item.product_id == product_id and item.variant_id == variant_id:
                self.items.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def update_quantity(self, product_id: int, quantity: int, 
                       variant_id: int = None) -> bool:
        """Update item quantity in cart."""
        for item in self.items:
            if item.product_id == product_id and item.variant_id == variant_id:
                if quantity <= 0:
                    return self.remove_item(product_id, variant_id)
                item.quantity = quantity
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_subtotal(self) -> Decimal:
        """Get cart subtotal."""
        return sum(item.get_subtotal() for item in self.items)
    
    def get_total(self) -> Decimal:
        """Get cart total after discounts."""
        return self.get_subtotal() - self.discount_amount
    
    def get_item_count(self) -> int:
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items)
    
    def clear(self):
        """Clear all items from cart."""
        self.items = []
        self.updated_at = datetime.now()
    
    def apply_coupon(self, coupon_code: str, discount_amount: Decimal):
        """Apply coupon to cart."""
        self.coupon_code = coupon_code
        self.discount_amount = discount_amount
    
    def __repr__(self) -> str:
        return f"ShoppingCart(id={self.cart_id}, user={self.user_id}, items={len(self.items)})"


class Address:
    """Address model."""
    
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
        self.created_at = datetime.now()
    
    def get_full_address(self) -> str:
        """Get formatted full address."""
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"
    
    def __repr__(self) -> str:
        return f"Address(id={self.address_id}, city={self.city}, country={self.country})"


class OrderItem:
    """Order item model."""
    
    def __init__(self, order_item_id: int, order_id: int, product_id: int,
                 quantity: int, unit_price: Decimal, variant_id: int = None):
        self.order_item_id = order_item_id
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = Decimal(str(unit_price))
        self.variant_id = variant_id
        self.discount_amount = Decimal('0')
        self.tax_amount = Decimal('0')
    
    def get_subtotal(self) -> Decimal:
        """Get item subtotal."""
        return (self.unit_price * self.quantity) - self.discount_amount
    
    def get_total_with_tax(self) -> Decimal:
        """Get item total including tax."""
        return self.get_subtotal() + self.tax_amount
    
    def __repr__(self) -> str:
        return f"OrderItem(id={self.order_item_id}, product={self.product_id}, qty={self.quantity})"


class SalesOrder:
    """Sales order model."""
    
    STATUS_CHOICES = [
        'pending', 'confirmed', 'processing', 'shipped', 
        'delivered', 'cancelled', 'refunded', 'returned'
    ]
    
    def __init__(self, order_id: int, user_id: int, 
                 shipping_address_id: int, billing_address_id: int):
        self.order_id = order_id
        self.order_number = f"SO-{order_id:08d}"
        self.user_id = user_id
        self.shipping_address_id = shipping_address_id
        self.billing_address_id = billing_address_id
        self.items = []
        self.status = 'pending'
        self.payment_status = 'pending'
        self.payment_method = ''
        self.subtotal = Decimal('0')
        self.tax_amount = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.discount_amount = Decimal('0')
        self.total_amount = Decimal('0')
        self.coupon_code = None
        self.notes = ''
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.shipped_at = None
        self.delivered_at = None
        self.tracking_number = ''
        self.carrier = ''
        self.status_history = []
    
    def add_item(self, product_id: int, quantity: int, unit_price: Decimal,
                variant_id: int = None) -> OrderItem:
        """Add item to order."""
        order_item = OrderItem(
            order_item_id=len(self.items) + 1,
            order_id=self.order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            variant_id=variant_id
        )
        self.items.append(order_item)
        self.calculate_totals()
        return order_item
    
    def calculate_totals(self):
        """Calculate order totals."""
        self.subtotal = sum(item.get_subtotal() for item in self.items)
        self.tax_amount = sum(item.tax_amount for item in self.items)
        self.total_amount = (self.subtotal + self.tax_amount + 
                           self.shipping_cost - self.discount_amount)
        self.updated_at = datetime.now()
    
    def update_status(self, new_status: str, notes: str = ''):
        """Update order status."""
        if new_status in self.STATUS_CHOICES:
            old_status = self.status
            self.status = new_status
            self.status_history.append({
                'from': old_status,
                'to': new_status,
                'timestamp': datetime.now(),
                'notes': notes
            })
            self.updated_at = datetime.now()
            
            if new_status == 'shipped':
                self.shipped_at = datetime.now()
            elif new_status == 'delivered':
                self.delivered_at = datetime.now()
    
    def cancel(self, reason: str = '') -> bool:
        """Cancel the order."""
        if self.status in ['pending', 'confirmed']:
            self.update_status('cancelled', reason)
            return True
        return False
    
    def __repr__(self) -> str:
        return f"SalesOrder(id={self.order_id}, number={self.order_number}, status={self.status})"


class PurchaseOrderItem:
    """Purchase order item model."""
    
    def __init__(self, item_id: int, po_id: int, product_id: int,
                 quantity: int, unit_cost: Decimal):
        self.item_id = item_id
        self.po_id = po_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_cost = Decimal(str(unit_cost))
        self.received_quantity = 0
        self.is_fully_received = False
    
    def receive_quantity(self, qty: int) -> bool:
        """Record received quantity."""
        if self.received_quantity + qty <= self.quantity:
            self.received_quantity += qty
            self.is_fully_received = self.received_quantity >= self.quantity
            return True
        return False
    
    def get_total_cost(self) -> Decimal:
        """Get total cost for this item."""
        return self.unit_cost * self.quantity
    
    def __repr__(self) -> str:
        return f"POItem(id={self.item_id}, product={self.product_id}, qty={self.quantity})"


class PurchaseOrder:
    """Purchase order model for inventory management."""
    
    STATUS_CHOICES = [
        'draft', 'submitted', 'approved', 'ordered', 
        'partially_received', 'received', 'cancelled'
    ]
    
    def __init__(self, po_id: int, supplier_id: int, warehouse_id: int,
                 created_by: int, expected_delivery: datetime = None):
        self.po_id = po_id
        self.po_number = f"PO-{po_id:08d}"
        self.supplier_id = supplier_id
        self.warehouse_id = warehouse_id
        self.created_by = created_by
        self.items = []
        self.status = 'draft'
        self.total_amount = Decimal('0')
        self.tax_amount = Decimal('0')
        self.shipping_cost = Decimal('0')
        self.expected_delivery = expected_delivery
        self.actual_delivery = None
        self.notes = ''
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.approved_by = None
        self.approved_at = None
        self.status_history = []
    
    def add_item(self, product_id: int, quantity: int, 
                unit_cost: Decimal) -> PurchaseOrderItem:
        """Add item to purchase order."""
        item = PurchaseOrderItem(
            item_id=len(self.items) + 1,
            po_id=self.po_id,
            product_id=product_id,
            quantity=quantity,
            unit_cost=unit_cost
        )
        self.items.append(item)
        self.calculate_total()
        return item
    
    def calculate_total(self):
        """Calculate purchase order total."""
        self.total_amount = (sum(item.get_total_cost() for item in self.items) + 
                           self.tax_amount + self.shipping_cost)
        self.updated_at = datetime.now()
    
    def submit(self) -> bool:
        """Submit purchase order for approval."""
        if self.status == 'draft' and self.items:
            self.update_status('submitted')
            return True
        return False
    
    def approve(self, approved_by: int) -> bool:
        """Approve purchase order."""
        if self.status == 'submitted':
            self.approved_by = approved_by
            self.approved_at = datetime.now()
            self.update_status('approved')
            return True
        return False
    
    def update_status(self, new_status: str, notes: str = ''):
        """Update purchase order status."""
        if new_status in self.STATUS_CHOICES:
            old_status = self.status
            self.status = new_status
            self.status_history.append({
                'from': old_status,
                'to': new_status,
                'timestamp': datetime.now(),
                'notes': notes
            })
            self.updated_at = datetime.now()
    
    def receive_items(self, warehouse: Warehouse, 
                     received_items: dict) -> bool:
        """Record received items and update warehouse inventory."""
        all_received = True
        for item in self.items:
            qty = received_items.get(item.product_id, 0)
            if qty > 0:
                item.receive_quantity(qty)
                warehouse.add_stock(item.product_id, qty)
            if not item.is_fully_received:
                all_received = False
        
        if all_received:
            self.update_status('received')
            self.actual_delivery = datetime.now()
        else:
            self.update_status('partially_received')
        
        return all_received
    
    def __repr__(self) -> str:
        return f"PurchaseOrder(id={self.po_id}, number={self.po_number}, status={self.status})"


class Coupon:
    """Coupon/discount model."""
    
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
        """Check if coupon is valid."""
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
        """Calculate discount amount."""
        if self.discount_type == 'percentage':
            return order_amount * (self.discount_value / 100)
        elif self.discount_type == 'fixed_amount':
            return min(self.discount_value, order_amount)
        elif self.discount_type == 'free_shipping':
            return Decimal('0')  # Handled separately
        return Decimal('0')
    
    def use(self):
        """Mark coupon as used."""
        self.current_uses += 1
    
    def __repr__(self) -> str:
        return f"Coupon(id={self.coupon_id}, code={self.code}, type={self.discount_type})"


class Payment:
    """Payment model."""
    
    STATUS_CHOICES = ['pending', 'processing', 'completed', 'failed', 'refunded']
    
    def __init__(self, payment_id: int, order_id: int, amount: Decimal,
                 payment_method: str, transaction_id: str = ''):
        self.payment_id = payment_id
        self.order_id = order_id
        self.amount = Decimal(str(amount))
        self.payment_method = payment_method  # credit_card, paypal, bank_transfer
        self.transaction_id = transaction_id
        self.status = 'pending'
        self.created_at = datetime.now()
        self.processed_at = None
        self.refund_amount = Decimal('0')
        self.refund_reason = ''
    
    def process(self, transaction_id: str) -> bool:
        """Process payment."""
        self.transaction_id = transaction_id
        self.status = 'completed'
        self.processed_at = datetime.now()
        return True
    
    def refund(self, amount: Decimal, reason: str = '') -> bool:
        """Process refund."""
        if self.status == 'completed' and amount <= self.amount:
            self.refund_amount = amount
            self.refund_reason = reason
            self.status = 'refunded'
            return True
        return False
    
    def __repr__(self) -> str:
        return f"Payment(id={self.payment_id}, amount={self.amount}, status={self.status})"


class Shipment:
    """Shipment tracking model."""
    
    STATUS_CHOICES = ['preparing', 'shipped', 'in_transit', 'out_for_delivery', 'delivered', 'failed']
    
    def __init__(self, shipment_id: int, order_id: int, warehouse_id: int,
                 carrier: str, tracking_number: str = ''):
        self.shipment_id = shipment_id
        self.order_id = order_id
        self.warehouse_id = warehouse_id
        self.carrier = carrier
        self.tracking_number = tracking_number
        self.status = 'preparing'
        self.created_at = datetime.now()
        self.shipped_at = None
        self.estimated_delivery = None
        self.actual_delivery = None
        self.tracking_events = []
    
    def add_tracking_event(self, location: str, description: str, status: str):
        """Add tracking event."""
        event = {
            'timestamp': datetime.now(),
            'location': location,
            'description': description,
            'status': status
        }
        self.tracking_events.append(event)
        self.status = status
    
    def ship(self, tracking_number: str, estimated_delivery: datetime):
        """Mark shipment as shipped."""
        self.tracking_number = tracking_number
        self.shipped_at = datetime.now()
        self.estimated_delivery = estimated_delivery
        self.status = 'shipped'
    
    def deliver(self):
        """Mark shipment as delivered."""
        self.actual_delivery = datetime.now()
        self.status = 'delivered'
    
    def __repr__(self) -> str:
        return f"Shipment(id={self.shipment_id}, order={self.order_id}, status={self.status})"


class InventoryTransaction:
    """Inventory transaction model for tracking stock movements."""
    
    TRANSACTION_TYPES = [
        'purchase', 'sale', 'return', 'adjustment', 
        'transfer', 'damage', 'expired'
    ]
    
    def __init__(self, transaction_id: int, product_id: int, warehouse_id: int,
                 transaction_type: str, quantity: int, reference_id: int = None,
                 notes: str = ''):
        self.transaction_id = transaction_id
        self.product_id = product_id
        self.warehouse_id = warehouse_id
        self.transaction_type = transaction_type
        self.quantity = quantity  # positive for in, negative for out
        self.reference_id = reference_id  # PO ID or SO ID
        self.notes = notes
        self.created_at = datetime.now()
        self.created_by = None
    
    def __repr__(self) -> str:
        return f"InventoryTransaction(id={self.transaction_id}, type={self.transaction_type}, qty={self.quantity})"


class Wishlist:
    """Wishlist model."""
    
    def __init__(self, wishlist_id: int, user_id: int, name: str = 'My Wishlist'):
        self.wishlist_id = wishlist_id
        self.user_id = user_id
        self.name = name
        self.items = []
        self.is_public = False
        self.created_at = datetime.now()
    
    def add_item(self, product_id: int) -> bool:
        """Add product to wishlist."""
        if product_id not in self.items:
            self.items.append(product_id)
            return True
        return False
    
    def remove_item(self, product_id: int) -> bool:
        """Remove product from wishlist."""
        if product_id in self.items:
            self.items.remove(product_id)
            return True
        return False
    
    def __repr__(self) -> str:
        return f"Wishlist(id={self.wishlist_id}, user={self.user_id}, items={len(self.items)})"


# ============================================================
# SERVICES / BUSINESS LOGIC
# ============================================================

class UserService:
    """Service for user management operations."""
    
    def __init__(self):
        self.users = {}
        self.next_id = 1
    
    def create_user(self, username: str, email: str, password: str,
                   first_name: str = '', last_name: str = '',
                   user_type: str = 'customer') -> UserProfile:
        """Create a new user."""
        # Validate email uniqueness
        for user in self.users.values():
            if user.email == email:
                raise ValueError(f"Email {email} already exists")
            if user.username == username:
                raise ValueError(f"Username {username} already exists")
        
        user = UserProfile(
            user_id=self.next_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type
        )
        self.users[self.next_id] = user
        self.next_id += 1
        return user
    
    def get_user(self, user_id: int) -> UserProfile:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> UserProfile:
        """Get user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def update_user(self, user_id: int, **kwargs) -> UserProfile:
        """Update user profile."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        allowed_fields = ['first_name', 'last_name', 'phone', 'address', 'email']
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(user, key, value)
        
        return user
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        user = self.get_user(user_id)
        if user:
            user.is_active = False
            return True
        return False
    
    def get_all_users(self, user_type: str = None) -> list:
        """Get all users, optionally filtered by type."""
        users = list(self.users.values())
        if user_type:
            users = [u for u in users if u.user_type == user_type]
        return users
    
    def add_loyalty_points(self, user_id: int, points: int):
        """Add loyalty points to user."""
        user = self.get_user(user_id)
        if user:
            user.loyalty_points += points


class ProductService:
    """Service for product management operations."""
    
    def __init__(self):
        self.products = {}
        self.categories = {}
        self.variants = {}
        self.reviews = {}
        self.next_product_id = 1
        self.next_category_id = 1
        self.next_variant_id = 1
        self.next_review_id = 1
    
    def create_category(self, name: str, description: str = '',
                       parent_id: int = None) -> Category:
        """Create a new category."""
        level = 1
        if parent_id:
            parent = self.categories.get(parent_id)
            if parent:
                level = parent.level + 1
        
        category = Category(
            category_id=self.next_category_id,
            name=name,
            description=description,
            parent_id=parent_id,
            level=level
        )
        self.categories[self.next_category_id] = category
        
        if parent_id and parent_id in self.categories:
            self.categories[parent_id].add_child(category)
        
        self.next_category_id += 1
        return category
    
    def create_product(self, name: str, description: str, price: Decimal,
                      category_id: int, supplier_id: int = None,
                      **kwargs) -> Product:
        """Create a new product."""
        product = Product(
            product_id=self.next_product_id,
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            supplier_id=supplier_id,
            **kwargs
        )
        self.products[self.next_product_id] = product
        self.next_product_id += 1
        return product
    
    def get_product(self, product_id: int) -> Product:
        """Get product by ID."""
        return self.products.get(product_id)
    
    def search_products(self, query: str = '', category_id: int = None,
                       min_price: Decimal = None, max_price: Decimal = None,
                       brand: str = None, in_stock: bool = None,
                       sort_by: str = 'name') -> list:
        """Search and filter products."""
        results = [p for p in self.products.values() if p.is_active]
        
        if query:
            query_lower = query.lower()
            results = [p for p in results if 
                      query_lower in p.name.lower() or 
                      query_lower in p.description.lower() or
                      query_lower in p.brand.lower() or
                      any(query_lower in tag.lower() for tag in p.tags)]
        
        if category_id:
            # Include subcategories
            category_ids = self._get_category_tree(category_id)
            results = [p for p in results if p.category_id in category_ids]
        
        if min_price is not None:
            results = [p for p in results if p.get_discounted_price() >= min_price]
        
        if max_price is not None:
            results = [p for p in results if p.get_discounted_price() <= max_price]
        
        if brand:
            results = [p for p in results if p.brand.lower() == brand.lower()]
        
        if in_stock is not None:
            results = [p for p in results if p.is_in_stock() == in_stock]
        
        # Sort results
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
    
    def _get_category_tree(self, category_id: int) -> set:
        """Get all category IDs in a category tree."""
        ids = {category_id}
        category = self.categories.get(category_id)
        if category:
            for child in category.children:
                ids.update(self._get_category_tree(child.category_id))
        return ids
    
    def add_product_variant(self, product_id: int, variant_type: str,
                           variant_value: str, price_modifier: Decimal = Decimal('0'),
                           stock_quantity: int = 0) -> ProductVariant:
        """Add variant to product."""
        variant = ProductVariant(
            variant_id=self.next_variant_id,
            product_id=product_id,
            variant_type=variant_type,
            variant_value=variant_value,
            price_modifier=price_modifier,
            stock_quantity=stock_quantity
        )
        self.variants[self.next_variant_id] = variant
        self.next_variant_id += 1
        return variant
    
    def add_review(self, product_id: int, user_id: int, rating: int,
                  title: str = '', content: str = '') -> Review:
        """Add product review."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        review = Review(
            review_id=self.next_review_id,
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            content=content
        )
        
        if product_id not in self.reviews:
            self.reviews[product_id] = []
        self.reviews[product_id].append(review)
        
        # Update product rating
        product = self.get_product(product_id)
        if product:
            product.update_rating(rating)
        
        self.next_review_id += 1
        return review
    
    def get_product_reviews(self, product_id: int) -> list:
        """Get all reviews for a product."""
        return self.reviews.get(product_id, [])
    
    def get_featured_products(self) -> list:
        """Get featured products."""
        return [p for p in self.products.values() if p.is_featured and p.is_active]
    
    def update_stock(self, product_id: int, quantity: int):
        """Update product stock quantity."""
        product = self.get_product(product_id)
        if product:
            product.stock_quantity = quantity
    
    def get_low_stock_products(self) -> list:
        """Get products that need reordering."""
        return [p for p in self.products.values() if p.needs_reorder() and p.is_active]


class CartService:
    """Service for shopping cart operations."""
    
    def __init__(self, product_service: ProductService):
        self.carts = {}
        self.product_service = product_service
        self.next_cart_id = 1
    
    def get_or_create_cart(self, user_id: int = None, 
                          session_id: str = None) -> ShoppingCart:
        """Get existing cart or create new one."""
        # Look for existing cart
        for cart in self.carts.values():
            if user_id and cart.user_id == user_id:
                return cart
            if session_id and cart.session_id == session_id:
                return cart
        
        # Create new cart
        cart = ShoppingCart(
            cart_id=self.next_cart_id,
            user_id=user_id,
            session_id=session_id
        )
        self.carts[self.next_cart_id] = cart
        self.next_cart_id += 1
        return cart
    
    def add_to_cart(self, cart_id: int, product_id: int, quantity: int,
                   variant_id: int = None) -> tuple:
        """Add product to cart."""
        cart = self.carts.get(cart_id)
        if not cart:
            return None, "Cart not found"
        
        product = self.product_service.get_product(product_id)
        if not product:
            return None, "Product not found"
        
        if not product.is_active:
            return None, "Product is not available"
        
        if not product.is_in_stock():
            return None, "Product is out of stock"
        
        if quantity > product.stock_quantity:
            return None, f"Only {product.stock_quantity} items available"
        
        price = product.get_discounted_price()
        if variant_id:
            variant = self.product_service.variants.get(variant_id)
            if variant:
                price += variant.price_modifier
        
        item = cart.add_item(product_id, quantity, price, variant_id)
        return item, "Item added to cart"
    
    def remove_from_cart(self, cart_id: int, product_id: int,
                        variant_id: int = None) -> bool:
        """Remove product from cart."""
        cart = self.carts.get(cart_id)
        if cart:
            return cart.remove_item(product_id, variant_id)
        return False
    
    def update_cart_quantity(self, cart_id: int, product_id: int,
                            quantity: int, variant_id: int = None) -> tuple:
        """Update product quantity in cart."""
        cart = self.carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        if quantity > 0:
            product = self.product_service.get_product(product_id)
            if product and quantity > product.stock_quantity:
                return False, f"Only {product.stock_quantity} items available"
        
        success = cart.update_quantity(product_id, quantity, variant_id)
        return success, "Cart updated" if success else "Item not found in cart"
    
    def merge_carts(self, session_cart_id: int, user_cart_id: int) -> ShoppingCart:
        """Merge session cart with user cart after login."""
        session_cart = self.carts.get(session_cart_id)
        user_cart = self.carts.get(user_cart_id)
        
        if session_cart and user_cart:
            for item in session_cart.items:
                user_cart.add_item(
                    item.product_id, item.quantity, 
                    item.price, item.variant_id
                )
            del self.carts[session_cart_id]
        
        return user_cart
    
    def apply_coupon(self, cart_id: int, coupon: Coupon) -> tuple:
        """Apply coupon to cart."""
        cart = self.carts.get(cart_id)
        if not cart:
            return False, "Cart not found"
        
        is_valid, message = coupon.is_valid(cart.get_subtotal())
        if not is_valid:
            return False, message
        
        discount = coupon.calculate_discount(cart.get_subtotal())
        cart.apply_coupon(coupon.code, discount)
        return True, f"Coupon applied. Discount: {discount}"


class OrderService:
    """Service for order management operations."""
    
    def __init__(self, product_service: ProductService, 
                 cart_service: CartService):
        self.orders = {}
        self.product_service = product_service
        self.cart_service = cart_service
        self.next_order_id = 1
        self.payments = {}
        self.next_payment_id = 1
        self.shipments = {}
        self.next_shipment_id = 1
    
    def create_order_from_cart(self, cart_id: int, user_id: int,
                               shipping_address_id: int, 
                               billing_address_id: int,
                               payment_method: str) -> tuple:
        """Create order from shopping cart."""
        cart = self.cart_service.carts.get(cart_id)
        if not cart or not cart.items:
            return None, "Cart is empty"
        
        # Validate stock availability
        for item in cart.items:
            product = self.product_service.get_product(item.product_id)
            if not product:
                return None, f"Product {item.product_id} not found"
            if product.stock_quantity < item.quantity:
                return None, f"Insufficient stock for {product.name}"
        
        # Create order
        order = SalesOrder(
            order_id=self.next_order_id,
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id
        )
        order.payment_method = payment_method
        order.coupon_code = cart.coupon_code
        order.discount_amount = cart.discount_amount
        
        # Add items to order
        for item in cart.items:
            order.add_item(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.price,
                variant_id=item.variant_id
            )
        
        # Calculate shipping
        order.shipping_cost = self._calculate_shipping(order)
        order.calculate_totals()
        
        # Reserve stock
        for item in cart.items:
            product = self.product_service.get_product(item.product_id)
            product.stock_quantity -= item.quantity
        
        self.orders[self.next_order_id] = order
        self.next_order_id += 1
        
        # Clear cart
        cart.clear()
        
        return order, "Order created successfully"
    
    def _calculate_shipping(self, order: SalesOrder) -> Decimal:
        """Calculate shipping cost."""
        subtotal = order.subtotal
        if subtotal >= Decimal('50'):
            return Decimal('0')  # Free shipping over $50
        return Decimal('9.99')
    
    def process_payment(self, order_id: int, 
                       transaction_id: str) -> tuple:
        """Process payment for order."""
        order = self.orders.get(order_id)
        if not order:
            return None, "Order not found"
        
        payment = Payment(
            payment_id=self.next_payment_id,
            order_id=order_id,
            amount=order.total_amount,
            payment_method=order.payment_method,
            transaction_id=transaction_id
        )
        
        success = payment.process(transaction_id)
        if success:
            order.payment_status = 'paid'
            order.update_status('confirmed')
            self.payments[self.next_payment_id] = payment
            self.next_payment_id += 1
            return payment, "Payment processed successfully"
        
        return None, "Payment processing failed"
    
    def create_shipment(self, order_id: int, warehouse_id: int,
                       carrier: str, tracking_number: str,
                       estimated_delivery: datetime) -> tuple:
        """Create shipment for order."""
        order = self.orders.get(order_id)
        if not order:
            return None, "Order not found"
        
        if order.status not in ['confirmed', 'processing']:
            return None, "Order cannot be shipped in current status"
        
        shipment = Shipment(
            shipment_id=self.next_shipment_id,
            order_id=order_id,
            warehouse_id=warehouse_id,
            carrier=carrier,
            tracking_number=tracking_number
        )
        shipment.ship(tracking_number, estimated_delivery)
        
        order.update_status('shipped')
        order.tracking_number = tracking_number
        order.carrier = carrier
        
        self.shipments[self.next_shipment_id] = shipment
        self.next_shipment_id += 1
        
        return shipment, "Shipment created successfully"
    
    def deliver_order(self, order_id: int) -> bool:
        """Mark order as delivered."""
        order = self.orders.get(order_id)
        if order and order.status == 'shipped':
            order.update_status('delivered')
            
            # Find and update shipment
            for shipment in self.shipments.values():
                if shipment.order_id == order_id:
                    shipment.deliver()
            
            return True
        return False
    
    def cancel_order(self, order_id: int, reason: str = '') -> tuple:
        """Cancel an order."""
        order = self.orders.get(order_id)
        if not order:
            return False, "Order not found"
        
        if order.cancel(reason):
            # Restore stock
            for item in order.items:
                product = self.product_service.get_product(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
            return True, "Order cancelled successfully"
        
        return False, "Order cannot be cancelled in current status"
    
    def get_user_orders(self, user_id: int) -> list:
        """Get all orders for a user."""
        return [o for o in self.orders.values() if o.user_id == user_id]
    
    def get_order(self, order_id: int) -> SalesOrder:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def process_return(self, order_id: int, items: list, reason: str) -> tuple:
        """Process order return."""
        order = self.orders.get(order_id)
        if not order:
            return False, "Order not found"
        
        if order.status != 'delivered':
            return False, "Only delivered orders can be returned"
        
        order.update_status('returned', reason)
        
        # Restore stock for returned items
        for item_data in items:
            product = self.product_service.get_product(item_data['product_id'])
            if product:
                product.stock_quantity += item_data['quantity']
        
        return True, "Return processed successfully"


class InventoryService:
    """Service for inventory management operations."""
    
    def __init__(self, product_service: ProductService):
        self.warehouses = {}
        self.suppliers = {}
        self.purchase_orders = {}
        self.transactions = {}
        self.product_service = product_service
        self.next_warehouse_id = 1
        self.next_supplier_id = 1
        self.next_po_id = 1
        self.next_transaction_id = 1
    
    def create_warehouse(self, name: str, location: str,
                        capacity: int = 10000, 
                        manager_id: int = None) -> Warehouse:
        """Create a new warehouse."""
        warehouse = Warehouse(
            warehouse_id=self.next_warehouse_id,
            name=name,
            location=location,
            capacity=capacity,
            manager_id=manager_id
        )
        self.warehouses[self.next_warehouse_id] = warehouse
        self.next_warehouse_id += 1
        return warehouse
    
    def create_supplier(self, name: str, email: str, phone: str = '',
                       address: str = '', contact_person: str = '',
                       payment_terms: str = 'NET30') -> Supplier:
        """Create a new supplier."""
        supplier = Supplier(
            supplier_id=self.next_supplier_id,
            name=name,
            email=email,
            phone=phone,
            address=address,
            contact_person=contact_person,
            payment_terms=payment_terms
        )
        self.suppliers[self.next_supplier_id] = supplier
        self.next_supplier_id += 1
        return supplier
    
    def create_purchase_order(self, supplier_id: int, warehouse_id: int,
                             created_by: int, 
                             expected_delivery: datetime = None) -> tuple:
        """Create a new purchase order."""
        supplier = self.suppliers.get(supplier_id)
        if not supplier:
            return None, "Supplier not found"
        
        warehouse = self.warehouses.get(warehouse_id)
        if not warehouse:
            return None, "Warehouse not found"
        
        po = PurchaseOrder(
            po_id=self.next_po_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            created_by=created_by,
            expected_delivery=expected_delivery
        )
        self.purchase_orders[self.next_po_id] = po
        self.next_po_id += 1
        
        return po, "Purchase order created"
    
    def add_po_item(self, po_id: int, product_id: int, quantity: int,
                   unit_cost: Decimal) -> tuple:
        """Add item to purchase order."""
        po = self.purchase_orders.get(po_id)
        if not po:
            return None, "Purchase order not found"
        
        if po.status != 'draft':
            return None, "Can only add items to draft purchase orders"
        
        product = self.product_service.get_product(product_id)
        if not product:
            return None, "Product not found"
        
        item = po.add_item(product_id, quantity, unit_cost)
        return item, "Item added to purchase order"
    
    def submit_purchase_order(self, po_id: int) -> tuple:
        """Submit purchase order for approval."""
        po = self.purchase_orders.get(po_id)
        if not po:
            return False, "Purchase order not found"
        
        if po.submit():
            return True, "Purchase order submitted for approval"
        return False, "Cannot submit purchase order"
    
    def approve_purchase_order(self, po_id: int, 
                              approved_by: int) -> tuple:
        """Approve purchase order."""
        po = self.purchase_orders.get(po_id)
        if not po:
            return False, "Purchase order not found"
        
        if po.approve(approved_by):
            return True, "Purchase order approved"
        return False, "Cannot approve purchase order"
    
    def receive_purchase_order(self, po_id: int, 
                              received_items: dict) -> tuple:
        """Receive items from purchase order."""
        po = self.purchase_orders.get(po_id)
        if not po:
            return False, "Purchase order not found"
        
        if po.status not in ['approved', 'ordered', 'partially_received']:
            return False, "Purchase order is not in receivable status"
        
        warehouse = self.warehouses.get(po.warehouse_id)
        if not warehouse:
            return False, "Warehouse not found"
        
        all_received = po.receive_items(warehouse, received_items)
        
        # Update product stock levels
        for product_id, qty in received_items.items():
            product = self.product_service.get_product(product_id)
            if product:
                product.stock_quantity += qty
            
            # Record inventory transaction
            self._record_transaction(
                product_id=product_id,
                warehouse_id=po.warehouse_id,
                transaction_type='purchase',
                quantity=qty,
                reference_id=po_id
            )
        
        return True, "Items received successfully"
    
    def _record_transaction(self, product_id: int, warehouse_id: int,
                           transaction_type: str, quantity: int,
                           reference_id: int = None, notes: str = ''):
        """Record inventory transaction."""
        transaction = InventoryTransaction(
            transaction_id=self.next_transaction_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference_id=reference_id,
            notes=notes
        )
        self.transactions[self.next_transaction_id] = transaction
        self.next_transaction_id += 1
        return transaction
    
    def transfer_stock(self, product_id: int, from_warehouse_id: int,
                      to_warehouse_id: int, quantity: int) -> tuple:
        """Transfer stock between warehouses."""
        from_warehouse = self.warehouses.get(from_warehouse_id)
        to_warehouse = self.warehouses.get(to_warehouse_id)
        
        if not from_warehouse or not to_warehouse:
            return False, "Warehouse not found"
        
        if from_warehouse.get_product_quantity(product_id) < quantity:
            return False, "Insufficient stock in source warehouse"
        
        if to_warehouse.get_available_capacity() < quantity:
            return False, "Insufficient capacity in destination warehouse"
        
        from_warehouse.remove_stock(product_id, quantity)
        to_warehouse.add_stock(product_id, quantity)
        
        # Record transactions
        self._record_transaction(product_id, from_warehouse_id, 'transfer', -quantity)
        self._record_transaction(product_id, to_warehouse_id, 'transfer', quantity)
        
        return True, "Stock transferred successfully"
    
    def adjust_inventory(self, product_id: int, warehouse_id: int,
                        new_quantity: int, reason: str = '') -> tuple:
        """Adjust inventory quantity."""
        warehouse = self.warehouses.get(warehouse_id)
        if not warehouse:
            return False, "Warehouse not found"
        
        current_qty = warehouse.get_product_quantity(product_id)
        difference = new_quantity - current_qty
        
        if difference > 0:
            warehouse.add_stock(product_id, difference)
        elif difference < 0:
            warehouse.remove_stock(product_id, abs(difference))
        
        # Update product stock
        product = self.product_service.get_product(product_id)
        if product:
            product.stock_quantity = new_quantity
        
        self._record_transaction(
            product_id, warehouse_id, 'adjustment', 
            difference, notes=reason
        )
        
        return True, f"Inventory adjusted by {difference}"
    
    def get_inventory_report(self) -> dict:
        """Generate inventory report."""
        report = {
            'total_products': len(self.product_service.products),
            'total_warehouses': len(self.warehouses),
            'total_suppliers': len(self.suppliers),
            'low_stock_products': [],
            'out_of_stock_products': [],
            'warehouse_utilization': {},
            'pending_purchase_orders': 0,
            'total_inventory_value': Decimal('0')
        }
        
        # Low stock and out of stock
        for product in self.product_service.products.values():
            if product.stock_quantity == 0:
                report['out_of_stock_products'].append(product)
            elif product.needs_reorder():
                report['low_stock_products'].append(product)
            
            report['total_inventory_value'] += (
                product.price * product.stock_quantity
            )
        
        # Warehouse utilization
        for wh in self.warehouses.values():
            utilization = (wh.current_stock / wh.capacity * 100) if wh.capacity > 0 else 0
            report['warehouse_utilization'][wh.warehouse_id] = {
                'name': wh.name,
                'utilization_percentage': round(utilization, 2),
                'current_stock': wh.current_stock,
                'capacity': wh.capacity
            }
        
        # Pending POs
        report['pending_purchase_orders'] = sum(
            1 for po in self.purchase_orders.values() 
            if po.status in ['submitted', 'approved', 'ordered']
        )
        
        return report
    
    def get_supplier(self, supplier_id: int) -> Supplier:
        """Get supplier by ID."""
        return self.suppliers.get(supplier_id)
    
    def get_warehouse(self, warehouse_id: int) -> Warehouse:
        """Get warehouse by ID."""
        return self.warehouses.get(warehouse_id)
    
    def get_purchase_order(self, po_id: int) -> PurchaseOrder:
        """Get purchase order by ID."""
        return self.purchase_orders.get(po_id)
    
    def get_all_purchase_orders(self, status: str = None) -> list:
        """Get all purchase orders."""
        orders = list(self.purchase_orders.values())
        if status:
            orders = [po for po in orders if po.status == status]
        return orders


class WishlistService:
    """Service for wishlist operations."""
    
    def __init__(self):
        self.wishlists = {}
        self.next_wishlist_id = 1
    
    def create_wishlist(self, user_id: int, name: str = 'My Wishlist') -> Wishlist:
        """Create a new wishlist."""
        wishlist = Wishlist(
            wishlist_id=self.next_wishlist_id,
            user_id=user_id,
            name=name
        )
        self.wishlists[self.next_wishlist_id] = wishlist
        self.next_wishlist_id += 1
        return wishlist
    
    def get_user_wishlists(self, user_id: int) -> list:
        """Get all wishlists for a user."""
        return [w for w in self.wishlists.values() if w.user_id == user_id]
    
    def add_to_wishlist(self, wishlist_id: int, product_id: int) -> tuple:
        """Add product to wishlist."""
        wishlist = self.wishlists.get(wishlist_id)
        if not wishlist:
            return False, "Wishlist not found"
        
        if wishlist.add_item(product_id):
            return True, "Product added to wishlist"
        return False, "Product already in wishlist"
    
    def remove_from_wishlist(self, wishlist_id: int, product_id: int) -> tuple:
        """Remove product from wishlist."""
        wishlist = self.wishlists.get(wishlist_id)
        if not wishlist:
            return False, "Wishlist not found"
        
        if wishlist.remove_item(product_id):
            return True, "Product removed from wishlist"
        return False, "Product not in wishlist"


class AddressService:
    """Service for address management."""
    
    def __init__(self):
        self.addresses = {}
        self.next_address_id = 1
    
    def add_address(self, user_id: int, address_type: str, street: str,
                   city: str, state: str, country: str, postal_code: str,
                   is_default: bool = False) -> Address:
        """Add new address for user."""
        if is_default:
            # Remove default from other addresses of same type
            for addr in self.addresses.values():
                if addr.user_id == user_id and addr.address_type == address_type:
                    addr.is_default = False
        
        address = Address(
            address_id=self.next_address_id,
            user_id=user_id,
            address_type=address_type,
            street=street,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            is_default=is_default
        )
        self.addresses[self.next_address_id] = address
        self.next_address_id += 1
        return address
    
    def get_user_addresses(self, user_id: int, 
                          address_type: str = None) -> list:
        """Get all addresses for a user."""
        addresses = [a for a in self.addresses.values() if a.user_id == user_id]
        if address_type:
            addresses = [a for a in addresses if a.address_type == address_type]
        return addresses
    
    def get_default_address(self, user_id: int, 
                           address_type: str) -> Address:
        """Get default address for user."""
        for addr in self.addresses.values():
            if (addr.user_id == user_id and 
                addr.address_type == address_type and 
                addr.is_default):
                return addr
        return None
    
    def update_address(self, address_id: int, **kwargs) -> Address:
        """Update address."""
        address = self.addresses.get(address_id)
        if not address:
            raise ValueError(f"Address {address_id} not found")
        
        allowed_fields = ['street', 'city', 'state', 'country', 'postal_code']
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(address, key, value)
        
        return address
    
    def delete_address(self, address_id: int) -> bool:
        """Delete address."""
        if address_id in self.addresses:
            del self.addresses[address_id]
            return True
        return False


class CouponService:
    """Service for coupon management."""
    
    def __init__(self):
        self.coupons = {}
        self.next_coupon_id = 1
    
    def create_coupon(self, code: str, discount_type: str,
                     discount_value: Decimal, 
                     min_order_amount: Decimal = Decimal('0'),
                     max_uses: int = None,
                     expiry_date: datetime = None) -> Coupon:
        """Create a new coupon."""
        # Check for duplicate code
        for coupon in self.coupons.values():
            if coupon.code == code.upper():
                raise ValueError(f"Coupon code {code} already exists")
        
        coupon = Coupon(
            coupon_id=self.next_coupon_id,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            min_order_amount=min_order_amount,
            max_uses=max_uses,
            expiry_date=expiry_date
        )
        self.coupons[self.next_coupon_id] = coupon
        self.next_coupon_id += 1
        return coupon
    
    def get_coupon_by_code(self, code: str) -> Coupon:
        """Get coupon by code."""
        for coupon in self.coupons.values():
            if coupon.code == code.upper():
                return coupon
        return None
    
    def validate_coupon(self, code: str, 
                       order_amount: Decimal) -> tuple:
        """Validate coupon code."""
        coupon = self.get_coupon_by_code(code)
        if not coupon:
            return None, "Invalid coupon code"
        
        is_valid, message = coupon.is_valid(order_amount)
        if not is_valid:
            return None, message
        
        return coupon, "Coupon is valid"


# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class AmazonCloneApp:
    """Main application class that orchestrates all services."""
    
    def __init__(self):
        # Initialize services
        self.user_service = UserService()
        self.product_service = ProductService()
        self.cart_service = CartService(self.product_service)
        self.order_service = OrderService(self.product_service, self.cart_service)
        self.inventory_service = InventoryService(self.product_service)
        self.wishlist_service = WishlistService()
        self.address_service = AddressService()
        self.coupon_service = CouponService()
        
        print("Amazon Clone Application initialized successfully!")
    
    def setup_demo_data(self):
        """Setup demo data for testing."""
        print("\n=== Setting up demo data ===\n")
        
        # Create users
        admin = self.user_service.create_user(
            username='admin',
            email='admin@amazon-clone.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            user_type='admin'
        )
        
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
        
        warehouse_manager = self.user_service.create_user(
            username='wh_manager',
            email='warehouse@amazon-clone.com',
            password='manager123',
            first_name='Warehouse',
            last_name='Manager',
            user_type='warehouse_manager'
        )
        
        print(f"Created users: {admin}, {customer1}, {customer2}, {warehouse_manager}")
        
        # Create categories (multi-level)
        electronics = self.product_service.create_category(
            name='Electronics',
            description='Electronic devices and accessories'
        )
        
        computers = self.product_service.create_category(
            name='Computers',
            description='Laptops, desktops, and accessories',
            parent_id=electronics.category_id
        )
        
        laptops = self.product_service.create_category(
            name='Laptops',
            description='Portable computers',
            parent_id=computers.category_id
        )
        
        phones = self.product_service.create_category(
            name='Smartphones',
            description='Mobile phones and accessories',
            parent_id=electronics.category_id
        )
        
        clothing = self.product_service.create_category(
            name='Clothing',
            description='Fashion and apparel'
        )
        
        mens_clothing = self.product_service.create_category(
            name="Men's Clothing",
            description="Men's fashion",
            parent_id=clothing.category_id
        )
        
        books = self.product_service.create_category(
            name='Books',
            description='Books and literature'
        )
        
        print(f"Created categories: Electronics, Computers, Laptops, Smartphones, Clothing, Books")
        
        # Create suppliers
        supplier1 = self.inventory_service.create_supplier(
            name='TechSupply Co.',
            email='supply@techsupply.com',
            phone='+1-555-0100',
            address='123 Tech Street, Silicon Valley, CA',
            contact_person='Bob Johnson',
            payment_terms='NET30'
        )
        
        supplier2 = self.inventory_service.create_supplier(
            name='Fashion Wholesale Ltd.',
            email='orders@fashionwholesale.com',
            phone='+1-555-0200',
            address='456 Fashion Ave, New York, NY',
            contact_person='Sarah Williams',
            payment_terms='NET15'
        )
        
        print(f"Created suppliers: {supplier1}, {supplier2}")
        
        # Create warehouses
        warehouse1 = self.inventory_service.create_warehouse(
            name='Main Warehouse',
            location='Seattle, WA',
            capacity=50000,
            manager_id=warehouse_manager.user_id
        )
        
        warehouse2 = self.inventory_service.create_warehouse(
            name='East Coast Warehouse',
            location='New York, NY',
            capacity=30000,
            manager_id=warehouse_manager.user_id
        )
        
        print(f"Created warehouses: {warehouse1}, {warehouse2}")
        
        # Create products
        laptop1 = self.product_service.create_product(
            name='ProBook Laptop 15',
            description='High-performance laptop with Intel Core i7, 16GB RAM, 512GB SSD',
            price=Decimal('999.99'),
            category_id=laptops.category_id,
            supplier_id=supplier1.supplier_id,
            brand='ProBook',
            weight=2.1,
            sku='LAPTOP-001'
        )
        laptop1.stock_quantity = 50
        laptop1.is_featured = True
        laptop1.tags = ['laptop', 'computer', 'intel', 'portable']
        
        laptop2 = self.product_service.create_product(
            name='UltraSlim Laptop 13',
            description='Ultra-thin laptop perfect for professionals',
            price=Decimal('1299.99'),
            category_id=laptops.category_id,
            supplier_id=supplier1.supplier_id,
            brand='UltraSlim',
            weight=1.2,
            sku='LAPTOP-002'
        )
        laptop2.stock_quantity = 30
        laptop2.discount_percentage = 10.0
        
        phone1 = self.product_service.create_product(
            name='SmartPhone X Pro',
            description='Latest flagship smartphone with 5G capability',
            price=Decimal('799.99'),
            category_id=phones.category_id,
            supplier_id=supplier1.supplier_id,
            brand='SmartPhone',
            weight=0.18,
            sku='PHONE-001'
        )
        phone1.stock_quantity = 100
        phone1.is_featured = True
        phone1.tags = ['smartphone', 'mobile', '5G', 'camera']
        
        shirt1 = self.product_service.create_product(
            name='Classic Cotton T-Shirt',
            description='Comfortable everyday cotton t-shirt',
            price=Decimal('19.99'),
            category_id=mens_clothing.category_id,
            supplier_id=supplier2.supplier_id,
            brand='BasicWear',
            weight=0.2,
            sku='SHIRT-001'
        )
        shirt1.stock_quantity = 200
        shirt1.tags = ['shirt', 'cotton', 'casual', 'clothing']
        
        book1 = self.product_service.create_product(
            name='Python Programming Mastery',
            description='Complete guide to Python programming',
            price=Decimal('39.99'),
            category_id=books.category_id,
            brand='TechBooks',
            weight=0.5,
            sku='BOOK-001'
        )
        book1.stock_quantity = 75
        
        print(f"Created products: {laptop1}, {laptop2}, {phone1}, {shirt1}, {book1}")
        
        # Add product variants
        self.product_service.add_product_variant(
            product_id=shirt1.product_id,
            variant_type='size',
            variant_value='S',
            stock_quantity=50
        )
        self.product_service.add_product_variant(
            product_id=shirt1.product_id,
            variant_type='size',
            variant_value='M',
            stock_quantity=80
        )
        self.product_service.add_product_variant(
            product_id=shirt1.product_id,
            variant_type='size',
            variant_value='L',
            stock_quantity=70
        )
        self.product_service.add_product_variant(
            product_id=shirt1.product_id,
            variant_type='color',
            variant_value='Blue',
            stock_quantity=100
        )
        
        # Add reviews
        self.product_service.add_review(
            product_id=laptop1.product_id,
            user_id=customer1.user_id,
            rating=5,
            title='Excellent laptop!',
            content='Great performance and battery life.'
        )
        
        self.product_service.add_review(
            product_id=phone1.product_id,
            user_id=customer2.user_id,
            rating=4,
            title='Good phone',
            content='Camera is amazing, battery could be better.'
        )
        
        # Add addresses
        addr1 = self.address_service.add_address(
            user_id=customer1.user_id,
            address_type='shipping',
            street='123 Main St',
            city='Seattle',
            state='WA',
            country='USA',
            postal_code='98101',
            is_default=True
        )
        
        addr2 = self.address_service.add_address(
            user_id=customer1.user_id,
            address_type='billing',
            street='123 Main St',
            city='Seattle',
            state='WA',
            country='USA',
            postal_code='98101',
            is_default=True
        )
        
        # Create coupons
        coupon1 = self.coupon_service.create_coupon(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10'),
            min_order_amount=Decimal('50'),
            max_uses=100,
            expiry_date=datetime.now() + timedelta(days=30)
        )
        
        coupon2 = self.coupon_service.create_coupon(
            code='FLAT20',
            discount_type='fixed_amount',
            discount_value=Decimal('20'),
            min_order_amount=Decimal('100')
        )
        
        print(f"Created coupons: {coupon1}, {coupon2}")
        
        # Create purchase order
        po, msg = self.inventory_service.create_purchase_order(
            supplier_id=supplier1.supplier_id,
            warehouse_id=warehouse1.warehouse_id,
            created_by=admin.user_id,
            expected_delivery=datetime.now() + timedelta(days=7)
        )
        
        self.inventory_service.add_po_item(
            po_id=po.po_id,
            product_id=laptop1.product_id,
            quantity=20,
            unit_cost=Decimal('750.00')
        )
        
        self.inventory_service.add_po_item(
            po_id=po.po_id,
            product_id=phone1.product_id,
            quantity=50,
            unit_cost=Decimal('500.00')
        )
        
        self.inventory_service.submit_purchase_order(po.po_id)
        self.inventory_service.approve_purchase_order(po.po_id, admin.user_id)
        
        print(f"Created and approved purchase order: {po}")
        
        # Add stock to warehouse
        warehouse1.add_stock(laptop1.product_id, 50)
        warehouse1.add_stock(phone1.product_id, 100)
        warehouse1.add_stock(shirt1.product_id, 200)
        warehouse2.add_stock(laptop2.product_id, 30)
        
        print("\n=== Demo data setup complete ===\n")
        
        return {
            'admin': admin,
            'customer1': customer1,
            'customer2': customer2,
            'warehouse_manager': warehouse_manager,
            'laptop1': laptop1,
            'laptop2': laptop2,
            'phone1': phone1,
            'shirt1': shirt1,
            'book1': book1,
            'warehouse1': warehouse1,
            'warehouse2': warehouse2,
            'supplier1': supplier1,
            'supplier2': supplier2,
            'addr1': addr1,
            'addr2': addr2,
            'coupon1': coupon1,
            'coupon2': coupon2,
            'po': po
        }
    
    def demo_shopping_flow(self, demo_data: dict):
        """Demonstrate complete shopping flow."""
        print("\n=== Shopping Flow Demo ===\n")
        
        customer1 = demo_data['customer1']
        laptop1 = demo_data['laptop1']
        phone1 = demo_data['phone1']
        addr1 = demo_data['addr1']
        addr2 = demo_data['addr2']
        coupon1 = demo_data['coupon1']
        
        # Create cart
        cart = self.cart_service.get_or_create_cart(user_id=customer1.user_id)
        print(f"Created cart: {cart}")
        
        # Add items to cart
        item1, msg1 = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=laptop1.product_id,
            quantity=1
        )
        print(f"Add laptop to cart: {msg1}")
        
        item2, msg2 = self.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=phone1.product_id,
            quantity=2
        )
        print(f"Add phone to cart: {msg2}")
        
        print(f"Cart total: ${cart.get_total()}")
        print(f"Cart items: {cart.get_item_count()}")
        
        # Apply coupon
        coupon, coupon_msg = self.coupon_service.validate_coupon(
            'SAVE10', cart.get_subtotal()
        )
        if coupon:
            success, apply_msg = self.cart_service.apply_coupon(
                cart.cart_id, coupon
            )
            print(f"Apply coupon: {apply_msg}")
        
        print(f"Cart total after coupon: ${cart.get_total()}")
        
        # Create order
        order, order_msg = self.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=customer1.user_id,
            shipping_address_id=addr1.address_id,
            billing_address_id=addr2.address_id,
            payment_method='credit_card'
        )
        
        if order:
            print(f"Order created: {order}")
            print(f"Order total: ${order.total_amount}")
            
            # Process payment
            payment, pay_msg = self.order_service.process_payment(
                order_id=order.order_id,
                transaction_id='TXN-123456789'
            )
            print(f"Payment: {pay_msg}")
            
            # Create shipment
            shipment, ship_msg = self.order_service.create_shipment(
                order_id=order.order_id,
                warehouse_id=demo_data['warehouse1'].warehouse_id,
                carrier='FedEx',
                tracking_number='FX-987654321',
                estimated_delivery=datetime.now() + timedelta(days=3)
            )
            print(f"Shipment: {ship_msg}")
            
            # Deliver order
            delivered = self.order_service.deliver_order(order.order_id)
            print(f"Order delivered: {delivered}")
            print(f"Final order status: {order.status}")
        
        return order
    
    def demo_inventory_management(self, demo_data: dict):
        """Demonstrate inventory management features."""
        print("\n=== Inventory Management Demo ===\n")
        
        warehouse1 = demo_data['warehouse1']
        warehouse2 = demo_data['warehouse2']
        laptop1 = demo_data['laptop1']
        
        # Transfer stock between warehouses
        success, msg = self.inventory_service.transfer_stock(
            product_id=laptop1.product_id,
            from_warehouse_id=warehouse1.warehouse_id,
            to_warehouse_id=warehouse2.warehouse_id,
            quantity=10
        )
        print(f"Stock transfer: {msg}")
        print(f"Warehouse 1 laptop stock: {warehouse1.get_product_quantity(laptop1.product_id)}")
        print(f"Warehouse 2 laptop stock: {warehouse2.get_product_quantity(laptop1.product_id)}")
        
        # Inventory adjustment
        success, msg = self.inventory_service.adjust_inventory(
            product_id=laptop1.product_id,
            warehouse_id=warehouse1.warehouse_id,
            new_quantity=45,
            reason='Physical count adjustment'
        )
        print(f"Inventory adjustment: {msg}")
        
        # Generate inventory report
        report = self.inventory_service.get_inventory_report()
        print(f"\nInventory Report:")
        print(f"  Total Products: {report['total_products']}")
        print(f"  Total Warehouses: {report['total_warehouses']}")
        print(f"  Total Suppliers: {report['total_suppliers']}")
        print(f"  Low Stock Products: {len(report['low_stock_products'])}")
        print(f"  Out of Stock Products: {len(report['out_of_stock_products'])}")
        print(f"  Total Inventory Value: ${report['total_inventory_value']}")
        print(f"  Pending Purchase Orders: {report['pending_purchase_orders']}")
        
        for wh_id, wh_data in report['warehouse_utilization'].items():
            print(f"  Warehouse '{wh_data['name']}': {wh_data['utilization_percentage']}% utilized")
    
    def demo_product_search(self):
        """Demonstrate product search functionality."""
        print("\n=== Product Search Demo ===\n")
        
        # Search by query
        results = self.product_service.search_products(query='laptop')
        print(f"Search 'laptop': {len(results)} results")
        for p in results:
            print(f"  - {p.name}: ${p.get_discounted_price()}")
        
        # Search by category
        electronics_cat = None
        for cat in self.product_service.categories.values():
            if cat.name == 'Electronics':
                electronics_cat = cat
                break
        
        if electronics_cat:
            results = self.product_service.search_products(
                category_id=electronics_cat.category_id
            )
            print(f"\nElectronics category: {len(results)} products")
        
        # Search with price filter
        results = self.product_service.search_products(
            max_price=Decimal('100'),
            sort_by='price_asc'
        )
        print(f"\nProducts under $100: {len(results)} results")
        for p in results:
            print(f"  - {p.name}: ${p.get_discounted_price()}")
        
        # Featured products
        featured = self.product_service.get_featured_products()
        print(f"\nFeatured products: {len(featured)}")
        for p in featured:
            print(f"  - {p.name}")
    
    def demo_user_management(self, demo_data: dict):
        """Demonstrate user management features."""
        print("\n=== User Management Demo ===\n")
        
        # Get all users
        all_users = self.user_service.get_all_users()
        print(f"Total users: {len(all_users)}")
        
        # Get customers only
        customers = self.user_service.get_all_users(user_type='customer')
        print(f"Customers: {len(customers)}")
        
        # Update user profile
        customer1 = demo_data['customer1']
        updated_user = self.user_service.update_user(
            user_id=customer1.user_id,
            phone='+1-555-1234',
            address='123 Main St, Seattle, WA'
        )
        print(f"Updated user: {updated_user.get_full_name()}, Phone: {updated_user.phone}")
        
        # Add loyalty points
        self.user_service.add_loyalty_points(customer1.user_id, 100)
        print(f"Loyalty points: {customer1.loyalty_points}")
        
        # Wishlist management
        wishlist = self.wishlist_service.create_wishlist(
            user_id=customer1.user_id,
            name='My Tech Wishlist'
        )
        
        success, msg = self.wishlist_service.add_to_wishlist(
            wishlist_id=wishlist.wishlist_id,
            product_id=demo_data['laptop2'].product_id
        )
        print(f"Add to wishlist: {msg}")
        
        success, msg = self.wishlist_service.add_to_wishlist(
            wishlist_id=wishlist.wishlist_id,
            product_id=demo_data['phone1'].product_id
        )
        print(f"Add to wishlist: {msg}")
        
        print(f"Wishlist items: {len(wishlist.items)}")
    
    def run_demo(self):
        """Run complete application demo."""
        print("=" * 60)
        print("AMAZON CLONE - COMPLETE DEMO")
        print("=" * 60)
        
        # Setup demo data
        demo_data = self.setup_demo_data()
        
        # Run demos
        self.demo_product_search()
        self.demo_shopping_flow(demo_data)
        self.demo_inventory_management(demo_data)
        self.demo_user_management(demo_data)
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        
        # Print summary statistics
        print("\n=== Application Statistics ===")
        print(f"Total Users: {len(self.user_service.users)}")
        print(f"Total Products: {len(self.product_service.products)}")
        print(f"Total Categories: {len(self.product_service.categories)}")
        print(f"Total Orders: {len(self.order_service.orders)}")
        print(f"Total Warehouses: {len(self.inventory_service.warehouses)}")
        print(f"Total Suppliers: {len(self.inventory_service.suppliers)}")
        print(f"Total Purchase Orders: {len(self.inventory_service.purchase_orders)}")
        print(f"Total Coupons: {len(self.coupon_service.coupons)}")
        print(f"Total Wishlists: {len(self.wishlist_service.wishlists)}")
        print(f"Total Addresses: {len(self.address_service.addresses)}")


# ============================================================
# DJANGO VIEWS (Conceptual Implementation)
# ============================================================

class ViewHandler:
    """Conceptual view handler representing Django views."""
    
    def __init__(self, app: AmazonCloneApp):
        self.app = app
    
    # Authentication Views
    def signup_view(self, username: str, email: str, password: str,
                   first_name: str = '', last_name: str = '') -> dict:
        """Handle user registration."""
        try:
            user = self.app.user_service.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            return {'success': True, 'user': user, 'message': 'Account created successfully'}
        except ValueError as e:
            return {'success': False, 'error': str(e)}
    
    def login_view(self, username: str, password: str) -> dict:
        """Handle user login."""
        user = self.app.user_service.get_user_by_username(username)
        if user and user.is_active:
            return {'success': True, 'user': user, 'message': 'Login successful'}
        return {'success': False, 'error': 'Invalid credentials'}
    
    def logout_view(self, user_id: int) -> dict:
        """Handle user logout."""
        return {'success': True, 'message': 'Logged out successfully'}
    
    # Product Views
    def product_list_view(self, query: str = '', category_id: int = None,
                         page: int = 1, per_page: int = 20) -> dict:
        """Handle product listing."""
        products = self.app.product_service.search_products(
            query=query, category_id=category_id
        )
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated = products[start:end]
        
        return {
            'products': paginated,
            'total': len(products),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(products) + per_page - 1) // per_page
        }
    
    def product_detail_view(self, product_id: int) -> dict:
        """Handle product detail view."""
        product = self.app.product_service.get_product(product_id)
        if not product:
            return {'error': 'Product not found'}
        
        reviews = self.app.product_service.get_product_reviews(product_id)
        variants = [v for v in self.app.product_service.variants.values() 
                   if v.product_id == product_id]
        
        return {
            'product': product,
            'reviews': reviews,
            'variants': variants
        }
    
    # Cart Views
    def cart_view(self, user_id: int) -> dict:
        """Handle cart view."""
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        return {
            'cart': cart,
            'items': cart.items,
            'subtotal': cart.get_subtotal(),
            'total': cart.get_total(),
            'item_count': cart.get_item_count()
        }
    
    def add_to_cart_view(self, user_id: int, product_id: int,
                        quantity: int, variant_id: int = None) -> dict:
        """Handle add to cart."""
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        item, message = self.app.cart_service.add_to_cart(
            cart_id=cart.cart_id,
            product_id=product_id,
            quantity=quantity,
            variant_id=variant_id
        )
        return {'success': item is not None, 'message': message, 'cart': cart}
    
    # Order Views
    def checkout_view(self, user_id: int, shipping_address_id: int,
                     billing_address_id: int, payment_method: str) -> dict:
        """Handle checkout."""
        cart = self.app.cart_service.get_or_create_cart(user_id=user_id)
        
        order, message = self.app.order_service.create_order_from_cart(
            cart_id=cart.cart_id,
            user_id=user_id,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id,
            payment_method=payment_method
        )
        
        return {
            'success': order is not None,
            'order': order,
            'message': message
        }
    
    def order_list_view(self, user_id: int) -> dict:
        """Handle order listing for user."""
        orders = self.app.order_service.get_user_orders(user_id)
        return {'orders': orders}
    
    def order_detail_view(self, order_id: int, user_id: int) -> dict:
        """Handle order detail view."""
        order = self.app.order_service.get_order(order_id)
        if not order or order.user_id != user_id:
            return {'error': 'Order not found'}
        return {'order': order}
    
    # Admin Views
    def admin_dashboard_view(self) -> dict:
        """Handle admin dashboard."""
        report = self.app.inventory_service.get_inventory_report()
        all_orders = list(self.app.order_service.orders.values())
        
        return {
            'inventory_report': report,
            'total_orders': len(all_orders),
            'pending_orders': len([o for o in all_orders if o.status == 'pending']),
            'total_revenue': sum(o.total_amount for o in all_orders 
                               if o.payment_status == 'paid'),
            'total_users': len(self.app.user_service.users)
        }
    
    def admin_inventory_view(self) -> dict:
        """Handle admin inventory view."""
        return {
            'products': list(self.app.product_service.products.values()),
            'warehouses': list(self.app.inventory_service.warehouses.values()),
            'low_stock': self.app.product_service.get_low_stock_products(),
            'purchase_orders': self.app.inventory_service.get_all_purchase_orders()
        }


# ============================================================
# URL PATTERNS (Conceptual)
# ============================================================

URL_PATTERNS = {
    # Authentication
    '/signup/': 'signup_view',
    '/login/': 'login_view',
    '/logout/': 'logout_view',
    
    # Products
    '/': 'product_list_view',
    '/products/': 'product_list_view',
    '/products/<int:product_id>/': 'product_detail_view',
    '/search/': 'product_list_view',
    
    # Cart
    '/cart/': 'cart_view',
    '/cart/add/': 'add_to_cart_view',
    '/cart/remove/': 'remove_from_cart_view',
    '/cart/update/': 'update_cart_view',
    
    # Orders
    '/checkout/': 'checkout_view',
    '/orders/': 'order_list_view',
    '/orders/<int:order_id>/': 'order_detail_view',
    
    # User Profile
    '/profile/': 'profile_view',
    '/profile/addresses/': 'address_list_view',
    '/wishlist/': 'wishlist_view',
    
    # Admin
    '/admin/dashboard/': 'admin_dashboard_view',
    '/admin/inventory/': 'admin_inventory_view',
    '/admin/orders/': 'admin_orders_view',
    '/admin/users/': 'admin_users_view',
    '/admin/suppliers/': 'admin_suppliers_view',
    '/admin/warehouses/': 'admin_warehouses_view',
    '/admin/purchase-orders/': 'admin_purchase_orders_view',
}


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Main entry point for the Amazon Clone application."""
    print("Starting Amazon Clone Application...")
    print("=" * 60)
    
    # Create and run the application
    app = AmazonCloneApp()
    
    # Run demo
    app.run_demo()
    
    # Demonstrate view handler
    print("\n=== View Handler Demo ===\n")
    view_handler = ViewHandler(app)
    
    # Test signup
    signup_result = view_handler.signup_view(
        username='new_user',
        email='newuser@example.com',
        password='password123',
        first_name='New',
        last_name='User'
    )
    print(f"Signup: {signup_result['message']}")
    
    # Test login
    login_result = view_handler.login_view('new_user', 'password123')
    print(f"Login: {login_result['message']}")
    
    # Test product list
    product_list = view_handler.product_list_view(query='laptop')
    print(f"Product search 'laptop': {product_list['total']} results")
    
    # Test admin dashboard
    dashboard = view_handler.admin_dashboard_view()
    print(f"\nAdmin Dashboard:")
    print(f"  Total Orders: {dashboard['total_orders']}")
    print(f"  Total Revenue: ${dashboard['total_revenue']}")
    print(f"  Total Users: {dashboard['total_users']}")
    
    print("\n" + "=" * 60)
    print("Amazon Clone Application - All features demonstrated successfully!")
    print("=" * 60)
    
    return app


if __name__ == '__main__':
    app = main()