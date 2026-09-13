from django.db import models


class Inventory(models.Model):
    id = models.AutoField(primary_key=True)
    quantity = models.IntegerField()
    mrp = models.CharField(max_length=255)
    batch_number = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=255)
    discount_amout = models.FloatField()
    sr_no = models.CharField(max_length=255)
    mfg_date = models.DateTimeField()
    uom = models.CharField(max_length=255)
    ptr = models.CharField(max_length=255)
    received_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    quantity_inwarded = models.IntegerField()
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    stock_status = models.CharField(max_length=255)
    inward_type = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    added_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='added_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    product = models.ForeignKey(
        'productservices.Product',
        on_delete=models.CASCADE,
        db_column='product_id_id',
        related_name='inventories',
    )
    purchase_order = models.ForeignKey(
        'orderservice.PurchaseOrder',
        on_delete=models.CASCADE,
        db_column='purchase_order_id_id',
        related_name='inventories',
    )
    purchase_order_item = models.ForeignKey(
        'orderservice.PurchaseOrderItem',
        on_delete=models.CASCADE,
        db_column='purchase_order_item_id_id',
        related_name='inventories',
    )
    po_item_inwarded = models.ForeignKey(
        'orderservice.PurchaseOrderItemInwardedLog',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='purchase_order_item_inwarded_item_id_id',
        related_name='inventories',
    )
    rack_shelf_floor = models.ForeignKey(
        'inventoryservices.RackShelfFloor',
        on_delete=models.CASCADE,
        db_column='rack_shelf_floor_id_id',
        related_name='inventories',
    )
    warehouse = models.ForeignKey(
        'inventoryservices.Warehouse',
        on_delete=models.CASCADE,
        db_column='warehouse_id_id',
        related_name='inventories',
    )

    class Meta:
        db_table = 'inventoryservices_inventory'
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'


class InventoryLog(models.Model):
    id = models.AutoField(primary_key=True)
    quantity = models.IntegerField()
    status = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    added_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='added_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        db_column='inventory_id_id',
        related_name='logs',
    )
    po = models.ForeignKey(
        'orderservice.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='po_id_id',
        related_name='inventory_logs',
    )
    so = models.ForeignKey(
        'orderservice.SalesOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='so_id_id',
        related_name='inventory_logs',
    )
    rack_shelf_floor = models.ForeignKey(
        'inventoryservices.RackShelfFloor',
        on_delete=models.CASCADE,
        db_column='rack_shelf_floor_id_id',
        related_name='inventory_logs',
    )
    warehouse = models.ForeignKey(
        'inventoryservices.Warehouse',
        on_delete=models.CASCADE,
        db_column='warehouse_id_id',
        related_name='inventory_logs',
    )

    class Meta:
        db_table = 'inventoryservices_inventorylog'
        verbose_name = 'Inventory Log'
        verbose_name_plural = 'Inventory Logs'


class RackShelfFloor(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    rack = models.CharField(max_length=255)
    shelf = models.CharField(max_length=255)
    floor = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    added_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='added_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    warehouse = models.ForeignKey(
        'inventoryservices.Warehouse',
        on_delete=models.CASCADE,
        db_column='warehouse_id_id',
        related_name='rack_shelf_floors',
    )

    class Meta:
        db_table = 'inventoryservices_rackandshelvesandfloor'
        verbose_name = 'Rack Shelf Floor'
        verbose_name_plural = 'Rack Shelves & Floors'


class Warehouse(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    pincode = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    email = models.CharField(max_length=254)
    status = models.CharField(max_length=255)
    size = models.CharField(max_length=255)
    capacity = models.CharField(max_length=255)
    warehouse_type = models.CharField(max_length=255)
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    added_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='added_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    warehouse_manager = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='warehouse_manager_id',
        related_name='managed_warehouses',
    )

    class Meta:
        db_table = 'inventoryservices_warehouse'
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'


class PurchaseOrder(models.Model):
    id = models.AutoField(primary_key=True)
    po_code = models.CharField(max_length=255)
    po_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField()
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
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='approved_by_user_id_id',
        related_name='+',
    )
    cancelled_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='cancelled_by_user_id_id',
        related_name='+',
    )
    created_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='created_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    last_updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='last_updated_by_user_id_id',
        related_name='+',
    )
    received_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='received_by_user_id_id',
        related_name='+',
    )
    returned_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='returned_by_user_id_id',
        related_name='+',
    )
    supplier = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='supplier_id_id',
        related_name='supplied_orders',
    )
    updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='updated_by_user_id_id',
        related_name='+',
    )
    warehouse = models.ForeignKey(
        'inventoryservices.Warehouse',
        on_delete=models.CASCADE,
        db_column='warehouse_id_id',
        related_name='purchase_orders',
    )

    class Meta:
        db_table = 'orderservice_purchaseorder'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'


class PurchaseOrderItem(models.Model):
    id = models.AutoField(primary_key=True)
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
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='approved_by_user_id_id',
        related_name='+',
    )
    cancelled_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='cancelled_by_user_id_id',
        related_name='+',
    )
    created_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='created_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    last_updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='last_updated_by_user_id_id',
        related_name='+',
    )
    received_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='received_by_user_id_id',
        related_name='+',
    )
    returned_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='returned_by_user_id_id',
        related_name='+',
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        db_column='po_id_id',
        related_name='items',
    )
    product = models.ForeignKey(
        'productservices.Product',
        on_delete=models.CASCADE,
        db_column='product_id_id',
        related_name='purchase_order_items',
    )
    updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='updated_by_user_id_id',
        related_name='+',
    )

    class Meta:
        db_table = 'orderservice_purchaseorderitems'
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'


class PurchaseOrderLog(models.Model):
    id = models.AutoField(primary_key=True)
    comment = models.TextField()
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    created_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='created_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        db_column='po_id_id',
        related_name='logs',
    )

    class Meta:
        db_table = 'orderservice_purchaseorderlogs'
        verbose_name = 'Purchase Order Log'
        verbose_name_plural = 'Purchase Order Logs'


class PurchaseOrderInwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    inwarded_at = models.DateTimeField()
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    inwarded_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='inwarded_by_user_id_id',
        related_name='+',
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        db_column='po_id_id',
        related_name='inwarded_logs',
    )

    class Meta:
        db_table = 'orderservice_purchaseorderinwardedlog'
        verbose_name = 'Purchase Order Inwarded Log'
        verbose_name_plural = 'Purchase Order Inwarded Logs'


class PurchaseOrderItemInwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
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

    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.CASCADE,
        db_column='po_item_id_id',
        related_name='inwarded_logs',
    )

    class Meta:
        db_table = 'orderservice_purchaseorderiteminwardedlog'
        verbose_name = 'Purchase Order Item Inwarded Log'
        verbose_name_plural = 'Purchase Order Item Inwarded Logs'


class SalesOrder(models.Model):
    id = models.AutoField(primary_key=True)
    so_code = models.CharField(max_length=255)
    so_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField()
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
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='approved_by_user_id_id',
        related_name='+',
    )
    cancelled_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='cancelled_by_user_id_id',
        related_name='+',
    )
    created_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='created_by_user_id_id',
        related_name='+',
    )
    customer = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='customer_id_id',
        related_name='sales_orders',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    last_updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='last_updated_by_user_id_id',
        related_name='+',
    )
    received_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='received_by_user_id_id',
        related_name='+',
    )
    returned_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='returned_by_user_id_id',
        related_name='+',
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='po_id_id',
        related_name='sales_orders',
    )
    product = models.ForeignKey(
        'productservices.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='product_id_id',
        related_name='sales_orders',
    )
    updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='updated_by_user_id_id',
        related_name='+',
    )

    class Meta:
        db_table = 'orderservice_salesorder'
        verbose_name = 'Sales Order'
        verbose_name_plural = 'Sales Orders'


class SalesOrderItem(models.Model):
    id = models.AutoField(primary_key=True)
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
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    approved_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='approved_by_user_id_id',
        related_name='+',
    )
    cancelled_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='cancelled_by_user_id_id',
        related_name='+',
    )
    created_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='created_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    product = models.ForeignKey(
        'productservices.Product',
        on_delete=models.CASCADE,
        db_column='product_id_id',
        related_name='sales_order_items',
    )
    returned_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='returned_by_user_id_id',
        related_name='+',
    )
    shipped_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='shipped_by_user_id_id',
        related_name='+',
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        db_column='so_id_id',
        related_name='items',
    )
    updated_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='updated_by_user_id_id',
        related_name='+',
    )

    class Meta:
        db_table = 'orderservice_salesorderorderitems'
        verbose_name = 'Sales Order Item'
        verbose_name_plural = 'Sales Order Items'


class SalesOrderLog(models.Model):
    id = models.AutoField(primary_key=True)
    comment = models.TextField()
    additional_details = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    created_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='created_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        db_column='so_id_id',
        related_name='logs',
    )

    class Meta:
        db_table = 'orderservice_salesorderlogs'
        verbose_name = 'Sales Order Log'
        verbose_name_plural = 'Sales Order Logs'


class SalesOrderOutwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    outwared_at = models.DateTimeField()
    additional_details = models.JSONField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    outwarded_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='outwarded_by_user_id_id',
        related_name='+',
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        db_column='so_id_id',
        related_name='outwarded_logs',
    )

    class Meta:
        db_table = 'orderservice_salesorderoutwardedlog'
        verbose_name = 'Sales Order Outwarded Log'
        verbose_name_plural = 'Sales Order Outwarded Logs'


class SalesOrderItemOutwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
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

    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    so_item = models.ForeignKey(
        SalesOrderItem,
        on_delete=models.CASCADE,
        db_column='so_item_id_id',
        related_name='outwarded_logs',
    )

    class Meta:
        db_table = 'orderservice_salesorderitemoutwardedlog'
        verbose_name = 'Sales Order Item Outwarded Log'
        verbose_name_plural = 'Sales Order Item Outwarded Logs'


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    image = models.TextField()
    description = models.TextField()
    display_order = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    added_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='added_by_user_id_id',
        related_name='+',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='parent_id_id',
        related_name='children',
    )

    class Meta:
        db_table = 'productservices_categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Product(models.Model):
    id = models.AutoField(primary_key=True)
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

    added_by_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='added_by_user_id_id',
        related_name='+',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        db_column='category_id_id',
        related_name='products',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )

    class Meta:
        db_table = 'productservices_products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'


class ProductQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    question = models.TextField()
    answer = models.TextField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    answer_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='answer_user_id_id',
        related_name='answered_questions',
    )
    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    question_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='question_user_id_id',
        related_name='questions',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column='product_id_id',
        related_name='questions',
    )

    class Meta:
        db_table = 'productservices_productquestions'
        verbose_name = 'Product Question'
        verbose_name_plural = 'Product Questions'


class ProductReview(models.Model):
    id = models.AutoField(primary_key=True)
    review_images = models.JSONField()
    rating = models.FloatField()
    reviews = models.TextField()
    status = models.CharField(max_length=255)

    domain_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    review_user = models.ForeignKey(
        'userservices.User',
        on_delete=models.CASCADE,
        db_column='review_user_id_id',
        related_name='reviews',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column='product_id_id',
        related_name='reviews',
    )

    class Meta:
        db_table = 'productservices_productreviews'
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews'


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_superuser = models.BooleanField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
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

    domain_user = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='domain_user_id_id',
        related_name='domain_users',
    )

    # Many-to-many relationships will be managed through explicit join tables.
    # We'll define the reverse accessors here but actual links are in UsersGroups, UsersUserPermissions.

    class Meta:
        db_table = 'userservices_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class UserShippingAddress(models.Model):
    id = models.AutoField(primary_key=True)
    address_type = models.CharField(max_length=50)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='shipping_addresses',
    )

    class Meta:
        db_table = 'userservices_usershippingaddress'
        verbose_name = 'User Shipping Address'
        verbose_name_plural = 'User Shipping Addresses'


class ActivityLog(models.Model):
    id = models.AutoField(primary_key=True)
    activity = models.TextField()
    activity_type = models.CharField(max_length=50)
    activity_date = models.DateTimeField()
    activity_ip = models.CharField(max_length=39)
    activity_device = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='+',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='activity_logs',
    )

    class Meta:
        db_table = 'userservices_activitylog'
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'


class Module(models.Model):
    id = models.AutoField(primary_key=True)
    module_name = models.CharField(max_length=50)
    module_icon = models.TextField()
    is_menu = models.BooleanField()
    is_active = models.BooleanField()
    module_url = models.TextField()
    display_order = models.IntegerField()
    module_description = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='parent_id_id',
        related_name='children',
    )

    class Meta:
        db_table = 'userservices_modules'
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'


class UserPermission(models.Model):
    id = models.AutoField(primary_key=True)
    is_view = models.BooleanField()
    is_add = models.BooleanField()
    is_edit = models.BooleanField()
    is_delete = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        db_column='module_id_id',
        related_name='user_permissions',
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='domain_user_id_id',
        related_name='domain_permissions',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='permissions',
    )

    class Meta:
        db_table = 'userservices_userpermissions'
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'


class UsersGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    users = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='users_id',
        related_name='users_groups',
    )
    group = models.ForeignKey(
        'auth_group',
        on_delete=models.CASCADE,
        db_column='group_id',
        related_name='users_groups',
    )

    class Meta:
        db_table = 'userservices_users_groups'
        verbose_name = 'Users Group'
        verbose_name_plural = 'Users Groups'


class UsersUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    users = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='users_id',
        related_name='users_user_permissions',
    )
    permission = models.ForeignKey(
        'auth_permission',
        on_delete=models.CASCADE,
        db_column='permission_id',
        related_name='users_user_permissions',
    )

    class Meta:
        db_table = 'userservices_users_user_permissions'
        verbose_name = 'Users User Permission'
        verbose_name_plural = 'Users User Permissions'


class AdminLog(models.Model):
    id = models.AutoField(primary_key=True)
    action_time = models.DateTimeField()
    object_id = models.TextField()
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()

    content_type = models.ForeignKey(
        'django_content_type',
        on_delete=models.CASCADE,
        db_column='content_type_id',
        related_name='admin_logs',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='admin_actions',
    )

    class Meta:
        db_table = 'django_admin_log'
        verbose_name = 'Admin Log'
        verbose_name_plural = 'Admin Logs'


class Migrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        db_table = 'django_migrations'
        verbose_name = 'Migration'
        verbose_name_plural = 'Migrations'


class ContentType(models.Model):
    id = models.AutoField(primary_key=True)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        db_table = 'django_content_type'
        verbose_name = 'Content Type'
        verbose_name_plural = 'Content Types'


class Session(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        db_table = 'django_session'
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'


class AuthGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)

    class Meta:
        db_table = 'auth_group'
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(
        AuthGroup,
        on_delete=models.CASCADE,
        db_column='group_id',
        related_name='group_permissions',
    )
    permission = models.ForeignKey(
        'auth_permission',
        on_delete=models.CASCADE,
        db_column='permission_id',
        related_name='group_permissions',
    )

    class Meta:
        db_table = 'auth_group_permissions'
        verbose_name = 'Group Permission'
        verbose_name_plural = 'Group Permissions'


class AuthPermission(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        db_column='content_type_id',
        related_name='permissions',
    )

    class Meta:
        db_table = 'auth_permission'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'