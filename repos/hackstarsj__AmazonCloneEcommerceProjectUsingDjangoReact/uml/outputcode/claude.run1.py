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
            raise ValueError("app_label is required")
        if not self.model:
            raise ValueError("model is required")


@dataclass
class DjangoMigrations:
    id: int
    app: str
    name: str
    applied: datetime


@dataclass
class DjangoSession:
    session_key: str
    session_data: str
    expire_date: datetime

    def __post_init__(self):
        if len(self.session_key) > 40:
            raise ValueError("session_key max length is 40")


@dataclass
class DjangoAdminLog:
    id: int
    action_time: datetime
    object_repr: str
    action_flag: int
    change_message: str
    content_type_id: Optional[int] = None
    user_id: Optional[int] = None
    object_id: Optional[str] = None

    _content_type: Optional[DjangoContentType] = field(default=None, repr=False)
    _user: Optional[Any] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.object_repr) > 200:
            raise ValueError("object_repr max length is 200")
        if self.action_flag < 0:
            raise ValueError("action_flag must be unsigned smallint")

    @property
    def content_type(self) -> Optional[DjangoContentType]:
        return self._content_type

    @content_type.setter
    def content_type(self, value: Optional[DjangoContentType]):
        self._content_type = value
        if value is not None:
            self.content_type_id = value.id

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
        if value is not None:
            self.user_id = value.id


@dataclass
class AuthGroup:
    id: int
    name: str

    def __post_init__(self):
        if len(self.name) > 150:
            raise ValueError("name max length is 150")


@dataclass
class AuthPermission:
    id: int
    name: str
    codename: str
    content_type_id: int

    _content_type: Optional[DjangoContentType] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.codename) > 100:
            raise ValueError("codename max length is 100")

    @property
    def content_type(self) -> Optional[DjangoContentType]:
        return self._content_type

    @content_type.setter
    def content_type(self, value: Optional[DjangoContentType]):
        self._content_type = value
        if value is not None:
            self.content_type_id = value.id


@dataclass
class AuthGroupPermissions:
    id: int
    group_id: int
    permission_id: int

    _group: Optional[AuthGroup] = field(default=None, repr=False)
    _permission: Optional[AuthPermission] = field(default=None, repr=False)

    @property
    def group(self) -> Optional[AuthGroup]:
        return self._group

    @group.setter
    def group(self, value: Optional[AuthGroup]):
        self._group = value
        if value is not None:
            self.group_id = value.id

    @property
    def permission(self) -> Optional[AuthPermission]:
        return self._permission

    @permission.setter
    def permission(self, value: Optional[AuthPermission]):
        self._permission = value
        if value is not None:
            self.permission_id = value.id


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

    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.first_name) > 150:
            raise ValueError("first_name max length is 150")
        if len(self.last_name) > 150:
            raise ValueError("last_name max length is 150")
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
        if len(self.name) > 100:
            raise ValueError("name max length is 100")

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id


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

    _user: Optional[UserservicesUsers] = field(default=None, repr=False)

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

    @property
    def user(self) -> Optional[UserservicesUsers]:
        return self._user

    @user.setter
    def user(self, value: Optional[UserservicesUsers]):
        self._user = value
        if value is not None:
            self.user_id = value.id


@dataclass
class UserservicesActivityLog:
    id: int
    user_id: int
    activity: str = ""
    activity_type: str = ""
    activity_date: Optional[datetime] = None
    activity_ip: str = ""
    activity_device: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None

    _user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.activity_type) > 50:
            raise ValueError("activity_type max length is 50")
        if len(self.activity_ip) > 39:
            raise ValueError("activity_ip max length is 39")
        if len(self.activity_device) > 50:
            raise ValueError("activity_device max length is 50")

    @property
    def user(self) -> Optional[UserservicesUsers]:
        return self._user

    @user.setter
    def user(self, value: Optional[UserservicesUsers]):
        self._user = value
        if value is not None:
            self.user_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id


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

    _parent: Optional[UserservicesModules] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.module_name) > 50:
            raise ValueError("module_name max length is 50")

    @property
    def parent(self) -> Optional[UserservicesModules]:
        return self._parent

    @parent.setter
    def parent(self, value: Optional[UserservicesModules]):
        self._parent = value
        if value is not None:
            self.parent_id_id = value.id


@dataclass
class UserservicesUserPermissions:
    id: int
    user_id: int
    module_id_id: int
    is_view: bool = False
    is_add: bool = False
    is_edit: bool = False
    is_delete: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None

    _user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _module: Optional[UserservicesModules] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    @property
    def user(self) -> Optional[UserservicesUsers]:
        return self._user

    @user.setter
    def user(self, value: Optional[UserservicesUsers]):
        self._user = value
        if value is not None:
            self.user_id = value.id

    @property
    def module(self) -> Optional[UserservicesModules]:
        return self._module

    @module.setter
    def module(self, value: Optional[UserservicesModules]):
        self._module = value
        if value is not None:
            self.module_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id


@dataclass
class UserservicesUsersGroups:
    id: int
    users_id: int
    group_id: int

    _user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _group: Optional[AuthGroup] = field(default=None, repr=False)

    @property
    def user(self) -> Optional[UserservicesUsers]:
        return self._user

    @user.setter
    def user(self, value: Optional[UserservicesUsers]):
        self._user = value
        if value is not None:
            self.users_id = value.id

    @property
    def group(self) -> Optional[AuthGroup]:
        return self._group

    @group.setter
    def group(self, value: Optional[AuthGroup]):
        self._group = value
        if value is not None:
            self.group_id = value.id


@dataclass
class UserservicesUsersUserPermissions:
    id: int
    users_id: int
    permission_id: int

    _user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _permission: Optional[AuthPermission] = field(default=None, repr=False)

    @property
    def user(self) -> Optional[UserservicesUsers]:
        return self._user

    @user.setter
    def user(self, value: Optional[UserservicesUsers]):
        self._user = value
        if value is not None:
            self.users_id = value.id

    @property
    def permission(self) -> Optional[AuthPermission]:
        return self._permission

    @permission.setter
    def permission(self, value: Optional[AuthPermission]):
        self._permission = value
        if value is not None:
            self.permission_id = value.id


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

    _added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _parent: Optional[ProductservicesCategories] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")

    @property
    def added_by_user(self) -> Optional[UserservicesUsers]:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional[UserservicesUsers]):
        self._added_by_user = value
        if value is not None:
            self.added_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def parent(self) -> Optional[ProductservicesCategories]:
        return self._parent

    @parent.setter
    def parent(self, value: Optional[ProductservicesCategories]):
        self._parent = value
        if value is not None:
            self.parent_id_id = value.id


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

    _added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _category: Optional[ProductservicesCategories] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.sku) > 255:
            raise ValueError("sku max length is 255")

    @property
    def added_by_user(self) -> Optional[UserservicesUsers]:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional[UserservicesUsers]):
        self._added_by_user = value
        if value is not None:
            self.added_by_user_id_id = value.id

    @property
    def category(self) -> Optional[ProductservicesCategories]:
        return self._category

    @category.setter
    def category(self, value: Optional[ProductservicesCategories]):
        self._category = value
        if value is not None:
            self.category_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id


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

    _answer_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _question_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _product: Optional[ProductservicesProducts] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.status) > 255:
            raise ValueError("status max length is 255")

    @property
    def answer_user(self) -> Optional[UserservicesUsers]:
        return self._answer_user

    @answer_user.setter
    def answer_user(self, value: Optional[UserservicesUsers]):
        self._answer_user = value
        if value is not None:
            self.answer_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def question_user(self) -> Optional[UserservicesUsers]:
        return self._question_user

    @question_user.setter
    def question_user(self, value: Optional[UserservicesUsers]):
        self._question_user = value
        if value is not None:
            self.question_user_id_id = value.id

    @property
    def product(self) -> Optional[ProductservicesProducts]:
        return self._product

    @product.setter
    def product(self, value: Optional[ProductservicesProducts]):
        self._product = value
        if value is not None:
            self.product_id_id = value.id


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

    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _review_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _product: Optional[ProductservicesProducts] = field(default=None, repr=False)

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def review_user(self) -> Optional[UserservicesUsers]:
        return self._review_user

    @review_user.setter
    def review_user(self, value: Optional[UserservicesUsers]):
        self._review_user = value
        if value is not None:
            self.review_user_id_id = value.id

    @property
    def product(self) -> Optional[ProductservicesProducts]:
        return self._product

    @product.setter
    def product(self, value: Optional[ProductservicesProducts]):
        self._product = value
        if value is not None:
            self.product_id_id = value.id


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

    _added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _warehouse_manager: Optional[UserservicesUsers] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.email) > 254:
            raise ValueError("email max length is 254")

    @property
    def added_by_user(self) -> Optional[UserservicesUsers]:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional[UserservicesUsers]):
        self._added_by_user = value
        if value is not None:
            self.added_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def warehouse_manager(self) -> Optional[UserservicesUsers]:
        return self._warehouse_manager

    @warehouse_manager.setter
    def warehouse_manager(self, value: Optional[UserservicesUsers]):
        self._warehouse_manager = value
        if value is not None:
            self.warehouse_manager_id = value.id


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

    _added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.name) > 255:
            raise ValueError("name max length is 255")
        if len(self.rack) > 255:
            raise ValueError("rack max length is 255")
        if len(self.shelf) > 255:
            raise ValueError("shelf max length is 255")
        if len(self.floor) > 255:
            raise ValueError("floor max length is 255")

    @property
    def added_by_user(self) -> Optional[UserservicesUsers]:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional[UserservicesUsers]):
        self._added_by_user = value
        if value is not None:
            self.added_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def warehouse(self) -> Optional[InventoryservicesWarehouse]:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional[InventoryservicesWarehouse]):
        self._warehouse = value
        if value is not None:
            self.warehouse_id_id = value.id


# ============================================================
#  ORDER SERVICE
# ============================================================

@dataclass
class OrderservicePurchaseOrder:
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

    _approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _supplier: Optional[UserservicesUsers] = field(default=None, repr=False)
    _updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    @property
    def approved_by_user(self) -> Optional[UserservicesUsers]:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional[UserservicesUsers]):
        self._approved_by_user = value
        if value is not None:
            self.approved_by_user_id_id = value.id

    @property
    def cancelled_by_user(self) -> Optional[UserservicesUsers]:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional[UserservicesUsers]):
        self._cancelled_by_user = value
        if value is not None:
            self.cancelled_by_user_id_id = value.id

    @property
    def created_by_user(self) -> Optional[UserservicesUsers]:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional[UserservicesUsers]):
        self._created_by_user = value
        if value is not None:
            self.created_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def last_updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._last_updated_by_user

    @last_updated_by_user.setter
    def last_updated_by_user(self, value: Optional[UserservicesUsers]):
        self._last_updated_by_user = value
        if value is not None:
            self.last_updated_by_user_id_id = value.id

    @property
    def received_by_user(self) -> Optional[UserservicesUsers]:
        return self._received_by_user

    @received_by_user.setter
    def received_by_user(self, value: Optional[UserservicesUsers]):
        self._received_by_user = value
        if value is not None:
            self.received_by_user_id_id = value.id

    @property
    def returned_by_user(self) -> Optional[UserservicesUsers]:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional[UserservicesUsers]):
        self._returned_by_user = value
        if value is not None:
            self.returned_by_user_id_id = value.id

    @property
    def supplier(self) -> Optional[UserservicesUsers]:
        return self._supplier

    @supplier.setter
    def supplier(self, value: Optional[UserservicesUsers]):
        self._supplier = value
        if value is not None:
            self.supplier_id_id = value.id

    @property
    def updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional[UserservicesUsers]):
        self._updated_by_user = value
        if value is not None:
            self.updated_by_user_id_id = value.id

    @property
    def warehouse(self) -> Optional[InventoryservicesWarehouse]:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional[InventoryservicesWarehouse]):
        self._warehouse = value
        if value is not None:
            self.warehouse_id_id = value.id


@dataclass
class OrderservicePurchaseOrderItems:
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

    _approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    _product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    _updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    @property
    def approved_by_user(self) -> Optional[UserservicesUsers]:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional[UserservicesUsers]):
        self._approved_by_user = value
        if value is not None:
            self.approved_by_user_id_id = value.id

    @property
    def cancelled_by_user(self) -> Optional[UserservicesUsers]:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional[UserservicesUsers]):
        self._cancelled_by_user = value
        if value is not None:
            self.cancelled_by_user_id_id = value.id

    @property
    def created_by_user(self) -> Optional[UserservicesUsers]:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional[UserservicesUsers]):
        self._created_by_user = value
        if value is not None:
            self.created_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def last_updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._last_updated_by_user

    @last_updated_by_user.setter
    def last_updated_by_user(self, value: Optional[UserservicesUsers]):
        self._last_updated_by_user = value
        if value is not None:
            self.last_updated_by_user_id_id = value.id

    @property
    def received_by_user(self) -> Optional[UserservicesUsers]:
        return self._received_by_user

    @received_by_user.setter
    def received_by_user(self, value: Optional[UserservicesUsers]):
        self._received_by_user = value
        if value is not None:
            self.received_by_user_id_id = value.id

    @property
    def returned_by_user(self) -> Optional[UserservicesUsers]:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional[UserservicesUsers]):
        self._returned_by_user = value
        if value is not None:
            self.returned_by_user_id_id = value.id

    @property
    def po(self) -> Optional[OrderservicePurchaseOrder]:
        return self._po

    @po.setter
    def po(self, value: Optional[OrderservicePurchaseOrder]):
        self._po = value
        if value is not None:
            self.po_id_id = value.id

    @property
    def product(self) -> Optional[ProductservicesProducts]:
        return self._product

    @product.setter
    def product(self, value: Optional[ProductservicesProducts]):
        self._product = value
        if value is not None:
            self.product_id_id = value.id

    @property
    def updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional[UserservicesUsers]):
        self._updated_by_user = value
        if value is not None:
            self.updated_by_user_id_id = value.id


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

    _created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)

    @property
    def created_by_user(self) -> Optional[UserservicesUsers]:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional[UserservicesUsers]):
        self._created_by_user = value
        if value is not None:
            self.created_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def po(self) -> Optional[OrderservicePurchaseOrder]:
        return self._po

    @po.setter
    def po(self, value: Optional[OrderservicePurchaseOrder]):
        self._po = value
        if value is not None:
            self.po_id_id = value.id


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

    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _inwarded_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.invoice_number) > 255:
            raise ValueError("invoice_number max length is 255")

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def inwarded_by_user(self) -> Optional[UserservicesUsers]:
        return self._inwarded_by_user

    @inwarded_by_user.setter
    def inwarded_by_user(self, value: Optional[UserservicesUsers]):
        self._inwarded_by_user = value
        if value is not None:
            self.inwarded_by_user_id_id = value.id

    @property
    def po(self) -> Optional[OrderservicePurchaseOrder]:
        return self._po

    @po.setter
    def po(self, value: Optional[OrderservicePurchaseOrder]):
        self._po = value
        if value is not None:
            self.po_id_id = value.id


@dataclass
class OrderservicePurchaseOrderItemInwardedLog:
    id: int
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
    domain_user_id_id: Optional[int] = None
    po_item_id_id: Optional[int] = None

    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _po_item: Optional[OrderservicePurchaseOrderItems] = field(default=None, repr=False)

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def po_item(self) -> Optional[OrderservicePurchaseOrderItems]:
        return self._po_item

    @po_item.setter
    def po_item(self, value: Optional[OrderservicePurchaseOrderItems]):
        self._po_item = value
        if value is not None:
            self.po_item_id_id = value.id


@dataclass
class OrderserviceSalesOrder:
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

    _approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _customer: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _last_updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _received_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    _product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    _updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    @property
    def approved_by_user(self) -> Optional[UserservicesUsers]:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional[UserservicesUsers]):
        self._approved_by_user = value
        if value is not None:
            self.approved_by_user_id_id = value.id

    @property
    def cancelled_by_user(self) -> Optional[UserservicesUsers]:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional[UserservicesUsers]):
        self._cancelled_by_user = value
        if value is not None:
            self.cancelled_by_user_id_id = value.id

    @property
    def created_by_user(self) -> Optional[UserservicesUsers]:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional[UserservicesUsers]):
        self._created_by_user = value
        if value is not None:
            self.created_by_user_id_id = value.id

    @property
    def customer(self) -> Optional[UserservicesUsers]:
        return self._customer

    @customer.setter
    def customer(self, value: Optional[UserservicesUsers]):
        self._customer = value
        if value is not None:
            self.customer_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def last_updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._last_updated_by_user

    @last_updated_by_user.setter
    def last_updated_by_user(self, value: Optional[UserservicesUsers]):
        self._last_updated_by_user = value
        if value is not None:
            self.last_updated_by_user_id_id = value.id

    @property
    def received_by_user(self) -> Optional[UserservicesUsers]:
        return self._received_by_user

    @received_by_user.setter
    def received_by_user(self, value: Optional[UserservicesUsers]):
        self._received_by_user = value
        if value is not None:
            self.received_by_user_id_id = value.id

    @property
    def returned_by_user(self) -> Optional[UserservicesUsers]:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional[UserservicesUsers]):
        self._returned_by_user = value
        if value is not None:
            self.returned_by_user_id_id = value.id

    @property
    def po(self) -> Optional[OrderservicePurchaseOrder]:
        return self._po

    @po.setter
    def po(self, value: Optional[OrderservicePurchaseOrder]):
        self._po = value
        if value is not None:
            self.po_id_id = value.id

    @property
    def product(self) -> Optional[ProductservicesProducts]:
        return self._product

    @product.setter
    def product(self, value: Optional[ProductservicesProducts]):
        self._product = value
        if value is not None:
            self.product_id_id = value.id

    @property
    def updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional[UserservicesUsers]):
        self._updated_by_user = value
        if value is not None:
            self.updated_by_user_id_id = value.id


@dataclass
class OrderserviceSalesOrderOrderItems:
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

    _approved_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _cancelled_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    _returned_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _shipped_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)
    _updated_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)

    @property
    def approved_by_user(self) -> Optional[UserservicesUsers]:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional[UserservicesUsers]):
        self._approved_by_user = value
        if value is not None:
            self.approved_by_user_id_id = value.id

    @property
    def cancelled_by_user(self) -> Optional[UserservicesUsers]:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional[UserservicesUsers]):
        self._cancelled_by_user = value
        if value is not None:
            self.cancelled_by_user_id_id = value.id

    @property
    def created_by_user(self) -> Optional[UserservicesUsers]:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional[UserservicesUsers]):
        self._created_by_user = value
        if value is not None:
            self.created_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def product(self) -> Optional[ProductservicesProducts]:
        return self._product

    @product.setter
    def product(self, value: Optional[ProductservicesProducts]):
        self._product = value
        if value is not None:
            self.product_id_id = value.id

    @property
    def returned_by_user(self) -> Optional[UserservicesUsers]:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional[UserservicesUsers]):
        self._returned_by_user = value
        if value is not None:
            self.returned_by_user_id_id = value.id

    @property
    def shipped_by_user(self) -> Optional[UserservicesUsers]:
        return self._shipped_by_user

    @shipped_by_user.setter
    def shipped_by_user(self, value: Optional[UserservicesUsers]):
        self._shipped_by_user = value
        if value is not None:
            self.shipped_by_user_id_id = value.id

    @property
    def so(self) -> Optional[OrderserviceSalesOrder]:
        return self._so

    @so.setter
    def so(self, value: Optional[OrderserviceSalesOrder]):
        self._so = value
        if value is not None:
            self.so_id_id = value.id

    @property
    def updated_by_user(self) -> Optional[UserservicesUsers]:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional[UserservicesUsers]):
        self._updated_by_user = value
        if value is not None:
            self.updated_by_user_id_id = value.id


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

    _created_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)

    @property
    def created_by_user(self) -> Optional[UserservicesUsers]:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional[UserservicesUsers]):
        self._created_by_user = value
        if value is not None:
            self.created_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def so(self) -> Optional[OrderserviceSalesOrder]:
        return self._so

    @so.setter
    def so(self, value: Optional[OrderserviceSalesOrder]):
        self._so = value
        if value is not None:
            self.so_id_id = value.id


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

    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _outwarded_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)

    def __post_init__(self):
        if len(self.invoice_number) > 255:
            raise ValueError("invoice_number max length is 255")

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def outwarded_by_user(self) -> Optional[UserservicesUsers]:
        return self._outwarded_by_user

    @outwarded_by_user.setter
    def outwarded_by_user(self, value: Optional[UserservicesUsers]):
        self._outwarded_by_user = value
        if value is not None:
            self.outwarded_by_user_id_id = value.id

    @property
    def so(self) -> Optional[OrderserviceSalesOrder]:
        return self._so

    @so.setter
    def so(self, value: Optional[OrderserviceSalesOrder]):
        self._so = value
        if value is not None:
            self.so_id_id = value.id


@dataclass
class OrderserviceSalesOrderItemOutwardedLog:
    id: int
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
    domain_user_id_id: Optional[int] = None
    so_item_id_id: Optional[int] = None

    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _so_item: Optional[OrderserviceSalesOrderOrderItems] = field(default=None, repr=False)

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def so_item(self) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._so_item

    @so_item.setter
    def so_item(self, value: Optional[OrderserviceSalesOrderOrderItems]):
        self._so_item = value
        if value is not None:
            self.so_item_id_id = value.id


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
    buy_price: Decimal = Decimal("0.00")
    sell_price: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
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

    _added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _product: Optional[ProductservicesProducts] = field(default=None, repr=False)
    _purchase_order: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    _purchase_order_item: Optional[OrderservicePurchaseOrderItems] = field(default=None, repr=False)
    _purchase_order_item_inwarded_item: Optional[OrderservicePurchaseOrderItemInwardedLog] = field(default=None, repr=False)
    _rack_shelf_floor: Optional[InventoryservicesRackAndShelvesAndFloor] = field(default=None, repr=False)
    _warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    @property
    def added_by_user(self) -> Optional[UserservicesUsers]:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional[UserservicesUsers]):
        self._added_by_user = value
        if value is not None:
            self.added_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def product(self) -> Optional[ProductservicesProducts]:
        return self._product

    @product.setter
    def product(self, value: Optional[ProductservicesProducts]):
        self._product = value
        if value is not None:
            self.product_id_id = value.id

    @property
    def purchase_order(self) -> Optional[OrderservicePurchaseOrder]:
        return self._purchase_order

    @purchase_order.setter
    def purchase_order(self, value: Optional[OrderservicePurchaseOrder]):
        self._purchase_order = value
        if value is not None:
            self.purchase_order_id_id = value.id

    @property
    def purchase_order_item(self) -> Optional[OrderservicePurchaseOrderItems]:
        return self._purchase_order_item

    @purchase_order_item.setter
    def purchase_order_item(self, value: Optional[OrderservicePurchaseOrderItems]):
        self._purchase_order_item = value
        if value is not None:
            self.purchase_order_item_id_id = value.id

    @property
    def purchase_order_item_inwarded_item(self) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._purchase_order_item_inwarded_item

    @purchase_order_item_inwarded_item.setter
    def purchase_order_item_inwarded_item(self, value: Optional[OrderservicePurchaseOrderItemInwardedLog]):
        self._purchase_order_item_inwarded_item = value
        if value is not None:
            self.purchase_order_item_inwarded_item_id_id = value.id

    @property
    def rack_shelf_floor(self) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._rack_shelf_floor

    @rack_shelf_floor.setter
    def rack_shelf_floor(self, value: Optional[InventoryservicesRackAndShelvesAndFloor]):
        self._rack_shelf_floor = value
        if value is not None:
            self.rack_shelf_floor_id_id = value.id

    @property
    def warehouse(self) -> Optional[InventoryservicesWarehouse]:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional[InventoryservicesWarehouse]):
        self._warehouse = value
        if value is not None:
            self.warehouse_id_id = value.id


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

    _added_by_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _domain_user: Optional[UserservicesUsers] = field(default=None, repr=False)
    _inventory: Optional[InventoryservicesInventory] = field(default=None, repr=False)
    _po: Optional[OrderservicePurchaseOrder] = field(default=None, repr=False)
    _so: Optional[OrderserviceSalesOrder] = field(default=None, repr=False)
    _rack_shelf_floor: Optional[InventoryservicesRackAndShelvesAndFloor] = field(default=None, repr=False)
    _warehouse: Optional[InventoryservicesWarehouse] = field(default=None, repr=False)

    @property
    def added_by_user(self) -> Optional[UserservicesUsers]:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional[UserservicesUsers]):
        self._added_by_user = value
        if value is not None:
            self.added_by_user_id_id = value.id

    @property
    def domain_user(self) -> Optional[UserservicesUsers]:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional[UserservicesUsers]):
        self._domain_user = value
        if value is not None:
            self.domain_user_id_id = value.id

    @property
    def inventory(self) -> Optional[InventoryservicesInventory]:
        return self._inventory

    @inventory.setter
    def inventory(self, value: Optional[InventoryservicesInventory]):
        self._inventory = value
        if value is not None:
            self.inventory_id_id = value.id

    @property
    def po(self) -> Optional[OrderservicePurchaseOrder]:
        return self._po

    @po.setter
    def po(self, value: Optional[OrderservicePurchaseOrder]):
        self._po = value
        if value is not None:
            self.po_id_id = value.id

    @property
    def so(self) -> Optional[OrderserviceSalesOrder]:
        return self._so

    @so.setter
    def so(self, value: Optional[OrderserviceSalesOrder]):
        self._so = value
        if value is not None:
            self.so_id_id = value.id

    @property
    def rack_shelf_floor(self) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._rack_shelf_floor

    @rack_shelf_floor.setter
    def rack_shelf_floor(self, value: Optional[InventoryservicesRackAndShelvesAndFloor]):
        self._rack_shelf_floor = value
        if value is not None:
            self.rack_shelf_floor_id_id = value.id

    @property
    def warehouse(self) -> Optional[InventoryservicesWarehouse]:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional[InventoryservicesWarehouse]):
        self._warehouse = value
        if value is not None:
            self.warehouse_id_id = value.id


# ============================================================
#  REGISTRY / REPOSITORY CLASSES
# ============================================================

class EcommerceRepository:
    def __init__(self):
        self._django_content_types: Dict[int, DjangoContentType] = {}
        self._django_migrations: Dict[int, DjangoMigrations] = {}
        self._django_sessions: Dict[str, DjangoSession] = {}
        self._django_admin_logs: Dict[int, DjangoAdminLog] = {}
        self._auth_groups: Dict[int, AuthGroup] = {}
        self._auth_permissions: Dict[int, AuthPermission] = {}
        self._auth_group_permissions: Dict[int, AuthGroupPermissions] = {}
        self._users: Dict[int, UserservicesUsers] = {}
        self._user_shipping_addresses: Dict[int, UserservicesUserShippingAddress] = {}
        self._activity_logs: Dict[int, UserservicesActivityLog] = {}
        self._modules: Dict[int, UserservicesModules] = {}
        self._user_permissions: Dict[int, UserservicesUserPermissions] = {}
        self._users_groups: Dict[int, UserservicesUsersGroups] = {}
        self._users_user_permissions: Dict[int, UserservicesUsersUserPermissions] = {}
        self._categories: Dict[int, ProductservicesCategories] = {}
        self._products: Dict[int, ProductservicesProducts] = {}
        self._product_questions: Dict[int, ProductservicesProductQuestions] = {}
        self._product_reviews: Dict[int, ProductservicesProductReviews] = {}
        self._warehouses: Dict[int, InventoryservicesWarehouse] = {}
        self._rack_shelves_floors: Dict[int, InventoryservicesRackAndShelvesAndFloor] = {}
        self._inventories: Dict[int, InventoryservicesInventory] = {}
        self._inventory_logs: Dict[int, InventoryservicesInventoryLog] = {}
        self._purchase_orders: Dict[int, OrderservicePurchaseOrder] = {}
        self._purchase_order_items: Dict[int, OrderservicePurchaseOrderItems] = {}
        self._purchase_order_logs: Dict[int, OrderservicePurchaseOrderLogs] = {}
        self._purchase_order_inwarded_logs: Dict[int, OrderservicePurchaseOrderInwardedLog] = {}
        self._purchase_order_item_inwarded_logs: Dict[int, OrderservicePurchaseOrderItemInwardedLog] = {}
        self._sales_orders: Dict[int, OrderserviceSalesOrder] = {}
        self._sales_order_items: Dict[int, OrderserviceSalesOrderOrderItems] = {}
        self._sales_order_logs: Dict[int, OrderserviceSalesOrderLogs] = {}
        self._sales_order_outwarded_logs: Dict[int, OrderserviceSalesOrderOutwardedLog] = {}
        self._sales_order_item_outwarded_logs: Dict[int, OrderserviceSalesOrderItemOutwardedLog] = {}

    # Django Content Type
    def add_django_content_type(self, obj: DjangoContentType) -> DjangoContentType:
        self._django_content_types[obj.id] = obj
        return obj

    def get_django_content_type(self, id: int) -> Optional[DjangoContentType]:
        return self._django_content_types.get(id)

    def list_django_content_types(self) -> List[DjangoContentType]:
        return list(self._django_content_types.values())

    # Django Migrations
    def add_django_migration(self, obj: DjangoMigrations) -> DjangoMigrations:
        self._django_migrations[obj.id] = obj
        return obj

    def get_django_migration(self, id: int) -> Optional[DjangoMigrations]:
        return self._django_migrations.get(id)

    def list_django_migrations(self) -> List[DjangoMigrations]:
        return list(self._django_migrations.values())

    # Django Session
    def add_django_session(self, obj: DjangoSession) -> DjangoSession:
        self._django_sessions[obj.session_key] = obj
        return obj

    def get_django_session(self, session_key: str) -> Optional[DjangoSession]:
        return self._django_sessions.get(session_key)

    def list_django_sessions(self) -> List[DjangoSession]:
        return list(self._django_sessions.values())

    # Django Admin Log
    def add_django_admin_log(self, obj: DjangoAdminLog) -> DjangoAdminLog:
        self._django_admin_logs[obj.id] = obj
        return obj

    def get_django_admin_log(self, id: int) -> Optional[DjangoAdminLog]:
        return self._django_admin_logs.get(id)

    def list_django_admin_logs(self) -> List[DjangoAdminLog]:
        return list(self._django_admin_logs.values())

    # Auth Group
    def add_auth_group(self, obj: AuthGroup) -> AuthGroup:
        self._auth_groups[obj.id] = obj
        return obj

    def get_auth_group(self, id: int) -> Optional[AuthGroup]:
        return self._auth_groups.get(id)

    def list_auth_groups(self) -> List[AuthGroup]:
        return list(self._auth_groups.values())

    # Auth Permission
    def add_auth_permission(self, obj: AuthPermission) -> AuthPermission:
        self._auth_permissions[obj.id] = obj
        return obj

    def get_auth_permission(self, id: int) -> Optional[AuthPermission]:
        return self._auth_permissions.get(id)

    def list_auth_permissions(self) -> List[AuthPermission]:
        return list(self._auth_permissions.values())

    # Auth Group Permissions
    def add_auth_group_permission(self, obj: AuthGroupPermissions) -> AuthGroupPermissions:
        self._auth_group_permissions[obj.id] = obj
        return obj

    def get_auth_group_permission(self, id: int) -> Optional[AuthGroupPermissions]:
        return self._auth_group_permissions.get(id)

    def list_auth_group_permissions(self) -> List[AuthGroupPermissions]:
        return list(self._auth_group_permissions.values())

    # Users
    def add_user(self, obj: UserservicesUsers) -> UserservicesUsers:
        self._users[obj.id] = obj
        return obj

    def get_user(self, id: int) -> Optional[UserservicesUsers]:
        return self._users.get(id)

    def list_users(self) -> List[UserservicesUsers]:
        return list(self._users.values())

    # User Shipping Address
    def add_user_shipping_address(self, obj: UserservicesUserShippingAddress) -> UserservicesUserShippingAddress:
        self._user_shipping_addresses[obj.id] = obj
        return obj

    def get_user_shipping_address(self, id: int) -> Optional[UserservicesUserShippingAddress]:
        return self._user_shipping_addresses.get(id)

    def list_user_shipping_addresses(self) -> List[UserservicesUserShippingAddress]:
        return list(self._user_shipping_addresses.values())

    def get_user_shipping_addresses_by_user(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [a for a in self._user_shipping_addresses.values() if a.user_id == user_id]

    # Activity Log
    def add_activity_log(self, obj: UserservicesActivityLog) -> UserservicesActivityLog:
        self._activity_logs[obj.id] = obj
        return obj

    def get_activity_log(self, id: int) -> Optional[UserservicesActivityLog]:
        return self._activity_logs.get(id)

    def list_activity_logs(self) -> List[UserservicesActivityLog]:
        return list(self._activity_logs.values())

    def get_activity_logs_by_user(self, user_id: int) -> List[UserservicesActivityLog]:
        return [a for a in self._activity_logs.values() if a.user_id == user_id]

    # Modules
    def add_module(self, obj: UserservicesModules) -> UserservicesModules:
        self._modules[obj.id] = obj
        return obj

    def get_module(self, id: int) -> Optional[UserservicesModules]:
        return self._modules.get(id)

    def list_modules(self) -> List[UserservicesModules]:
        return list(self._modules.values())

    # User Permissions
    def add_user_permission(self, obj: UserservicesUserPermissions) -> UserservicesUserPermissions:
        self._user_permissions[obj.id] = obj
        return obj

    def get_user_permission(self, id: int) -> Optional[UserservicesUserPermissions]:
        return self._user_permissions.get(id)

    def list_user_permissions(self) -> List[UserservicesUserPermissions]:
        return list(self._user_permissions.values())

    def get_user_permissions_by_user(self, user_id: int) -> List[UserservicesUserPermissions]:
        return [p for p in self._user_permissions.values() if p.user_id == user_id]

    # Users Groups
    def add_users_group(self, obj: UserservicesUsersGroups) -> UserservicesUsersGroups:
        self._users_groups[obj.id] = obj
        return obj

    def get_users_group(self, id: int) -> Optional[UserservicesUsersGroups]:
        return self._users_groups.get(id)

    def list_users_groups(self) -> List[UserservicesUsersGroups]:
        return list(self._users_groups.values())

    # Users User Permissions
    def add_users_user_permission(self, obj: UserservicesUsersUserPermissions) -> UserservicesUsersUserPermissions:
        self._users_user_permissions[obj.id] = obj
        return obj

    def get_users_user_permission(self, id: int) -> Optional[UserservicesUsersUserPermissions]:
        return self._users_user_permissions.get(id)

    def list_users_user_permissions(self) -> List[UserservicesUsersUserPermissions]:
        return list(self._users_user_permissions.values())

    # Categories
    def add_category(self, obj: ProductservicesCategories) -> ProductservicesCategories:
        self._categories[obj.id] = obj
        return obj

    def get_category(self, id: int) -> Optional[ProductservicesCategories]:
        return self._categories.get(id)

    def list_categories(self) -> List[ProductservicesCategories]:
        return list(self._categories.values())

    def get_subcategories(self, parent_id: int) -> List[ProductservicesCategories]:
        return [c for c in self._categories.values() if c.parent_id_id == parent_id]

    # Products
    def add_product(self, obj: ProductservicesProducts) -> ProductservicesProducts:
        self._products[obj.id] = obj
        return obj

    def get_product(self, id: int) -> Optional[ProductservicesProducts]:
        return self._products.get(id)

    def list_products(self) -> List[ProductservicesProducts]:
        return list(self._products.values())

    def get_products_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [p for p in self._products.values() if p.category_id_id == category_id]

    # Product Questions
    def add_product_question(self, obj: ProductservicesProductQuestions) -> ProductservicesProductQuestions:
        self._product_questions[obj.id] = obj
        return obj

    def get_product_question(self, id: int) -> Optional[ProductservicesProductQuestions]:
        return self._product_questions.get(id)

    def list_product_questions(self) -> List[ProductservicesProductQuestions]:
        return list(self._product_questions.values())

    def get_product_questions_by_product(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [q for q in self._product_questions.values() if q.product_id_id == product_id]

    # Product Reviews
    def add_product_review(self, obj: ProductservicesProductReviews) -> ProductservicesProductReviews:
        self._product_reviews[obj.id] = obj
        return obj

    def get_product_review(self, id: int) -> Optional[ProductservicesProductReviews]:
        return self._product_reviews.get(id)

    def list_product_reviews(self) -> List[ProductservicesProductReviews]:
        return list(self._product_reviews.values())

    def get_product_reviews_by_product(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [r for r in self._product_reviews.values() if r.product_id_id == product_id]

    # Warehouses
    def add_warehouse(self, obj: InventoryservicesWarehouse) -> InventoryservicesWarehouse:
        self._warehouses[obj.id] = obj
        return obj

    def get_warehouse(self, id: int) -> Optional[InventoryservicesWarehouse]:
        return self._warehouses.get(id)

    def list_warehouses(self) -> List[InventoryservicesWarehouse]:
        return list(self._warehouses.values())

    # Rack Shelves Floors
    def add_rack_shelf_floor(self, obj: InventoryservicesRackAndShelvesAndFloor) -> InventoryservicesRackAndShelvesAndFloor:
        self._rack_shelves_floors[obj.id] = obj
        return obj

    def get_rack_shelf_floor(self, id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._rack_shelves_floors.get(id)

    def list_rack_shelves_floors(self) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return list(self._rack_shelves_floors.values())

    def get_rack_shelves_floors_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return [r for r in self._rack_shelves_floors.values() if r.warehouse_id_id == warehouse_id]

    # Inventories
    def add_inventory(self, obj: InventoryservicesInventory) -> InventoryservicesInventory:
        self._inventories[obj.id] = obj
        return obj

    def get_inventory(self, id: int) -> Optional[InventoryservicesInventory]:
        return self._inventories.get(id)

    def list_inventories(self) -> List[InventoryservicesInventory]:
        return list(self._inventories.values())

    def get_inventories_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._inventories.values() if i.product_id_id == product_id]

    def get_inventories_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._inventories.values() if i.warehouse_id_id == warehouse_id]

    # Inventory Logs
    def add_inventory_log(self, obj: InventoryservicesInventoryLog) -> InventoryservicesInventoryLog:
        self._inventory_logs[obj.id] = obj
        return obj

    def get_inventory_log(self, id: int) -> Optional[InventoryservicesInventoryLog]:
        return self._inventory_logs.get(id)

    def list_inventory_logs(self) -> List[InventoryservicesInventoryLog]:
        return list(self._inventory_logs.values())

    def get_inventory_logs_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [l for l in self._inventory_logs.values() if l.inventory_id_id == inventory_id]

    # Purchase Orders
    def add_purchase_order(self, obj: OrderservicePurchaseOrder) -> OrderservicePurchaseOrder:
        self._purchase_orders[obj.id] = obj
        return obj

    def get_purchase_order(self, id: int) -> Optional[OrderservicePurchaseOrder]:
        return self._purchase_orders.get(id)

    def list_purchase_orders(self) -> List[OrderservicePurchaseOrder]:
        return list(self._purchase_orders.values())

    def get_purchase_orders_by_supplier(self, supplier_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._purchase_orders.values() if po.supplier_id_id == supplier_id]

    def get_purchase_orders_by_warehouse(self, warehouse_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._purchase_orders.values() if po.warehouse_id_id == warehouse_id]

    # Purchase Order Items
    def add_purchase_order_item(self, obj: OrderservicePurchaseOrderItems) -> OrderservicePurchaseOrderItems:
        self._purchase_order_items[obj.id] = obj
        return obj

    def get_purchase_order_item(self, id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self._purchase_order_items.get(id)

    def list_purchase_order_items(self) -> List[OrderservicePurchaseOrderItems]:
        return list(self._purchase_order_items.values())

    def get_purchase_order_items_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [i for i in self._purchase_order_items.values() if i.po_id_id == po_id]

    # Purchase Order Logs
    def add_purchase_order_log(self, obj: OrderservicePurchaseOrderLogs) -> OrderservicePurchaseOrderLogs:
        self._purchase_order_logs[obj.id] = obj
        return obj

    def get_purchase_order_log(self, id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self._purchase_order_logs.get(id)

    def list_purchase_order_logs(self) -> List[OrderservicePurchaseOrderLogs]:
        return list(self._purchase_order_logs.values())

    def get_purchase_order_logs_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return [l for l in self._purchase_order_logs.values() if l.po_id_id == po_id]

    # Purchase Order Inwarded Logs
    def add_purchase_order_inwarded_log(self, obj: OrderservicePurchaseOrderInwardedLog) -> OrderservicePurchaseOrderInwardedLog:
        self._purchase_order_inwarded_logs[obj.id] = obj
        return obj

    def get_purchase_order_inwarded_log(self, id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self._purchase_order_inwarded_logs.get(id)

    def list_purchase_order_inwarded_logs(self) -> List[OrderservicePurchaseOrderInwardedLog]:
        return list(self._purchase_order_inwarded_logs.values())

    def get_purchase_order_inwarded_logs_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderInwardedLog]:
        return [l for l in self._purchase_order_inwarded_logs.values() if l.po_id_id == po_id]

    # Purchase Order Item Inwarded Logs
    def add_purchase_order_item_inwarded_log(self, obj: OrderservicePurchaseOrderItemInwardedLog) -> OrderservicePurchaseOrderItemInwardedLog:
        self._purchase_order_item_inwarded_logs[obj.id] = obj
        return obj

    def get_purchase_order_item_inwarded_log(self, id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._purchase_order_item_inwarded_logs.get(id)

    def list_purchase_order_item_inwarded_logs(self) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return list(self._purchase_order_item_inwarded_logs.values())

    def get_purchase_order_item_inwarded_logs_by_po_item(self, po_item_id: int) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return [l for l in self._purchase_order_item_inwarded_logs.values() if l.po_item_id_id == po_item_id]

    # Sales Orders
    def add_sales_order(self, obj: OrderserviceSalesOrder) -> OrderserviceSalesOrder:
        self._sales_orders[obj.id] = obj
        return obj

    def get_sales_order(self, id: int) -> Optional[OrderserviceSalesOrder]:
        return self._sales_orders.get(id)

    def list_sales_orders(self) -> List[OrderserviceSalesOrder]:
        return list(self._sales_orders.values())

    def get_sales_orders_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return [so for so in self._sales_orders.values() if so.customer_id_id == customer_id]

    # Sales Order Items
    def add_sales_order_item(self, obj: OrderserviceSalesOrderOrderItems) -> OrderserviceSalesOrderOrderItems:
        self._sales_order_items[obj.id] = obj
        return obj

    def get_sales_order_item(self, id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._sales_order_items.get(id)

    def list_sales_order_items(self) -> List[OrderserviceSalesOrderOrderItems]:
        return list(self._sales_order_items.values())

    def get_sales_order_items_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [i for i in self._sales_order_items.values() if i.so_id_id == so_id]

    # Sales Order Logs
    def add_sales_order_log(self, obj: OrderserviceSalesOrderLogs) -> OrderserviceSalesOrderLogs:
        self._sales_order_logs[obj.id] = obj
        return obj

    def get_sales_order_log(self, id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self._sales_order_logs.get(id)

    def list_sales_order_logs(self) -> List[OrderserviceSalesOrderLogs]:
        return list(self._sales_order_logs.values())

    def get_sales_order_logs_by_so(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return [l for l in self._sales_order_logs.values() if l.so_id_id == so_id]

    # Sales Order Outwarded Logs
    def add_sales_order_outwarded_log(self, obj: OrderserviceSalesOrderOutwardedLog) -> OrderserviceSalesOrderOutwardedLog:
        self._sales_order_outwarded_logs[obj.id] = obj
        return obj

    def get_sales_order_outwarded_log(self, id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self._sales_order_outwarded_logs.get(id)

    def list_sales_order_outwarded_logs(self) -> List[OrderserviceSalesOrderOutwardedLog]:
        return list(self._sales_order_outwarded_logs.values())

    def get_sales_order_outwarded_logs_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOutwardedLog]:
        return [l for l in self._sales_order_outwarded_logs.values() if l.so_id_id == so_id]

    # Sales Order Item Outwarded Logs
    def add_sales_order_item_outwarded_log(self, obj: OrderserviceSalesOrderItemOutwardedLog) -> OrderserviceSalesOrderItemOutwardedLog:
        self._sales_order_item_outwarded_logs[obj.id] = obj
        return obj

    def get_sales_order_item_outwarded_log(self, id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self._sales_order_item_outwarded_logs.get(id)

    def list_sales_order_item_outwarded_logs(self) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return list(self._sales_order_item_outwarded_logs.values())

    def get_sales_order_item_outwarded_logs_by_so_item(self, so_item_id: int) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return [l for l in self._sales_order_item_outwarded_logs.values() if l.so_item_id_id == so_item_id]