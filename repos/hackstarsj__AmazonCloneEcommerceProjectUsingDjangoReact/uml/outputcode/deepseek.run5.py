from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional


# ============================================================
#  INVENTORY SERVICE
# ============================================================

@dataclass
class Warehouse:
    id: Optional[int] = None
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
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    warehouse_manager: Optional[User] = None

    inventories: List[Inventory] = field(default_factory=list)
    inventory_logs: List[InventoryLog] = field(default_factory=list)
    rack_shelf_floors: List[RackAndShelvesAndFloor] = field(default_factory=list)
    purchase_orders: List[PurchaseOrder] = field(default_factory=list)


@dataclass
class RackAndShelvesAndFloor:
    id: Optional[int] = None
    name: str = ''
    rack: str = ''
    shelf: str = ''
    floor: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    warehouse: Optional[Warehouse] = None

    inventories: List[Inventory] = field(default_factory=list)
    inventory_logs: List[InventoryLog] = field(default_factory=list)


@dataclass
class Inventory:
    id: Optional[int] = None
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
    buy_price: Decimal = Decimal('0.00')
    sell_price: Decimal = Decimal('0.00')
    tax_percentage: Decimal = Decimal('0.00')
    stock_status: str = ''
    inward_type: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    product: Optional[Product] = None
    purchase_order: Optional[PurchaseOrder] = None
    purchase_order_item: Optional[PurchaseOrderItem] = None
    purchase_order_item_inwarded_item: Optional[PurchaseOrderItemInwardedLog] = None
    rack_shelf_floor: Optional[RackAndShelvesAndFloor] = None
    warehouse: Optional[Warehouse] = None

    logs: List[InventoryLog] = field(default_factory=list)


@dataclass
class InventoryLog:
    id: Optional[int] = None
    quantity: int = 0
    status: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    inventory: Optional[Inventory] = None
    po: Optional[PurchaseOrder] = None
    so: Optional[SalesOrder] = None
    rack_shelf_floor: Optional[RackAndShelvesAndFloor] = None
    warehouse: Optional[Warehouse] = None


# ============================================================
#  ORDER SERVICE
# ============================================================

@dataclass
class PurchaseOrder:
    id: Optional[int] = None
    po_code: str = ''
    po_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ''
    payment_status: str = ''
    total_amount: Decimal = Decimal('0.00')
    paid_amount: Decimal = Decimal('0.00')
    due_amount: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    discount_type: str = ''
    shipping_amount: Decimal = Decimal('0.00')
    shipping_type: str = ''
    shipping_tax_percentage: Decimal = Decimal('0.00')
    shipping_tax_amount: Decimal = Decimal('0.00')
    shipping_cancelled_amount: Decimal = Decimal('0.00')
    shipping_cancelled_tax_amount: Decimal = Decimal('0.00')
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
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

    items: List[PurchaseOrderItem] = field(default_factory=list)
    logs: List[PurchaseOrderLog] = field(default_factory=list)
    inwarded_logs: List[PurchaseOrderInwardedLog] = field(default_factory=list)
    inventories: List[Inventory] = field(default_factory=list)
    inventory_logs: List[InventoryLog] = field(default_factory=list)


@dataclass
class PurchaseOrderItem:
    id: Optional[int] = None
    quantity_ordered: int = 0
    quantity_received: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    buying_price: Decimal = Decimal('0.00')
    selling_price: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    amount_paid: Decimal = Decimal('0.00')
    amount_returned: Decimal = Decimal('0.00')
    amount_cancelled: Decimal = Decimal('0.00')
    amount_ordered: Decimal = Decimal('0.00')
    tax_percentage: Decimal = Decimal('0.00')
    tax_amount: Decimal = Decimal('0.00')
    shipping_tax_percentage: Decimal = Decimal('0.00')
    shipping_amount: Decimal = Decimal('0.00')
    shipping_tax_amount: Decimal = Decimal('0.00')
    shipping_cancelled_amount: Decimal = Decimal('0.00')
    shipping_cancelled_tax_amount: Decimal = Decimal('0.00')
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

    inwarded_logs: List[PurchaseOrderItemInwardedLog] = field(default_factory=list)
    inventories: List[Inventory] = field(default_factory=list)


@dataclass
class PurchaseOrderLog:
    id: Optional[int] = None
    comment: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    po: Optional[PurchaseOrder] = None


@dataclass
class PurchaseOrderInwardedLog:
    id: Optional[int] = None
    invoice_path: str = ''
    invoice_number: str = ''
    notes: str = ''
    inwarded_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[User] = None
    inwarded_by_user: Optional[User] = None
    po: Optional[PurchaseOrder] = None

    item_logs: List[PurchaseOrderItemInwardedLog] = field(default_factory=list)


@dataclass
class PurchaseOrderItemInwardedLog:
    id: Optional[int] = None
    inwarded_quantity: int = 0
    price: Decimal = Decimal('0.00')
    tax_percentage: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    discount_type: str = ''
    shipping_amount: Decimal = Decimal('0.00')
    shipping_tax_percentage: Decimal = Decimal('0.00')
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[User] = None
    po_item: Optional[PurchaseOrderItem] = None

    inventories: List[Inventory] = field(default_factory=list)


@dataclass
class SalesOrder:
    id: Optional[int] = None
    so_code: str = ''
    so_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ''
    payment_status: str = ''
    total_amount: Decimal = Decimal('0.00')
    paid_amount: Decimal = Decimal('0.00')
    due_amount: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    discount_type: str = ''
    shipping_amount: Decimal = Decimal('0.00')
    shipping_type: str = ''
    shipping_tax_percentage: Decimal = Decimal('0.00')
    shipping_tax_amount: Decimal = Decimal('0.00')
    shipping_cancelled_amount: Decimal = Decimal('0.00')
    shipping_cancelled_tax_amount: Decimal = Decimal('0.00')
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
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

    items: List[SalesOrderItem] = field(default_factory=list)
    logs: List[SalesOrderLog] = field(default_factory=list)
    outwarded_logs: List[SalesOrderOutwardedLog] = field(default_factory=list)
    inventory_logs: List[InventoryLog] = field(default_factory=list)


@dataclass
class SalesOrderItem:
    id: Optional[int] = None
    quantity_ordered: int = 0
    quantity_delivered: int = 0
    quantity_shipped: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    purchase_price: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    discount_type: str = ''
    amount_paid: Decimal = Decimal('0.00')
    amount_returned: Decimal = Decimal('0.00')
    amount_cancelled: Decimal = Decimal('0.00')
    amount_ordered: Decimal = Decimal('0.00')
    tax_percentage: Decimal = Decimal('0.00')
    tax_amount: Decimal = Decimal('0.00')
    shipping_amount: Decimal = Decimal('0.00')
    shipping_type: str = ''
    shipping_tax_amount: Decimal = Decimal('0.00')
    shipping_cancelled_amount: Decimal = Decimal('0.00')
    shipping_cancelled_tax_amount: Decimal = Decimal('0.00')
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ''
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user: Optional[User] = None
    cancelled_by_user: Optional[User] = None
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    product: Optional[Product] = None
    returned_by_user: Optional[User] = None
    shipped_by_user: Optional[User] = None
    so: Optional[SalesOrder] = None
    updated_by_user: Optional[User] = None

    outwarded_logs: List[SalesOrderItemOutwardedLog] = field(default_factory=list)


@dataclass
class SalesOrderLog:
    id: Optional[int] = None
    comment: str = ''
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    so: Optional[SalesOrder] = None


@dataclass
class SalesOrderOutwardedLog:
    id: Optional[int] = None
    invoice_path: str = ''
    invoice_number: str = ''
    notes: str = ''
    outwared_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[User] = None
    outwarded_by_user: Optional[User] = None
    so: Optional[SalesOrder] = None

    item_logs: List[SalesOrderItemOutwardedLog] = field(default_factory=list)


@dataclass
class SalesOrderItemOutwardedLog:
    id: Optional[int] = None
    outwarded_quantity: int = 0
    price: Decimal = Decimal('0.00')
    tax_percentage: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    discount_type: str = ''
    shipping_amount: Decimal = Decimal('0.00')
    shipping_tax_percentage: Decimal = Decimal('0.00')
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[User] = None
    so_item: Optional[SalesOrderItem] = None


# ============================================================
#  PRODUCT SERVICE
# ============================================================

@dataclass
class Category:
    id: Optional[int] = None
    name: str = ''
    image: str = ''
    description: str = ''
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[User] = None
    domain_user: Optional[User] = None
    parent: Optional[Category] = None

    subcategories: List[Category] = field(default_factory=list)
    products: List[Product] = field(default_factory=list)


@dataclass
class Product:
    id: Optional[int] = None
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
    added_by_user: Optional[User] = None
    category: Optional[Category] = None
    domain_user: Optional[User] = None

    inventories: List[Inventory] = field(default_factory=list)
    questions: List[ProductQuestion] = field(default_factory=list)
    reviews: List[ProductReview] = field(default_factory=list)
    purchase_order_items: List[PurchaseOrderItem] = field(default_factory=list)
    sales_order_items: List[SalesOrderItem] = field(default_factory=list)


@dataclass
class ProductQuestion:
    id: Optional[int] = None
    question: str = ''
    answer: str = ''
    status: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user: Optional[User] = None
    domain_user: Optional[User] = None
    question_user: Optional[User] = None
    product: Optional[Product] = None


@dataclass
class ProductReview:
    id: Optional[int] = None
    review_images: Optional[Dict[str, Any]] = None
    rating: float = 0.0
    reviews: str = ''
    status: str = ''
    domain_user: Optional[User] = None
    review_user: Optional[User] = None
    product: Optional[Product] = None


# ============================================================
#  USER SERVICE
# ============================================================

@dataclass
class User:
    id: Optional[int] = None
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
    department: str = ''
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
    domain_user: Optional[User] = None

    shipping_addresses: List[UserShippingAddress] = field(default_factory=list)
    activity_logs: List[ActivityLog] = field(default_factory=list)
    user_permissions: List[UserPermission] = field(default_factory=list)
    groups: List[UserGroup] = field(default_factory=list)
    user_user_permissions: List[UserUserPermission] = field(default_factory=list)
    managed_warehouses: List[Warehouse] = field(default_factory=list)
    added_inventories: List[Inventory] = field(default_factory=list)
    domain_inventories: List[Inventory] = field(default_factory=list)
    # add more reverse relations as needed, but skipping for brevity


@dataclass
class UserShippingAddress:
    id: Optional[int] = None
    address_type: str = ''
    address: str = ''
    city: str = ''
    state: str = ''
    pincode: str = ''
    country: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[User] = None


@dataclass
class ActivityLog:
    id: Optional[int] = None
    activity: str = ''
    activity_type: str = ''
    activity_date: Optional[datetime] = None
    activity_ip: str = ''
    activity_device: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[User] = None
    user: Optional[User] = None


@dataclass
class Module:
    id: Optional[int] = None
    module_name: str = ''
    module_icon: str = ''
    is_menu: bool = False
    is_active: bool = True
    module_url: str = ''
    display_order: int = 0
    module_description: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent: Optional[Module] = None

    sub_modules: List[Module] = field(default_factory=list)
    permissions: List[UserPermission] = field(default_factory=list)


@dataclass
class UserPermission:
    id: Optional[int] = None
    is_view: bool = True
    is_add: bool = False
    is_edit: bool = False
    is_delete: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module: Optional[Module] = None
    domain_user: Optional[User] = None
    user: Optional[User] = None


@dataclass
class UserGroup:
    id: Optional[int] = None
    user: Optional[User] = None
    group: Optional[Group] = None


@dataclass
class UserUserPermission:
    id: Optional[int] = None
    user: Optional[User] = None
    permission: Optional[Permission] = None


# ============================================================
#  DJANGO FRAMEWORK / AUTH
# ============================================================

@dataclass
class ContentType:
    id: Optional[int] = None
    app_label: str = ''
    model: str = ''


@dataclass
class Permission:
    id: Optional[int] = None
    name: str = ''
    codename: str = ''
    content_type: Optional[ContentType] = None


@dataclass
class Group:
    id: Optional[int] = None
    name: str = ''

    permissions: List[GroupPermission] = field(default_factory=list)
    user_groups: List[UserGroup] = field(default_factory=list)


@dataclass
class GroupPermission:
    id: Optional[int] = None
    group: Optional[Group] = None
    permission: Optional[Permission] = None


@dataclass
class DjangoAdminLog:
    id: Optional[int] = None
    action_time: Optional[datetime] = None
    object_id: str = ''
    object_repr: str = ''
    action_flag: int = 0
    change_message: str = ''
    content_type: Optional[ContentType] = None
    user: Optional[User] = None


@dataclass
class DjangoMigrations:
    id: Optional[int] = None
    app: str = ''
    name: str = ''
    applied: Optional[datetime] = None


@dataclass
class DjangoSession:
    session_key: str = ''
    session_data: str = ''
    expire_date: Optional[datetime] = None


# Ensure forward references are resolved by placing the classes in the correct order.
# The __future__ annotations import allows forward references as strings.
# Additional reverse relationships can be added on demand.
# This is a complete runnable module that defines all entities and their relationships.