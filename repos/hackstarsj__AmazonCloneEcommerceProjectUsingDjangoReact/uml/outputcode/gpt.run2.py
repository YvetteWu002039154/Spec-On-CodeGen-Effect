from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional


class ValidationError(ValueError):
    pass


class BaseEntity:
    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        now = datetime.utcnow()
        self.created_at: datetime = created_at or now
        self.updated_at: datetime = updated_at or now

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class BaseEntityWithIntId(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("id must be a positive int")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = id


class BaseEntityWithBigIntId(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("id must be a positive bigint (int)")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = id


class BaseEntityWithStringPk(BaseEntity):
    def __init__(self, pk: str, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(pk, str) or not pk:
            raise ValidationError("primary key must be a non-empty string")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.session_key: str = pk


def _ensure_decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        raise ValidationError(f"{field} cannot be None")
    try:
        return Decimal(str(value))
    except Exception as e:
        raise ValidationError(f"{field} must be a decimal-compatible value") from e


def _ensure_optional_decimal(value: Any, field: str) -> Optional[Decimal]:
    if value is None:
        return None
    return _ensure_decimal(value, field)


def _ensure_non_negative_int(value: Any, field: str) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{field} must be int")
    if value < 0:
        raise ValidationError(f"{field} must be non-negative")
    return value


def _ensure_optional_int(value: Any, field: str) -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValidationError(f"{field} must be int")
    return value


def _ensure_optional_str(value: Any, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be str")
    return value


def _ensure_optional_dict(value: Any, field: str) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be a dict (json)")
    return value


def _ensure_optional_list(value: Any, field: str) -> Optional[list]:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list (json)")
    return value


class userservices_users(BaseEntityWithBigIntId):
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
        dob: date,
        username: str,
        password: str,
        social_media_links: Optional[Dict[str, Any]],
        addition_details: Optional[Dict[str, Any]],
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
        domain_user_id_id: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.is_superuser: bool = bool(is_superuser)
        self.first_name: str = str(first_name)
        self.last_name: str = str(last_name)
        self.is_staff: bool = bool(is_staff)
        self.is_active: bool = bool(is_active)
        if not isinstance(date_joined, datetime):
            raise ValidationError("date_joined must be datetime")
        self.date_joined: datetime = date_joined
        self.name: str = str(name)
        self.email: str = str(email)
        self.phone: str = str(phone)
        self.address: str = str(address)
        self.city: str = str(city)
        self.state: str = str(state)
        self.pincode: str = str(pincode)
        self.country: str = str(country)
        self.profile_pic: str = str(profile_pic)
        self.account_status: str = str(account_status)
        self.role: str = str(role)
        if not isinstance(dob, date):
            raise ValidationError("dob must be date")
        self.dob: date = dob
        self.username: str = str(username)
        self.password: str = str(password)
        self.social_media_links: Optional[Dict[str, Any]] = _ensure_optional_dict(social_media_links, "social_media_links")
        self.addition_details: Optional[Dict[str, Any]] = _ensure_optional_dict(addition_details, "addition_details")
        self.language: str = str(language)
        self.departMent: str = str(departMent)
        self.designation: str = str(designation)
        self.time_zone: str = str(time_zone)
        if last_login is not None and not isinstance(last_login, datetime):
            raise ValidationError("last_login must be datetime or None")
        self.last_login: Optional[datetime] = last_login
        self.last_device: str = str(last_device)
        self.last_ip: str = str(last_ip)
        self.currency: str = str(currency)
        self.domain_name: str = str(domain_name)
        self.plan_type: str = str(plan_type)
        if domain_user_id_id is not None and not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users or None")
        self.domain_user_id_id: Optional[userservices_users] = domain_user_id_id


class userservices_usershippingaddress(BaseEntityWithIntId):
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
        self.address_type: str = str(address_type)
        self.address: str = str(address)
        self.city: str = str(city)
        self.state: str = str(state)
        self.pincode: str = str(pincode)
        self.country: str = str(country)
        if not isinstance(user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")
        self.user_id: userservices_users = user_id


class userservices_activitylog(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        activity: str,
        activity_type: str,
        activity_date: datetime,
        activity_ip: str,
        activity_device: str,
        domain_user_id_id: userservices_users,
        user_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.activity: str = str(activity)
        self.activity_type: str = str(activity_type)
        if not isinstance(activity_date, datetime):
            raise ValidationError("activity_date must be datetime")
        self.activity_date: datetime = activity_date
        self.activity_ip: str = str(activity_ip)
        self.activity_device: str = str(activity_device)
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.user_id: userservices_users = user_id


class userservices_modules(BaseEntityWithIntId):
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
        self.module_name: str = str(module_name)
        self.module_icon: str = str(module_icon)
        self.is_menu: bool = bool(is_menu)
        self.is_active: bool = bool(is_active)
        self.module_url: str = str(module_url)
        if not isinstance(display_order, int):
            raise ValidationError("display_order must be int")
        self.display_order: int = display_order
        self.module_description: str = str(module_description)
        if parent_id_id is not None and not isinstance(parent_id_id, userservices_modules):
            raise ValidationError("parent_id_id must be userservices_modules or None")
        self.parent_id_id: Optional[userservices_modules] = parent_id_id


class userservices_userpermissions(BaseEntityWithIntId):
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
        self.is_view: bool = bool(is_view)
        self.is_add: bool = bool(is_add)
        self.is_edit: bool = bool(is_edit)
        self.is_delete: bool = bool(is_delete)
        if not isinstance(module_id_id, userservices_modules):
            raise ValidationError("module_id_id must be userservices_modules")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")
        self.module_id_id: userservices_modules = module_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.user_id: userservices_users = user_id


class auth_group(BaseEntityWithIntId):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.name: str = str(name)


class django_content_type(BaseEntityWithIntId):
    def __init__(self, id: int, app_label: str, model: str) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.app_label: str = str(app_label)
        self.model: str = str(model)


class auth_permission(BaseEntityWithIntId):
    def __init__(self, id: int, name: str, codename: str, content_type_id: django_content_type) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.name: str = str(name)
        self.codename: str = str(codename)
        if not isinstance(content_type_id, django_content_type):
            raise ValidationError("content_type_id must be django_content_type")
        self.content_type_id: django_content_type = content_type_id


class auth_group_permissions(BaseEntityWithBigIntId):
    def __init__(self, id: int, group_id: auth_group, permission_id: auth_permission) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        if not isinstance(group_id, auth_group):
            raise ValidationError("group_id must be auth_group")
        if not isinstance(permission_id, auth_permission):
            raise ValidationError("permission_id must be auth_permission")
        self.group_id: auth_group = group_id
        self.permission_id: auth_permission = permission_id


class userservices_users_groups(BaseEntityWithBigIntId):
    def __init__(self, id: int, users_id: userservices_users, group_id: auth_group) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        if not isinstance(users_id, userservices_users):
            raise ValidationError("users_id must be userservices_users")
        if not isinstance(group_id, auth_group):
            raise ValidationError("group_id must be auth_group")
        self.users_id: userservices_users = users_id
        self.group_id: auth_group = group_id


class userservices_users_user_permissions(BaseEntityWithBigIntId):
    def __init__(self, id: int, users_id: userservices_users, permission_id: auth_permission) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        if not isinstance(users_id, userservices_users):
            raise ValidationError("users_id must be userservices_users")
        if not isinstance(permission_id, auth_permission):
            raise ValidationError("permission_id must be auth_permission")
        self.users_id: userservices_users = users_id
        self.permission_id: auth_permission = permission_id


class django_admin_log(BaseEntityWithIntId):
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
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        if not isinstance(action_time, datetime):
            raise ValidationError("action_time must be datetime")
        self.action_time: datetime = action_time
        self.object_id: str = str(object_id)
        self.object_repr: str = str(object_repr)
        if not isinstance(action_flag, int):
            raise ValidationError("action_flag must be int")
        self.action_flag: int = action_flag
        self.change_message: str = str(change_message)
        if not isinstance(content_type_id, django_content_type):
            raise ValidationError("content_type_id must be django_content_type")
        if not isinstance(user_id, userservices_users):
            raise ValidationError("user_id must be userservices_users")
        self.content_type_id: django_content_type = content_type_id
        self.user_id: userservices_users = user_id


class django_migrations(BaseEntityWithBigIntId):
    def __init__(self, id: int, app: str, name: str, applied: datetime) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.app: str = str(app)
        self.name: str = str(name)
        if not isinstance(applied, datetime):
            raise ValidationError("applied must be datetime")
        self.applied: datetime = applied


class django_session(BaseEntityWithStringPk):
    def __init__(self, session_key: str, session_data: str, expire_date: datetime) -> None:
        super().__init__(pk=session_key, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.session_data: str = str(session_data)
        if not isinstance(expire_date, datetime):
            raise ValidationError("expire_date must be datetime")
        self.expire_date: datetime = expire_date


class productservices_categories(BaseEntityWithIntId):
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
        self.name: str = str(name)
        self.image: str = str(image)
        self.description: str = str(description)
        if not isinstance(display_order, int):
            raise ValidationError("display_order must be int")
        self.display_order: int = display_order
        if not isinstance(added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if parent_id_id is not None and not isinstance(parent_id_id, productservices_categories):
            raise ValidationError("parent_id_id must be productservices_categories or None")
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.parent_id_id: Optional[productservices_categories] = parent_id_id


class productservices_products(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        name: str,
        image: Optional[Dict[str, Any]],
        description: str,
        specifications: Optional[Dict[str, Any]],
        html_description: str,
        highlights: Optional[Dict[str, Any]],
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
        seo_keywords: Optional[Dict[str, Any]],
        addition_details: Optional[Dict[str, Any]],
        added_by_user_id_id: userservices_users,
        category_id_id: productservices_categories,
        domain_user_id_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name: str = str(name)
        self.image: Optional[Dict[str, Any]] = _ensure_optional_dict(image, "image")
        self.description: str = str(description)
        self.specifications: Optional[Dict[str, Any]] = _ensure_optional_dict(specifications, "specifications")
        self.html_description: str = str(html_description)
        self.highlights: Optional[Dict[str, Any]] = _ensure_optional_dict(highlights, "highlights")
        self.sku: str = str(sku)
        self.initial_buying_price: float = float(initial_buying_price)
        self.initial_selling_price: float = float(initial_selling_price)
        self.weight: float = float(weight)
        self.dimensions: str = str(dimensions)
        self.uom: str = str(uom)
        self.color: str = str(color)
        self.tax_percentage: float = float(tax_percentage)
        self.brand: str = str(brand)
        self.brand_model: str = str(brand_model)
        self.status: str = str(status)
        self.seo_title: str = str(seo_title)
        self.seo_description: str = str(seo_description)
        self.seo_keywords: Optional[Dict[str, Any]] = _ensure_optional_dict(seo_keywords, "seo_keywords")
        self.addition_details: Optional[Dict[str, Any]] = _ensure_optional_dict(addition_details, "addition_details")
        if not isinstance(added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(category_id_id, productservices_categories):
            raise ValidationError("category_id_id must be productservices_categories")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.category_id_id: productservices_categories = category_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id


class productservices_productquestions(BaseEntityWithIntId):
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
        self.question: str = str(question)
        self.answer: str = str(answer)
        self.status: str = str(status)
        if not isinstance(answer_user_id_id, userservices_users):
            raise ValidationError("answer_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(question_user_id_id, userservices_users):
            raise ValidationError("question_user_id_id must be userservices_users")
        if not isinstance(product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")
        self.answer_user_id_id: userservices_users = answer_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.question_user_id_id: userservices_users = question_user_id_id
        self.product_id_id: productservices_products = product_id_id


class productservices_productreviews(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        review_images: Optional[Dict[str, Any]],
        rating: float,
        reviews: str,
        status: str,
        domain_user_id_id: userservices_users,
        review_user_id_id: userservices_users,
        product_id_id: productservices_products,
    ) -> None:
        super().__init__(id=id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.review_images: Optional[Dict[str, Any]] = _ensure_optional_dict(review_images, "review_images")
        self.rating: float = float(rating)
        self.reviews: str = str(reviews)
        self.status: str = str(status)
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(review_user_id_id, userservices_users):
            raise ValidationError("review_user_id_id must be userservices_users")
        if not isinstance(product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.review_user_id_id: userservices_users = review_user_id_id
        self.product_id_id: productservices_products = product_id_id


class inventoryservices_warehouse(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        warehouse_manager_id: userservices_users,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name: str = str(name)
        self.address: str = str(address)
        self.city: str = str(city)
        self.state: str = str(state)
        self.country: str = str(country)
        self.pincode: str = str(pincode)
        self.phone: str = str(phone)
        self.email: str = str(email)
        self.status: str = str(status)
        self.size: str = str(size)
        self.capacity: str = str(capacity)
        self.warehouse_type: str = str(warehouse_type)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        if not isinstance(added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(warehouse_manager_id, userservices_users):
            raise ValidationError("warehouse_manager_id must be userservices_users")
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.warehouse_manager_id: userservices_users = warehouse_manager_id


class inventoryservices_rackandshelvesandfloor(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: Optional[Dict[str, Any]],
        added_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        warehouse_id_id: inventoryservices_warehouse,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.name: str = str(name)
        self.rack: str = str(rack)
        self.shelf: str = str(shelf)
        self.floor: str = str(floor)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        if not isinstance(added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.warehouse_id_id: inventoryservices_warehouse = warehouse_id_id


class orderservice_purchaseorder(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
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
        self.po_code: str = str(po_code)
        if not isinstance(po_date, datetime):
            raise ValidationError("po_date must be datetime")
        if not isinstance(expected_delivery_date, datetime):
            raise ValidationError("expected_delivery_date must be datetime")
        self.po_date: datetime = po_date
        self.expected_delivery_date: datetime = expected_delivery_date
        self.payment_terms: str = str(payment_terms)
        self.payment_status: str = str(payment_status)
        self.total_amount: Decimal = _ensure_decimal(total_amount, "total_amount")
        self.paid_amount: Decimal = _ensure_decimal(paid_amount, "paid_amount")
        self.due_amount: Decimal = _ensure_decimal(due_amount, "due_amount")
        self.discount_amount: Decimal = _ensure_decimal(discount_amount, "discount_amount")
        self.discount_type: str = str(discount_type)
        self.shipping_amount: Decimal = _ensure_decimal(shipping_amount, "shipping_amount")
        self.shipping_type: str = str(shipping_type)
        self.shipping_tax_percentage: Decimal = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.shipping_tax_amount: Decimal = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if approved_at is not None and not isinstance(approved_at, datetime):
            raise ValidationError("approved_at must be datetime or None")
        if cancelled_at is not None and not isinstance(cancelled_at, datetime):
            raise ValidationError("cancelled_at must be datetime or None")
        if received_at is not None and not isinstance(received_at, datetime):
            raise ValidationError("received_at must be datetime or None")
        if returned_at is not None and not isinstance(returned_at, datetime):
            raise ValidationError("returned_at must be datetime or None")
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = str(cancelled_reason)
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at

        for field_name, obj in [
            ("approved_by_user_id_id", approved_by_user_id_id),
            ("cancelled_by_user_id_id", cancelled_by_user_id_id),
            ("created_by_user_id_id", created_by_user_id_id),
            ("domain_user_id_id", domain_user_id_id),
            ("last_updated_by_user_id_id", last_updated_by_user_id_id),
            ("received_by_user_id_id", received_by_user_id_id),
            ("returned_by_user_id_id", returned_by_user_id_id),
            ("supplier_id_id", supplier_id_id),
            ("updated_by_user_id_id", updated_by_user_id_id),
        ]:
            if not isinstance(obj, userservices_users):
                raise ValidationError(f"{field_name} must be userservices_users")
        if not isinstance(warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")

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


class orderservice_purchaseorderitems(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
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
        self.quantity_ordered: int = _ensure_non_negative_int(quantity_ordered, "quantity_ordered")
        self.quantity_received: int = _ensure_non_negative_int(quantity_received, "quantity_received")
        self.quantity_cancelled: int = _ensure_non_negative_int(quantity_cancelled, "quantity_cancelled")
        self.quantity_returned: int = _ensure_non_negative_int(quantity_returned, "quantity_returned")
        self.buying_price: Decimal = _ensure_decimal(buying_price, "buying_price")
        self.selling_price: Decimal = _ensure_decimal(selling_price, "selling_price")
        self.discount_amount: Decimal = _ensure_decimal(discount_amount, "discount_amount")
        self.amount_paid: Decimal = _ensure_decimal(amount_paid, "amount_paid")
        self.amount_returned: Decimal = _ensure_decimal(amount_returned, "amount_returned")
        self.amount_cancelled: Decimal = _ensure_decimal(amount_cancelled, "amount_cancelled")
        self.amount_ordered: Decimal = _ensure_decimal(amount_ordered, "amount_ordered")
        self.tax_percentage: Decimal = _ensure_decimal(tax_percentage, "tax_percentage")
        self.tax_amount: Decimal = _ensure_decimal(tax_amount, "tax_amount")
        self.shipping_tax_percentage: Decimal = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.shipping_amount: Decimal = _ensure_decimal(shipping_amount, "shipping_amount")
        self.shipping_tax_amount: Decimal = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.discount_type: str = str(discount_type)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if approved_at is not None and not isinstance(approved_at, datetime):
            raise ValidationError("approved_at must be datetime or None")
        if cancelled_at is not None and not isinstance(cancelled_at, datetime):
            raise ValidationError("cancelled_at must be datetime or None")
        if received_at is not None and not isinstance(received_at, datetime):
            raise ValidationError("received_at must be datetime or None")
        if returned_at is not None and not isinstance(returned_at, datetime):
            raise ValidationError("returned_at must be datetime or None")
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = str(cancelled_reason)
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at

        for field_name, obj in [
            ("approved_by_user_id_id", approved_by_user_id_id),
            ("cancelled_by_user_id_id", cancelled_by_user_id_id),
            ("created_by_user_id_id", created_by_user_id_id),
            ("domain_user_id_id", domain_user_id_id),
            ("last_updated_by_user_id_id", last_updated_by_user_id_id),
            ("received_by_user_id_id", received_by_user_id_id),
            ("returned_by_user_id_id", returned_by_user_id_id),
            ("updated_by_user_id_id", updated_by_user_id_id),
        ]:
            if not isinstance(obj, userservices_users):
                raise ValidationError(f"{field_name} must be userservices_users")
        if not isinstance(po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")
        if not isinstance(product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")

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


class orderservice_purchaseorderlogs(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[Dict[str, Any]],
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        po_id_id: orderservice_purchaseorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.comment: str = str(comment)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        if not isinstance(created_by_user_id_id, userservices_users):
            raise ValidationError("created_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.po_id_id: orderservice_purchaseorder = po_id_id


class orderservice_purchaseorderinwardedlog(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: datetime,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        domain_user_id_id: userservices_users,
        inwarded_by_user_id_id: userservices_users,
        po_id_id: orderservice_purchaseorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.invoice_path: str = str(invoice_path)
        self.invoice_number: str = str(invoice_number)
        self.notes: str = str(notes)
        if not isinstance(inwarded_at, datetime):
            raise ValidationError("inwarded_at must be datetime")
        self.inwarded_at: datetime = inwarded_at
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(inwarded_by_user_id_id, userservices_users):
            raise ValidationError("inwarded_by_user_id_id must be userservices_users")
        if not isinstance(po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.inwarded_by_user_id_id: userservices_users = inwarded_by_user_id_id
        self.po_id_id: orderservice_purchaseorder = po_id_id


class orderservice_purchaseorderiteminwardedlog(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
        status: str,
        domain_user_id_id: userservices_users,
        po_item_id_id: orderservice_purchaseorderitems,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.inwarded_quantity: int = _ensure_non_negative_int(inwarded_quantity, "inwarded_quantity")
        self.price: Decimal = _ensure_decimal(price, "price")
        self.tax_percentage: Decimal = _ensure_decimal(tax_percentage, "tax_percentage")
        self.discount_amount: Decimal = _ensure_decimal(discount_amount, "discount_amount")
        self.discount_type: str = str(discount_type)
        self.shipping_amount: Decimal = _ensure_decimal(shipping_amount, "shipping_amount")
        self.shipping_tax_percentage: Decimal = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(po_item_id_id, orderservice_purchaseorderitems):
            raise ValidationError("po_item_id_id must be orderservice_purchaseorderitems")
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.po_item_id_id: orderservice_purchaseorderitems = po_item_id_id


class orderservice_salesorder(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
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
        self.so_code: str = str(so_code)
        if not isinstance(so_date, datetime):
            raise ValidationError("so_date must be datetime")
        if not isinstance(expected_delivery_date, datetime):
            raise ValidationError("expected_delivery_date must be datetime")
        self.so_date: datetime = so_date
        self.expected_delivery_date: datetime = expected_delivery_date
        self.payment_terms: str = str(payment_terms)
        self.payment_status: str = str(payment_status)
        self.total_amount: Decimal = _ensure_decimal(total_amount, "total_amount")
        self.paid_amount: Decimal = _ensure_decimal(paid_amount, "paid_amount")
        self.due_amount: Decimal = _ensure_decimal(due_amount, "due_amount")
        self.discount_amount: Decimal = _ensure_decimal(discount_amount, "discount_amount")
        self.discount_type: str = str(discount_type)
        self.shipping_amount: Decimal = _ensure_decimal(shipping_amount, "shipping_amount")
        self.shipping_type: str = str(shipping_type)
        self.shipping_tax_percentage: Decimal = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.shipping_tax_amount: Decimal = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if approved_at is not None and not isinstance(approved_at, datetime):
            raise ValidationError("approved_at must be datetime or None")
        if cancelled_at is not None and not isinstance(cancelled_at, datetime):
            raise ValidationError("cancelled_at must be datetime or None")
        if received_at is not None and not isinstance(received_at, datetime):
            raise ValidationError("received_at must be datetime or None")
        if returned_at is not None and not isinstance(returned_at, datetime):
            raise ValidationError("returned_at must be datetime or None")
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = str(cancelled_reason)
        self.received_at: Optional[datetime] = received_at
        self.returned_at: Optional[datetime] = returned_at

        for field_name, obj in [
            ("approved_by_user_id_id", approved_by_user_id_id),
            ("cancelled_by_user_id_id", cancelled_by_user_id_id),
            ("created_by_user_id_id", created_by_user_id_id),
            ("customer_id_id", customer_id_id),
            ("domain_user_id_id", domain_user_id_id),
            ("last_updated_by_user_id_id", last_updated_by_user_id_id),
            ("received_by_user_id_id", received_by_user_id_id),
            ("returned_by_user_id_id", returned_by_user_id_id),
            ("updated_by_user_id_id", updated_by_user_id_id),
        ]:
            if not isinstance(obj, userservices_users):
                raise ValidationError(f"{field_name} must be userservices_users")
        if not isinstance(po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder")
        if not isinstance(product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")

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


class orderservice_salesorderorderitems(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
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
        self.quantity_ordered: int = _ensure_non_negative_int(quantity_ordered, "quantity_ordered")
        self.quantity_delivered: int = _ensure_non_negative_int(quantity_delivered, "quantity_delivered")
        self.quantity_shipped: int = _ensure_non_negative_int(quantity_shipped, "quantity_shipped")
        self.quantity_cancelled: int = _ensure_non_negative_int(quantity_cancelled, "quantity_cancelled")
        self.quantity_returned: int = _ensure_non_negative_int(quantity_returned, "quantity_returned")
        self.purchase_price: Decimal = _ensure_decimal(purchase_price, "purchase_price")
        self.discount_amount: Decimal = _ensure_decimal(discount_amount, "discount_amount")
        self.discount_type: str = str(discount_type)
        self.amount_paid: Decimal = _ensure_decimal(amount_paid, "amount_paid")
        self.amount_returned: Decimal = _ensure_decimal(amount_returned, "amount_returned")
        self.amount_cancelled: Decimal = _ensure_decimal(amount_cancelled, "amount_cancelled")
        self.amount_ordered: Decimal = _ensure_decimal(amount_ordered, "amount_ordered")
        self.tax_percentage: Decimal = _ensure_decimal(tax_percentage, "tax_percentage")
        self.tax_amount: Decimal = _ensure_decimal(tax_amount, "tax_amount")
        self.shipping_amount: Decimal = _ensure_decimal(shipping_amount, "shipping_amount")
        self.shipping_type: str = str(shipping_type)
        self.shipping_tax_amount: Decimal = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if approved_at is not None and not isinstance(approved_at, datetime):
            raise ValidationError("approved_at must be datetime or None")
        if cancelled_at is not None and not isinstance(cancelled_at, datetime):
            raise ValidationError("cancelled_at must be datetime or None")
        if shipped_at is not None and not isinstance(shipped_at, datetime):
            raise ValidationError("shipped_at must be datetime or None")
        if returned_at is not None and not isinstance(returned_at, datetime):
            raise ValidationError("returned_at must be datetime or None")
        self.approved_at: Optional[datetime] = approved_at
        self.cancelled_at: Optional[datetime] = cancelled_at
        self.cancelled_reason: str = str(cancelled_reason)
        self.shipped_at: Optional[datetime] = shipped_at
        self.returned_at: Optional[datetime] = returned_at

        for field_name, obj in [
            ("approved_by_user_id_id", approved_by_user_id_id),
            ("cancelled_by_user_id_id", cancelled_by_user_id_id),
            ("created_by_user_id_id", created_by_user_id_id),
            ("domain_user_id_id", domain_user_id_id),
            ("returned_by_user_id_id", returned_by_user_id_id),
            ("shipped_by_user_id_id", shipped_by_user_id_id),
            ("updated_by_user_id_id", updated_by_user_id_id),
        ]:
            if not isinstance(obj, userservices_users):
                raise ValidationError(f"{field_name} must be userservices_users")
        if not isinstance(product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")
        if not isinstance(so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder")

        self.approved_by_user_id_id: userservices_users = approved_by_user_id_id
        self.cancelled_by_user_id_id: userservices_users = cancelled_by_user_id_id
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.product_id_id: productservices_products = product_id_id
        self.returned_by_user_id_id: userservices_users = returned_by_user_id_id
        self.shipped_by_user_id_id: userservices_users = shipped_by_user_id_id
        self.so_id_id: orderservice_salesorder = so_id_id
        self.updated_by_user_id_id: userservices_users = updated_by_user_id_id


class orderservice_salesorderlogs(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[Dict[str, Any]],
        created_by_user_id_id: userservices_users,
        domain_user_id_id: userservices_users,
        so_id_id: orderservice_salesorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.comment: str = str(comment)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        if not isinstance(created_by_user_id_id, userservices_users):
            raise ValidationError("created_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder")
        self.created_by_user_id_id: userservices_users = created_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.so_id_id: orderservice_salesorder = so_id_id


class orderservice_salesorderoutwardedlog(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: datetime,
        additional_details: Optional[Dict[str, Any]],
        status: str,
        domain_user_id_id: userservices_users,
        outwarded_by_user_id_id: userservices_users,
        so_id_id: orderservice_salesorder,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.invoice_path: str = str(invoice_path)
        self.invoice_number: str = str(invoice_number)
        self.notes: str = str(notes)
        if not isinstance(outwared_at, datetime):
            raise ValidationError("outwared_at must be datetime")
        self.outwared_at: datetime = outwared_at
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(outwarded_by_user_id_id, userservices_users):
            raise ValidationError("outwarded_by_user_id_id must be userservices_users")
        if not isinstance(so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder")
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.outwarded_by_user_id_id: userservices_users = outwarded_by_user_id_id
        self.so_id_id: orderservice_salesorder = so_id_id


class orderservice_salesorderitemoutwardedlog(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
        status: str,
        domain_user_id_id: userservices_users,
        so_item_id_id: orderservice_salesorderorderitems,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.outwarded_quantity: int = _ensure_non_negative_int(outwarded_quantity, "outwarded_quantity")
        self.price: Decimal = _ensure_decimal(price, "price")
        self.tax_percentage: Decimal = _ensure_decimal(tax_percentage, "tax_percentage")
        self.discount_amount: Decimal = _ensure_decimal(discount_amount, "discount_amount")
        self.discount_type: str = str(discount_type)
        self.shipping_amount: Decimal = _ensure_decimal(shipping_amount, "shipping_amount")
        self.shipping_tax_percentage: Decimal = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        self.status: str = str(status)
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(so_item_id_id, orderservice_salesorderorderitems):
            raise ValidationError("so_item_id_id must be orderservice_salesorderorderitems")
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.so_item_id_id: orderservice_salesorderorderitems = so_item_id_id


class inventoryservices_inventory(BaseEntityWithIntId):
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
        additional_details: Optional[Dict[str, Any]],
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
        self.quantity: int = _ensure_non_negative_int(quantity, "quantity")
        self.mrp: str = str(mrp)
        self.batch_number: str = str(batch_number)
        self.discount_type: str = str(discount_type)
        self.discount_amout: float = float(discount_amout)
        self.sr_no: str = str(sr_no)
        if not isinstance(mfg_date, datetime):
            raise ValidationError("mfg_date must be datetime")
        self.mfg_date: datetime = mfg_date
        self.uom: str = str(uom)
        self.ptr: str = str(ptr)
        if not isinstance(received_date, datetime):
            raise ValidationError("received_date must be datetime")
        if not isinstance(expiry_date, datetime):
            raise ValidationError("expiry_date must be datetime")
        self.received_date: datetime = received_date
        self.expiry_date: datetime = expiry_date
        self.quantity_inwarded: int = _ensure_non_negative_int(quantity_inwarded, "quantity_inwarded")
        self.buy_price: Decimal = _ensure_decimal(buy_price, "buy_price")
        self.sell_price: Decimal = _ensure_decimal(sell_price, "sell_price")
        self.tax_percentage: Decimal = _ensure_decimal(tax_percentage, "tax_percentage")
        self.stock_status: str = str(stock_status)
        self.inward_type: str = str(inward_type)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")

        if not isinstance(added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(product_id_id, productservices_products):
            raise ValidationError("product_id_id must be productservices_products")
        if not isinstance(purchase_order_id_id, orderservice_purchaseorder):
            raise ValidationError("purchase_order_id_id must be orderservice_purchaseorder")
        if not isinstance(purchase_order_item_id_id, orderservice_purchaseorderitems):
            raise ValidationError("purchase_order_item_id_id must be orderservice_purchaseorderitems")
        if purchase_order_item_inwarded_item_id_id is not None and not isinstance(
            purchase_order_item_inwarded_item_id_id, orderservice_purchaseorderiteminwardedlog
        ):
            raise ValidationError("purchase_order_item_inwarded_item_id_id must be orderservice_purchaseorderiteminwardedlog or None")
        if not isinstance(rack_shelf_floor_id_id, inventoryservices_rackandshelvesandfloor):
            raise ValidationError("rack_shelf_floor_id_id must be inventoryservices_rackandshelvesandfloor")
        if not isinstance(warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")

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


class inventoryservices_inventorylog(BaseEntityWithIntId):
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Optional[Dict[str, Any]],
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
        self.quantity: int = _ensure_non_negative_int(quantity, "quantity")
        self.status: str = str(status)
        self.additional_details: Optional[Dict[str, Any]] = _ensure_optional_dict(additional_details, "additional_details")
        if not isinstance(added_by_user_id_id, userservices_users):
            raise ValidationError("added_by_user_id_id must be userservices_users")
        if not isinstance(domain_user_id_id, userservices_users):
            raise ValidationError("domain_user_id_id must be userservices_users")
        if not isinstance(inventory_id_id, inventoryservices_inventory):
            raise ValidationError("inventory_id_id must be inventoryservices_inventory")
        if po_id_id is not None and not isinstance(po_id_id, orderservice_purchaseorder):
            raise ValidationError("po_id_id must be orderservice_purchaseorder or None")
        if so_id_id is not None and not isinstance(so_id_id, orderservice_salesorder):
            raise ValidationError("so_id_id must be orderservice_salesorder or None")
        if not isinstance(rack_shelf_floor_id_id, inventoryservices_rackandshelvesandfloor):
            raise ValidationError("rack_shelf_floor_id_id must be inventoryservices_rackandshelvesandfloor")
        if not isinstance(warehouse_id_id, inventoryservices_warehouse):
            raise ValidationError("warehouse_id_id must be inventoryservices_warehouse")
        self.added_by_user_id_id: userservices_users = added_by_user_id_id
        self.domain_user_id_id: userservices_users = domain_user_id_id
        self.inventory_id_id: inventoryservices_inventory = inventory_id_id
        self.po_id_id: Optional[orderservice_purchaseorder] = po_id_id
        self.so_id_id: Optional[orderservice_salesorder] = so_id_id
        self.rack_shelf_floor_id_id: inventoryservices_rackandshelvesandfloor = rack_shelf_floor_id_id
        self.warehouse_id_id: inventoryservices_warehouse = warehouse_id_id