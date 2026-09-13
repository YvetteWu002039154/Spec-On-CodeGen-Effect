from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


# ============================================================
#  DJANGO FRAMEWORK / AUTH
# ============================================================

class DjangoContentType:
    def __init__(
        self,
        id: int,
        app_label: str,
        model: str,
    ):
        self.id = id
        self.app_label = app_label
        self.model = model

    def __repr__(self):
        return f"DjangoContentType(id={self.id}, app_label={self.app_label!r}, model={self.model!r})"


class DjangoMigrations:
    def __init__(
        self,
        id: int,
        app: str,
        name: str,
        applied: datetime,
    ):
        self.id = id
        self.app = app
        self.name = name
        self.applied = applied

    def __repr__(self):
        return f"DjangoMigrations(id={self.id}, app={self.app!r}, name={self.name!r})"


class DjangoSession:
    def __init__(
        self,
        session_key: str,
        session_data: str,
        expire_date: datetime,
    ):
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date

    def __repr__(self):
        return f"DjangoSession(session_key={self.session_key!r})"


class AuthGroup:
    def __init__(
        self,
        id: int,
        name: str,
    ):
        self.id = id
        self.name = name
        self.permissions: List[AuthPermission] = []

    def __repr__(self):
        return f"AuthGroup(id={self.id}, name={self.name!r})"


class AuthPermission:
    def __init__(
        self,
        id: int,
        name: str,
        codename: str,
        content_type_id: int,
        content_type: Optional[DjangoContentType] = None,
    ):
        self.id = id
        self.name = name
        self.codename = codename
        self.content_type_id = content_type_id
        self.content_type = content_type

    def __repr__(self):
        return f"AuthPermission(id={self.id}, name={self.name!r}, codename={self.codename!r})"


class AuthGroupPermissions:
    def __init__(
        self,
        id: int,
        group_id: int,
        permission_id: int,
        group: Optional[AuthGroup] = None,
        permission: Optional[AuthPermission] = None,
    ):
        self.id = id
        self.group_id = group_id
        self.permission_id = permission_id
        self.group = group
        self.permission = permission

    def __repr__(self):
        return f"AuthGroupPermissions(id={self.id}, group_id={self.group_id}, permission_id={self.permission_id})"


# ============================================================
#  USER SERVICE
# ============================================================

class UserservicesUsers:
    def __init__(
        self,
        id: int,
        is_superuser: bool = False,
        first_name: str = "",
        last_name: str = "",
        is_staff: bool = False,
        is_active: bool = True,
        date_joined: Optional[datetime] = None,
        name: str = "",
        email: str = "",
        phone: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        pincode: str = "",
        country: str = "",
        profile_pic: str = "",
        account_status: str = "",
        role: str = "",
        dob: Optional[date] = None,
        username: str = "",
        password: str = "",
        social_media_links: Optional[Dict[str, Any]] = None,
        addition_details: Optional[Dict[str, Any]] = None,
        language: str = "",
        department: str = "",
        designation: str = "",
        time_zone: str = "",
        last_login: Optional[datetime] = None,
        last_device: str = "",
        last_ip: str = "",
        currency: str = "",
        domain_name: str = "",
        plan_type: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional["UserservicesUsers"] = None,
    ):
        self.id = id
        self.is_superuser = is_superuser
        self.first_name = first_name
        self.last_name = last_name
        self.is_staff = is_staff
        self.is_active = is_active
        self.date_joined = date_joined
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.profile_pic = profile_pic
        self.account_status = account_status
        self.role = role
        self.dob = dob
        self.username = username
        self.password = password
        self.social_media_links = social_media_links or {}
        self.addition_details = addition_details or {}
        self.language = language
        self.department = department
        self.designation = designation
        self.time_zone = time_zone
        self.last_login = last_login
        self.last_device = last_device
        self.last_ip = last_ip
        self.currency = currency
        self.domain_name = domain_name
        self.plan_type = plan_type
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user

    def __repr__(self):
        return f"UserservicesUsers(id={self.id}, username={self.username!r}, email={self.email!r})"


class UserservicesUserShippingAddress:
    def __init__(
        self,
        id: int,
        address_type: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        pincode: str = "",
        country: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        user_id: Optional[int] = None,
        user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.user = user

    def __repr__(self):
        return f"UserservicesUserShippingAddress(id={self.id}, user_id={self.user_id})"


class UserservicesActivityLog:
    def __init__(
        self,
        id: int,
        activity: str = "",
        activity_type: str = "",
        activity_date: Optional[datetime] = None,
        activity_ip: str = "",
        activity_device: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        user_id: Optional[int] = None,
        user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.user_id = user_id
        self.user = user

    def __repr__(self):
        return f"UserservicesActivityLog(id={self.id}, activity_type={self.activity_type!r})"


class UserservicesModules:
    def __init__(
        self,
        id: int,
        module_name: str = "",
        module_icon: str = "",
        is_menu: bool = False,
        is_active: bool = True,
        module_url: str = "",
        display_order: int = 0,
        module_description: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        parent_id_id: Optional[int] = None,
        parent: Optional["UserservicesModules"] = None,
    ):
        self.id = id
        self.module_name = module_name
        self.module_icon = module_icon
        self.is_menu = is_menu
        self.is_active = is_active
        self.module_url = module_url
        self.display_order = display_order
        self.module_description = module_description
        self.created_at = created_at
        self.updated_at = updated_at
        self.parent_id_id = parent_id_id
        self.parent = parent

    def __repr__(self):
        return f"UserservicesModules(id={self.id}, module_name={self.module_name!r})"


class UserservicesUserPermissions:
    def __init__(
        self,
        id: int,
        is_view: bool = False,
        is_add: bool = False,
        is_edit: bool = False,
        is_delete: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        module_id_id: Optional[int] = None,
        module: Optional[UserservicesModules] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        user_id: Optional[int] = None,
        user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = created_at
        self.updated_at = updated_at
        self.module_id_id = module_id_id
        self.module = module
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.user_id = user_id
        self.user = user

    def __repr__(self):
        return f"UserservicesUserPermissions(id={self.id}, user_id={self.user_id})"


class UserservicesUsersGroups:
    def __init__(
        self,
        id: int,
        users_id: int,
        group_id: int,
        user: Optional[UserservicesUsers] = None,
        group: Optional[AuthGroup] = None,
    ):
        self.id = id
        self.users_id = users_id
        self.group_id = group_id
        self.user = user
        self.group = group

    def __repr__(self):
        return f"UserservicesUsersGroups(id={self.id}, users_id={self.users_id}, group_id={self.group_id})"


class UserservicesUsersUserPermissions:
    def __init__(
        self,
        id: int,
        users_id: int,
        permission_id: int,
        user: Optional[UserservicesUsers] = None,
        permission: Optional[AuthPermission] = None,
    ):
        self.id = id
        self.users_id = users_id
        self.permission_id = permission_id
        self.user = user
        self.permission = permission

    def __repr__(self):
        return f"UserservicesUsersUserPermissions(id={self.id}, users_id={self.users_id}, permission_id={self.permission_id})"


class DjangoAdminLog:
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str = "",
        object_repr: str = "",
        action_flag: int = 0,
        change_message: str = "",
        content_type_id: Optional[int] = None,
        content_type: Optional[DjangoContentType] = None,
        user_id: Optional[int] = None,
        user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type_id = content_type_id
        self.content_type = content_type
        self.user_id = user_id
        self.user = user

    def __repr__(self):
        return f"DjangoAdminLog(id={self.id}, action_flag={self.action_flag})"


# ============================================================
#  PRODUCT SERVICE
# ============================================================

class ProductservicesCategories:
    def __init__(
        self,
        id: int,
        name: str = "",
        image: str = "",
        description: str = "",
        display_order: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        added_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        parent_id_id: Optional[int] = None,
        parent: Optional["ProductservicesCategories"] = None,
    ):
        self.id = id
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.added_by_user = added_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.parent_id_id = parent_id_id
        self.parent = parent

    def __repr__(self):
        return f"ProductservicesCategories(id={self.id}, name={self.name!r})"


class ProductservicesProducts:
    def __init__(
        self,
        id: int,
        name: str = "",
        image: Optional[Dict[str, Any]] = None,
        description: str = "",
        specifications: Optional[Dict[str, Any]] = None,
        html_description: str = "",
        highlights: Optional[Dict[str, Any]] = None,
        sku: str = "",
        initial_buying_price: float = 0.0,
        initial_selling_price: float = 0.0,
        weight: float = 0.0,
        dimensions: str = "",
        uom: str = "",
        color: str = "",
        tax_percentage: float = 0.0,
        brand: str = "",
        brand_model: str = "",
        status: str = "",
        seo_title: str = "",
        seo_description: str = "",
        seo_keywords: Optional[Dict[str, Any]] = None,
        addition_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        added_by_user: Optional[UserservicesUsers] = None,
        category_id_id: Optional[int] = None,
        category: Optional[ProductservicesCategories] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.name = name
        self.image = image or {}
        self.description = description
        self.specifications = specifications or {}
        self.html_description = html_description
        self.highlights = highlights or {}
        self.sku = sku
        self.initial_buying_price = initial_buying_price
        self.initial_selling_price = initial_selling_price
        self.weight = weight
        self.dimensions = dimensions
        self.uom = uom
        self.color = color
        self.tax_percentage = tax_percentage
        self.brand = brand
        self.brand_model = brand_model
        self.status = status
        self.seo_title = seo_title
        self.seo_description = seo_description
        self.seo_keywords = seo_keywords or {}
        self.addition_details = addition_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.added_by_user = added_by_user
        self.category_id_id = category_id_id
        self.category = category
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user

    def __repr__(self):
        return f"ProductservicesProducts(id={self.id}, name={self.name!r}, sku={self.sku!r})"


class ProductservicesProductQuestions:
    def __init__(
        self,
        id: int,
        question: str = "",
        answer: str = "",
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        answer_user_id_id: Optional[int] = None,
        answer_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        question_user_id_id: Optional[int] = None,
        question_user: Optional[UserservicesUsers] = None,
        product_id_id: Optional[int] = None,
        product: Optional[ProductservicesProducts] = None,
    ):
        self.id = id
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.answer_user_id_id = answer_user_id_id
        self.answer_user = answer_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.question_user_id_id = question_user_id_id
        self.question_user = question_user
        self.product_id_id = product_id_id
        self.product = product

    def __repr__(self):
        return f"ProductservicesProductQuestions(id={self.id}, product_id_id={self.product_id_id})"


class ProductservicesProductReviews:
    def __init__(
        self,
        id: int,
        review_images: Optional[Dict[str, Any]] = None,
        rating: float = 0.0,
        reviews: str = "",
        status: str = "",
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        review_user_id_id: Optional[int] = None,
        review_user: Optional[UserservicesUsers] = None,
        product_id_id: Optional[int] = None,
        product: Optional[ProductservicesProducts] = None,
    ):
        self.id = id
        self.review_images = review_images or {}
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.review_user_id_id = review_user_id_id
        self.review_user = review_user
        self.product_id_id = product_id_id
        self.product = product

    def __repr__(self):
        return f"ProductservicesProductReviews(id={self.id}, rating={self.rating}, product_id_id={self.product_id_id})"


# ============================================================
#  INVENTORY SERVICE
# ============================================================

class InventoryservicesWarehouse:
    def __init__(
        self,
        id: int,
        name: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        country: str = "",
        pincode: str = "",
        phone: str = "",
        email: str = "",
        status: str = "",
        size: str = "",
        capacity: str = "",
        warehouse_type: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        added_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        warehouse_manager_id: Optional[int] = None,
        warehouse_manager: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.country = country
        self.pincode = pincode
        self.phone = phone
        self.email = email
        self.status = status
        self.size = size
        self.capacity = capacity
        self.warehouse_type = warehouse_type
        self.additional_details = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.added_by_user = added_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.warehouse_manager_id = warehouse_manager_id
        self.warehouse_manager = warehouse_manager

    def __repr__(self):
        return f"InventoryservicesWarehouse(id={self.id}, name={self.name!r})"


class InventoryservicesRackAndShelvesAndFloor:
    def __init__(
        self,
        id: int,
        name: str = "",
        rack: str = "",
        shelf: str = "",
        floor: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        added_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        warehouse_id_id: Optional[int] = None,
        warehouse: Optional[InventoryservicesWarehouse] = None,
    ):
        self.id = id
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.added_by_user = added_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.warehouse_id_id = warehouse_id_id
        self.warehouse = warehouse

    def __repr__(self):
        return f"InventoryservicesRackAndShelvesAndFloor(id={self.id}, name={self.name!r})"


# ============================================================
#  ORDER SERVICE - Purchase
# ============================================================

class OrderservicePurchaseOrder:
    def __init__(
        self,
        id: int,
        po_code: str = "",
        po_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Optional[Decimal] = None,
        paid_amount: Optional[Decimal] = None,
        due_amount: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: str = "",
        shipping_amount: Optional[Decimal] = None,
        shipping_type: str = "",
        shipping_tax_percentage: Optional[Decimal] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        created_by_user_id_id: Optional[int] = None,
        created_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        last_updated_by_user: Optional[UserservicesUsers] = None,
        received_by_user_id_id: Optional[int] = None,
        received_by_user: Optional[UserservicesUsers] = None,
        returned_by_user_id_id: Optional[int] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        supplier_id_id: Optional[int] = None,
        supplier: Optional[UserservicesUsers] = None,
        updated_by_user_id_id: Optional[int] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
        warehouse_id_id: Optional[int] = None,
        warehouse: Optional[InventoryservicesWarehouse] = None,
    ):
        self.id = id
        self.po_code = po_code
        self.po_date = po_date
        self.expected_delivery_date = expected_delivery_date
        self.payment_terms = payment_terms
        self.payment_status = payment_status
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.due_amount = due_amount
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_type = shipping_type
        self.shipping_tax_percentage = shipping_tax_percentage
        self.shipping_tax_amount = shipping_tax_amount
        self.shipping_cancelled_amount = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount = shipping_cancelled_tax_amount
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
        self.approved_by_user_id_id = approved_by_user_id_id
        self.approved_by_user = approved_by_user
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user_id_id = created_by_user_id_id
        self.created_by_user = created_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.last_updated_by_user_id_id = last_updated_by_user_id_id
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user_id_id = received_by_user_id_id
        self.received_by_user = received_by_user
        self.returned_by_user_id_id = returned_by_user_id_id
        self.returned_by_user = returned_by_user
        self.supplier_id_id = supplier_id_id
        self.supplier = supplier
        self.updated_by_user_id_id = updated_by_user_id_id
        self.updated_by_user = updated_by_user
        self.warehouse_id_id = warehouse_id_id
        self.warehouse = warehouse

    def __repr__(self):
        return f"OrderservicePurchaseOrder(id={self.id}, po_code={self.po_code!r}, status={self.status!r})"


class OrderservicePurchaseOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: int = 0,
        quantity_received: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        buying_price: Optional[Decimal] = None,
        selling_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        amount_paid: Optional[Decimal] = None,
        amount_returned: Optional[Decimal] = None,
        amount_cancelled: Optional[Decimal] = None,
        amount_ordered: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        discount_type: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        created_by_user_id_id: Optional[int] = None,
        created_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        last_updated_by_user: Optional[UserservicesUsers] = None,
        received_by_user_id_id: Optional[int] = None,
        received_by_user: Optional[UserservicesUsers] = None,
        returned_by_user_id_id: Optional[int] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        po_id_id: Optional[int] = None,
        po: Optional[OrderservicePurchaseOrder] = None,
        product_id_id: Optional[int] = None,
        product: Optional[ProductservicesProducts] = None,
        updated_by_user_id_id: Optional[int] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.quantity_ordered = quantity_ordered
        self.quantity_received = quantity_received
        self.quantity_cancelled = quantity_cancelled
        self.quantity_returned = quantity_returned
        self.buying_price = buying_price
        self.selling_price = selling_price
        self.discount_amount = discount_amount
        self.amount_paid = amount_paid
        self.amount_returned = amount_returned
        self.amount_cancelled = amount_cancelled
        self.amount_ordered = amount_ordered
        self.tax_percentage = tax_percentage
        self.tax_amount = tax_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.shipping_amount = shipping_amount
        self.shipping_tax_amount = shipping_tax_amount
        self.shipping_cancelled_amount = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount = shipping_cancelled_tax_amount
        self.discount_type = discount_type
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
        self.approved_by_user_id_id = approved_by_user_id_id
        self.approved_by_user = approved_by_user
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user_id_id = created_by_user_id_id
        self.created_by_user = created_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.last_updated_by_user_id_id = last_updated_by_user_id_id
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user_id_id = received_by_user_id_id
        self.received_by_user = received_by_user
        self.returned_by_user_id_id = returned_by_user_id_id
        self.returned_by_user = returned_by_user
        self.po_id_id = po_id_id
        self.po = po
        self.product_id_id = product_id_id
        self.product = product
        self.updated_by_user_id_id = updated_by_user_id_id
        self.updated_by_user = updated_by_user

    def __repr__(self):
        return f"OrderservicePurchaseOrderItems(id={self.id}, po_id_id={self.po_id_id}, status={self.status!r})"


class OrderservicePurchaseOrderLogs:
    def __init__(
        self,
        id: int,
        comment: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        created_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        po_id_id: Optional[int] = None,
        po: Optional[OrderservicePurchaseOrder] = None,
    ):
        self.id = id
        self.comment = comment
        self.additional_details = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user_id_id = created_by_user_id_id
        self.created_by_user = created_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.po_id_id = po_id_id
        self.po = po

    def __repr__(self):
        return f"OrderservicePurchaseOrderLogs(id={self.id}, po_id_id={self.po_id_id})"


class OrderservicePurchaseOrderInwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        inwarded_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        inwarded_by_user_id_id: Optional[int] = None,
        inwarded_by_user: Optional[UserservicesUsers] = None,
        po_id_id: Optional[int] = None,
        po: Optional[OrderservicePurchaseOrder] = None,
    ):
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.inwarded_by_user_id_id = inwarded_by_user_id_id
        self.inwarded_by_user = inwarded_by_user
        self.po_id_id = po_id_id
        self.po = po

    def __repr__(self):
        return f"OrderservicePurchaseOrderInwardedLog(id={self.id}, po_id_id={self.po_id_id})"


class OrderservicePurchaseOrderItemInwardedLog:
    def __init__(
        self,
        id: int,
        inwarded_quantity: int = 0,
        price: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: str = "",
        shipping_amount: Optional[Decimal] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        po_item_id_id: Optional[int] = None,
        po_item: Optional[OrderservicePurchaseOrderItems] = None,
    ):
        self.id = id
        self.inwarded_quantity = inwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.po_item_id_id = po_item_id_id
        self.po_item = po_item

    def __repr__(self):
        return f"OrderservicePurchaseOrderItemInwardedLog(id={self.id}, po_item_id_id={self.po_item_id_id})"


# ============================================================
#  ORDER SERVICE - Sales
# ============================================================

class OrderserviceSalesOrder:
    def __init__(
        self,
        id: int,
        so_code: str = "",
        so_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Optional[Decimal] = None,
        paid_amount: Optional[Decimal] = None,
        due_amount: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: str = "",
        shipping_amount: Optional[Decimal] = None,
        shipping_type: str = "",
        shipping_tax_percentage: Optional[Decimal] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        created_by_user_id_id: Optional[int] = None,
        created_by_user: Optional[UserservicesUsers] = None,
        customer_id_id: Optional[int] = None,
        customer: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        last_updated_by_user: Optional[UserservicesUsers] = None,
        received_by_user_id_id: Optional[int] = None,
        received_by_user: Optional[UserservicesUsers] = None,
        returned_by_user_id_id: Optional[int] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        po_id_id: Optional[int] = None,
        po: Optional[OrderservicePurchaseOrder] = None,
        product_id_id: Optional[int] = None,
        product: Optional[ProductservicesProducts] = None,
        updated_by_user_id_id: Optional[int] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.so_code = so_code
        self.so_date = so_date
        self.expected_delivery_date = expected_delivery_date
        self.payment_terms = payment_terms
        self.payment_status = payment_status
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.due_amount = due_amount
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_type = shipping_type
        self.shipping_tax_percentage = shipping_tax_percentage
        self.shipping_tax_amount = shipping_tax_amount
        self.shipping_cancelled_amount = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount = shipping_cancelled_tax_amount
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
        self.approved_by_user_id_id = approved_by_user_id_id
        self.approved_by_user = approved_by_user
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user_id_id = created_by_user_id_id
        self.created_by_user = created_by_user
        self.customer_id_id = customer_id_id
        self.customer = customer
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.last_updated_by_user_id_id = last_updated_by_user_id_id
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user_id_id = received_by_user_id_id
        self.received_by_user = received_by_user
        self.returned_by_user_id_id = returned_by_user_id_id
        self.returned_by_user = returned_by_user
        self.po_id_id = po_id_id
        self.po = po
        self.product_id_id = product_id_id
        self.product = product
        self.updated_by_user_id_id = updated_by_user_id_id
        self.updated_by_user = updated_by_user

    def __repr__(self):
        return f"OrderserviceSalesOrder(id={self.id}, so_code={self.so_code!r}, status={self.status!r})"


class OrderserviceSalesOrderOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: int = 0,
        quantity_delivered: int = 0,
        quantity_shipped: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        purchase_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: str = "",
        amount_paid: Optional[Decimal] = None,
        amount_returned: Optional[Decimal] = None,
        amount_cancelled: Optional[Decimal] = None,
        amount_ordered: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_type: str = "",
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        shipped_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        created_by_user_id_id: Optional[int] = None,
        created_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        product_id_id: Optional[int] = None,
        product: Optional[ProductservicesProducts] = None,
        returned_by_user_id_id: Optional[int] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        shipped_by_user_id_id: Optional[int] = None,
        shipped_by_user: Optional[UserservicesUsers] = None,
        so_id_id: Optional[int] = None,
        so: Optional[OrderserviceSalesOrder] = None,
        updated_by_user_id_id: Optional[int] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
    ):
        self.id = id
        self.quantity_ordered = quantity_ordered
        self.quantity_delivered = quantity_delivered
        self.quantity_shipped = quantity_shipped
        self.quantity_cancelled = quantity_cancelled
        self.quantity_returned = quantity_returned
        self.purchase_price = purchase_price
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.amount_paid = amount_paid
        self.amount_returned = amount_returned
        self.amount_cancelled = amount_cancelled
        self.amount_ordered = amount_ordered
        self.tax_percentage = tax_percentage
        self.tax_amount = tax_amount
        self.shipping_amount = shipping_amount
        self.shipping_type = shipping_type
        self.shipping_tax_amount = shipping_tax_amount
        self.shipping_cancelled_amount = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount = shipping_cancelled_tax_amount
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.shipped_at = shipped_at
        self.returned_at = returned_at
        self.approved_by_user_id_id = approved_by_user_id_id
        self.approved_by_user = approved_by_user
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user_id_id = created_by_user_id_id
        self.created_by_user = created_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.product_id_id = product_id_id
        self.product = product
        self.returned_by_user_id_id = returned_by_user_id_id
        self.returned_by_user = returned_by_user
        self.shipped_by_user_id_id = shipped_by_user_id_id
        self.shipped_by_user = shipped_by_user
        self.so_id_id = so_id_id
        self.so = so
        self.updated_by_user_id_id = updated_by_user_id_id
        self.updated_by_user = updated_by_user

    def __repr__(self):
        return f"OrderserviceSalesOrderOrderItems(id={self.id}, so_id_id={self.so_id_id}, status={self.status!r})"


class OrderserviceSalesOrderLogs:
    def __init__(
        self,
        id: int,
        comment: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        created_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        so_id_id: Optional[int] = None,
        so: Optional[OrderserviceSalesOrder] = None,
    ):
        self.id = id
        self.comment = comment
        self.additional_details = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user_id_id = created_by_user_id_id
        self.created_by_user = created_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.so_id_id = so_id_id
        self.so = so

    def __repr__(self):
        return f"OrderserviceSalesOrderLogs(id={self.id}, so_id_id={self.so_id_id})"


class OrderserviceSalesOrderOutwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        outwared_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        outwarded_by_user_id_id: Optional[int] = None,
        outwarded_by_user: Optional[UserservicesUsers] = None,
        so_id_id: Optional[int] = None,
        so: Optional[OrderserviceSalesOrder] = None,
    ):
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.outwarded_by_user_id_id = outwarded_by_user_id_id
        self.outwarded_by_user = outwarded_by_user
        self.so_id_id = so_id_id
        self.so = so

    def __repr__(self):
        return f"OrderserviceSalesOrderOutwardedLog(id={self.id}, so_id_id={self.so_id_id})"


class OrderserviceSalesOrderItemOutwardedLog:
    def __init__(
        self,
        id: int,
        outwarded_quantity: int = 0,
        price: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: str = "",
        shipping_amount: Optional[Decimal] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        so_item_id_id: Optional[int] = None,
        so_item: Optional[OrderserviceSalesOrderOrderItems] = None,
    ):
        self.id = id
        self.outwarded_quantity = outwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.so_item_id_id = so_item_id_id
        self.so_item = so_item

    def __repr__(self):
        return f"OrderserviceSalesOrderItemOutwardedLog(id={self.id}, so_item_id_id={self.so_item_id_id})"


# ============================================================
#  INVENTORY SERVICE (continued - depends on order service)
# ============================================================

class InventoryservicesInventory:
    def __init__(
        self,
        id: int,
        quantity: int = 0,
        mrp: str = "",
        batch_number: str = "",
        discount_type: str = "",
        discount_amout: float = 0.0,
        sr_no: str = "",
        mfg_date: Optional[datetime] = None,
        uom: str = "",
        ptr: str = "",
        received_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        quantity_inwarded: int = 0,
        buy_price: Optional[Decimal] = None,
        sell_price: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        stock_status: str = "",
        inward_type: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        added_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        product_id_id: Optional[int] = None,
        product: Optional[ProductservicesProducts] = None,
        purchase_order_id_id: Optional[int] = None,
        purchase_order: Optional[OrderservicePurchaseOrder] = None,
        purchase_order_item_id_id: Optional[int] = None,
        purchase_order_item: Optional[OrderservicePurchaseOrderItems] = None,
        purchase_order_item_inwarded_item_id_id: Optional[int] = None,
        purchase_order_item_inwarded_item: Optional[OrderservicePurchaseOrderItemInwardedLog] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        rack_shelf_floor: Optional[InventoryservicesRackAndShelvesAndFloor] = None,
        warehouse_id_id: Optional[int] = None,
        warehouse: Optional[InventoryservicesWarehouse] = None,
    ):
        self.id = id
        self.quantity = quantity
        self.mrp = mrp
        self.batch_number = batch_number
        self.discount_type = discount_type
        self.discount_amout = discount_amout
        self.sr_no = sr_no
        self.mfg_date = mfg_date
        self.uom = uom
        self.ptr = ptr
        self.received_date = received_date
        self.expiry_date = expiry_date
        self.quantity_inwarded = quantity_inwarded
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.tax_percentage = tax_percentage
        self.stock_status = stock_status
        self.inward_type = inward_type
        self.additional_details = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.added_by_user = added_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.product_id_id = product_id_id
        self.product = product
        self.purchase_order_id_id = purchase_order_id_id
        self.purchase_order = purchase_order
        self.purchase_order_item_id_id = purchase_order_item_id_id
        self.purchase_order_item = purchase_order_item
        self.purchase_order_item_inwarded_item_id_id = purchase_order_item_inwarded_item_id_id
        self.purchase_order_item_inwarded_item = purchase_order_item_inwarded_item
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse_id_id = warehouse_id_id
        self.warehouse = warehouse

    def __repr__(self):
        return f"InventoryservicesInventory(id={self.id}, stock_status={self.stock_status!r}, quantity={self.quantity})"


class InventoryservicesInventoryLog:
    def __init__(
        self,
        id: int,
        quantity: int = 0,
        status: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        added_by_user: Optional[UserservicesUsers] = None,
        domain_user_id_id: Optional[int] = None,
        domain_user: Optional[UserservicesUsers] = None,
        inventory_id_id: Optional[int] = None,
        inventory: Optional[InventoryservicesInventory] = None,
        po_id_id: Optional[int] = None,
        po: Optional[OrderservicePurchaseOrder] = None,
        so_id_id: Optional[int] = None,
        so: Optional[OrderserviceSalesOrder] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        rack_shelf_floor: Optional[InventoryservicesRackAndShelvesAndFloor] = None,
        warehouse_id_id: Optional[int] = None,
        warehouse: Optional[InventoryservicesWarehouse] = None,
    ):
        self.id = id
        self.quantity = quantity
        self.status = status
        self.additional_details = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.added_by_user = added_by_user
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user
        self.inventory_id_id = inventory_id_id
        self.inventory = inventory
        self.po_id_id = po_id_id
        self.po = po
        self.so_id_id = so_id_id
        self.so = so
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse_id_id = warehouse_id_id
        self.warehouse = warehouse

    def __repr__(self):
        return f"InventoryservicesInventoryLog(id={self.id}, status={self.status!r}, quantity={self.quantity})"


# ============================================================
#  IN-MEMORY REPOSITORY / DATABASE SIMULATION
# ============================================================

class Repository:
    """Generic in-memory repository for storing and retrieving entities by id."""

    def __init__(self):
        self._store: Dict[Any, Any] = {}

    def save(self, entity: Any) -> Any:
        key = getattr(entity, 'id', None) or getattr(entity, 'session_key', None)
        if key is None:
            raise ValueError("Entity must have an 'id' or 'session_key' attribute.")
        self._store[key] = entity
        return entity

    def get(self, key: Any) -> Optional[Any]:
        return self._store.get(key)

    def all(self) -> List[Any]:
        return list(self._store.values())

    def delete(self, key: Any) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def filter(self, **kwargs) -> List[Any]:
        results = []
        for entity in self._store.values():
            match = all(
                getattr(entity, attr, None) == value
                for attr, value in kwargs.items()
            )
            if match:
                results.append(entity)
        return results

    def count(self) -> int:
        return len(self._store)


# ============================================================
#  DATABASE - collection of all repositories
# ============================================================

class EcommerceDatabase:
    """Central database holding all repositories for the ecommerce system."""

    def __init__(self):
        # Django / Auth
        self.django_content_types: Repository = Repository()
        self.django_migrations: Repository = Repository()
        self.django_sessions: Repository = Repository()
        self.django_admin_logs: Repository = Repository()
        self.auth_groups: Repository = Repository()
        self.auth_permissions: Repository = Repository()
        self.auth_group_permissions: Repository = Repository()

        # User Service
        self.users: Repository = Repository()
        self.user_shipping_addresses: Repository = Repository()
        self.activity_logs: Repository = Repository()
        self.modules: Repository = Repository()
        self.user_permissions: Repository = Repository()
        self.users_groups: Repository = Repository()
        self.users_user_permissions: Repository = Repository()

        # Product Service
        self.categories: Repository = Repository()
        self.products: Repository = Repository()
        self.product_questions: Repository = Repository()
        self.product_reviews: Repository = Repository()

        # Inventory Service
        self.warehouses: Repository = Repository()
        self.rack_shelves_floors: Repository = Repository()
        self.inventories: Repository = Repository()
        self.inventory_logs: Repository = Repository()

        # Order Service - Purchase
        self.purchase_orders: Repository = Repository()
        self.purchase_order_items: Repository = Repository()
        self.purchase_order_logs: Repository = Repository()
        self.purchase_order_inwarded_logs: Repository = Repository()
        self.purchase_order_item_inwarded_logs: Repository = Repository()

        # Order Service - Sales
        self.sales_orders: Repository = Repository()
        self.sales_order_items: Repository = Repository()
        self.sales_order_logs: Repository = Repository()
        self.sales_order_outwarded_logs: Repository = Repository()
        self.sales_order_item_outwarded_logs: Repository = Repository()

    def __repr__(self):
        return "EcommerceDatabase()"