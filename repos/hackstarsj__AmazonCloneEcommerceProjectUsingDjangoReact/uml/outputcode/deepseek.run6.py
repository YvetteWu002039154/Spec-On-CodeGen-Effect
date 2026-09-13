from django.db import models

class InventoryservicesWarehouse(models.Model):
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
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    added_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='warehouse_added_by',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='warehouse_domain_user',
        db_column='domain_user_id_id'
    )
    warehouse_manager = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_warehouses',
        db_column='warehouse_manager_id'
    )

    class Meta:
        db_table = 'inventoryservices_warehouse'


class InventoryservicesRackandshelvesandfloor(models.Model):
    name = models.CharField(max_length=255)
    rack = models.CharField(max_length=255)
    shelf = models.CharField(max_length=255)
    floor = models.CharField(max_length=255)
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    added_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='rack_added_by',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='rack_domain_user',
        db_column='domain_user_id_id'
    )
    warehouse = models.ForeignKey(
        InventoryservicesWarehouse,
        on_delete=models.CASCADE,
        related_name='racks_shelves_floors',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'inventoryservices_rackandshelvesandfloor'


class OrderservicePurchaseorder(models.Model):
    po_code = models.CharField(max_length=255)
    po_date = models.DateTimeField()
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
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_approved_by',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_cancelled_by',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_created_by',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_domain_user',
        db_column='domain_user_id_id'
    )
    last_updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_last_updated_by',
        db_column='last_updated_by_user_id_id'
    )
    received_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_received_by',
        db_column='received_by_user_id_id'
    )
    returned_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_returned_by',
        db_column='returned_by_user_id_id'
    )
    supplier = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplied_purchase_orders',
        db_column='supplier_id_id'
    )
    updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_updated_by',
        db_column='updated_by_user_id_id'
    )
    warehouse = models.ForeignKey(
        InventoryservicesWarehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorder'


class ProductservicesProducts(models.Model):
    name = models.CharField(max_length=255)
    image = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict)
    html_description = models.TextField(blank=True)
    highlights = models.JSONField(default=dict)
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
    seo_description = models.TextField(blank=True)
    seo_keywords = models.JSONField(default=dict)
    addition_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    added_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_added_by',
        db_column='added_by_user_id_id'
    )
    category = models.ForeignKey(
        'productservices_categories',
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
        db_column='category_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_domain_user',
        db_column='domain_user_id_id'
    )

    class Meta:
        db_table = 'productservices_products'


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
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_approved_by',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_cancelled_by',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_created_by',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_domain_user',
        db_column='domain_user_id_id'
    )
    last_updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_last_updated_by',
        db_column='last_updated_by_user_id_id'
    )
    received_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_received_by',
        db_column='received_by_user_id_id'
    )
    returned_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_returned_by',
        db_column='returned_by_user_id_id'
    )
    po = models.ForeignKey(
        OrderservicePurchaseorder,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='po_id_id'
    )
    product = models.ForeignKey(
        ProductservicesProducts,
        on_delete=models.CASCADE,
        related_name='purchase_order_items',
        db_column='product_id_id'
    )
    updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_item_updated_by',
        db_column='updated_by_user_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderitems'


class OrderservicePurchaseorderinwardedlog(models.Model):
    invoice_path = models.TextField(blank=True)
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    inwarded_at = models.DateTimeField(null=True, blank=True)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='po_inwarded_log_domain',
        db_column='domain_user_id_id'
    )
    inwarded_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='po_inwarded_by',
        db_column='inwarded_by_user_id_id'
    )
    po = models.ForeignKey(
        OrderservicePurchaseorder,
        on_delete=models.CASCADE,
        related_name='inwarded_logs',
        db_column='po_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderinwardedlog'


class OrderservicePurchaseorderiteminwardedlog(models.Model):
    inwarded_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='po_item_inwarded_log_domain',
        db_column='domain_user_id_id'
    )
    po_item = models.ForeignKey(
        OrderservicePurchaseorderitems,
        on_delete=models.CASCADE,
        related_name='inwarded_logs',
        db_column='po_item_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderiteminwardedlog'


class InventoryservicesInventory(models.Model):
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
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    added_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_added_by',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_domain_user',
        db_column='domain_user_id_id'
    )
    product = models.ForeignKey(
        ProductservicesProducts,
        on_delete=models.CASCADE,
        related_name='inventory_items',
        db_column='product_id_id'
    )
    purchase_order = models.ForeignKey(
        OrderservicePurchaseorder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='purchase_order_id_id'
    )
    purchase_order_item = models.ForeignKey(
        OrderservicePurchaseorderitems,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='purchase_order_item_id_id'
    )
    purchase_order_item_inwarded_item = models.ForeignKey(
        OrderservicePurchaseorderiteminwardedlog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='purchase_order_item_inwarded_item_id_id'
    )
    rack_shelf_floor = models.ForeignKey(
        InventoryservicesRackandshelvesandfloor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='rack_shelf_floor_id_id'
    )
    warehouse = models.ForeignKey(
        InventoryservicesWarehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'inventoryservices_inventory'


class InventoryservicesInventorylog(models.Model):
    quantity = models.IntegerField()
    status = models.CharField(max_length=255)
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    added_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_log_added_by',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_log_domain_user',
        db_column='domain_user_id_id'
    )
    inventory = models.ForeignKey(
        InventoryservicesInventory,
        on_delete=models.CASCADE,
        related_name='logs',
        db_column='inventory_id_id'
    )
    po = models.ForeignKey(
        OrderservicePurchaseorder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='po_id_id'
    )
    so = models.ForeignKey(
        'orderservice_salesorder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='so_id_id'
    )
    rack_shelf_floor = models.ForeignKey(
        InventoryservicesRackandshelvesandfloor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='rack_shelf_floor_id_id'
    )
    warehouse = models.ForeignKey(
        InventoryservicesWarehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'inventoryservices_inventorylog'


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
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_approved_by',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_cancelled_by',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_created_by',
        db_column='created_by_user_id_id'
    )
    customer = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders_as_customer',
        db_column='customer_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_domain_user',
        db_column='domain_user_id_id'
    )
    last_updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_last_updated_by',
        db_column='last_updated_by_user_id_id'
    )
    received_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_received_by',
        db_column='received_by_user_id_id'
    )
    returned_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_returned_by',
        db_column='returned_by_user_id_id'
    )
    po = models.ForeignKey(
        OrderservicePurchaseorder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
        db_column='po_id_id'
    )
    product = models.ForeignKey(
        ProductservicesProducts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
        db_column='product_id_id'
    )
    updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_updated_by',
        db_column='updated_by_user_id_id'
    )

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
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    # discount_type already defined; second occurrence seems redundant, but we keep one.
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_approved_by',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_cancelled_by',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_created_by',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_domain_user',
        db_column='domain_user_id_id'
    )
    product = models.ForeignKey(
        ProductservicesProducts,
        on_delete=models.CASCADE,
        related_name='sales_order_items',
        db_column='product_id_id'
    )
    returned_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_returned_by',
        db_column='returned_by_user_id_id'
    )
    shipped_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_shipped_by',
        db_column='shipped_by_user_id_id'
    )
    so = models.ForeignKey(
        OrderserviceSalesorder,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='so_id_id'
    )
    updated_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='so_item_updated_by',
        db_column='updated_by_user_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderorderitems'


class OrderserviceSalesorderoutwardedlog(models.Model):
    invoice_path = models.TextField(blank=True)
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    outwared_at = models.DateTimeField(null=True, blank=True)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='so_outwarded_log_domain',
        db_column='domain_user_id_id'
    )
    outwarded_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='so_outwarded_by',
        db_column='outwarded_by_user_id_id'
    )
    so = models.ForeignKey(
        OrderserviceSalesorder,
        on_delete=models.CASCADE,
        related_name='outwarded_logs',
        db_column='so_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderoutwardedlog'


class OrderserviceSalesorderitemoutwardedlog(models.Model):
    outwarded_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='so_item_outwarded_log_domain',
        db_column='domain_user_id_id'
    )
    so_item = models.ForeignKey(
        OrderserviceSalesorderorderitems,
        on_delete=models.CASCADE,
        related_name='outwarded_logs',
        db_column='so_item_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderitemoutwardedlog'


class ProductservicesCategories(models.Model):
    name = models.CharField(max_length=255)
    image = models.TextField(blank=True)
    description = models.TextField(blank=True)
    display_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    added_by_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='category_added_by',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='category_domain_user',
        db_column='domain_user_id_id'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        db_column='parent_id_id'
    )

    class Meta:
        db_table = 'productservices_categories'


class ProductservicesProductquestions(models.Model):
    question = models.TextField()
    answer = models.TextField(blank=True)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    answer_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='question_answers',
        db_column='answer_user_id_id'
    )
    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_questions_domain',
        db_column='domain_user_id_id'
    )
    question_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions_asked',
        db_column='question_user_id_id'
    )
    product = models.ForeignKey(
        ProductservicesProducts,
        on_delete=models.CASCADE,
        related_name='questions',
        db_column='product_id_id'
    )

    class Meta:
        db_table = 'productservices_productquestions'


class ProductservicesProductreviews(models.Model):
    review_images = models.JSONField(default=dict)
    rating = models.FloatField()
    reviews = models.TextField()
    status = models.CharField(max_length=255)

    domain_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_reviews_domain',
        db_column='domain_user_id_id'
    )
    review_user = models.ForeignKey(
        'userservices_users',
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_reviews',
        db_column='review_user_id_id'
    )
    product = models.ForeignKey(
        ProductservicesProducts,
        on_delete=models.CASCADE,
        related_name='reviews',
        db_column='product_id_id'
    )

    class Meta:
        db_table = 'productservices_productreviews'


class UserservicesUsers(models.Model):
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    profile_pic = models.TextField(blank=True)
    account_status = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    dob = models.DateField(null=True, blank=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)
    social_media_links = models.JSONField(default=dict)
    addition_details = models.JSONField(default=dict)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    domain_user = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='domain_users',
        db_column='domain_user_id_id'
    )

    # Django auth fields not present here since it's a custom user model,
    # but we are not inheriting AbstractUser; just regular model.

    class Meta:
        db_table = 'userservices_users'


class UserservicesUsershippingaddress(models.Model):
    address_type = models.CharField(max_length=50)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.CASCADE,
        related_name='shipping_addresses',
        db_column='user_id'
    )

    class Meta:
        db_table = 'userservices_usershippingaddress'


class UserservicesActivitylog(models.Model):
    activity = models.TextField()
    activity_type = models.CharField(max_length=50)
    activity_date = models.DateTimeField()
    activity_ip = models.CharField(max_length=39)
    activity_device = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    domain_user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_log_domain',
        db_column='domain_user_id_id'
    )
    user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        db_column='user_id'
    )

    class Meta:
        db_table = 'userservices_activitylog'


class UserservicesModules(models.Model):
    module_name = models.CharField(max_length=50)
    module_icon = models.TextField(blank=True)
    is_menu = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    module_url = models.TextField(blank=True)
    display_order = models.IntegerField()
    module_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        db_column='parent_id_id'
    )

    class Meta:
        db_table = 'userservices_modules'


class UserservicesUserpermissions(models.Model):
    is_view = models.BooleanField(default=False)
    is_add = models.BooleanField(default=False)
    is_edit = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    module = models.ForeignKey(
        UserservicesModules,
        on_delete=models.CASCADE,
        related_name='user_permissions',
        db_column='module_id_id'
    )
    domain_user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.SET_NULL,
        null=True,
        related_name='user_permissions_domain',
        db_column='domain_user_id_id'
    )
    user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.CASCADE,
        related_name='user_permissions',
        db_column='user_id'
    )

    class Meta:
        db_table = 'userservices_userpermissions'


class UserservicesUsersGroups(models.Model):
    users = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.CASCADE,
        db_column='users_id'
    )
    group = models.ForeignKey(
        'auth_group',
        on_delete=models.CASCADE,
        db_column='group_id'
    )

    class Meta:
        db_table = 'userservices_users_groups'


class UserservicesUsersUserPermissions(models.Model):
    users = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.CASCADE,
        db_column='users_id'
    )
    permission = models.ForeignKey(
        'auth_permission',
        on_delete=models.CASCADE,
        db_column='permission_id'
    )

    class Meta:
        db_table = 'userservices_users_user_permissions'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField(auto_now_add=True)
    object_id = models.TextField(blank=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField(blank=True)

    content_type = models.ForeignKey(
        'django_content_type',
        on_delete=models.CASCADE,
        related_name='admin_logs',
        db_column='content_type_id'
    )
    user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.CASCADE,
        related_name='admin_logs',
        db_column='user_id'
    )

    class Meta:
        db_table = 'django_admin_log'


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'django_migrations'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        db_table = 'django_content_type'


class DjangoSession(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        db_table = 'django_session'


class AuthGroup(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(
        AuthGroup,
        on_delete=models.CASCADE,
        db_column='group_id'
    )
    permission = models.ForeignKey(
        'auth_permission',
        on_delete=models.CASCADE,
        db_column='permission_id'
    )

    class Meta:
        db_table = 'auth_group_permissions'


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)

    content_type = models.ForeignKey(
        DjangoContentType,
        on_delete=models.CASCADE,
        related_name='permissions',
        db_column='content_type_id'
    )

    class Meta:
        db_table = 'auth_permission'


# Additional logs models that were missing explicit references but implied by the diagram
class OrderservicePurchaseorderlogs(models.Model):
    comment = models.TextField(blank=True)
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by_user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.SET_NULL,
        null=True,
        related_name='po_logs_created',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.SET_NULL,
        null=True,
        related_name='po_logs_domain',
        db_column='domain_user_id_id'
    )
    po = models.ForeignKey(
        OrderservicePurchaseorder,
        on_delete=models.CASCADE,
        related_name='logs',
        db_column='po_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderlogs'


class OrderserviceSalesorderlogs(models.Model):
    comment = models.TextField(blank=True)
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by_user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.SET_NULL,
        null=True,
        related_name='so_logs_created',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        UserservicesUsers,
        on_delete=models.SET_NULL,
        null=True,
        related_name='so_logs_domain',
        db_column='domain_user_id_id'
    )
    so = models.ForeignKey(
        OrderserviceSalesorder,
        on_delete=models.CASCADE,
        related_name='logs',
        db_column='so_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderlogs'