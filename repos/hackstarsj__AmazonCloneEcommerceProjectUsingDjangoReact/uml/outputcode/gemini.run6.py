from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

@dataclass
class DjangoContentType:
    id: int
    app_label: str
    model: str

@dataclass
class DjangoMigration:
    id: int
    app: str
    name: str
    applied: datetime

@dataclass
class DjangoSession:
    session_key: str
    session_data: str
    expire_date: datetime

@dataclass
class AuthGroup:
    id: int
    name: str
    permissions: List[AuthPermission] = field(default_factory=list)

@dataclass
class AuthPermission:
    id: int
    name: str
    codename: str
    content_type_id: int
    content_type: Optional[DjangoContentType] = None

@dataclass
class AuthGroupPermission:
    id: int
    group_id: int
    permission_id: int
    group: Optional[AuthGroup] = None
    permission: Optional[AuthPermission] = None

@dataclass
class DjangoAdminLog:
    id: int
    action_time: datetime
    object_id: str
    object_repr: str
    action_flag: int
    change_message: str
    content_type_id: int
    user_id: int
    content_type: Optional[DjangoContentType] = None
    user: Optional[User] = None

@dataclass
class User:
    id: int
    is_superuser: bool
    first_name: str
    last_name: str
    is_staff: bool
    is_active: bool
    date_joined: datetime
    name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    profile_pic: str
    account_status: str
    role: str
    dob: date
    username: str
    password: str
    social_media_links: Dict[str, Any]
    addition_details: Dict[str, Any]
    language: str
    departMent: str
    designation: str
    time_zone: str
    last_login: datetime
    last_device: str
    last_ip: str
    currency: str
    domain_name: str
    plan_type: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: Optional[int] = None
    domain_user: Optional[User] = None

@dataclass
class UserShippingAddress:
    id: int
    address_type: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    user: Optional[User] = None

@dataclass
class ActivityLog:
    id: int
    activity: str
    activity_type: str
    activity_date: datetime
    activity_ip: str
    activity_device: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    user_id: int
    domain_user: Optional[User] = None
    user: Optional[User] = None

@dataclass
class Module:
    id: int
    module_name: str
    module_icon: str
    is_menu: bool
    is_active: bool
    module_url: str
    display_order: int
    module_description: str
    created_at: datetime
    updated_at: datetime
    parent_id_id: Optional[int] = None
    parent: Optional[Module] = None

@dataclass
class UserPermission:
    id: int
    is_view: bool
    is_add: bool
    is_edit: bool
    is_delete: bool
    created_at: datetime
    updated_at: datetime
    module_id_id: int
    domain_user_id_id: int
    user_id: int
    module: Optional[Module] = None
    domain_user: Optional[User] = None
    user: Optional[User] = None

@dataclass
class UserGroup:
    id: int
    users_id: int
    group_id: int
    user: Optional[User] = None
    group: Optional[AuthGroup] = None

@dataclass
class UserUserPermission:
    id: int
    users_id: int
    permission_id: int
    user: Optional[User] = None
    permission: Optional[AuthPermission] = None

@dataclass
class Category:
    id: int
    name: str
    image: str
    description: str
    display_order: int
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    parent_id_id: Optional[int] = None
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    parent: Optional[Category] = None

@dataclass
class Product:
    id: int
    name: str
    image: Dict[str, Any]
    description: str
    specifications: Dict[str, Any]
    html_description: str
    highlights: Dict[str, Any]
    sku: str
    initial_buying_price: float
    initial_selling_price: float
    weight: float
    dimensions: str
    uom: str
    color: str
    tax_percentage: float
    brand: str
    brand_model: str
    status: str
    seo_title: str
    seo_description: str
    seo_keywords: Dict[str, Any]
    addition_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    category_id_id: int
    domain_user_id_id: int
    added_by_user: Optional[User] = None
    category: Optional[Category] = None
    domain_user: Optional[User] = None

@dataclass
class ProductQuestion:
    id: int
    question: str
    answer: str
    status: str
    created_at: datetime
    updated_at: datetime
    answer_user_id_id: int
    domain_user_id_id: int
    question_user_id_id: int
    product_id_id: int
    answer_user: Optional[User] = None
    domain_user: Optional[User] = None
    question_user: Optional[User] = None
    product: Optional[Product] = None

@dataclass
class ProductReview:
    id: int
    review_images: Dict[str, Any]
    rating: float
    reviews: str
    status: str
    domain_user_id_id: int
    review_user_id_id: int
    product_id_id: int
    domain_user: Optional[User] = None
    review_user: Optional[User] = None
    product: Optional[Product] = None

@dataclass
class Warehouse:
    id: int
    name: str
    address: str
    city: str
    state: str
    country: str
    pincode: str
    phone: str
    email: str
    status: str
    size: str
    capacity: str
    warehouse_type: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    warehouse_manager_id: int
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    warehouse_manager: Optional[User] = None

@dataclass
class RackAndShelvesAndFloor:
    id: int
    name: str
    rack: str
    shelf: str
    floor: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    warehouse_id_id: int
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    warehouse: Optional[Warehouse] = None

@dataclass
class PurchaseOrder:
    id: int
    po_code: str
    po_date: datetime
    expected_delivery_date: datetime
    payment_terms: str
    payment_status: str
    total_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_type: str
    shipping_tax_percentage: Decimal
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: str
    received_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: Optional[int]
    cancelled_by_user_id_id: Optional[int]
    created_by_user_id_id: int
    domain_user_id_id: int
    last_updated_by_user_id_id: int
    received_by_user_id_id: Optional[int]
    returned_by_user_id_id: Optional[int]
    supplier_id_id: int
    updated_by_user_id_id: int
    warehouse_id_id: int
    approved_by_user: Optional[User] = None
    cancelled_by_user: Optional[User] = None
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    last_updated_by_user: Optional[User] = None
    received_by_user: Optional[User] = None
    returned_by_user: Optional[User] = None
    supplier: Optional[User] = None
    updated_by_user: Optional[User] = None
    warehouse: Optional[Warehouse] = None

    def __post_init__(self):
        if self.total_amount < 0:
            raise ValueError("Total amount cannot be negative")

@dataclass
class PurchaseOrderItem:
    id: int
    quantity_ordered: int
    quantity_received: int
    quantity_cancelled: int
    quantity_returned: int
    buying_price: Decimal
    selling_price: Decimal
    discount_amount: Decimal
    amount_paid: Decimal
    amount_returned: Decimal
    amount_cancelled: Decimal
    amount_ordered: Decimal
    tax_percentage: Decimal
    tax_amount: Decimal
    shipping_tax_percentage: Decimal
    shipping_amount: Decimal
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    discount_type: str
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: str
    received_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: Optional[int]
    cancelled_by_user_id_id: Optional[int]
    created_by_user_id_id: int
    domain_user_id_id: int
    last_updated_by_user_id_id: int
    received_by_user_id_id: Optional[int]
    returned_by_user_id_id: Optional[int]
    po_id_id: int
    product_id_id: int
    updated_by_user_id_id: int
    approved_by_user: Optional[User] = None
    cancelled_by_user: Optional[User] = None
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    last_updated_by_user: Optional[User] = None
    received_by_user: Optional[User] = None
    returned_by_user: Optional[User] = None
    po: Optional[PurchaseOrder] = None
    product: Optional[Product] = None
    updated_by_user: Optional[User] = None

@dataclass
class PurchaseOrderLog:
    id: int
    comment: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by_user_id_id: int
    domain_user_id_id: int
    po_id_id: int
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    po: Optional[PurchaseOrder] = None

@dataclass
class PurchaseOrderInwardedLog:
    id: int
    invoice_path: str
    invoice_number: str
    notes: str
    inwarded_at: datetime
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    inwarded_by_user_id_id: int
    po_id_id: int
    domain_user: Optional[User] = None
    inwarded_by_user: Optional[User] = None
    po: Optional[PurchaseOrder] = None

@dataclass
class PurchaseOrderItemInwardedLog:
    id: int
    inwarded_quantity: int
    price: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_tax_percentage: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    po_item_id_id: int
    domain_user: Optional[User] = None
    po_item: Optional[PurchaseOrderItem] = None

@dataclass
class SalesOrder:
    id: int
    so_code: str
    so_date: datetime
    expected_delivery_date: datetime
    payment_terms: str
    payment_status: str
    total_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_type: str
    shipping_tax_percentage: Decimal
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: str
    received_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: Optional[int]
    cancelled_by_user_id_id: Optional[int]
    created_by_user_id_id: int
    customer_id_id: int
    domain_user_id_id: int
    last_updated_by_user_id_id: int
    received_by_user_id_id: Optional[int]
    returned_by_user_id_id: Optional[int]
    po_id_id: Optional[int]
    product_id_id: Optional[int]
    updated_by_user_id_id: int
    approved_by_user: Optional[User] = None
    cancelled_by_user: Optional[User] = None
    created_by_user: Optional[User] = None
    customer: Optional[User] = None
    domain_user: Optional[User] = None
    last_updated_by_user: Optional[User] = None
    received_by_user: Optional[User] = None
    returned_by_user: Optional[User] = None
    po: Optional[PurchaseOrder] = None
    product: Optional[Product] = None
    updated_by_user: Optional[User] = None

    def __post_init__(self):
        if self.total_amount < 0:
            raise ValueError("Total amount cannot be negative")

@dataclass
class SalesOrderOrderItem:
    id: int
    quantity_ordered: int
    quantity_delivered: int
    quantity_shipped: int
    quantity_cancelled: int
    quantity_returned: int
    purchase_price: Decimal
    discount_amount: Decimal
    discount_type: str
    amount_paid: Decimal
    amount_returned: Decimal
    amount_cancelled: Decimal
    amount_ordered: Decimal
    tax_percentage: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    shipping_type: str
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: str
    shipped_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: Optional[int]
    cancelled_by_user_id_id: Optional[int]
    created_by_user_id_id: int
    domain_user_id_id: int
    product_id_id: int
    returned_by_user_id_id: Optional[int]
    shipped_by_user_id_id: Optional[int]
    so_id_id: int
    updated_by_user_id_id: int
    approved_by_user: Optional[User] = None
    cancelled_by_user: Optional[User] = None
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    product: Optional[Product] = None
    returned_by_user: Optional[User] = None
    shipped_by_user: Optional[User] = None
    so: Optional[SalesOrder] = None
    updated_by_user: Optional[User] = None

@dataclass
class SalesOrderLog:
    id: int
    comment: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by_user_id_id: int
    domain_user_id_id: int
    so_id_id: int
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    so: Optional[SalesOrder] = None

@dataclass
class SalesOrderOutwardedLog:
    id: int
    invoice_path: str
    invoice_number: str
    notes: str
    outwared_at: datetime
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    outwarded_by_user_id_id: int
    so_id_id: int
    domain_user: Optional[User] = None
    outwarded_by_user: Optional[User] = None
    so: Optional[SalesOrder] = None

@dataclass
class SalesOrderItemOutwardedLog:
    id: int
    outwarded_quantity: int
    price: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_tax_percentage: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    so_item_id_id: int
    domain_user: Optional[User] = None
    so_item: Optional[SalesOrderOrderItem] = None

@dataclass
class Inventory:
    id: int
    quantity: int
    mrp: str
    batch_number: str
    discount_type: str
    discount_amout: float
    sr_no: str
    mfg_date: datetime
    uom: str
    ptr: str
    received_date: datetime
    expiry_date: datetime
    quantity_inwarded: int
    buy_price: Decimal
    sell_price: Decimal
    tax_percentage: Decimal
    stock_status: str
    inward_type: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    product_id_id: int
    purchase_order_id_id: int
    purchase_order_item_id_id: int
    purchase_order_item_inwarded_item_id_id: Optional[int]
    rack_shelf_floor_id_id: int
    warehouse_id_id: int
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    product: Optional[Product] = None
    purchase_order: Optional[PurchaseOrder] = None
    purchase_order_item: Optional[PurchaseOrderItem] = None
    purchase_order_item_inwarded_item: Optional[PurchaseOrderItemInwardedLog] = None
    rack_shelf_floor: Optional[RackAndShelvesAndFloor] = None
    warehouse: Optional[Warehouse] = None

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("Inventory quantity cannot be negative")

@dataclass
class InventoryLog:
    id: int
    quantity: int
    status: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    inventory_id_id: int
    po_id_id: Optional[int]
    so_id_id: Optional[int]
    rack_shelf_floor_id_id: int
    warehouse_id_id: int
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    inventory: Optional[Inventory] = None
    po: Optional[PurchaseOrder] = None
    so: Optional[SalesOrder] = None
    rack_shelf_floor: Optional[RackAndShelvesAndFloor] = None
    warehouse: Optional[Warehouse] = None