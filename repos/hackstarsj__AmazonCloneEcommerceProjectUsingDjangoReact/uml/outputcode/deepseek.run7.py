from django.db import models

class DjangoContentType(models.Model):
    id = models.AutoField(primary_key=True)
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

class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        db_table = 'django_migrations'

class AuthPermission(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)
    content_type = models.ForeignKey(DjangoContentType, on_delete=models.CASCADE, db_column='content_type_id')

    class Meta:
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)

class AuthGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)

    class Meta:
        db_table = 'auth_group'

class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE, db_column='group_id')
    permission = models.ForeignKey(AuthPermission, on_delete=models.CASCADE, db_column='permission_id')

    class Meta:
        db_table = 'auth_group_permissions'

class UserservicesUsers(models.Model):
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
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    social_media_links = models.JSONField(default=dict)
    addition_details = models.JSONField(default=dict)
    language = models.CharField(max_length=50)
    departMent = models.CharField(max_length=50)
    designation = models.CharField(max_length=50)
    time_zone = models.CharField(max_length=50)
    last_login = models.DateTimeField(null=True, blank=True)
    last_device = models.CharField(max_length=50)
    last_ip = models.GenericIPAddressField(protocol='IPv4', max_length=39)
    currency = models.CharField(max_length=50)
    domain_name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='domain_user_id', related_name='domain_users')

    class Meta:
        db_table = 'userservices_users'

class UserservicesUsershippingaddress(models.Model):
    id = models.IntegerField(primary_key=True)
    address_type = models.CharField(max_length=50)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        db_table = 'userservices_usershippingaddress'

class UserservicesActivitylog(models.Model):
    id = models.IntegerField(primary_key=True)
    activity = models.TextField()
    activity_type = models.CharField(max_length=50)
    activity_date = models.DateTimeField()
    activity_ip = models.GenericIPAddressField(protocol='IPv4', max_length=39)
    activity_device = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='activitylog_domain')
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='user_id', related_name='activitylog_entries')

    class Meta:
        db_table = 'userservices_activitylog'

class UserservicesModules(models.Model):
    id = models.IntegerField(primary_key=True)
    module_name = models.CharField(max_length=50)
    module_icon = models.TextField()
    is_menu = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    module_url = models.TextField()
    display_order = models.IntegerField()
    module_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='parent_id_id', related_name='children')

    class Meta:
        db_table = 'userservices_modules'

class UserservicesUserpermissions(models.Model):
    id = models.IntegerField(primary_key=True)
    is_view = models.BooleanField(default=False)
    is_add = models.BooleanField(default=False)
    is_edit = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    module = models.ForeignKey(UserservicesModules, on_delete=models.CASCADE, db_column='module_id_id')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='userpermissions_domain')
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='user_id', related_name='userpermissions_user')

    class Meta:
        db_table = 'userservices_userpermissions'

class UserservicesUsersGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    users = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='users_id')
    group = models.ForeignKey(AuthGroup, on_delete=models.CASCADE, db_column='group_id')

    class Meta:
        db_table = 'userservices_users_groups'

class UserservicesUsersUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    users = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='users_id')
    permission = models.ForeignKey(AuthPermission, on_delete=models.CASCADE, db_column='permission_id')

    class Meta:
        db_table = 'userservices_users_user_permissions'

class DjangoAdminLog(models.Model):
    id = models.IntegerField(primary_key=True)
    action_time = models.DateTimeField()
    object_id = models.TextField(null=True, blank=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(DjangoContentType, on_delete=models.SET_NULL, null=True, blank=True, db_column='content_type_id')
    user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        db_table = 'django_admin_log'


# Product Service
class ProductservicesCategories(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    image = models.TextField()
    description = models.TextField()
    display_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='added_by_user_id_id', related_name='categories_added')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='categories_domain')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='parent_id_id', related_name='subcategories')

    class Meta:
        db_table = 'productservices_categories'

class ProductservicesProducts(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    image = models.JSONField(default=dict)
    description = models.TextField()
    specifications = models.JSONField(default=dict)
    html_description = models.TextField()
    highlights = models.JSONField(default=list)
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
    seo_keywords = models.JSONField(default=list)
    addition_details = models.JSONField(default=dict, db_column='addition_details')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='added_by_user_id_id', related_name='products_added')
    category = models.ForeignKey(ProductservicesCategories, on_delete=models.CASCADE, db_column='category_id_id')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='products_domain')

    class Meta:
        db_table = 'productservices_products'

class ProductservicesProductquestions(models.Model):
    id = models.IntegerField(primary_key=True)
    question = models.TextField()
    answer = models.TextField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    answer_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='answer_user_id_id', related_name='answered_questions')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='productquestions_domain')
    question_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='question_user_id_id', related_name='asked_questions')
    product = models.ForeignKey(ProductservicesProducts, on_delete=models.CASCADE, db_column='product_id_id')

    class Meta:
        db_table = 'productservices_productquestions'

class ProductservicesProductreviews(models.Model):
    id = models.IntegerField(primary_key=True)
    review_images = models.JSONField(default=list)
    rating = models.FloatField()
    reviews = models.TextField()
    status = models.CharField(max_length=255)
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='productreviews_domain')
    review_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='review_user_id_id', related_name='written_reviews')
    product = models.ForeignKey(ProductservicesProducts, on_delete=models.CASCADE, db_column='product_id_id')

    class Meta:
        db_table = 'productservices_productreviews'


# Inventory Service
class InventoryservicesWarehouse(models.Model):
    id = models.IntegerField(primary_key=True)
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
    added_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='added_by_user_id_id', related_name='warehouses_added')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='warehouses_domain')
    warehouse_manager = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='warehouse_manager_id', related_name='managed_warehouses')

    class Meta:
        db_table = 'inventoryservices_warehouse'

class InventoryservicesRackandshelvesandfloor(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    rack = models.CharField(max_length=255)
    shelf = models.CharField(max_length=255)
    floor = models.CharField(max_length=255)
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='added_by_user_id_id', related_name='racks_added')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='racks_domain')
    warehouse = models.ForeignKey(InventoryservicesWarehouse, on_delete=models.CASCADE, db_column='warehouse_id_id')

    class Meta:
        db_table = 'inventoryservices_rackandshelvesandfloor'


# Order Service - Purchase
class OrderservicePurchaseorder(models.Model):
    id = models.IntegerField(primary_key=True)
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
    cancelled_reason = models.TextField()
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='approved_by_user_id_id', related_name='approved_purchase_orders')
    cancelled_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='cancelled_by_user_id_id', related_name='cancelled_purchase_orders')
    created_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='created_by_user_id_id', related_name='created_purchase_orders')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='purchaseorder_domain')
    last_updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='last_updated_by_user_id_id', related_name='last_updated_purchase_orders')
    received_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='received_by_user_id_id', related_name='received_purchase_orders')
    returned_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='returned_by_user_id_id', related_name='returned_purchase_orders')
    supplier = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='supplier_id_id', related_name='supplied_purchase_orders')
    updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='updated_by_user_id_id', related_name='updated_purchase_orders')
    warehouse = models.ForeignKey(InventoryservicesWarehouse, on_delete=models.CASCADE, db_column='warehouse_id_id', related_name='purchase_orders')

    class Meta:
        db_table = 'orderservice_purchaseorder'

class OrderservicePurchaseorderitems(models.Model):
    id = models.IntegerField(primary_key=True)
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
    cancelled_reason = models.TextField()
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='approved_by_user_id_id', related_name='approved_po_items')
    cancelled_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='cancelled_by_user_id_id', related_name='cancelled_po_items')
    created_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='created_by_user_id_id', related_name='created_po_items')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='poitem_domain')
    last_updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='last_updated_by_user_id_id', related_name='last_updated_po_items')
    received_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='received_by_user_id_id', related_name='received_po_items')
    returned_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='returned_by_user_id_id', related_name='returned_po_items')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.CASCADE, db_column='po_id_id', related_name='items')
    product = models.ForeignKey(ProductservicesProducts, on_delete=models.CASCADE, db_column='product_id_id')
    updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='updated_by_user_id_id', related_name='updated_po_items')

    class Meta:
        db_table = 'orderservice_purchaseorderitems'

class OrderservicePurchaseorderlogs(models.Model):
    id = models.IntegerField(primary_key=True)
    comment = models.TextField()
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='created_by_user_id_id', related_name='purchase_order_logs_created')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='purchaseorderlog_domain')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.CASCADE, db_column='po_id_id', related_name='logs')

    class Meta:
        db_table = 'orderservice_purchaseorderlogs'

class OrderservicePurchaseorderinwardedlog(models.Model):
    id = models.IntegerField(primary_key=True)
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    inwarded_at = models.DateTimeField()
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='purchaseorderinwardedlog_domain')
    inwarded_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='inwarded_by_user_id_id', related_name='inwarded_purchase_orders')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.CASCADE, db_column='po_id_id', related_name='inwarded_logs')

    class Meta:
        db_table = 'orderservice_purchaseorderinwardedlog'

class OrderservicePurchaseorderiteminwardedlog(models.Model):
    id = models.IntegerField(primary_key=True)
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
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='purchaseorderiteminwardedlog_domain')
    po_item = models.ForeignKey(OrderservicePurchaseorderitems, on_delete=models.CASCADE, db_column='po_item_id_id', related_name='inwarded_logs')

    class Meta:
        db_table = 'orderservice_purchaseorderiteminwardedlog'


# Order Service - Sales
class OrderserviceSalesorder(models.Model):
    id = models.IntegerField(primary_key=True)
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
    cancelled_reason = models.TextField()
    received_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='approved_by_user_id_id', related_name='approved_sales_orders')
    cancelled_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='cancelled_by_user_id_id', related_name='cancelled_sales_orders')
    created_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='created_by_user_id_id', related_name='created_sales_orders')
    customer = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='customer_id_id', related_name='customer_sales_orders')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='salesorder_domain')
    last_updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='last_updated_by_user_id_id', related_name='last_updated_sales_orders')
    received_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='received_by_user_id_id', related_name='received_sales_orders')
    returned_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='returned_by_user_id_id', related_name='returned_sales_orders')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.SET_NULL, null=True, blank=True, db_column='po_id_id', related_name='sales_orders')
    product = models.ForeignKey(ProductservicesProducts, on_delete=models.SET_NULL, null=True, blank=True, db_column='product_id_id', related_name='sales_orders')
    updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='updated_by_user_id_id', related_name='updated_sales_orders')

    class Meta:
        db_table = 'orderservice_salesorder'

class OrderserviceSalesorderorderitems(models.Model):
    id = models.IntegerField(primary_key=True)
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
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField()
    shipped_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    approved_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='approved_by_user_id_id', related_name='approved_so_items')
    cancelled_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='cancelled_by_user_id_id', related_name='cancelled_so_items')
    created_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='created_by_user_id_id', related_name='created_so_items')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='soitem_domain')
    product = models.ForeignKey(ProductservicesProducts, on_delete=models.CASCADE, db_column='product_id_id')
    returned_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='returned_by_user_id_id', related_name='returned_so_items')
    shipped_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.SET_NULL, null=True, blank=True, db_column='shipped_by_user_id_id', related_name='shipped_so_items')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.CASCADE, db_column='so_id_id', related_name='items')
    updated_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='updated_by_user_id_id', related_name='updated_so_items')

    class Meta:
        db_table = 'orderservice_salesorderorderitems'

class OrderserviceSalesorderlogs(models.Model):
    id = models.IntegerField(primary_key=True)
    comment = models.TextField()
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='created_by_user_id_id', related_name='sales_order_logs_created')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='salesorderlog_domain')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.CASCADE, db_column='so_id_id', related_name='logs')

    class Meta:
        db_table = 'orderservice_salesorderlogs'

class OrderserviceSalesorderoutwardedlog(models.Model):
    id = models.IntegerField(primary_key=True)
    invoice_path = models.TextField()
    invoice_number = models.CharField(max_length=255)
    notes = models.TextField()
    outwared_at = models.DateTimeField()
    additional_details = models.JSONField(default=dict)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='salesorderoutwardedlog_domain')
    outwarded_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='outwarded_by_user_id_id', related_name='outwarded_sales_orders')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.CASCADE, db_column='so_id_id', related_name='outwarded_logs')

    class Meta:
        db_table = 'orderservice_salesorderoutwardedlog'

class OrderserviceSalesorderitemoutwardedlog(models.Model):
    id = models.IntegerField(primary_key=True)
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
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='salesorderitemoutwardedlog_domain')
    so_item = models.ForeignKey(OrderserviceSalesorderorderitems, on_delete=models.CASCADE, db_column='so_item_id_id', related_name='outwarded_logs')

    class Meta:
        db_table = 'orderservice_salesorderitemoutwardedlog'


# Inventory models that depend on OrderService models (to avoid circular references, these are defined after the orders)
class InventoryservicesInventory(models.Model):
    id = models.IntegerField(primary_key=True)
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
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='added_by_user_id_id', related_name='inventory_added')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='inventory_domain')
    product = models.ForeignKey(ProductservicesProducts, on_delete=models.CASCADE, db_column='product_id_id')
    purchase_order = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.SET_NULL, null=True, blank=True, db_column='purchase_order_id_id', related_name='inventory_records')
    purchase_order_item = models.ForeignKey(OrderservicePurchaseorderitems, on_delete=models.SET_NULL, null=True, blank=True, db_column='purchase_order_item_id_id', related_name='inventory_records')
    purchase_order_item_inwarded_item = models.ForeignKey(OrderservicePurchaseorderiteminwardedlog, on_delete=models.SET_NULL, null=True, blank=True, db_column='purchase_order_item_inwarded_item_id_id', related_name='inventory_records')
    rack_shelf_floor = models.ForeignKey(InventoryservicesRackandshelvesandfloor, on_delete=models.SET_NULL, null=True, blank=True, db_column='rack_shelf_floor_id_id', related_name='inventory_items')
    warehouse = models.ForeignKey(InventoryservicesWarehouse, on_delete=models.CASCADE, db_column='warehouse_id_id', related_name='inventory_items')

    class Meta:
        db_table = 'inventoryservices_inventory'

class InventoryservicesInventorylog(models.Model):
    id = models.IntegerField(primary_key=True)
    quantity = models.IntegerField()
    status = models.CharField(max_length=255)
    additional_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='added_by_user_id_id', related_name='inventorylog_added')
    domain_user = models.ForeignKey(UserservicesUsers, on_delete=models.CASCADE, db_column='domain_user_id_id', related_name='inventorylog_domain')
    inventory = models.ForeignKey(InventoryservicesInventory, on_delete=models.CASCADE, db_column='inventory_id_id', related_name='logs')
    po = models.ForeignKey(OrderservicePurchaseorder, on_delete=models.SET_NULL, null=True, blank=True, db_column='po_id_id', related_name='inventory_logs')
    so = models.ForeignKey(OrderserviceSalesorder, on_delete=models.SET_NULL, null=True, blank=True, db_column='so_id_id', related_name='inventory_logs')
    rack_shelf_floor = models.ForeignKey(InventoryservicesRackandshelvesandfloor, on_delete=models.SET_NULL, null=True, blank=True, db_column='rack_shelf_floor_id_id', related_name='inventory_logs')
    warehouse = models.ForeignKey(InventoryservicesWarehouse, on_delete=models.CASCADE, db_column='warehouse_id_id', related_name='inventory_logs')

    class Meta:
        db_table = 'inventoryservices_inventorylog'