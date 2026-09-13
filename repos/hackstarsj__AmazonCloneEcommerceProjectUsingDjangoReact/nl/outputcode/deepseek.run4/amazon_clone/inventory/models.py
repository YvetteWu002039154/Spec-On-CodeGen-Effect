from django.db import models
from django.core.exceptions import ValidationError
from store.models import Product

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_records')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name_plural = 'inventories'

    def __str__(self):
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}'

    @staticmethod
    def get_default_warehouse():
        return Warehouse.objects.first()

    @staticmethod
    def decrease_stock(product, warehouse, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        inv = Inventory.objects.filter(product=product, warehouse=warehouse).first()
        if not inv:
            raise ValidationError(f"No inventory for {product.name} in {warehouse.name}")
        if inv.quantity < quantity:
            raise ValidationError(f"Insufficient stock for {product.name}")
        inv.quantity -= quantity
        inv.save()

    @staticmethod
    def increase_stock(product, warehouse, quantity):
        inv, created = Inventory.objects.get_or_create(product=product, warehouse=warehouse)
        inv.quantity += quantity
        inv.save()

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'PO-{self.id} ({self.supplier.name})'

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def total_price(self):
        return self.quantity * self.unit_price

