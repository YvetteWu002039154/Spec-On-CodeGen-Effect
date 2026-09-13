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
        if not self.app_label:
            raise ValueError("app_label cannot be empty")
        if not self.model:
            raise ValueError("model cannot be empty")


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

    def __post_init__(self):
        if len(self.session_key) > 40:
            raise ValueError("session_key max length is 40")


@dataclass
class AuthPermission:
    id: int
    name: str
    codename: str
    content_type_id: int
    content_type: Optional[DjangoContentType] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.codename) > 100:
            raise ValueError("codename max length is 100")


@dataclass
class AuthGroup:
    id: int
    name: str

    def __post_init__(self):
        if len(self.name) > 150:
            raise ValueError("name max length is 150")


@dataclass
class AuthGroupPermissions:
    id: int
    group_id: int
    permission_id: int
    group: Optional[AuthGroup] = field(default=None, repr=False)
    permission: Optional[AuthPermission] = field(default=None, repr=False)


@dataclass
class DjangoAdminLog:
    id: int
    action_time: datetime
    object_repr: str
    action_flag: int  # smallint unsigned
    change_message: str
    content_type_id: int
    user_id: int
    object_id: Optional[str] = None
    content_type: Optional[DjangoContentType] = field(default=None, repr=False)
    user: Optional[Any] = field(default=None, repr=False)  # userservices_users

    def __post_init__(self):
        if len(self.object_repr) > 200:
            raise ValueError("object_repr max length is 200")
        if self.action_flag < 0:
            raise ValueError("action_flag must be unsigned")


# ============================================================
#  USER SERVICE
# ============================================================

@dataclass
class UserservicesUsers:
    id: int
    is_superuser: bool = False
    first_name: str = ""
    last_name: str = ""
    is_staff: bool = False
    is_active: bool = True
    date_joined: Optional[datetime] = None
    name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = ""
    profile_pic: str = ""
    account_status: str = ""
    role: str = ""
    dob: Optional[date] = None
    username: str = ""
    password: str = ""
    social_media_links: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    language: str = ""
    departMent: str = ""
    designation: str = ""
    time_zone: str = ""
    last_login: Optional[datetime] = None
    last_device: str = ""
    last_ip: str = ""
    currency: str = ""
    domain_name: str = ""
    plan_type: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.first_name) > 150:
            raise ValueError("first_name max length is 150")
        if len(self.last_name) > 150:
            raise ValueError("last_name max length is 150")
        if len(self.name) > 100:
            raise ValueError("name max length is 100")
        if len(self.email) > 254:
            raise ValueError("email max length is 254")
        if len(self.phone) > 15:
            raise ValueError("phone max length is 15")
        if len(self.city) > 50:
            raise ValueError("city max length is 50")
        if len(self.state) > 50:
            raise ValueError("state max length is 50")
        if len(self.pincode) > 10:
            raise ValueError("pincode max length is 10")
        if len(self.country) > 50:
            raise ValueError("country max length is 50")
        if len(self.account_status) > 50:
            raise ValueError("account_status max length is 50")
        if len(self.role) > 50:
            raise ValueError("role max length is 50")
        if len(self.username) > 50:
            raise ValueError("username max length is 50")
        if len(self.password) > 50:
            raise ValueError("password max length is 50")
        if len(self.language) > 50:
            raise ValueError("language max length is 50")
        if len(self.departMent) > 50:
            raise ValueError("departMent max length is 50")
        if len(self.designation) > 50:
            raise ValueError("designation max length is 50")
        if len(self.time_zone) > 50:
            raise ValueError("time_zone max length is 50")
        if len(self.last_device) > 50:
            raise ValueError("last_device max length is 50")
        if len(self.last_ip) > 39:
            raise ValueError("last_ip max length is 39")
        if len(self.currency) > 50:
            raise ValueError("currency max length is 50")
        if len(self.domain_name) > 50:
            raise ValueError("domain_name max length is 50")
        if len(self.plan_type) > 50:
            raise ValueError("plan_type max length is 50")


@dataclass
class UserservicesUserShippingAddress:
    id: int
    user_id: int
    address_type: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.address_type) > 50:
            raise ValueError("address_type max length is 50")
        if len(self.city) > 50:
            raise ValueError("city max length is 50")
        if len(self.state) > 50:
            raise ValueError("state max length is 50")
        if len(self.pincode) > 10:
            raise ValueError("pincode max length is 10")
        if len(self.country) > 50:
            raise ValueError("country max length is 50")


@dataclass
class UserservicesActivityLog:
    id: int
    user_id: int
    domain_user_id_id: int
    activity: str = ""
    activity_type: str = ""
    activity_date: Optional[datetime] = None
    activity_ip: str = ""
    activity_device: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.activity_type) > 50:
            raise ValueError("activity_type max length is 50")
        if len(self.activity_ip) > 39:
            raise ValueError("activity_ip max length is 39")
        if len(self.activity_device) > 50:
            raise ValueError("activity_device max length is 50")


@dataclass
class UserservicesModules:
    id: int
    module_name: str = ""
    module_icon: str = ""
    is_menu: bool = False
    is_active: bool = True
    module_url: str = ""
    display_order: int = 0
    module_description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id_id: Optional[int] = None
    parent: Optional[UserservicesModules] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.module_name) > 50:
            raise ValueError("module_name max length is 50")


@dataclass
class UserservicesUserPermissions:
    id: int
    module_id_id: int
    domain_user_id_id: int
    user_id: int
    is_view: bool = False
    is_add: bool = False
    is_edit: bool = False
    is_delete: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module: Optional[UserservicesModules] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    user: Optional[UserservicesUsers] = field(default=None, repr=False)


@dataclass
class UserservicesUsersGroups:
    id: int
    users_id: int
    group_id: int
    user: Optional[UserservicesUsers] = field(default=None, repr=False)
    group: Optional[AuthGroup] = field(default=None, repr=False)


@dataclass
class UserservicesUsersUserPermissions:
    id: int
    users_id: int
    permission_id: int
    user: Optional[UserservicesUsers] = field(default=None, repr=False)
    permission: Optional[AuthPermission] = field(default=None, repr=False)


# ============================================================
#  PRODUCT SERVICE
# ============================================================

@dataclass
class ProductservicesCategories:
    id: int
    added_by_user_id_id: int
    domain_user_id_id: int
    name: str = ""
    image: str = ""
    description: str = ""
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id_id: Optional[int] = None
    parent: Optional[ProductservicesCategories] = field(default=None, repr=False)
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")


@dataclass
class ProductservicesProducts:
    id: int
    added_by_user_id_id: int
    category_id_id: int
    domain_user_id_id: int
    name: str = ""
    image: Optional[Dict[str, Any]] = None
    description: str = ""
    specifications: Optional[Dict[str, Any]] = None
    html_description: str = ""
    highlights: Optional[Dict[str, Any]] = None
    sku: str = ""
    initial_buying_price: float = 0.0
    initial_selling_price: float = 0.0
    weight: float = 0.0
    dimensions: str = ""
    uom: str = ""
    color: str = ""
    tax_percentage: float = 0.0
    brand: str = ""
    brand_model: str = ""
    status: str = ""
    seo_title: str = ""
    seo_description: str = ""
    seo_keywords: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    category: Optional[ProductservicesCategories] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.sku) > 255:
            raise ValueError("sku max length is 255")
        if len(self.dimensions) > 255:
            raise ValueError("dimensions max length is 255")
        if len(self.uom) > 255:
            raise ValueError("uom max length is 255")
        if len(self.color) > 255:
            raise ValueError("color max length is 255")
        if len(self.brand) > 255:
            raise ValueError("brand max length is 255")
        if len(self.brand_model) > 255:
            raise ValueError("brand_model max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")
        if len(self.seo_title) > 255:
            raise ValueError("seo_title max length is 255")


@dataclass
class ProductservicesProductQuestions:
    id: int
    domain_user_id_id: int
    question_user_id_id: int
    product_id_id: int
    question: str = ""
    answer: str = ""
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user_id_id: Optional[int] = None
    answer_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    question_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class ProductservicesProductReviews:
    id: int
    domain_user_id_id: int
    review_user_id_id: int
    product_id_id: int
    review_images: Optional[Dict[str, Any]] = None
    rating: float = 0.0
    reviews: str = ""
    status: str = ""
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    review_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


# ============================================================
#  INVENTORY SERVICE
# ============================================================

@dataclass
class InventoryservicesWarehouse:
    id: int
    added_by_user_id_id: int
    domain_user_id_id: int
    warehouse_manager_id: int
    name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    pincode: str = ""
    phone: str = ""
    email: str = ""
    status: str = ""
    size: str = ""
    capacity: str = ""
    warehouse_type: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    warehouse_manager: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.city) > 255:
            raise ValueError("city max length is 255")
        if len(self.state) > 255:
            raise ValueError("state max length is 255")
        if len(self.country) > 255:
            raise ValueError("country max length is 255")
        if len(self.pincode) > 255:
            raise ValueError("pincode max length is 255")
        if len(self.phone) > 255:
            raise ValueError("phone max length is 255")
        if len(self.email) > 254:
            raise ValueError("email max length is 254")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")
        if len(self.size) > 255:
            raise ValueError("size max length is 255")
        if len(self.capacity) > 255:
            raise ValueError("capacity max length is 255")
        if len(self.warehouse_type) > 255:
            raise ValueError("warehouse_type max length is 255")


@dataclass
class InventoryservicesRackAndShelvesAndFloor:
    id: int
    added_by_user_id_id: int
    domain_user_id_id: int
    warehouse_id_id: int
    name: str = ""
    rack: str = ""
    shelf: str = ""
    floor: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.rack) > 255:
            raise ValueError("rack max length is 255")
        if len(self.shelf) > 255:
            raise ValueError("shelf max length is 255")
        if len(self.floor) > 255:
            raise ValueError("floor max length is 255")


# ============================================================
#  ORDER SERVICE - Purchase Orders
# ============================================================

@dataclass
class OrderservicePurchaseOrder:
    id: int
    domain_user_id_id: int
    supplier_id_id: int
    warehouse_id_id: int
    po_code: str = ""
    po_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ""
    payment_status: str = ""
    total_amount: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    due_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    shipping_amount: Decimal = Decimal("0.00")
    shipping_type: str = ""
    shipping_tax_percentage: Decimal = Decimal("0.00")
    shipping_tax_amount: Decimal = Decimal("0.00")
    shipping_cancelled_amount: Decimal = Decimal("0.00")
    shipping_cancelled_tax_amount: Decimal = Decimal("0.00")
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    supplier: Optional[UserservicesUsers] = field(default=None, repr=False)
    updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.po_code) > 255:
            raise ValueError("po_code max length is 255")
        if len(self.payment_terms) > 255:
            raise ValueError("payment_terms max length is 255")
        if len(self.payment_status) > 255:
            raise ValueError("payment_status max length is 255")
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.shipping_type) > 255:
            raise ValueError("shipping_type max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class OrderservicePurchaseOrderItems:
    id: int
    domain_user_id_id: int
    po_id_id: int
    product_id_id: int
    quantity_ordered: int = 0
    quantity_received: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    buying_price: Decimal = Decimal("0.00")
    selling_price: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    amount_paid: Decimal = Decimal("0.00")
    amount_returned: Decimal = Decimal("0.00")
    amount_cancelled: Decimal = Decimal("0.00")
    amount_ordered: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    shipping_tax_percentage: Decimal = Decimal("0.00")
    shipping_amount: Decimal = Decimal("0.00")
    shipping_tax_amount: Decimal = Decimal("0.00")
    shipping_cancelled_amount: Decimal = Decimal("0.00")
    shipping_cancelled_tax_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class OrderservicePurchaseOrderLogs:
    id: int
    domain_user_id_id: int
    po_id_id: int
    comment: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)


@dataclass
class OrderservicePurchaseOrderInwardedLog:
    id: int
    domain_user_id_id: int
    po_id_id: int
    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    inwarded_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    inwarded_by_user_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    inwarded_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.invoice_number) > 255:
            raise ValueError("invoice_number max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class OrderservicePurchaseOrderItemInwardedLog:
    id: int
    domain_user_id_id: int
    po_item_id_id: int
    inwarded_quantity: int = 0
    price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    shipping_amount: Decimal = Decimal("0.00")
    shipping_tax_percentage: Decimal = Decimal("0.00")
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po_item: Optional[OrderservicePurchaseOrderItems] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


# ============================================================
#  ORDER SERVICE - Sales Orders
# ============================================================

@dataclass
class OrderserviceSalesOrder:
    id: int
    customer_id_id: int
    domain_user_id_id: int
    so_code: str = ""
    so_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ""
    payment_status: str = ""
    total_amount: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    due_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    shipping_amount: Decimal = Decimal("0.00")
    shipping_type: str = ""
    shipping_tax_percentage: Decimal = Decimal("0.00")
    shipping_tax_amount: Decimal = Decimal("0.00")
    shipping_cancelled_amount: Decimal = Decimal("0.00")
    shipping_cancelled_tax_amount: Decimal = Decimal("0.00")
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    customer: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.so_code) > 255:
            raise ValueError("so_code max length is 255")
        if len(self.payment_terms) > 255:
            raise ValueError("payment_terms max length is 255")
        if len(self.payment_status) > 255:
            raise ValueError("payment_status max length is 255")
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.shipping_type) > 255:
            raise ValueError("shipping_type max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class OrderserviceSalesOrderOrderItems:
    id: int
    domain_user_id_id: int
    product_id_id: int
    so_id_id: int
    quantity_ordered: int = 0
    quantity_delivered: int = 0
    quantity_shipped: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    purchase_price: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    amount_paid: Decimal = Decimal("0.00")
    amount_returned: Decimal = Decimal("0.00")
    amount_cancelled: Decimal = Decimal("0.00")
    amount_ordered: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    shipping_amount: Decimal = Decimal("0.00")
    shipping_type: str = ""
    shipping_tax_amount: Decimal = Decimal("0.00")
    shipping_cancelled_amount: Decimal = Decimal("0.00")
    shipping_cancelled_tax_amount: Decimal = Decimal("0.00")
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    shipped_by_user_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    shipped_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)
    updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.shipping_type) > 255:
            raise ValueError("shipping_type max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class OrderserviceSalesOrderLogs:
    id: int
    domain_user_id_id: int
    so_id_id: int
    comment: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)


@dataclass
class OrderserviceSalesOrderOutwardedLog:
    id: int
    domain_user_id_id: int
    so_id_id: int
    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    outwared_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    outwarded_by_user_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    outwarded_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.invoice_number) > 255:
            raise ValueError("invoice_number max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


@dataclass
class OrderserviceSalesOrderItemOutwardedLog:
    id: int
    domain_user_id_id: int
    so_item_id_id: int
    outwarded_quantity: int = 0
    price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    shipping_amount: Decimal = Decimal("0.00")
    shipping_tax_percentage: Decimal = Decimal("0.00")
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so_item: Optional[OrderserviceSalesOrderOrderItems] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


# ============================================================
#  INVENTORY SERVICE (continued - depends on order service)
# ============================================================

@dataclass
class InventoryservicesInventory:
    id: int
    added_by_user_id_id: int
    domain_user_id_id: int
    product_id_id: int
    purchase_order_id_id: int
    purchase_order_item_id_id: int
    warehouse_id_id: int
    rack_shelf_floor_id_id: int
    quantity: int = 0
    mrp: str = ""
    batch_number: str = ""
    discount_type: str = ""
    discount_amout: float = 0.0
    sr_no: str = ""
    mfg_date: Optional[datetime] = None
    uom: str = ""
    ptr: str = ""
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    quantity_inwarded: int = 0
    buy_price: Decimal = Decimal("0.00")
    sell_price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    stock_status: str = ""
    inward_type: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    purchase_order_item_inwarded_item_id_id: Optional[int] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    purchase_order: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    purchase_order_item: Optional[OrderservicePurchaseOrderItems] = field(default=None, repr=False)
    purchase_order_item_inwarded_item: Optional[OrderservicePurchaseOrderItemInwardedLog] = field(default=None, repr=False)
    rack_shelf_floor: Optional[InventoryservicesRackAndShelvesAndFloor] = field(default=None, repr=False)
    warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.mrp) > 255:
            raise ValueError("mrp max length is 255")
        if len(self.batch_number) > 255:
            raise ValueError("batch_number max length is 255")
        if len(self.discount_type) > 255:
            raise ValueError("discount_type max length is 255")
        if len(self.sr_no) > 255:
            raise ValueError("sr_no max length is 255")
        if len(self.uom) > 255:
            raise ValueError("uom max length is 255")
        if len(self.ptr) > 255:
            raise ValueError("ptr max length is 255")
        if len(self.stock_status) > 255:
            raise ValueError("stock_status max length is 255")
        if len(self.inward_type) > 255:
            raise ValueError("inward_type max length is 255")


@dataclass
class InventoryservicesInventoryLog:
    id: int
    added_by_user_id_id: int
    domain_user_id_id: int
    inventory_id_id: int
    warehouse_id_id: int
    rack_shelf_floor_id_id: int
    quantity: int = 0
    status: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    po_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    inventory: Optional[InventoryservicesInventory] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)
    rack_shelf_floor: Optional[InventoryservicesRackAndShelvesAndFloor] = field(default=None, repr=False)
    warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.status) > 255:
            raise ValueError("status max length is 255")


# ============================================================
#  REPOSITORY / MANAGER CLASSES
# ============================================================

class UserservicesUsersManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUsers] = {}

    def add(self, user: UserservicesUsers) -> None:
        self._store[user.id] = user

    def get(self, user_id: int) -> Optional[UserservicesUsers]:
        return self._store.get(user_id)

    def all(self) -> List[UserservicesUsers]:
        return list(self._store.values())

    def delete(self, user_id: int) -> bool:
        if user_id in self._store:
            del self._store[user_id]
            return True
        return False

    def filter_by_role(self, role: str) -> List[UserservicesUsers]:
        return [u for u in self._store.values() if u.role == role]

    def filter_by_domain(self, domain_user_id: int) -> List[UserservicesUsers]:
        return [u for u in self._store.values() if u.domain_user_id_id == domain_user_id]


class ProductservicesProductsManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesProducts] = {}

    def add(self, product: ProductservicesProducts) -> None:
        self._store[product.id] = product

    def get(self, product_id: int) -> Optional[ProductservicesProducts]:
        return self._store.get(product_id)

    def all(self) -> List[ProductservicesProducts]:
        return list(self._store.values())

    def delete(self, product_id: int) -> bool:
        if product_id in self._store:
            del self._store[product_id]
            return True
        return False

    def filter_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [p for p in self._store.values() if p.category_id_id == category_id]

    def filter_by_status(self, status: str) -> List[ProductservicesProducts]:
        return [p for p in self._store.values() if p.status == status]


class ProductservicesCategoriesManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesCategories] = {}

    def add(self, category: ProductservicesCategories) -> None:
        self._store[category.id] = category

    def get(self, category_id: int) -> Optional[ProductservicesCategories]:
        return self._store.get(category_id)

    def all(self) -> List[ProductservicesCategories]:
        return list(self._store.values())

    def delete(self, category_id: int) -> bool:
        if category_id in self._store:
            del self._store[category_id]
            return True
        return False

    def get_children(self, parent_id: int) -> List[ProductservicesCategories]:
        return [c for c in self._store.values() if c.parent_id_id == parent_id]

    def get_root_categories(self) -> List[ProductservicesCategories]:
        return [c for c in self._store.values() if c.parent_id_id is None]


class InventoryservicesWarehouseManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesWarehouse] = {}

    def add(self, warehouse: InventoryservicesWarehouse) -> None:
        self._store[warehouse.id] = warehouse

    def get(self, warehouse_id: int) -> Optional[InventoryservicesWarehouse]:
        return self._store.get(warehouse_id)

    def all(self) -> List[InventoryservicesWarehouse]:
        return list(self._store.values())

    def delete(self, warehouse_id: int) -> bool:
        if warehouse_id in self._store:
            del self._store[warehouse_id]
            return True
        return False

    def filter_by_status(self, status: str) -> List[InventoryservicesWarehouse]:
        return [w for w in self._store.values() if w.status == status]


class InventoryservicesRackAndShelvesAndFloorManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesRackAndShelvesAndFloor] = {}

    def add(self, rack: InventoryservicesRackAndShelvesAndFloor) -> None:
        self._store[rack.id] = rack

    def get(self, rack_id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._store.get(rack_id)

    def all(self) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return list(self._store.values())

    def delete(self, rack_id: int) -> bool:
        if rack_id in self._store:
            del self._store[rack_id]
            return True
        return False

    def filter_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return [r for r in self._store.values() if r.warehouse_id_id == warehouse_id]


class InventoryservicesInventoryManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesInventory] = {}

    def add(self, inventory: InventoryservicesInventory) -> None:
        self._store[inventory.id] = inventory

    def get(self, inventory_id: int) -> Optional[InventoryservicesInventory]:
        return self._store.get(inventory_id)

    def all(self) -> List[InventoryservicesInventory]:
        return list(self._store.values())

    def delete(self, inventory_id: int) -> bool:
        if inventory_id in self._store:
            del self._store[inventory_id]
            return True
        return False

    def filter_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.product_id_id == product_id]

    def filter_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.warehouse_id_id == warehouse_id]

    def filter_by_stock_status(self, stock_status: str) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.stock_status == stock_status]


class InventoryservicesInventoryLogManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesInventoryLog] = {}

    def add(self, log: InventoryservicesInventoryLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[InventoryservicesInventoryLog]:
        return self._store.get(log_id)

    def all(self) -> List[InventoryservicesInventoryLog]:
        return list(self._store.values())

    def delete(self, log_id: int) -> bool:
        if log_id in self._store:
            del self._store[log_id]
            return True
        return False

    def filter_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [l for l in self._store.values() if l.inventory_id_id == inventory_id]


class OrderservicePurchaseOrderManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrder] = {}

    def add(self, po: OrderservicePurchaseOrder) -> None:
        self._store[po.id] = po

    def get(self, po_id: int) -> Optional[OrderservicePurchaseOrder]:
        return self._store.get(po_id)

    def all(self) -> List[OrderservicePurchaseOrder]:
        return list(self._store.values())

    def delete(self, po_id: int) -> bool:
        if po_id in self._store:
            del self._store[po_id]
            return True
        return False

    def filter_by_status(self, status: str) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.status == status]

    def filter_by_supplier(self, supplier_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.supplier_id_id == supplier_id]

    def filter_by_warehouse(self, warehouse_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.warehouse_id_id == warehouse_id]


class OrderservicePurchaseOrderItemsManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderItems] = {}

    def add(self, item: OrderservicePurchaseOrderItems) -> None:
        self._store[item.id] = item

    def get(self, item_id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self._store.get(item_id)

    def all(self) -> List[OrderservicePurchaseOrderItems]:
        return list(self._store.values())

    def delete(self, item_id: int) -> bool:
        if item_id in self._store:
            del self._store[item_id]
            return True
        return False

    def filter_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [i for i in self._store.values() if i.po_id_id == po_id]

    def filter_by_product(self, product_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [i for i in self._store.values() if i.product_id_id == product_id]


class OrderservicePurchaseOrderLogsManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderLogs] = {}

    def add(self, log: OrderservicePurchaseOrderLogs) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self._store.get(log_id)

    def all(self) -> List[OrderservicePurchaseOrderLogs]:
        return list(self._store.values())

    def filter_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return [l for l in self._store.values() if l.po_id_id == po_id]


class OrderservicePurchaseOrderInwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderInwardedLog] = {}

    def add(self, log: OrderservicePurchaseOrderInwardedLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self._store.get(log_id)

    def all(self) -> List[OrderservicePurchaseOrderInwardedLog]:
        return list(self._store.values())

    def filter_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderInwardedLog]:
        return [l for l in self._store.values() if l.po_id_id == po_id]


class OrderservicePurchaseOrderItemInwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderItemInwardedLog] = {}

    def add(self, log: OrderservicePurchaseOrderItemInwardedLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._store.get(log_id)

    def all(self) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return list(self._store.values())

    def filter_by_po_item(self, po_item_id: int) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return [l for l in self._store.values() if l.po_item_id_id == po_item_id]


class OrderserviceSalesOrderManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrder] = {}

    def add(self, so: OrderserviceSalesOrder) -> None:
        self._store[so.id] = so

    def get(self, so_id: int) -> Optional[OrderserviceSalesOrder]:
        return self._store.get(so_id)

    def all(self) -> List[OrderserviceSalesOrder]:
        return list(self._store.values())

    def delete(self, so_id: int) -> bool:
        if so_id in self._store:
            del self._store[so_id]
            return True
        return False

    def filter_by_status(self, status: str) -> List[OrderserviceSalesOrder]:
        return [so for so in self._store.values() if so.status == status]

    def filter_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return [so for so in self._store.values() if so.customer_id_id == customer_id]


class OrderserviceSalesOrderOrderItemsManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderOrderItems] = {}

    def add(self, item: OrderserviceSalesOrderOrderItems) -> None:
        self._store[item.id] = item

    def get(self, item_id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._store.get(item_id)

    def all(self) -> List[OrderserviceSalesOrderOrderItems]:
        return list(self._store.values())

    def delete(self, item_id: int) -> bool:
        if item_id in self._store:
            del self._store[item_id]
            return True
        return False

    def filter_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [i for i in self._store.values() if i.so_id_id == so_id]

    def filter_by_product(self, product_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [i for i in self._store.values() if i.product_id_id == product_id]


class OrderserviceSalesOrderLogsManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderLogs] = {}

    def add(self, log: OrderserviceSalesOrderLogs) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self._store.get(log_id)

    def all(self) -> List[OrderserviceSalesOrderLogs]:
        return list(self._store.values())

    def filter_by_so(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return [l for l in self._store.values() if l.so_id_id == so_id]


class OrderserviceSalesOrderOutwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderOutwardedLog] = {}

    def add(self, log: OrderserviceSalesOrderOutwardedLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self._store.get(log_id)

    def all(self) -> List[OrderserviceSalesOrderOutwardedLog]:
        return list(self._store.values())

    def filter_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOutwardedLog]:
        return [l for l in self._store.values() if l.so_id_id == so_id]


class OrderserviceSalesOrderItemOutwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderItemOutwardedLog] = {}

    def add(self, log: OrderserviceSalesOrderItemOutwardedLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self._store.get(log_id)

    def all(self) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return list(self._store.values())

    def filter_by_so_item(self, so_item_id: int) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return [l for l in self._store.values() if l.so_item_id_id == so_item_id]


class AuthGroupManager:
    def __init__(self):
        self._store: Dict[int, AuthGroup] = {}

    def add(self, group: AuthGroup) -> None:
        self._store[group.id] = group

    def get(self, group_id: int) -> Optional[AuthGroup]:
        return self._store.get(group_id)

    def all(self) -> List[AuthGroup]:
        return list(self._store.values())

    def delete(self, group_id: int) -> bool:
        if group_id in self._store:
            del self._store[group_id]
            return True
        return False


class AuthPermissionManager:
    def __init__(self):
        self._store: Dict[int, AuthPermission] = {}

    def add(self, permission: AuthPermission) -> None:
        self._store[permission.id] = permission

    def get(self, permission_id: int) -> Optional[AuthPermission]:
        return self._store.get(permission_id)

    def all(self) -> List[AuthPermission]:
        return list(self._store.values())

    def filter_by_content_type(self, content_type_id: int) -> List[AuthPermission]:
        return [p for p in self._store.values() if p.content_type_id == content_type_id]


class AuthGroupPermissionsManager:
    def __init__(self):
        self._store: Dict[int, AuthGroupPermissions] = {}

    def add(self, gp: AuthGroupPermissions) -> None:
        self._store[gp.id] = gp

    def get(self, gp_id: int) -> Optional[AuthGroupPermissions]:
        return self._store.get(gp_id)

    def all(self) -> List[AuthGroupPermissions]:
        return list(self._store.values())

    def filter_by_group(self, group_id: int) -> List[AuthGroupPermissions]:
        return [gp for gp in self._store.values() if gp.group_id == group_id]

    def filter_by_permission(self, permission_id: int) -> List[AuthGroupPermissions]:
        return [gp for gp in self._store.values() if gp.permission_id == permission_id]


class DjangoContentTypeManager:
    def __init__(self):
        self._store: Dict[int, DjangoContentType] = {}

    def add(self, ct: DjangoContentType) -> None:
        self._store[ct.id] = ct

    def get(self, ct_id: int) -> Optional[DjangoContentType]:
        return self._store.get(ct_id)

    def all(self) -> List[DjangoContentType]:
        return list(self._store.values())


class DjangoAdminLogManager:
    def __init__(self):
        self._store: Dict[int, DjangoAdminLog] = {}

    def add(self, log: DjangoAdminLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[DjangoAdminLog]:
        return self._store.get(log_id)

    def all(self) -> List[DjangoAdminLog]:
        return list(self._store.values())

    def filter_by_user(self, user_id: int) -> List[DjangoAdminLog]:
        return [l for l in self._store.values() if l.user_id == user_id]

    def filter_by_content_type(self, content_type_id: int) -> List[DjangoAdminLog]:
        return [l for l in self._store.values() if l.content_type_id == content_type_id]


class DjangoMigrationsManager:
    def __init__(self):
        self._store: Dict[int, DjangoMigrations] = {}

    def add(self, migration: DjangoMigrations) -> None:
        self._store[migration.id] = migration

    def get(self, migration_id: int) -> Optional[DjangoMigrations]:
        return self._store.get(migration_id)

    def all(self) -> List[DjangoMigrations]:
        return list(self._store.values())


class DjangoSessionManager:
    def __init__(self):
        self._store: Dict[str, DjangoSession] = {}

    def add(self, session: DjangoSession) -> None:
        self._store[session.session_key] = session

    def get(self, session_key: str) -> Optional[DjangoSession]:
        return self._store.get(session_key)

    def all(self) -> List[DjangoSession]:
        return list(self._store.values())

    def delete(self, session_key: str) -> bool:
        if session_key in self._store:
            del self._store[session_key]
            return True
        return False


class UserservicesUserShippingAddressManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUserShippingAddress] = {}

    def add(self, address: UserservicesUserShippingAddress) -> None:
        self._store[address.id] = address

    def get(self, address_id: int) -> Optional[UserservicesUserShippingAddress]:
        return self._store.get(address_id)

    def all(self) -> List[UserservicesUserShippingAddress]:
        return list(self._store.values())

    def delete(self, address_id: int) -> bool:
        if address_id in self._store:
            del self._store[address_id]
            return True
        return False

    def filter_by_user(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [a for a in self._store.values() if a.user_id == user_id]


class UserservicesActivityLogManager:
    def __init__(self):
        self._store: Dict[int, UserservicesActivityLog] = {}

    def add(self, log: UserservicesActivityLog) -> None:
        self._store[log.id] = log

    def get(self, log_id: int) -> Optional[UserservicesActivityLog]:
        return self._store.get(log_id)

    def all(self) -> List[UserservicesActivityLog]:
        return list(self._store.values())

    def filter_by_user(self, user_id: int) -> List[UserservicesActivityLog]:
        return [l for l in self._store.values() if l.user_id == user_id]

    def filter_by_activity_type(self, activity_type: str) -> List[UserservicesActivityLog]:
        return [l for l in self._store.values() if l.activity_type == activity_type]


class UserservicesModulesManager:
    def __init__(self):
        self._store: Dict[int, UserservicesModules] = {}

    def add(self, module: UserservicesModules) -> None:
        self._store[module.id] = module

    def get(self, module_id: int) -> Optional[UserservicesModules]:
        return self._store.get(module_id)

    def all(self) -> List[UserservicesModules]:
        return list(self._store.values())

    def delete(self, module_id: int) -> bool:
        if module_id in self._store:
            del self._store[module_id]
            return True
        return False

    def get_children(self, parent_id: int) -> List[UserservicesModules]:
        return [m for m in self._store.values() if m.parent_id_id == parent_id]

    def get_root_modules(self) -> List[UserservicesModules]:
        return [m for m in self._store.values() if m.parent_id_id is None]

    def filter_active(self) -> List[UserservicesModules]:
        return [m for m in self._store.values() if m.is_active]


class UserservicesUserPermissionsManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUserPermissions] = {}

    def add(self, perm: UserservicesUserPermissions) -> None:
        self._store[perm.id] = perm

    def get(self, perm_id: int) -> Optional[UserservicesUserPermissions]:
        return self._store.get(perm_id)

    def all(self) -> List[UserservicesUserPermissions]:
        return list(self._store.values())

    def delete(self, perm_id: int) -> bool:
        if perm_id in self._store:
            del self._store[perm_id]
            return True
        return False

    def filter_by_user(self, user_id: int) -> List[UserservicesUserPermissions]:
        return [p for p in self._store.values() if p.user_id == user_id]

    def filter_by_module(self, module_id: int) -> List[UserservicesUserPermissions]:
        return [p for p in self._store.values() if p.module_id_id == module_id]


class UserservicesUsersGroupsManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUsersGroups] = {}

    def add(self, ug: UserservicesUsersGroups) -> None:
        self._store[ug.id] = ug

    def get(self, ug_id: int) -> Optional[UserservicesUsersGroups]:
        return self._store.get(ug_id)

    def all(self) -> List[UserservicesUsersGroups]:
        return list(self._store.values())

    def filter_by_user(self, users_id: int) -> List[UserservicesUsersGroups]:
        return [ug for ug in self._store.values() if ug.users_id == users_id]

    def filter_by_group(self, group_id: int) -> List[UserservicesUsersGroups]:
        return [ug for ug in self._store.values() if ug.group_id == group_id]


class UserservicesUsersUserPermissionsManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUsersUserPermissions] = {}

    def add(self, up: UserservicesUsersUserPermissions) -> None:
        self._store[up.id] = up

    def get(self, up_id: int) -> Optional[UserservicesUsersUserPermissions]:
        return self._store.get(up_id)

    def all(self) -> List[UserservicesUsersUserPermissions]:
        return list(self._store.values())

    def filter_by_user(self, users_id: int) -> List[UserservicesUsersUserPermissions]:
        return [up for up in self._store.values() if up.users_id == users_id]

    def filter_by_permission(self, permission_id: int) -> List[UserservicesUsersUserPermissions]:
        return [up for up in self._store.values() if up.permission_id == permission_id]


class ProductservicesProductQuestionsManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesProductQuestions] = {}

    def add(self, question: ProductservicesProductQuestions) -> None:
        self._store[question.id] = question

    def get(self, question_id: int) -> Optional[ProductservicesProductQuestions]:
        return self._store.get(question_id)

    def all(self) -> List[ProductservicesProductQuestions]:
        return list(self._store.values())

    def delete(self, question_id: int) -> bool:
        if question_id in self._store:
            del self._store[question_id]
            return True
        return False

    def filter_by_product(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [q for q in self._store.values() if q.product_id_id == product_id]

    def filter_by_status(self, status: str) -> List[ProductservicesProductQuestions]:
        return [q for q in self._store.values() if q.status == status]


class ProductservicesProductReviewsManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesProductReviews] = {}

    def add(self, review: ProductservicesProductReviews) -> None:
        self._store[review.id] = review

    def get(self, review_id: int) -> Optional[ProductservicesProductReviews]:
        return self._store.get(review_id)

    def all(self) -> List[ProductservicesProductReviews]:
        return list(self._store.values())

    def delete(self, review_id: int) -> bool:
        if review_id in self._store:
            del self._store[review_id]
            return True
        return False

    def filter_by_product(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [r for r in self._store.values() if r.product_id_id == product_id]

    def filter_by_status(self, status: str) -> List[ProductservicesProductReviews]:
        return [r for r in self._store.values() if r.status == status]

    def average_rating(self, product_id: int) -> float:
        reviews = self.filter_by_product(product_id)
        if not reviews:
            return 0.0
        return sum(r.rating for r in reviews) / len(reviews)


# ============================================================
#  APPLICATION / DATABASE FACADE
# ============================================================

class EcommerceDatabase:
    def __init__(self):
        self.users = UserservicesUsersManager()
        self.user_shipping_addresses = UserservicesUserShippingAddressManager()
        self.activity_logs = UserservicesActivityLogManager()
        self.modules = UserservicesModulesManager()
        self.user_permissions = UserservicesUserPermissionsManager()
        self.users_groups = UserservicesUsersGroupsManager()
        self.users_user_permissions = UserservicesUsersUserPermissionsManager()

        self.categories = ProductservicesCategoriesManager()
        self.products = ProductservicesProductsManager()
        self.product_questions = ProductservicesProductQuestionsManager()
        self.product_reviews = ProductservicesProductReviewsManager()

        self.warehouses = InventoryservicesWarehouseManager()
        self.rack_shelves_floors = InventoryservicesRackAndShelvesAndFloorManager()
        self.inventory = InventoryservicesInventoryManager()
        self.inventory_logs = InventoryservicesInventoryLogManager()

        self.purchase_orders = OrderservicePurchaseOrderManager()
        self.purchase_order_items = OrderservicePurchaseOrderItemsManager()
        self.purchase_order_logs = OrderservicePurchaseOrderLogsManager()
        self.purchase_order_inwarded_logs = OrderservicePurchaseOrderInwardedLogManager()
        self.purchase_order_item_inwarded_logs = OrderservicePurchaseOrderItemInwardedLogManager()

        self.sales_orders = OrderserviceSalesOrderManager()
        self.sales_order_items = OrderserviceSalesOrderOrderItemsManager()
        self.sales_order_logs = OrderserviceSalesOrderLogsManager()
        self.sales_order_outwarded_logs = OrderserviceSalesOrderOutwardedLogManager()
        self.sales_order_item_outwarded_logs = OrderserviceSalesOrderItemOutwardedLogManager()

        self.auth_groups = AuthGroupManager()
        self.auth_permissions = AuthPermissionManager()
        self.auth_group_permissions = AuthGroupPermissionsManager()
        self.content_types = DjangoContentTypeManager()
        self.admin_logs = DjangoAdminLogManager()
        self.migrations = DjangoMigrationsManager()
        self.sessions = DjangoSessionManager()

    def resolve_inventory_relations(self, inventory: InventoryservicesInventory) -> None:
        inventory.added_by_user = self.users.get(inventory.added_by_user_id_id)
        inventory.domain_user = self.users.get(inventory.domain_user_id_id)
        inventory.product = self.products.get(inventory.product_id_id)
        inventory.purchase_order = self.purchase_orders.get(inventory.purchase_order_id_id)
        inventory.purchase_order_item = self.purchase_order_items.get(inventory.purchase_order_item_id_id)
        inventory.warehouse = self.warehouses.get(inventory.warehouse_id_id)
        inventory.rack_shelf_floor = self.rack_shelves_floors.get(inventory.rack_shelf_floor_id_id)
        if inventory.purchase_order_item_inwarded_item_id_id is not None:
            inventory.purchase_order_item_inwarded_item = self.purchase_order_item_inwarded_logs.get(
                inventory.purchase_order_item_inwarded_item_id_id
            )

    def resolve_inventory_log_relations(self, log: InventoryservicesInventoryLog) -> None:
        log.added_by_user = self.users.get(log.added_by_user_id_id)
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.inventory = self.inventory.get(log.inventory_id_id)
        log.warehouse = self.warehouses.get(log.warehouse_id_id)
        log.rack_shelf_floor = self.rack_shelves_floors.get(log.rack_shelf_floor_id_id)
        if log.po_id_id is not None:
            log.po = self.purchase_orders.get(log.po_id_id)
        if log.so_id_id is not None:
            log.so = self.sales_orders.get(log.so_id_id)

    def resolve_warehouse_relations(self, warehouse: InventoryservicesWarehouse) -> None:
        warehouse.added_by_user = self.users.get(warehouse.added_by_user_id_id)
        warehouse.domain_user = self.users.get(warehouse.domain_user_id_id)
        warehouse.warehouse_manager = self.users.get(warehouse.warehouse_manager_id)

    def resolve_rack_relations(self, rack: InventoryservicesRackAndShelvesAndFloor) -> None:
        rack.added_by_user = self.users.get(rack.added_by_user_id_id)
        rack.domain_user = self.users.get(rack.domain_user_id_id)
        rack.warehouse = self.warehouses.get(rack.warehouse_id_id)

    def resolve_purchase_order_relations(self, po: OrderservicePurchaseOrder) -> None:
        po.domain_user = self.users.get(po.domain_user_id_id)
        po.supplier = self.users.get(po.supplier_id_id)
        po.warehouse = self.warehouses.get(po.warehouse_id_id)
        if po.approved_by_user_id_id is not None:
            po.approved_by_user = self.users.get(po.approved_by_user_id_id)
        if po.cancelled_by_user_id_id is not None:
            po.cancelled_by_user = self.users.get(po.cancelled_by_user_id_id)
        if po.created_by_user_id_id is not None:
            po.created_by_user = self.users.get(po.created_by_user_id_id)
        if po.last_updated_by_user_id_id is not None:
            po.last_updated_by_user = self.users.get(po.last_updated_by_user_id_id)
        if po.received_by_user_id_id is not None:
            po.received_by_user = self.users.get(po.received_by_user_id_id)
        if po.returned_by_user_id_id is not None:
            po.returned_by_user = self.users.get(po.returned_by_user_id_id)
        if po.updated_by_user_id_id is not None:
            po.updated_by_user = self.users.get(po.updated_by_user_id_id)

    def resolve_purchase_order_item_relations(self, item: OrderservicePurchaseOrderItems) -> None:
        item.domain_user = self.users.get(item.domain_user_id_id)
        item.po = self.purchase_orders.get(item.po_id_id)
        item.product = self.products.get(item.product_id_id)
        if item.approved_by_user_id_id is not None:
            item.approved_by_user = self.users.get(item.approved_by_user_id_id)
        if item.cancelled_by_user_id_id is not None:
            item.cancelled_by_user = self.users.get(item.cancelled_by_user_id_id)
        if item.created_by_user_id_id is not None:
            item.created_by_user = self.users.get(item.created_by_user_id_id)
        if item.last_updated_by_user_id_id is not None:
            item.last_updated_by_user = self.users.get(item.last_updated_by_user_id_id)
        if item.received_by_user_id_id is not None:
            item.received_by_user = self.users.get(item.received_by_user_id_id)
        if item.returned_by_user_id_id is not None:
            item.returned_by_user = self.users.get(item.returned_by_user_id_id)
        if item.updated_by_user_id_id is not None:
            item.updated_by_user = self.users.get(item.updated_by_user_id_id)

    def resolve_sales_order_relations(self, so: OrderserviceSalesOrder) -> None:
        so.customer = self.users.get(so.customer_id_id)
        so.domain_user = self.users.get(so.domain_user_id_id)
        if so.approved_by_user_id_id is not None:
            so.approved_by_user = self.users.get(so.approved_by_user_id_id)
        if so.cancelled_by_user_id_id is not None:
            so.cancelled_by_user = self.users.get(so.cancelled_by_user_id_id)
        if so.created_by_user_id_id is not None:
            so.created_by_user = self.users.get(so.created_by_user_id_id)
        if so.last_updated_by_user_id_id is not None:
            so.last_updated_by_user = self.users.get(so.last_updated_by_user_id_id)
        if so.received_by_user_id_id is not None:
            so.received_by_user = self.users.get(so.received_by_user_id_id)
        if so.returned_by_user_id_id is not None:
            so.returned_by_user = self.users.get(so.returned_by_user_id_id)
        if so.updated_by_user_id_id is not None:
            so.updated_by_user = self.users.get(so.updated_by_user_id_id)
        if so.po_id_id is not None:
            so.po = self.purchase_orders.get(so.po_id_id)
        if so.product_id_id is not None:
            so.product = self.products.get(so.product_id_id)

    def resolve_sales_order_item_relations(self, item: OrderserviceSalesOrderOrderItems) -> None:
        item.domain_user = self.users.get(item.domain_user_id_id)
        item.product = self.products.get(item.product_id_id)
        item.so = self.sales_orders.get(item.so_id_id)
        if item.approved_by_user_id_id is not None:
            item.approved_by_user = self.users.get(item.approved_by_user_id_id)
        if item.cancelled_by_user_id_id is not None:
            item.cancelled_by_user = self.users.get(item.cancelled_by_user_id_id)
        if item.created_by_user_id_id is not None:
            item.created_by_user = self.users.get(item.created_by_user_id_id)
        if item.returned_by_user_id_id is not None:
            item.returned_by_user = self.users.get(item.returned_by_user_id_id)
        if item.shipped_by_user_id_id is not None:
            item.shipped_by_user = self.users.get(item.shipped_by_user_id_id)
        if item.updated_by_user_id_id is not None:
            item.updated_by_user = self.users.get(item.updated_by_user_id_id)

    def resolve_product_relations(self, product: ProductservicesProducts) -> None:
        product.added_by_user = self.users.get(product.added_by_user_id_id)
        product.domain_user = self.users.get(product.domain_user_id_id)
        product.category = self.categories.get(product.category_id_id)

    def resolve_category_relations(self, category: ProductservicesCategories) -> None:
        category.added_by_user = self.users.get(category.added_by_user_id_id)
        category.domain_user = self.users.get(category.domain_user_id_id)
        if category.parent_id_id is not None:
            category.parent = self.categories.get(category.parent_id_id)

    def resolve_user_relations(self, user: UserservicesUsers) -> None:
        if user.domain_user_id_id is not None:
            user.domain_user = self.users.get(user.domain_user_id_id)

    def resolve_module_relations(self, module: UserservicesModules) -> None:
        if module.parent_id_id is not None:
            module.parent = self.modules.get(module.parent_id_id)

    def resolve_admin_log_relations(self, log: DjangoAdminLog) -> None:
        log.content_type = self.content_types.get(log.content_type_id)
        log.user = self.users.get(log.user_id)

    def resolve_auth_permission_relations(self, permission: AuthPermission) -> None:
        permission.content_type = self.content_types.get(permission.content_type_id)

    def resolve_auth_group_permissions_relations(self, gp: AuthGroupPermissions) -> None:
        gp.group = self.auth_groups.get(gp.group_id)
        gp.permission = self.auth_permissions.get(gp.permission_id)

    def resolve_users_groups_relations(self, ug: UserservicesUsersGroups) -> None:
        ug.user = self.users.get(ug.users_id)
        ug.group = self.auth_groups.get(ug.group_id)

    def resolve_users_user_permissions_relations(self, up: UserservicesUsersUserPermissions) -> None:
        up.user = self.users.get(up.users_id)
        up.permission = self.auth_permissions.get(up.permission_id)

    def resolve_user_permissions_relations(self, perm: UserservicesUserPermissions) -> None:
        perm.module = self.modules.get(perm.module_id_id)
        perm.domain_user = self.users.get(perm.domain_user_id_id)
        perm.user = self.users.get(perm.user_id)

    def resolve_product_question_relations(self, question: ProductservicesProductQuestions) -> None:
        question.domain_user = self.users.get(question.domain_user_id_id)
        question.question_user = self.users.get(question.question_user_id_id)
        question.product = self.products.get(question.product_id_id)
        if question.answer_user_id_id is not None:
            question.answer_user = self.users.get(question.answer_user_id_id)

    def resolve_product_review_relations(self, review: ProductservicesProductReviews) -> None:
        review.domain_user = self.users.get(review.domain_user_id_id)
        review.review_user = self.users.get(review.review_user_id_id)
        review.product = self.products.get(review.product_id_id)

    def resolve_purchase_order_log_relations(self, log: OrderservicePurchaseOrderLogs) -> None:
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.po = self.purchase_orders.get(log.po_id_id)
        if log.created_by_user_id_id is not None:
            log.created_by_user = self.users.get(log.created_by_user_id_id)

    def resolve_purchase_order_inwarded_log_relations(self, log: OrderservicePurchaseOrderInwardedLog) -> None:
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.po = self.purchase_orders.get(log.po_id_id)
        if log.inwarded_by_user_id_id is not None:
            log.inwarded_by_user = self.users.get(log.inwarded_by_user_id_id)

    def resolve_purchase_order_item_inwarded_log_relations(self, log: OrderservicePurchaseOrderItemInwardedLog) -> None:
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.po_item = self.purchase_order_items.get(log.po_item_id_id)

    def resolve_sales_order_log_relations(self, log: OrderserviceSalesOrderLogs) -> None:
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.so = self.sales_orders.get(log.so_id_id)
        if log.created_by_user_id_id is not None:
            log.created_by_user = self.users.get(log.created_by_user_id_id)

    def resolve_sales_order_outwarded_log_relations(self, log: OrderserviceSalesOrderOutwardedLog) -> None:
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.so = self.sales_orders.get(log.so_id_id)
        if log.outwarded_by_user_id_id is not None:
            log.outwarded_by_user = self.users.get(log.outwarded_by_user_id_id)

    def resolve_sales_order_item_outwarded_log_relations(self, log: OrderserviceSalesOrderItemOutwardedLog) -> None:
        log.domain_user = self.users.get(log.domain_user_id_id)
        log.so_item = self.sales_order_items.get(log.so_item_id_id)

    def resolve_user_shipping_address_relations(self, address: UserservicesUserShippingAddress) -> None:
        address.user = self.users.get(address.user_id)

    def resolve_activity_log_relations(self, log: UserservicesActivityLog) -> None:
        log.user = self.users.get(log.user_id)
        log.domain_user = self.users.get(log.domain_user_id_id)