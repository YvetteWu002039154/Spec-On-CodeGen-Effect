from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Union


JsonType = Dict[str, Any]


class ValidationError(ValueError):
    pass


class BaseEntity:
    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        now = datetime.utcnow()
        self.created_at: datetime = created_at or now
        self.updated_at: datetime = updated_at or now

    def touch(self, when: Optional[datetime] = None) -> None:
        self.updated_at = when or datetime.utcnow()


class IntPKEntity(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("id must be a positive int")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = id


class BigIntPKEntity(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("id must be a positive bigint (int)")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = id


class StringPKEntity(BaseEntity):
    def __init__(self, session_key: str, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(session_key, str) or not session_key:
            raise ValidationError("session_key must be a non-empty string")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.session_key: str = session_key


def _ensure_non_negative_int(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValidationError(f"{name} must be a non-negative int")


def _ensure_optional_positive_int(name: str, value: Optional[int]) -> None:
    if value is None:
        return
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{name} must be a positive int when provided")


def _ensure_optional_positive_bigint(name: str, value: Optional[int]) -> None:
    if value is None:
        return
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{name} must be a positive bigint (int) when provided")


def _ensure_decimal(name: str, value: Decimal) -> None:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{name} must be a Decimal")


def _ensure_optional_decimal(name: str, value: Optional[Decimal]) -> None:
    if value is None:
        return
    _ensure_decimal(name, value)


def _ensure_optional_datetime(name: str, value: Optional[datetime]) -> None:
    if value is None:
        return
    if not isinstance(value, datetime):
        raise ValidationError(f"{name} must be a datetime when provided")


def _ensure_optional_date(name: str, value: Optional[date]) -> None:
    if value is None:
        return
    if not isinstance(value, date):
        raise ValidationError(f"{name} must be a date when provided")


def _ensure_optional_json(name: str, value: Optional[JsonType]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be a dict (json) when provided")


def _ensure_optional_str(name: str, value: Optional[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a str when provided")


def _ensure_optional_float(name: str, value: Optional[float]) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a float when provided")


def _ensure_optional_int(name: str, value: Optional[int]) -> None:
    if value is None:
        return
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an int when provided")


class userservices_users(BigIntPKEntity):
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
        profile_pic: str,
        account_status: str,
        role: str,
        dob: Optional[date],
        username: str,
        password: str,
        social_media_links: Optional[JsonType],
        addition_details: Optional[JsonType],
        language: str,
        departMent: str,
        designation: str,
        time_zone: str,
        last_login: Optional[datetime],
        last_device: str,
        last_ip: str,
        currency: str,
        domain_name: str,
        plan_type: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(is_superuser, bool):
            raise ValidationError("is_superuser must be bool")
        if not isinstance(is_staff, bool):
            raise ValidationError("is_staff must be bool")
        if not isinstance(is_active, bool):
            raise ValidationError("is_active must be bool")
        if not isinstance(date_joined, datetime):
            raise ValidationError("date_joined must be datetime")
        _ensure_optional_date("dob", dob)
        _ensure_optional_datetime("last_login", last_login)
        _ensure_optional_json("social_media_links", social_media_links)
        _ensure_optional_json("addition_details", addition_details)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)

        self.is_superuser: bool = is_superuser
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.is_staff: bool = is_staff
        self.is_active: bool = is_active
        self.date_joined: datetime = date_joined
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
        self.social_media_links: Optional[JsonType] = social_media_links
        self.addition_details: Optional[JsonType] = addition_details
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

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.domain_user: Optional[userservices_users] = None

    def set_domain_user(self, domain_user: Optional["userservices_users"]) -> None:
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = domain_user
        self.domain_user_id_id = domain_user.id if domain_user is not None else None
        self.touch()


class inventoryservices_warehouse(IntPKEntity):
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
        additional_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_manager_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("added_by_user_id_id", added_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("warehouse_manager_id", warehouse_manager_id)

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
        self.additional_details: Optional[JsonType] = additional_details

        self.added_by_user_id_id: Optional[int] = added_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.warehouse_manager_id: Optional[int] = warehouse_manager_id

        self.added_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.warehouse_manager: Optional[userservices_users] = None

    def set_added_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        self.added_by_user = user
        self.added_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()

    def set_warehouse_manager(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("warehouse_manager must be userservices_users or None")
        self.warehouse_manager = user
        self.warehouse_manager_id = user.id if user is not None else None
        self.touch()


class inventoryservices_rackandshelvesandfloor(IntPKEntity):
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("added_by_user_id_id", added_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("warehouse_id_id", warehouse_id_id)

        self.name: str = name
        self.rack: str = rack
        self.shelf: str = shelf
        self.floor: str = floor
        self.additional_details: Optional[JsonType] = additional_details

        self.added_by_user_id_id: Optional[int] = added_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.warehouse_id_id: Optional[int] = warehouse_id_id

        self.added_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.warehouse: Optional[inventoryservices_warehouse] = None

    def set_warehouse(self, warehouse: Optional[inventoryservices_warehouse]) -> None:
        if warehouse is not None and not isinstance(warehouse, inventoryservices_warehouse):
            raise ValidationError("warehouse must be inventoryservices_warehouse or None")
        self.warehouse = warehouse
        self.warehouse_id_id = warehouse.id if warehouse is not None else None
        self.touch()

    def set_added_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        self.added_by_user = user
        self.added_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class productservices_categories(IntPKEntity):
    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        description: str,
        display_order: int,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        parent_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("display_order", display_order)
        _ensure_optional_positive_bigint("added_by_user_id_id", added_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("parent_id_id", parent_id_id)

        self.name: str = name
        self.image: str = image
        self.description: str = description
        self.display_order: int = display_order

        self.added_by_user_id_id: Optional[int] = added_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.parent_id_id: Optional[int] = parent_id_id

        self.added_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.parent: Optional[productservices_categories] = None

    def set_parent(self, parent: Optional["productservices_categories"]) -> None:
        if parent is not None and not isinstance(parent, productservices_categories):
            raise ValidationError("parent must be productservices_categories or None")
        if parent is not None and parent.id == self.id:
            raise ValidationError("category cannot be its own parent")
        self.parent = parent
        self.parent_id_id = parent.id if parent is not None else None
        self.touch()

    def set_added_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        self.added_by_user = user
        self.added_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class productservices_products(IntPKEntity):
    def __init__(
        self,
        id: int,
        name: str,
        image: Optional[JsonType],
        description: str,
        specifications: Optional[JsonType],
        html_description: str,
        highlights: Optional[JsonType],
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
        seo_keywords: Optional[JsonType],
        addition_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        category_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_json("image", image)
        _ensure_optional_json("specifications", specifications)
        _ensure_optional_json("highlights", highlights)
        _ensure_optional_json("seo_keywords", seo_keywords)
        _ensure_optional_json("addition_details", addition_details)
        _ensure_optional_float("initial_buying_price", initial_buying_price)
        _ensure_optional_float("initial_selling_price", initial_selling_price)
        _ensure_optional_float("weight", weight)
        _ensure_optional_float("tax_percentage", tax_percentage)
        _ensure_optional_positive_bigint("added_by_user_id_id", added_by_user_id_id)
        _ensure_optional_positive_int("category_id_id", category_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)

        self.name: str = name
        self.image: Optional[JsonType] = image
        self.description: str = description
        self.specifications: Optional[JsonType] = specifications
        self.html_description: str = html_description
        self.highlights: Optional[JsonType] = highlights
        self.sku: str = sku
        self.initial_buying_price: float = float(initial_buying_price)
        self.initial_selling_price: float = float(initial_selling_price)
        self.weight: float = float(weight)
        self.dimensions: str = dimensions
        self.uom: str = uom
        self.color: str = color
        self.tax_percentage: float = float(tax_percentage)
        self.brand: str = brand
        self.brand_model: str = brand_model
        self.status: str = status
        self.seo_title: str = seo_title
        self.seo_description: str = seo_description
        self.seo_keywords: Optional[JsonType] = seo_keywords
        self.addition_details: Optional[JsonType] = addition_details

        self.added_by_user_id_id: Optional[int] = added_by_user_id_id
        self.category_id_id: Optional[int] = category_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id

        self.added_by_user: Optional[userservices_users] = None
        self.category: Optional[productservices_categories] = None
        self.domain_user: Optional[userservices_users] = None

    def set_category(self, category: Optional[productservices_categories]) -> None:
        if category is not None and not isinstance(category, productservices_categories):
            raise ValidationError("category must be productservices_categories or None")
        self.category = category
        self.category_id_id = category.id if category is not None else None
        self.touch()

    def set_added_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        self.added_by_user = user
        self.added_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class orderservice_purchaseorder(IntPKEntity):
    def __init__(
        self,
        id: int,
        po_code: str,
        po_date: datetime,
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
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        received_by_user_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        supplier_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(po_date, datetime):
            raise ValidationError("po_date must be datetime")
        _ensure_optional_datetime("expected_delivery_date", expected_delivery_date)
        _ensure_decimal("total_amount", total_amount)
        _ensure_decimal("paid_amount", paid_amount)
        _ensure_decimal("due_amount", due_amount)
        _ensure_decimal("discount_amount", discount_amount)
        _ensure_decimal("shipping_amount", shipping_amount)
        _ensure_decimal("shipping_tax_percentage", shipping_tax_percentage)
        _ensure_decimal("shipping_tax_amount", shipping_tax_amount)
        _ensure_decimal("shipping_cancelled_amount", shipping_cancelled_amount)
        _ensure_decimal("shipping_cancelled_tax_amount", shipping_cancelled_tax_amount)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_datetime("approved_at", approved_at)
        _ensure_optional_datetime("cancelled_at", cancelled_at)
        _ensure_optional_str("cancelled_reason", cancelled_reason)
        _ensure_optional_datetime("received_at", received_at)
        _ensure_optional_datetime("returned_at", returned_at)

        _ensure_optional_positive_bigint("approved_by_user_id_id", approved_by_user_id_id)
        _ensure_optional_positive_bigint("cancelled_by_user_id_id", cancelled_by_user_id_id)
        _ensure_optional_positive_bigint("created_by_user_id_id", created_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("last_updated_by_user_id_id", last_updated_by_user_id_id)
        _ensure_optional_positive_bigint("received_by_user_id_id", received_by_user_id_id)
        _ensure_optional_positive_bigint("returned_by_user_id_id", returned_by_user_id_id)
        _ensure_optional_positive_bigint("supplier_id_id", supplier_id_id)
        _ensure_optional_positive_bigint("updated_by_user_id_id", updated_by_user_id_id)
        _ensure_optional_positive_int("warehouse_id_id", warehouse_id_id)

        self.po_code: str = po_code
        self.po_date: datetime = po_date
        self.expected_delivery_date: Optional[datetime] = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = total_amount
        self.paid_amount: Decimal = paid_amount
        self.due_amount: Decimal = due_amount
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.shipping_tax_amount: Decimal = shipping_tax_amount
        self.shipping_cancelled_amount: Decimal = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount: Decimal = shipping_cancelled_tax_amount
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: Optional[str] = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at

        self.approved_by_user_id_id: Optional[int] = approved_by_user_id_id
        self.cancelled_by_user_id_id: Optional[int] = cancelled_by_user_id_id
        self.created_by_user_id_id: Optional[int] = created_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.last_updated_by_user_id_id: Optional[int] = last_updated_by_user_id_id
        self.received_by_user_id_id: Optional[int] = received_by_user_id_id
        self.returned_by_user_id_id: Optional[int] = returned_by_user_id_id
        self.supplier_id_id: Optional[int] = supplier_id_id
        self.updated_by_user_id_id: Optional[int] = updated_by_user_id_id
        self.warehouse_id_id: Optional[int] = warehouse_id_id

        self.approved_by_user: Optional[userservices_users] = None
        self.cancelled_by_user: Optional[userservices_users] = None
        self.created_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.last_updated_by_user: Optional[userservices_users] = None
        self.received_by_user: Optional[userservices_users] = None
        self.returned_by_user: Optional[userservices_users] = None
        self.supplier: Optional[userservices_users] = None
        self.updated_by_user: Optional[userservices_users] = None
        self.warehouse: Optional[inventoryservices_warehouse] = None

    def set_warehouse(self, warehouse: Optional[inventoryservices_warehouse]) -> None:
        if warehouse is not None and not isinstance(warehouse, inventoryservices_warehouse):
            raise ValidationError("warehouse must be inventoryservices_warehouse or None")
        self.warehouse = warehouse
        self.warehouse_id_id = warehouse.id if warehouse is not None else None
        self.touch()

    def set_supplier(self, supplier: Optional[userservices_users]) -> None:
        if supplier is not None and not isinstance(supplier, userservices_users):
            raise ValidationError("supplier must be userservices_users or None")
        self.supplier = supplier
        self.supplier_id_id = supplier.id if supplier is not None else None
        self.touch()

    def set_created_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("created_by_user must be userservices_users or None")
        self.created_by_user = user
        self.created_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class orderservice_purchaseorderitems(IntPKEntity):
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
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        received_by_user_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("quantity_ordered", quantity_ordered)
        _ensure_non_negative_int("quantity_received", quantity_received)
        _ensure_non_negative_int("quantity_cancelled", quantity_cancelled)
        _ensure_non_negative_int("quantity_returned", quantity_returned)

        _ensure_decimal("buying_price", buying_price)
        _ensure_decimal("selling_price", selling_price)
        _ensure_decimal("discount_amount", discount_amount)
        _ensure_decimal("amount_paid", amount_paid)
        _ensure_decimal("amount_returned", amount_returned)
        _ensure_decimal("amount_cancelled", amount_cancelled)
        _ensure_decimal("amount_ordered", amount_ordered)
        _ensure_decimal("tax_percentage", tax_percentage)
        _ensure_decimal("tax_amount", tax_amount)
        _ensure_decimal("shipping_tax_percentage", shipping_tax_percentage)
        _ensure_decimal("shipping_amount", shipping_amount)
        _ensure_decimal("shipping_tax_amount", shipping_tax_amount)
        _ensure_decimal("shipping_cancelled_amount", shipping_cancelled_amount)
        _ensure_decimal("shipping_cancelled_tax_amount", shipping_cancelled_tax_amount)

        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_datetime("approved_at", approved_at)
        _ensure_optional_datetime("cancelled_at", cancelled_at)
        _ensure_optional_str("cancelled_reason", cancelled_reason)
        _ensure_optional_datetime("received_at", received_at)
        _ensure_optional_datetime("returned_at", returned_at)

        _ensure_optional_positive_bigint("approved_by_user_id_id", approved_by_user_id_id)
        _ensure_optional_positive_bigint("cancelled_by_user_id_id", cancelled_by_user_id_id)
        _ensure_optional_positive_bigint("created_by_user_id_id", created_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("last_updated_by_user_id_id", last_updated_by_user_id_id)
        _ensure_optional_positive_bigint("received_by_user_id_id", received_by_user_id_id)
        _ensure_optional_positive_bigint("returned_by_user_id_id", returned_by_user_id_id)
        _ensure_optional_positive_int("po_id_id", po_id_id)
        _ensure_optional_positive_int("product_id_id", product_id_id)
        _ensure_optional_positive_bigint("updated_by_user_id_id", updated_by_user_id_id)

        self.quantity_ordered: int = quantity_ordered
        self.quantity_received: int = quantity_received
        self.quantity_cancelled: int = quantity_cancelled
        self.quantity_returned: int = quantity_returned
        self.buying_price: Decimal = buying_price
        self.selling_price: Decimal = selling_price
        self.discount_amount: Decimal = discount_amount
        self.amount_paid: Decimal = amount_paid
        self.amount_returned: Decimal = amount_returned
        self.amount_cancelled: Decimal = amount_cancelled
        self.amount_ordered: Decimal = amount_ordered
        self.tax_percentage: Decimal = tax_percentage
        self.tax_amount: Decimal = tax_amount
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_tax_amount: Decimal = shipping_tax_amount
        self.shipping_cancelled_amount: Decimal = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount: Decimal = shipping_cancelled_tax_amount
        self.discount_type: str = discount_type
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: Optional[str] = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at

        self.approved_by_user_id_id: Optional[int] = approved_by_user_id_id
        self.cancelled_by_user_id_id: Optional[int] = cancelled_by_user_id_id
        self.created_by_user_id_id: Optional[int] = created_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.last_updated_by_user_id_id: Optional[int] = last_updated_by_user_id_id
        self.received_by_user_id_id: Optional[int] = received_by_user_id_id
        self.returned_by_user_id_id: Optional[int] = returned_by_user_id_id
        self.po_id_id: Optional[int] = po_id_id
        self.product_id_id: Optional[int] = product_id_id
        self.updated_by_user_id_id: Optional[int] = updated_by_user_id_id

        self.approved_by_user: Optional[userservices_users] = None
        self.cancelled_by_user: Optional[userservices_users] = None
        self.created_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.last_updated_by_user: Optional[userservices_users] = None
        self.received_by_user: Optional[userservices_users] = None
        self.returned_by_user: Optional[userservices_users] = None
        self.po: Optional[orderservice_purchaseorder] = None
        self.product: Optional[productservices_products] = None
        self.updated_by_user: Optional[userservices_users] = None

    def set_po(self, po: Optional[orderservice_purchaseorder]) -> None:
        if po is not None and not isinstance(po, orderservice_purchaseorder):
            raise ValidationError("po must be orderservice_purchaseorder or None")
        self.po = po
        self.po_id_id = po.id if po is not None else None
        self.touch()

    def set_product(self, product: Optional[productservices_products]) -> None:
        if product is not None and not isinstance(product, productservices_products):
            raise ValidationError("product must be productservices_products or None")
        self.product = product
        self.product_id_id = product.id if product is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class orderservice_purchaseorderlogs(IntPKEntity):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("created_by_user_id_id", created_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("po_id_id", po_id_id)

        self.comment: str = comment
        self.additional_details: Optional[JsonType] = additional_details

        self.created_by_user_id_id: Optional[int] = created_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.po_id_id: Optional[int] = po_id_id

        self.created_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.po: Optional[orderservice_purchaseorder] = None

    def set_po(self, po: Optional[orderservice_purchaseorder]) -> None:
        if po is not None and not isinstance(po, orderservice_purchaseorder):
            raise ValidationError("po must be orderservice_purchaseorder or None")
        self.po = po
        self.po_id_id = po.id if po is not None else None
        self.touch()


class orderservice_purchaseorderinwardedlog(IntPKEntity):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: Optional[datetime],
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        inwarded_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_datetime("inwarded_at", inwarded_at)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("inwarded_by_user_id_id", inwarded_by_user_id_id)
        _ensure_optional_positive_int("po_id_id", po_id_id)

        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.inwarded_at: Optional[datetime] = inwarded_at
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.inwarded_by_user_id_id: Optional[int] = inwarded_by_user_id_id
        self.po_id_id: Optional[int] = po_id_id

        self.domain_user: Optional[userservices_users] = None
        self.inwarded_by_user: Optional[userservices_users] = None
        self.po: Optional[orderservice_purchaseorder] = None

    def set_po(self, po: Optional[orderservice_purchaseorder]) -> None:
        if po is not None and not isinstance(po, orderservice_purchaseorder):
            raise ValidationError("po must be orderservice_purchaseorder or None")
        self.po = po
        self.po_id_id = po.id if po is not None else None
        self.touch()


class orderservice_purchaseorderiteminwardedlog(IntPKEntity):
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
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        po_item_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("inwarded_quantity", inwarded_quantity)
        _ensure_decimal("price", price)
        _ensure_decimal("tax_percentage", tax_percentage)
        _ensure_decimal("discount_amount", discount_amount)
        _ensure_decimal("shipping_amount", shipping_amount)
        _ensure_decimal("shipping_tax_percentage", shipping_tax_percentage)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("po_item_id_id", po_item_id_id)

        self.inwarded_quantity: int = inwarded_quantity
        self.price: Decimal = price
        self.tax_percentage: Decimal = tax_percentage
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.po_item_id_id: Optional[int] = po_item_id_id

        self.domain_user: Optional[userservices_users] = None
        self.po_item: Optional[orderservice_purchaseorderitems] = None

    def set_po_item(self, po_item: Optional[orderservice_purchaseorderitems]) -> None:
        if po_item is not None and not isinstance(po_item, orderservice_purchaseorderitems):
            raise ValidationError("po_item must be orderservice_purchaseorderitems or None")
        self.po_item = po_item
        self.po_item_id_id = po_item.id if po_item is not None else None
        self.touch()


class orderservice_salesorder(IntPKEntity):
    def __init__(
        self,
        id: int,
        so_code: str,
        so_date: datetime,
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
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        customer_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        received_by_user_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(so_date, datetime):
            raise ValidationError("so_date must be datetime")
        _ensure_optional_datetime("expected_delivery_date", expected_delivery_date)
        _ensure_decimal("total_amount", total_amount)
        _ensure_decimal("paid_amount", paid_amount)
        _ensure_decimal("due_amount", due_amount)
        _ensure_decimal("discount_amount", discount_amount)
        _ensure_decimal("shipping_amount", shipping_amount)
        _ensure_decimal("shipping_tax_percentage", shipping_tax_percentage)
        _ensure_decimal("shipping_tax_amount", shipping_tax_amount)
        _ensure_decimal("shipping_cancelled_amount", shipping_cancelled_amount)
        _ensure_decimal("shipping_cancelled_tax_amount", shipping_cancelled_tax_amount)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_datetime("approved_at", approved_at)
        _ensure_optional_datetime("cancelled_at", cancelled_at)
        _ensure_optional_str("cancelled_reason", cancelled_reason)
        _ensure_optional_datetime("received_at", received_at)
        _ensure_optional_datetime("returned_at", returned_at)

        _ensure_optional_positive_bigint("approved_by_user_id_id", approved_by_user_id_id)
        _ensure_optional_positive_bigint("cancelled_by_user_id_id", cancelled_by_user_id_id)
        _ensure_optional_positive_bigint("created_by_user_id_id", created_by_user_id_id)
        _ensure_optional_positive_bigint("customer_id_id", customer_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("last_updated_by_user_id_id", last_updated_by_user_id_id)
        _ensure_optional_positive_bigint("received_by_user_id_id", received_by_user_id_id)
        _ensure_optional_positive_bigint("returned_by_user_id_id", returned_by_user_id_id)
        _ensure_optional_positive_int("po_id_id", po_id_id)
        _ensure_optional_positive_int("product_id_id", product_id_id)
        _ensure_optional_positive_bigint("updated_by_user_id_id", updated_by_user_id_id)

        self.so_code: str = so_code
        self.so_date: datetime = so_date
        self.expected_delivery_date: Optional[datetime] = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = total_amount
        self.paid_amount: Decimal = paid_amount
        self.due_amount: Decimal = due_amount
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.shipping_tax_amount: Decimal = shipping_tax_amount
        self.shipping_cancelled_amount: Decimal = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount: Decimal = shipping_cancelled_tax_amount
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: Optional[str] = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at

        self.approved_by_user_id_id: Optional[int] = approved_by_user_id_id
        self.cancelled_by_user_id_id: Optional[int] = cancelled_by_user_id_id
        self.created_by_user_id_id: Optional[int] = created_by_user_id_id
        self.customer_id_id: Optional[int] = customer_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.last_updated_by_user_id_id: Optional[int] = last_updated_by_user_id_id
        self.received_by_user_id_id: Optional[int] = received_by_user_id_id
        self.returned_by_user_id_id: Optional[int] = returned_by_user_id_id
        self.po_id_id: Optional[int] = po_id_id
        self.product_id_id: Optional[int] = product_id_id
        self.updated_by_user_id_id: Optional[int] = updated_by_user_id_id

        self.approved_by_user: Optional[userservices_users] = None
        self.cancelled_by_user: Optional[userservices_users] = None
        self.created_by_user: Optional[userservices_users] = None
        self.customer: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.last_updated_by_user: Optional[userservices_users] = None
        self.received_by_user: Optional[userservices_users] = None
        self.returned_by_user: Optional[userservices_users] = None
        self.po: Optional[orderservice_purchaseorder] = None
        self.product: Optional[productservices_products] = None
        self.updated_by_user: Optional[userservices_users] = None

    def set_customer(self, customer: Optional[userservices_users]) -> None:
        if customer is not None and not isinstance(customer, userservices_users):
            raise ValidationError("customer must be userservices_users or None")
        self.customer = customer
        self.customer_id_id = customer.id if customer is not None else None
        self.touch()

    def set_po(self, po: Optional[orderservice_purchaseorder]) -> None:
        if po is not None and not isinstance(po, orderservice_purchaseorder):
            raise ValidationError("po must be orderservice_purchaseorder or None")
        self.po = po
        self.po_id_id = po.id if po is not None else None
        self.touch()

    def set_product(self, product: Optional[productservices_products]) -> None:
        if product is not None and not isinstance(product, productservices_products):
            raise ValidationError("product must be productservices_products or None")
        self.product = product
        self.product_id_id = product.id if product is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class orderservice_salesorderorderitems(IntPKEntity):
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
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        shipped_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        shipped_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("quantity_ordered", quantity_ordered)
        _ensure_non_negative_int("quantity_delivered", quantity_delivered)
        _ensure_non_negative_int("quantity_shipped", quantity_shipped)
        _ensure_non_negative_int("quantity_cancelled", quantity_cancelled)
        _ensure_non_negative_int("quantity_returned", quantity_returned)

        _ensure_decimal("purchase_price", purchase_price)
        _ensure_decimal("discount_amount", discount_amount)
        _ensure_decimal("amount_paid", amount_paid)
        _ensure_decimal("amount_returned", amount_returned)
        _ensure_decimal("amount_cancelled", amount_cancelled)
        _ensure_decimal("amount_ordered", amount_ordered)
        _ensure_decimal("tax_percentage", tax_percentage)
        _ensure_decimal("tax_amount", tax_amount)
        _ensure_decimal("shipping_amount", shipping_amount)
        _ensure_decimal("shipping_tax_amount", shipping_tax_amount)
        _ensure_decimal("shipping_cancelled_amount", shipping_cancelled_amount)
        _ensure_decimal("shipping_cancelled_tax_amount", shipping_cancelled_tax_amount)

        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_datetime("approved_at", approved_at)
        _ensure_optional_datetime("cancelled_at", cancelled_at)
        _ensure_optional_str("cancelled_reason", cancelled_reason)
        _ensure_optional_datetime("shipped_at", shipped_at)
        _ensure_optional_datetime("returned_at", returned_at)

        _ensure_optional_positive_bigint("approved_by_user_id_id", approved_by_user_id_id)
        _ensure_optional_positive_bigint("cancelled_by_user_id_id", cancelled_by_user_id_id)
        _ensure_optional_positive_bigint("created_by_user_id_id", created_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("product_id_id", product_id_id)
        _ensure_optional_positive_bigint("returned_by_user_id_id", returned_by_user_id_id)
        _ensure_optional_positive_bigint("shipped_by_user_id_id", shipped_by_user_id_id)
        _ensure_optional_positive_int("so_id_id", so_id_id)
        _ensure_optional_positive_bigint("updated_by_user_id_id", updated_by_user_id_id)

        self.quantity_ordered: int = quantity_ordered
        self.quantity_delivered: int = quantity_delivered
        self.quantity_shipped: int = quantity_shipped
        self.quantity_cancelled: int = quantity_cancelled
        self.quantity_returned: int = quantity_returned
        self.purchase_price: Decimal = purchase_price
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.amount_paid: Decimal = amount_paid
        self.amount_returned: Decimal = amount_returned
        self.amount_cancelled: Decimal = amount_cancelled
        self.amount_ordered: Decimal = amount_ordered
        self.tax_percentage: Decimal = tax_percentage
        self.tax_amount: Decimal = tax_amount
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_type: str = shipping_type
        self.shipping_tax_amount: Decimal = shipping_tax_amount
        self.shipping_cancelled_amount: Decimal = shipping_cancelled_amount
        self.shipping_cancelled_tax_amount: Decimal = shipping_cancelled_tax_amount
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: Optional[str] = cancelled_reason
        self.shipped_at: Optional[datetime] = shipped_at
        self.returned_at: Optional[datetime] = returned_at

        self.approved_by_user_id_id: Optional[int] = approved_by_user_id_id
        self.cancelled_by_user_id_id: Optional[int] = cancelled_by_user_id_id
        self.created_by_user_id_id: Optional[int] = created_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.product_id_id: Optional[int] = product_id_id
        self.returned_by_user_id_id: Optional[int] = returned_by_user_id_id
        self.shipped_by_user_id_id: Optional[int] = shipped_by_user_id_id
        self.so_id_id: Optional[int] = so_id_id
        self.updated_by_user_id_id: Optional[int] = updated_by_user_id_id

        self.approved_by_user: Optional[userservices_users] = None
        self.cancelled_by_user: Optional[userservices_users] = None
        self.created_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.product: Optional[productservices_products] = None
        self.returned_by_user: Optional[userservices_users] = None
        self.shipped_by_user: Optional[userservices_users] = None
        self.so: Optional[orderservice_salesorder] = None
        self.updated_by_user: Optional[userservices_users] = None

    def set_so(self, so: Optional[orderservice_salesorder]) -> None:
        if so is not None and not isinstance(so, orderservice_salesorder):
            raise ValidationError("so must be orderservice_salesorder or None")
        self.so = so
        self.so_id_id = so.id if so is not None else None
        self.touch()

    def set_product(self, product: Optional[productservices_products]) -> None:
        if product is not None and not isinstance(product, productservices_products):
            raise ValidationError("product must be productservices_products or None")
        self.product = product
        self.product_id_id = product.id if product is not None else None
        self.touch()


class orderservice_salesorderlogs(IntPKEntity):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("created_by_user_id_id", created_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("so_id_id", so_id_id)

        self.comment: str = comment
        self.additional_details: Optional[JsonType] = additional_details

        self.created_by_user_id_id: Optional[int] = created_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.so_id_id: Optional[int] = so_id_id

        self.created_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.so: Optional[orderservice_salesorder] = None

    def set_so(self, so: Optional[orderservice_salesorder]) -> None:
        if so is not None and not isinstance(so, orderservice_salesorder):
            raise ValidationError("so must be orderservice_salesorder or None")
        self.so = so
        self.so_id_id = so.id if so is not None else None
        self.touch()


class orderservice_salesorderoutwardedlog(IntPKEntity):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: Optional[datetime],
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        outwarded_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_datetime("outwared_at", outwared_at)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("outwarded_by_user_id_id", outwarded_by_user_id_id)
        _ensure_optional_positive_int("so_id_id", so_id_id)

        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.outwared_at: Optional[datetime] = outwared_at
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.outwarded_by_user_id_id: Optional[int] = outwarded_by_user_id_id
        self.so_id_id: Optional[int] = so_id_id

        self.domain_user: Optional[userservices_users] = None
        self.outwarded_by_user: Optional[userservices_users] = None
        self.so: Optional[orderservice_salesorder] = None

    def set_so(self, so: Optional[orderservice_salesorder]) -> None:
        if so is not None and not isinstance(so, orderservice_salesorder):
            raise ValidationError("so must be orderservice_salesorder or None")
        self.so = so
        self.so_id_id = so.id if so is not None else None
        self.touch()


class orderservice_salesorderitemoutwardedlog(IntPKEntity):
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
        additional_details: Optional[JsonType],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        so_item_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("outwarded_quantity", outwarded_quantity)
        _ensure_decimal("price", price)
        _ensure_decimal("tax_percentage", tax_percentage)
        _ensure_decimal("discount_amount", discount_amount)
        _ensure_decimal("shipping_amount", shipping_amount)
        _ensure_decimal("shipping_tax_percentage", shipping_tax_percentage)
        _ensure_optional_json("additional_details", additional_details)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("so_item_id_id", so_item_id_id)

        self.outwarded_quantity: int = outwarded_quantity
        self.price: Decimal = price
        self.tax_percentage: Decimal = tax_percentage
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.additional_details: Optional[JsonType] = additional_details
        self.status: str = status

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.so_item_id_id: Optional[int] = so_item_id_id

        self.domain_user: Optional[userservices_users] = None
        self.so_item: Optional[orderservice_salesorderorderitems] = None

    def set_so_item(self, so_item: Optional[orderservice_salesorderorderitems]) -> None:
        if so_item is not None and not isinstance(so_item, orderservice_salesorderorderitems):
            raise ValidationError("so_item must be orderservice_salesorderorderitems or None")
        self.so_item = so_item
        self.so_item_id_id = so_item.id if so_item is not None else None
        self.touch()


class inventoryservices_inventory(IntPKEntity):
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
        additional_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        purchase_order_id_id: Optional[int] = None,
        purchase_order_item_id_id: Optional[int] = None,
        purchase_order_item_inwarded_item_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("quantity", quantity)
        _ensure_optional_float("discount_amout", discount_amout)
        _ensure_optional_datetime("mfg_date", mfg_date)
        _ensure_optional_datetime("received_date", received_date)
        _ensure_optional_datetime("expiry_date", expiry_date)
        _ensure_non_negative_int("quantity_inwarded", quantity_inwarded)
        _ensure_decimal("buy_price", buy_price)
        _ensure_decimal("sell_price", sell_price)
        _ensure_decimal("tax_percentage", tax_percentage)
        _ensure_optional_json("additional_details", additional_details)

        _ensure_optional_positive_bigint("added_by_user_id_id", added_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("product_id_id", product_id_id)
        _ensure_optional_positive_int("purchase_order_id_id", purchase_order_id_id)
        _ensure_optional_positive_int("purchase_order_item_id_id", purchase_order_item_id_id)
        _ensure_optional_positive_int("purchase_order_item_inwarded_item_id_id", purchase_order_item_inwarded_item_id_id)
        _ensure_optional_positive_int("rack_shelf_floor_id_id", rack_shelf_floor_id_id)
        _ensure_optional_positive_int("warehouse_id_id", warehouse_id_id)

        self.quantity: int = quantity
        self.mrp: str = mrp
        self.batch_number: str = batch_number
        self.discount_type: str = discount_type
        self.discount_amout: float = float(discount_amout)
        self.sr_no: str = sr_no
        self.mfg_date: Optional[datetime] = mfg_date
        self.uom: str = uom
        self.ptr: str = ptr
        self.received_date: Optional[datetime] = received_date
        self.expiry_date: Optional[datetime] = expiry_date
        self.quantity_inwarded: int = quantity_inwarded
        self.buy_price: Decimal = buy_price
        self.sell_price: Decimal = sell_price
        self.tax_percentage: Decimal = tax_percentage
        self.stock_status: str = stock_status
        self.inward_type: str = inward_type
        self.additional_details: Optional[JsonType] = additional_details

        self.added_by_user_id_id: Optional[int] = added_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.product_id_id: Optional[int] = product_id_id
        self.purchase_order_id_id: Optional[int] = purchase_order_id_id
        self.purchase_order_item_id_id: Optional[int] = purchase_order_item_id_id
        self.purchase_order_item_inwarded_item_id_id: Optional[int] = purchase_order_item_inwarded_item_id_id
        self.rack_shelf_floor_id_id: Optional[int] = rack_shelf_floor_id_id
        self.warehouse_id_id: Optional[int] = warehouse_id_id

        self.added_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.product: Optional[productservices_products] = None
        self.purchase_order: Optional[orderservice_purchaseorder] = None
        self.purchase_order_item: Optional[orderservice_purchaseorderitems] = None
        self.purchase_order_item_inwarded_item: Optional[orderservice_purchaseorderiteminwardedlog] = None
        self.rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None
        self.warehouse: Optional[inventoryservices_warehouse] = None

    def set_product(self, product: Optional[productservices_products]) -> None:
        if product is not None and not isinstance(product, productservices_products):
            raise ValidationError("product must be productservices_products or None")
        self.product = product
        self.product_id_id = product.id if product is not None else None
        self.touch()

    def set_warehouse(self, warehouse: Optional[inventoryservices_warehouse]) -> None:
        if warehouse is not None and not isinstance(warehouse, inventoryservices_warehouse):
            raise ValidationError("warehouse must be inventoryservices_warehouse or None")
        self.warehouse = warehouse
        self.warehouse_id_id = warehouse.id if warehouse is not None else None
        self.touch()

    def set_rack_shelf_floor(self, rsf: Optional[inventoryservices_rackandshelvesandfloor]) -> None:
        if rsf is not None and not isinstance(rsf, inventoryservices_rackandshelvesandfloor):
            raise ValidationError("rack_shelf_floor must be inventoryservices_rackandshelvesandfloor or None")
        self.rack_shelf_floor = rsf
        self.rack_shelf_floor_id_id = rsf.id if rsf is not None else None
        self.touch()

    def set_purchase_order(self, po: Optional[orderservice_purchaseorder]) -> None:
        if po is not None and not isinstance(po, orderservice_purchaseorder):
            raise ValidationError("purchase_order must be orderservice_purchaseorder or None")
        self.purchase_order = po
        self.purchase_order_id_id = po.id if po is not None else None
        self.touch()

    def set_purchase_order_item(self, po_item: Optional[orderservice_purchaseorderitems]) -> None:
        if po_item is not None and not isinstance(po_item, orderservice_purchaseorderitems):
            raise ValidationError("purchase_order_item must be orderservice_purchaseorderitems or None")
        self.purchase_order_item = po_item
        self.purchase_order_item_id_id = po_item.id if po_item is not None else None
        self.touch()

    def set_purchase_order_item_inwarded_item(self, inwarded: Optional[orderservice_purchaseorderiteminwardedlog]) -> None:
        if inwarded is not None and not isinstance(inwarded, orderservice_purchaseorderiteminwardedlog):
            raise ValidationError("purchase_order_item_inwarded_item must be orderservice_purchaseorderiteminwardedlog or None")
        self.purchase_order_item_inwarded_item = inwarded
        self.purchase_order_item_inwarded_item_id_id = inwarded.id if inwarded is not None else None
        self.touch()

    def set_added_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        self.added_by_user = user
        self.added_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class inventoryservices_inventorylog(IntPKEntity):
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Optional[JsonType],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        inventory_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_non_negative_int("quantity", quantity)
        _ensure_optional_json("additional_details", additional_details)

        _ensure_optional_positive_bigint("added_by_user_id_id", added_by_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_int("inventory_id_id", inventory_id_id)
        _ensure_optional_positive_int("po_id_id", po_id_id)
        _ensure_optional_positive_int("so_id_id", so_id_id)
        _ensure_optional_positive_int("rack_shelf_floor_id_id", rack_shelf_floor_id_id)
        _ensure_optional_positive_int("warehouse_id_id", warehouse_id_id)

        self.quantity: int = quantity
        self.status: str = status
        self.additional_details: Optional[JsonType] = additional_details

        self.added_by_user_id_id: Optional[int] = added_by_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.inventory_id_id: Optional[int] = inventory_id_id
        self.po_id_id: Optional[int] = po_id_id
        self.so_id_id: Optional[int] = so_id_id
        self.rack_shelf_floor_id_id: Optional[int] = rack_shelf_floor_id_id
        self.warehouse_id_id: Optional[int] = warehouse_id_id

        self.added_by_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.inventory: Optional[inventoryservices_inventory] = None
        self.po: Optional[orderservice_purchaseorder] = None
        self.so: Optional[orderservice_salesorder] = None
        self.rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None
        self.warehouse: Optional[inventoryservices_warehouse] = None

    def set_inventory(self, inventory: Optional[inventoryservices_inventory]) -> None:
        if inventory is not None and not isinstance(inventory, inventoryservices_inventory):
            raise ValidationError("inventory must be inventoryservices_inventory or None")
        self.inventory = inventory
        self.inventory_id_id = inventory.id if inventory is not None else None
        self.touch()

    def set_warehouse(self, warehouse: Optional[inventoryservices_warehouse]) -> None:
        if warehouse is not None and not isinstance(warehouse, inventoryservices_warehouse):
            raise ValidationError("warehouse must be inventoryservices_warehouse or None")
        self.warehouse = warehouse
        self.warehouse_id_id = warehouse.id if warehouse is not None else None
        self.touch()

    def set_rack_shelf_floor(self, rsf: Optional[inventoryservices_rackandshelvesandfloor]) -> None:
        if rsf is not None and not isinstance(rsf, inventoryservices_rackandshelvesandfloor):
            raise ValidationError("rack_shelf_floor must be inventoryservices_rackandshelvesandfloor or None")
        self.rack_shelf_floor = rsf
        self.rack_shelf_floor_id_id = rsf.id if rsf is not None else None
        self.touch()

    def set_po(self, po: Optional[orderservice_purchaseorder]) -> None:
        if po is not None and not isinstance(po, orderservice_purchaseorder):
            raise ValidationError("po must be orderservice_purchaseorder or None")
        self.po = po
        self.po_id_id = po.id if po is not None else None
        self.touch()

    def set_so(self, so: Optional[orderservice_salesorder]) -> None:
        if so is not None and not isinstance(so, orderservice_salesorder):
            raise ValidationError("so must be orderservice_salesorder or None")
        self.so = so
        self.so_id_id = so.id if so is not None else None
        self.touch()

    def set_added_by_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        self.added_by_user = user
        self.added_by_user_id_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class productservices_productquestions(IntPKEntity):
    def __init__(
        self,
        id: int,
        question: str,
        answer: str,
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        answer_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        question_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_positive_bigint("answer_user_id_id", answer_user_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("question_user_id_id", question_user_id_id)
        _ensure_optional_positive_int("product_id_id", product_id_id)

        self.question: str = question
        self.answer: str = answer
        self.status: str = status

        self.answer_user_id_id: Optional[int] = answer_user_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.question_user_id_id: Optional[int] = question_user_id_id
        self.product_id_id: Optional[int] = product_id_id

        self.answer_user: Optional[userservices_users] = None
        self.domain_user: Optional[userservices_users] = None
        self.question_user: Optional[userservices_users] = None
        self.product: Optional[productservices_products] = None

    def set_product(self, product: Optional[productservices_products]) -> None:
        if product is not None and not isinstance(product, productservices_products):
            raise ValidationError("product must be productservices_products or None")
        self.product = product
        self.product_id_id = product.id if product is not None else None
        self.touch()


class productservices_productreviews(IntPKEntity):
    def __init__(
        self,
        id: int,
        review_images: Optional[JsonType],
        rating: float,
        reviews: str,
        status: str,
        domain_user_id_id: Optional[int] = None,
        review_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        _ensure_optional_json("review_images", review_images)
        _ensure_optional_float("rating", rating)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("review_user_id_id", review_user_id_id)
        _ensure_optional_positive_int("product_id_id", product_id_id)

        self.review_images: Optional[JsonType] = review_images
        self.rating: float = float(rating)
        self.reviews: str = reviews
        self.status: str = status

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.review_user_id_id: Optional[int] = review_user_id_id
        self.product_id_id: Optional[int] = product_id_id

        self.domain_user: Optional[userservices_users] = None
        self.review_user: Optional[userservices_users] = None
        self.product: Optional[productservices_products] = None

    def set_product(self, product: Optional[productservices_products]) -> None:
        if product is not None and not isinstance(product, productservices_products):
            raise ValidationError("product must be productservices_products or None")
        self.product = product
        self.product_id_id = product.id if product is not None else None
        self.touch()


class userservices_usershippingaddress(IntPKEntity):
    def __init__(
        self,
        id: int,
        address_type: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        country: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        _ensure_optional_positive_bigint("user_id", user_id)

        self.address_type: str = address_type
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.pincode: str = pincode
        self.country: str = country

        self.user_id: Optional[int] = user_id
        self.user: Optional[userservices_users] = None

    def set_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user = user
        self.user_id = user.id if user is not None else None
        self.touch()


class userservices_activitylog(IntPKEntity):
    def __init__(
        self,
        id: int,
        activity: str,
        activity_type: str,
        activity_date: datetime,
        activity_ip: str,
        activity_device: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(activity_date, datetime):
            raise ValidationError("activity_date must be datetime")
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("user_id", user_id)

        self.activity: str = activity
        self.activity_type: str = activity_type
        self.activity_date: datetime = activity_date
        self.activity_ip: str = activity_ip
        self.activity_device: str = activity_device

        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.user_id: Optional[int] = user_id

        self.domain_user: Optional[userservices_users] = None
        self.user: Optional[userservices_users] = None

    def set_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user = user
        self.user_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class userservices_modules(IntPKEntity):
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        parent_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(is_menu, bool):
            raise ValidationError("is_menu must be bool")
        if not isinstance(is_active, bool):
            raise ValidationError("is_active must be bool")
        _ensure_non_negative_int("display_order", display_order)
        _ensure_optional_positive_int("parent_id_id", parent_id_id)

        self.module_name: str = module_name
        self.module_icon: str = module_icon
        self.is_menu: bool = is_menu
        self.is_active: bool = is_active
        self.module_url: str = module_url
        self.display_order: int = display_order
        self.module_description: str = module_description

        self.parent_id_id: Optional[int] = parent_id_id
        self.parent: Optional[userservices_modules] = None

    def set_parent(self, parent: Optional["userservices_modules"]) -> None:
        if parent is not None and not isinstance(parent, userservices_modules):
            raise ValidationError("parent must be userservices_modules or None")
        if parent is not None and parent.id == self.id:
            raise ValidationError("module cannot be its own parent")
        self.parent = parent
        self.parent_id_id = parent.id if parent is not None else None
        self.touch()


class userservices_userpermissions(IntPKEntity):
    def __init__(
        self,
        id: int,
        is_view: bool,
        is_add: bool,
        is_edit: bool,
        is_delete: bool,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        module_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for n, v in (("is_view", is_view), ("is_add", is_add), ("is_edit", is_edit), ("is_delete", is_delete)):
            if not isinstance(v, bool):
                raise ValidationError(f"{n} must be bool")
        _ensure_optional_positive_int("module_id_id", module_id_id)
        _ensure_optional_positive_bigint("domain_user_id_id", domain_user_id_id)
        _ensure_optional_positive_bigint("user_id", user_id)

        self.is_view: bool = is_view
        self.is_add: bool = is_add
        self.is_edit: bool = is_edit
        self.is_delete: bool = is_delete

        self.module_id_id: Optional[int] = module_id_id
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.user_id: Optional[int] = user_id

        self.module: Optional[userservices_modules] = None
        self.domain_user: Optional[userservices_users] = None
        self.user: Optional[userservices_users] = None

    def set_module(self, module: Optional[userservices_modules]) -> None:
        if module is not None and not isinstance(module, userservices_modules):
            raise ValidationError("module must be userservices_modules or None")
        self.module = module
        self.module_id_id = module.id if module is not None else None
        self.touch()

    def set_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user = user
        self.user_id = user.id if user is not None else None
        self.touch()

    def set_domain_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.domain_user = user
        self.domain_user_id_id = user.id if user is not None else None
        self.touch()


class auth_group(IntPKEntity):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        self.name: str = name


class django_content_type(IntPKEntity):
    def __init__(self, id: int, app_label: str, model: str) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        self.app_label: str = app_label
        self.model: str = model


class auth_permission(IntPKEntity):
    def __init__(
        self,
        id: int,
        name: str,
        codename: str,
        content_type_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        _ensure_optional_positive_int("content_type_id", content_type_id)
        self.name: str = name
        self.codename: str = codename
        self.content_type_id: Optional[int] = content_type_id
        self.content_type: Optional[django_content_type] = None

    def set_content_type(self, ct: Optional[django_content_type]) -> None:
        if ct is not None and not isinstance(ct, django_content_type):
            raise ValidationError("content_type must be django_content_type or None")
        self.content_type = ct
        self.content_type_id = ct.id if ct is not None else None
        self.touch()


class auth_group_permissions(BigIntPKEntity):
    def __init__(self, id: int, group_id: Optional[int] = None, permission_id: Optional[int] = None) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        _ensure_optional_positive_int("group_id", group_id)
        _ensure_optional_positive_int("permission_id", permission_id)
        self.group_id: Optional[int] = group_id
        self.permission_id: Optional[int] = permission_id
        self.group: Optional[auth_group] = None
        self.permission: Optional[auth_permission] = None

    def set_group(self, group: Optional[auth_group]) -> None:
        if group is not None and not isinstance(group, auth_group):
            raise ValidationError("group must be auth_group or None")
        self.group = group
        self.group_id = group.id if group is not None else None
        self.touch()

    def set_permission(self, perm: Optional[auth_permission]) -> None:
        if perm is not None and not isinstance(perm, auth_permission):
            raise ValidationError("permission must be auth_permission or None")
        self.permission = perm
        self.permission_id = perm.id if perm is not None else None
        self.touch()


class userservices_users_groups(BigIntPKEntity):
    def __init__(self, id: int, users_id: Optional[int] = None, group_id: Optional[int] = None) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        _ensure_optional_positive_bigint("users_id", users_id)
        _ensure_optional_positive_int("group_id", group_id)
        self.users_id: Optional[int] = users_id
        self.group_id: Optional[int] = group_id
        self.user: Optional[userservices_users] = None
        self.group: Optional[auth_group] = None

    def set_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user = user
        self.users_id = user.id if user is not None else None
        self.touch()

    def set_group(self, group: Optional[auth_group]) -> None:
        if group is not None and not isinstance(group, auth_group):
            raise ValidationError("group must be auth_group or None")
        self.group = group
        self.group_id = group.id if group is not None else None
        self.touch()


class userservices_users_user_permissions(BigIntPKEntity):
    def __init__(self, id: int, users_id: Optional[int] = None, permission_id: Optional[int] = None) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        _ensure_optional_positive_bigint("users_id", users_id)
        _ensure_optional_positive_int("permission_id", permission_id)
        self.users_id: Optional[int] = users_id
        self.permission_id: Optional[int] = permission_id
        self.user: Optional[userservices_users] = None
        self.permission: Optional[auth_permission] = None

    def set_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user = user
        self.users_id = user.id if user is not None else None
        self.touch()

    def set_permission(self, perm: Optional[auth_permission]) -> None:
        if perm is not None and not isinstance(perm, auth_permission):
            raise ValidationError("permission must be auth_permission or None")
        self.permission = perm
        self.permission_id = perm.id if perm is not None else None
        self.touch()


class django_admin_log(IntPKEntity):
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str,
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        if not isinstance(action_time, datetime):
            raise ValidationError("action_time must be datetime")
        if not isinstance(action_flag, int) or action_flag < 0:
            raise ValidationError("action_flag must be a non-negative int")
        _ensure_optional_positive_int("content_type_id", content_type_id)
        _ensure_optional_positive_bigint("user_id", user_id)

        self.action_time: datetime = action_time
        self.object_id: str = object_id
        self.object_repr: str = object_repr
        self.action_flag: int = action_flag
        self.change_message: str = change_message

        self.content_type_id: Optional[int] = content_type_id
        self.user_id: Optional[int] = user_id

        self.content_type: Optional[django_content_type] = None
        self.user: Optional[userservices_users] = None

    def set_content_type(self, ct: Optional[django_content_type]) -> None:
        if ct is not None and not isinstance(ct, django_content_type):
            raise ValidationError("content_type must be django_content_type or None")
        self.content_type = ct
        self.content_type_id = ct.id if ct is not None else None
        self.touch()

    def set_user(self, user: Optional[userservices_users]) -> None:
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user = user
        self.user_id = user.id if user is not None else None
        self.touch()


class django_migrations(BigIntPKEntity):
    def __init__(self, id: int, app: str, name: str, applied: datetime) -> None:
        super().__init__(id=id, created_at=None, updated_at=None)
        if not isinstance(applied, datetime):
            raise ValidationError("applied must be datetime")
        self.app: str = app
        self.name: str = name
        self.applied: datetime = applied


class django_session(StringPKEntity):
    def __init__(self, session_key: str, session_data: str, expire_date: datetime) -> None:
        super().__init__(session_key=session_key, created_at=None, updated_at=None)
        if not isinstance(expire_date, datetime):
            raise ValidationError("expire_date must be datetime")
        self.session_data: str = session_data
        self.expire_date: datetime = expire_date