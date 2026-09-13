from django.contrib import admin
from .models import SalesOrder, SalesOrderItem, PurchaseOrder, PurchaseOrderItem

admin.site.register(SalesOrder)
admin.site.register(SalesOrderItem)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
