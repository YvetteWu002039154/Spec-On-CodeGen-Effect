from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


# ============================================================
#  DJANGO AUTH / FRAMEWORK ENTITIES
# ============================================================

class DjangoContentType:
    def __init__(
        self,
        id: int,
        app_label: str,
        model: str,
    ) -> None:
        self.id = id
        self.app_label = app_label
        self.model = model

    def __repr__(self) -> str:
        return f"DjangoContentType(id={self.id}, app_label={self.app_label!r}, model={self.model!r})"


class DjangoMigrations:
    def __init__(
        self,
        id: int,
        app: str,
        name: str,
        applied: datetime,
    ) -> None:
        self.id = id
        self.app = app
        self.name = name
        self.applied = applied

    def __repr__(self) -> str:
        return f"DjangoMigrations(id={self.id}, app={self.app!r}, name={self.name!r})"


class DjangoSession:
    def __init__(
        self,
        session_key: str,
        session_data: str,
        expire_date: datetime,
    ) -> None:
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date

    def __repr__(self) -> str:
        return f"DjangoSession(session_key={self.session_key!r})"


class AuthPermission:
    def __init__(
        self,
        id: int,
        name: str,
        codename: str,
        content_type: DjangoContentType,
    ) -> None:
        self.id = id
        self.name = name
        self.codename = codename
        self.content_type = content_type

    def __repr__(self) -> str:
        return f"AuthPermission(id={self.id}, name={self.name!r})"


class AuthGroup:
    def __init__(
        self,
        id: int,
        name: str,
    ) -> None:
        self.id = id
        self.name = name
        self.permissions: List[AuthPermission] = []

    def __repr__(self) -> str:
        return f"AuthGroup(id={self.id}, name={self.name!r})"


class AuthGroupPermissions:
    def __init__(
        self,
        id: int,
        group: AuthGroup,
        permission: AuthPermission,
    ) -> None:
        self.id = id
        self.group = group
        self.permission = permission

    def __repr__(self) -> str:
        return f"AuthGroupPermissions(id={self.id})"


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
        domain_user: Optional["UserservicesUsers"] = None,
    ) -> None:
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
        self.social_media_links: Dict[str, Any] = social_media_links or {}
        self.addition_details: Dict[str, Any] = addition_details or {}
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
        self.domain_user = domain_user

    def __repr__(self) -> str:
        return f"UserservicesUsers(id={self.id}, username={self.username!r})"


class UserservicesUsersGroups:
    def __init__(
        self,
        id: int,
        user: UserservicesUsers,
        group: AuthGroup,
    ) -> None:
        self.id = id
        self.user = user
        self.group = group

    def __repr__(self) -> str:
        return f"UserservicesUsersGroups(id={self.id})"


class UserservicesUsersUserPermissions:
    def __init__(
        self,
        id: int,
        user: UserservicesUsers,
        permission: AuthPermission,
    ) -> None:
        self.id = id
        self.user = user
        self.permission = permission

    def __repr__(self) -> str:
        return f"UserservicesUsersUserPermissions(id={self.id})"


class UserservicesUserShippingAddress:
    def __init__(
        self,
        id: int,
        user: UserservicesUsers,
        address_type: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        pincode: str = "",
        country: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.user = user
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"UserservicesUserShippingAddress(id={self.id})"


class UserservicesActivityLog:
    def __init__(
        self,
        id: int,
        user: UserservicesUsers,
        domain_user: UserservicesUsers,
        activity: str = "",
        activity_type: str = "",
        activity_date: Optional[datetime] = None,
        activity_ip: str = "",
        activity_device: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.user = user
        self.domain_user = domain_user
        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"UserservicesActivityLog(id={self.id})"


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
        parent: Optional["UserservicesModules"] = None,
    ) -> None:
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
        self.parent = parent

    def __repr__(self) -> str:
        return f"UserservicesModules(id={self.id}, module_name={self.module_name!r})"


class UserservicesUserPermissions:
    def __init__(
        self,
        id: int,
        user: UserservicesUsers,
        domain_user: UserservicesUsers,
        module: UserservicesModules,
        is_view: bool = False,
        is_add: bool = False,
        is_edit: bool = False,
        is_delete: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.user = user
        self.domain_user = domain_user
        self.module = module
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"UserservicesUserPermissions(id={self.id})"


# ============================================================
#  DJANGO ADMIN LOG
# ============================================================

class DjangoAdminLog:
    def __init__(
        self,
        id: int,
        user: UserservicesUsers,
        content_type: DjangoContentType,
        action_time: Optional[datetime] = None,
        object_id: str = "",
        object_repr: str = "",
        action_flag: int = 0,
        change_message: str = "",
    ) -> None:
        self.id = id
        self.user = user
        self.content_type = content_type
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message

    def __repr__(self) -> str:
        return f"DjangoAdminLog(id={self.id})"


# ============================================================
#  PRODUCT SERVICE
# ============================================================

class ProductservicesCategories:
    def __init__(
        self,
        id: int,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        name: str = "",
        image: str = "",
        description: str = "",
        display_order: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        parent: Optional["ProductservicesCategories"] = None,
    ) -> None:
        self.id = id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.parent = parent

    def __repr__(self) -> str:
        return f"ProductservicesCategories(id={self.id}, name={self.name!r})"


class ProductservicesProducts:
    def __init__(
        self,
        id: int,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        category: ProductservicesCategories,
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
    ) -> None:
        self.id = id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.category = category
        self.name = name
        self.image: Dict[str, Any] = image or {}
        self.description = description
        self.specifications: Dict[str, Any] = specifications or {}
        self.html_description = html_description
        self.highlights: Dict[str, Any] = highlights or {}
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
        self.seo_keywords: Dict[str, Any] = seo_keywords or {}
        self.addition_details: Dict[str, Any] = addition_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"ProductservicesProducts(id={self.id}, name={self.name!r})"


class ProductservicesProductQuestions:
    def __init__(
        self,
        id: int,
        product: ProductservicesProducts,
        domain_user: UserservicesUsers,
        question_user: UserservicesUsers,
        answer_user: Optional[UserservicesUsers] = None,
        question: str = "",
        answer: str = "",
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.product = product
        self.domain_user = domain_user
        self.question_user = question_user
        self.answer_user = answer_user
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"ProductservicesProductQuestions(id={self.id})"


class ProductservicesProductReviews:
    def __init__(
        self,
        id: int,
        product: ProductservicesProducts,
        domain_user: UserservicesUsers,
        review_user: UserservicesUsers,
        review_images: Optional[Dict[str, Any]] = None,
        rating: float = 0.0,
        reviews: str = "",
        status: str = "",
    ) -> None:
        self.id = id
        self.product = product
        self.domain_user = domain_user
        self.review_user = review_user
        self.review_images: Dict[str, Any] = review_images or {}
        self.rating = rating
        self.reviews = reviews
        self.status = status

    def __repr__(self) -> str:
        return f"ProductservicesProductReviews(id={self.id})"


# ============================================================
#  INVENTORY SERVICE
# ============================================================

class InventoryservicesWarehouse:
    def __init__(
        self,
        id: int,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        warehouse_manager: UserservicesUsers,
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
    ) -> None:
        self.id = id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse_manager = warehouse_manager
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
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"InventoryservicesWarehouse(id={self.id}, name={self.name!r})"


class InventoryservicesRackAndShelvesAndFloor:
    def __init__(
        self,
        id: int,
        warehouse: InventoryservicesWarehouse,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        name: str = "",
        rack: str = "",
        shelf: str = "",
        floor: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.warehouse = warehouse
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"InventoryservicesRackAndShelvesAndFloor(id={self.id}, name={self.name!r})"


# ============================================================
#  ORDER SERVICE - PURCHASE ORDER
# ============================================================

class OrderservicePurchaseOrder:
    def __init__(
        self,
        id: int,
        warehouse: InventoryservicesWarehouse,
        domain_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        supplier: UserservicesUsers,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        last_updated_by_user: Optional[UserservicesUsers] = None,
        received_by_user: Optional[UserservicesUsers] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
        po_code: str = "",
        po_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Decimal = Decimal("0.00"),
        paid_amount: Decimal = Decimal("0.00"),
        due_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_type: str = "",
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.warehouse = warehouse
        self.domain_user = domain_user
        self.created_by_user = created_by_user
        self.supplier = supplier
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.updated_by_user = updated_by_user
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
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at

    def __repr__(self) -> str:
        return f"OrderservicePurchaseOrder(id={self.id}, po_code={self.po_code!r})"


class OrderservicePurchaseOrderItems:
    def __init__(
        self,
        id: int,
        po: OrderservicePurchaseOrder,
        product: ProductservicesProducts,
        domain_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        last_updated_by_user: Optional[UserservicesUsers] = None,
        received_by_user: Optional[UserservicesUsers] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
        quantity_ordered: int = 0,
        quantity_received: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        buying_price: Decimal = Decimal("0.00"),
        selling_price: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        amount_paid: Decimal = Decimal("0.00"),
        amount_returned: Decimal = Decimal("0.00"),
        amount_cancelled: Decimal = Decimal("0.00"),
        amount_ordered: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        tax_amount: Decimal = Decimal("0.00"),
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
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
    ) -> None:
        self.id = id
        self.po = po
        self.product = product
        self.domain_user = domain_user
        self.created_by_user = created_by_user
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.updated_by_user = updated_by_user
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
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at

    def __repr__(self) -> str:
        return f"OrderservicePurchaseOrderItems(id={self.id})"


class OrderservicePurchaseOrderLogs:
    def __init__(
        self,
        id: int,
        po: OrderservicePurchaseOrder,
        domain_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        comment: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.po = po
        self.domain_user = domain_user
        self.created_by_user = created_by_user
        self.comment = comment
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"OrderservicePurchaseOrderLogs(id={self.id})"


class OrderservicePurchaseOrderInwardedLog:
    def __init__(
        self,
        id: int,
        po: OrderservicePurchaseOrder,
        domain_user: UserservicesUsers,
        inwarded_by_user: UserservicesUsers,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        inwarded_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.po = po
        self.domain_user = domain_user
        self.inwarded_by_user = inwarded_by_user
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"OrderservicePurchaseOrderInwardedLog(id={self.id})"


class OrderservicePurchaseOrderItemInwardedLog:
    def __init__(
        self,
        id: int,
        po_item: OrderservicePurchaseOrderItems,
        domain_user: UserservicesUsers,
        inwarded_quantity: int = 0,
        price: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.po_item = po_item
        self.domain_user = domain_user
        self.inwarded_quantity = inwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"OrderservicePurchaseOrderItemInwardedLog(id={self.id})"


# ============================================================
#  ORDER SERVICE - SALES ORDER
# ============================================================

class OrderserviceSalesOrder:
    def __init__(
        self,
        id: int,
        domain_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        customer: UserservicesUsers,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        last_updated_by_user: Optional[UserservicesUsers] = None,
        received_by_user: Optional[UserservicesUsers] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
        po: Optional[OrderservicePurchaseOrder] = None,
        product: Optional[ProductservicesProducts] = None,
        so_code: str = "",
        so_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Decimal = Decimal("0.00"),
        paid_amount: Decimal = Decimal("0.00"),
        due_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_type: str = "",
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.domain_user = domain_user
        self.created_by_user = created_by_user
        self.customer = customer
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.updated_by_user = updated_by_user
        self.po = po
        self.product = product
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
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at

    def __repr__(self) -> str:
        return f"OrderserviceSalesOrder(id={self.id}, so_code={self.so_code!r})"


class OrderserviceSalesOrderOrderItems:
    def __init__(
        self,
        id: int,
        so: OrderserviceSalesOrder,
        product: ProductservicesProducts,
        domain_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        approved_by_user: Optional[UserservicesUsers] = None,
        cancelled_by_user: Optional[UserservicesUsers] = None,
        returned_by_user: Optional[UserservicesUsers] = None,
        shipped_by_user: Optional[UserservicesUsers] = None,
        updated_by_user: Optional[UserservicesUsers] = None,
        quantity_ordered: int = 0,
        quantity_delivered: int = 0,
        quantity_shipped: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        purchase_price: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        amount_paid: Decimal = Decimal("0.00"),
        amount_returned: Decimal = Decimal("0.00"),
        amount_cancelled: Decimal = Decimal("0.00"),
        amount_ordered: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        tax_amount: Decimal = Decimal("0.00"),
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_type: str = "",
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        shipped_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.so = so
        self.product = product
        self.domain_user = domain_user
        self.created_by_user = created_by_user
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.returned_by_user = returned_by_user
        self.shipped_by_user = shipped_by_user
        self.updated_by_user = updated_by_user
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
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.shipped_at = shipped_at
        self.returned_at = returned_at

    def __repr__(self) -> str:
        return f"OrderserviceSalesOrderOrderItems(id={self.id})"


class OrderserviceSalesOrderLogs:
    def __init__(
        self,
        id: int,
        so: OrderserviceSalesOrder,
        domain_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        comment: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.so = so
        self.domain_user = domain_user
        self.created_by_user = created_by_user
        self.comment = comment
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"OrderserviceSalesOrderLogs(id={self.id})"


class OrderserviceSalesOrderOutwardedLog:
    def __init__(
        self,
        id: int,
        so: OrderserviceSalesOrder,
        domain_user: UserservicesUsers,
        outwarded_by_user: UserservicesUsers,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        outwared_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.so = so
        self.domain_user = domain_user
        self.outwarded_by_user = outwarded_by_user
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"OrderserviceSalesOrderOutwardedLog(id={self.id})"


class OrderserviceSalesOrderItemOutwardedLog:
    def __init__(
        self,
        id: int,
        so_item: OrderserviceSalesOrderOrderItems,
        domain_user: UserservicesUsers,
        outwarded_quantity: int = 0,
        price: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.so_item = so_item
        self.domain_user = domain_user
        self.outwarded_quantity = outwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"OrderserviceSalesOrderItemOutwardedLog(id={self.id})"


# ============================================================
#  INVENTORY SERVICE - INVENTORY & LOG
# ============================================================

class InventoryservicesInventory:
    def __init__(
        self,
        id: int,
        product: ProductservicesProducts,
        warehouse: InventoryservicesWarehouse,
        rack_shelf_floor: InventoryservicesRackAndShelvesAndFloor,
        purchase_order: OrderservicePurchaseOrder,
        purchase_order_item: OrderservicePurchaseOrderItems,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        purchase_order_item_inwarded_item: Optional[OrderservicePurchaseOrderItemInwardedLog] = None,
        quantity: int = 0,
        mrp: str = "",
        batch_number: str = "",
        discount_type: str = "",
        discount_amount: float = 0.0,
        sr_no: str = "",
        mfg_date: Optional[datetime] = None,
        uom: str = "",
        ptr: str = "",
        received_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        quantity_inwarded: int = 0,
        buy_price: Decimal = Decimal("0.00"),
        sell_price: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        stock_status: str = "",
        inward_type: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.product = product
        self.warehouse = warehouse
        self.rack_shelf_floor = rack_shelf_floor
        self.purchase_order = purchase_order
        self.purchase_order_item = purchase_order_item
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.purchase_order_item_inwarded_item = purchase_order_item_inwarded_item
        self.quantity = quantity
        self.mrp = mrp
        self.batch_number = batch_number
        self.discount_type = discount_type
        self.discount_amount = discount_amount
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
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"InventoryservicesInventory(id={self.id})"


class InventoryservicesInventoryLog:
    def __init__(
        self,
        id: int,
        inventory: InventoryservicesInventory,
        warehouse: InventoryservicesWarehouse,
        rack_shelf_floor: InventoryservicesRackAndShelvesAndFloor,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        po: Optional[OrderservicePurchaseOrder] = None,
        so: Optional[OrderserviceSalesOrder] = None,
        quantity: int = 0,
        status: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.inventory = inventory
        self.warehouse = warehouse
        self.rack_shelf_floor = rack_shelf_floor
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.po = po
        self.so = so
        self.quantity = quantity
        self.status = status
        self.additional_details: Dict[str, Any] = additional_details or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"InventoryservicesInventoryLog(id={self.id})"


# ============================================================
#  SIMPLE IN-MEMORY REPOSITORY (generic)
# ============================================================

class Repository:
    def __init__(self) -> None:
        self._store: Dict[int, Any] = {}

    def save(self, entity: Any) -> None:
        self._store[entity.id] = entity

    def get(self, id: int) -> Optional[Any]:
        return self._store.get(id)

    def all(self) -> List[Any]:
        return list(self._store.values())

    def delete(self, id: int) -> bool:
        if id in self._store:
            del self._store[id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._store)


# ============================================================
#  TYPED REPOSITORIES
# ============================================================

class DjangoContentTypeRepository(Repository):
    def get(self, id: int) -> Optional[DjangoContentType]:
        return self._store.get(id)

    def all(self) -> List[DjangoContentType]:
        return list(self._store.values())


class DjangoMigrationsRepository(Repository):
    def get(self, id: int) -> Optional[DjangoMigrations]:
        return self._store.get(id)

    def all(self) -> List[DjangoMigrations]:
        return list(self._store.values())


class DjangoSessionRepository:
    def __init__(self) -> None:
        self._store: Dict[str, DjangoSession] = {}

    def save(self, session: DjangoSession) -> None:
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


class AuthPermissionRepository(Repository):
    def get(self, id: int) -> Optional[AuthPermission]:
        return self._store.get(id)

    def all(self) -> List[AuthPermission]:
        return list(self._store.values())


class AuthGroupRepository(Repository):
    def get(self, id: int) -> Optional[AuthGroup]:
        return self._store.get(id)

    def all(self) -> List[AuthGroup]:
        return list(self._store.values())


class AuthGroupPermissionsRepository(Repository):
    def get(self, id: int) -> Optional[AuthGroupPermissions]:
        return self._store.get(id)

    def all(self) -> List[AuthGroupPermissions]:
        return list(self._store.values())


class UserservicesUsersRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesUsers]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsers]:
        return list(self._store.values())

    def find_by_email(self, email: str) -> Optional[UserservicesUsers]:
        for user in self._store.values():
            if user.email == email:
                return user
        return None

    def find_by_username(self, username: str) -> Optional[UserservicesUsers]:
        for user in self._store.values():
            if user.username == username:
                return user
        return None


class UserservicesUsersGroupsRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesUsersGroups]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsersGroups]:
        return list(self._store.values())

    def find_by_user(self, user_id: int) -> List[UserservicesUsersGroups]:
        return [ug for ug in self._store.values() if ug.user.id == user_id]


class UserservicesUsersUserPermissionsRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesUsersUserPermissions]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsersUserPermissions]:
        return list(self._store.values())

    def find_by_user(self, user_id: int) -> List[UserservicesUsersUserPermissions]:
        return [up for up in self._store.values() if up.user.id == user_id]


class UserservicesUserShippingAddressRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesUserShippingAddress]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUserShippingAddress]:
        return list(self._store.values())

    def find_by_user(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [a for a in self._store.values() if a.user.id == user_id]


class UserservicesActivityLogRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesActivityLog]:
        return self._store.get(id)

    def all(self) -> List[UserservicesActivityLog]:
        return list(self._store.values())

    def find_by_user(self, user_id: int) -> List[UserservicesActivityLog]:
        return [log for log in self._store.values() if log.user.id == user_id]


class UserservicesModulesRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesModules]:
        return self._store.get(id)

    def all(self) -> List[UserservicesModules]:
        return list(self._store.values())

    def find_children(self, parent_id: int) -> List[UserservicesModules]:
        return [m for m in self._store.values() if m.parent and m.parent.id == parent_id]


class UserservicesUserPermissionsRepository(Repository):
    def get(self, id: int) -> Optional[UserservicesUserPermissions]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUserPermissions]:
        return list(self._store.values())

    def find_by_user(self, user_id: int) -> List[UserservicesUserPermissions]:
        return [p for p in self._store.values() if p.user.id == user_id]


class DjangoAdminLogRepository(Repository):
    def get(self, id: int) -> Optional[DjangoAdminLog]:
        return self._store.get(id)

    def all(self) -> List[DjangoAdminLog]:
        return list(self._store.values())

    def find_by_user(self, user_id: int) -> List[DjangoAdminLog]:
        return [log for log in self._store.values() if log.user.id == user_id]


class ProductservicesCategoriesRepository(Repository):
    def get(self, id: int) -> Optional[ProductservicesCategories]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesCategories]:
        return list(self._store.values())

    def find_children(self, parent_id: int) -> List[ProductservicesCategories]:
        return [c for c in self._store.values() if c.parent and c.parent.id == parent_id]

    def find_root_categories(self) -> List[ProductservicesCategories]:
        return [c for c in self._store.values() if c.parent is None]


class ProductservicesProductsRepository(Repository):
    def get(self, id: int) -> Optional[ProductservicesProducts]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProducts]:
        return list(self._store.values())

    def find_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [p for p in self._store.values() if p.category.id == category_id]

    def find_by_sku(self, sku: str) -> Optional[ProductservicesProducts]:
        for p in self._store.values():
            if p.sku == sku:
                return p
        return None


class ProductservicesProductQuestionsRepository(Repository):
    def get(self, id: int) -> Optional[ProductservicesProductQuestions]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProductQuestions]:
        return list(self._store.values())

    def find_by_product(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [q for q in self._store.values() if q.product.id == product_id]


class ProductservicesProductReviewsRepository(Repository):
    def get(self, id: int) -> Optional[ProductservicesProductReviews]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProductReviews]:
        return list(self._store.values())

    def find_by_product(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [r for r in self._store.values() if r.product.id == product_id]


class InventoryservicesWarehouseRepository(Repository):
    def get(self, id: int) -> Optional[InventoryservicesWarehouse]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesWarehouse]:
        return list(self._store.values())

    def find_by_status(self, status: str) -> List[InventoryservicesWarehouse]:
        return [w for w in self._store.values() if w.status == status]


class InventoryservicesRackAndShelvesAndFloorRepository(Repository):
    def get(self, id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return list(self._store.values())

    def find_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return [r for r in self._store.values() if r.warehouse.id == warehouse_id]


class InventoryservicesInventoryRepository(Repository):
    def get(self, id: int) -> Optional[InventoryservicesInventory]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesInventory]:
        return list(self._store.values())

    def find_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.product.id == product_id]

    def find_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.warehouse.id == warehouse_id]

    def find_by_stock_status(self, stock_status: str) -> List[InventoryservicesInventory]:
        return [i for i in self._store.values() if i.stock_status == stock_status]


class InventoryservicesInventoryLogRepository(Repository):
    def get(self, id: int) -> Optional[InventoryservicesInventoryLog]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesInventoryLog]:
        return list(self._store.values())

    def find_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [log for log in self._store.values() if log.inventory.id == inventory_id]

    def find_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventoryLog]:
        return [log for log in self._store.values() if log.warehouse.id == warehouse_id]


class OrderservicePurchaseOrderRepository(Repository):
    def get(self, id: int) -> Optional[OrderservicePurchaseOrder]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrder]:
        return list(self._store.values())

    def find_by_status(self, status: str) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.status == status]

    def find_by_supplier(self, supplier_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.supplier.id == supplier_id]

    def find_by_warehouse(self, warehouse_id: int) -> List[OrderservicePurchaseOrder]:
        return [po for po in self._store.values() if po.warehouse.id == warehouse_id]


class OrderservicePurchaseOrderItemsRepository(Repository):
    def get(self, id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderItems]:
        return list(self._store.values())

    def find_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [item for item in self._store.values() if item.po.id == po_id]

    def find_by_product(self, product_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [item for item in self._store.values() if item.product.id == product_id]


class OrderservicePurchaseOrderLogsRepository(Repository):
    def get(self, id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderLogs]:
        return list(self._store.values())

    def find_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return [log for log in self._store.values() if log.po.id == po_id]


class OrderservicePurchaseOrderInwardedLogRepository(Repository):
    def get(self, id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderInwardedLog]:
        return list(self._store.values())

    def find_by_po(self, po_id: int) -> List[OrderservicePurchaseOrderInwardedLog]:
        return [log for log in self._store.values() if log.po.id == po_id]


class OrderservicePurchaseOrderItemInwardedLogRepository(Repository):
    def get(self, id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return list(self._store.values())

    def find_by_po_item(self, po_item_id: int) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return [log for log in self._store.values() if log.po_item.id == po_item_id]


class OrderserviceSalesOrderRepository(Repository):
    def get(self, id: int) -> Optional[OrderserviceSalesOrder]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrder]:
        return list(self._store.values())

    def find_by_status(self, status: str) -> List[OrderserviceSalesOrder]:
        return [so for so in self._store.values() if so.status == status]

    def find_by_customer(self, customer_id: int) -> List[OrderserviceSalesOrder]:
        return [so for so in self._store.values() if so.customer.id == customer_id]


class OrderserviceSalesOrderOrderItemsRepository(Repository):
    def get(self, id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderOrderItems]:
        return list(self._store.values())

    def find_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [item for item in self._store.values() if item.so.id == so_id]

    def find_by_product(self, product_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [item for item in self._store.values() if item.product.id == product_id]


class OrderserviceSalesOrderLogsRepository(Repository):
    def get(self, id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderLogs]:
        return list(self._store.values())

    def find_by_so(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return [log for log in self._store.values() if log.so.id == so_id]


class OrderserviceSalesOrderOutwardedLogRepository(Repository):
    def get(self, id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderOutwardedLog]:
        return list(self._store.values())

    def find_by_so(self, so_id: int) -> List[OrderserviceSalesOrderOutwardedLog]:
        return [log for log in self._store.values() if log.so.id == so_id]


class OrderserviceSalesOrderItemOutwardedLogRepository(Repository):
    def get(self, id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return list(self._store.values())

    def find_by_so_item(self, so_item_id: int) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return [log for log in self._store.values() if log.so_item.id == so_item_id]


# ============================================================
#  UNIT OF WORK / DATABASE CONTEXT
# ============================================================

class EcommerceDatabase:
    def __init__(self) -> None:
        self.django_content_types = DjangoContentTypeRepository()
        self.django_migrations = DjangoMigrationsRepository()
        self.django_sessions = DjangoSessionRepository()
        self.django_admin_logs = DjangoAdminLogRepository()
        self.auth_permissions = AuthPermissionRepository()
        self.auth_groups = AuthGroupRepository()
        self.auth_group_permissions = AuthGroupPermissionsRepository()
        self.users = UserservicesUsersRepository()
        self.users_groups = UserservicesUsersGroupsRepository()
        self.users_user_permissions = UserservicesUsersUserPermissionsRepository()
        self.user_shipping_addresses = UserservicesUserShippingAddressRepository()
        self.activity_logs = UserservicesActivityLogRepository()
        self.modules = UserservicesModulesRepository()
        self.user_permissions = UserservicesUserPermissionsRepository()
        self.categories = ProductservicesCategoriesRepository()
        self.products = ProductservicesProductsRepository()
        self.product_questions = ProductservicesProductQuestionsRepository()
        self.product_reviews = ProductservicesProductReviewsRepository()
        self.warehouses = InventoryservicesWarehouseRepository()
        self.rack_shelves_floors = InventoryservicesRackAndShelvesAndFloorRepository()
        self.inventories = InventoryservicesInventoryRepository()
        self.inventory_logs = InventoryservicesInventoryLogRepository()
        self.purchase_orders = OrderservicePurchaseOrderRepository()
        self.purchase_order_items = OrderservicePurchaseOrderItemsRepository()
        self.purchase_order_logs = OrderservicePurchaseOrderLogsRepository()
        self.purchase_order_inwarded_logs = OrderservicePurchaseOrderInwardedLogRepository()
        self.purchase_order_item_inwarded_logs = OrderservicePurchaseOrderItemInwardedLogRepository()
        self.sales_orders = OrderserviceSalesOrderRepository()
        self.sales_order_items = OrderserviceSalesOrderOrderItemsRepository()
        self.sales_order_logs = OrderserviceSalesOrderLogsRepository()
        self.sales_order_outwarded_logs = OrderserviceSalesOrderOutwardedLogRepository()
        self.sales_order_item_outwarded_logs = OrderserviceSalesOrderItemOutwardedLogRepository()

    def __repr__(self) -> str:
        return "EcommerceDatabase()"