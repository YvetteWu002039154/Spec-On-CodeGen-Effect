from django.contrib import admin
from .models import Supplier, Warehouse, Inventory, PurchaseOrder, PurchaseOrderItem


admin.site.register(Supplier)
admin.site.register(Warehouse)
admin.site.register(Inventory)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    raw_id_fields = ['product']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'warehouse', 'status', 'created']
    list_filter = ['status', 'supplier', 'warehouse']
    inlines = [PurchaseOrderItemInline]
    actions = ['receive_purchase_orders']

    def receive_purchase_orders(self, request, queryset):
        for po in queryset.filter(status='pending'):
            po.receive()
        self.message_user(request, f'{queryset.count()} purchase order(s) received.')
    receive_purchase_orders.short_description = 'Receive selected purchase orders'

