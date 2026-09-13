# =============================================
# models.py
# =============================================
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import MinValueValidator
from django.utils import timezone

class User(AbstractUser):
    """
    Custom user model with additional fields for e-commerce.
    """
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_supplier = models.BooleanField(default=False)  # if the user is a supplier contact (not used for auth)

    def __str__(self):
        return self.email or self.username

class Category(models.Model):
    """
    Hierarchical product categories.
    """
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Supplier(models.Model):
    """
    External suppliers for purchase orders.
    """
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name

class Warehouse(models.Model):
    """
    Physical warehouses for inventory storage.
    """
    name = models.CharField(max_length=100)
    location = models.TextField()
    capacity = models.PositiveIntegerField(default=0)  # optional capacity

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Product sold on the platform.
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)  # optional unique identifier
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        """
        Aggregates stock across all warehouses.
        """
        return self.inventories.aggregate(total=models.Sum('quantity'))['total'] or 0

class Inventory(models.Model):
    """
    Stock quantity of a product in a specific warehouse.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name_plural = "Inventories"

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"

    def clean(self):
        if self.quantity < 0:
            raise ValidationError("Inventory quantity cannot be negative.")

class InventoryTransaction(models.Model):
    """
    Tracks all stock changes (shipsments, adjustments, etc.)
    """
    TRANSACTION_TYPES = (
        ('PURCHASE', 'Purchase Order Received'),
        ('SALE', 'Sale Order Fulfilled'),
        ('ADJUST', 'Manual Adjustment'),
        ('RETURN', 'Customer Return'),
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity_change = models.IntegerField()  # positive for in, negative for out
    reference = models.CharField(max_length=100, blank=True, null=True)  # e.g., order number
    timestamp = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.product.name} ({self.quantity_change})"

class Cart(models.Model):
    """
    Shopping cart associated with a user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    """
    Individual item in a cart.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity

class Order(models.Model):
    """
    Customer sales order.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    order_date = models.DateTimeField(auto_now_add=True)
    shipping_address = models.TextField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):
    """
    A product line within an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)  # denormalized for history
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)  # from which warehouse the stock was deducted

    @property
    def item_total(self):
        return self.price * self.quantity

class PurchaseOrder(models.Model):
    """
    Purchase order to a supplier.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    expected_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"PO #{self.id} to {self.supplier.company_name}"

class PurchaseOrderItem(models.Model):
    """
    Line item of a purchase order.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_cost * self.quantity
