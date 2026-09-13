# =============================================
# admin.py
# =============================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Category, Supplier, Warehouse, Product,
    Inventory, InventoryTransaction, Cart, CartItem,
    Order, OrderItem, PurchaseOrder, PurchaseOrderItem
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'address', 'is_supplier')}),
    )

class InventoryInline(admin.TabularInline):
    model = Inventory
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'total_stock', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'sku')
    inlines = [InventoryInline]

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)
admin.site.register(Product, ProductAdmin)
admin.site.register(Inventory)
admin.site.register(InventoryTransaction)
admin.site.register(Cart)
admin.site.register(CartItem)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'order_date', 'total_price')
    list_filter = ('status',)
    inlines = [OrderItemInline]

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'status', 'order_date', 'total_cost')
    inlines = [PurchaseOrderItemInline]

admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(PurchaseOrderItem)
