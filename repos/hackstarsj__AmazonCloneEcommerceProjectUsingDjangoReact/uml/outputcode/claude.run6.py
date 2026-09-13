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


# ============================================================
#  DJANGO ADMIN LOG
# ============================================================

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
        return f"OrderservicePurchaseOrderItems(id={self.id}, po_id_id={self.po_id_id}, product_id_id={self.product_id_id})"


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
        return f"OrderserviceSalesOrderOrderItems(id={self.id}, so_id_id={self.so_id_id}, product_id_id={self.product_id_id})"


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
#  INVENTORY SERVICE - Inventory and InventoryLog
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
        return f"InventoryservicesInventory(id={self.id}, product_id_id={self.product_id_id}, quantity={self.quantity})"


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
        return f"InventoryservicesInventoryLog(id={self.id}, inventory_id_id={self.inventory_id_id}, status={self.status!r})"


# ============================================================
#  REPOSITORY / MANAGER CLASSES
# ============================================================

class UserservicesUsersRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesUsers] = {}

    def save(self, user: UserservicesUsers) -> UserservicesUsers:
        self._store[user.id] = user
        return user

    def get_by_id(self, id: int) -> Optional[UserservicesUsers]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesUsers]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class AuthGroupRepository:
    def __init__(self):
        self._store: Dict[int, AuthGroup] = {}

    def save(self, group: AuthGroup) -> AuthGroup:
        self._store[group.id] = group
        return group

    def get_by_id(self, id: int) -> Optional[AuthGroup]:
        return self._store.get(id)

    def get_all(self) -> List[AuthGroup]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class AuthPermissionRepository:
    def __init__(self):
        self._store: Dict[int, AuthPermission] = {}

    def save(self, permission: AuthPermission) -> AuthPermission:
        self._store[permission.id] = permission
        return permission

    def get_by_id(self, id: int) -> Optional[AuthPermission]:
        return self._store.get(id)

    def get_all(self) -> List[AuthPermission]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoContentTypeRepository:
    def __init__(self):
        self._store: Dict[int, DjangoContentType] = {}

    def save(self, ct: DjangoContentType) -> DjangoContentType:
        self._store[ct.id] = ct
        return ct

    def get_by_id(self, id: int) -> Optional[DjangoContentType]:
        return self._store.get(id)

    def get_all(self) -> List[DjangoContentType]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesCategoriesRepository:
    def __init__(self):
        self._store: Dict[int, ProductservicesCategories] = {}

    def save(self, category: ProductservicesCategories) -> ProductservicesCategories:
        self._store[category.id] = category
        return category

    def get_by_id(self, id: int) -> Optional[ProductservicesCategories]:
        return self._store.get(id)

    def get_all(self) -> List[ProductservicesCategories]:
        return list(self._store.values())

    def get_by_parent(self, parent_id: int) -> List[ProductservicesCategories]:
        return [c for c in self._store.values() if c.parent_id_id == parent_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesProductsRepository:
    def __init__(self):
        self._store: Dict[int, ProductservicesProducts] = {}

    def save(self, product: ProductservicesProducts) -> ProductservicesProducts:
        self._store[product.id] = product
        return product

    def get_by_id(self, id: int) -> Optional[ProductservicesProducts]:
        return self._store.get(id)

    def get_all(self) -> List[ProductservicesProducts]:
        return list(self._store.values())

    def get_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [p for p in self._store.values() if p.category_id_id == category_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesProductQuestionsRepository:
    def __init__(self):
        self._store: Dict[int, ProductservicesProductQuestions] = {}

    def save(self, question: ProductservicesProductQuestions) -> ProductservicesProductQuestions:
        self._store[question.id] = question
        return question

    def get_by_id(self, id: int) -> Optional[ProductservicesProductQuestions]:
        return self._store.get(id)

    def get_all(self) -> List[ProductservicesProductQuestions]:
        return list(self._store.values())

    def get_by_product(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [q for q in self._store.values() if q.product_id_id == product_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class ProductservicesProductReviewsRepository:
    def __init__(self):
        self._store: Dict[int, ProductservicesProductReviews] = {}

    def save(self, review: ProductservicesProductReviews) -> ProductservicesProductReviews:
        self._store[review.id] = review
        return review

    def get_by_id(self, id: int) -> Optional[ProductservicesProductReviews]:
        return self._store.get(id)

    def get_all(self) -> List[ProductservicesProductReviews]:
        return list(self._store.values())

    def get_by_product(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [r for r in self._store.values() if r.product_id_id == product_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesWarehouseRepository:
    def __init__(self):
        self._store: Dict[int, InventoryservicesWarehouse] = {}

    def save(self, warehouse: InventoryservicesWarehouse) -> InventoryservicesWarehouse:
        self._store[warehouse.id] = warehouse
        return warehouse

    def get_by_id(self, id: int) -> Optional[InventoryservicesWarehouse]:
        return self._store.get(id)

    def get_all(self) -> List[InventoryservicesWarehouse]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesRackAndShelvesAndFloorRepository:
    def __init__(self):
        self._store: Dict[int, InventoryservicesRackAndShelvesAndFloor] = {}

    def save(self, rack: InventoryservicesRackAndShelvesAndFloor) -> InventoryservicesRackAndShelvesAndFloor:
        self._store[rack.id] = rack
        return rack

    def get_by_id(self, id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._store.get(id)

    def get_all(self) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return list(self._store.values())

    def get_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return [r for r in self._store.values() if r.warehouse_id_id == warehouse_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesInventoryRepository:
    def __init__(self):
        self._store: Dict[int, InventoryservicesInventory] = {}

    def save(self, inventory: InventoryservicesInventory) -> InventoryservicesInventory:
        self._store[inventory.id] = inventory
        return inventory

    def get_by_id(self, id: int) -> Optional[InventoryservicesInventory]:
        return self._store.get(id)

    def get_all(self) -> List[InventoryservicesInventory]:
        return list(self._store.values())

    def get_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.product_id_id == product_id]

    def get_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.warehouse_id_id == warehouse_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class InventoryservicesInventoryLogRepository:
    def __init__(self):
        self._store: Dict[int, InventoryservicesInventoryLog] = {}

    def save(self, log: InventoryservicesInventoryLog) -> InventoryservicesInventoryLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[InventoryservicesInventoryLog]:
        return self._store.get(id)

    def get_all(self) -> List[InventoryservicesInventoryLog]:
        return list(self._store.values())

    def get_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [l for l in self._store.values() if l.inventory_id_id == inventory_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderRepository:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrder] = {}

    def save(self, po: OrderservicePurchaseOrder) -> OrderservicePurchaseOrder:
        self._store[po.id] = po
        return po

    def get_by_id(self, id: int) -> Optional[OrderservicePurchaseOrder]:
        return self._store.get(id)

    def get_all(self) -> List[OrderservicePurchaseOrder]:
        return list(self._store.values())

    def get_by_status(self, status: str) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.status == status]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderItemsRepository:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderItems] = {}

    def save(self, item: OrderservicePurchaseOrderItems) -> OrderservicePurchaseOrderItems:
        self._store[item.id] = item
        return item

    def get_by_id(self, id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self._store.get(id)

    def get_all(self) -> List[OrderservicePurchaseOrderItems]:
        return list(self._store.values())

    def get_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [i for i in self._store.values() if i.po_id_id == po_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderLogsRepository:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderLogs] = {}

    def save(self, log: OrderservicePurchaseOrderLogs) -> OrderservicePurchaseOrderLogs:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self._store.get(id)

    def get_all(self) -> List[OrderservicePurchaseOrderLogs]:
        return list(self._store.values())

    def get_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return [l for l in self._store.values() if l.po_id_id == po_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderInwardedLogRepository:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderInwardedLog] = {}

    def save(self, log: OrderservicePurchaseOrderInwardedLog) -> OrderservicePurchaseOrderInwardedLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self._store.get(id)

    def get_all(self) -> List[OrderservicePurchaseOrderInwardedLog]:
        return list(self._store.values())

    def get_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderInwardedLog]:
        return [l for l in self._store.values() if l.po_id_id == po_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderservicePurchaseOrderItemInwardedLogRepository:
    def __init__(self):
        self._store: Dict[int, OrderservicePurchaseOrderItemInwardedLog] = {}

    def save(self, log: OrderservicePurchaseOrderItemInwardedLog) -> OrderservicePurchaseOrderItemInwardedLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._store.get(id)

    def get_all(self) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return list(self._store.values())

    def get_by_po_item(self, po_item_id: int) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return [l for l in self._store.values() if l.po_item_id_id == po_item_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderRepository:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrder] = {}

    def save(self, so: OrderserviceSalesOrder) -> OrderserviceSalesOrder:
        self._store[so.id] = so
        return so

    def get_by_id(self, id: int) -> Optional[OrderserviceSalesOrder]:
        return self._store.get(id)

    def get_all(self) -> List[OrderserviceSalesOrder]:
        return list(self._store.values())

    def get_by_status(self, status: str) -> List[OrderserviceSalesOrder]:
        return [so for so in self._store.values() if so.status == status]

    def get_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return [so for so in self._store.values() if so.customer_id_id == customer_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderOrderItemsRepository:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderOrderItems] = {}

    def save(self, item: OrderserviceSalesOrderOrderItems) -> OrderserviceSalesOrderOrderItems:
        self._store[item.id] = item
        return item

    def get_by_id(self, id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._store.get(id)

    def get_all(self) -> List[OrderserviceSalesOrderOrderItems]:
        return list(self._store.values())

    def get_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [i for i in self._store.values() if i.so_id_id == so_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderLogsRepository:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderLogs] = {}

    def save(self, log: OrderserviceSalesOrderLogs) -> OrderserviceSalesOrderLogs:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self._store.get(id)

    def get_all(self) -> List[OrderserviceSalesOrderLogs]:
        return list(self._store.values())

    def get_by_so(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return [l for l in self._store.values() if l.so_id_id == so_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderOutwardedLogRepository:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderOutwardedLog] = {}

    def save(self, log: OrderserviceSalesOrderOutwardedLog) -> OrderserviceSalesOrderOutwardedLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self._store.get(id)

    def get_all(self) -> List[OrderserviceSalesOrderOutwardedLog]:
        return list(self._store.values())

    def get_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOutwardedLog]:
        return [l for l in self._store.values() if l.so_id_id == so_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class OrderserviceSalesOrderItemOutwardedLogRepository:
    def __init__(self):
        self._store: Dict[int, OrderserviceSalesOrderItemOutwardedLog] = {}

    def save(self, log: OrderserviceSalesOrderItemOutwardedLog) -> OrderserviceSalesOrderItemOutwardedLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self._store.get(id)

    def get_all(self) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return list(self._store.values())

    def get_by_so_item(self, so_item_id: int) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return [l for l in self._store.values() if l.so_item_id_id == so_item_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUserShippingAddressRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesUserShippingAddress] = {}

    def save(self, address: UserservicesUserShippingAddress) -> UserservicesUserShippingAddress:
        self._store[address.id] = address
        return address

    def get_by_id(self, id: int) -> Optional[UserservicesUserShippingAddress]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesUserShippingAddress]:
        return list(self._store.values())

    def get_by_user(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [a for a in self._store.values() if a.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesActivityLogRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesActivityLog] = {}

    def save(self, log: UserservicesActivityLog) -> UserservicesActivityLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[UserservicesActivityLog]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesActivityLog]:
        return list(self._store.values())

    def get_by_user(self, user_id: int) -> List[UserservicesActivityLog]:
        return [l for l in self._store.values() if l.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesModulesRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesModules] = {}

    def save(self, module: UserservicesModules) -> UserservicesModules:
        self._store[module.id] = module
        return module

    def get_by_id(self, id: int) -> Optional[UserservicesModules]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesModules]:
        return list(self._store.values())

    def get_by_parent(self, parent_id: int) -> List[UserservicesModules]:
        return [m for m in self._store.values() if m.parent_id_id == parent_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUserPermissionsRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesUserPermissions] = {}

    def save(self, perm: UserservicesUserPermissions) -> UserservicesUserPermissions:
        self._store[perm.id] = perm
        return perm

    def get_by_id(self, id: int) -> Optional[UserservicesUserPermissions]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesUserPermissions]:
        return list(self._store.values())

    def get_by_user(self, user_id: int) -> List[UserservicesUserPermissions]:
        return [p for p in self._store.values() if p.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUsersGroupsRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesUsersGroups] = {}

    def save(self, ug: UserservicesUsersGroups) -> UserservicesUsersGroups:
        self._store[ug.id] = ug
        return ug

    def get_by_id(self, id: int) -> Optional[UserservicesUsersGroups]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesUsersGroups]:
        return list(self._store.values())

    def get_by_user(self, users_id: int) -> List[UserservicesUsersGroups]:
        return [ug for ug in self._store.values() if ug.users_id == users_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class UserservicesUsersUserPermissionsRepository:
    def __init__(self):
        self._store: Dict[int, UserservicesUsersUserPermissions] = {}

    def save(self, up: UserservicesUsersUserPermissions) -> UserservicesUsersUserPermissions:
        self._store[up.id] = up
        return up

    def get_by_id(self, id: int) -> Optional[UserservicesUsersUserPermissions]:
        return self._store.get(id)

    def get_all(self) -> List[UserservicesUsersUserPermissions]:
        return list(self._store.values())

    def get_by_user(self, users_id: int) -> List[UserservicesUsersUserPermissions]:
        return [up for up in self._store.values() if up.users_id == users_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoAdminLogRepository:
    def __init__(self):
        self._store: Dict[int, DjangoAdminLog] = {}

    def save(self, log: DjangoAdminLog) -> DjangoAdminLog:
        self._store[log.id] = log
        return log

    def get_by_id(self, id: int) -> Optional[DjangoAdminLog]:
        return self._store.get(id)

    def get_all(self) -> List[DjangoAdminLog]:
        return list(self._store.values())

    def get_by_user(self, user_id: int) -> List[DjangoAdminLog]:
        return [l for l in self._store.values() if l.user_id == user_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoMigrationsRepository:
    def __init__(self):
        self._store: Dict[int, DjangoMigrations] = {}

    def save(self, migration: DjangoMigrations) -> DjangoMigrations:
        self._store[migration.id] = migration
        return migration

    def get_by_id(self, id: int) -> Optional[DjangoMigrations]:
        return self._store.get(id)

    def get_all(self) -> List[DjangoMigrations]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


class DjangoSessionRepository:
    def __init__(self):
        self._store: Dict[str, DjangoSession] = {}

    def save(self, session: DjangoSession) -> DjangoSession:
        self._store[session.session_key] = session
        return session

    def get_by_key(self, session_key: str) -> Optional[DjangoSession]:
        return self._store.get(session_key)

    def get_all(self) -> List[DjangoSession]:
        return list(self._store.values())

    def delete(self, session_key: str) -> bool:
        if session_key in self._store:
            del self._store[session_key]
            return True
        return False


class AuthGroupPermissionsRepository:
    def __init__(self):
        self._store: Dict[int, AuthGroupPermissions] = {}

    def save(self, gp: AuthGroupPermissions) -> AuthGroupPermissions:
        self._store[gp.id] = gp
        return gp

    def get_by_id(self, id: int) -> Optional[AuthGroupPermissions]:
        return self._store.get(id)

    def get_all(self) -> List[AuthGroupPermissions]:
        return list(self._store.values())

    def get_by_group(self, group_id: int) -> List[AuthGroupPermissions]:
        return [gp for gp in self._store.values() if gp.group_id == group_id]

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False


# ============================================================
#  SERVICE CLASSES
# ============================================================

class UserService:
    def __init__(self):
        self.users_repo = UserservicesUsersRepository()
        self.shipping_address_repo = UserservicesUserShippingAddressRepository()
        self.activity_log_repo = UserservicesActivityLogRepository()
        self.modules_repo = UserservicesModulesRepository()
        self.user_permissions_repo = UserservicesUserPermissionsRepository()
        self.users_groups_repo = UserservicesUsersGroupsRepository()
        self.users_user_permissions_repo = UserservicesUsersUserPermissionsRepository()

    def create_user(self, user: UserservicesUsers) -> UserservicesUsers:
        return self.users_repo.save(user)

    def get_user(self, user_id: int) -> Optional[UserservicesUsers]:
        return self.users_repo.get_by_id(user_id)

    def update_user(self, user: UserservicesUsers) -> UserservicesUsers:
        return self.users_repo.save(user)

    def delete_user(self, user_id: int) -> bool:
        return self.users_repo.delete(user_id)

    def add_shipping_address(self, address: UserservicesUserShippingAddress) -> UserservicesUserShippingAddress:
        return self.shipping_address_repo.save(address)

    def get_user_shipping_addresses(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return self.shipping_address_repo.get_by_user(user_id)

    def log_activity(self, log: UserservicesActivityLog) -> UserservicesActivityLog:
        return self.activity_log_repo.save(log)

    def get_user_activity_logs(self, user_id: int) -> List[UserservicesActivityLog]:
        return self.activity_log_repo.get_by_user(user_id)

    def create_module(self, module: UserservicesModules) -> UserservicesModules:
        return self.modules_repo.save(module)

    def get_module(self, module_id: int) -> Optional[UserservicesModules]:
        return self.modules_repo.get_by_id(module_id)

    def set_user_permission(self, permission: UserservicesUserPermissions) -> UserservicesUserPermissions:
        return self.user_permissions_repo.save(permission)

    def get_user_permissions(self, user_id: int) -> List[UserservicesUserPermissions]:
        return self.user_permissions_repo.get_by_user(user_id)

    def assign_user_to_group(self, user_group: UserservicesUsersGroups) -> UserservicesUsersGroups:
        return self.users_groups_repo.save(user_group)

    def assign_permission_to_user(self, user_perm: UserservicesUsersUserPermissions) -> UserservicesUsersUserPermissions:
        return self.users_user_permissions_repo.save(user_perm)


class ProductService:
    def __init__(self):
        self.categories_repo = ProductservicesCategoriesRepository()
        self.products_repo = ProductservicesProductsRepository()
        self.questions_repo = ProductservicesProductQuestionsRepository()
        self.reviews_repo = ProductservicesProductReviewsRepository()

    def create_category(self, category: ProductservicesCategories) -> ProductservicesCategories:
        return self.categories_repo.save(category)

    def get_category(self, category_id: int) -> Optional[ProductservicesCategories]:
        return self.categories_repo.get_by_id(category_id)

    def get_subcategories(self, parent_id: int) -> List[ProductservicesCategories]:
        return self.categories_repo.get_by_parent(parent_id)

    def create_product(self, product: ProductservicesProducts) -> ProductservicesProducts:
        return self.products_repo.save(product)

    def get_product(self, product_id: int) -> Optional[ProductservicesProducts]:
        return self.products_repo.get_by_id(product_id)

    def get_products_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return self.products_repo.get_by_category(category_id)

    def add_question(self, question: ProductservicesProductQuestions) -> ProductservicesProductQuestions:
        return self.questions_repo.save(question)

    def get_product_questions(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return self.questions_repo.get_by_product(product_id)

    def add_review(self, review: ProductservicesProductReviews) -> ProductservicesProductReviews:
        return self.reviews_repo.save(review)

    def get_product_reviews(self, product_id: int) -> List[ProductservicesProductReviews]:
        return self.reviews_repo.get_by_product(product_id)


class InventoryService:
    def __init__(self):
        self.warehouse_repo = InventoryservicesWarehouseRepository()
        self.rack_repo = InventoryservicesRackAndShelvesAndFloorRepository()
        self.inventory_repo = InventoryservicesInventoryRepository()
        self.inventory_log_repo = InventoryservicesInventoryLogRepository()

    def create_warehouse(self, warehouse: InventoryservicesWarehouse) -> InventoryservicesWarehouse:
        return self.warehouse_repo.save(warehouse)

    def get_warehouse(self, warehouse_id: int) -> Optional[InventoryservicesWarehouse]:
        return self.warehouse_repo.get_by_id(warehouse_id)

    def create_rack(self, rack: InventoryservicesRackAndShelvesAndFloor) -> InventoryservicesRackAndShelvesAndFloor:
        return self.rack_repo.save(rack)

    def get_racks_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return self.rack_repo.get_by_warehouse(warehouse_id)

    def add_inventory(self, inventory: InventoryservicesInventory) -> InventoryservicesInventory:
        return self.inventory_repo.save(inventory)

    def get_inventory(self, inventory_id: int) -> Optional[InventoryservicesInventory]:
        return self.inventory_repo.get_by_id(inventory_id)

    def get_inventory_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return self.inventory_repo.get_by_product(product_id)

    def get_inventory_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return self.inventory_repo.get_by_warehouse(warehouse_id)

    def log_inventory_change(self, log: InventoryservicesInventoryLog) -> InventoryservicesInventoryLog:
        return self.inventory_log_repo.save(log)

    def get_inventory_logs(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return self.inventory_log_repo.get_by_inventory(inventory_id)


class PurchaseOrderService:
    def __init__(self):
        self.po_repo = OrderservicePurchaseOrderRepository()
        self.po_items_repo = OrderservicePurchaseOrderItemsRepository()
        self.po_logs_repo = OrderservicePurchaseOrderLogsRepository()
        self.po_inwarded_log_repo = OrderservicePurchaseOrderInwardedLogRepository()
        self.po_item_inwarded_log_repo = OrderservicePurchaseOrderItemInwardedLogRepository()

    def create_purchase_order(self, po: OrderservicePurchaseOrder) -> OrderservicePurchaseOrder:
        return self.po_repo.save(po)

    def get_purchase_order(self, po_id: int) -> Optional[OrderservicePurchaseOrder]:
        return self.po_repo.get_by_id(po_id)

    def get_purchase_orders_by_status(self, status: str) -> List[OrderservicePurchaseOrder]:
        return self.po_repo.get_by_status(status)

    def add_purchase_order_item(self, item: OrderservicePurchaseOrderItems) -> OrderservicePurchaseOrderItems:
        return self.po_items_repo.save(item)

    def get_purchase_order_items(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return self.po_items_repo.get_by_po(po_id)

    def log_purchase_order(self, log: OrderservicePurchaseOrderLogs) -> OrderservicePurchaseOrderLogs:
        return self.po_logs_repo.save(log)

    def get_purchase_order_logs(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return self.po_logs_repo.get_by_po(po_id)

    def log_inward(self, log: OrderservicePurchaseOrderInwardedLog) -> OrderservicePurchaseOrderInwardedLog:
        return self.po_inwarded_log_repo.save(log)

    def get_inward_logs(self, po_id: int) -> List[OrderservicePurchaseOrderInwardedLog]:
        return self.po_inwarded_log_repo.get_by_po(po_id)

    def log_item_inward(self, log: OrderservicePurchaseOrderItemInwardedLog) -> OrderservicePurchaseOrderItemInwardedLog:
        return self.po_item_inwarded_log_repo.save(log)

    def get_item_inward_logs(self, po_item_id: int) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return self.po_item_inwarded_log_repo.get_by_po_item(po_item_id)

    def approve_purchase_order(self, po_id: int, approved_by_user_id: int, approved_at: datetime) -> Optional[OrderservicePurchaseOrder]:
        po = self.po_repo.get_by_id(po_id)
        if po:
            po.status = "approved"
            po.approved_by_user_id_id = approved_by_user_id
            po.approved_at = approved_at
            self.po_repo.save(po)
        return po

    def cancel_purchase_order(self, po_id: int, cancelled_by_user_id: int, cancelled_at: datetime, reason: str) -> Optional[OrderservicePurchaseOrder]:
        po = self.po_repo.get_by_id(po_id)
        if po:
            po.status = "cancelled"
            po.cancelled_by_user_id_id = cancelled_by_user_id
            po.cancelled_at = cancelled_at
            po.cancelled_reason = reason
            self.po_repo.save(po)
        return po

    def receive_purchase_order(self, po_id: int, received_by_user_id: int, received_at: datetime) -> Optional[OrderservicePurchaseOrder]:
        po = self.po_repo.get_by_id(po_id)
        if po:
            po.status = "received"
            po.received_by_user_id_id = received_by_user_id
            po.received_at = received_at
            self.po_repo.save(po)
        return po


class SalesOrderService:
    def __init__(self):
        self.so_repo = OrderserviceSalesOrderRepository()
        self.so_items_repo = OrderserviceSalesOrderOrderItemsRepository()
        self.so_logs_repo = OrderserviceSalesOrderLogsRepository()
        self.so_outwarded_log_repo = OrderserviceSalesOrderOutwardedLogRepository()
        self.so_item_outwarded_log_repo = OrderserviceSalesOrderItemOutwardedLogRepository()

    def create_sales_order(self, so: OrderserviceSalesOrder) -> OrderserviceSalesOrder:
        return self.so_repo.save(so)

    def get_sales_order(self, so_id: int) -> Optional[OrderserviceSalesOrder]:
        return self.so_repo.get_by_id(so_id)

    def get_sales_orders_by_status(self, status: str) -> List[OrderserviceSalesOrder]:
        return self.so_repo.get_by_status(status)

    def get_sales_orders_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return self.so_repo.get_by_customer(customer_id)

    def add_sales_order_item(self, item: OrderserviceSalesOrderOrderItems) -> OrderserviceSalesOrderOrderItems:
        return self.so_items_repo.save(item)

    def get_sales_order_items(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return self.so_items_repo.get_by_so(so_id)

    def log_sales_order(self, log: OrderserviceSalesOrderLogs) -> OrderserviceSalesOrderLogs:
        return self.so_logs_repo.save(log)

    def get_sales_order_logs(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return self.so_logs_repo.get_by_so(so_id)

    def log_outward(self, log: OrderserviceSalesOrderOutwardedLog) -> OrderserviceSalesOrderOutwardedLog:
        return self.so_outwarded_log_repo.save(log)

    def get_outward_logs(self, so_id: int) -> List[OrderserviceSalesOrderOutwardedLog]:
        return self.so_outwarded_log_repo.get_by_so(so_id)

    def log_item_outward(self, log: OrderserviceSalesOrderItemOutwardedLog) -> OrderserviceSalesOrderItemOutwardedLog:
        return self.so_item_outwarded_log_repo.save(log)

    def get_item_outward_logs(self, so_item_id: int) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return self.so_item_outwarded_log_repo.get_by_so_item(so_item_id)

    def approve_sales_order(self, so_id: int, approved_by_user_id: int, approved_at: datetime) -> Optional[OrderserviceSalesOrder]:
        so = self.so_repo.get_by_id(so_id)
        if so:
            so.status = "approved"
            so.approved_by_user_id_id = approved_by_user_id
            so.approved_at = approved_at
            self.so_repo.save(so)
        return so

    def cancel_sales_order(self, so_id: int, cancelled_by_user_id: int, cancelled_at: datetime, reason: str) -> Optional[OrderserviceSalesOrder]:
        so = self.so_repo.get_by_id(so_id)
        if so:
            so.status = "cancelled"
            so.cancelled_by_user_id_id = cancelled_by_user_id
            so.cancelled_at = cancelled_at
            so.cancelled_reason = reason
            self.so_repo.save(so)
        return so


# ============================================================
#  APPLICATION FACADE
# ============================================================

class EcommerceApplication:
    def __init__(self):
        self.user_service = UserService()
        self.product_service = ProductService()
        self.inventory_service = InventoryService()
        self.purchase_order_service = PurchaseOrderService()
        self.sales_order_service = SalesOrderService()
        self.django_admin_log_repo = DjangoAdminLogRepository()
        self.django_migrations_repo = DjangoMigrationsRepository()
        self.django_session_repo = DjangoSessionRepository()
        self.django_content_type_repo = DjangoContentTypeRepository()
        self.auth_group_repo = AuthGroupRepository()
        self.auth_permission_repo = AuthPermissionRepository()
        self.auth_group_permissions_repo = AuthGroupPermissionsRepository()

    def get_user_service(self) -> UserService:
        return self.user_service

    def get_product_service(self) -> ProductService:
        return self.product_service

    def get_inventory_service(self) -> InventoryService:
        return self.inventory_service

    def get_purchase_order_service(self) -> PurchaseOrderService:
        return self.purchase_order_service

    def get_sales_order_service(self) -> SalesOrderService:
        return self.sales_order_service