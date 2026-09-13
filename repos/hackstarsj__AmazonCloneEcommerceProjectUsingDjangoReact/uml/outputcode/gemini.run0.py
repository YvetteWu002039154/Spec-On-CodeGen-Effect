from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

# ============================================================
#  DJANGO FRAMEWORK / AUTH
# ============================================================

@dataclass
class django_content_type:
    id: int
    app_label: Optional[str] = None
    model: Optional[str] = None

@dataclass
class django_migrations:
    id: int
    app: Optional[str] = None
    name: Optional[str] = None
    applied: Optional[datetime] = None

@dataclass
class django_session:
    session_key: str
    session_data: Optional[str] = None
    expire_date: Optional[datetime] = None

@dataclass
class auth_group:
    id: int
    name: Optional[str] = None

@dataclass
class auth_permission:
    id: int
    name: Optional[str] = None
    codename: Optional[str] = None
    content_type_id: Optional[int] = None
    
    content_type: Optional['django_content_type'] = None

@dataclass
class auth_group_permissions:
    id: int
    group_id: Optional[int] = None
    permission_id: Optional[int] = None
    
    group: Optional['auth_group'] = None
    permission: Optional['auth_permission'] = None

@dataclass
class django_admin_log:
    id: int
    action_time: Optional[datetime] = None
    object_id: Optional[str] = None
    object_repr: Optional[str] = None
    action_flag: Optional[int] = None
    change_message: Optional[str] = None
    content_type_id: Optional[int] = None
    user_id: Optional[int] = None
    
    content_type: Optional['django_content_type'] = None
    user: Optional['userservices_users'] = None

# ============================================================
#  USER SERVICE
# ============================================================

@dataclass
class userservices_users:
    id: int
    is_superuser: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_staff: Optional[bool] = None
    is_active: Optional[bool] = None
    date_joined: Optional[datetime] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    profile_pic: Optional[str] = None
    account_status: Optional[str] = None
    role: Optional[str] = None
    dob: Optional[date] = None
    username: Optional[str] = None
    password: Optional[str] = None
    social_media_links: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    departMent: Optional[str] = None
    designation: Optional[str] = None
    time_zone: Optional[str] = None
    last_login: Optional[datetime] = None
    last_device: Optional[str] = None
    last_ip: Optional[str] = None
    currency: Optional[str] = None
    domain_name: Optional[str] = None
    plan_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None

@dataclass
class userservices_usershippingaddress:
    id: int
    address_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[int] = None
    
    user: Optional['userservices_users'] = None

@dataclass
class userservices_activitylog:
    id: int
    activity: Optional[str] = None
    activity_type: Optional[str] = None
    activity_date: Optional[datetime] = None
    activity_ip: Optional[str] = None
    activity_device: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None
    user: Optional['userservices_users'] = None

@dataclass
class userservices_modules:
    id: int
    module_name: Optional[str] = None
    module_icon: Optional[str] = None
    is_menu: Optional[bool] = None
    is_active: Optional[bool] = None
    module_url: Optional[str] = None
    display_order: Optional[int] = None
    module_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id_id: Optional[int] = None
    
    parent: Optional['userservices_modules'] = None

@dataclass
class userservices_userpermissions:
    id: int
    is_view: Optional[bool] = None
    is_add: Optional[bool] = None
    is_edit: Optional[bool] = None
    is_delete: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    
    module: Optional['userservices_modules'] = None
    domain_user: Optional['userservices_users'] = None
    user: Optional['userservices_users'] = None

@dataclass
class userservices_users_groups:
    id: int
    users_id: Optional[int] = None
    group_id: Optional[int] = None
    
    user: Optional['userservices_users'] = None
    group: Optional['auth_group'] = None

@dataclass
class userservices_users_user_permissions:
    id: int
    users_id: Optional[int] = None
    permission_id: Optional[int] = None
    
    user: Optional['userservices_users'] = None
    permission: Optional['auth_permission'] = None

# ============================================================
#  PRODUCT SERVICE
# ============================================================

@dataclass
class productservices_categories:
    id: int
    name: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    parent_id_id: Optional[int] = None
    
    added_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    parent: Optional['productservices_categories'] = None

@dataclass
class productservices_products:
    id: int
    name: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    html_description: Optional[str] = None
    highlights: Optional[Dict[str, Any]] = None
    sku: Optional[str] = None
    initial_buying_price: Optional[float] = None
    initial_selling_price: Optional[float] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    uom: Optional[str] = None
    color: Optional[str] = None
    tax_percentage: Optional[float] = None
    brand: Optional[str] = None
    brand_model: Optional[str] = None
    status: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    category_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    
    added_by_user: Optional['userservices_users'] = None
    category: Optional['productservices_categories'] = None
    domain_user: Optional['userservices_users'] = None

@dataclass
class productservices_productquestions:
    id: int
    question: Optional[str] = None
    answer: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    question_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    
    answer_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    question_user: Optional['userservices_users'] = None
    product: Optional['productservices_products'] = None

@dataclass
class productservices_productreviews:
    id: int
    review_images: Optional[Dict[str, Any]] = None
    rating: Optional[float] = None
    reviews: Optional[str] = None
    status: Optional[str] = None
    domain_user_id_id: Optional[int] = None
    review_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None
    review_user: Optional['userservices_users'] = None
    product: Optional['productservices_products'] = None

# ============================================================
#  INVENTORY SERVICE
# ============================================================

@dataclass
class inventoryservices_warehouse:
    id: int
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    size: Optional[str] = None
    capacity: Optional[str] = None
    warehouse_type: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_manager_id: Optional[int] = None
    
    added_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    warehouse_manager: Optional['userservices_users'] = None

@dataclass
class inventoryservices_rackandshelvesandfloor:
    id: int
    name: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    floor: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    
    added_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    warehouse: Optional['inventoryservices_warehouse'] = None

@dataclass
class inventoryservices_inventory:
    id: int
    quantity: Optional[int] = None
    mrp: Optional[str] = None
    batch_number: Optional[str] = None
    discount_type: Optional[str] = None
    discount_amout: Optional[float] = None
    sr_no: Optional[str] = None
    mfg_date: Optional[datetime] = None
    uom: Optional[str] = None
    ptr: Optional[str] = None
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    quantity_inwarded: Optional[int] = None
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    stock_status: Optional[str] = None
    inward_type: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    purchase_order_id_id: Optional[int] = None
    purchase_order_item_id_id: Optional[int] = None
    purchase_order_item_inwarded_item_id_id: Optional[int] = None
    rack_shelf_floor_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    
    added_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    product: Optional['productservices_products'] = None
    purchase_order: Optional['orderservice_purchaseorder'] = None
    purchase_order_item: Optional['orderservice_purchaseorderitems'] = None
    purchase_order_item_inwarded_item: Optional['orderservice_purchaseorderiteminwardedlog'] = None
    rack_shelf_floor: Optional['inventoryservices_rackandshelvesandfloor'] = None
    warehouse: Optional['inventoryservices_warehouse'] = None

@dataclass
class inventoryservices_inventorylog:
    id: int
    quantity: Optional[int] = None
    status: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    inventory_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    rack_shelf_floor_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    
    added_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    inventory: Optional['inventoryservices_inventory'] = None
    po: Optional['orderservice_purchaseorder'] = None
    so: Optional['orderservice_salesorder'] = None
    rack_shelf_floor: Optional['inventoryservices_rackandshelvesandfloor'] = None
    warehouse: Optional['inventoryservices_warehouse'] = None

# ============================================================
#  ORDER SERVICE
# ============================================================

@dataclass
class orderservice_purchaseorder:
    id: int
    po_code: Optional[str] = None
    po_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    payment_status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    due_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: Optional[str] = None
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    supplier_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    
    approved_by_user: Optional['userservices_users'] = None
    cancelled_by_user: Optional['userservices_users'] = None
    created_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    last_updated_by_user: Optional['userservices_users'] = None
    received_by_user: Optional['userservices_users'] = None
    returned_by_user: Optional['userservices_users'] = None
    supplier: Optional['userservices_users'] = None
    updated_by_user: Optional['userservices_users'] = None
    warehouse: Optional['inventoryservices_warehouse'] = None

@dataclass
class orderservice_purchaseorderitems:
    id: int
    quantity_ordered: Optional[int] = None
    quantity_received: Optional[int] = None
    quantity_cancelled: Optional[int] = None
    quantity_returned: Optional[int] = None
    buying_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    amount_returned: Optional[Decimal] = None
    amount_cancelled: Optional[Decimal] = None
    amount_ordered: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_amount: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    
    approved_by_user: Optional['userservices_users'] = None
    cancelled_by_user: Optional['userservices_users'] = None
    created_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    last_updated_by_user: Optional['userservices_users'] = None
    received_by_user: Optional['userservices_users'] = None
    returned_by_user: Optional['userservices_users'] = None
    po: Optional['orderservice_purchaseorder'] = None
    product: Optional['productservices_products'] = None
    updated_by_user: Optional['userservices_users'] = None

@dataclass
class orderservice_purchaseorderlogs:
    id: int
    comment: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    
    created_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    po: Optional['orderservice_purchaseorder'] = None

@dataclass
class orderservice_purchaseorderinwardedlog:
    id: int
    invoice_path: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    inwarded_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    inwarded_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None
    inwarded_by_user: Optional['userservices_users'] = None
    po: Optional['orderservice_purchaseorder'] = None

@dataclass
class orderservice_purchaseorderiteminwardedlog:
    id: int
    inwarded_quantity: Optional[int] = None
    price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    po_item_id_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None
    po_item: Optional['orderservice_purchaseorderitems'] = None

@dataclass
class orderservice_salesorder:
    id: int
    so_code: Optional[str] = None
    so_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    payment_status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    due_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: Optional[str] = None
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    customer_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    
    approved_by_user: Optional['userservices_users'] = None
    cancelled_by_user: Optional['userservices_users'] = None
    created_by_user: Optional['userservices_users'] = None
    customer: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    last_updated_by_user: Optional['userservices_users'] = None
    received_by_user: Optional['userservices_users'] = None
    returned_by_user: Optional['userservices_users'] = None
    po: Optional['orderservice_purchaseorder'] = None
    product: Optional['productservices_products'] = None
    updated_by_user: Optional['userservices_users'] = None

@dataclass
class orderservice_salesorderorderitems:
    id: int
    quantity_ordered: Optional[int] = None
    quantity_delivered: Optional[int] = None
    quantity_shipped: Optional[int] = None
    quantity_cancelled: Optional[int] = None
    quantity_returned: Optional[int] = None
    purchase_price: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    amount_paid: Optional[Decimal] = None
    amount_returned: Optional[Decimal] = None
    amount_cancelled: Optional[Decimal] = None
    amount_ordered: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: Optional[str] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    shipped_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    
    approved_by_user: Optional['userservices_users'] = None
    cancelled_by_user: Optional['userservices_users'] = None
    created_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    product: Optional['productservices_products'] = None
    returned_by_user: Optional['userservices_users'] = None
    shipped_by_user: Optional['userservices_users'] = None
    so: Optional['orderservice_salesorder'] = None
    updated_by_user: Optional['userservices_users'] = None

@dataclass
class orderservice_salesorderlogs:
    id: int
    comment: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    
    created_by_user: Optional['userservices_users'] = None
    domain_user: Optional['userservices_users'] = None
    so: Optional['orderservice_salesorder'] = None

@dataclass
class orderservice_salesorderoutwardedlog:
    id: int
    invoice_path: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    outwared_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    outwarded_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None
    outwarded_by_user: Optional['userservices_users'] = None
    so: Optional['orderservice_salesorder'] = None

@dataclass
class orderservice_salesorderitemoutwardedlog:
    id: int
    outwarded_quantity: Optional[int] = None
    price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    so_item_id_id: Optional[int] = None
    
    domain_user: Optional['userservices_users'] = None
    so_item: Optional['orderservice_salesorderorderitems'] = None