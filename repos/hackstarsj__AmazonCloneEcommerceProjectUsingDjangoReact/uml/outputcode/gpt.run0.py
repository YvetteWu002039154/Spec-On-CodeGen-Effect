from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


def _now() -> datetime:
    return datetime.now()


def _require_non_negative_int(name: str, value: Optional[int]) -> None:
    if value is None:
        return
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")


def _require_non_negative_decimal(name: str, value: Optional[Decimal]) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be Decimal")
    if value < Decimal("0"):
        raise ValueError(f"{name} must be >= 0")


def _require_non_negative_float(name: str, value: Optional[float]) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be float")
    if float(value) < 0.0:
        raise ValueError(f"{name} must be >= 0")


def _require_str(name: str, value: Optional[str], max_len: Optional[int] = None) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if max_len is not None and len(value) > max_len:
        raise ValueError(f"{name} length must be <= {max_len}")


def _require_bool_int(name: str, value: Optional[bool]) -> None:
    if value is None:
        return
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")


def _require_json_dict(name: str, value: Optional[JsonDict]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be dict")


def _require_json_list(name: str, value: Optional[List[Any]]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise TypeError(f"{name} must be list")


@dataclass
class userservices_users:
    id: int

    is_superuser: bool = False
    first_name: str = ""
    last_name: str = ""
    is_staff: bool = False
    is_active: bool = True
    date_joined: datetime = field(default_factory=_now)
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
    social_media_links: JsonDict = field(default_factory=dict)
    addition_details: JsonDict = field(default_factory=dict)
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
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    domain_user_id_id: Optional[userservices_users] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_bool_int("is_superuser", self.is_superuser)
        _require_bool_int("is_staff", self.is_staff)
        _require_bool_int("is_active", self.is_active)
        _require_str("first_name", self.first_name, 150)
        _require_str("last_name", self.last_name, 150)
        _require_str("name", self.name, 100)
        _require_str("email", self.email, 254)
        _require_str("phone", self.phone, 15)
        _require_str("city", self.city, 50)
        _require_str("state", self.state, 50)
        _require_str("pincode", self.pincode, 10)
        _require_str("country", self.country, 50)
        _require_str("account_status", self.account_status, 50)
        _require_str("role", self.role, 50)
        _require_str("username", self.username, 50)
        _require_str("password", self.password, 50)
        _require_json_dict("social_media_links", self.social_media_links)
        _require_json_dict("addition_details", self.addition_details)
        _require_str("language", self.language, 50)
        _require_str("departMent", self.departMent, 50)
        _require_str("designation", self.designation, 50)
        _require_str("time_zone", self.time_zone, 50)
        _require_str("last_device", self.last_device, 50)
        _require_str("last_ip", self.last_ip, 39)
        _require_str("currency", self.currency, 50)
        _require_str("domain_name", self.domain_name, 50)
        _require_str("plan_type", self.plan_type, 50)
        if self.domain_user_id_id is not None and not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users or None")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class userservices_usershippingaddress:
    id: int

    address_type: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    user_id: userservices_users = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("address_type", self.address_type, 50)
        _require_str("city", self.city, 50)
        _require_str("state", self.state, 50)
        _require_str("pincode", self.pincode, 10)
        _require_str("country", self.country, 50)
        if not isinstance(self.user_id, userservices_users):
            raise TypeError("user_id must be userservices_users")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class userservices_activitylog:
    id: int

    activity: str = ""
    activity_type: str = ""
    activity_date: datetime = field(default_factory=_now)
    activity_ip: str = ""
    activity_device: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    domain_user_id_id: userservices_users = field(default=None)
    user_id: userservices_users = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("activity_type", self.activity_type, 50)
        _require_str("activity_ip", self.activity_ip, 39)
        _require_str("activity_device", self.activity_device, 50)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.user_id, userservices_users):
            raise TypeError("user_id must be userservices_users")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class userservices_modules:
    id: int

    module_name: str = ""
    module_icon: str = ""
    is_menu: bool = False
    is_active: bool = True
    module_url: str = ""
    display_order: int = 0
    module_description: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    parent_id_id: Optional[userservices_modules] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("module_name", self.module_name, 50)
        _require_bool_int("is_menu", self.is_menu)
        _require_bool_int("is_active", self.is_active)
        _require_non_negative_int("display_order", self.display_order)
        if self.parent_id_id is not None and not isinstance(self.parent_id_id, userservices_modules):
            raise TypeError("parent_id_id must be userservices_modules or None")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class userservices_userpermissions:
    id: int

    is_view: bool = False
    is_add: bool = False
    is_edit: bool = False
    is_delete: bool = False
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    module_id_id: userservices_modules = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    user_id: userservices_users = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_bool_int("is_view", self.is_view)
        _require_bool_int("is_add", self.is_add)
        _require_bool_int("is_edit", self.is_edit)
        _require_bool_int("is_delete", self.is_delete)
        if not isinstance(self.module_id_id, userservices_modules):
            raise TypeError("module_id_id must be userservices_modules")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.user_id, userservices_users):
            raise TypeError("user_id must be userservices_users")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class auth_group:
    id: int
    name: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("name", self.name, 150)


@dataclass
class django_content_type:
    id: int
    app_label: str = ""
    model: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("app_label", self.app_label, 100)
        _require_str("model", self.model, 100)


@dataclass
class auth_permission:
    id: int
    name: str = ""
    codename: str = ""
    content_type_id: django_content_type = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("name", self.name, 255)
        _require_str("codename", self.codename, 100)
        if not isinstance(self.content_type_id, django_content_type):
            raise TypeError("content_type_id must be django_content_type")


@dataclass
class auth_group_permissions:
    id: int
    group_id: auth_group = field(default=None)
    permission_id: auth_permission = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        if not isinstance(self.group_id, auth_group):
            raise TypeError("group_id must be auth_group")
        if not isinstance(self.permission_id, auth_permission):
            raise TypeError("permission_id must be auth_permission")


@dataclass
class userservices_users_groups:
    id: int
    users_id: userservices_users = field(default=None)
    group_id: auth_group = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        if not isinstance(self.users_id, userservices_users):
            raise TypeError("users_id must be userservices_users")
        if not isinstance(self.group_id, auth_group):
            raise TypeError("group_id must be auth_group")


@dataclass
class userservices_users_user_permissions:
    id: int
    users_id: userservices_users = field(default=None)
    permission_id: auth_permission = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        if not isinstance(self.users_id, userservices_users):
            raise TypeError("users_id must be userservices_users")
        if not isinstance(self.permission_id, auth_permission):
            raise TypeError("permission_id must be auth_permission")


@dataclass
class django_admin_log:
    id: int

    action_time: datetime = field(default_factory=_now)
    object_id: str = ""
    object_repr: str = ""
    action_flag: int = 0
    change_message: str = ""

    content_type_id: django_content_type = field(default=None)
    user_id: userservices_users = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("object_repr", self.object_repr, 200)
        if not isinstance(self.action_flag, int):
            raise TypeError("action_flag must be int")
        if self.action_flag < 0:
            raise ValueError("action_flag must be >= 0")
        if not isinstance(self.content_type_id, django_content_type):
            raise TypeError("content_type_id must be django_content_type")
        if not isinstance(self.user_id, userservices_users):
            raise TypeError("user_id must be userservices_users")


@dataclass
class django_migrations:
    id: int
    app: str = ""
    name: str = ""
    applied: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("app", self.app, 255)
        _require_str("name", self.name, 255)


@dataclass
class django_session:
    session_key: str
    session_data: str = ""
    expire_date: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require_str("session_key", self.session_key, 40)


@dataclass
class productservices_categories:
    id: int

    name: str = ""
    image: str = ""
    description: str = ""
    display_order: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    added_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    parent_id_id: Optional[productservices_categories] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("name", self.name, 255)
        _require_non_negative_int("display_order", self.display_order)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise TypeError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if self.parent_id_id is not None and not isinstance(self.parent_id_id, productservices_categories):
            raise TypeError("parent_id_id must be productservices_categories or None")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class productservices_products:
    id: int

    name: str = ""
    image: JsonDict = field(default_factory=dict)
    description: str = ""
    specifications: JsonDict = field(default_factory=dict)
    html_description: str = ""
    highlights: JsonDict = field(default_factory=dict)
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
    seo_keywords: JsonDict = field(default_factory=dict)
    addition_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    added_by_user_id_id: userservices_users = field(default=None)
    category_id_id: productservices_categories = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("name", self.name, 255)
        _require_json_dict("image", self.image)
        _require_json_dict("specifications", self.specifications)
        _require_json_dict("highlights", self.highlights)
        _require_str("sku", self.sku, 255)
        _require_non_negative_float("initial_buying_price", self.initial_buying_price)
        _require_non_negative_float("initial_selling_price", self.initial_selling_price)
        _require_non_negative_float("weight", self.weight)
        _require_non_negative_float("tax_percentage", self.tax_percentage)
        _require_str("dimensions", self.dimensions, 255)
        _require_str("uom", self.uom, 255)
        _require_str("color", self.color, 255)
        _require_str("brand", self.brand, 255)
        _require_str("brand_model", self.brand_model, 255)
        _require_str("status", self.status, 255)
        _require_str("seo_title", self.seo_title, 255)
        _require_json_dict("seo_keywords", self.seo_keywords)
        _require_json_dict("addition_details", self.addition_details)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise TypeError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.category_id_id, productservices_categories):
            raise TypeError("category_id_id must be productservices_categories")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class productservices_productquestions:
    id: int

    question: str = ""
    answer: str = ""
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    answer_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    question_user_id_id: userservices_users = field(default=None)
    product_id_id: productservices_products = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("status", self.status, 255)
        if not isinstance(self.answer_user_id_id, userservices_users):
            raise TypeError("answer_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.question_user_id_id, userservices_users):
            raise TypeError("question_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise TypeError("product_id_id must be productservices_products")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class productservices_productreviews:
    id: int

    review_images: JsonDict = field(default_factory=dict)
    rating: float = 0.0
    reviews: str = ""
    status: str = ""

    domain_user_id_id: userservices_users = field(default=None)
    review_user_id_id: userservices_users = field(default=None)
    product_id_id: productservices_products = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_json_dict("review_images", self.review_images)
        _require_non_negative_float("rating", self.rating)
        _require_str("status", self.status, 255)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.review_user_id_id, userservices_users):
            raise TypeError("review_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise TypeError("product_id_id must be productservices_products")


@dataclass
class inventoryservices_warehouse:
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
    additional_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    added_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    warehouse_manager_id: userservices_users = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("name", self.name, 255)
        _require_str("city", self.city, 255)
        _require_str("state", self.state, 255)
        _require_str("country", self.country, 255)
        _require_str("pincode", self.pincode, 255)
        _require_str("phone", self.phone, 255)
        _require_str("email", self.email, 254)
        _require_str("status", self.status, 255)
        _require_str("size", self.size, 255)
        _require_str("capacity", self.capacity, 255)
        _require_str("warehouse_type", self.warehouse_type, 255)
        _require_json_dict("additional_details", self.additional_details)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise TypeError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.warehouse_manager_id, userservices_users):
            raise TypeError("warehouse_manager_id must be userservices_users")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class inventoryservices_rackandshelvesandfloor:
    id: int

    name: str = ""
    rack: str = ""
    shelf: str = ""
    floor: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    added_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    warehouse_id_id: inventoryservices_warehouse = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("name", self.name, 255)
        _require_str("rack", self.rack, 255)
        _require_str("shelf", self.shelf, 255)
        _require_str("floor", self.floor, 255)
        _require_json_dict("additional_details", self.additional_details)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise TypeError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise TypeError("warehouse_id_id must be inventoryservices_warehouse")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_purchaseorder:
    id: int

    po_code: str = ""
    po_date: datetime = field(default_factory=_now)
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
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    approved_by_user_id_id: Optional[userservices_users] = None
    cancelled_by_user_id_id: Optional[userservices_users] = None
    created_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    last_updated_by_user_id_id: Optional[userservices_users] = None
    received_by_user_id_id: Optional[userservices_users] = None
    returned_by_user_id_id: Optional[userservices_users] = None
    supplier_id_id: userservices_users = field(default=None)
    updated_by_user_id_id: Optional[userservices_users] = None
    warehouse_id_id: inventoryservices_warehouse = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("po_code", self.po_code, 255)
        _require_str("payment_terms", self.payment_terms, 255)
        _require_str("payment_status", self.payment_status, 255)
        _require_non_negative_decimal("total_amount", self.total_amount)
        _require_non_negative_decimal("paid_amount", self.paid_amount)
        _require_non_negative_decimal("due_amount", self.due_amount)
        _require_non_negative_decimal("discount_amount", self.discount_amount)
        _require_str("discount_type", self.discount_type, 255)
        _require_non_negative_decimal("shipping_amount", self.shipping_amount)
        _require_str("shipping_type", self.shipping_type, 255)
        _require_non_negative_decimal("shipping_tax_percentage", self.shipping_tax_percentage)
        _require_non_negative_decimal("shipping_tax_amount", self.shipping_tax_amount)
        _require_non_negative_decimal("shipping_cancelled_amount", self.shipping_cancelled_amount)
        _require_non_negative_decimal("shipping_cancelled_tax_amount", self.shipping_cancelled_tax_amount)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if self.approved_by_user_id_id is not None and not isinstance(self.approved_by_user_id_id, userservices_users):
            raise TypeError("approved_by_user_id_id must be userservices_users or None")
        if self.cancelled_by_user_id_id is not None and not isinstance(self.cancelled_by_user_id_id, userservices_users):
            raise TypeError("cancelled_by_user_id_id must be userservices_users or None")
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise TypeError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if self.last_updated_by_user_id_id is not None and not isinstance(self.last_updated_by_user_id_id, userservices_users):
            raise TypeError("last_updated_by_user_id_id must be userservices_users or None")
        if self.received_by_user_id_id is not None and not isinstance(self.received_by_user_id_id, userservices_users):
            raise TypeError("received_by_user_id_id must be userservices_users or None")
        if self.returned_by_user_id_id is not None and not isinstance(self.returned_by_user_id_id, userservices_users):
            raise TypeError("returned_by_user_id_id must be userservices_users or None")
        if not isinstance(self.supplier_id_id, userservices_users):
            raise TypeError("supplier_id_id must be userservices_users")
        if self.updated_by_user_id_id is not None and not isinstance(self.updated_by_user_id_id, userservices_users):
            raise TypeError("updated_by_user_id_id must be userservices_users or None")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise TypeError("warehouse_id_id must be inventoryservices_warehouse")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_purchaseorderitems:
    id: int

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
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    approved_by_user_id_id: Optional[userservices_users] = None
    cancelled_by_user_id_id: Optional[userservices_users] = None
    created_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    last_updated_by_user_id_id: Optional[userservices_users] = None
    received_by_user_id_id: Optional[userservices_users] = None
    returned_by_user_id_id: Optional[userservices_users] = None
    po_id_id: orderservice_purchaseorder = field(default=None)
    product_id_id: productservices_products = field(default=None)
    updated_by_user_id_id: Optional[userservices_users] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_non_negative_int("quantity_ordered", self.quantity_ordered)
        _require_non_negative_int("quantity_received", self.quantity_received)
        _require_non_negative_int("quantity_cancelled", self.quantity_cancelled)
        _require_non_negative_int("quantity_returned", self.quantity_returned)
        _require_non_negative_decimal("buying_price", self.buying_price)
        _require_non_negative_decimal("selling_price", self.selling_price)
        _require_non_negative_decimal("discount_amount", self.discount_amount)
        _require_non_negative_decimal("amount_paid", self.amount_paid)
        _require_non_negative_decimal("amount_returned", self.amount_returned)
        _require_non_negative_decimal("amount_cancelled", self.amount_cancelled)
        _require_non_negative_decimal("amount_ordered", self.amount_ordered)
        _require_non_negative_decimal("tax_percentage", self.tax_percentage)
        _require_non_negative_decimal("tax_amount", self.tax_amount)
        _require_non_negative_decimal("shipping_tax_percentage", self.shipping_tax_percentage)
        _require_non_negative_decimal("shipping_amount", self.shipping_amount)
        _require_non_negative_decimal("shipping_tax_amount", self.shipping_tax_amount)
        _require_non_negative_decimal("shipping_cancelled_amount", self.shipping_cancelled_amount)
        _require_non_negative_decimal("shipping_cancelled_tax_amount", self.shipping_cancelled_tax_amount)
        _require_str("discount_type", self.discount_type, 255)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if self.approved_by_user_id_id is not None and not isinstance(self.approved_by_user_id_id, userservices_users):
            raise TypeError("approved_by_user_id_id must be userservices_users or None")
        if self.cancelled_by_user_id_id is not None and not isinstance(self.cancelled_by_user_id_id, userservices_users):
            raise TypeError("cancelled_by_user_id_id must be userservices_users or None")
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise TypeError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if self.last_updated_by_user_id_id is not None and not isinstance(self.last_updated_by_user_id_id, userservices_users):
            raise TypeError("last_updated_by_user_id_id must be userservices_users or None")
        if self.received_by_user_id_id is not None and not isinstance(self.received_by_user_id_id, userservices_users):
            raise TypeError("received_by_user_id_id must be userservices_users or None")
        if self.returned_by_user_id_id is not None and not isinstance(self.returned_by_user_id_id, userservices_users):
            raise TypeError("returned_by_user_id_id must be userservices_users or None")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise TypeError("po_id_id must be orderservice_purchaseorder")
        if not isinstance(self.product_id_id, productservices_products):
            raise TypeError("product_id_id must be productservices_products")
        if self.updated_by_user_id_id is not None and not isinstance(self.updated_by_user_id_id, userservices_users):
            raise TypeError("updated_by_user_id_id must be userservices_users or None")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_purchaseorderlogs:
    id: int

    comment: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    created_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    po_id_id: orderservice_purchaseorder = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_json_dict("additional_details", self.additional_details)
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise TypeError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise TypeError("po_id_id must be orderservice_purchaseorder")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_purchaseorderinwardedlog:
    id: int

    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    inwarded_at: datetime = field(default_factory=_now)
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    domain_user_id_id: userservices_users = field(default=None)
    inwarded_by_user_id_id: userservices_users = field(default=None)
    po_id_id: orderservice_purchaseorder = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("invoice_number", self.invoice_number, 255)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.inwarded_by_user_id_id, userservices_users):
            raise TypeError("inwarded_by_user_id_id must be userservices_users")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise TypeError("po_id_id must be orderservice_purchaseorder")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_purchaseorderiteminwardedlog:
    id: int

    inwarded_quantity: int = 0
    price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    shipping_amount: Decimal = Decimal("0.00")
    shipping_tax_percentage: Decimal = Decimal("0.00")
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    domain_user_id_id: userservices_users = field(default=None)
    po_item_id_id: orderservice_purchaseorderitems = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_non_negative_int("inwarded_quantity", self.inwarded_quantity)
        _require_non_negative_decimal("price", self.price)
        _require_non_negative_decimal("tax_percentage", self.tax_percentage)
        _require_non_negative_decimal("discount_amount", self.discount_amount)
        _require_str("discount_type", self.discount_type, 255)
        _require_non_negative_decimal("shipping_amount", self.shipping_amount)
        _require_non_negative_decimal("shipping_tax_percentage", self.shipping_tax_percentage)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.po_item_id_id, orderservice_purchaseorderitems):
            raise TypeError("po_item_id_id must be orderservice_purchaseorderitems")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_salesorder:
    id: int

    so_code: str = ""
    so_date: datetime = field(default_factory=_now)
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
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    approved_by_user_id_id: Optional[userservices_users] = None
    cancelled_by_user_id_id: Optional[userservices_users] = None
    created_by_user_id_id: userservices_users = field(default=None)
    customer_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    last_updated_by_user_id_id: Optional[userservices_users] = None
    received_by_user_id_id: Optional[userservices_users] = None
    returned_by_user_id_id: Optional[userservices_users] = None
    po_id_id: Optional[orderservice_purchaseorder] = None
    product_id_id: Optional[productservices_products] = None
    updated_by_user_id_id: Optional[userservices_users] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("so_code", self.so_code, 255)
        _require_str("payment_terms", self.payment_terms, 255)
        _require_str("payment_status", self.payment_status, 255)
        _require_non_negative_decimal("total_amount", self.total_amount)
        _require_non_negative_decimal("paid_amount", self.paid_amount)
        _require_non_negative_decimal("due_amount", self.due_amount)
        _require_non_negative_decimal("discount_amount", self.discount_amount)
        _require_str("discount_type", self.discount_type, 255)
        _require_non_negative_decimal("shipping_amount", self.shipping_amount)
        _require_str("shipping_type", self.shipping_type, 255)
        _require_non_negative_decimal("shipping_tax_percentage", self.shipping_tax_percentage)
        _require_non_negative_decimal("shipping_tax_amount", self.shipping_tax_amount)
        _require_non_negative_decimal("shipping_cancelled_amount", self.shipping_cancelled_amount)
        _require_non_negative_decimal("shipping_cancelled_tax_amount", self.shipping_cancelled_tax_amount)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if self.approved_by_user_id_id is not None and not isinstance(self.approved_by_user_id_id, userservices_users):
            raise TypeError("approved_by_user_id_id must be userservices_users or None")
        if self.cancelled_by_user_id_id is not None and not isinstance(self.cancelled_by_user_id_id, userservices_users):
            raise TypeError("cancelled_by_user_id_id must be userservices_users or None")
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise TypeError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.customer_id_id, userservices_users):
            raise TypeError("customer_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if self.last_updated_by_user_id_id is not None and not isinstance(self.last_updated_by_user_id_id, userservices_users):
            raise TypeError("last_updated_by_user_id_id must be userservices_users or None")
        if self.received_by_user_id_id is not None and not isinstance(self.received_by_user_id_id, userservices_users):
            raise TypeError("received_by_user_id_id must be userservices_users or None")
        if self.returned_by_user_id_id is not None and not isinstance(self.returned_by_user_id_id, userservices_users):
            raise TypeError("returned_by_user_id_id must be userservices_users or None")
        if self.po_id_id is not None and not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise TypeError("po_id_id must be orderservice_purchaseorder or None")
        if self.product_id_id is not None and not isinstance(self.product_id_id, productservices_products):
            raise TypeError("product_id_id must be productservices_products or None")
        if self.updated_by_user_id_id is not None and not isinstance(self.updated_by_user_id_id, userservices_users):
            raise TypeError("updated_by_user_id_id must be userservices_users or None")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_salesorderorderitems:
    id: int

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
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    approved_by_user_id_id: Optional[userservices_users] = None
    cancelled_by_user_id_id: Optional[userservices_users] = None
    created_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    product_id_id: productservices_products = field(default=None)
    returned_by_user_id_id: Optional[userservices_users] = None
    shipped_by_user_id_id: Optional[userservices_users] = None
    so_id_id: orderservice_salesorder = field(default=None)
    updated_by_user_id_id: Optional[userservices_users] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_non_negative_int("quantity_ordered", self.quantity_ordered)
        _require_non_negative_int("quantity_delivered", self.quantity_delivered)
        _require_non_negative_int("quantity_shipped", self.quantity_shipped)
        _require_non_negative_int("quantity_cancelled", self.quantity_cancelled)
        _require_non_negative_int("quantity_returned", self.quantity_returned)
        _require_non_negative_decimal("purchase_price", self.purchase_price)
        _require_non_negative_decimal("discount_amount", self.discount_amount)
        _require_str("discount_type", self.discount_type, 255)
        _require_non_negative_decimal("amount_paid", self.amount_paid)
        _require_non_negative_decimal("amount_returned", self.amount_returned)
        _require_non_negative_decimal("amount_cancelled", self.amount_cancelled)
        _require_non_negative_decimal("amount_ordered", self.amount_ordered)
        _require_non_negative_decimal("tax_percentage", self.tax_percentage)
        _require_non_negative_decimal("tax_amount", self.tax_amount)
        _require_non_negative_decimal("shipping_amount", self.shipping_amount)
        _require_str("shipping_type", self.shipping_type, 255)
        _require_non_negative_decimal("shipping_tax_amount", self.shipping_tax_amount)
        _require_non_negative_decimal("shipping_cancelled_amount", self.shipping_cancelled_amount)
        _require_non_negative_decimal("shipping_cancelled_tax_amount", self.shipping_cancelled_tax_amount)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if self.approved_by_user_id_id is not None and not isinstance(self.approved_by_user_id_id, userservices_users):
            raise TypeError("approved_by_user_id_id must be userservices_users or None")
        if self.cancelled_by_user_id_id is not None and not isinstance(self.cancelled_by_user_id_id, userservices_users):
            raise TypeError("cancelled_by_user_id_id must be userservices_users or None")
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise TypeError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise TypeError("product_id_id must be productservices_products")
        if self.returned_by_user_id_id is not None and not isinstance(self.returned_by_user_id_id, userservices_users):
            raise TypeError("returned_by_user_id_id must be userservices_users or None")
        if self.shipped_by_user_id_id is not None and not isinstance(self.shipped_by_user_id_id, userservices_users):
            raise TypeError("shipped_by_user_id_id must be userservices_users or None")
        if not isinstance(self.so_id_id, orderservice_salesorder):
            raise TypeError("so_id_id must be orderservice_salesorder")
        if self.updated_by_user_id_id is not None and not isinstance(self.updated_by_user_id_id, userservices_users):
            raise TypeError("updated_by_user_id_id must be userservices_users or None")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_salesorderlogs:
    id: int

    comment: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    created_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    so_id_id: orderservice_salesorder = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_json_dict("additional_details", self.additional_details)
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise TypeError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.so_id_id, orderservice_salesorder):
            raise TypeError("so_id_id must be orderservice_salesorder")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_salesorderoutwardedlog:
    id: int

    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    outwared_at: datetime = field(default_factory=_now)
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    domain_user_id_id: userservices_users = field(default=None)
    outwarded_by_user_id_id: userservices_users = field(default=None)
    so_id_id: orderservice_salesorder = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_str("invoice_number", self.invoice_number, 255)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.outwarded_by_user_id_id, userservices_users):
            raise TypeError("outwarded_by_user_id_id must be userservices_users")
        if not isinstance(self.so_id_id, orderservice_salesorder):
            raise TypeError("so_id_id must be orderservice_salesorder")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class orderservice_salesorderitemoutwardedlog:
    id: int

    outwarded_quantity: int = 0
    price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str = ""
    shipping_amount: Decimal = Decimal("0.00")
    shipping_tax_percentage: Decimal = Decimal("0.00")
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    domain_user_id_id: userservices_users = field(default=None)
    so_item_id_id: orderservice_salesorderorderitems = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_non_negative_int("outwarded_quantity", self.outwarded_quantity)
        _require_non_negative_decimal("price", self.price)
        _require_non_negative_decimal("tax_percentage", self.tax_percentage)
        _require_non_negative_decimal("discount_amount", self.discount_amount)
        _require_str("discount_type", self.discount_type, 255)
        _require_non_negative_decimal("shipping_amount", self.shipping_amount)
        _require_non_negative_decimal("shipping_tax_percentage", self.shipping_tax_percentage)
        _require_json_dict("additional_details", self.additional_details)
        _require_str("status", self.status, 255)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.so_item_id_id, orderservice_salesorderorderitems):
            raise TypeError("so_item_id_id must be orderservice_salesorderorderitems")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class inventoryservices_inventory:
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
    buy_price: Decimal = Decimal("0.00")
    sell_price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    stock_status: str = ""
    inward_type: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    added_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    product_id_id: productservices_products = field(default=None)
    purchase_order_id_id: orderservice_purchaseorder = field(default=None)
    purchase_order_item_id_id: orderservice_purchaseorderitems = field(default=None)
    purchase_order_item_inwarded_item_id_id: Optional[orderservice_purchaseorderiteminwardedlog] = None
    rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor = field(default=None)
    warehouse_id_id: inventoryservices_warehouse = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_non_negative_int("quantity", self.quantity)
        _require_str("mrp", self.mrp, 255)
        _require_str("batch_number", self.batch_number, 255)
        _require_str("discount_type", self.discount_type, 255)
        _require_non_negative_float("discount_amout", self.discount_amout)
        _require_str("sr_no", self.sr_no, 255)
        _require_str("uom", self.uom, 255)
        _require_str("ptr", self.ptr, 255)
        _require_non_negative_int("quantity_inwarded", self.quantity_inwarded)
        _require_non_negative_decimal("buy_price", self.buy_price)
        _require_non_negative_decimal("sell_price", self.sell_price)
        _require_non_negative_decimal("tax_percentage", self.tax_percentage)
        _require_str("stock_status", self.stock_status, 255)
        _require_str("inward_type", self.inward_type, 255)
        _require_json_dict("additional_details", self.additional_details)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise TypeError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise TypeError("product_id_id must be productservices_products")
        if not isinstance(self.purchase_order_id_id, orderservice_purchaseorder):
            raise TypeError("purchase_order_id_id must be orderservice_purchaseorder")
        if not isinstance(self.purchase_order_item_id_id, orderservice_purchaseorderitems):
            raise TypeError("purchase_order_item_id_id must be orderservice_purchaseorderitems")
        if self.purchase_order_item_inwarded_item_id_id is not None and not isinstance(
            self.purchase_order_item_inwarded_item_id_id, orderservice_purchaseorderiteminwardedlog
        ):
            raise TypeError("purchase_order_item_inwarded_item_id_id must be orderservice_purchaseorderiteminwardedlog or None")
        if not isinstance(self.rack_shelf_floor_id_id, inventoryservices_rackandshelvesandfloor):
            raise TypeError("rack_shelf_floor_id_id must be inventoryservices_rackandshelvesandfloor")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise TypeError("warehouse_id_id must be inventoryservices_warehouse")

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class inventoryservices_inventorylog:
    id: int

    quantity: int = 0
    status: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    added_by_user_id_id: userservices_users = field(default=None)
    domain_user_id_id: userservices_users = field(default=None)
    inventory_id_id: inventoryservices_inventory = field(default=None)
    po_id_id: Optional[orderservice_purchaseorder] = None
    so_id_id: Optional[orderservice_salesorder] = None
    rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor = field(default=None)
    warehouse_id_id: inventoryservices_warehouse = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.id, int):
            raise TypeError("id must be int")
        _require_non_negative_int("quantity", self.quantity)
        _require_str("status", self.status, 255)
        _require_json_dict("additional_details", self.additional_details)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise TypeError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise TypeError("domain_user_id_id must be userservices_users")
        if not isinstance(self.inventory_id_id, inventoryservices_inventory):
            raise TypeError("inventory_id_id must be inventoryservices_inventory")
        if self.po_id_id is not None and not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise TypeError("po_id_id must be orderservice_purchaseorder or None")
        if self.so_id_id is not None and not isinstance(self.so_id_id, orderservice_salesorder):
            raise TypeError("so_id_id must be orderservice_salesorder or None")
        if not isinstance(self.rack_shelf_floor_id_id, inventoryservices_rackandshelvesandfloor):
            raise TypeError("rack_shelf_floor_id_id must be inventoryservices_rackandshelvesandfloor")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise TypeError("warehouse_id_id must be inventoryservices_warehouse")

    def touch(self) -> None:
        self.updated_at = _now()