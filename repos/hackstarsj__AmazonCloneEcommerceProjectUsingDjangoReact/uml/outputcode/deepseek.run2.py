from django.db import models

class InventoryServicesWarehouse(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    pincode = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    email = models.EmailField(max_length=254)
    status = models.CharField(max_length=255)
    size = models.CharField(max_length=255)
    capacity = models.CharField(max_length=255)
    warehouse_type = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    added_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='warehouses_added_by')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='warehouses_domain')
    warehouse_manager = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_warehouses')

    class Meta:
        db_table = 'inventoryservices_warehouse'


class InventoryServicesRackAndShelvesAndFloor(models.Model):
    name = models.CharField(max_length=255)
    rack = models.CharField(max_length=255)
    shelf = models.CharField(max_length=255)
    floor = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    added_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='racks_added_by')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='racks_domain')
    warehouse = models.ForeignKey(InventoryServicesWarehouse, on_delete=models.CASCADE, related_name='racks_shelves_floors')

    class Meta:
        db_table = 'inventoryservices_rackandshelvesandfloor'


class ProductServicesCategories(models.Model):
    name = models.CharField(max_length=255)
    image = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    added_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='categories_added_by')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='categories_domain')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    class Meta:
        db_table = 'productservices_categories'


class ProductServicesProducts(models.Model):
    name = models.CharField(max_length=255)
    image = models.JSONField()
    description = models.TextField()
    specifications = models.JSONField()
    html_description = models.TextField()
    highlights = models.JSONField()
    sku = models.CharField(max_length=255)
    initial_buying_price = models.FloatField()
    initial_selling_price = models.FloatField()
    weight = models.FloatField()
    dimensions = models.CharField(max_length=255)
    uom = models.CharField(max_length=255)
    color = models.CharField(max_length=255)
    tax_percentage = models.FloatField()
    brand = models.CharField(max_length=255)
    brand_model = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    seo_title = models.CharField(max_length=255)
    seo_description = models.TextField()
    seo_keywords = models.JSONField()
    addition_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    added_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='products_added_by')
    category = models.ForeignKey(ProductServicesCategories, on_delete=models.CASCADE, related_name='products')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='products_domain')

    class Meta:
        db_table = 'productservices_products'


class OrderservicePurchaseorder(models.Model):
    po_code = models.CharField(max_length=255)
    po_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField(null=True, blank=True)
    payment_terms = models.CharField(max_length=255)
    payment_status = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_type = models.CharField(max_length=255, null=True, blank=True)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_type = models.CharField(max_length=255, null=True, blank=True)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchases')
    cancelled_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_purchases')
    created_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_purchases')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases_domain')
    last_updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_updated_purchases')
    received_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_purchases')
    returned_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='returned_purchases')
    supplier = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='supplied_purchases')
    updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_purchases')
    warehouse = models.ForeignKey(InventoryServicesWarehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')

    class Meta:
        db_table = 'orderservice_purchaseorder'


class OrderservicePurchaseorderitems(models.Model):
    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField()
    quantity_cancelled = models.IntegerField()
    quantity_returned = models.IntegerField()
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_returned = models.DecimalField(max_digits=10, decimal_places=2)
    amount_cancelled = models.DecimalField(max_digits=10, decimal_places=2)
    amount_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=255)
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_po_items')
    cancelled_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_po_items')
    created_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_po_items')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='po_items_domain')
    last_updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_updated_po_items')
    received_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_po_items')
    returned_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='returned_po_items')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductServicesProducts, on_delete=models.CASCADE, related_name='purchase_items')
    updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_po_items')

    class Meta:
        db_table = 'orderservice_purchaseorderitems'


class OrderservicePurchaseorderiteminwardedlog(models.Model):
    inwarded_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='po_inwarded_item_logs_domain')
    po_item = models.ForeignKey(OrderservicePurchaseorderitems, on_delete=models.CASCADE, related_name='inwarded_logs')

    class Meta:
        db_table = 'orderservice_purchaseorderiteminwardedlog'


class InventoryServicesInventory(models.Model):
    quantity = models.IntegerField()
    mrp = models.CharField(max_length=255)
    batch_number = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=255)
    discount_amout = models.FloatField()
    sr_no = models.CharField(max_length=255)
    mfg_date = models.DateTimeField(null=True, blank=True)
    uom = models.CharField(max_length=255)
    ptr = models.CharField(max_length=255)
    received_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    quantity_inwarded = models.IntegerField()
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    stock_status = models.CharField(max_length=255)
    inward_type = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    added_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventories_added_by')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventories_domain')
    product = models.ForeignKey(ProductServicesProducts, on_delete=models.CASCADE, related_name='inventory_items')
    purchase_order = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_items')
    purchase_order_item = models.ForeignKey(OrderservicePurchaseorderitems, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_items')
    purchase_order_item_inwarded = models.ForeignKey(OrderservicePurchaseorderiteminwardedlog, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_items')
    rack_shelf_floor = models.ForeignKey(InventoryServicesRackAndShelvesAndFloor, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_items')
    warehouse = models.ForeignKey(InventoryServicesWarehouse, on_delete=models.CASCADE, related_name='inventory_items')

    class Meta:
        db_table = 'inventoryservices_inventory'


class OrderservicePurchaseorderinwardedlog(models.Model):
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    inwarded_at = models.DateTimeField()
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='po_inwarded_logs_domain')
    inwarded_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='po_inwarded_logs_by')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.CASCADE, related_name='inwarded_logs')

    class Meta:
        db_table = 'orderservice_purchaseorderinwardedlog'


class OrderservicePurchaseorderlogs(models.Model):
    comment = models.TextField()
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    created_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='po_logs_created')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='po_logs_domain')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.CASCADE, related_name='logs')

    class Meta:
        db_table = 'orderservice_purchaseorderlogs'


class OrderserviceSalesorder(models.Model):
    so_code = models.CharField(max_length=255)
    so_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField(null=True, blank=True)
    payment_terms = models.CharField(max_length=255)
    payment_status = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_type = models.CharField(max_length=255)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_sales')
    cancelled_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_sales')
    created_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_sales')
    customer = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_domain')
    last_updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_updated_sales')
    received_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_sales')
    returned_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='returned_sales')
    # Note: po_id_id and product_id_id appear here but likely incorrectly; ignoring as they are not in relationships list. They are present in the entity, so I'll include them as nullable FKs.
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    product = models.ForeignKey(ProductServicesProducts, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_sales')

    class Meta:
        db_table = 'orderservice_salesorder'


class OrderserviceSalesorderorderitems(models.Model):
    quantity_ordered = models.IntegerField()
    quantity_delivered = models.IntegerField()
    quantity_shipped = models.IntegerField()
    quantity_cancelled = models.IntegerField()
    quantity_returned = models.IntegerField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_returned = models.DecimalField(max_digits=10, decimal_places=2)
    amount_cancelled = models.DecimalField(max_digits=10, decimal_places=2)
    amount_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_type = models.CharField(max_length=255)
    shipping_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_so_items')
    cancelled_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_so_items')
    created_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_so_items')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='so_items_domain')
    product = models.ForeignKey(ProductServicesProducts, on_delete=models.CASCADE, related_name='sales_items')
    returned_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='returned_so_items')
    shipped_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='shipped_so_items')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.CASCADE, related_name='items')
    updated_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_so_items')

    class Meta:
        db_table = 'orderservice_salesorderorderitems'


class OrderserviceSalesorderitemoutwardedlog(models.Model):
    outwarded_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='so_outwarded_item_logs_domain')
    so_item = models.ForeignKey(OrderserviceSalesorderorderitems, on_delete=models.CASCADE, related_name='outwarded_logs')

    class Meta:
        db_table = 'orderservice_salesorderitemoutwardedlog'


class OrderserviceSalesorderoutwardedlog(models.Model):
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    outwared_at = models.DateTimeField()
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='so_outwarded_logs_domain')
    outwarded_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='so_outwarded_logs_by')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.CASCADE, related_name='outwarded_logs')

    class Meta:
        db_table = 'orderservice_salesorderoutwardedlog'


class OrderserviceSalesorderlogs(models.Model):
    comment = models.TextField()
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    created_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='so_logs_created')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='so_logs_domain')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.CASCADE, related_name='logs')

    class Meta:
        db_table = 'orderservice_salesorderlogs'


class InventoryServicesInventorylog(models.Model):
    quantity = models.IntegerField()
    status = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    added_by_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs_added_by')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs_domain')
    inventory = models.ForeignKey(InventoryServicesInventory, on_delete=models.CASCADE, related_name='logs')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs')
    rack_shelf_floor = models.ForeignKey(InventoryServicesRackAndShelvesAndFloor, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs')
    warehouse = models.ForeignKey(InventoryServicesWarehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_logs')

    class Meta:
        db_table = 'inventoryservices_inventorylog'


class ProductServicesProductquestions(models.Model):
    question = models.TextField()
    answer = models.TextField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    answer_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='answers')
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='product_questions_domain')
    question_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    product = models.ForeignKey(ProductServicesProducts, on_delete=models.CASCADE, related_name='questions')

    class Meta:
        db_table = 'productservices_productquestions'


class ProductServicesProductreviews(models.Model):
    review_images = models.JSONField()
    rating = models.FloatField()
    reviews = models.TextField()
    status = models.CharField(max_length=255)
    domain_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews_domain')
    review_user = models.ForeignKey('userservices_users', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    product = models.ForeignKey(ProductServicesProducts, on_delete=models.CASCADE, related_name='reviews')

    class Meta:
        db_table = 'productservices_productreviews'


class UserservicesUsers(models.Model):
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField()
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    profile_pic = models.TextField()
    account_status = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    dob = models.DateField(null=True, blank=True)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    social_media_links = models.JSONField()
    addition_details = models.JSONField()
    language = models.CharField(max_length=50)
    departMent = models.CharField(max_length=50)
    designation = models.CharField(max_length=50)
    time_zone = models.CharField(max_length=50)
    last_login = models.DateTimeField(null=True, blank=True)
    last_device = models.CharField(max_length=50)
    last_ip = models.CharField(max_length=39)
    currency = models.CharField(max_length=50)
    domain_name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    domain_user = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='domain_users')

    class Meta:
        db_table = 'userservices_users'


class UserservicesUsershippingaddress(models.Model):
    address_type = models.CharField(max_length=50)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, related_name='shipping_addresses')

    class Meta:
        db_table = 'userservices_usershippingaddress'


class UserservicesActivitylog(models.Model):
    activity = models.TextField()
    activity_type = models.CharField(max_length=50)
    activity_date = models.DateTimeField()
    activity_ip = models.CharField(max_length=39)
    activity_device = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs_domain')
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, related_name='activity_logs')

    class Meta:
        db_table = 'userservices_activitylog'


class UserservicesModules(models.Model):
    module_name = models.CharField(max_length=50)
    module_icon = models.TextField()
    is_menu = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    module_url = models.TextField()
    display_order = models.IntegerField()
    module_description = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    class Meta:
        db_table = 'userservices_modules'


class UserservicesUserpermissions(models.Model):
    is_view = models.BooleanField(default=False)
    is_add = models.BooleanField(default=False)
    is_edit = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    module = models.ForeignKey(UserservicesModules, on_delete=models.CASCADE, related_name='user_permissions')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, related_name='permissions_given_domain')
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, related_name='user_permissions')

    class Meta:
        db_table = 'userservices_userpermissions'


class AuthGroup(models.Model):
    name = models.CharField(max_length=150)

    class Meta:
        db_table = 'auth_group'


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)
    content_type = models.ForeignKey('DjangoContentType', on_delete=models.CASCADE, related_name='permissions')

    class Meta:
        db_table = 'auth_permission'


class UserservicesUsersGroups(models.Model):
    users = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, related_name='groups_membership')
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE, related_name='users_membership')

    class Meta:
        db_table = 'userservices_users_groups'


class UserservicesUsersUserPermissions(models.Model):
    users = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, related_name='user_permissions_membership')
    permission = models.ForeignKey(AuthPermission, on_delete=models.CASCADE, related_name='users_membership')

    class Meta:
        db_table = 'userservices_users_user_permissions'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE, related_name='group_permissions_membership')
    permission = models.ForeignKey(AuthPermission, on_delete=models.CASCADE, related_name='group_permissions_membership')

    class Meta:
        db_table = 'auth_group_permissions'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        db_table = 'django_content_type'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField()
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(DjangoContentType, on_delete=models.CASCADE, related_name='admin_logs')
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, related_name='admin_logs')

    class Meta:
        db_table = 'django_admin_log'


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        db_table = 'django_session'