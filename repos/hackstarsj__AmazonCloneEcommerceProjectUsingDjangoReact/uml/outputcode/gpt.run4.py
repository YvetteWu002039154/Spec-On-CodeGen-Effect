from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


class ValidationError(ValueError):
    pass


class BaseEntity:
    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        now = datetime.utcnow()
        self.created_at: datetime = created_at or now
        self.updated_at: datetime = updated_at or now

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class IdEntity(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = int(id)


class BigIdEntity(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = int(id)


class StringIdEntity(BaseEntity):
    def __init__(self, session_key: str, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        super().__init__(created_at=created_at, updated_at=updated_at)
        if not session_key:
            raise ValidationError("session_key must be non-empty")
        self.session_key: str = session_key


def _ensure_non_negative_int(name: str, value: int) -> int:
    if value is None:
        raise ValidationError(f"{name} is required")
    if int(value) < 0:
        raise ValidationError(f"{name} must be >= 0")
    return int(value)


def _ensure_non_negative_decimal(name: str, value: Decimal) -> Decimal:
    if value is None:
        raise ValidationError(f"{name} is required")
    if value < Decimal("0"):
        raise ValidationError(f"{name} must be >= 0")
    return value


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _validate_email(email: Optional[str]) -> None:
    if email is None:
        return
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError("Invalid email")


def _validate_status(value: Optional[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ValidationError("status must be a string")


class userservices_users(BigIdEntity):
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
        social_media_links: Optional[JsonDict] = None,
        addition_details: Optional[JsonDict] = None,
        language: str = "",
        departMent: str = "",
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
        domain_user_id_id: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _validate_email(email)
        self.is_superuser: bool = bool(is_superuser)
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.is_staff: bool = bool(is_staff)
        self.is_active: bool = bool(is_active)
        self.date_joined: datetime = date_joined or datetime.utcnow()
        self.name: str = name
        self.email: str = email
        self.phone: str = phone
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.pincode: str = pincode
        self.country: str = country
        self.profile_pic: str = profile_pic
        self.account_status: str = account_status
        self.role: str = role
        self.dob: Optional[date] = dob
        self.username: str = username
        self.password: str = password
        self.social_media_links: JsonDict = dict(social_media_links or {})
        self.addition_details: JsonDict = dict(addition_details or {})
        self.language: str = language
        self.departMent: str = departMent
        self.designation: str = designation
        self.time_zone: str = time_zone
        self.last_login: Optional[datetime] = last_login
        self.last_device: str = last_device
        self.last_ip: str = last_ip
        self.currency: str = currency
        self.domain_name: str = domain_name
        self.plan_type: str = plan_type
        self.domain_user_id_id: Optional[userservices_users] = domain_user_id_id


class userservices_usershippingaddress(IdEntity):
    def __init__(
        self,
        id: int,
        address_type: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        country: str,
        user_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if user_id is None:
            raise ValidationError("user_id is required")
        self.address_type: str = address_type
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.pincode: str = pincode
        self.country: str = country
        self.user_id: userservices_users = user_id


class userservices_activitylog(IdEntity):
    def __init__(
        self,
        id: int,
        activity: str,
        activity_type: str,
        activity_date: Optional[datetime],
        activity_ip: str,
        activity_device: str,
        domain_user_id_id: userservices_users,
        user_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or user_id is None:
            raise ValidationError("domain_user_id_id and user_id are required")
        self.activity: str = activity
        self.activity_type: str = activity_type
        self.activity_date: datetime = activity_date or datetime.utcnow()
        self.activity_ip: str = activity_ip
        self.activity_device: str = activity_device
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.user_id: userservices_users = user_id


class userservices_modules(IdEntity):
    def __init__(
        self,
        id: int,
        module_name: str,
        module_icon: str,
        is_menu: bool,
        is_active: bool,
        module_url: str,
        display_order: int,
        module_description: str,
        parent_id_id: Optional[userservices_modules] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.module_name: str = module_name
        self.module_icon: str = module_icon
        self.is_menu: bool = bool(is_menu)
        self.is_active: bool = bool(is_active)
        self.module_url: str = module_url
        self.display_order: int = int(display_order)
        self.module_description: str = module_description
        self.parent_id_id: Optional[userservices_modules] = parent_id_id


class userservices_userpermissions(IdEntity):
    def __init__(
        self,
        id: int,
        is_view: bool,
        is_add: bool,
        is_edit: bool,
        is_delete: bool,
        module_id_id: userservices_modules,
        domain_user_id_id: userservices_users,
        user_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if module_id_id is None or domain_user_id_id is None or user_id is None:
            raise ValidationError("module_id_id, domain_user_id_id, user_id are required")
        self.is_view: bool = bool(is_view)
        self.is_add: bool = bool(is_add)
        self.is_edit: bool = bool(is_edit)
        self.is_delete: bool = bool(is_delete)
        self.module_id_id: userservices_modules = module_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.user_id: userservices_users = user_id


class auth_group(IdEntity):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id)
        self.name: str = name


class django_content_type(IdEntity):
    def __init__(self, id: int, app_label: str, model: str) -> None:
        super().__init__(id=id)
        self.app_label: str = app_label
        self.model: str = model


class auth_permission(IdEntity):
    def __init__(self, id: int, name: str, codename: str, content_type_id: django_content_type) -> None:
        super().__init__(id=id)
        if content_type_id is None:
            raise ValidationError("content_type_id is required")
        self.name: str = name
        self.codename: str = codename
        self.content_type_id: django_content_type = content_type_id


class auth_group_permissions(BigIdEntity):
    def __init__(self, id: int, group_id: auth_group, permission_id: auth_permission) -> None:
        super().__init__(id=id)
        if group_id is None or permission_id is None:
            raise ValidationError("group_id and permission_id are required")
        self.group_id: auth_group = group_id
        self.permission_id: auth_permission = permission_id


class userservices_users_groups(BigIdEntity):
    def __init__(self, id: int, users_id: userservices_users, group_id: auth_group) -> None:
        super().__init__(id=id)
        if users_id is None or group_id is None:
            raise ValidationError("users_id and group_id are required")
        self.users_id: userservices_users = users_id
        self.group_id: auth_group = group_id


class userservices_users_user_permissions(BigIdEntity):
    def __init__(self, id: int, users_id: userservices_users, permission_id: auth_permission) -> None:
        super().__init__(id=id)
        if users_id is None or permission_id is None:
            raise ValidationError("users_id and permission_id are required")
        self.users_id: userservices_users = users_id
        self.permission_id: auth_permission = permission_id


class django_admin_log(IdEntity):
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str,
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type_id: django_content_type,
        user_id: userservices_users,
    ) -> None:
        super().__init__(id=id)
        if content_type_id is None or user_id is None:
            raise ValidationError("content_type_id and user_id are required")
        self.action_time: datetime = action_time
        self.object_id: str = object_id
        self.object_repr: str = object_repr
        self.action_flag: int = int(action_flag)
        self.change_message: str = change_message
        self.content_type_id: django_content_type = content_type_id
        self.user_id: userservices_users = user_id


class django_migrations(BigIdEntity):
    def __init__(self, id: int, app: str, name: str, applied: datetime) -> None:
        super().__init__(id=id)
        self.app: str = app
        self.name: str = name
        self.applied: datetime = applied


class django_session(StringIdEntity):
    def __init__(self, session_key: str, session_data: str, expire_date: datetime) -> None:
        super().__init__(session_key=session_key)
        self.session_data: str = session_data
        self.expire_date: datetime = expire_date


class productservices_categories(IdEntity):
    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        description: str,
        display_order: int,
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        parent_id_id: Optional[productservices_categories] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if added_by_user_id_id is None or domain_user_id_id is None:
            raise ValidationError("added_by_user_id_id and domain_user_id_id are required")
        self.name: str = name
        self.image: str = image
        self.description: str = description
        self.display_order: int = int(display_order)
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.parent_id_id: Optional[productservices_categories] = parent_id_id


class productservices_products(IdEntity):
    def __init__(
        self,
        id: int,
        name: str,
        image: Optional[JsonDict],
        description: str,
        specifications: Optional[JsonDict],
        html_description: str,
        highlights: Optional[JsonDict],
        sku: str,
        initial_buying_price: float,
        initial_selling_price: float,
        weight: float,
        dimensions: str,
        uom: str,
        color: str,
        tax_percentage: float,
        brand: str,
        brand_model: str,
        status: str,
        seo_title: str,
        seo_description: str,
        seo_keywords: Optional[JsonDict],
        addition_details: Optional[JsonDict],
        added_by_user_id_id: userservices_users,
        category_id_id: productservices_categories,
        domain_user_id_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if added_by_user_id_id is None or category_id_id is None or domain_user_id_id is None:
            raise ValidationError("added_by_user_id_id, category_id_id, domain_user_id_id are required")
        _validate_status(status)
        self.name: str = name
        self.image: JsonDict = dict(image or {})
        self.description: str = description
        self.specifications: JsonDict = dict(specifications or {})
        self.html_description: str = html_description
        self.highlights: JsonDict = dict(highlights or {})
        self.sku: str = sku
        self.initial_buying_price: float = _to_float(initial_buying_price)
        self.initial_selling_price: float = _to_float(initial_selling_price)
        self.weight: float = _to_float(weight)
        self.dimensions: str = dimensions
        self.uom: str = uom
        self.color: str = color
        self.tax_percentage: float = _to_float(tax_percentage)
        self.brand: str = brand
        self.brand_model: str = brand_model
        self.status: str = status
        self.seo_title: str = seo_title
        self.seo_description: str = seo_description
        self.seo_keywords: JsonDict = dict(seo_keywords or {})
        self.addition_details: JsonDict = dict(addition_details or {})
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.category_id_id: productservices_categories = category_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id


class productservices_productquestions(IdEntity):
    def __init__(
        self,
        id: int,
        question: str,
        answer: str,
        status: str,
        answer_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        question_user_id_id: userservices_users,
        product_id_id: productservices_products,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if (
            answer_user_id_id is None
            or domain_user_id_id is None
            or question_user_id_id is None
            or product_id_id is None
        ):
            raise ValidationError("answer_user_id_id, domain_user_id_id, question_user_id_id, product_id_id are required")
        _validate_status(status)
        self.question: str = question
        self.answer: str = answer
        self.status: str = status
        self.answer_user_id_id: userservices_users = answer_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.question_user_id_id: userservices_users = question_user_id_id
        self.product_id_id: productservices_products = product_id_id


class productservices_productreviews(IdEntity):
    def __init__(
        self,
        id: int,
        review_images: Optional[JsonDict],
        rating: float,
        reviews: str,
        status: str,
        domain_user_id_id: userservices_users,
        review_user_id_id: userservices_users,
        product_id_id: productservices_products,
    ) -> None:
        super().__init__(id=id)
        if domain_user_id_id is None or review_user_id_id is None or product_id_id is None:
            raise ValidationError("domain_user_id_id, review_user_id_id, product_id_id are required")
        _validate_status(status)
        self.review_images: JsonDict = dict(review_images or {})
        self.rating: float = _to_float(rating)
        self.reviews: str = reviews
        self.status: str = status
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.review_user_id_id: userservices_users = review_user_id_id
        self.product_id_id: productservices_products = product_id_id


class inventoryservices_warehouse(IdEntity):
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
        size: str,
        capacity: str,
        warehouse_type: str,
        additional_details: Optional[JsonDict],
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        warehouse_manager_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if added_by_user_id_id is None or domain_user_id_id is None or warehouse_manager_id is None:
            raise ValidationError("added_by_user_id_id, domain_user_id_id, warehouse_manager_id are required")
        _validate_email(email)
        _validate_status(status)
        self.name: str = name
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.country: str = country
        self.pincode: str = pincode
        self.phone: str = phone
        self.email: str = email
        self.status: str = status
        self.size: str = size
        self.capacity: str = capacity
        self.warehouse_type: str = warehouse_type
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.warehouse_manager_id: userservices_users = warehouse_manager_id


class inventoryservices_rackandshelvesandfloor(IdEntity):
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: Optional[JsonDict],
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        warehouse_id_id: inventoryservices_warehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if added_by_user_id_id is None or domain_user_id_id is None or warehouse_id_id is None:
            raise ValidationError("added_by_user_id_id, domain_user_id_id, warehouse_id_id are required")
        self.name: str = name
        self.rack: str = rack
        self.shelf: str = shelf
        self.floor: str = floor
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.warehouse_id_id: inventoryservices_warehouse = warehouse_id_id


class orderservice_purchaseorder(IdEntity):
    def __init__(
        self,
        id: int,
        po_code: str,
        po_date: Optional[datetime],
        expected_delivery_date: Optional[datetime],
        payment_terms: str,
        payment_status: str,
        total_amount: Decimal,
        paid_amount: Decimal,
        due_amount: Decimal,
        discount_amount: Decimal,
        discount_type: str,
        shipping_amount: Decimal,
        shipping_type: str,
        shipping_tax_percentage: Decimal,
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        additional_details: Optional[JsonDict],
        status: str,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: str,
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user_id_id: userservices_users,
        cancelled_by_user_id_id: userservices_users,
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        last_updated_by_user_id_id: userservices_users,
        received_by_user_id_id: userservices_users,
        returned_by_user_id_id: userservices_users,
        supplier_id_id: userservices_users,
        updated_by_user_id_id: userservices_users,
        warehouse_id_id: inventoryservices_warehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or created_by_user_id_id is None or supplier_id_id is None or warehouse_id_id is None:
            raise ValidationError("domain_user_id_id, created_by_user_id_id, supplier_id_id, warehouse_id_id are required")
        _validate_status(status)
        self.po_code: str = po_code
        self.po_date: datetime = po_date or datetime.utcnow()
        self.expected_delivery_date: Optional[datetime] = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = _ensure_non_negative_decimal("total_amount", _to_decimal(total_amount))
        self.paid_amount: Decimal = _ensure_non_negative_decimal("paid_amount", _to_decimal(paid_amount))
        self.due_amount: Decimal = _ensure_non_negative_decimal("due_amount", _to_decimal(due_amount))
        self.discount_amount: Decimal = _ensure_non_negative_decimal("discount_amount", _to_decimal(discount_amount))
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal("shipping_amount", _to_decimal(shipping_amount))
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(
            "shipping_tax_percentage", _to_decimal(shipping_tax_percentage)
        )
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal("shipping_tax_amount", _to_decimal(shipping_tax_amount))
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_amount", _to_decimal(shipping_cancelled_amount)
        )
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_tax_amount", _to_decimal(shipping_cancelled_tax_amount)
        )
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: userservices_users = approved_by_user_id_id
        self.cancelled_by_user_id_id: userservices_users = cancelled_by_user_id_id
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.last_updated_by_user_id_id: userservices_users = last_updated_by_user_id_id
        self.received_by_user_id_id: userservices_users = received_by_user_id_id
        self.returned_by_user_id_id: userservices_users = returned_by_user_id_id
        self.supplier_id_id: userservices_users = supplier_id_id
        self.updated_by_user_id_id: userservices_users = updated_by_user_id_id
        self.warehouse_id_id: inventoryservices_warehouse = warehouse_id_id


class orderservice_purchaseorderitems(IdEntity):
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
        discount_type: str,
        additional_details: Optional[JsonDict],
        status: str,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: str,
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user_id_id: userservices_users,
        cancelled_by_user_id_id: userservices_users,
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        last_updated_by_user_id_id: userservices_users,
        received_by_user_id_id: userservices_users,
        returned_by_user_id_id: userservices_users,
        po_id_id: orderservice_purchaseorder,
        product_id_id: productservices_products,
        updated_by_user_id_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if po_id_id is None or product_id_id is None or domain_user_id_id is None:
            raise ValidationError("po_id_id, product_id_id, domain_user_id_id are required")
        _validate_status(status)
        self.quantity_ordered: int = _ensure_non_negative_int("quantity_ordered", quantity_ordered)
        self.quantity_received: int = _ensure_non_negative_int("quantity_received", quantity_received)
        self.quantity_cancelled: int = _ensure_non_negative_int("quantity_cancelled", quantity_cancelled)
        self.quantity_returned: int = _ensure_non_negative_int("quantity_returned", quantity_returned)
        self.buying_price: Decimal = _ensure_non_negative_decimal("buying_price", _to_decimal(buying_price))
        self.selling_price: Decimal = _ensure_non_negative_decimal("selling_price", _to_decimal(selling_price))
        self.discount_amount: Decimal = _ensure_non_negative_decimal("discount_amount", _to_decimal(discount_amount))
        self.amount_paid: Decimal = _ensure_non_negative_decimal("amount_paid", _to_decimal(amount_paid))
        self.amount_returned: Decimal = _ensure_non_negative_decimal("amount_returned", _to_decimal(amount_returned))
        self.amount_cancelled: Decimal = _ensure_non_negative_decimal("amount_cancelled", _to_decimal(amount_cancelled))
        self.amount_ordered: Decimal = _ensure_non_negative_decimal("amount_ordered", _to_decimal(amount_ordered))
        self.tax_percentage: Decimal = _ensure_non_negative_decimal("tax_percentage", _to_decimal(tax_percentage))
        self.tax_amount: Decimal = _ensure_non_negative_decimal("tax_amount", _to_decimal(tax_amount))
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(
            "shipping_tax_percentage", _to_decimal(shipping_tax_percentage)
        )
        self.shipping_amount: Decimal = _ensure_non_negative_decimal("shipping_amount", _to_decimal(shipping_amount))
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal("shipping_tax_amount", _to_decimal(shipping_tax_amount))
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_amount", _to_decimal(shipping_cancelled_amount)
        )
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_tax_amount", _to_decimal(shipping_cancelled_tax_amount)
        )
        self.discount_type: str = discount_type
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: userservices_users = approved_by_user_id_id
        self.cancelled_by_user_id_id: userservices_users = cancelled_by_user_id_id
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.last_updated_by_user_id_id: userservices_users = last_updated_by_user_id_id
        self.received_by_user_id_id: userservices_users = received_by_user_id_id
        self.returned_by_user_id_id: userservices_users = returned_by_user_id_id
        self.po_id_id: orderservice_purchaseorder = po_id_id
        self.product_id_id: productservices_products = product_id_id
        self.updated_by_user_id_id: userservices_users = updated_by_user_id_id


class orderservice_purchaseorderlogs(IdEntity):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonDict],
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        po_id_id: orderservice_purchaseorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if created_by_user_id_id is None or domain_user_id_id is None or po_id_id is None:
            raise ValidationError("created_by_user_id_id, domain_user_id_id, po_id_id are required")
        self.comment: str = comment
        self.additional_details: JsonDict = dict(additional_details or {})
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.po_id_id: orderservice_purchaseorder = po_id_id


class orderservice_purchaseorderinwardedlog(IdEntity):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: Optional[datetime],
        additional_details: Optional[JsonDict],
        status: str,
        domain_user_id_id: userservices_users,
        inwarded_by_user_id_id: userservices_users,
        po_id_id: orderservice_purchaseorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or inwarded_by_user_id_id is None or po_id_id is None:
            raise ValidationError("domain_user_id_id, inwarded_by_user_id_id, po_id_id are required")
        _validate_status(status)
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.inwarded_at: datetime = inwarded_at or datetime.utcnow()
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.inwarded_by_user_id_id: userservices_users = inwarded_by_user_id_id
        self.po_id_id: orderservice_purchaseorder = po_id_id


class orderservice_purchaseorderiteminwardedlog(IdEntity):
    def __init__(
        self,
        id: int,
        inwarded_quantity: int,
        price: Decimal,
        tax_percentage: Decimal,
        discount_amount: Decimal,
        discount_type: str,
        shipping_amount: Decimal,
        shipping_tax_percentage: Decimal,
        additional_details: Optional[JsonDict],
        status: str,
        domain_user_id_id: userservices_users,
        po_item_id_id: orderservice_purchaseorderitems,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or po_item_id_id is None:
            raise ValidationError("domain_user_id_id and po_item_id_id are required")
        _validate_status(status)
        self.inwarded_quantity: int = _ensure_non_negative_int("inwarded_quantity", inwarded_quantity)
        self.price: Decimal = _ensure_non_negative_decimal("price", _to_decimal(price))
        self.tax_percentage: Decimal = _ensure_non_negative_decimal("tax_percentage", _to_decimal(tax_percentage))
        self.discount_amount: Decimal = _ensure_non_negative_decimal("discount_amount", _to_decimal(discount_amount))
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal("shipping_amount", _to_decimal(shipping_amount))
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(
            "shipping_tax_percentage", _to_decimal(shipping_tax_percentage)
        )
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.po_item_id_id: orderservice_purchaseorderitems = po_item_id_id


class orderservice_salesorder(IdEntity):
    def __init__(
        self,
        id: int,
        so_code: str,
        so_date: Optional[datetime],
        expected_delivery_date: Optional[datetime],
        payment_terms: str,
        payment_status: str,
        total_amount: Decimal,
        paid_amount: Decimal,
        due_amount: Decimal,
        discount_amount: Decimal,
        discount_type: str,
        shipping_amount: Decimal,
        shipping_type: str,
        shipping_tax_percentage: Decimal,
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        additional_details: Optional[JsonDict],
        status: str,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: str,
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user_id_id: userservices_users,
        cancelled_by_user_id_id: userservices_users,
        created_by_user_id_id: userservices_users,
        customer_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        last_updated_by_user_id_id: userservices_users,
        received_by_user_id_id: userservices_users,
        returned_by_user_id_id: userservices_users,
        po_id_id: orderservice_purchaseorder,
        product_id_id: productservices_products,
        updated_by_user_id_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or created_by_user_id_id is None or customer_id_id is None:
            raise ValidationError("domain_user_id_id, created_by_user_id_id, customer_id_id are required")
        _validate_status(status)
        self.so_code: str = so_code
        self.so_date: datetime = so_date or datetime.utcnow()
        self.expected_delivery_date: Optional[datetime] = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = _ensure_non_negative_decimal("total_amount", _to_decimal(total_amount))
        self.paid_amount: Decimal = _ensure_non_negative_decimal("paid_amount", _to_decimal(paid_amount))
        self.due_amount: Decimal = _ensure_non_negative_decimal("due_amount", _to_decimal(due_amount))
        self.discount_amount: Decimal = _ensure_non_negative_decimal("discount_amount", _to_decimal(discount_amount))
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal("shipping_amount", _to_decimal(shipping_amount))
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(
            "shipping_tax_percentage", _to_decimal(shipping_tax_percentage)
        )
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal("shipping_tax_amount", _to_decimal(shipping_tax_amount))
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_amount", _to_decimal(shipping_cancelled_amount)
        )
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_tax_amount", _to_decimal(shipping_cancelled_tax_amount)
        )
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: userservices_users = approved_by_user_id_id
        self.cancelled_by_user_id_id: userservices_users = cancelled_by_user_id_id
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.customer_id_id: userservices_users = customer_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.last_updated_by_user_id_id: userservices_users = last_updated_by_user_id_id
        self.received_by_user_id_id: userservices_users = received_by_user_id_id
        self.returned_by_user_id_id: userservices_users = returned_by_user_id_id
        self.po_id_id: orderservice_purchaseorder = po_id_id
        self.product_id_id: productservices_products = product_id_id
        self.updated_by_user_id_id: userservices_users = updated_by_user_id_id


class orderservice_salesorderorderitems(IdEntity):
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
        discount_type: str,
        amount_paid: Decimal,
        amount_returned: Decimal,
        amount_cancelled: Decimal,
        amount_ordered: Decimal,
        tax_percentage: Decimal,
        tax_amount: Decimal,
        shipping_amount: Decimal,
        shipping_type: str,
        shipping_tax_amount: Decimal,
        shipping_cancelled_amount: Decimal,
        shipping_cancelled_tax_amount: Decimal,
        additional_details: Optional[JsonDict],
        status: str,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: str,
        shipped_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user_id_id: userservices_users,
        cancelled_by_user_id_id: userservices_users,
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        product_id_id: productservices_products,
        returned_by_user_id_id: userservices_users,
        shipped_by_user_id_id: userservices_users,
        so_id_id: orderservice_salesorder,
        updated_by_user_id_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if so_id_id is None or product_id_id is None or domain_user_id_id is None:
            raise ValidationError("so_id_id, product_id_id, domain_user_id_id are required")
        _validate_status(status)
        self.quantity_ordered: int = _ensure_non_negative_int("quantity_ordered", quantity_ordered)
        self.quantity_delivered: int = _ensure_non_negative_int("quantity_delivered", quantity_delivered)
        self.quantity_shipped: int = _ensure_non_negative_int("quantity_shipped", quantity_shipped)
        self.quantity_cancelled: int = _ensure_non_negative_int("quantity_cancelled", quantity_cancelled)
        self.quantity_returned: int = _ensure_non_negative_int("quantity_returned", quantity_returned)
        self.purchase_price: Decimal = _ensure_non_negative_decimal("purchase_price", _to_decimal(purchase_price))
        self.discount_amount: Decimal = _ensure_non_negative_decimal("discount_amount", _to_decimal(discount_amount))
        self.discount_type: str = discount_type
        self.amount_paid: Decimal = _ensure_non_negative_decimal("amount_paid", _to_decimal(amount_paid))
        self.amount_returned: Decimal = _ensure_non_negative_decimal("amount_returned", _to_decimal(amount_returned))
        self.amount_cancelled: Decimal = _ensure_non_negative_decimal("amount_cancelled", _to_decimal(amount_cancelled))
        self.amount_ordered: Decimal = _ensure_non_negative_decimal("amount_ordered", _to_decimal(amount_ordered))
        self.tax_percentage: Decimal = _ensure_non_negative_decimal("tax_percentage", _to_decimal(tax_percentage))
        self.tax_amount: Decimal = _ensure_non_negative_decimal("tax_amount", _to_decimal(tax_amount))
        self.shipping_amount: Decimal = _ensure_non_negative_decimal("shipping_amount", _to_decimal(shipping_amount))
        self.shipping_type: str = shipping_type
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal("shipping_tax_amount", _to_decimal(shipping_tax_amount))
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_amount", _to_decimal(shipping_cancelled_amount)
        )
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            "shipping_cancelled_tax_amount", _to_decimal(shipping_cancelled_tax_amount)
        )
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.shipped_at: Optional[datetime] = shipped_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: userservices_users = approved_by_user_id_id
        self.cancelled_by_user_id_id: userservices_users = cancelled_by_user_id_id
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.product_id_id: productservices_products = product_id_id
        self.returned_by_user_id_id: userservices_users = returned_by_user_id_id
        self.shipped_by_user_id_id: userservices_users = shipped_by_user_id_id
        self.so_id_id: orderservice_salesorder = so_id_id
        self.updated_by_user_id_id: userservices_users = updated_by_user_id_id


class orderservice_salesorderlogs(IdEntity):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonDict],
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        so_id_id: orderservice_salesorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if created_by_user_id_id is None or domain_user_id_id is None or so_id_id is None:
            raise ValidationError("created_by_user_id_id, domain_user_id_id, so_id_id are required")
        self.comment: str = comment
        self.additional_details: JsonDict = dict(additional_details or {})
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.so_id_id: orderservice_salesorder = so_id_id


class orderservice_salesorderoutwardedlog(IdEntity):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: Optional[datetime],
        additional_details: Optional[JsonDict],
        status: str,
        domain_user_id_id: userservices_users,
        outwarded_by_user_id_id: userservices_users,
        so_id_id: orderservice_salesorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or outwarded_by_user_id_id is None or so_id_id is None:
            raise ValidationError("domain_user_id_id, outwarded_by_user_id_id, so_id_id are required")
        _validate_status(status)
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.outwared_at: datetime = outwared_at or datetime.utcnow()
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.outwarded_by_user_id_id: userservices_users = outwarded_by_user_id_id
        self.so_id_id: orderservice_salesorder = so_id_id


class orderservice_salesorderitemoutwardedlog(IdEntity):
    def __init__(
        self,
        id: int,
        outwarded_quantity: int,
        price: Decimal,
        tax_percentage: Decimal,
        discount_amount: Decimal,
        discount_type: str,
        shipping_amount: Decimal,
        shipping_tax_percentage: Decimal,
        additional_details: Optional[JsonDict],
        status: str,
        domain_user_id_id: userservices_users,
        so_item_id_id: orderservice_salesorderorderitems,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if domain_user_id_id is None or so_item_id_id is None:
            raise ValidationError("domain_user_id_id and so_item_id_id are required")
        _validate_status(status)
        self.outwarded_quantity: int = _ensure_non_negative_int("outwarded_quantity", outwarded_quantity)
        self.price: Decimal = _ensure_non_negative_decimal("price", _to_decimal(price))
        self.tax_percentage: Decimal = _ensure_non_negative_decimal("tax_percentage", _to_decimal(tax_percentage))
        self.discount_amount: Decimal = _ensure_non_negative_decimal("discount_amount", _to_decimal(discount_amount))
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal("shipping_amount", _to_decimal(shipping_amount))
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(
            "shipping_tax_percentage", _to_decimal(shipping_tax_percentage)
        )
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.so_item_id_id: orderservice_salesorderorderitems = so_item_id_id


class inventoryservices_inventory(IdEntity):
    def __init__(
        self,
        id: int,
        quantity: int,
        mrp: str,
        batch_number: str,
        discount_type: str,
        discount_amout: float,
        sr_no: str,
        mfg_date: Optional[datetime],
        uom: str,
        ptr: str,
        received_date: Optional[datetime],
        expiry_date: Optional[datetime],
        quantity_inwarded: int,
        buy_price: Decimal,
        sell_price: Decimal,
        tax_percentage: Decimal,
        stock_status: str,
        inward_type: str,
        additional_details: Optional[JsonDict],
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        product_id_id: productservices_products,
        purchase_order_id_id: orderservice_purchaseorder,
        purchase_order_item_id_id: orderservice_purchaseorderitems,
        purchase_order_item_inwarded_item_id_id: Optional[orderservice_purchaseorderiteminwardedlog],
        rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor,
        warehouse_id_id: inventoryservices_warehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if (
            added_by_user_id_id is None
            or domain_user_id_id is None
            or product_id_id is None
            or purchase_order_id_id is None
            or purchase_order_item_id_id is None
            or rack_shelf_floor_id_id is None
            or warehouse_id_id is None
        ):
            raise ValidationError("Required foreign keys are missing")
        self.quantity: int = _ensure_non_negative_int("quantity", quantity)
        self.mrp: str = mrp
        self.batch_number: str = batch_number
        self.discount_type: str = discount_type
        self.discount_amout: float = _to_float(discount_amout)
        self.sr_no: str = sr_no
        self.mfg_date: Optional[datetime] = mfg_date
        self.uom: str = uom
        self.ptr: str = ptr
        self.received_date: Optional[datetime] = received_date
        self.expiry_date: Optional[datetime] = expiry_date
        self.quantity_inwarded: int = _ensure_non_negative_int("quantity_inwarded", quantity_inwarded)
        self.buy_price: Decimal = _ensure_non_negative_decimal("buy_price", _to_decimal(buy_price))
        self.sell_price: Decimal = _ensure_non_negative_decimal("sell_price", _to_decimal(sell_price))
        self.tax_percentage: Decimal = _ensure_non_negative_decimal("tax_percentage", _to_decimal(tax_percentage))
        self.stock_status: str = stock_status
        self.inward_type: str = inward_type
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.product_id_id: productservices_products = product_id_id
        self.purchase_order_id_id: orderservice_purchaseorder = purchase_order_id_id
        self.purchase_order_item_id_id: orderservice_purchaseorderitems = purchase_order_item_id_id
        self.purchase_order_item_inwarded_item_id_id: Optional[
            orderservice_purchaseorderiteminwardedlog
        ] = purchase_order_item_inwarded_item_id_id
        self.rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor = rack_shelf_floor_id_id
        self.warehouse_id_id: inventoryservices_warehouse = warehouse_id_id


class inventoryservices_inventorylog(IdEntity):
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Optional[JsonDict],
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        inventory_id_id: inventoryservices_inventory,
        po_id_id: Optional[orderservice_purchaseorder],
        so_id_id: Optional[orderservice_salesorder],
        rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor,
        warehouse_id_id: inventoryservices_warehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if (
            added_by_user_id_id is None
            or domain_user_id_id is None
            or inventory_id_id is None
            or rack_shelf_floor_id_id is None
            or warehouse_id_id is None
        ):
            raise ValidationError("Required foreign keys are missing")
        _validate_status(status)
        self.quantity: int = _ensure_non_negative_int("quantity", quantity)
        self.status: str = status
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.inventory_id_id: inventoryservices_inventory = inventory_id_id
        self.po_id_id: Optional[orderservice_purchaseorder] = po_id_id
        self.so_id_id: Optional[orderservice_salesorder] = so_id_id
        self.rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor = rack_shelf_floor_id_id
        self.warehouse_id_id: inventoryservices_warehouse = warehouse_id_id


__all__ = [
    "ValidationError",
    "inventoryservices_inventory",
    "inventoryservices_inventorylog",
    "inventoryservices_rackandshelvesandfloor",
    "inventoryservices_warehouse",
    "orderservice_purchaseorder",
    "orderservice_purchaseorderitems",
    "orderservice_purchaseorderlogs",
    "orderservice_purchaseorderinwardedlog",
    "orderservice_purchaseorderiteminwardedlog",
    "orderservice_salesorder",
    "orderservice_salesorderorderitems",
    "orderservice_salesorderlogs",
    "orderservice_salesorderoutwardedlog",
    "orderservice_salesorderitemoutwardedlog",
    "productservices_categories",
    "productservices_products",
    "productservices_productquestions",
    "productservices_productreviews",
    "userservices_users",
    "userservices_usershippingaddress",
    "userservices_activitylog",
    "userservices_modules",
    "userservices_userpermissions",
    "userservices_users_groups",
    "userservices_users_user_permissions",
    "django_admin_log",
    "django_migrations",
    "django_content_type",
    "django_session",
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
]