from django.db import models
from accounts.models import CustomUser
from products.models import Product
from suppliers.models import Supplier
from warehouses.models import Warehouse

class SalesOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('processing','Processing'),('shipped','Shipped'),('delivered','Delivered'),('cancelled','Cancelled')], default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_address = models.TextField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')

    def __str__(self):
        return f"Order {{self.id}} by {{self.user.username}}"

    def calculate_total(self):
        self.total = sum(item.total_price for item in self.items.all())
        self.save()

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.quantity * self.price

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('draft','Draft'),('ordered','Ordered'),('received','Received'),('cancelled','Cancelled')], default='draft')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"PO {{self.id}} from {{self.supplier.name}}"

    def calculate_total_cost(self):
        self.total_cost = sum(item.total_cost for item in self.items.all())
        self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost
