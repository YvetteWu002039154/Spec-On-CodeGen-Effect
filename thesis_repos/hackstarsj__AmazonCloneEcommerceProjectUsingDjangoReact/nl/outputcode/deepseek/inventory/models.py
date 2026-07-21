# File: inventory/models.py
from django.db import models
from products.models import Product
from warehouse.models import Warehouse

class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f'{self.product.name} - {self.quantity} @ {self.warehouse.name}'

    def needs_reorder(self):
        return self.quantity <= self.reorder_level
