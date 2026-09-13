from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


class _IdMixin:
    id: Any

    def __hash__(self) -> int:
        return hash((self.__class__, getattr(self, "id", None)))


@dataclass
class userservices_users(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id: Optional["userservices_users"] = None


@dataclass
class userservices_usershippingaddress(_IdMixin):
    id: int
    address_type: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: userservices_users = field(default=None)


@dataclass
class userservices_activitylog(_IdMixin):
    id: int
    activity: str = ""
    activity_type: str = ""
    activity_date: Optional[datetime] = None
    activity_ip: str = ""
    activity_device: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id: userservices_users = field(default=None)
    user_id: userservices_users = field(default=None)


@dataclass
class userservices_modules(_IdMixin):
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
    parent_id: Optional["userservices_modules"] = None


@dataclass
class userservices_userpermissions(_IdMixin):
    id: int
    is_view: bool = False
    is_add: bool = False
    is_edit: bool = False
    is_delete: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module_id: userservices_modules = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    user_id: userservices_users = field(default=None)


@dataclass
class auth_group(_IdMixin):
    id: int
    name: str = ""


@dataclass
class django_content_type(_IdMixin):
    id: int
    app_label: str = ""
    model: str = ""


@dataclass
class auth_permission(_IdMixin):
    id: int
    name: str = ""
    codename: str = ""
    content_type_id: django_content_type = field(default=None)


@dataclass
class userservices_users_groups(_IdMixin):
    id: int
    users_id: userservices_users = field(default=None)
    group_id: auth_group = field(default=None)


@dataclass
class userservices_users_user_permissions(_IdMixin):
    id: int
    users_id: userservices_users = field(default=None)
    permission_id: auth_permission = field(default=None)


@dataclass
class auth_group_permissions(_IdMixin):
    id: int
    group_id: auth_group = field(default=None)
    permission_id: auth_permission = field(default=None)


@dataclass
class django_admin_log(_IdMixin):
    id: int
    action_time: Optional[datetime] = None
    object_id: str = ""
    object_repr: str = ""
    action_flag: int = 0
    change_message: str = ""
    content_type_id: django_content_type = field(default=None)
    user_id: userservices_users = field(default=None)


@dataclass
class django_migrations(_IdMixin):
    id: int
    app: str = ""
    name: str = ""
    applied: Optional[datetime] = None


@dataclass
class django_session(_IdMixin):
    session_key: str
    session_data: str = ""
    expire_date: Optional[datetime] = None

    @property
    def id(self) -> str:
        return self.session_key


@dataclass
class productservices_categories(_IdMixin):
    id: int
    name: str = ""
    image: str = ""
    description: str = ""
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    parent_id: Optional["productservices_categories"] = None


@dataclass
class productservices_products(_IdMixin):
    id: int
    name: str = ""
    image: Any = field(default_factory=dict)
    description: str = ""
    specifications: Any = field(default_factory=dict)
    html_description: str = ""
    highlights: Any = field(default_factory=dict)
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
    seo_keywords: Any = field(default_factory=dict)
    addition_details: Any = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id: userservices_users = field(default=None)
    category_id: productservices_categories = field(default=None)
    domain_user_id: userservices_users = field(default=None)


@dataclass
class productservices_productquestions(_IdMixin):
    id: int
    question: str = ""
    answer: str = ""
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    question_user_id: userservices_users = field(default=None)
    product_id: productservices_products = field(default=None)


@dataclass
class productservices_productreviews(_IdMixin):
    id: int
    review_images: Any = field(default_factory=dict)
    rating: float = 0.0
    reviews: str = ""
    status: str = ""
    domain_user_id: userservices_users = field(default=None)
    review_user_id: userservices_users = field(default=None)
    product_id: productservices_products = field(default=None)


@dataclass
class inventoryservices_warehouse(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    warehouse_manager_id: userservices_users = field(default=None)


@dataclass
class inventoryservices_rackandshelvesandfloor(_IdMixin):
    id: int
    name: str = ""
    rack: str = ""
    shelf: str = ""
    floor: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    warehouse_id: inventoryservices_warehouse = field(default=None)


@dataclass
class orderservice_purchaseorder(_IdMixin):
    id: int
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
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id: Optional[userservices_users] = None
    cancelled_by_user_id: Optional[userservices_users] = None
    created_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    last_updated_by_user_id: Optional[userservices_users] = None
    received_by_user_id: Optional[userservices_users] = None
    returned_by_user_id: Optional[userservices_users] = None
    supplier_id: userservices_users = field(default=None)
    updated_by_user_id: Optional[userservices_users] = None
    warehouse_id: inventoryservices_warehouse = field(default=None)


@dataclass
class orderservice_purchaseorderitems(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id: Optional[userservices_users] = None
    cancelled_by_user_id: Optional[userservices_users] = None
    created_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    last_updated_by_user_id: Optional[userservices_users] = None
    received_by_user_id: Optional[userservices_users] = None
    returned_by_user_id: Optional[userservices_users] = None
    po_id: orderservice_purchaseorder = field(default=None)
    product_id: productservices_products = field(default=None)
    updated_by_user_id: Optional[userservices_users] = None


@dataclass
class orderservice_purchaseorderlogs(_IdMixin):
    id: int
    comment: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    po_id: orderservice_purchaseorder = field(default=None)


@dataclass
class orderservice_purchaseorderinwardedlog(_IdMixin):
    id: int
    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    inwarded_at: Optional[datetime] = None
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id: userservices_users = field(default=None)
    inwarded_by_user_id: userservices_users = field(default=None)
    po_id: orderservice_purchaseorder = field(default=None)


@dataclass
class orderservice_purchaseorderiteminwardedlog(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id: userservices_users = field(default=None)
    po_item_id: orderservice_purchaseorderitems = field(default=None)


@dataclass
class orderservice_salesorder(_IdMixin):
    id: int
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
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id: Optional[userservices_users] = None
    cancelled_by_user_id: Optional[userservices_users] = None
    created_by_user_id: userservices_users = field(default=None)
    customer_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    last_updated_by_user_id: Optional[userservices_users] = None
    received_by_user_id: Optional[userservices_users] = None
    returned_by_user_id: Optional[userservices_users] = None
    po_id: Optional[orderservice_purchaseorder] = None
    product_id: Optional[productservices_products] = None
    updated_by_user_id: Optional[userservices_users] = None


@dataclass
class orderservice_salesorderorderitems(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: str = ""
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id: Optional[userservices_users] = None
    cancelled_by_user_id: Optional[userservices_users] = None
    created_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    product_id: productservices_products = field(default=None)
    returned_by_user_id: Optional[userservices_users] = None
    shipped_by_user_id: Optional[userservices_users] = None
    so_id: orderservice_salesorder = field(default=None)
    updated_by_user_id: Optional[userservices_users] = None


@dataclass
class orderservice_salesorderlogs(_IdMixin):
    id: int
    comment: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    so_id: orderservice_salesorder = field(default=None)


@dataclass
class orderservice_salesorderoutwardedlog(_IdMixin):
    id: int
    invoice_path: str = ""
    invoice_number: str = ""
    notes: str = ""
    outwared_at: Optional[datetime] = None
    additional_details: JsonDict = field(default_factory=dict)
    status: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id: userservices_users = field(default=None)
    outwarded_by_user_id: userservices_users = field(default=None)
    so_id: orderservice_salesorder = field(default=None)


@dataclass
class orderservice_salesorderitemoutwardedlog(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id: userservices_users = field(default=None)
    so_item_id: orderservice_salesorderorderitems = field(default=None)


@dataclass
class inventoryservices_inventory(_IdMixin):
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    product_id: productservices_products = field(default=None)
    purchase_order_id: orderservice_purchaseorder = field(default=None)
    purchase_order_item_id: orderservice_purchaseorderitems = field(default=None)
    purchase_order_item_inwarded_item_id: Optional[orderservice_purchaseorderiteminwardedlog] = None
    rack_shelf_floor_id: inventoryservices_rackandshelvesandfloor = field(default=None)
    warehouse_id: inventoryservices_warehouse = field(default=None)


@dataclass
class inventoryservices_inventorylog(_IdMixin):
    id: int
    quantity: int = 0
    status: str = ""
    additional_details: JsonDict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id: userservices_users = field(default=None)
    domain_user_id: userservices_users = field(default=None)
    inventory_id: inventoryservices_inventory = field(default=None)
    po_id: Optional[orderservice_purchaseorder] = None
    so_id: Optional[orderservice_salesorder] = None
    rack_shelf_floor_id: inventoryservices_rackandshelvesandfloor = field(default=None)
    warehouse_id: inventoryservices_warehouse = field(default=None)


def _validate_fk(obj: Any, expected_type: Any, field_name: str) -> None:
    if obj is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(obj, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__}")


def _validate_optional_fk(obj: Any, expected_type: Any, field_name: str) -> None:
    if obj is not None and not isinstance(obj, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__} or None")


def validate_relationships(instances: List[Any]) -> None:
    for obj in instances:
        if isinstance(obj, userservices_usershippingaddress):
            _validate_fk(obj.user_id, userservices_users, "userservices_usershippingaddress.user_id")
        elif isinstance(obj, userservices_activitylog):
            _validate_fk(obj.domain_user_id, userservices_users, "userservices_activitylog.domain_user_id")
            _validate_fk(obj.user_id, userservices_users, "userservices_activitylog.user_id")
        elif isinstance(obj, userservices_modules):
            _validate_optional_fk(obj.parent_id, userservices_modules, "userservices_modules.parent_id")
        elif isinstance(obj, userservices_userpermissions):
            _validate_fk(obj.module_id, userservices_modules, "userservices_userpermissions.module_id")
            _validate_fk(obj.domain_user_id, userservices_users, "userservices_userpermissions.domain_user_id")
            _validate_fk(obj.user_id, userservices_users, "userservices_userpermissions.user_id")
        elif isinstance(obj, userservices_users_groups):
            _validate_fk(obj.users_id, userservices_users, "userservices_users_groups.users_id")
            _validate_fk(obj.group_id, auth_group, "userservices_users_groups.group_id")
        elif isinstance(obj, userservices_users_user_permissions):
            _validate_fk(obj.users_id, userservices_users, "userservices_users_user_permissions.users_id")
            _validate_fk(obj.permission_id, auth_permission, "userservices_users_user_permissions.permission_id")
        elif isinstance(obj, auth_permission):
            _validate_fk(obj.content_type_id, django_content_type, "auth_permission.content_type_id")
        elif isinstance(obj, auth_group_permissions):
            _validate_fk(obj.group_id, auth_group, "auth_group_permissions.group_id")
            _validate_fk(obj.permission_id, auth_permission, "auth_group_permissions.permission_id")
        elif isinstance(obj, django_admin_log):
            _validate_fk(obj.content_type_id, django_content_type, "django_admin_log.content_type_id")
            _validate_fk(obj.user_id, userservices_users, "django_admin_log.user_id")
        elif isinstance(obj, productservices_categories):
            _validate_fk(obj.added_by_user_id, userservices_users, "productservices_categories.added_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "productservices_categories.domain_user_id")
            _validate_optional_fk(obj.parent_id, productservices_categories, "productservices_categories.parent_id")
        elif isinstance(obj, productservices_products):
            _validate_fk(obj.added_by_user_id, userservices_users, "productservices_products.added_by_user_id")
            _validate_fk(obj.category_id, productservices_categories, "productservices_products.category_id")
            _validate_fk(obj.domain_user_id, userservices_users, "productservices_products.domain_user_id")
        elif isinstance(obj, productservices_productquestions):
            _validate_fk(obj.answer_user_id, userservices_users, "productservices_productquestions.answer_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "productservices_productquestions.domain_user_id")
            _validate_fk(obj.question_user_id, userservices_users, "productservices_productquestions.question_user_id")
            _validate_fk(obj.product_id, productservices_products, "productservices_productquestions.product_id")
        elif isinstance(obj, productservices_productreviews):
            _validate_fk(obj.domain_user_id, userservices_users, "productservices_productreviews.domain_user_id")
            _validate_fk(obj.review_user_id, userservices_users, "productservices_productreviews.review_user_id")
            _validate_fk(obj.product_id, productservices_products, "productservices_productreviews.product_id")
        elif isinstance(obj, inventoryservices_warehouse):
            _validate_fk(obj.added_by_user_id, userservices_users, "inventoryservices_warehouse.added_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "inventoryservices_warehouse.domain_user_id")
            _validate_fk(obj.warehouse_manager_id, userservices_users, "inventoryservices_warehouse.warehouse_manager_id")
        elif isinstance(obj, inventoryservices_rackandshelvesandfloor):
            _validate_fk(obj.added_by_user_id, userservices_users, "inventoryservices_rackandshelvesandfloor.added_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "inventoryservices_rackandshelvesandfloor.domain_user_id")
            _validate_fk(obj.warehouse_id, inventoryservices_warehouse, "inventoryservices_rackandshelvesandfloor.warehouse_id")
        elif isinstance(obj, orderservice_purchaseorder):
            _validate_fk(obj.created_by_user_id, userservices_users, "orderservice_purchaseorder.created_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_purchaseorder.domain_user_id")
            _validate_fk(obj.supplier_id, userservices_users, "orderservice_purchaseorder.supplier_id")
            _validate_fk(obj.warehouse_id, inventoryservices_warehouse, "orderservice_purchaseorder.warehouse_id")
            _validate_optional_fk(obj.approved_by_user_id, userservices_users, "orderservice_purchaseorder.approved_by_user_id")
            _validate_optional_fk(obj.cancelled_by_user_id, userservices_users, "orderservice_purchaseorder.cancelled_by_user_id")
            _validate_optional_fk(obj.last_updated_by_user_id, userservices_users, "orderservice_purchaseorder.last_updated_by_user_id")
            _validate_optional_fk(obj.received_by_user_id, userservices_users, "orderservice_purchaseorder.received_by_user_id")
            _validate_optional_fk(obj.returned_by_user_id, userservices_users, "orderservice_purchaseorder.returned_by_user_id")
            _validate_optional_fk(obj.updated_by_user_id, userservices_users, "orderservice_purchaseorder.updated_by_user_id")
        elif isinstance(obj, orderservice_purchaseorderitems):
            _validate_fk(obj.created_by_user_id, userservices_users, "orderservice_purchaseorderitems.created_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_purchaseorderitems.domain_user_id")
            _validate_fk(obj.po_id, orderservice_purchaseorder, "orderservice_purchaseorderitems.po_id")
            _validate_fk(obj.product_id, productservices_products, "orderservice_purchaseorderitems.product_id")
            _validate_optional_fk(obj.approved_by_user_id, userservices_users, "orderservice_purchaseorderitems.approved_by_user_id")
            _validate_optional_fk(obj.cancelled_by_user_id, userservices_users, "orderservice_purchaseorderitems.cancelled_by_user_id")
            _validate_optional_fk(obj.last_updated_by_user_id, userservices_users, "orderservice_purchaseorderitems.last_updated_by_user_id")
            _validate_optional_fk(obj.received_by_user_id, userservices_users, "orderservice_purchaseorderitems.received_by_user_id")
            _validate_optional_fk(obj.returned_by_user_id, userservices_users, "orderservice_purchaseorderitems.returned_by_user_id")
            _validate_optional_fk(obj.updated_by_user_id, userservices_users, "orderservice_purchaseorderitems.updated_by_user_id")
        elif isinstance(obj, orderservice_purchaseorderlogs):
            _validate_fk(obj.created_by_user_id, userservices_users, "orderservice_purchaseorderlogs.created_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_purchaseorderlogs.domain_user_id")
            _validate_fk(obj.po_id, orderservice_purchaseorder, "orderservice_purchaseorderlogs.po_id")
        elif isinstance(obj, orderservice_purchaseorderinwardedlog):
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_purchaseorderinwardedlog.domain_user_id")
            _validate_fk(obj.inwarded_by_user_id, userservices_users, "orderservice_purchaseorderinwardedlog.inwarded_by_user_id")
            _validate_fk(obj.po_id, orderservice_purchaseorder, "orderservice_purchaseorderinwardedlog.po_id")
        elif isinstance(obj, orderservice_purchaseorderiteminwardedlog):
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_purchaseorderiteminwardedlog.domain_user_id")
            _validate_fk(obj.po_item_id, orderservice_purchaseorderitems, "orderservice_purchaseorderiteminwardedlog.po_item_id")
        elif isinstance(obj, orderservice_salesorder):
            _validate_fk(obj.created_by_user_id, userservices_users, "orderservice_salesorder.created_by_user_id")
            _validate_fk(obj.customer_id, userservices_users, "orderservice_salesorder.customer_id")
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_salesorder.domain_user_id")
            _validate_optional_fk(obj.approved_by_user_id, userservices_users, "orderservice_salesorder.approved_by_user_id")
            _validate_optional_fk(obj.cancelled_by_user_id, userservices_users, "orderservice_salesorder.cancelled_by_user_id")
            _validate_optional_fk(obj.last_updated_by_user_id, userservices_users, "orderservice_salesorder.last_updated_by_user_id")
            _validate_optional_fk(obj.received_by_user_id, userservices_users, "orderservice_salesorder.received_by_user_id")
            _validate_optional_fk(obj.returned_by_user_id, userservices_users, "orderservice_salesorder.returned_by_user_id")
            _validate_optional_fk(obj.updated_by_user_id, userservices_users, "orderservice_salesorder.updated_by_user_id")
            _validate_optional_fk(obj.po_id, orderservice_purchaseorder, "orderservice_salesorder.po_id")
            _validate_optional_fk(obj.product_id, productservices_products, "orderservice_salesorder.product_id")
        elif isinstance(obj, orderservice_salesorderorderitems):
            _validate_fk(obj.created_by_user_id, userservices_users, "orderservice_salesorderorderitems.created_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_salesorderorderitems.domain_user_id")
            _validate_fk(obj.product_id, productservices_products, "orderservice_salesorderorderitems.product_id")
            _validate_fk(obj.so_id, orderservice_salesorder, "orderservice_salesorderorderitems.so_id")
            _validate_optional_fk(obj.approved_by_user_id, userservices_users, "orderservice_salesorderorderitems.approved_by_user_id")
            _validate_optional_fk(obj.cancelled_by_user_id, userservices_users, "orderservice_salesorderorderitems.cancelled_by_user_id")
            _validate_optional_fk(obj.returned_by_user_id, userservices_users, "orderservice_salesorderorderitems.returned_by_user_id")
            _validate_optional_fk(obj.shipped_by_user_id, userservices_users, "orderservice_salesorderorderitems.shipped_by_user_id")
            _validate_optional_fk(obj.updated_by_user_id, userservices_users, "orderservice_salesorderorderitems.updated_by_user_id")
        elif isinstance(obj, orderservice_salesorderlogs):
            _validate_fk(obj.created_by_user_id, userservices_users, "orderservice_salesorderlogs.created_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_salesorderlogs.domain_user_id")
            _validate_fk(obj.so_id, orderservice_salesorder, "orderservice_salesorderlogs.so_id")
        elif isinstance(obj, orderservice_salesorderoutwardedlog):
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_salesorderoutwardedlog.domain_user_id")
            _validate_fk(obj.outwarded_by_user_id, userservices_users, "orderservice_salesorderoutwardedlog.outwarded_by_user_id")
            _validate_fk(obj.so_id, orderservice_salesorder, "orderservice_salesorderoutwardedlog.so_id")
        elif isinstance(obj, orderservice_salesorderitemoutwardedlog):
            _validate_fk(obj.domain_user_id, userservices_users, "orderservice_salesorderitemoutwardedlog.domain_user_id")
            _validate_fk(obj.so_item_id, orderservice_salesorderorderitems, "orderservice_salesorderitemoutwardedlog.so_item_id")
        elif isinstance(obj, inventoryservices_inventory):
            _validate_fk(obj.added_by_user_id, userservices_users, "inventoryservices_inventory.added_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "inventoryservices_inventory.domain_user_id")
            _validate_fk(obj.product_id, productservices_products, "inventoryservices_inventory.product_id")
            _validate_fk(obj.purchase_order_id, orderservice_purchaseorder, "inventoryservices_inventory.purchase_order_id")
            _validate_fk(obj.purchase_order_item_id, orderservice_purchaseorderitems, "inventoryservices_inventory.purchase_order_item_id")
            _validate_optional_fk(
                obj.purchase_order_item_inwarded_item_id,
                orderservice_purchaseorderiteminwardedlog,
                "inventoryservices_inventory.purchase_order_item_inwarded_item_id",
            )
            _validate_fk(obj.rack_shelf_floor_id, inventoryservices_rackandshelvesandfloor, "inventoryservices_inventory.rack_shelf_floor_id")
            _validate_fk(obj.warehouse_id, inventoryservices_warehouse, "inventoryservices_inventory.warehouse_id")
        elif isinstance(obj, inventoryservices_inventorylog):
            _validate_fk(obj.added_by_user_id, userservices_users, "inventoryservices_inventorylog.added_by_user_id")
            _validate_fk(obj.domain_user_id, userservices_users, "inventoryservices_inventorylog.domain_user_id")
            _validate_fk(obj.inventory_id, inventoryservices_inventory, "inventoryservices_inventorylog.inventory_id")
            _validate_optional_fk(obj.po_id, orderservice_purchaseorder, "inventoryservices_inventorylog.po_id")
            _validate_optional_fk(obj.so_id, orderservice_salesorder, "inventoryservices_inventorylog.so_id")
            _validate_fk(obj.rack_shelf_floor_id, inventoryservices_rackandshelvesandfloor, "inventoryservices_inventorylog.rack_shelf_floor_id")
            _validate_fk(obj.warehouse_id, inventoryservices_warehouse, "inventoryservices_inventorylog.warehouse_id")
        elif isinstance(obj, userservices_users):
            _validate_optional_fk(obj.domain_user_id, userservices_users, "userservices_users.domain_user_id")