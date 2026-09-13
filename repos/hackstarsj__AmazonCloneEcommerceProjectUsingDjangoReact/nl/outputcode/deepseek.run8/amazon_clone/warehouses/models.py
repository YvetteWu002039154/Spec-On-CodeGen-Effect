from django.db import models

class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='warehouse_stocks')
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)

    class Meta:
        unique_together = ('warehouse', 'product')

    def __str__(self):
        return f"{{self.product.name}} in {{self.warehouse.name}}: {{self.quantity}}"
