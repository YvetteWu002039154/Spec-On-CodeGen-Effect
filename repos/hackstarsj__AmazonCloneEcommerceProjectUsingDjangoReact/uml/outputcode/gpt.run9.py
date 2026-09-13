from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


class ModelBase:
    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        now = datetime.utcnow()
        self.created_at: datetime = created_at or now
        self.updated_at: datetime = updated_at or now

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class IntPKMixin:
    def __init__(self, id: int, *args: Any, **kwargs: Any) -> None:
        if not isinstance(id, int):
            raise TypeError("id must be int")
        self.id: int = id
        super().__init__(*args, **kwargs)


class BigIntPKMixin:
    def __init__(self, id: int, *args: Any, **kwargs: Any) -> None:
        if not isinstance(id, int):
            raise TypeError("id must be int (bigint)")
        self.id: int = id
        super().__init__(*args, **kwargs)


class StringPKMixin:
    def __init__(self, session_key: str, *args: Any, **kwargs: Any) -> None:
        if not isinstance(session_key, str) or not session_key:
            raise ValueError("session_key must be non-empty str")
        self.session_key: str = session_key
        super().__init__(*args, **kwargs)


class UserservicesUsers(BigIntPKMixin, ModelBase):
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
        social_media_links: Optional[JsonDict],
        addition_details: Optional[JsonDict],
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
        domain_user_id: Optional["UserservicesUsers"] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.is_superuser: bool = bool(is_superuser)
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.is_staff: bool = bool(is_staff)
        self.is_active: bool = bool(is_active)
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
        self.domain_user_id: Optional[UserservicesUsers] = domain_user_id


class UserservicesUserShippingAddress(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        address_type: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        country: str,
        user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.address_type: str = address_type
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.pincode: str = pincode
        self.country: str = country
        self.user_id: UserservicesUsers = user


class UserservicesActivityLog(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        activity: str,
        activity_type: str,
        activity_date: datetime,
        activity_ip: str,
        activity_device: str,
        domain_user: UserservicesUsers,
        user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.activity: str = activity
        self.activity_type: str = activity_type
        self.activity_date: datetime = activity_date
        self.activity_ip: str = activity_ip
        self.activity_device: str = activity_device
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.user_id: UserservicesUsers = user


class UserservicesModules(IntPKMixin, ModelBase):
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
        parent: Optional["UserservicesModules"] = None,
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
        self.parent_id_id: Optional[UserservicesModules] = parent


class UserservicesUserPermissions(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        is_view: bool,
        is_add: bool,
        is_edit: bool,
        is_delete: bool,
        module: UserservicesModules,
        domain_user: UserservicesUsers,
        user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.is_view: bool = bool(is_view)
        self.is_add: bool = bool(is_add)
        self.is_edit: bool = bool(is_edit)
        self.is_delete: bool = bool(is_delete)
        self.module_id_id: UserservicesModules = module
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.user_id: UserservicesUsers = user


class AuthGroup(IntPKMixin):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id)
        self.name: str = name


class DjangoContentType(IntPKMixin):
    def __init__(self, id: int, app_label: str, model: str) -> None:
        super().__init__(id=id)
        self.app_label: str = app_label
        self.model: str = model


class AuthPermission(IntPKMixin):
    def __init__(self, id: int, name: str, codename: str, content_type: DjangoContentType) -> None:
        super().__init__(id=id)
        self.name: str = name
        self.codename: str = codename
        self.content_type_id: DjangoContentType = content_type


class UserservicesUsersGroups(BigIntPKMixin):
    def __init__(self, id: int, users: UserservicesUsers, group: AuthGroup) -> None:
        super().__init__(id=id)
        self.users_id: UserservicesUsers = users
        self.group_id: AuthGroup = group


class UserservicesUsersUserPermissions(BigIntPKMixin):
    def __init__(self, id: int, users: UserservicesUsers, permission: AuthPermission) -> None:
        super().__init__(id=id)
        self.users_id: UserservicesUsers = users
        self.permission_id: AuthPermission = permission


class AuthGroupPermissions(BigIntPKMixin):
    def __init__(self, id: int, group: AuthGroup, permission: AuthPermission) -> None:
        super().__init__(id=id)
        self.group_id: AuthGroup = group
        self.permission_id: AuthPermission = permission


class DjangoAdminLog(IntPKMixin):
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str,
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type: DjangoContentType,
        user: UserservicesUsers,
    ) -> None:
        super().__init__(id=id)
        self.action_time: datetime = action_time
        self.object_id: str = object_id
        self.object_repr: str = object_repr
        self.action_flag: int = int(action_flag)
        self.change_message: str = change_message
        self.content_type_id: DjangoContentType = content_type
        self.user_id: UserservicesUsers = user


class DjangoMigrations(BigIntPKMixin):
    def __init__(self, id: int, app: str, name: str, applied: datetime) -> None:
        super().__init__(id=id)
        self.app: str = app
        self.name: str = name
        self.applied: datetime = applied


class DjangoSession(StringPKMixin):
    def __init__(self, session_key: str, session_data: str, expire_date: datetime) -> None:
        super().__init__(session_key=session_key)
        self.session_data: str = session_data
        self.expire_date: datetime = expire_date


class ProductservicesCategories(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        description: str,
        display_order: int,
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        parent: Optional["ProductservicesCategories"] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name: str = name
        self.image: str = image
        self.description: str = description
        self.display_order: int = int(display_order)
        self.added_by_user_id_id: UserservicesUsers = added_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.parent_id_id: Optional[ProductservicesCategories] = parent


class ProductservicesProducts(IntPKMixin, ModelBase):
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
        added_by_user: UserservicesUsers,
        category: ProductservicesCategories,
        domain_user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name: str = name
        self.image: JsonDict = dict(image or {})
        self.description: str = description
        self.specifications: JsonDict = dict(specifications or {})
        self.html_description: str = html_description
        self.highlights: JsonDict = dict(highlights or {})
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
        self.seo_keywords: JsonDict = dict(seo_keywords or {})
        self.addition_details: JsonDict = dict(addition_details or {})
        self.added_by_user_id_id: UserservicesUsers = added_by_user
        self.category_id_id: ProductservicesCategories = category
        self.domain_user_id_id: UserservicesUsers = domain_user


class ProductservicesProductQuestions(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        question: str,
        answer: str,
        status: str,
        answer_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        question_user: UserservicesUsers,
        product: ProductservicesProducts,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.question: str = question
        self.answer: str = answer
        self.status: str = status
        self.answer_user_id_id: UserservicesUsers = answer_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.question_user_id_id: UserservicesUsers = question_user
        self.product_id_id: ProductservicesProducts = product


class ProductservicesProductReviews(IntPKMixin):
    def __init__(
        self,
        id: int,
        review_images: Optional[JsonDict],
        rating: float,
        reviews: str,
        status: str,
        domain_user: UserservicesUsers,
        review_user: UserservicesUsers,
        product: ProductservicesProducts,
    ) -> None:
        super().__init__(id=id)
        self.review_images: JsonDict = dict(review_images or {})
        self.rating: float = float(rating)
        self.reviews: str = reviews
        self.status: str = status
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.review_user_id_id: UserservicesUsers = review_user
        self.product_id_id: ProductservicesProducts = product


class InventoryservicesWarehouse(IntPKMixin, ModelBase):
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
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        warehouse_manager: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
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
        self.added_by_user_id_id: UserservicesUsers = added_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.warehouse_manager_id: UserservicesUsers = warehouse_manager


class InventoryservicesRackAndShelvesAndFloor(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: Optional[JsonDict],
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        warehouse: InventoryservicesWarehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name: str = name
        self.rack: str = rack
        self.shelf: str = shelf
        self.floor: str = floor
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: UserservicesUsers = added_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.warehouse_id_id: InventoryservicesWarehouse = warehouse


class OrderservicePurchaseOrder(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        po_code: str,
        po_date: datetime,
        expected_delivery_date: datetime,
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
        approved_by_user: UserservicesUsers,
        cancelled_by_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        last_updated_by_user: UserservicesUsers,
        received_by_user: UserservicesUsers,
        returned_by_user: UserservicesUsers,
        supplier: UserservicesUsers,
        updated_by_user: UserservicesUsers,
        warehouse: InventoryservicesWarehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.po_code: str = po_code
        self.po_date: datetime = po_date
        self.expected_delivery_date: datetime = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = Decimal(total_amount)
        self.paid_amount: Decimal = Decimal(paid_amount)
        self.due_amount: Decimal = Decimal(due_amount)
        self.discount_amount: Decimal = Decimal(discount_amount)
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = Decimal(shipping_amount)
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = Decimal(shipping_tax_percentage)
        self.shipping_tax_amount: Decimal = Decimal(shipping_tax_amount)
        self.shipping_cancelled_amount: Decimal = Decimal(shipping_cancelled_amount)
        self.shipping_cancelled_tax_amount: Decimal = Decimal(shipping_cancelled_tax_amount)
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: UserservicesUsers = approved_by_user
        self.cancelled_by_user_id_id: UserservicesUsers = cancelled_by_user
        self.created_by_user_id_id: UserservicesUsers = created_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.last_updated_by_user_id_id: UserservicesUsers = last_updated_by_user
        self.received_by_user_id_id: UserservicesUsers = received_by_user
        self.returned_by_user_id_id: UserservicesUsers = returned_by_user
        self.supplier_id_id: UserservicesUsers = supplier
        self.updated_by_user_id_id: UserservicesUsers = updated_by_user
        self.warehouse_id_id: InventoryservicesWarehouse = warehouse


class OrderservicePurchaseOrderItems(IntPKMixin, ModelBase):
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
        approved_by_user: UserservicesUsers,
        cancelled_by_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        last_updated_by_user: UserservicesUsers,
        received_by_user: UserservicesUsers,
        returned_by_user: UserservicesUsers,
        po: OrderservicePurchaseOrder,
        product: ProductservicesProducts,
        updated_by_user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity_ordered: int = int(quantity_ordered)
        self.quantity_received: int = int(quantity_received)
        self.quantity_cancelled: int = int(quantity_cancelled)
        self.quantity_returned: int = int(quantity_returned)
        self.buying_price: Decimal = Decimal(buying_price)
        self.selling_price: Decimal = Decimal(selling_price)
        self.discount_amount: Decimal = Decimal(discount_amount)
        self.amount_paid: Decimal = Decimal(amount_paid)
        self.amount_returned: Decimal = Decimal(amount_returned)
        self.amount_cancelled: Decimal = Decimal(amount_cancelled)
        self.amount_ordered: Decimal = Decimal(amount_ordered)
        self.tax_percentage: Decimal = Decimal(tax_percentage)
        self.tax_amount: Decimal = Decimal(tax_amount)
        self.shipping_tax_percentage: Decimal = Decimal(shipping_tax_percentage)
        self.shipping_amount: Decimal = Decimal(shipping_amount)
        self.shipping_tax_amount: Decimal = Decimal(shipping_tax_amount)
        self.shipping_cancelled_amount: Decimal = Decimal(shipping_cancelled_amount)
        self.shipping_cancelled_tax_amount: Decimal = Decimal(shipping_cancelled_tax_amount)
        self.discount_type: str = discount_type
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: UserservicesUsers = approved_by_user
        self.cancelled_by_user_id_id: UserservicesUsers = cancelled_by_user
        self.created_by_user_id_id: UserservicesUsers = created_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.last_updated_by_user_id_id: UserservicesUsers = last_updated_by_user
        self.received_by_user_id_id: UserservicesUsers = received_by_user
        self.returned_by_user_id_id: UserservicesUsers = returned_by_user
        self.po_id_id: OrderservicePurchaseOrder = po
        self.product_id_id: ProductservicesProducts = product
        self.updated_by_user_id_id: UserservicesUsers = updated_by_user


class OrderservicePurchaseOrderLogs(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonDict],
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        po: OrderservicePurchaseOrder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.comment: str = comment
        self.additional_details: JsonDict = dict(additional_details or {})
        self.created_by_user_id_id: UserservicesUsers = created_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.po_id_id: OrderservicePurchaseOrder = po


class OrderservicePurchaseOrderInwardedLog(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: datetime,
        additional_details: Optional[JsonDict],
        status: str,
        domain_user: UserservicesUsers,
        inwarded_by_user: UserservicesUsers,
        po: OrderservicePurchaseOrder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.inwarded_at: datetime = inwarded_at
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.inwarded_by_user_id_id: UserservicesUsers = inwarded_by_user
        self.po_id_id: OrderservicePurchaseOrder = po


class OrderservicePurchaseOrderItemInwardedLog(IntPKMixin, ModelBase):
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
        domain_user: UserservicesUsers,
        po_item: OrderservicePurchaseOrderItems,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.inwarded_quantity: int = int(inwarded_quantity)
        self.price: Decimal = Decimal(price)
        self.tax_percentage: Decimal = Decimal(tax_percentage)
        self.discount_amount: Decimal = Decimal(discount_amount)
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = Decimal(shipping_amount)
        self.shipping_tax_percentage: Decimal = Decimal(shipping_tax_percentage)
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.po_item_id_id: OrderservicePurchaseOrderItems = po_item


class OrderserviceSalesOrder(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        so_code: str,
        so_date: datetime,
        expected_delivery_date: datetime,
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
        approved_by_user: UserservicesUsers,
        cancelled_by_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        customer: UserservicesUsers,
        domain_user: UserservicesUsers,
        last_updated_by_user: UserservicesUsers,
        received_by_user: UserservicesUsers,
        returned_by_user: UserservicesUsers,
        po: OrderservicePurchaseOrder,
        product: ProductservicesProducts,
        updated_by_user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.so_code: str = so_code
        self.so_date: datetime = so_date
        self.expected_delivery_date: datetime = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = Decimal(total_amount)
        self.paid_amount: Decimal = Decimal(paid_amount)
        self.due_amount: Decimal = Decimal(due_amount)
        self.discount_amount: Decimal = Decimal(discount_amount)
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = Decimal(shipping_amount)
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = Decimal(shipping_tax_percentage)
        self.shipping_tax_amount: Decimal = Decimal(shipping_tax_amount)
        self.shipping_cancelled_amount: Decimal = Decimal(shipping_cancelled_amount)
        self.shipping_cancelled_tax_amount: Decimal = Decimal(shipping_cancelled_tax_amount)
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: UserservicesUsers = approved_by_user
        self.cancelled_by_user_id_id: UserservicesUsers = cancelled_by_user
        self.created_by_user_id_id: UserservicesUsers = created_by_user
        self.customer_id_id: UserservicesUsers = customer
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.last_updated_by_user_id_id: UserservicesUsers = last_updated_by_user
        self.received_by_user_id_id: UserservicesUsers = received_by_user
        self.returned_by_user_id_id: UserservicesUsers = returned_by_user
        self.po_id_id: OrderservicePurchaseOrder = po
        self.product_id_id: ProductservicesProducts = product
        self.updated_by_user_id_id: UserservicesUsers = updated_by_user


class OrderserviceSalesOrderOrderItems(IntPKMixin, ModelBase):
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
        approved_by_user: UserservicesUsers,
        cancelled_by_user: UserservicesUsers,
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        product: ProductservicesProducts,
        returned_by_user: UserservicesUsers,
        shipped_by_user: UserservicesUsers,
        so: OrderserviceSalesOrder,
        updated_by_user: UserservicesUsers,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity_ordered: int = int(quantity_ordered)
        self.quantity_delivered: int = int(quantity_delivered)
        self.quantity_shipped: int = int(quantity_shipped)
        self.quantity_cancelled: int = int(quantity_cancelled)
        self.quantity_returned: int = int(quantity_returned)
        self.purchase_price: Decimal = Decimal(purchase_price)
        self.discount_amount: Decimal = Decimal(discount_amount)
        self.discount_type: str = discount_type
        self.amount_paid: Decimal = Decimal(amount_paid)
        self.amount_returned: Decimal = Decimal(amount_returned)
        self.amount_cancelled: Decimal = Decimal(amount_cancelled)
        self.amount_ordered: Decimal = Decimal(amount_ordered)
        self.tax_percentage: Decimal = Decimal(tax_percentage)
        self.tax_amount: Decimal = Decimal(tax_amount)
        self.shipping_amount: Decimal = Decimal(shipping_amount)
        self.shipping_type: str = shipping_type
        self.shipping_tax_amount: Decimal = Decimal(shipping_tax_amount)
        self.shipping_cancelled_amount: Decimal = Decimal(shipping_cancelled_amount)
        self.shipping_cancelled_tax_amount: Decimal = Decimal(shipping_cancelled_tax_amount)
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.shipped_at: Optional[datetime] = shipped_at
        self.returned_at: Optional[datetime] = returned_at
        self.approved_by_user_id_id: UserservicesUsers = approved_by_user
        self.cancelled_by_user_id_id: UserservicesUsers = cancelled_by_user
        self.created_by_user_id_id: UserservicesUsers = created_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.product_id_id: ProductservicesProducts = product
        self.returned_by_user_id_id: UserservicesUsers = returned_by_user
        self.shipped_by_user_id_id: UserservicesUsers = shipped_by_user
        self.so_id_id: OrderserviceSalesOrder = so
        self.updated_by_user_id_id: UserservicesUsers = updated_by_user


class OrderserviceSalesOrderLogs(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonDict],
        created_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        so: OrderserviceSalesOrder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.comment: str = comment
        self.additional_details: JsonDict = dict(additional_details or {})
        self.created_by_user_id_id: UserservicesUsers = created_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.so_id_id: OrderserviceSalesOrder = so


class OrderserviceSalesOrderOutwardedLog(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: datetime,
        additional_details: Optional[JsonDict],
        status: str,
        domain_user: UserservicesUsers,
        outwarded_by_user: UserservicesUsers,
        so: OrderserviceSalesOrder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.outwared_at: datetime = outwared_at
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.outwarded_by_user_id_id: UserservicesUsers = outwarded_by_user
        self.so_id_id: OrderserviceSalesOrder = so


class OrderserviceSalesOrderItemOutwardedLog(IntPKMixin, ModelBase):
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
        domain_user: UserservicesUsers,
        so_item: OrderserviceSalesOrderOrderItems,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.outwarded_quantity: int = int(outwarded_quantity)
        self.price: Decimal = Decimal(price)
        self.tax_percentage: Decimal = Decimal(tax_percentage)
        self.discount_amount: Decimal = Decimal(discount_amount)
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = Decimal(shipping_amount)
        self.shipping_tax_percentage: Decimal = Decimal(shipping_tax_percentage)
        self.additional_details: JsonDict = dict(additional_details or {})
        self.status: str = status
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.so_item_id_id: OrderserviceSalesOrderOrderItems = so_item


class InventoryservicesInventory(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        quantity: int,
        mrp: str,
        batch_number: str,
        discount_type: str,
        discount_amout: float,
        sr_no: str,
        mfg_date: datetime,
        uom: str,
        ptr: str,
        received_date: datetime,
        expiry_date: datetime,
        quantity_inwarded: int,
        buy_price: Decimal,
        sell_price: Decimal,
        tax_percentage: Decimal,
        stock_status: str,
        inward_type: str,
        additional_details: Optional[JsonDict],
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        product: ProductservicesProducts,
        purchase_order: OrderservicePurchaseOrder,
        purchase_order_item: OrderservicePurchaseOrderItems,
        purchase_order_item_inwarded_item: Optional[OrderservicePurchaseOrderItemInwardedLog],
        rack_shelf_floor: InventoryservicesRackAndShelvesAndFloor,
        warehouse: InventoryservicesWarehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity: int = int(quantity)
        self.mrp: str = mrp
        self.batch_number: str = batch_number
        self.discount_type: str = discount_type
        self.discount_amout: float = float(discount_amout)
        self.sr_no: str = sr_no
        self.mfg_date: datetime = mfg_date
        self.uom: str = uom
        self.ptr: str = ptr
        self.received_date: datetime = received_date
        self.expiry_date: datetime = expiry_date
        self.quantity_inwarded: int = int(quantity_inwarded)
        self.buy_price: Decimal = Decimal(buy_price)
        self.sell_price: Decimal = Decimal(sell_price)
        self.tax_percentage: Decimal = Decimal(tax_percentage)
        self.stock_status: str = stock_status
        self.inward_type: str = inward_type
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: UserservicesUsers = added_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.product_id_id: ProductservicesProducts = product
        self.purchase_order_id_id: OrderservicePurchaseOrder = purchase_order
        self.purchase_order_item_id_id: OrderservicePurchaseOrderItems = purchase_order_item
        self.purchase_order_item_inwarded_item_id_id: Optional[OrderservicePurchaseOrderItemInwardedLog] = (
            purchase_order_item_inwarded_item
        )
        self.rack_shelf_floor_id_id: InventoryservicesRackAndShelvesAndFloor = rack_shelf_floor
        self.warehouse_id_id: InventoryservicesWarehouse = warehouse


class InventoryservicesInventoryLog(IntPKMixin, ModelBase):
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Optional[JsonDict],
        added_by_user: UserservicesUsers,
        domain_user: UserservicesUsers,
        inventory: InventoryservicesInventory,
        po: Optional[OrderservicePurchaseOrder],
        so: Optional[OrderserviceSalesOrder],
        rack_shelf_floor: InventoryservicesRackAndShelvesAndFloor,
        warehouse: InventoryservicesWarehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity: int = int(quantity)
        self.status: str = status
        self.additional_details: JsonDict = dict(additional_details or {})
        self.added_by_user_id_id: UserservicesUsers = added_by_user
        self.domain_user_id_id: UserservicesUsers = domain_user
        self.inventory_id_id: InventoryservicesInventory = inventory
        self.po_id_id: Optional[OrderservicePurchaseOrder] = po
        self.so_id_id: Optional[OrderserviceSalesOrder] = so
        self.rack_shelf_floor_id_id: InventoryservicesRackAndShelvesAndFloor = rack_shelf_floor
        self.warehouse_id_id: InventoryservicesWarehouse = warehouse