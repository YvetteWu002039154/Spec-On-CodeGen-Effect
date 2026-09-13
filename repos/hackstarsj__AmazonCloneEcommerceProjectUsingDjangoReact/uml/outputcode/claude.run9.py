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
    department: str = ""
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
    domain_user: Optional['UserservicesUsers'] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.first_name) > 150:
            raise ValueError("first_name max length is 150")
        if len(self.last_name) > 150:
            raise ValueError("last_name max length is 150")
        if len(self.email) > 254:
            raise ValueError("email max length is 254")
        if len(self.phone) > 15:
            raise ValueError("phone max length is 15")
        if len(self.username) > 50:
            raise ValueError("username max length is 50")
        if len(self.last_ip) > 39:
            raise ValueError("last_ip max length is 39")


@dataclass
class UserservicesUserShippingAddress:
    id: int
    address_type: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[int] = None
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
    activity: str = ""
    activity_type: str = ""
    activity_date: Optional[datetime] = None
    activity_ip: str = ""
    activity_device: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    user: Optional[UserservicesUsers] = field(default=None, repr=False)

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
    parent: Optional['UserservicesModules'] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.module_name) > 50:
            raise ValueError("module_name max length is 50")


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
#  DJANGO ADMIN LOG
# ============================================================

@dataclass
class DjangoAdminLog:
    id: int
    action_time: datetime
    object_id: str = ""
    object_repr: str = ""
    action_flag: int = 0
    change_message: str = ""
    content_type_id: Optional[int] = None
    user_id: Optional[int] = None
    content_type: Optional[DjangoContentType] = field(default=None, repr=False)
    user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.object_repr) > 200:
            raise ValueError("object_repr max length is 200")
        if self.action_flag < 0:
            raise ValueError("action_flag must be unsigned smallint")


# ============================================================
#  PRODUCT SERVICE
# ============================================================

@dataclass
class ProductservicesCategories:
    id: int
    name: str = ""
    image: str = ""
    description: str = ""
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    parent_id_id: Optional[int] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    parent: Optional['ProductservicesCategories'] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")


@dataclass
class ProductservicesProducts:
    id: int
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
    added_by_user_id_id: Optional[int] = None
    category_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    category: Optional[ProductservicesCategories] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.sku) > 255:
            raise ValueError("sku max length is 255")


@dataclass
class ProductservicesProductQuestions:
    id: int
    question: str = ""
    answer: str = ""
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    question_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
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
    review_images: Optional[Dict[str, Any]] = None
    rating: float = 0.0
    reviews: str = ""
    status: str = ""
    domain_user_id_id: Optional[int] = None
    review_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
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
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_manager_id: Optional[int] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    warehouse_manager: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.email) > 254:
            raise ValueError("email max length is 254")


@dataclass
class InventoryservicesRackAndShelvesAndFloor:
    id: int
    name: str = ""
    rack: str = ""
    shelf: str = ""
    floor: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")


# ============================================================
#  ORDER SERVICE - PURCHASE
# ============================================================

@dataclass
class OrderservicePurchaseOrder:
    id: int
    po_code: str = ""
    po_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ""
    payment_status: str = ""
    total_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    paid_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    due_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_type: str = ""
    shipping_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_type: str = ""
    shipping_tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
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
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    supplier_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
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


@dataclass
class OrderservicePurchaseOrderItems:
    id: int
    quantity_ordered: int = 0
    quantity_received: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    buying_price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    selling_price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_paid: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_returned: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_cancelled: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_ordered: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
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
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)


@dataclass
class OrderservicePurchaseOrderLogs:
    id: int
    comment: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)


@dataclass
class OrderservicePurchaseOrderInwardedLog:
    id: int
    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    inwarded_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    inwarded_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    inwarded_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.invoice_number) > 255:
            raise ValueError("invoice_number max length is 255")


@dataclass
class OrderservicePurchaseOrderItemInwardedLog:
    id: int
    inwarded_quantity: int = 0
    price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_type: str = ""
    shipping_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    po_item_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    po_item: Optional[OrderservicePurchaseOrderItems] = field(default=None, repr=False)


# ============================================================
#  ORDER SERVICE - SALES
# ============================================================

@dataclass
class OrderserviceSalesOrder:
    id: int
    so_code: str = ""
    so_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: str = ""
    payment_status: str = ""
    total_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    paid_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    due_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_type: str = ""
    shipping_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_type: str = ""
    shipping_tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
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
    customer_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
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


@dataclass
class OrderserviceSalesOrderOrderItems:
    id: int
    quantity_ordered: int = 0
    quantity_delivered: int = 0
    quantity_shipped: int = 0
    quantity_cancelled: int = 0
    quantity_returned: int = 0
    purchase_price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_type: str = ""
    amount_paid: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_returned: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_cancelled: Decimal = field(default_factory=lambda: Decimal("0.00"))
    amount_ordered: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_type: str = ""
    shipping_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_cancelled_tax_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
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
    domain_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    shipped_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
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


@dataclass
class OrderserviceSalesOrderLogs:
    id: int
    comment: str = ""
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)


@dataclass
class OrderserviceSalesOrderOutwardedLog:
    id: int
    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    outwared_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    outwarded_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    outwarded_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.invoice_number) > 255:
            raise ValueError("invoice_number max length is 255")


@dataclass
class OrderserviceSalesOrderItemOutwardedLog:
    id: int
    outwarded_quantity: int = 0
    price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    discount_type: str = ""
    shipping_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    shipping_tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    additional_details: Optional[Dict[str, Any]] = None
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    so_item_id_id: Optional[int] = None
    domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    so_item: Optional[OrderserviceSalesOrderOrderItems] = field(default=None, repr=False)


# ============================================================
#  INVENTORY SERVICE (continued - depends on order service)
# ============================================================

@dataclass
class InventoryservicesInventory:
    id: int
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
    buy_price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    sell_price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tax_percentage: Decimal = field(default_factory=lambda: Decimal("0.00"))
    stock_status: str = ""
    inward_type: str = ""
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
    quantity: int = 0
    status: str = ""
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

class DjangoContentTypeManager:
    def __init__(self):
        self._store: Dict[int, DjangoContentType] = {}

    def create(self, id: int, app_label: str, model: str) -> DjangoContentType:
        obj = DjangoContentType(id=id, app_label=app_label, model=model)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[DjangoContentType]:
        return self._store.get(id)

    def all(self) -> List[DjangoContentType]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoMigrationsManager:
    def __init__(self):
        self._store: Dict[int, DjangoMigrations] = {}

    def create(self, id: int, app: str, name: str, applied: datetime) -> DjangoMigrations:
        obj = DjangoMigrations(id=id, app=app, name=name, applied=applied)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[DjangoMigrations]:
        return self._store.get(id)

    def all(self) -> List[DjangoMigrations]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoSessionManager:
    def __init__(self):
        self._store: Dict[str, DjangoSession] = {}

    def create(self, session_key: str, session_data: str, expire_date: datetime) -> DjangoSession:
        obj = DjangoSession(session_key=session_key, session_data=session_data, expire_date=expire_date)
        self._store[session_key] = obj
        return obj

    def get(self, session_key: str) -> Optional[DjangoSession]:
        return self._store.get(session_key)

    def all(self) -> List[DjangoSession]:
        return list(self._store.values())

    def delete(self, session_key: str) -> bool:
        if session_key in self._store:
            del self._store[session_key]
            return True
        return False


class AuthPermissionManager:
    def __init__(self):
        self._store: Dict[int, AuthPermission] = {}

    def create(self, id: int, name: str, codename: str, content_type_id: int,
               content_type: Optional[DjangoContentType] = None) -> AuthPermission:
        obj = AuthPermission(id=id, name=name, codename=codename,
                             content_type_id=content_type_id, content_type=content_type)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[AuthPermission]:
        return self._store.get(id)

    def all(self) -> List[AuthPermission]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class AuthGroupManager:
    def __init__(self):
        self._store: Dict[int, AuthGroup] = {}

    def create(self, id: int, name: str) -> AuthGroup:
        obj = AuthGroup(id=id, name=name)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[AuthGroup]:
        return self._store.get(id)

    def all(self) -> List[AuthGroup]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class AuthGroupPermissionsManager:
    def __init__(self):
        self._store: Dict[int, AuthGroupPermissions] = {}

    def create(self, id: int, group_id: int, permission_id: int,
               group: Optional[AuthGroup] = None,
               permission: Optional[AuthPermission] = None) -> AuthGroupPermissions:
        obj = AuthGroupPermissions(id=id, group_id=group_id, permission_id=permission_id,
                                   group=group, permission=permission)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[AuthGroupPermissions]:
        return self._store.get(id)

    def all(self) -> List[AuthGroupPermissions]:
        return list(self._store.values())

    def filter_by_group(self, group_id: int) -> List[AuthGroupPermissions]:
        return [v for v in self._store.values() if v.group_id == group_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUsersManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUsers] = {}

    def create(self, id: int, **kwargs) -> UserservicesUsers:
        obj = UserservicesUsers(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesUsers]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsers]:
        return list(self._store.values())

    def filter_by_domain(self, domain_user_id: int) -> List[UserservicesUsers]:
        return [v for v in self._store.values() if v.domain_user_id_id == domain_user_id]

    def filter_by_role(self, role: str) -> List[UserservicesUsers]:
        return [v for v in self._store.values() if v.role == role]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUserShippingAddressManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUserShippingAddress] = {}

    def create(self, id: int, **kwargs) -> UserservicesUserShippingAddress:
        obj = UserservicesUserShippingAddress(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesUserShippingAddress]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUserShippingAddress]:
        return list(self._store.values())

    def filter_by_user(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [v for v in self._store.values() if v.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesActivityLogManager:
    def __init__(self):
        self._store: Dict[int, UserservicesActivityLog] = {}

    def create(self, id: int, **kwargs) -> UserservicesActivityLog:
        obj = UserservicesActivityLog(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesActivityLog]:
        return self._store.get(id)

    def all(self) -> List[UserservicesActivityLog]:
        return list(self._store.values())

    def filter_by_user(self, user_id: int) -> List[UserservicesActivityLog]:
        return [v for v in self._store.values() if v.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesModulesManager:
    def __init__(self):
        self._store: Dict[int, UserservicesModules] = {}

    def create(self, id: int, **kwargs) -> UserservicesModules:
        obj = UserservicesModules(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesModules]:
        return self._store.get(id)

    def all(self) -> List[UserservicesModules]:
        return list(self._store.values())

    def filter_by_parent(self, parent_id: int) -> List[UserservicesModules]:
        return [v for v in self._store.values() if v.parent_id_id == parent_id]

    def get_root_modules(self) -> List[UserservicesModules]:
        return [v for v in self._store.values() if v.parent_id_id is None]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUserPermissionsManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUserPermissions] = {}

    def create(self, id: int, **kwargs) -> UserservicesUserPermissions:
        obj = UserservicesUserPermissions(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesUserPermissions]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUserPermissions]:
        return list(self._store.values())

    def filter_by_user(self, user_id: int) -> List[UserservicesUserPermissions]:
        return [v for v in self._store.values() if v.user_id == user_id]

    def filter_by_module(self, module_id: int) -> List[UserservicesUserPermissions]:
        return [v for v in self._store.values() if v.module_id_id == module_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUsersGroupsManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUsersGroups] = {}

    def create(self, id: int, users_id: int, group_id: int,
               user: Optional[UserservicesUsers] = None,
               group: Optional[AuthGroup] = None) -> UserservicesUsersGroups:
        obj = UserservicesUsersGroups(id=id, users_id=users_id, group_id=group_id,
                                      user=user, group=group)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesUsersGroups]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsersGroups]:
        return list(self._store.values())

    def filter_by_user(self, users_id: int) -> List[UserservicesUsersGroups]:
        return [v for v in self._store.values() if v.users_id == users_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUsersUserPermissionsManager:
    def __init__(self):
        self._store: Dict[int, UserservicesUsersUserPermissions] = {}

    def create(self, id: int, users_id: int, permission_id: int,
               user: Optional[UserservicesUsers] = None,
               permission: Optional[AuthPermission] = None) -> UserservicesUsersUserPermissions:
        obj = UserservicesUsersUserPermissions(id=id, users_id=users_id,
                                               permission_id=permission_id,
                                               user=user, permission=permission)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[UserservicesUsersUserPermissions]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsersUserPermissions]:
        return list(self._store.values())

    def filter_by_user(self, users_id: int) -> List[UserservicesUsersUserPermissions]:
        return [v for v in self._store.values() if v.users_id == users_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoAdminLogManager:
    def __init__(self):
        self._store: Dict[int, DjangoAdminLog] = {}

    def create(self, id: int, action_time: datetime, **kwargs) -> DjangoAdminLog:
        obj = DjangoAdminLog(id=id, action_time=action_time, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[DjangoAdminLog]:
        return self._store.get(id)

    def all(self) -> List[DjangoAdminLog]:
        return list(self._store.values())

    def filter_by_user(self, user_id: int) -> List[DjangoAdminLog]:
        return [v for v in self._store.values() if v.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesCategoriesManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesCategories] = {}

    def create(self, id: int, **kwargs) -> ProductservicesCategories:
        obj = ProductservicesCategories(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[ProductservicesCategories]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesCategories]:
        return list(self._store.values())

    def filter_by_parent(self, parent_id: int) -> List[ProductservicesCategories]:
        return [v for v in self._store.values() if v.parent_id_id == parent_id]

    def get_root_categories(self) -> List[ProductservicesCategories]:
        return [v for v in self._store.values() if v.parent_id_id is None]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesProductsManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesProducts] = {}

    def create(self, id: int, **kwargs) -> ProductservicesProducts:
        obj = ProductservicesProducts(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[ProductservicesProducts]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProducts]:
        return list(self._store.values())

    def filter_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [v for v in self._store.values() if v.category_id_id == category_id]

    def filter_by_status(self, status: str) -> List[ProductservicesProducts]:
        return [v for v in self._store.values() if v.status == status]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesProductQuestionsManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesProductQuestions] = {}

    def create(self, id: int, **kwargs) -> ProductservicesProductQuestions:
        obj = ProductservicesProductQuestions(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[ProductservicesProductQuestions]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProductQuestions]:
        return list(self._store.values())

    def filter_by_product(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [v for v in self._store.values() if v.product_id_id == product_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesProductReviewsManager:
    def __init__(self):
        self._store: Dict[int, ProductservicesProductReviews] = {}

    def create(self, id: int, **kwargs) -> ProductservicesProductReviews:
        obj = ProductservicesProductReviews(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[ProductservicesProductReviews]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProductReviews]:
        return list(self._store.values())

    def filter_by_product(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [v for v in self._store.values() if v.product_id_id == product_id]

    def average_rating(self, product_id: int) -> float:
        reviews = self.filter_by_product(product_id)
        if not reviews:
            return 0.0
        return sum(r.rating for r in reviews) / len(reviews)

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesWarehouseManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesWarehouse] = {}

    def create(self, id: int, **kwargs) -> InventoryservicesWarehouse:
        obj = InventoryservicesWarehouse(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[InventoryservicesWarehouse]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesWarehouse]:
        return list(self._store.values())

    def filter_by_status(self, status: str) -> List[InventoryservicesWarehouse]:
        return [v for v in self._store.values() if v.status == status]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesRackAndShelvesAndFloorManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesRackAndShelvesAndFloor] = {}

    def create(self, id: int, **kwargs) -> InventoryservicesRackAndShelvesAndFloor:
        obj = InventoryservicesRackAndShelvesAndFloor(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return list(self._store.values())

    def filter_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return [v for v in self._store.values() if v.warehouse_id_id == warehouse_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesInventoryManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesInventory] = {}

    def create(self, id: int, **kwargs) -> InventoryservicesInventory:
        obj = InventoryservicesInventory(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[InventoryservicesInventory]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesInventory]:
        return list(self._store.values())

    def filter_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [v for v in self._store.values() if v.product_id_id == product_id]

    def filter_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [v for v in self._store.values() if v.warehouse_id_id == warehouse_id]

    def filter_by_stock_status(self, stock_status: str) -> List[InventoryservicesInventory]:
        return [v for v in self._store.values() if v.stock_status == stock_status]

    def total_quantity_by_product(self, product_id: int) -> int:
        return sum(v.quantity for v in self._store.values() if v.product_id_id == product_id)

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesInventoryLogManager:
    def __init__(self):
        self._store: Dict[int, InventoryservicesInventoryLog] = {}

    def create(self, id: int, **kwargs) -> InventoryservicesInventoryLog:
        obj = InventoryservicesInventoryLog(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[InventoryservicesInventoryLog]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesInventoryLog]:
        return list(self._store.values())

    def filter_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [v for v in self._store.values() if v.inventory_id_id == inventory_id]

    def filter_by_po(self, po_id: int) -> List[InventoryservicesInventoryLog]:
        return [v for v in self._store.values() if v.po_id_id == po_id]

    def filter_by_so(self, so_id: int) -> List[InventoryservicesInventoryLog]:
        return [v for v in self._store.values() if v.so_id_id == so_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrder] = {}

    def create(self, id: int, **kwargs) -> OrderservicePurchaseOrder:
        obj = OrderservicePurchaseOrder(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderservicePurchaseOrder]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrder]:
        return list(self._store.values())

    def filter_by_status(self, status: str) -> List[OrderservicePurchaseOrder]:
        return [v for v in self._store.values() if v.status == status]

    def filter_by_supplier(self, supplier_id: int) -> List[OrderservicePurchaseOrder]:
        return [v for v in self._store.values() if v.supplier_id_id == supplier_id]

    def filter_by_warehouse(self, warehouse_id: int) -> List[OrderservicePurchaseOrder]:
        return [v for v in self._store.values() if v.warehouse_id_id == warehouse_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderItemsManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderItems] = {}

    def create(self, id: int, **kwargs) -> OrderservicePurchaseOrderItems:
        obj = OrderservicePurchaseOrderItems(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderItems]:
        return list(self._store.values())

    def filter_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [v for v in self._store.values() if v.po_id_id == po_id]

    def filter_by_product(self, product_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [v for v in self._store.values() if v.product_id_id == product_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderLogsManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderLogs] = {}

    def create(self, id: int, **kwargs) -> OrderservicePurchaseOrderLogs:
        obj = OrderservicePurchaseOrderLogs(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderLogs]:
        return list(self._store.values())

    def filter_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return [v for v in self._store.values() if v.po_id_id == po_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderInwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderInwardedLog] = {}

    def create(self, id: int, **kwargs) -> OrderservicePurchaseOrderInwardedLog:
        obj = OrderservicePurchaseOrderInwardedLog(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderInwardedLog]:
        return list(self._store.values())

    def filter_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderInwardedLog]:
        return [v for v in self._store.values() if v.po_id_id == po_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderItemInwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderItemInwardedLog] = {}

    def create(self, id: int, **kwargs) -> OrderservicePurchaseOrderItemInwardedLog:
        obj = OrderservicePurchaseOrderItemInwardedLog(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return list(self._store.values())

    def filter_by_po_item(self, po_item_id: int) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return [v for v in self._store.values() if v.po_item_id_id == po_item_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrder] = {}

    def create(self, id: int, **kwargs) -> OrderserviceSalesOrder:
        obj = OrderserviceSalesOrder(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderserviceSalesOrder]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrder]:
        return list(self._store.values())

    def filter_by_status(self, status: str) -> List[OrderserviceSalesOrder]:
        return [v for v in self._store.values() if v.status == status]

    def filter_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return [v for v in self._store.values() if v.customer_id_id == customer_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderOrderItemsManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderOrderItems] = {}

    def create(self, id: int, **kwargs) -> OrderserviceSalesOrderOrderItems:
        obj = OrderserviceSalesOrderOrderItems(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderOrderItems]:
        return list(self._store.values())

    def filter_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [v for v in self._store.values() if v.so_id_id == so_id]

    def filter_by_product(self, product_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [v for v in self._store.values() if v.product_id_id == product_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderLogsManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderLogs] = {}

    def create(self, id: int, **kwargs) -> OrderserviceSalesOrderLogs:
        obj = OrderserviceSalesOrderLogs(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderLogs]:
        return list(self._store.values())

    def filter_by_so(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return [v for v in self._store.values() if v.so_id_id == so_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderOutwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderOutwardedLog] = {}

    def create(self, id: int, **kwargs) -> OrderserviceSalesOrderOutwardedLog:
        obj = OrderserviceSalesOrderOutwardedLog(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderOutwardedLog]:
        return list(self._store.values())

    def filter_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOutwardedLog]:
        return [v for v in self._store.values() if v.so_id_id == so_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderItemOutwardedLogManager:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderItemOutwardedLog] = {}

    def create(self, id: int, **kwargs) -> OrderserviceSalesOrderItemOutwardedLog:
        obj = OrderserviceSalesOrderItemOutwardedLog(id=id, **kwargs)
        self._store[id] = obj
        return obj

    def get(self, id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return list(self._store.values())

    def filter_by_so_item(self, so_item_id: int) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return [v for v in self._store.values() if v.so_item_id_id == so_item_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


# ============================================================
#  DATABASE / APPLICATION FACADE
# ============================================================

class EcommerceDatabase:
    def __init__(self):
        self.django_content_types = DjangoContentTypeManager()
        self.django_migrations = DjangoMigrationsManager()
        self.django_sessions = DjangoSessionManager()
        self.django_admin_logs = DjangoAdminLogManager()
        self.auth_permissions = AuthPermissionManager()
        self.auth_groups = AuthGroupManager()
        self.auth_group_permissions = AuthGroupPermissionsManager()
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
        self.inventories = InventoryservicesInventoryManager()
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