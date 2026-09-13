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
        return f"<DjangoContentType id={self.id} {self.app_label}.{self.model}>"


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
        return f"<DjangoMigrations id={self.id} {self.app}.{self.name}>"


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
        return f"<DjangoSession session_key={self.session_key}>"


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
        return f"<AuthPermission id={self.id} {self.codename}>"


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
        return f"<AuthGroup id={self.id} {self.name}>"


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
        return f"<AuthGroupPermissions id={self.id}>"


# ============================================================
#  USER SERVICE
# ============================================================

class UserservicesUsers:
    def __init__(
        self,
        id: int,
        is_superuser: bool,
        first_name: str,
        last_name: str,
        is_staff: bool,
        is_active: bool,
        date_joined: datetime,
        name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        country: str,
        profile_pic: Optional[str],
        account_status: str,
        role: str,
        dob: Optional[date],
        username: str,
        password: str,
        social_media_links: Optional[Dict[str, Any]],
        addition_details: Optional[Dict[str, Any]],
        language: str,
        department: str,
        designation: str,
        time_zone: str,
        last_login: Optional[datetime],
        last_device: Optional[str],
        last_ip: Optional[str],
        currency: str,
        domain_name: str,
        plan_type: str,
        created_at: datetime,
        updated_at: datetime,
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
        self.social_media_links = social_media_links
        self.addition_details = addition_details
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
        return f"<UserservicesUsers id={self.id} username={self.username}>"


class UserservicesUserShippingAddress:
    def __init__(
        self,
        id: int,
        address_type: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        country: str,
        created_at: datetime,
        updated_at: datetime,
        user: UserservicesUsers,
    ) -> None:
        self.id = id
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.created_at = created_at
        self.updated_at = updated_at
        self.user = user

    def __repr__(self) -> str:
        return f"<UserservicesUserShippingAddress id={self.id}>"


class UserservicesActivityLog:
    def __init__(
        self,
        id: int,
        activity: str,
        activity_type: str,
        activity_date: datetime,
        activity_ip: str,
        activity_device: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: UserservicesUsers,
        user: UserservicesUsers,
    ) -> None:
        self.id = id
        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.user = user

    def __repr__(self) -> str:
        return f"<UserservicesActivityLog id={self.id}>"


class UserservicesModules:
    def __init__(
        self,
        id: int,
        module_name: str,
        module_icon: Optional[str],
        is_menu: bool,
        is_active: bool,
        module_url: Optional[str],
        display_order: int,
        module_description: Optional[str],
        created_at: datetime,
        updated_at: datetime,
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
        return f"<UserservicesModules id={self.id} {self.module_name}>"


class UserservicesUserPermissions:
    def __init__(
        self,
        id: int,
        is_view: bool,
        is_add: bool,
        is_edit: bool,
        is_delete: bool,
        created_at: datetime,
        updated_at: datetime,
        module: UserservicesModules,
        domain_user: UserservicesUsers,
        user: UserservicesUsers,
    ) -> None:
        self.id = id
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = created_at
        self.updated_at = updated_at
        self.module = module
        self.domain_user = domain_user
        self.user = user

    def __repr__(self) -> str:
        return f"<UserservicesUserPermissions id={self.id}>"


class UserservicesUsersGroups:
    def __init__(
        self,
        id: int,
        users: UserservicesUsers,
        group: AuthGroup,
    ) -> None:
        self.id = id
        self.users = users
        self.group = group

    def __repr__(self) -> str:
        return f"<UserservicesUsersGroups id={self.id}>"


class UserservicesUsersUserPermissions:
    def __init__(
        self,
        id: int,
        users: UserservicesUsers,
        permission: AuthPermission,
    ) -> None:
        self.id = id
        self.users = users
        self.permission = permission

    def __repr__(self) -> str:
        return f"<UserservicesUsersUserPermissions id={self.id}>"


class DjangoAdminLog:
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: Optional[str],
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type: DjangoContentType,
        user: UserservicesUsers,
    ) -> None:
        self.id = id
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type = content_type
        self.user = user

    def __repr__(self) -> str:
        return f"<DjangoAdminLog id={self.id}>"


# ============================================================
#  PRODUCT SERVICE
# ============================================================

class ProductservicesCategories:
    def __init__(
        self,
        id: int,
        name: str,
        image: Optional[str],
        description: Optional[str],
        display_order: int,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        parent: Optional["ProductservicesCategories"] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.parent = parent

    def __repr__(self) -> str:
        return f"<ProductservicesCategories id={self.id} {self.name}>"


class ProductservicesProducts:
    def __init__(
        self,
        id: int,
        name: str,
        image: Optional[Dict[str, Any]],
        description: Optional[str],
        specifications: Optional[Dict[str, Any]],
        html_description: Optional[str],
        highlights: Optional[Dict[str, Any]],
        sku: str,
        initial_buying_price: float,
        initial_selling_price: float,
        weight: float,
        dimensions: Optional[str],
        uom: Optional[str],
        color: Optional[str],
        tax_percentage: float,
        brand: Optional[str],
        brand_model: Optional[str],
        status: str,
        seo_title: Optional[str],
        seo_description: Optional[str],
        seo_keywords: Optional[Dict[str, Any]],
        addition_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user: UserservicesUsers,
        category: ProductservicesCategories,
        domain_user: UserservicesUsers,
    ) -> None:
        self.id = id
        self.name = name
        self.image = image
        self.description = description
        self.specifications = specifications
        self.html_description = html_description
        self.highlights = highlights
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
        self.seo_keywords = seo_keywords
        self.addition_details = addition_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.category = category
        self.domain_user = domain_user

    def __repr__(self) -> str:
        return f"<ProductservicesProducts id={self.id} {self.name}>"


class ProductservicesProductQuestions:
    def __init__(
        self,
        id: int,
        question: str,
        answer: Optional[str],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        answer_user: Optional[UserservicesUsers],
        domain_user: UserservicesUsers,
        question_user: UserservicesUsers,
        product: ProductservicesProducts,
    ) -> None:
        self.id = id
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.answer_user = answer_user
        self.domain_user = domain_user
        self.question_user = question_user
        self.product = product

    def __repr__(self) -> str:
        return f"<ProductservicesProductQuestions id={self.id}>"


class ProductservicesProductReviews:
    def __init__(
        self,
        id: int,
        review_images: Optional[Dict[str, Any]],
        rating: float,
        reviews: Optional[str],
        status: str,
        domain_user: UserservicesUsers,
        review_user: UserservicesUsers,
        product: ProductservicesProducts,
    ) -> None:
        self.id = id
        self.review_images = review_images
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user = domain_user
        self.review_user = review_user
        self.product = product

    def __repr__(self) -> str:
        return f"<ProductservicesProductReviews id={self.id}>"


# ============================================================
#  INVENTORY SERVICE
# ============================================================

class InventoryservicesWarehouse:
    def __init__(
        self,
        id: int,
        name: str,
        address: str,
        city: str,
        state: str,
        country: str,
        pincode: str,
        phone: str,
        email: str,
        status: str,
        size: Optional[str],
        capacity: Optional[str],
        warehouse_type: Optional[str],
        additional_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        warehouse_manager: UserservicesUsers,
    ) -> None:
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
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse_manager = warehouse_manager

    def __repr__(self) -> str:
        return f"<InventoryservicesWarehouse id={self.id} {self.name}>"


class InventoryservicesRackAndShelvesAndFloor:
    def __init__(
        self,
        id: int,
        name: str,
        rack: Optional[str],
        shelf: Optional[str],
        floor: Optional[str],
        additional_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        warehouse: InventoryservicesWarehouse,
    ) -> None:
        self.id = id
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f"<InventoryservicesRackAndShelvesAndFloor id={self.id} {self.name}>"


# ============================================================
#  ORDER SERVICE - PURCHASE
# ============================================================

class OrderservicePurchaseOrder:
    def __init__(
        self,
        id: int,
        po_code: str,
        po_date: datetime,
        expected_delivery_date: Optional[datetime],
        payment_terms: Optional[str],
        payment_status: str,
        total_amount: Decimal,
        paid_amount: Decimal,
        due_amount: Decimal,
        discount_amount: Decimal,
        discount_type: Optional[str],
        shipping_amount: Decimal,
        shipping_type: Optional[str],
        shipping_tax_percentage: Decimal,
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[UserservicesUsers],
        cancelled_by_user: Optional[UserservicesUsers],
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        last_updated_by_user: Optional[UserservicesUsers],
        received_by_user: Optional[UserservicesUsers],
        returned_by_user: Optional[UserservicesUsers],
        supplier: UserservicesUsers,
        updated_by_user: Optional[UserservicesUsers],
        warehouse: InventoryservicesWarehouse,
    ) -> None:
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.supplier = supplier
        self.updated_by_user = updated_by_user
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f"<OrderservicePurchaseOrder id={self.id} {self.po_code}>"


class OrderservicePurchaseOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: int,
        quantity_received: int,
        quantity_cancelled: int,
        quantity_returned: int,
        buying_price: Decimal,
        selling_price: Decimal,
        discount_amount: Decimal,
        amount_paid: Decimal,
        amount_returned: Decimal,
        amount_cancelled: Decimal,
        amount_ordered: Decimal,
        tax_percentage: Decimal,
        tax_amount: Decimal,
        shipping_tax_percentage: Decimal,
        shipping_amount: Decimal,
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        discount_type: Optional[str],
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[UserservicesUsers],
        cancelled_by_user: Optional[UserservicesUsers],
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        last_updated_by_user: Optional[UserservicesUsers],
        received_by_user: Optional[UserservicesUsers],
        returned_by_user: Optional[UserservicesUsers],
        po: OrderservicePurchaseOrder,
        product: ProductservicesProducts,
        updated_by_user: Optional[UserservicesUsers],
    ) -> None:
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.po = po
        self.product = product
        self.updated_by_user = updated_by_user

    def __repr__(self) -> str:
        return f"<OrderservicePurchaseOrderItems id={self.id}>"


class OrderservicePurchaseOrderLogs:
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        po: OrderservicePurchaseOrder,
    ) -> None:
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.po = po

    def __repr__(self) -> str:
        return f"<OrderservicePurchaseOrderLogs id={self.id}>"


class OrderservicePurchaseOrderInwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: Optional[str],
        invoice_number: Optional[str],
        notes: Optional[str],
        inwarded_at: Optional[datetime],
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: UserservicesUsers,
        inwarded_by_user: UserservicesUsers,
        po: OrderservicePurchaseOrder,
    ) -> None:
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.inwarded_by_user = inwarded_by_user
        self.po = po

    def __repr__(self) -> str:
        return f"<OrderservicePurchaseOrderInwardedLog id={self.id}>"


class OrderservicePurchaseOrderItemInwardedLog:
    def __init__(
        self,
        id: int,
        inwarded_quantity: int,
        price: Decimal,
        tax_percentage: Decimal,
        discount_amount: Decimal,
        discount_type: Optional[str],
        shipping_amount: Decimal,
        shipping_tax_percentage: Decimal,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: UserservicesUsers,
        po_item: OrderservicePurchaseOrderItems,
    ) -> None:
        self.id = id
        self.inwarded_quantity = inwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.po_item = po_item

    def __repr__(self) -> str:
        return f"<OrderservicePurchaseOrderItemInwardedLog id={self.id}>"


# ============================================================
#  ORDER SERVICE - SALES
# ============================================================

class OrderserviceSalesOrder:
    def __init__(
        self,
        id: int,
        so_code: str,
        so_date: datetime,
        expected_delivery_date: Optional[datetime],
        payment_terms: Optional[str],
        payment_status: str,
        total_amount: Decimal,
        paid_amount: Decimal,
        due_amount: Decimal,
        discount_amount: Decimal,
        discount_type: Optional[str],
        shipping_amount: Decimal,
        shipping_type: Optional[str],
        shipping_tax_percentage: Decimal,
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[UserservicesUsers],
        cancelled_by_user: Optional[UserservicesUsers],
        created_by_user: UserservicesUsers,
        customer: UserservicesUsers,
        domain_user: UserservicesUsers,
        last_updated_by_user: Optional[UserservicesUsers],
        received_by_user: Optional[UserservicesUsers],
        returned_by_user: Optional[UserservicesUsers],
        po: Optional[OrderservicePurchaseOrder],
        product: Optional[ProductservicesProducts],
        updated_by_user: Optional[UserservicesUsers],
    ) -> None:
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.customer = customer
        self.domain_user = domain_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.po = po
        self.product = product
        self.updated_by_user = updated_by_user

    def __repr__(self) -> str:
        return f"<OrderserviceSalesOrder id={self.id} {self.so_code}>"


class OrderserviceSalesOrderOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: int,
        quantity_delivered: int,
        quantity_shipped: int,
        quantity_cancelled: int,
        quantity_returned: int,
        purchase_price: Decimal,
        discount_amount: Decimal,
        discount_type: Optional[str],
        amount_paid: Decimal,
        amount_returned: Decimal,
        amount_cancelled: Decimal,
        amount_ordered: Decimal,
        tax_percentage: Decimal,
        tax_amount: Decimal,
        shipping_amount: Decimal,
        shipping_type: Optional[str],
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        shipped_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[UserservicesUsers],
        cancelled_by_user: Optional[UserservicesUsers],
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        product: ProductservicesProducts,
        returned_by_user: Optional[UserservicesUsers],
        shipped_by_user: Optional[UserservicesUsers],
        so: OrderserviceSalesOrder,
        updated_by_user: Optional[UserservicesUsers],
    ) -> None:
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.shipped_at = shipped_at
        self.returned_at = returned_at
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.product = product
        self.returned_by_user = returned_by_user
        self.shipped_by_user = shipped_by_user
        self.so = so
        self.updated_by_user = updated_by_user

    def __repr__(self) -> str:
        return f"<OrderserviceSalesOrderOrderItems id={self.id}>"


class OrderserviceSalesOrderLogs:
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        so: OrderserviceSalesOrder,
    ) -> None:
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.so = so

    def __repr__(self) -> str:
        return f"<OrderserviceSalesOrderLogs id={self.id}>"


class OrderserviceSalesOrderOutwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: Optional[str],
        invoice_number: Optional[str],
        notes: Optional[str],
        outwared_at: Optional[datetime],
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: UserservicesUsers,
        outwarded_by_user: UserservicesUsers,
        so: OrderserviceSalesOrder,
    ) -> None:
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.outwarded_by_user = outwarded_by_user
        self.so = so

    def __repr__(self) -> str:
        return f"<OrderserviceSalesOrderOutwardedLog id={self.id}>"


class OrderserviceSalesOrderItemOutwardedLog:
    def __init__(
        self,
        id: int,
        outwarded_quantity: int,
        price: Decimal,
        tax_percentage: Decimal,
        discount_amount: Decimal,
        discount_type: Optional[str],
        shipping_amount: Decimal,
        shipping_tax_percentage: Decimal,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: UserservicesUsers,
        so_item: OrderserviceSalesOrderOrderItems,
    ) -> None:
        self.id = id
        self.outwarded_quantity = outwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.so_item = so_item

    def __repr__(self) -> str:
        return f"<OrderserviceSalesOrderItemOutwardedLog id={self.id}>"


# ============================================================
#  INVENTORY SERVICE (continued - depends on order service)
# ============================================================

class InventoryservicesInventory:
    def __init__(
        self,
        id: int,
        quantity: int,
        mrp: Optional[str],
        batch_number: Optional[str],
        discount_type: Optional[str],
        discount_amount: float,
        sr_no: Optional[str],
        mfg_date: Optional[datetime],
        uom: Optional[str],
        ptr: Optional[str],
        received_date: Optional[datetime],
        expiry_date: Optional[datetime],
        quantity_inwarded: int,
        buy_price: Decimal,
        sell_price: Decimal,
        tax_percentage: Decimal,
        stock_status: str,
        inward_type: Optional[str],
        additional_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        product: ProductservicesProducts,
        purchase_order: OrderservicePurchaseOrder,
        purchase_order_item: OrderservicePurchaseOrderItems,
        purchase_order_item_inwarded_item: Optional[OrderservicePurchaseOrderItemInwardedLog],
        rack_shelf_floor: InventoryservicesRackAndShelvesAndFloor,
        warehouse: InventoryservicesWarehouse,
    ) -> None:
        self.id = id
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
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.product = product
        self.purchase_order = purchase_order
        self.purchase_order_item = purchase_order_item
        self.purchase_order_item_inwarded_item = purchase_order_item_inwarded_item
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f"<InventoryservicesInventory id={self.id}>"


class InventoryservicesInventoryLog:
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Optional[Dict[str, Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        inventory: InventoryservicesInventory,
        po: Optional[OrderservicePurchaseOrder],
        so: Optional[OrderserviceSalesOrder],
        rack_shelf_floor: InventoryservicesRackAndShelvesAndFloor,
        warehouse: InventoryservicesWarehouse,
    ) -> None:
        self.id = id
        self.quantity = quantity
        self.status = status
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.inventory = inventory
        self.po = po
        self.so = so
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f"<InventoryservicesInventoryLog id={self.id}>"


# ============================================================
#  REPOSITORY / REGISTRY CLASSES
# ============================================================

class UserservicesUsersRepository:
    def __init__(self) -> None:
        self._store: Dict[int, UserservicesUsers] = {}

    def add(self, user: UserservicesUsers) -> None:
        self._store[user.id] = user

    def get(self, id: int) -> Optional[UserservicesUsers]:
        return self._store.get(id)

    def all(self) -> List[UserservicesUsers]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class ProductservicesProductsRepository:
    def __init__(self) -> None:
        self._store: Dict[int, ProductservicesProducts] = {}

    def add(self, product: ProductservicesProducts) -> None:
        self._store[product.id] = product

    def get(self, id: int) -> Optional[ProductservicesProducts]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesProducts]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class ProductservicesCategoriesRepository:
    def __init__(self) -> None:
        self._store: Dict[int, ProductservicesCategories] = {}

    def add(self, category: ProductservicesCategories) -> None:
        self._store[category.id] = category

    def get(self, id: int) -> Optional[ProductservicesCategories]:
        return self._store.get(id)

    def all(self) -> List[ProductservicesCategories]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class InventoryservicesWarehouseRepository:
    def __init__(self) -> None:
        self._store: Dict[int, InventoryservicesWarehouse] = {}

    def add(self, warehouse: InventoryservicesWarehouse) -> None:
        self._store[warehouse.id] = warehouse

    def get(self, id: int) -> Optional[InventoryservicesWarehouse]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesWarehouse]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class InventoryservicesRackAndShelvesAndFloorRepository:
    def __init__(self) -> None:
        self._store: Dict[int, InventoryservicesRackAndShelvesAndFloor] = {}

    def add(self, rack: InventoryservicesRackAndShelvesAndFloor) -> None:
        self._store[rack.id] = rack

    def get(self, id: int) -> Optional[InventoryservicesRackAndShelvesAndFloor]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesRackAndShelvesAndFloor]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class InventoryservicesInventoryRepository:
    def __init__(self) -> None:
        self._store: Dict[int, InventoryservicesInventory] = {}

    def add(self, inventory: InventoryservicesInventory) -> None:
        self._store[inventory.id] = inventory

    def get(self, id: int) -> Optional[InventoryservicesInventory]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesInventory]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class InventoryservicesInventoryLogRepository:
    def __init__(self) -> None:
        self._store: Dict[int, InventoryservicesInventoryLog] = {}

    def add(self, log: InventoryservicesInventoryLog) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[InventoryservicesInventoryLog]:
        return self._store.get(id)

    def all(self) -> List[InventoryservicesInventoryLog]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderservicePurchaseOrderRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderservicePurchaseOrder] = {}

    def add(self, po: OrderservicePurchaseOrder) -> None:
        self._store[po.id] = po

    def get(self, id: int) -> Optional[OrderservicePurchaseOrder]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrder]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderservicePurchaseOrderItemsRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderservicePurchaseOrderItems] = {}

    def add(self, item: OrderservicePurchaseOrderItems) -> None:
        self._store[item.id] = item

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderItems]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderItems]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderservicePurchaseOrderLogsRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderservicePurchaseOrderLogs] = {}

    def add(self, log: OrderservicePurchaseOrderLogs) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderLogs]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderLogs]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderservicePurchaseOrderInwardedLogRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderservicePurchaseOrderInwardedLog] = {}

    def add(self, log: OrderservicePurchaseOrderInwardedLog) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderInwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderInwardedLog]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderservicePurchaseOrderItemInwardedLogRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderservicePurchaseOrderItemInwardedLog] = {}

    def add(self, log: OrderservicePurchaseOrderItemInwardedLog) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[OrderservicePurchaseOrderItemInwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderservicePurchaseOrderItemInwardedLog]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderserviceSalesOrderRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderserviceSalesOrder] = {}

    def add(self, so: OrderserviceSalesOrder) -> None:
        self._store[so.id] = so

    def get(self, id: int) -> Optional[OrderserviceSalesOrder]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrder]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderserviceSalesOrderOrderItemsRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderserviceSalesOrderOrderItems] = {}

    def add(self, item: OrderserviceSalesOrderOrderItems) -> None:
        self._store[item.id] = item

    def get(self, id: int) -> Optional[OrderserviceSalesOrderOrderItems]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderOrderItems]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderserviceSalesOrderLogsRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderserviceSalesOrderLogs] = {}

    def add(self, log: OrderserviceSalesOrderLogs) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[OrderserviceSalesOrderLogs]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderLogs]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderserviceSalesOrderOutwardedLogRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderserviceSalesOrderOutwardedLog] = {}

    def add(self, log: OrderserviceSalesOrderOutwardedLog) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[OrderserviceSalesOrderOutwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderOutwardedLog]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class OrderserviceSalesOrderItemOutwardedLogRepository:
    def __init__(self) -> None:
        self._store: Dict[int, OrderserviceSalesOrderItemOutwardedLog] = {}

    def add(self, log: OrderserviceSalesOrderItemOutwardedLog) -> None:
        self._store[log.id] = log

    def get(self, id: int) -> Optional[OrderserviceSalesOrderItemOutwardedLog]:
        return self._store.get(id)

    def all(self) -> List[OrderserviceSalesOrderItemOutwardedLog]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class AuthGroupRepository:
    def __init__(self) -> None:
        self._store: Dict[int, AuthGroup] = {}

    def add(self, group: AuthGroup) -> None:
        self._store[group.id] = group

    def get(self, id: int) -> Optional[AuthGroup]:
        return self._store.get(id)

    def all(self) -> List[AuthGroup]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class AuthPermissionRepository:
    def __init__(self) -> None:
        self._store: Dict[int, AuthPermission] = {}

    def add(self, permission: AuthPermission) -> None:
        self._store[permission.id] = permission

    def get(self, id: int) -> Optional[AuthPermission]:
        return self._store.get(id)

    def all(self) -> List[AuthPermission]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class DjangoContentTypeRepository:
    def __init__(self) -> None:
        self._store: Dict[int, DjangoContentType] = {}

    def add(self, ct: DjangoContentType) -> None:
        self._store[ct.id] = ct

    def get(self, id: int) -> Optional[DjangoContentType]:
        return self._store.get(id)

    def all(self) -> List[DjangoContentType]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


class UserservicesModulesRepository:
    def __init__(self) -> None:
        self._store: Dict[int, UserservicesModules] = {}

    def add(self, module: UserservicesModules) -> None:
        self._store[module.id] = module

    def get(self, id: int) -> Optional[UserservicesModules]:
        return self._store.get(id)

    def all(self) -> List[UserservicesModules]:
        return list(self._store.values())

    def remove(self, id: int) -> None:
        self._store.pop(id, None)


# ============================================================
#  ECOMMERCE PROJECT - TOP-LEVEL FACADE
# ============================================================

class EcommerceProject:
    def __init__(self) -> None:
        self.users = UserservicesUsersRepository()
        self.products = ProductservicesProductsRepository()
        self.categories = ProductservicesCategoriesRepository()
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
        self.auth_groups = AuthGroupRepository()
        self.auth_permissions = AuthPermissionRepository()
        self.content_types = DjangoContentTypeRepository()
        self.modules = UserservicesModulesRepository()
        self.user_shipping_addresses: List[UserservicesUserShippingAddress] = []
        self.activity_logs: List[UserservicesActivityLog] = []
        self.user_permissions: List[UserservicesUserPermissions] = []
        self.users_groups: List[UserservicesUsersGroups] = []
        self.users_user_permissions: List[UserservicesUsersUserPermissions] = []
        self.auth_group_permissions: List[AuthGroupPermissions] = []
        self.django_admin_logs: List[DjangoAdminLog] = []
        self.django_migrations: List[DjangoMigrations] = []
        self.django_sessions: Dict[str, DjangoSession] = {}
        self.product_questions: List[ProductservicesProductQuestions] = []
        self.product_reviews: List[ProductservicesProductReviews] = []

    def register_user(self, user: UserservicesUsers) -> None:
        self.users.add(user)

    def register_product(self, product: ProductservicesProducts) -> None:
        self.products.add(product)

    def register_category(self, category: ProductservicesCategories) -> None:
        self.categories.add(category)

    def register_warehouse(self, warehouse: InventoryservicesWarehouse) -> None:
        self.warehouses.add(warehouse)

    def register_rack_shelf_floor(self, rsf: InventoryservicesRackAndShelvesAndFloor) -> None:
        self.rack_shelves_floors.add(rsf)

    def register_inventory(self, inventory: InventoryservicesInventory) -> None:
        self.inventories.add(inventory)

    def register_inventory_log(self, log: InventoryservicesInventoryLog) -> None:
        self.inventory_logs.add(log)

    def register_purchase_order(self, po: OrderservicePurchaseOrder) -> None:
        self.purchase_orders.add(po)

    def register_purchase_order_item(self, item: OrderservicePurchaseOrderItems) -> None:
        self.purchase_order_items.add(item)

    def register_purchase_order_log(self, log: OrderservicePurchaseOrderLogs) -> None:
        self.purchase_order_logs.add(log)

    def register_purchase_order_inwarded_log(self, log: OrderservicePurchaseOrderInwardedLog) -> None:
        self.purchase_order_inwarded_logs.add(log)

    def register_purchase_order_item_inwarded_log(self, log: OrderservicePurchaseOrderItemInwardedLog) -> None:
        self.purchase_order_item_inwarded_logs.add(log)

    def register_sales_order(self, so: OrderserviceSalesOrder) -> None:
        self.sales_orders.add(so)

    def register_sales_order_item(self, item: OrderserviceSalesOrderOrderItems) -> None:
        self.sales_order_items.add(item)

    def register_sales_order_log(self, log: OrderserviceSalesOrderLogs) -> None:
        self.sales_order_logs.add(log)

    def register_sales_order_outwarded_log(self, log: OrderserviceSalesOrderOutwardedLog) -> None:
        self.sales_order_outwarded_logs.add(log)

    def register_sales_order_item_outwarded_log(self, log: OrderserviceSalesOrderItemOutwardedLog) -> None:
        self.sales_order_item_outwarded_logs.add(log)

    def add_user_shipping_address(self, addr: UserservicesUserShippingAddress) -> None:
        self.user_shipping_addresses.append(addr)

    def add_activity_log(self, log: UserservicesActivityLog) -> None:
        self.activity_logs.append(log)

    def add_user_permission(self, perm: UserservicesUserPermissions) -> None:
        self.user_permissions.append(perm)

    def add_users_group(self, ug: UserservicesUsersGroups) -> None:
        self.users_groups.append(ug)

    def add_users_user_permission(self, uup: UserservicesUsersUserPermissions) -> None:
        self.users_user_permissions.append(uup)

    def add_auth_group_permission(self, agp: AuthGroupPermissions) -> None:
        self.auth_group_permissions.append(agp)

    def add_django_admin_log(self, log: DjangoAdminLog) -> None:
        self.django_admin_logs.append(log)

    def add_django_migration(self, migration: DjangoMigrations) -> None:
        self.django_migrations.append(migration)

    def add_django_session(self, session: DjangoSession) -> None:
        self.django_sessions[session.session_key] = session

    def add_product_question(self, question: ProductservicesProductQuestions) -> None:
        self.product_questions.append(question)

    def add_product_review(self, review: ProductservicesProductReviews) -> None:
        self.product_reviews.append(review)

    def get_inventory_by_product(self, product_id: int) -> List[InventoryservicesInventory]:
        return [inv for inv in self.inventories.all() if inv.product.id == product_id]

    def get_inventory_by_warehouse(self, warehouse_id: int) -> List[InventoryservicesInventory]:
        return [inv for inv in self.inventories.all() if inv.warehouse.id == warehouse_id]

    def get_purchase_order_items(self, po_id: int) -> List[OrderservicePurchaseOrderItems]:
        return [item for item in self.purchase_order_items.all() if item.po.id == po_id]

    def get_sales_order_items(self, so_id: int) -> List[OrderserviceSalesOrderOrderItems]:
        return [item for item in self.sales_order_items.all() if item.so.id == so_id]

    def get_products_by_category(self, category_id: int) -> List[ProductservicesProducts]:
        return [p for p in self.products.all() if p.category.id == category_id]

    def get_user_shipping_addresses(self, user_id: int) -> List[UserservicesUserShippingAddress]:
        return [a for a in self.user_shipping_addresses if a.user.id == user_id]

    def get_user_activity_logs(self, user_id: int) -> List[UserservicesActivityLog]:
        return [log for log in self.activity_logs if log.user.id == user_id]

    def get_user_permissions(self, user_id: int) -> List[UserservicesUserPermissions]:
        return [p for p in self.user_permissions if p.user.id == user_id]

    def get_purchase_order_logs(self, po_id: int) -> List[OrderservicePurchaseOrderLogs]:
        return [log for log in self.purchase_order_logs.all() if log.po.id == po_id]

    def get_sales_order_logs(self, so_id: int) -> List[OrderserviceSalesOrderLogs]:
        return [log for log in self.sales_order_logs.all() if log.so.id == so_id]

    def get_inventory_logs_by_inventory(self, inventory_id: int) -> List[InventoryservicesInventoryLog]:
        return [log for log in self.inventory_logs.all() if log.inventory.id == inventory_id]

    def get_product_questions(self, product_id: int) -> List[ProductservicesProductQuestions]:
        return [q for q in self.product_questions if q.product.id == product_id]

    def get_product_reviews(self, product_id: int) -> List[ProductservicesProductReviews]:
        return [r for r in self.product_reviews if r.product.id == product_id]

    def get_subcategories(self, parent_id: int) -> List[ProductservicesCategories]:
        return [c for c in self.categories.all() if c.parent is not None and c.parent.id == parent_id]

    def get_submodules(self, parent_id: int) -> List[UserservicesModules]:
        return [m for m in self.modules.all() if m.parent is not None and m.parent.id == parent_id]

    def __repr__(self) -> str:
        return (
            f"<EcommerceProject users={len(self.users.all())} "
            f"products={len(self.products.all())} "
            f"warehouses={len(self.warehouses.all())}>"
        )