from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


class ValidationError(ValueError):
    pass


class BaseEntity:
    def touch_updated(self) -> None:
        if hasattr(self, "updated_at"):
            setattr(self, "updated_at", datetime.utcnow())


def _validate_non_negative_int(name: str, value: Optional[int]) -> None:
    if value is None:
        return
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be int")
    if value < 0:
        raise ValidationError(f"{name} must be non-negative")


def _validate_non_negative_decimal(name: str, value: Optional[Decimal]) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise ValidationError(f"{name} must be Decimal")
    if value < Decimal("0"):
        raise ValidationError(f"{name} must be non-negative")


def _validate_non_negative_float(name: str, value: Optional[float]) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be float")
    if float(value) < 0.0:
        raise ValidationError(f"{name} must be non-negative")


def _validate_datetime(name: str, value: Optional[datetime]) -> None:
    if value is None:
        return
    if not isinstance(value, datetime):
        raise ValidationError(f"{name} must be datetime")


def _validate_date(name: str, value: Optional[date]) -> None:
    if value is None:
        return
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValidationError(f"{name} must be date")


def _validate_str(name: str, value: Optional[str], max_len: Optional[int] = None) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be str")
    if max_len is not None and len(value) > max_len:
        raise ValidationError(f"{name} exceeds max length {max_len}")


def _validate_json(name: str, value: Optional[JsonDict]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be dict")


@dataclass
class userservices_users(BaseEntity):
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
    social_media_links: JsonDict
    addition_details: JsonDict
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
    domain_user_id_id: Optional[userservices_users] = None

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("date_joined", self.date_joined)
        _validate_date("dob", self.dob)
        _validate_datetime("last_login", self.last_login)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        _validate_str("email", self.email, 254)
        _validate_str("phone", self.phone, 15)
        _validate_str("pincode", self.pincode, 10)
        _validate_str("last_ip", self.last_ip, 39)
        _validate_json("social_media_links", self.social_media_links)
        _validate_json("addition_details", self.addition_details)
        if self.domain_user_id_id is not None and not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users or None")


@dataclass
class userservices_usershippingaddress(BaseEntity):
    id: int
    address_type: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    created_at: datetime
    updated_at: datetime
    user_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")


@dataclass
class userservices_activitylog(BaseEntity):
    id: int
    activity: str
    activity_type: str
    activity_date: datetime
    activity_ip: str
    activity_device: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: userservices_users
    user_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("activity_date", self.activity_date)
        _validate_str("activity_ip", self.activity_ip, 39)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")


@dataclass
class userservices_modules(BaseEntity):
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
    parent_id_id: Optional[userservices_modules] = None

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_non_negative_int("display_order", self.display_order)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if self.parent_id_id is not None and not isinstance(self.parent_id_id, userservices_modules):
            raise ValidationError("parent_id_id must be userservices_modules or None")


@dataclass
class userservices_userpermissions(BaseEntity):
    id: int
    is_view: bool
    is_add: bool
    is_edit: bool
    is_delete: bool
    created_at: datetime
    updated_at: datetime
    module_id_id: userservices_modules
    domain_user_id_id: userservices_users
    user_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.module_id_id, userservices_modules):
            raise ValidationError("module_id_id must be userservices_modules")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")


@dataclass
class auth_group(BaseEntity):
    id: int
    name: str

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_str("name", self.name, 150)


@dataclass
class django_content_type(BaseEntity):
    id: int
    app_label: str
    model: str

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_str("app_label", self.app_label, 100)
        _validate_str("model", self.model, 100)


@dataclass
class auth_permission(BaseEntity):
    id: int
    name: str
    codename: str
    content_type_id: django_content_type

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_str("name", self.name, 255)
        _validate_str("codename", self.codename, 100)
        if not isinstance(self.content_type_id, django_content_type):
            raise ValidationError("content_type_id must be django_content_type")


@dataclass
class auth_group_permissions(BaseEntity):
    id: int
    group_id: auth_group
    permission_id: auth_permission

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        if not isinstance(self.group_id, auth_group):
            raise ValidationError("group_id must be auth_group")
        if not isinstance(self.permission_id, auth_permission):
            raise ValidationError("permission_id must be auth_permission")


@dataclass
class userservices_users_groups(BaseEntity):
    id: int
    users_id: userservices_users
    group_id: auth_group

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        if not isinstance(self.users_id, userservices_users):
            raise ValidationError("users_id must be userservices_users")
        if not isinstance(self.group_id, auth_group):
            raise ValidationError("group_id must be auth_group")


@dataclass
class userservices_users_user_permissions(BaseEntity):
    id: int
    users_id: userservices_users
    permission_id: auth_permission

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        if not isinstance(self.users_id, userservices_users):
            raise ValidationError("users_id must be userservices_users")
        if not isinstance(self.permission_id, auth_permission):
            raise ValidationError("permission_id must be auth_permission")


@dataclass
class django_admin_log(BaseEntity):
    id: int
    action_time: datetime
    object_id: str
    object_repr: str
    action_flag: int
    change_message: str
    content_type_id: django_content_type
    user_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("action_time", self.action_time)
        _validate_str("object_repr", self.object_repr, 200)
        if not isinstance(self.content_type_id, django_content_type):
            raise ValidationError("content_type_id must be django_content_type")
        if not isinstance(self.user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")


@dataclass
class django_migrations(BaseEntity):
    id: int
    app: str
    name: str
    applied: datetime

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("applied", self.applied)


@dataclass
class django_session(BaseEntity):
    session_key: str
    session_data: str
    expire_date: datetime

    def __post_init__(self) -> None:
        _validate_str("session_key", self.session_key, 40)
        _validate_datetime("expire_date", self.expire_date)


@dataclass
class productservices_categories(BaseEntity):
    id: int
    name: str
    image: str
    description: str
    display_order: int
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    parent_id_id: Optional[productservices_categories] = None

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_non_negative_int("display_order", self.display_order)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if self.parent_id_id is not None and not isinstance(self.parent_id_id, productservices_categories):
            raise ValidationError("parent_id_id must be productservices_categories or None")


@dataclass
class productservices_products(BaseEntity):
    id: int
    name: str
    image: JsonDict
    description: str
    specifications: JsonDict
    html_description: str
    highlights: JsonDict
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
    seo_keywords: JsonDict
    addition_details: JsonDict
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: userservices_users
    category_id_id: productservices_categories
    domain_user_id_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_json("image", self.image)
        _validate_json("specifications", self.specifications)
        _validate_json("highlights", self.highlights)
        _validate_json("seo_keywords", self.seo_keywords)
        _validate_json("addition_details", self.addition_details)
        _validate_non_negative_float("initial_buying_price", self.initial_buying_price)
        _validate_non_negative_float("initial_selling_price", self.initial_selling_price)
        _validate_non_negative_float("weight", self.weight)
        _validate_non_negative_float("tax_percentage", self.tax_percentage)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.category_id_id, productservices_categories):
            raise ValidationError("category_id_id must be productservices_categories")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")


@dataclass
class productservices_productquestions(BaseEntity):
    id: int
    question: str
    answer: str
    status: str
    created_at: datetime
    updated_at: datetime
    answer_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    question_user_id_id: userservices_users
    product_id_id: productservices_products

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.answer_user_id_id, userservices_users):
            raise ValidationError("answer_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.question_user_id_id, userservices_users):
            raise ValidationError("question_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")


@dataclass
class productservices_productreviews(BaseEntity):
    id: int
    review_images: JsonDict
    rating: float
    reviews: str
    status: str
    domain_user_id_id: userservices_users
    review_user_id_id: userservices_users
    product_id_id: productservices_products

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_json("review_images", self.review_images)
        _validate_non_negative_float("rating", self.rating)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.review_user_id_id, userservices_users):
            raise ValidationError("review_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")


@dataclass
class inventoryservices_warehouse(BaseEntity):
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
    additional_details: JsonDict
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    warehouse_manager_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_str("email", self.email, 254)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.warehouse_manager_id, userservices_users):
            raise ValidationError("warehouse_manager_id must be userservices_users")


@dataclass
class inventoryservices_rackandshelvesandfloor(BaseEntity):
    id: int
    name: str
    rack: str
    shelf: str
    floor: str
    additional_details: JsonDict
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    warehouse_id_id: inventoryservices_warehouse

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")


@dataclass
class orderservice_purchaseorder(BaseEntity):
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
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: datetime
    cancelled_at: datetime
    cancelled_reason: str
    received_at: datetime
    returned_at: datetime
    approved_by_user_id_id: userservices_users
    cancelled_by_user_id_id: userservices_users
    created_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    last_updated_by_user_id_id: userservices_users
    received_by_user_id_id: userservices_users
    returned_by_user_id_id: userservices_users
    supplier_id_id: userservices_users
    updated_by_user_id_id: userservices_users
    warehouse_id_id: inventoryservices_warehouse

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("po_date", self.po_date)
        _validate_datetime("expected_delivery_date", self.expected_delivery_date)
        for n in (
            "total_amount",
            "paid_amount",
            "due_amount",
            "discount_amount",
            "shipping_amount",
            "shipping_tax_percentage",
            "shipping_tax_amount",
            "shipping_cancelled_amount",
            "shipping_cancelled_tax_amount",
        ):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        for n in ("created_at", "updated_at", "approved_at", "cancelled_at", "received_at", "returned_at"):
            _validate_datetime(n, getattr(self, n))
        for rel in (
            "approved_by_user_id_id",
            "cancelled_by_user_id_id",
            "created_by_user_id_id",
            "domain_user_id_id",
            "last_updated_by_user_id_id",
            "received_by_user_id_id",
            "returned_by_user_id_id",
            "supplier_id_id",
            "updated_by_user_id_id",
        ):
            if not isinstance(getattr(self, rel), userservices_users):
                raise ValidationError(f"{rel} must be userservices_users")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")


@dataclass
class orderservice_purchaseorderitems(BaseEntity):
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
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: datetime
    cancelled_at: datetime
    cancelled_reason: str
    received_at: datetime
    returned_at: datetime
    approved_by_user_id_id: userservices_users
    cancelled_by_user_id_id: userservices_users
    created_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    last_updated_by_user_id_id: userservices_users
    received_by_user_id_id: userservices_users
    returned_by_user_id_id: userservices_users
    po_id_id: orderservice_purchaseorder
    product_id_id: productservices_products
    updated_by_user_id_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        for n in ("quantity_ordered", "quantity_received", "quantity_cancelled", "quantity_returned"):
            _validate_non_negative_int(n, getattr(self, n))
        for n in (
            "buying_price",
            "selling_price",
            "discount_amount",
            "amount_paid",
            "amount_returned",
            "amount_cancelled",
            "amount_ordered",
            "tax_percentage",
            "tax_amount",
            "shipping_tax_percentage",
            "shipping_amount",
            "shipping_tax_amount",
            "shipping_cancelled_amount",
            "shipping_cancelled_tax_amount",
        ):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        for n in ("created_at", "updated_at", "approved_at", "cancelled_at", "received_at", "returned_at"):
            _validate_datetime(n, getattr(self, n))
        for rel in (
            "approved_by_user_id_id",
            "cancelled_by_user_id_id",
            "created_by_user_id_id",
            "domain_user_id_id",
            "last_updated_by_user_id_id",
            "received_by_user_id_id",
            "returned_by_user_id_id",
            "updated_by_user_id_id",
        ):
            if not isinstance(getattr(self, rel), userservices_users):
                raise ValidationError(f"{rel} must be userservices_users")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")
        if not isinstance(self.product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")


@dataclass
class orderservice_purchaseorderlogs(BaseEntity):
    id: int
    comment: str
    additional_details: JsonDict
    created_at: datetime
    updated_at: datetime
    created_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    po_id_id: orderservice_purchaseorder

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise ValidationError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")


@dataclass
class orderservice_purchaseorderinwardedlog(BaseEntity):
    id: int
    invoice_path: str
    invoice_number: str
    notes: str
    inwarded_at: datetime
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: userservices_users
    inwarded_by_user_id_id: userservices_users
    po_id_id: orderservice_purchaseorder

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("inwarded_at", self.inwarded_at)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.inwarded_by_user_id_id, userservices_users):
            raise ValidationError("inwarded_by_user_id_id must be userservices_users")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")


@dataclass
class orderservice_purchaseorderiteminwardedlog(BaseEntity):
    id: int
    inwarded_quantity: int
    price: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_tax_percentage: Decimal
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: userservices_users
    po_item_id_id: orderservice_purchaseorderitems

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_non_negative_int("inwarded_quantity", self.inwarded_quantity)
        for n in ("price", "tax_percentage", "discount_amount", "shipping_amount", "shipping_tax_percentage"):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.po_item_id_id, orderservice_purchaseorderitems):
            raise ValidationError("po_item_id_id must be orderservice_purchaseorderitems")


@dataclass
class orderservice_salesorder(BaseEntity):
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
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: datetime
    cancelled_at: datetime
    cancelled_reason: str
    received_at: datetime
    returned_at: datetime
    approved_by_user_id_id: userservices_users
    cancelled_by_user_id_id: userservices_users
    created_by_user_id_id: userservices_users
    customer_id_id: userservices_users
    domain_user_id_id: userservices_users
    last_updated_by_user_id_id: userservices_users
    received_by_user_id_id: userservices_users
    returned_by_user_id_id: userservices_users
    po_id_id: orderservice_purchaseorder
    product_id_id: productservices_products
    updated_by_user_id_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("so_date", self.so_date)
        _validate_datetime("expected_delivery_date", self.expected_delivery_date)
        for n in (
            "total_amount",
            "paid_amount",
            "due_amount",
            "discount_amount",
            "shipping_amount",
            "shipping_tax_percentage",
            "shipping_tax_amount",
            "shipping_cancelled_amount",
            "shipping_cancelled_tax_amount",
        ):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        for n in ("created_at", "updated_at", "approved_at", "cancelled_at", "received_at", "returned_at"):
            _validate_datetime(n, getattr(self, n))
        for rel in (
            "approved_by_user_id_id",
            "cancelled_by_user_id_id",
            "created_by_user_id_id",
            "customer_id_id",
            "domain_user_id_id",
            "last_updated_by_user_id_id",
            "received_by_user_id_id",
            "returned_by_user_id_id",
            "updated_by_user_id_id",
        ):
            if not isinstance(getattr(self, rel), userservices_users):
                raise ValidationError(f"{rel} must be userservices_users")
        if not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")
        if not isinstance(self.product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")


@dataclass
class orderservice_salesorderorderitems(BaseEntity):
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
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: datetime
    cancelled_at: datetime
    cancelled_reason: str
    shipped_at: datetime
    returned_at: datetime
    approved_by_user_id_id: userservices_users
    cancelled_by_user_id_id: userservices_users
    created_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    product_id_id: productservices_products
    returned_by_user_id_id: userservices_users
    shipped_by_user_id_id: userservices_users
    so_id_id: orderservice_salesorder
    updated_by_user_id_id: userservices_users

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        for n in (
            "quantity_ordered",
            "quantity_delivered",
            "quantity_shipped",
            "quantity_cancelled",
            "quantity_returned",
        ):
            _validate_non_negative_int(n, getattr(self, n))
        for n in (
            "purchase_price",
            "discount_amount",
            "amount_paid",
            "amount_returned",
            "amount_cancelled",
            "amount_ordered",
            "tax_percentage",
            "tax_amount",
            "shipping_amount",
            "shipping_tax_amount",
            "shipping_cancelled_amount",
            "shipping_cancelled_tax_amount",
        ):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        for n in ("created_at", "updated_at", "approved_at", "cancelled_at", "shipped_at", "returned_at"):
            _validate_datetime(n, getattr(self, n))
        for rel in (
            "approved_by_user_id_id",
            "cancelled_by_user_id_id",
            "created_by_user_id_id",
            "domain_user_id_id",
            "returned_by_user_id_id",
            "shipped_by_user_id_id",
            "updated_by_user_id_id",
        ):
            if not isinstance(getattr(self, rel), userservices_users):
                raise ValidationError(f"{rel} must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")
        if not isinstance(self.so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder")


@dataclass
class orderservice_salesorderlogs(BaseEntity):
    id: int
    comment: str
    additional_details: JsonDict
    created_at: datetime
    updated_at: datetime
    created_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    so_id_id: orderservice_salesorder

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.created_by_user_id_id, userservices_users):
            raise ValidationError("created_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder")


@dataclass
class orderservice_salesorderoutwardedlog(BaseEntity):
    id: int
    invoice_path: str
    invoice_number: str
    notes: str
    outwared_at: datetime
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: userservices_users
    outwarded_by_user_id_id: userservices_users
    so_id_id: orderservice_salesorder

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_datetime("outwared_at", self.outwared_at)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.outwarded_by_user_id_id, userservices_users):
            raise ValidationError("outwarded_by_user_id_id must be userservices_users")
        if not isinstance(self.so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder")


@dataclass
class orderservice_salesorderitemoutwardedlog(BaseEntity):
    id: int
    outwarded_quantity: int
    price: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_tax_percentage: Decimal
    additional_details: JsonDict
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: userservices_users
    so_item_id_id: orderservice_salesorderorderitems

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_non_negative_int("outwarded_quantity", self.outwarded_quantity)
        for n in ("price", "tax_percentage", "discount_amount", "shipping_amount", "shipping_tax_percentage"):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.so_item_id_id, orderservice_salesorderorderitems):
            raise ValidationError("so_item_id_id must be orderservice_salesorderorderitems")


@dataclass
class inventoryservices_inventory(BaseEntity):
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
    additional_details: JsonDict
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    product_id_id: productservices_products
    purchase_order_id_id: orderservice_purchaseorder
    purchase_order_item_id_id: orderservice_purchaseorderitems
    purchase_order_item_inwarded_item_id_id: Optional[orderservice_purchaseorderiteminwardedlog]
    rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor
    warehouse_id_id: inventoryservices_warehouse

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_non_negative_int("quantity", self.quantity)
        _validate_non_negative_int("quantity_inwarded", self.quantity_inwarded)
        _validate_non_negative_float("discount_amout", self.discount_amout)
        for n in ("mfg_date", "received_date", "expiry_date", "created_at", "updated_at"):
            _validate_datetime(n, getattr(self, n))
        for n in ("buy_price", "sell_price", "tax_percentage"):
            _validate_non_negative_decimal(n, getattr(self, n))
        _validate_json("additional_details", self.additional_details)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")
        if not isinstance(self.purchase_order_id_id, orderservice_purchaseorder):
            raise ValidationError("purchase_order_id_id must be orderservice_purchaseorder")
        if not isinstance(self.purchase_order_item_id_id, orderservice_purchaseorderitems):
            raise ValidationError("purchase_order_item_id_id must be orderservice_purchaseorderitems")
        if self.purchase_order_item_inwarded_item_id_id is not None and not isinstance(
            self.purchase_order_item_inwarded_item_id_id, orderservice_purchaseorderiteminwardedlog
        ):
            raise ValidationError("purchase_order_item_inwarded_item_id_id must be orderservice_purchaseorderiteminwardedlog or None")
        if not isinstance(self.rack_shelf_floor_id_id, inventoryservices_rackandshelvesandfloor):
            raise ValidationError("rack_shelf_floor_id_id must be inventoryservices_rackandshelvesandfloor")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")


@dataclass
class inventoryservices_inventorylog(BaseEntity):
    id: int
    quantity: int
    status: str
    additional_details: JsonDict
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: userservices_users
    domain_user_id_id: userservices_users
    inventory_id_id: inventoryservices_inventory
    po_id_id: Optional[orderservice_purchaseorder]
    so_id_id: Optional[orderservice_salesorder]
    rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor
    warehouse_id_id: inventoryservices_warehouse

    def __post_init__(self) -> None:
        _validate_non_negative_int("id", self.id)
        _validate_non_negative_int("quantity", self.quantity)
        _validate_json("additional_details", self.additional_details)
        _validate_datetime("created_at", self.created_at)
        _validate_datetime("updated_at", self.updated_at)
        if not isinstance(self.added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(self.domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(self.inventory_id_id, inventoryservices_inventory):
            raise ValidationError("inventory_id_id must be inventoryservices_inventory")
        if self.po_id_id is not None and not isinstance(self.po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder or None")
        if self.so_id_id is not None and not isinstance(self.so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder or None")
        if not isinstance(self.rack_shelf_floor_id_id, inventoryservices_rackandshelvesandfloor):
            raise ValidationError("rack_shelf_floor_id_id must be inventoryservices_rackandshelvesandfloor")
        if not isinstance(self.warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")