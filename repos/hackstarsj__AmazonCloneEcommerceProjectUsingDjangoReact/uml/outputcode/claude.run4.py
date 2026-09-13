from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


# ============================================================
#  DJANGO FRAMEWORK / AUTH
# ============================================================

@dataclass
class DjangoContentType:
    id: int
    app_label: str
    model: str

    def __post_init__(self):
        self._permissions: List['AuthPermission'] = []
        self._admin_logs: List['DjangoAdminLog'] = []


@dataclass
class DjangoMigrations:
    id: int
    app: str
    name: str
    applied: datetime


@dataclass
class DjangoSession:
    session_key: str  # PK
    session_data: str
    expire_date: datetime


@dataclass
class AuthGroup:
    id: int
    name: str

    def __post_init__(self):
        self._permissions: List['AuthPermission'] = []
        self._group_permissions: List['AuthGroupPermissions'] = []
        self._user_groups: List['UserservicesUsersGroups'] = []


@dataclass
class AuthPermission:
    id: int
    name: str
    codename: str
    content_type_id: int
    content_type: Optional['DjangoContentType'] = None

    def __post_init__(self):
        self._group_permissions: List['AuthGroupPermissions'] = []
        self._user_permissions: List['UserservicesUsersUserPermissions'] = []


@dataclass
class AuthGroupPermissions:
    id: int
    group_id: int
    permission_id: int
    group: Optional['AuthGroup'] = None
    permission: Optional['AuthPermission'] = None


@dataclass
class DjangoAdminLog:
    id: int
    action_time: datetime
    object_id: Optional[str]
    object_repr: str
    action_flag: int
    change_message: str
    content_type_id: Optional[int]
    user_id: int
    content_type: Optional['DjangoContentType'] = None
    user: Optional['UserservicesUsers'] = None


# ============================================================
#  USER SERVICE
# ============================================================

@dataclass
class UserservicesUsers:
    id: int
    is_superuser: bool = False
    first_name: str = ''
    last_name: str = ''
    is_staff: bool = False
    is_active: bool = True
    date_joined: Optional[datetime] = None
    name: str = ''
    email: str = ''
    phone: str = ''
    address: str = ''
    city: str = ''
    state: str = ''
    pincode: str = ''
    country: str = ''
    profile_pic: str = ''
    account_status: str = ''
    role: str = ''
    dob: Optional[date] = None
    username: str = ''
    password: str = ''
    social_media_links: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    language: str = ''
    departMent: str = ''
    designation: str = ''
    time_zone: str = ''
    last_login: Optional[datetime] = None
    last_device: str = ''
    last_ip: str = ''
    currency: str = ''
    domain_name: str = ''
    plan_type: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None

    def __post_init__(self):
        self._shipping_addresses: List['UserservicesUserShippingAddress'] = []
        self._activity_logs: List['UserservicesActivityLog'] = []
        self._permissions: List['UserservicesUserPermissions'] = []
        self._groups: List['UserservicesUsersGroups'] = []
        self._user_permissions: List['UserservicesUsersUserPermissions'] = []
        self._admin_logs: List['DjangoAdminLog'] = []
        self._managed_warehouses: List['InventoryservicesWarehouse'] = []
        self._added_warehouses: List['InventoryservicesWarehouse'] = []
        self._domain_warehouses: List['InventoryservicesWarehouse'] = []
        self._added_inventories: List['InventoryservicesInventory'] = []
        self._domain_inventories: List['InventoryservicesInventory'] = []
        self._added_inventory_logs: List['InventoryservicesInventoryLog'] = []
        self._domain_inventory_logs: List['InventoryservicesInventoryLog'] = []
        self._added_rack_shelves: List['InventoryservicesRackAndShelvesAndFloor'] = []
        self._domain_rack_shelves: List['InventoryservicesRackAndShelvesAndFloor'] = []
        self._added_products: List['ProductservicesProducts'] = []
        self._domain_products: List['ProductservicesProducts'] = []
        self._added_categories: List['ProductservicesCategories'] = []
        self._domain_categories: List['ProductservicesCategories'] = []
        self._question_product_questions: List['ProductservicesProductQuestions'] = []
        self._answer_product_questions: List['ProductservicesProductQuestions'] = []
        self._domain_product_questions: List['ProductservicesProductQuestions'] = []
        self._review_product_reviews: List['ProductservicesProductReviews'] = []
        self._domain_product_reviews: List['ProductservicesProductReviews'] = []
        self._supplier_purchase_orders: List['OrderservicePurchaseOrder'] = []
        self._created_purchase_orders: List['OrderservicePurchaseOrder'] = []
        self._domain_purchase_orders: List['OrderservicePurchaseOrder'] = []
        self._customer_sales_orders: List['OrderserviceSalesOrder'] = []
        self._created_sales_orders: List['OrderserviceSalesOrder'] = []
        self._domain_sales_orders: List['OrderserviceSalesOrder'] = []
        self._domain_users: List['UserservicesUsers'] = []


@dataclass
class UserservicesUserShippingAddress:
    id: int
    address_type: str = ''
    address: str = ''
    city: str = ''
    state: str = ''
    pincode: str = ''
    country: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[int] = None
    user: Optional['UserservicesUsers'] = None


@dataclass
class UserservicesActivityLog:
    id: int
    activity: str = ''
    activity_type: str = ''
    activity_date: Optional[datetime] = None
    activity_ip: str = ''
    activity_device: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None
    user: Optional['UserservicesUsers'] = None


@dataclass
class UserservicesModules:
    id: int
    module_name: str = ''
    module_icon: str = ''
    is_menu: bool = False
    is_active: bool = True
    module_url: str = ''
    display_order: int = 0
    module_description: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id_id: Optional[int] = None
    parent: Optional['UserservicesModules'] = None

    def __post_init__(self):
        self._children: List['UserservicesModules'] = []
        self._permissions: List['UserservicesUserPermissions'] = []


@dataclass
class UserservicesUserPermissions:
    id: int
    is_view: bool = False
    is_add: bool = False
    is_edit: bool = False
    is_delete: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    module: Optional['UserservicesModules'] = None
    domain_user: Optional['UserservicesUsers'] = None
    user: Optional['UserservicesUsers'] = None


@dataclass
class UserservicesUsersGroups:
    id: int
    users_id: Optional[int] = None
    group_id: Optional[int] = None
    user: Optional['UserservicesUsers'] = None
    group: Optional['AuthGroup'] = None


@dataclass
class UserservicesUsersUserPermissions:
    id: int
    users_id: Optional[int] = None
    permission_id: Optional[int] = None
    user: Optional['UserservicesUsers'] = None
    permission: Optional['AuthPermission'] = None


# ============================================================
#  PRODUCT SERVICE
# ============================================================

@dataclass
class ProductservicesCategories:
    id: int
    name: str = ''
    image: str = ''
    description: str = ''
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    parent_id_id: Optional[int] = None
    added_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    parent: Optional['ProductservicesCategories'] = None

    def __post_init__(self):
        self._children: List['ProductservicesCategories'] = []
        self._products: List['ProductservicesProducts'] = []


@dataclass
class ProductservicesProducts:
    id: int
    name: str = ''
    image: Optional[Dict[str, Any]] = None
    description: str = ''
    specifications: Optional[Dict[str, Any]] = None
    html_description: str = ''
    highlights: Optional[Dict[str, Any]] = None
    sku: str = ''
    initial_buying_price: float = 0.0
    initial_selling_price: float = 0.0
    weight: float = 0.0
    dimensions: str = ''
    uom: str = ''
    color: str = ''
    tax_percentage: float = 0.0
    brand: str = ''
    brand_model: str = ''
    status: str = ''
    seo_title: str = ''
    seo_description: str = ''
    seo_keywords: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    category_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    added_by_user: Optional['UserservicesUsers'] = None
    category: Optional['ProductservicesCategories'] = None
    domain_user: Optional['UserservicesUsers'] = None

    def __post_init__(self):
        self._questions: List['ProductservicesProductQuestions'] = []
        self._reviews: List['ProductservicesProductReviews'] = []
        self._inventories: List['InventoryservicesInventory'] = []
        self._purchase_order_items: List['OrderservicePurchaseOrderItems'] = []
        self._sales_order_items: List['OrderserviceSalesOrderOrderItems'] = []


@dataclass
class ProductservicesProductQuestions:
    id: int
    question: str = ''
    answer: str = ''
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    question_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    answer_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    question_user: Optional['UserservicesUsers'] = None
    product: Optional['ProductservicesProducts'] = None


@dataclass
class ProductservicesProductReviews:
    id: int
    review_images: Optional[Dict[str, Any]] = None
    rating: float = 0.0
    reviews: str = ''
    status: str = ''
    domain_user_id_id: Optional[int] = None
    review_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None
    review_user: Optional['UserservicesUsers'] = None
    product: Optional['ProductservicesProducts'] = None


# ============================================================
#  INVENTORY SERVICE
# ============================================================

@dataclass
class InventoryservicesWarehouse:
    id: int
    name: str = ''
    address: str = ''
    city: str = ''
    state: str = ''
    country: str = ''
    pincode: str = ''
    phone: str = ''
    email: str = ''
    status: str = ''
    size: str = ''
    capacity: str = ''
    warehouse_type: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_manager_id: Optional[int] = None
    added_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    warehouse_manager: Optional['UserservicesUsers'] = None

    def __post_init__(self):
        self._inventories: List['InventoryservicesInventory'] = []
        self._inventory_logs: List['InventoryservicesInventoryLog'] = []
        self._rack_shelves: List['InventoryservicesRackAndShelvesAndFloor'] = []
        self._purchase_orders: List['OrderservicePurchaseOrder'] = []


@dataclass
class InventoryservicesRackAndShelvesAndFloor:
    id: int
    name: str = ''
    rack: str = ''
    shelf: str = ''
    floor: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    added_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    warehouse: Optional['InventoryservicesWarehouse'] = None

    def __post_init__(self):
        self._inventories: List['InventoryservicesInventory'] = []
        self._inventory_logs: List['InventoryservicesInventoryLog'] = []


@dataclass
class InventoryservicesInventory:
    id: int
    quantity: int = 0
    mrp: str = ''
    batch_number: str = ''
    discount_type: str = ''
    discount_amout: float = 0.0
    sr_no: str = ''
    mfg_date: Optional[datetime] = None
    uom: str = ''
    ptr: str = ''
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    quantity_inwarded: int = 0
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    stock_status: str = ''
    inward_type: str = ''
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
    added_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    product: Optional['ProductservicesProducts'] = None
    purchase_order: Optional['OrderservicePurchaseOrder'] = None
    purchase_order_item: Optional['OrderservicePurchaseOrderItems'] = None
    purchase_order_item_inwarded_item: Optional['OrderservicePurchaseOrderItemInwardedLog'] = None
    rack_shelf_floor: Optional['InventoryservicesRackAndShelvesAndFloor'] = None
    warehouse: Optional['InventoryservicesWarehouse'] = None

    def __post_init__(self):
        self._inventory_logs: List['InventoryservicesInventoryLog'] = []


@dataclass
class InventoryservicesInventoryLog:
    id: int
    quantity: int = 0
    status: str = ''
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
    added_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    inventory: Optional['InventoryservicesInventory'] = None
    po: Optional['OrderservicePurchaseOrder'] = None
    so: Optional['OrderserviceSalesOrder'] = None
    rack_shelf_floor: Optional['InventoryservicesRackAndShelvesAndFloor'] = None
    warehouse: Optional['InventoryservicesWarehouse'] = None


# ============================================================
#  ORDER SERVICE
# ============================================================

@dataclass
class OrderservicePurchaseOrder:
    id: int
    po_code: str = ''
    po_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ''
    payment_status: str = ''
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    due_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: str = ''
    shipping_amount: Optional[Decimal] = None
    shipping_type: str = ''
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
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
    approved_by_user: Optional['UserservicesUsers'] = None
    cancelled_by_user: Optional['UserservicesUsers'] = None
    created_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    last_updated_by_user: Optional['UserservicesUsers'] = None
    received_by_user: Optional['UserservicesUsers'] = None
    returned_by_user: Optional['UserservicesUsers'] = None
    supplier: Optional['UserservicesUsers'] = None
    updated_by_user: Optional['UserservicesUsers'] = None
    warehouse: Optional['InventoryservicesWarehouse'] = None

    def __post_init__(self):
        self._items: List['OrderservicePurchaseOrderItems'] = []
        self._logs: List['OrderservicePurchaseOrderLogs'] = []
        self._inwarded_logs: List['OrderservicePurchaseOrderInwardedLog'] = []
        self._inventories: List['InventoryservicesInventory'] = []
        self._inventory_logs: List['InventoryservicesInventoryLog'] = []


@dataclass
class OrderservicePurchaseOrderItems:
    id: int
    quantity_ordered: int = 0
    quantity_received: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
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
    discount_type: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
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
    approved_by_user: Optional['UserservicesUsers'] = None
    cancelled_by_user: Optional['UserservicesUsers'] = None
    created_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    last_updated_by_user: Optional['UserservicesUsers'] = None
    received_by_user: Optional['UserservicesUsers'] = None
    returned_by_user: Optional['UserservicesUsers'] = None
    po: Optional['OrderservicePurchaseOrder'] = None
    product: Optional['ProductservicesProducts'] = None
    updated_by_user: Optional['UserservicesUsers'] = None

    def __post_init__(self):
        self._inwarded_logs: List['OrderservicePurchaseOrderItemInwardedLog'] = []
        self._inventories: List['InventoryservicesInventory'] = []


@dataclass
class OrderservicePurchaseOrderLogs:
    id: int
    comment: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    created_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    po: Optional['OrderservicePurchaseOrder'] = None


@dataclass
class OrderservicePurchaseOrderInwardedLog:
    id: int
    invoice_path: str = ''
    invoice_number: str = ''
    notes: str = ''
    inwarded_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    inwarded_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None
    inwarded_by_user: Optional['UserservicesUsers'] = None
    po: Optional['OrderservicePurchaseOrder'] = None


@dataclass
class OrderservicePurchaseOrderItemInwardedLog:
    id: int
    inwarded_quantity: int = 0
    price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: str = ''
    shipping_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    po_item_id_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None
    po_item: Optional['OrderservicePurchaseOrderItems'] = None

    def __post_init__(self):
        self._inventories: List['InventoryservicesInventory'] = []


@dataclass
class OrderserviceSalesOrder:
    id: int
    so_code: str = ''
    so_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ''
    payment_status: str = ''
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    due_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: str = ''
    shipping_amount: Optional[Decimal] = None
    shipping_type: str = ''
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
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
    approved_by_user: Optional['UserservicesUsers'] = None
    cancelled_by_user: Optional['UserservicesUsers'] = None
    created_by_user: Optional['UserservicesUsers'] = None
    customer: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    last_updated_by_user: Optional['UserservicesUsers'] = None
    received_by_user: Optional['UserservicesUsers'] = None
    returned_by_user: Optional['UserservicesUsers'] = None
    po: Optional['OrderservicePurchaseOrder'] = None
    product: Optional['ProductservicesProducts'] = None
    updated_by_user: Optional['UserservicesUsers'] = None

    def __post_init__(self):
        self._items: List['OrderserviceSalesOrderOrderItems'] = []
        self._logs: List['OrderserviceSalesOrderLogs'] = []
        self._outwarded_logs: List['OrderserviceSalesOrderOutwardedLog'] = []
        self._inventory_logs: List['InventoryservicesInventoryLog'] = []


@dataclass
class OrderserviceSalesOrderOrderItems:
    id: int
    quantity_ordered: int = 0
    quantity_delivered: int = 0
    quantity_shipped: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    purchase_price: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: str = ''
    amount_paid: Optional[Decimal] = None
    amount_returned: Optional[Decimal] = None
    amount_cancelled: Optional[Decimal] = None
    amount_ordered: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: str = ''
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
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
    approved_by_user: Optional['UserservicesUsers'] = None
    cancelled_by_user: Optional['UserservicesUsers'] = None
    created_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    product: Optional['ProductservicesProducts'] = None
    returned_by_user: Optional['UserservicesUsers'] = None
    shipped_by_user: Optional['UserservicesUsers'] = None
    so: Optional['OrderserviceSalesOrder'] = None
    updated_by_user: Optional['UserservicesUsers'] = None

    def __post_init__(self):
        self._outwarded_item_logs: List['OrderserviceSalesOrderItemOutwardedLog'] = []


@dataclass
class OrderserviceSalesOrderLogs:
    id: int
    comment: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    created_by_user: Optional['UserservicesUsers'] = None
    domain_user: Optional['UserservicesUsers'] = None
    so: Optional['OrderserviceSalesOrder'] = None


@dataclass
class OrderserviceSalesOrderOutwardedLog:
    id: int
    invoice_path: str = ''
    invoice_number: str = ''
    notes: str = ''
    outwared_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    outwarded_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None
    outwarded_by_user: Optional['UserservicesUsers'] = None
    so: Optional['OrderserviceSalesOrder'] = None


@dataclass
class OrderserviceSalesOrderItemOutwardedLog:
    id: int
    outwarded_quantity: int = 0
    price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: str = ''
    shipping_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    so_item_id_id: Optional[int] = None
    domain_user: Optional['UserservicesUsers'] = None
    so_item: Optional['OrderserviceSalesOrderOrderItems'] = None


# ============================================================
#  REPOSITORY / MANAGER CLASSES
# ============================================================

class EcommerceDatabase:
    def __init__(self):
        self.django_content_types: Dict[int, DjangoContentType] = {}
        self.django_migrations: Dict[int, DjangoMigrations] = {}
        self.django_sessions: Dict[str, DjangoSession] = {}
        self.django_admin_logs: Dict[int, DjangoAdminLog] = {}
        self.auth_groups: Dict[int, AuthGroup] = {}
        self.auth_permissions: Dict[int, AuthPermission] = {}
        self.auth_group_permissions: Dict[int, AuthGroupPermissions] = {}
        self.users: Dict[int, UserservicesUsers] = {}
        self.user_shipping_addresses: Dict[int, UserservicesUserShippingAddress] = {}
        self.activity_logs: Dict[int, UserservicesActivityLog] = {}
        self.modules: Dict[int, UserservicesModules] = {}
        self.user_permissions: Dict[int, UserservicesUserPermissions] = {}
        self.users_groups: Dict[int, UserservicesUsersGroups] = {}
        self.users_user_permissions: Dict[int, UserservicesUsersUserPermissions] = {}
        self.categories: Dict[int, ProductservicesCategories] = {}
        self.products: Dict[int, ProductservicesProducts] = {}
        self.product_questions: Dict[int, ProductservicesProductQuestions] = {}
        self.product_reviews: Dict[int, ProductservicesProductReviews] = {}
        self.warehouses: Dict[int, InventoryservicesWarehouse] = {}
        self.rack_shelves: Dict[int, InventoryservicesRackAndShelvesAndFloor] = {}
        self.inventories: Dict[int, InventoryservicesInventory] = {}
        self.inventory_logs: Dict[int, InventoryservicesInventoryLog] = {}
        self.purchase_orders: Dict[int, OrderservicePurchaseOrder] = {}
        self.purchase_order_items: Dict[int, OrderservicePurchaseOrderItems] = {}
        self.purchase_order_logs: Dict[int, OrderservicePurchaseOrderLogs] = {}
        self.purchase_order_inwarded_logs: Dict[int, OrderservicePurchaseOrderInwardedLog] = {}
        self.purchase_order_item_inwarded_logs: Dict[int, OrderservicePurchaseOrderItemInwardedLog] = {}
        self.sales_orders: Dict[int, OrderserviceSalesOrder] = {}
        self.sales_order_items: Dict[int, OrderserviceSalesOrderOrderItems] = {}
        self.sales_order_logs: Dict[int, OrderserviceSalesOrderLogs] = {}
        self.sales_order_outwarded_logs: Dict[int, OrderserviceSalesOrderOutwardedLog] = {}
        self.sales_order_item_outwarded_logs: Dict[int, OrderserviceSalesOrderItemOutwardedLog] = {}

    # ---- Django Content Type ----
    def add_django_content_type(self, content_type: DjangoContentType) -> DjangoContentType:
        self.django_content_types[content_type.id] = content_type
        return content_type

    def get_django_content_type(self, id: int) -> Optional[DjangoContentType]:
        return self.django_content_types.get(id)

    # ---- Django Migrations ----
    def add_django_migration(self, migration: DjangoMigrations) -> DjangoMigrations:
        self.django_migrations[migration.id] = migration
        return migration

    def get_django_migration(self, id: int) -> Optional[DjangoMigrations]:
        return self.django_migrations.get(id)

    # ---- Django Session ----
    def add_django_session(self, session: DjangoSession) -> DjangoSession:
        self.django_sessions[session.session_key] = session
        return session

    def get_django_session(self, session_key: str) -> Optional[DjangoSession]:
        return self.django_sessions.get(session_key)

    # ---- Django Admin Log ----
    def add_django_admin_log(self, log: DjangoAdminLog) -> DjangoAdminLog:
        if log.content_type_id is not None:
            ct = self.django_content_types.get(log.content_type_id)
            if ct:
                log.content_type = ct
                ct._admin_logs.append(log)
        if log.user_id is not None:
            user = self.users.get(log.user_id)
            if user:
                log.user = user
                user._admin_logs.append(log)
        self.django_admin_logs[log.id] = log
        return log

    def get_django_admin_log(self, id: int) -> Optional[DjangoAdminLog]:
        return self.django_admin_logs.get(id)

    # ---- Auth Group ----
    def add_auth_group(self, group: AuthGroup) -> AuthGroup:
        self.auth_groups[group.id] = group
        return group

    def get_auth_group(self, id: int) -> Optional[AuthGroup]:
        return self.auth_groups.get(id)

    # ---- Auth Permission ----
    def add_auth_permission(self, permission: AuthPermission) -> AuthPermission:
        if permission.content_type_id is not None:
            ct = self.django_content_types.get(permission.content_type_id)
            if ct:
                permission.content_type = ct
                ct._permissions.append(permission)
        self.auth_permissions[permission.id] = permission
        return permission

    def get_auth_permission(self, id: int) -> Optional[AuthPermission]:
        return self.auth_permissions.get(id)

    # ---- Auth Group Permissions ----
    def add_auth_group_permission(self, gp: AuthGroupPermissions) -> AuthGroupPermissions:
        if gp.group_id is not None:
            group = self.auth_groups.get(gp.group_id)
            if group:
                gp.group = group
                group._group_permissions.append(gp)
        if gp.permission_id is not None:
            perm = self.auth_permissions.get(gp.permission_id)
            if perm:
                gp.permission = perm
                perm._group_permissions.append(gp)
        self.auth_group_permissions[gp.id] = gp
        return gp

    def get_auth_group_permission(self, id: int) -> Optional[AuthGroupPermissions]:
        return self.auth_group_permissions.get(id)

    # ---- Users ----
    def add_user(self, user: UserservicesUsers) -> UserservicesUsers:
        if user.domain_user_id_id is not None:
            domain_user = self.users.get(user.domain_user_id_id)
            if domain_user:
                user.domain_user = domain_user
                domain_user._domain_users.append(user)
        self.users[user.id] = user
        return user

    def get_user(self, id: int) -> Optional[UserservicesUsers]:
        return self.users.get(id)

    def get_all_users(self) -> List[UserservicesUsers]:
        return list(self.users.values())

    # ---- User Shipping Address ----
    def add_user_shipping_address(self, addr: UserservicesUserShippingAddress) -> UserservicesUserShippingAddress:
        if addr.user_id is not None:
            user = self.users.get(addr.user_id)
            if user:
                addr.user = user
                user._shipping_addresses.append(addr)
        self.user_shipping_addresses[addr.id] = addr
        return addr

    def get_user_shipping_address(self, id: int) -> Optional[UserservicesUserShippingAddress]:
        return self.user_shipping_addresses.get(id)

    # ---- Activity Log ----
    def add_activity_log(self, log: UserservicesActivityLog) -> UserservicesActivityLog:
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.user_id is not None:
            user = self.users.get(log.user_id)
            if user:
                log.user = user
                user._activity_logs.append(log)
        self.activity_logs[log.id] = log
        return log

    def get_activity_log(self, id: int) -> Optional[UserservicesActivityLog]:
        return self.activity_logs.get(id)

    # ---- Modules ----
    def add_module(self, module: UserservicesModules) -> UserservicesModules:
        if module.parent_id_id is not None:
            parent = self.modules.get(module.parent_id_id)
            if parent:
                module.parent = parent
                parent._children.append(module)
        self.modules[module.id] = module
        return module

    def get_module(self, id: int) -> Optional[UserservicesModules]:
        return self.modules.get(id)

    # ---- User Permissions ----
    def add_user_permission(self, perm: UserservicesUserPermissions) -> UserservicesUserPermissions:
        if perm.module_id_id is not None:
            module = self.modules.get(perm.module_id_id)
            if module:
                perm.module = module
                module._permissions.append(perm)
        if perm.domain_user_id_id is not None:
            domain_user = self.users.get(perm.domain_user_id_id)
            if domain_user:
                perm.domain_user = domain_user
        if perm.user_id is not None:
            user = self.users.get(perm.user_id)
            if user:
                perm.user = user
                user._permissions.append(perm)
        self.user_permissions[perm.id] = perm
        return perm

    def get_user_permission(self, id: int) -> Optional[UserservicesUserPermissions]:
        return self.user_permissions.get(id)

    # ---- Users Groups ----
    def add_users_group(self, ug: UserservicesUsersGroups) -> UserservicesUsersGroups:
        if ug.users_id is not None:
            user = self.users.get(ug.users_id)
            if user:
                ug.user = user
                user._groups.append(ug)
        if ug.group_id is not None:
            group = self.auth_groups.get(ug.group_id)
            if group:
                ug.group = group
                group._user_groups.append(ug)
        self.users_groups[ug.id] = ug
        return ug

    def get_users_group(self, id: int) -> Optional[UserservicesUsersGroups]:
        return self.users_groups.get(id)

    # ---- Users User Permissions ----
    def add_users_user_permission(self, uup: UserservicesUsersUserPermissions) -> UserservicesUsersUserPermissions:
        if uup.users_id is not None:
            user = self.users.get(uup.users_id)
            if user:
                uup.user = user
                user._user_permissions.append(uup)
        if uup.permission_id is not None:
            perm = self.auth_permissions.get(uup.permission_id)
            if perm:
                uup.permission = perm
                perm._user_permissions.append(uup)
        self.users_user_permissions[uup.id] = uup
        return uup

    def get_users_user_permission(self, id: int) -> Optional[UserservicesUsersUserPermissions]:
        return self.users_user_permissions.get(id)

    # ---- Categories ----
    def add_category(self, category: ProductservicesCategories) -> ProductservicesCategories:
        if category.added_by_user_id_id is not None:
            user = self.users.get(category.added_by_user_id_id)
            if user:
                category.added_by_user = user
                user._added_categories.append(category)
        if category.domain_user_id_id is not None:
            domain_user = self.users.get(category.domain_user_id_id)
            if domain_user:
                category.domain_user = domain_user
                domain_user._domain_categories.append(category)
        if category.parent_id_id is not None:
            parent = self.categories.get(category.parent_id_id)
            if parent:
                category.parent = parent
                parent._children.append(category)
        self.categories[category.id] = category
        return category

    def get_category(self, id: int) -> Optional[ProductservicesCategories]:
        return self.categories.get(id)

    def get_all_categories(self) -> List[ProductservicesCategories]:
        return list(self.categories.values())

    # ---- Products ----
    def add_product(self, product: ProductservicesProducts) -> ProductservicesProducts:
        if product.added_by_user_id_id is not None:
            user = self.users.get(product.added_by_user_id_id)
            if user:
                product.added_by_user = user
                user._added_products.append(product)
        if product.domain_user_id_id is not None:
            domain_user = self.users.get(product.domain_user_id_id)
            if domain_user:
                product.domain_user = domain_user
                domain_user._domain_products.append(product)
        if product.category_id_id is not None:
            category = self.categories.get(product.category_id_id)
            if category:
                product.category = category
                category._products.append(product)
        self.products[product.id] = product
        return product

    def get_product(self, id: int) -> Optional[ProductservicesProducts]:
        return self.products.get(id)

    def get_all_products(self) -> List[ProductservicesProducts]:
        return list(self.products.values())

    # ---- Product Questions ----
    def add_product_question(self, pq: ProductservicesProductQuestions) -> ProductservicesProductQuestions:
        if pq.answer_user_id_id is not None:
            user = self.users.get(pq.answer_user_id_id)
            if user:
                pq.answer_user = user
                user._answer_product_questions.append(pq)
        if pq.domain_user_id_id is not None:
            domain_user = self.users.get(pq.domain_user_id_id)
            if domain_user:
                pq.domain_user = domain_user
                domain_user._domain_product_questions.append(pq)
        if pq.question_user_id_id is not None:
            user = self.users.get(pq.question_user_id_id)
            if user:
                pq.question_user = user
                user._question_product_questions.append(pq)
        if pq.product_id_id is not None:
            product = self.products.get(pq.product_id_id)
            if product:
                pq.product = product
                product._questions.append(pq)
        self.product_questions[pq.id] = pq
        return pq

    def get_product_question(self, id: int) -> Optional[ProductservicesProductQuestions]:
        return self.product_questions.get(id)

    # ---- Product Reviews ----
    def add_product_review(self, pr: ProductservicesProductReviews) -> ProductservicesProductReviews:
        if pr.domain_user_id_id is not None:
            domain_user = self.users.get(pr.domain_user_id_id)
            if domain_user:
                pr.domain_user = domain_user
                domain_user._domain_product_reviews.append(pr)
        if pr.review_user_id_id is not None:
            user = self.users.get(pr.review_user_id_id)
            if user:
                pr.review_user = user
                user._review_product_reviews.append(pr)
        if pr.product_id_id is not None:
            product = self.products.get(pr.product_id_id)
            if product:
                pr.product = product
                product._reviews.append(pr)
        self.product_reviews[pr.id] = pr
        return pr

    def get_product_review(self, id: int) -> Optional[ProductservicesProductReviews]:
        return self.product_reviews.get(id)

    # ---- Warehouse ----
    def add_warehouse(self, warehouse: InventoryservicesWarehouse) -> InventoryservicesWarehouse:
        if warehouse.added_by_user_id_id is not None:
            user = self.users.get(warehouse.added_by_user_id_id)
            if user:
                warehouse.added_by_user = user
                user._added_warehouses.append(warehouse)
        if warehouse.domain_user_id_id is not None:
            domain_user = self.users.get(warehouse.domain_user_id_id)
            if domain_user:
                warehouse.domain_user = domain_user
                domain_user._domain_warehouses.append(warehouse)
        if warehouse.warehouse_manager_id is not None:
            manager = self.users.get(warehouse.warehouse_manager_id)
            if manager:
                warehouse.warehouse_manager = manager
                manager._managed_warehouses.append(warehouse)
        self.warehouses[warehouse.id] = warehouse
        return warehouse

    def get_warehouse(self, id: int) -> Optional[InventoryservicesWarehouse]:
        return self.warehouses.get(id)

    def get_all_warehouses(self) -> List[InventoryservicesWarehouse]:
        return list(self.warehouses.values())

    # ---- Rack and Shelves and Floor ----
    def add_rack_shelf_floor(self, rsf: InventoryservicesRackAndShelvesAndFloor) -> InventoryservicesRackAndShelvesAndFloor:
        if rsf.added_by_user_id_id is not None:
            user = self.users.get(rsf.added_by_user_id_id)
            if user:
                rsf.added_by_user = user
                user._added_rack_shelves.append(rsf)
        if rsf.domain_user_id_id is not None:
            domain_user = self.users.get(rsf.domain_user_id_id)
            if domain_user:
                rsf.domain_user = domain_user
                domain_user._domain_rack_shelves.append(rsf)
        if rsf.warehouse_id_id is not None:
            warehouse = self.warehouses.get(rsf.warehouse_id_id)
            if warehouse:
                rsf.warehouse = warehouse
                warehouse._rack_shelves.append(rsf)
        self.rack_shelves[rsf.id] = rsf
        return rsf

    def get_rack_shelf_floor(self, id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self.rack_shelves.get(id)

    # ---- Inventory ----
    def add_inventory(self, inv: InventoryservicesInventory) -> InventoryservicesInventory:
        if inv.added_by_user_id_id is not None:
            user = self.users.get(inv.added_by_user_id_id)
            if user:
                inv.added_by_user = user
                user._added_inventories.append(inv)
        if inv.domain_user_id_id is not None:
            domain_user = self.users.get(inv.domain_user_id_id)
            if domain_user:
                inv.domain_user = domain_user
                domain_user._domain_inventories.append(inv)
        if inv.product_id_id is not None:
            product = self.products.get(inv.product_id_id)
            if product:
                inv.product = product
                product._inventories.append(inv)
        if inv.purchase_order_id_id is not None:
            po = self.purchase_orders.get(inv.purchase_order_id_id)
            if po:
                inv.purchase_order = po
                po._inventories.append(inv)
        if inv.purchase_order_item_id_id is not None:
            poi = self.purchase_order_items.get(inv.purchase_order_item_id_id)
            if poi:
                inv.purchase_order_item = poi
                poi._inventories.append(inv)
        if inv.purchase_order_item_inwarded_item_id_id is not None:
            poiil = self.purchase_order_item_inwarded_logs.get(inv.purchase_order_item_inwarded_item_id_id)
            if poiil:
                inv.purchase_order_item_inwarded_item = poiil
                poiil._inventories.append(inv)
        if inv.rack_shelf_floor_id_id is not None:
            rsf = self.rack_shelves.get(inv.rack_shelf_floor_id_id)
            if rsf:
                inv.rack_shelf_floor = rsf
                rsf._inventories.append(inv)
        if inv.warehouse_id_id is not None:
            warehouse = self.warehouses.get(inv.warehouse_id_id)
            if warehouse:
                inv.warehouse = warehouse
                warehouse._inventories.append(inv)
        self.inventories[inv.id] = inv
        return inv

    def get_inventory(self, id: int) -> Optional[InventoryservicesInventory]:
        return self.inventories.get(id)

    def get_all_inventories(self) -> List[InventoryservicesInventory]:
        return list(self.inventories.values())

    # ---- Inventory Log ----
    def add_inventory_log(self, log: InventoryservicesInventoryLog) -> InventoryservicesInventoryLog:
        if log.added_by_user_id_id is not None:
            user = self.users.get(log.added_by_user_id_id)
            if user:
                log.added_by_user = user
                user._added_inventory_logs.append(log)
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
                domain_user._domain_inventory_logs.append(log)
        if log.inventory_id_id is not None:
            inv = self.inventories.get(log.inventory_id_id)
            if inv:
                log.inventory = inv
                inv._inventory_logs.append(log)
        if log.po_id_id is not None:
            po = self.purchase_orders.get(log.po_id_id)
            if po:
                log.po = po
                po._inventory_logs.append(log)
        if log.so_id_id is not None:
            so = self.sales_orders.get(log.so_id_id)
            if so:
                log.so = so
                so._inventory_logs.append(log)
        if log.rack_shelf_floor_id_id is not None:
            rsf = self.rack_shelves.get(log.rack_shelf_floor_id_id)
            if rsf:
                log.rack_shelf_floor = rsf
                rsf._inventory_logs.append(log)
        if log.warehouse_id_id is not None:
            warehouse = self.warehouses.get(log.warehouse_id_id)
            if warehouse:
                log.warehouse = warehouse
                warehouse._inventory_logs.append(log)
        self.inventory_logs[log.id] = log
        return log

    def get_inventory_log(self, id: int) -> Optional[InventoryservicesInventoryLog]:
        return self.inventory_logs.get(id)

    # ---- Purchase Order ----
    def add_purchase_order(self, po: OrderservicePurchaseOrder) -> OrderservicePurchaseOrder:
        if po.approved_by_user_id_id is not None:
            user = self.users.get(po.approved_by_user_id_id)
            if user:
                po.approved_by_user = user
        if po.cancelled_by_user_id_id is not None:
            user = self.users.get(po.cancelled_by_user_id_id)
            if user:
                po.cancelled_by_user = user
        if po.created_by_user_id_id is not None:
            user = self.users.get(po.created_by_user_id_id)
            if user:
                po.created_by_user = user
                user._created_purchase_orders.append(po)
        if po.domain_user_id_id is not None:
            domain_user = self.users.get(po.domain_user_id_id)
            if domain_user:
                po.domain_user = domain_user
                domain_user._domain_purchase_orders.append(po)
        if po.last_updated_by_user_id_id is not None:
            user = self.users.get(po.last_updated_by_user_id_id)
            if user:
                po.last_updated_by_user = user
        if po.received_by_user_id_id is not None:
            user = self.users.get(po.received_by_user_id_id)
            if user:
                po.received_by_user = user
        if po.returned_by_user_id_id is not None:
            user = self.users.get(po.returned_by_user_id_id)
            if user:
                po.returned_by_user = user
        if po.supplier_id_id is not None:
            supplier = self.users.get(po.supplier_id_id)
            if supplier:
                po.supplier = supplier
                supplier._supplier_purchase_orders.append(po)
        if po.updated_by_user_id_id is not None:
            user = self.users.get(po.updated_by_user_id_id)
            if user:
                po.updated_by_user = user
        if po.warehouse_id_id is not None:
            warehouse = self.warehouses.get(po.warehouse_id_id)
            if warehouse:
                po.warehouse = warehouse
                warehouse._purchase_orders.append(po)
        self.purchase_orders[po.id] = po
        return po

    def get_purchase_order(self, id: int) -> Optional[OrderservicePurchaseOrder]:
        return self.purchase_orders.get(id)

    def get_all_purchase_orders(self) -> List[OrderservicePurchaseOrder]:
        return list(self.purchase_orders.values())

    # ---- Purchase Order Items ----
    def add_purchase_order_item(self, poi: OrderservicePurchaseOrderItems) -> OrderservicePurchaseOrderItems:
        if poi.approved_by_user_id_id is not None:
            user = self.users.get(poi.approved_by_user_id_id)
            if user:
                poi.approved_by_user = user
        if poi.cancelled_by_user_id_id is not None:
            user = self.users.get(poi.cancelled_by_user_id_id)
            if user:
                poi.cancelled_by_user = user
        if poi.created_by_user_id_id is not None:
            user = self.users.get(poi.created_by_user_id_id)
            if user:
                poi.created_by_user = user
        if poi.domain_user_id_id is not None:
            domain_user = self.users.get(poi.domain_user_id_id)
            if domain_user:
                poi.domain_user = domain_user
        if poi.last_updated_by_user_id_id is not None:
            user = self.users.get(poi.last_updated_by_user_id_id)
            if user:
                poi.last_updated_by_user = user
        if poi.received_by_user_id_id is not None:
            user = self.users.get(poi.received_by_user_id_id)
            if user:
                poi.received_by_user = user
        if poi.returned_by_user_id_id is not None:
            user = self.users.get(poi.returned_by_user_id_id)
            if user:
                poi.returned_by_user = user
        if poi.po_id_id is not None:
            po = self.purchase_orders.get(poi.po_id_id)
            if po:
                poi.po = po
                po._items.append(poi)
        if poi.product_id_id is not None:
            product = self.products.get(poi.product_id_id)
            if product:
                poi.product = product
                product._purchase_order_items.append(poi)
        if poi.updated_by_user_id_id is not None:
            user = self.users.get(poi.updated_by_user_id_id)
            if user:
                poi.updated_by_user = user
        self.purchase_order_items[poi.id] = poi
        return poi

    def get_purchase_order_item(self, id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self.purchase_order_items.get(id)

    # ---- Purchase Order Logs ----
    def add_purchase_order_log(self, log: OrderservicePurchaseOrderLogs) -> OrderservicePurchaseOrderLogs:
        if log.created_by_user_id_id is not None:
            user = self.users.get(log.created_by_user_id_id)
            if user:
                log.created_by_user = user
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.po_id_id is not None:
            po = self.purchase_orders.get(log.po_id_id)
            if po:
                log.po = po
                po._logs.append(log)
        self.purchase_order_logs[log.id] = log
        return log

    def get_purchase_order_log(self, id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self.purchase_order_logs.get(id)

    # ---- Purchase Order Inwarded Log ----
    def add_purchase_order_inwarded_log(self, log: OrderservicePurchaseOrderInwardedLog) -> OrderservicePurchaseOrderInwardedLog:
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.inwarded_by_user_id_id is not None:
            user = self.users.get(log.inwarded_by_user_id_id)
            if user:
                log.inwarded_by_user = user
        if log.po_id_id is not None:
            po = self.purchase_orders.get(log.po_id_id)
            if po:
                log.po = po
                po._inwarded_logs.append(log)
        self.purchase_order_inwarded_logs[log.id] = log
        return log

    def get_purchase_order_inwarded_log(self, id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self.purchase_order_inwarded_logs.get(id)

    # ---- Purchase Order Item Inwarded Log ----
    def add_purchase_order_item_inwarded_log(self, log: OrderservicePurchaseOrderItemInwardedLog) -> OrderservicePurchaseOrderItemInwardedLog:
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.po_item_id_id is not None:
            poi = self.purchase_order_items.get(log.po_item_id_id)
            if poi:
                log.po_item = poi
                poi._inwarded_logs.append(log)
        self.purchase_order_item_inwarded_logs[log.id] = log
        return log

    def get_purchase_order_item_inwarded_log(self, id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self.purchase_order_item_inwarded_logs.get(id)

    # ---- Sales Order ----
    def add_sales_order(self, so: OrderserviceSalesOrder) -> OrderserviceSalesOrder:
        if so.approved_by_user_id_id is not None:
            user = self.users.get(so.approved_by_user_id_id)
            if user:
                so.approved_by_user = user
        if so.cancelled_by_user_id_id is not None:
            user = self.users.get(so.cancelled_by_user_id_id)
            if user:
                so.cancelled_by_user = user
        if so.created_by_user_id_id is not None:
            user = self.users.get(so.created_by_user_id_id)
            if user:
                so.created_by_user = user
                user._created_sales_orders.append(so)
        if so.customer_id_id is not None:
            customer = self.users.get(so.customer_id_id)
            if customer:
                so.customer = customer
                customer._customer_sales_orders.append(so)
        if so.domain_user_id_id is not None:
            domain_user = self.users.get(so.domain_user_id_id)
            if domain_user:
                so.domain_user = domain_user
                domain_user._domain_sales_orders.append(so)
        if so.last_updated_by_user_id_id is not None:
            user = self.users.get(so.last_updated_by_user_id_id)
            if user:
                so.last_updated_by_user = user
        if so.received_by_user_id_id is not None:
            user = self.users.get(so.received_by_user_id_id)
            if user:
                so.received_by_user = user
        if so.returned_by_user_id_id is not None:
            user = self.users.get(so.returned_by_user_id_id)
            if user:
                so.returned_by_user = user
        if so.po_id_id is not None:
            po = self.purchase_orders.get(so.po_id_id)
            if po:
                so.po = po
        if so.product_id_id is not None:
            product = self.products.get(so.product_id_id)
            if product:
                so.product = product
        if so.updated_by_user_id_id is not None:
            user = self.users.get(so.updated_by_user_id_id)
            if user:
                so.updated_by_user = user
        self.sales_orders[so.id] = so
        return so

    def get_sales_order(self, id: int) -> Optional[OrderserviceSalesOrder]:
        return self.sales_orders.get(id)

    def get_all_sales_orders(self) -> List[OrderserviceSalesOrder]:
        return list(self.sales_orders.values())

    # ---- Sales Order Items ----
    def add_sales_order_item(self, soi: OrderserviceSalesOrderOrderItems) -> OrderserviceSalesOrderOrderItems:
        if soi.approved_by_user_id_id is not None:
            user = self.users.get(soi.approved_by_user_id_id)
            if user:
                soi.approved_by_user = user
        if soi.cancelled_by_user_id_id is not None:
            user = self.users.get(soi.cancelled_by_user_id_id)
            if user:
                soi.cancelled_by_user = user
        if soi.created_by_user_id_id is not None:
            user = self.users.get(soi.created_by_user_id_id)
            if user:
                soi.created_by_user = user
        if soi.domain_user_id_id is not None:
            domain_user = self.users.get(soi.domain_user_id_id)
            if domain_user:
                soi.domain_user = domain_user
        if soi.product_id_id is not None:
            product = self.products.get(soi.product_id_id)
            if product:
                soi.product = product
                product._sales_order_items.append(soi)
        if soi.returned_by_user_id_id is not None:
            user = self.users.get(soi.returned_by_user_id_id)
            if user:
                soi.returned_by_user = user
        if soi.shipped_by_user_id_id is not None:
            user = self.users.get(soi.shipped_by_user_id_id)
            if user:
                soi.shipped_by_user = user
        if soi.so_id_id is not None:
            so = self.sales_orders.get(soi.so_id_id)
            if so:
                soi.so = so
                so._items.append(soi)
        if soi.updated_by_user_id_id is not None:
            user = self.users.get(soi.updated_by_user_id_id)
            if user:
                soi.updated_by_user = user
        self.sales_order_items[soi.id] = soi
        return soi

    def get_sales_order_item(self, id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self.sales_order_items.get(id)

    # ---- Sales Order Logs ----
    def add_sales_order_log(self, log: OrderserviceSalesOrderLogs) -> OrderserviceSalesOrderLogs:
        if log.created_by_user_id_id is not None:
            user = self.users.get(log.created_by_user_id_id)
            if user:
                log.created_by_user = user
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.so_id_id is not None:
            so = self.sales_orders.get(log.so_id_id)
            if so:
                log.so = so
                so._logs.append(log)
        self.sales_order_logs[log.id] = log
        return log

    def get_sales_order_log(self, id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self.sales_order_logs.get(id)

    # ---- Sales Order Outwarded Log ----
    def add_sales_order_outwarded_log(self, log: OrderserviceSalesOrderOutwardedLog) -> OrderserviceSalesOrderOutwardedLog:
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.outwarded_by_user_id_id is not None:
            user = self.users.get(log.outwarded_by_user_id_id)
            if user:
                log.outwarded_by_user = user
        if log.so_id_id is not None:
            so = self.sales_orders.get(log.so_id_id)
            if so:
                log.so = so
                so._outwarded_logs.append(log)
        self.sales_order_outwarded_logs[log.id] = log
        return log

    def get_sales_order_outwarded_log(self, id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self.sales_order_outwarded_logs.get(id)

    # ---- Sales Order Item Outwarded Log ----
    def add_sales_order_item_outwarded_log(self, log: OrderserviceSalesOrderItemOutwardedLog) -> OrderserviceSalesOrderItemOutwardedLog:
        if log.domain_user_id_id is not None:
            domain_user = self.users.get(log.domain_user_id_id)
            if domain_user:
                log.domain_user = domain_user
        if log.so_item_id_id is not None:
            soi = self.sales_order_items.get(log.so_item_id_id)
            if soi:
                log.so_item = soi
                soi._outwarded_item_logs.append(log)
        self.sales_order_item_outwarded_logs[log.id] = log
        return log

    def get_sales_order_item_outwarded_log(self, id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self.sales_order_item_outwarded_logs.get(id)

    # ---- Query helpers ----
    def get_products_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [p for p in self.products.values() if p.category_id_id == category_id]

    def get_inventories_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self.inventories.values() if i.warehouse_id_id == warehouse_id]

    def get_inventories_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self.inventories.values() if i.product_id_id == product_id]

    def get_purchase_orders_by_supplier(self, supplier_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self.purchase_orders.values() if po.supplier_id_id == supplier_id]

    def get_sales_orders_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return [so for so in self.sales_orders.values() if so.customer_id_id == customer_id]

    def get_purchase_order_items_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [poi for poi in self.purchase_order_items.values() if poi.po_id_id == po_id]

    def get_sales_order_items_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [soi for soi in self.sales_order_items.values() if soi.so_id_id == so_id]

    def get_rack_shelves_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return [rsf for rsf in self.rack_shelves.values() if rsf.warehouse_id_id == warehouse_id]

    def get_inventory_logs_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [log for log in self.inventory_logs.values() if log.inventory_id_id == inventory_id]

    def get_product_reviews_by_product(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [pr for pr in self.product_reviews.values() if pr.product_id_id == product_id]

    def get_product_questions_by_product(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [pq for pq in self.product_questions.values() if pq.product_id_id == product_id]

    def get_user_shipping_addresses(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [addr for addr in self.user_shipping_addresses.values() if addr.user_id == user_id]

    def get_activity_logs_by_user(self, user_id: int) -> List[UserservicesActivityLog]:
        return [log for log in self.activity_logs.values() if log.user_id == user_id]

    def get_modules_by_parent(self, parent_id: Optional[int]) -> List[UserservicesModules]:
        return [m for m in self.modules.values() if m.parent_id_id == parent_id]

    def get_root_modules(self) -> List[UserservicesModules]:
        return [m for m in self.modules.values() if m.parent_id_id is None]

    def get_categories_by_parent(self, parent_id: Optional[int]) -> List[ProductservicesCategories]:
        return [c for c in self.categories.values() if c.parent_id_id == parent_id]

    def get_root_categories(self) -> List[ProductservicesCategories]:
        return [c for c in self.categories.values() if c.parent_id_id is None]