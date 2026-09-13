from django.db import models
from django.db.models import JSONField
from decimal import Decimal
import datetime


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
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
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    social_media_links = JSONField(default=dict)
    addition_details = JSONField(default=dict)
    language = models.CharField(max_length=50)
    department = models.CharField(max_length=50)
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
    domain_user_id = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='domain_children'
    )

    class Meta:
        db_table = 'userservices_users'


class Warehouse(models.Model):
    id = models.AutoField(primary_key=True)
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
    additional_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='added_warehouses',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_warehouses',
        db_column='domain_user_id_id'
    )
    warehouse_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_warehouses',
        db_column='warehouse_manager_id'
    )

    class Meta:
        db_table = 'inventoryservices_warehouse'


class RackAndShelvesAndFloor(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    rack = models.CharField(max_length=255)
    shelf = models.CharField(max_length=255)
    floor = models.CharField(max_length=255)
    additional_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='added_racks',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_racks',
        db_column='domain_user_id_id'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='rack_shelf_floors',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'inventoryservices_rackandshelvesandfloor'


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    image = models.TextField()
    description = models.TextField()
    display_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='added_categories',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_categories',
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


class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    image = JSONField(default=dict)
    description = models.TextField()
    specifications = JSONField(default=dict)
    html_description = models.TextField()
    highlights = JSONField(default=dict)
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
    seo_keywords = JSONField(default=dict)
    addition_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='added_products',
        db_column='added_by_user_id_id'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        db_column='category_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_products',
        db_column='domain_user_id_id'
    )

    class Meta:
        db_table = 'productservices_products'


class PurchaseOrder(models.Model):
    id = models.AutoField(primary_key=True)
    po_code = models.CharField(max_length=255)
    po_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField()
    payment_terms = models.CharField(max_length=255)
    payment_status = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_type = models.CharField(max_length=255)
    shipping_tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    shipping_tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_orders',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_purchase_orders',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_purchase_orders',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_purchase_orders',
        db_column='domain_user_id_id'
    )
    last_updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_updated_purchase_orders',
        db_column='last_updated_by_user_id_id'
    )
    received_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_purchase_orders',
        db_column='received_by_user_id_id'
    )
    returned_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returned_purchase_orders',
        db_column='returned_by_user_id_id'
    )
    supplier = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='supplier_purchase_orders',
        db_column='supplier_id_id'
    )
    updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_purchase_orders',
        db_column='updated_by_user_id_id'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='purchase_orders',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorder'


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
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_po_items',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_po_items',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_po_items',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_po_items',
        db_column='domain_user_id_id'
    )
    last_updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_updated_po_items',
        db_column='last_updated_by_user_id_id'
    )
    received_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_po_items',
        db_column='received_by_user_id_id'
    )
    returned_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returned_po_items',
        db_column='returned_by_user_id_id'
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='po_id_id'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='purchase_order_items',
        db_column='product_id_id'
    )
    updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_po_items',
        db_column='updated_by_user_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderitems'


class PurchaseOrderLog(models.Model):
    id = models.AutoField(primary_key=True)
    comment = models.TextField()
    additional_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='po_logs',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_po_logs',
        db_column='domain_user_id_id'
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='logs',
        db_column='po_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderlogs'


class PurchaseOrderInwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    inwarded_at = models.DateTimeField()
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_po_inwarded_logs',
        db_column='domain_user_id_id'
    )
    inwarded_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inwarded_po_logs',
        db_column='inwarded_by_user_id_id'
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='inwarded_logs',
        db_column='po_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderinwardedlog'


class PurchaseOrderItemInwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
    inwarded_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_po_item_inwarded_logs',
        db_column='domain_user_id_id'
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.CASCADE,
        related_name='inwarded_logs',
        db_column='po_item_id_id'
    )

    class Meta:
        db_table = 'orderservice_purchaseorderiteminwardedlog'


class SalesOrder(models.Model):
    id = models.AutoField(primary_key=True)
    so_code = models.CharField(max_length=255)
    so_date = models.DateTimeField()
    expected_delivery_date = models.DateTimeField()
    payment_terms = models.CharField(max_length=255)
    payment_status = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_type = models.CharField(max_length=255)
    shipping_tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    shipping_tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_sales_orders',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_sales_orders',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_sales_orders',
        db_column='created_by_user_id_id'
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='customer_sales_orders',
        db_column='customer_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_sales_orders',
        db_column='domain_user_id_id'
    )
    last_updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_updated_sales_orders',
        db_column='last_updated_by_user_id_id'
    )
    received_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_sales_orders',
        db_column='received_by_user_id_id'
    )
    returned_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returned_sales_orders',
        db_column='returned_by_user_id_id'
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
        db_column='po_id_id'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders',
        db_column='product_id_id'
    )
    updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_sales_orders',
        db_column='updated_by_user_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorder'


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
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_type = models.CharField(max_length=255)
    shipping_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cancelled_tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_so_items',
        db_column='approved_by_user_id_id'
    )
    cancelled_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_so_items',
        db_column='cancelled_by_user_id_id'
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_so_items',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_so_items',
        db_column='domain_user_id_id'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='sales_order_items',
        db_column='product_id_id'
    )
    returned_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returned_so_items',
        db_column='returned_by_user_id_id'
    )
    shipped_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipped_so_items',
        db_column='shipped_by_user_id_id'
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='so_id_id'
    )
    updated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_so_items',
        db_column='updated_by_user_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderorderitems'


class SalesOrderLog(models.Model):
    id = models.AutoField(primary_key=True)
    comment = models.TextField()
    additional_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='so_logs',
        db_column='created_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_so_logs',
        db_column='domain_user_id_id'
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='logs',
        db_column='so_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderlogs'


class SalesOrderOutwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    outwared_at = models.DateTimeField()
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_so_outwarded_logs',
        db_column='domain_user_id_id'
    )
    outwarded_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='outwarded_so_logs',
        db_column='outwarded_by_user_id_id'
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='outwarded_logs',
        db_column='so_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderoutwardedlog'


class SalesOrderItemOutwardedLog(models.Model):
    id = models.AutoField(primary_key=True)
    outwarded_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=255)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    additional_details = JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_so_item_outwarded_logs',
        db_column='domain_user_id_id'
    )
    so_item = models.ForeignKey(
        SalesOrderItem,
        on_delete=models.CASCADE,
        related_name='outwarded_logs',
        db_column='so_item_id_id'
    )

    class Meta:
        db_table = 'orderservice_salesorderitemoutwardedlog'


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
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    stock_status = models.CharField(max_length=255)
    inward_type = models.CharField(max_length=255)
    additional_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='added_inventories',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_inventories',
        db_column='domain_user_id_id'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventories',
        db_column='product_id_id'
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='purchase_order_id_id'
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='purchase_order_item_id_id'
    )
    purchase_order_item_inwarded_item = models.ForeignKey(
        PurchaseOrderItemInwardedLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='purchase_order_item_inwarded_item_id_id'
    )
    rack_shelf_floor = models.ForeignKey(
        RackAndShelvesAndFloor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        db_column='rack_shelf_floor_id_id'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='inventories',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'inventoryservices_inventory'


class InventoryLog(models.Model):
    id = models.AutoField(primary_key=True)
    quantity = models.IntegerField()
    status = models.CharField(max_length=255)
    additional_details = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='added_inventory_logs',
        db_column='added_by_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_inventory_logs',
        db_column='domain_user_id_id'
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='logs',
        db_column='inventory_id_id'
    )
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='po_id_id'
    )
    so = models.ForeignKey(
        SalesOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='so_id_id'
    )
    rack_shelf_floor = models.ForeignKey(
        RackAndShelvesAndFloor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs',
        db_column='rack_shelf_floor_id_id'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='inventory_logs',
        db_column='warehouse_id_id'
    )

    class Meta:
        db_table = 'inventoryservices_inventorylog'


class ProductQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    question = models.TextField()
    answer = models.TextField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    answer_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='answered_questions',
        db_column='answer_user_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_product_questions',
        db_column='domain_user_id_id'
    )
    question_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='asked_questions',
        db_column='question_user_id_id'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='questions',
        db_column='product_id_id'
    )

    class Meta:
        db_table = 'productservices_productquestions'


class ProductReview(models.Model):
    id = models.AutoField(primary_key=True)
    review_images = JSONField(default=dict)
    rating = models.FloatField()
    reviews = models.TextField()
    status = models.CharField(max_length=255)
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_product_reviews',
        db_column='domain_user_id_id'
    )
    review_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        db_column='review_user_id_id'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        db_column='product_id_id'
    )

    class Meta:
        db_table = 'productservices_productreviews'


class UserShippingAddress(models.Model):
    id = models.AutoField(primary_key=True)
    address_type = models.CharField(max_length=50)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shipping_addresses',
        db_column='user_id'
    )

    class Meta:
        db_table = 'userservices_usershippingaddress'


class ActivityLog(models.Model):
    id = models.AutoField(primary_key=True)
    activity = models.TextField()
    activity_type = models.CharField(max_length=50)
    activity_date = models.DateTimeField()
    activity_ip = models.CharField(max_length=39)
    activity_device = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_activity_logs',
        db_column='domain_user_id_id'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        db_column='user_id'
    )

    class Meta:
        db_table = 'userservices_activitylog'


class Module(models.Model):
    id = models.AutoField(primary_key=True)
    module_name = models.CharField(max_length=50)
    module_icon = models.TextField()
    is_menu = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    module_url = models.TextField()
    display_order = models.IntegerField()
    module_description = models.TextField()
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


class UserPermission(models.Model):
    id = models.AutoField(primary_key=True)
    is_view = models.BooleanField(default=False)
    is_add = models.BooleanField(default=False)
    is_edit = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='user_permissions',
        db_column='module_id_id'
    )
    domain_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='domain_user_permissions',
        db_column='domain_user_id_id'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_permissions',
        db_column='user_id'
    )

    class Meta:
        db_table = 'userservices_userpermissions'


class DjangoContentType(models.Model):
    id = models.AutoField(primary_key=True)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        db_table = 'django_content_type'


class AuthPermission(models.Model):
    id = models.AutoField(primary_key=True)
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


class AuthGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)

    class Meta:
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(
        AuthGroup,
        on_delete=models.CASCADE,
        db_column='group_id'
    )
    permission = models.ForeignKey(
        AuthPermission,
        on_delete=models.CASCADE,
        db_column='permission_id'
    )

    class Meta:
        db_table = 'auth_group_permissions'


class UserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='users_id'
    )
    group = models.ForeignKey(
        AuthGroup,
        on_delete=models.CASCADE,
        db_column='group_id'
    )

    class Meta:
        db_table = 'userservices_users_groups'


class UserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='users_id'
    )
    permission = models.ForeignKey(
        AuthPermission,
        on_delete=models.CASCADE,
        db_column='permission_id'
    )

    class Meta:
        db_table = 'userservices_users_user_permissions'


class DjangoAdminLog(models.Model):
    id = models.AutoField(primary_key=True)
    action_time = models.DateTimeField()
    object_id = models.TextField()
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(
        DjangoContentType,
        on_delete=models.CASCADE,
        related_name='admin_logs',
        db_column='content_type_id'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_logs',
        db_column='user_id'
    )

    class Meta:
        db_table = 'django_admin_log'


class DjangoMigration(models.Model):
    id = models.BigAutoField(primary_key=True)
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