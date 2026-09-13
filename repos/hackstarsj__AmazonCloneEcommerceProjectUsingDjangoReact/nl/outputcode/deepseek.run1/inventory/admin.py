from django.contrib import admin
from .models import Warehouse, Supplier, ProductSupplier, Stock, PurchaseOrder, PurchaseOrderItem

class StockInline(admin.TabularInline):
    model = Stock

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'manager')
    inlines = [StockInline]

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    pass

@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'cost_price', 'lead_time_days')

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'warehouse', 'status', 'total_cost', 'order_date')
    list_filter = ('status', 'supplier')
    inlines = [PurchaseOrderItemInline]
    actions = ['mark_as_received']

    def mark_as_received(self, request, queryset):
        for po in queryset.filter(status='ordered'):
            try:
                po.receive()
                self.message_user(request, f"PO #{po.id} received.")
            except ValueError as e:
                self.message_user(request, f"Error receiving PO #{po.id}: {e}", level='error')
    mark_as_received.short_description = "Mark selected purchase orders as received"

# file: static/css/base.css (optional)

