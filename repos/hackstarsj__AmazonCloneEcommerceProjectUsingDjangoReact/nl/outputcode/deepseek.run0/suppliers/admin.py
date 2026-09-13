# File: suppliers/admin.py
from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'status', 'total', 'created_at']
    list_filter = ['status']
    inlines = [PurchaseOrderItemInline]
    actions = ['mark_received']

    def mark_received(self, request, queryset):
        for po in queryset:
            po.status = 'received'
            po.save()
            # Increase stock for each item
            from inventory.models import Stock
            for item in po.items.all():
                stock, created = Stock.objects.get_or_create(product=item.product, warehouse=warehouse)  # warehouse fix
    mark_received.short_description = 'Mark selected as received and increase stock'

admin.site.register(Supplier)
