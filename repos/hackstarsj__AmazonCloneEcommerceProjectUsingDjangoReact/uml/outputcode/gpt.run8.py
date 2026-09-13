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
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("id must be a positive int")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = id


class BigIdEntity(BaseEntity):
    def __init__(self, id: int, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(id, int) or id <= 0:
            raise ValidationError("id must be a positive int")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.id: int = id


class StringPkEntity(BaseEntity):
    def __init__(self, session_key: str, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        if not isinstance(session_key, str) or not session_key:
            raise ValidationError("session_key must be a non-empty str")
        super().__init__(created_at=created_at, updated_at=updated_at)
        self.session_key: str = session_key


def _ensure_decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        try:
            return Decimal(str(value))
        except Exception as e:
            raise ValidationError(f"{field} must be a decimal-compatible value") from e
    raise ValidationError(f"{field} must be a decimal-compatible value")


def _ensure_non_negative_int(value: Any, field: str) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{field} must be int")
    if value < 0:
        raise ValidationError(f"{field} must be non-negative")
    return value


def _ensure_optional_non_negative_int(value: Any, field: str) -> Optional[int]:
    if value is None:
        return None
    return _ensure_non_negative_int(value, field)


def _ensure_optional_decimal(value: Any, field: str) -> Optional[Decimal]:
    if value is None:
        return None
    d = _ensure_decimal(value, field)
    if d < 0:
        raise ValidationError(f"{field} must be non-negative")
    return d


def _ensure_non_negative_decimal(value: Any, field: str) -> Decimal:
    d = _ensure_decimal(value, field)
    if d < 0:
        raise ValidationError(f"{field} must be non-negative")
    return d


def _ensure_optional_datetime(value: Any, field: str) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValidationError(f"{field} must be datetime")
    return value


def _ensure_optional_date(value: Any, field: str) -> Optional[date]:
    if value is None:
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValidationError(f"{field} must be date")
    return value


def _ensure_optional_str(value: Any, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be str")
    return value


def _ensure_optional_json(value: Any, field: str) -> Optional[JsonDict]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be a dict (json)")
    return value


def _ensure_optional_list(value: Any, field: str) -> Optional[List[Any]]:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list (json array)")
    return value


class userservices_users(BigIdEntity):
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id: Optional[userservices_users] = None,
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
        for field_name, v in [
            ("first_name", first_name),
            ("last_name", last_name),
            ("name", name),
            ("email", email),
            ("phone", phone),
            ("address", address),
            ("city", city),
            ("state", state),
            ("pincode", pincode),
            ("country", country),
            ("profile_pic", profile_pic),
            ("account_status", account_status),
            ("role", role),
            ("username", username),
            ("password", password),
            ("language", language),
            ("departMent", departMent),
            ("designation", designation),
            ("time_zone", time_zone),
            ("last_device", last_device),
            ("last_ip", last_ip),
            ("currency", currency),
            ("domain_name", domain_name),
            ("plan_type", plan_type),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
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
        self.dob: Optional[date] = _ensure_optional_date(dob, "dob")
        self.username: str = username
        self.password: str = password
        self.social_media_links: Optional[JsonDict] = _ensure_optional_json(social_media_links, "social_media_links")
        self.addition_details: Optional[JsonDict] = _ensure_optional_json(addition_details, "addition_details")
        self.language: str = language
        self.departMent: str = departMent
        self.designation: str = designation
        self.time_zone: str = time_zone
        self.last_login: Optional[datetime] = _ensure_optional_datetime(last_login, "last_login")
        self.last_device: str = last_device
        self.last_ip: str = last_ip
        self.currency: str = currency
        self.domain_name: str = domain_name
        self.plan_type: str = plan_type
        if domain_user_id is not None and not isinstance(domain_user_id, userservices_users):
            raise ValidationError("domain_user_id must be userservices_users or None")
        self.domain_user_id: Optional[userservices_users] = domain_user_id


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("address_type", address_type),
            ("address", address),
            ("city", city),
            ("state", state),
            ("pincode", pincode),
            ("country", country),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        self.address_type: str = address_type
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.pincode: str = pincode
        self.country: str = country
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.user: Optional[userservices_users] = user


class userservices_activitylog(IdEntity):
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
        domain_user: Optional[userservices_users] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("activity", activity),
            ("activity_type", activity_type),
            ("activity_ip", activity_ip),
            ("activity_device", activity_device),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(activity_date, datetime):
            raise ValidationError("activity_date must be datetime")
        self.activity: str = activity
        self.activity_type: str = activity_type
        self.activity_date: datetime = activity_date
        self.activity_ip: str = activity_ip
        self.activity_device: str = activity_device
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.domain_user: Optional[userservices_users] = domain_user
        self.user: Optional[userservices_users] = user


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        parent: Optional[userservices_modules] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("module_name", module_name),
            ("module_icon", module_icon),
            ("module_url", module_url),
            ("module_description", module_description),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(is_menu, bool):
            raise ValidationError("is_menu must be bool")
        if not isinstance(is_active, bool):
            raise ValidationError("is_active must be bool")
        if not isinstance(display_order, int):
            raise ValidationError("display_order must be int")
        self.module_name: str = module_name
        self.module_icon: str = module_icon
        self.is_menu: bool = is_menu
        self.is_active: bool = is_active
        self.module_url: str = module_url
        self.display_order: int = display_order
        self.module_description: str = module_description
        if parent is not None and not isinstance(parent, userservices_modules):
            raise ValidationError("parent must be userservices_modules or None")
        self.parent: Optional[userservices_modules] = parent


class userservices_userpermissions(IdEntity):
    def __init__(
        self,
        id: int,
        is_view: bool,
        is_add: bool,
        is_edit: bool,
        is_delete: bool,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        module: Optional[userservices_modules] = None,
        domain_user: Optional[userservices_users] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("is_view", is_view),
            ("is_add", is_add),
            ("is_edit", is_edit),
            ("is_delete", is_delete),
        ]:
            if not isinstance(v, bool):
                raise ValidationError(f"{field_name} must be bool")
        self.is_view: bool = is_view
        self.is_add: bool = is_add
        self.is_edit: bool = is_edit
        self.is_delete: bool = is_delete
        if module is not None and not isinstance(module, userservices_modules):
            raise ValidationError("module must be userservices_modules or None")
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.module: Optional[userservices_modules] = module
        self.domain_user: Optional[userservices_users] = domain_user
        self.user: Optional[userservices_users] = user


class auth_group(IdEntity):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id=id)
        if not isinstance(name, str):
            raise ValidationError("name must be str")
        self.name: str = name


class django_content_type(IdEntity):
    def __init__(self, id: int, app_label: str, model: str) -> None:
        super().__init__(id=id)
        if not isinstance(app_label, str):
            raise ValidationError("app_label must be str")
        if not isinstance(model, str):
            raise ValidationError("model must be str")
        self.app_label: str = app_label
        self.model: str = model


class auth_permission(IdEntity):
    def __init__(self, id: int, name: str, codename: str, content_type: Optional[django_content_type] = None) -> None:
        super().__init__(id=id)
        if not isinstance(name, str):
            raise ValidationError("name must be str")
        if not isinstance(codename, str):
            raise ValidationError("codename must be str")
        if content_type is not None and not isinstance(content_type, django_content_type):
            raise ValidationError("content_type must be django_content_type or None")
        self.name: str = name
        self.codename: str = codename
        self.content_type: Optional[django_content_type] = content_type


class auth_group_permissions(BigIdEntity):
    def __init__(self, id: int, group: Optional[auth_group] = None, permission: Optional[auth_permission] = None) -> None:
        super().__init__(id=id)
        if group is not None and not isinstance(group, auth_group):
            raise ValidationError("group must be auth_group or None")
        if permission is not None and not isinstance(permission, auth_permission):
            raise ValidationError("permission must be auth_permission or None")
        self.group: Optional[auth_group] = group
        self.permission: Optional[auth_permission] = permission


class userservices_users_groups(BigIdEntity):
    def __init__(self, id: int, users: Optional[userservices_users] = None, group: Optional[auth_group] = None) -> None:
        super().__init__(id=id)
        if users is not None and not isinstance(users, userservices_users):
            raise ValidationError("users must be userservices_users or None")
        if group is not None and not isinstance(group, auth_group):
            raise ValidationError("group must be auth_group or None")
        self.users: Optional[userservices_users] = users
        self.group: Optional[auth_group] = group


class userservices_users_user_permissions(BigIdEntity):
    def __init__(self, id: int, users: Optional[userservices_users] = None, permission: Optional[auth_permission] = None) -> None:
        super().__init__(id=id)
        if users is not None and not isinstance(users, userservices_users):
            raise ValidationError("users must be userservices_users or None")
        if permission is not None and not isinstance(permission, auth_permission):
            raise ValidationError("permission must be auth_permission or None")
        self.users: Optional[userservices_users] = users
        self.permission: Optional[auth_permission] = permission


class django_admin_log(IdEntity):
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str,
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type: Optional[django_content_type] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id)
        if not isinstance(action_time, datetime):
            raise ValidationError("action_time must be datetime")
        for field_name, v in [
            ("object_id", object_id),
            ("object_repr", object_repr),
            ("change_message", change_message),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(action_flag, int):
            raise ValidationError("action_flag must be int")
        if content_type is not None and not isinstance(content_type, django_content_type):
            raise ValidationError("content_type must be django_content_type or None")
        if user is not None and not isinstance(user, userservices_users):
            raise ValidationError("user must be userservices_users or None")
        self.action_time: datetime = action_time
        self.object_id: str = object_id
        self.object_repr: str = object_repr
        self.action_flag: int = action_flag
        self.change_message: str = change_message
        self.content_type: Optional[django_content_type] = content_type
        self.user: Optional[userservices_users] = user


class django_migrations(BigIdEntity):
    def __init__(self, id: int, app: str, name: str, applied: datetime) -> None:
        super().__init__(id=id)
        if not isinstance(app, str):
            raise ValidationError("app must be str")
        if not isinstance(name, str):
            raise ValidationError("name must be str")
        if not isinstance(applied, datetime):
            raise ValidationError("applied must be datetime")
        self.app: str = app
        self.name: str = name
        self.applied: datetime = applied


class django_session(StringPkEntity):
    def __init__(self, session_key: str, session_data: str, expire_date: datetime) -> None:
        super().__init__(session_key=session_key)
        if not isinstance(session_data, str):
            raise ValidationError("session_data must be str")
        if not isinstance(expire_date, datetime):
            raise ValidationError("expire_date must be datetime")
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        parent: Optional[productservices_categories] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str):
            raise ValidationError("name must be str")
        if not isinstance(image, str):
            raise ValidationError("image must be str")
        if not isinstance(description, str):
            raise ValidationError("description must be str")
        if not isinstance(display_order, int):
            raise ValidationError("display_order must be int")
        if added_by_user is not None and not isinstance(added_by_user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        if parent is not None and not isinstance(parent, productservices_categories):
            raise ValidationError("parent must be productservices_categories or None")
        self.name: str = name
        self.image: str = image
        self.description: str = description
        self.display_order: int = display_order
        self.added_by_user: Optional[userservices_users] = added_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.parent: Optional[productservices_categories] = parent


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional[userservices_users] = None,
        category: Optional[productservices_categories] = None,
        domain_user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("name", name),
            ("description", description),
            ("html_description", html_description),
            ("sku", sku),
            ("dimensions", dimensions),
            ("uom", uom),
            ("color", color),
            ("brand", brand),
            ("brand_model", brand_model),
            ("status", status),
            ("seo_title", seo_title),
            ("seo_description", seo_description),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        for field_name, v in [
            ("initial_buying_price", initial_buying_price),
            ("initial_selling_price", initial_selling_price),
            ("weight", weight),
            ("tax_percentage", tax_percentage),
        ]:
            if not isinstance(v, (int, float)):
                raise ValidationError(f"{field_name} must be number")
        self.name: str = name
        self.image: Optional[JsonDict] = _ensure_optional_json(image, "image")
        self.description: str = description
        self.specifications: Optional[JsonDict] = _ensure_optional_json(specifications, "specifications")
        self.html_description: str = html_description
        self.highlights: Optional[JsonDict] = _ensure_optional_json(highlights, "highlights")
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
        self.seo_keywords: Optional[JsonDict] = _ensure_optional_json(seo_keywords, "seo_keywords")
        self.addition_details: Optional[JsonDict] = _ensure_optional_json(addition_details, "addition_details")
        if added_by_user is not None and not isinstance(added_by_user, userservices_users):
            raise ValidationError("added_by_user must be userservices_users or None")
        if category is not None and not isinstance(category, productservices_categories):
            raise ValidationError("category must be productservices_categories or None")
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        self.added_by_user: Optional[userservices_users] = added_by_user
        self.category: Optional[productservices_categories] = category
        self.domain_user: Optional[userservices_users] = domain_user


class productservices_productquestions(IdEntity):
    def __init__(
        self,
        id: int,
        question: str,
        answer: str,
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        answer_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        question_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [("question", question), ("answer", answer), ("status", status)]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        self.question: str = question
        self.answer: str = answer
        self.status: str = status
        for field_name, obj, cls in [
            ("answer_user", answer_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("question_user", question_user, userservices_users),
            ("product", product, productservices_products),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.answer_user: Optional[userservices_users] = answer_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.question_user: Optional[userservices_users] = question_user
        self.product: Optional[productservices_products] = product


class productservices_productreviews(IdEntity):
    def __init__(
        self,
        id: int,
        review_images: Optional[JsonDict],
        rating: float,
        reviews: str,
        status: str,
        domain_user: Optional[userservices_users] = None,
        review_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
    ) -> None:
        super().__init__(id=id)
        if not isinstance(rating, (int, float)):
            raise ValidationError("rating must be number")
        if not isinstance(reviews, str):
            raise ValidationError("reviews must be str")
        if not isinstance(status, str):
            raise ValidationError("status must be str")
        self.review_images: Optional[JsonDict] = _ensure_optional_json(review_images, "review_images")
        self.rating: float = float(rating)
        self.reviews: str = reviews
        self.status: str = status
        for field_name, obj, cls in [
            ("domain_user", domain_user, userservices_users),
            ("review_user", review_user, userservices_users),
            ("product", product, productservices_products),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.domain_user: Optional[userservices_users] = domain_user
        self.review_user: Optional[userservices_users] = review_user
        self.product: Optional[productservices_products] = product


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        warehouse_manager: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("name", name),
            ("address", address),
            ("city", city),
            ("state", state),
            ("country", country),
            ("pincode", pincode),
            ("phone", phone),
            ("email", email),
            ("status", status),
            ("size", size),
            ("capacity", capacity),
            ("warehouse_type", warehouse_type),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
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
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        for field_name, obj in [
            ("added_by_user", added_by_user),
            ("domain_user", domain_user),
            ("warehouse_manager", warehouse_manager),
        ]:
            if obj is not None and not isinstance(obj, userservices_users):
                raise ValidationError(f"{field_name} must be userservices_users or None")
        self.added_by_user: Optional[userservices_users] = added_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.warehouse_manager: Optional[userservices_users] = warehouse_manager


class inventoryservices_rackandshelvesandfloor(IdEntity):
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: Optional[JsonDict],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [("name", name), ("rack", rack), ("shelf", shelf), ("floor", floor)]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        self.name: str = name
        self.rack: str = rack
        self.shelf: str = shelf
        self.floor: str = floor
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        for field_name, obj, cls in [
            ("added_by_user", added_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("warehouse", warehouse, inventoryservices_warehouse),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.added_by_user: Optional[userservices_users] = added_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


class orderservice_purchaseorder(IdEntity):
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional[userservices_users] = None,
        cancelled_by_user: Optional[userservices_users] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        last_updated_by_user: Optional[userservices_users] = None,
        received_by_user: Optional[userservices_users] = None,
        returned_by_user: Optional[userservices_users] = None,
        supplier: Optional[userservices_users] = None,
        updated_by_user: Optional[userservices_users] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("po_code", po_code),
            ("payment_terms", payment_terms),
            ("payment_status", payment_status),
            ("discount_type", discount_type),
            ("shipping_type", shipping_type),
            ("status", status),
            ("cancelled_reason", cancelled_reason),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(po_date, datetime):
            raise ValidationError("po_date must be datetime")
        if not isinstance(expected_delivery_date, datetime):
            raise ValidationError("expected_delivery_date must be datetime")
        self.po_code: str = po_code
        self.po_date: datetime = po_date
        self.expected_delivery_date: datetime = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = _ensure_non_negative_decimal(total_amount, "total_amount")
        self.paid_amount: Decimal = _ensure_non_negative_decimal(paid_amount, "paid_amount")
        self.due_amount: Decimal = _ensure_non_negative_decimal(due_amount, "due_amount")
        self.discount_amount: Decimal = _ensure_non_negative_decimal(discount_amount, "discount_amount")
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal(shipping_amount, "shipping_amount")
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        self.status: str = status
        self.approved_at: Optional[datetime] = _ensure_optional_datetime(approved_at, "approved_at")
        self.cancelled_at: Optional[datetime] = _ensure_optional_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = _ensure_optional_datetime(received_at, "received_at")
        self.returned_at: Optional[datetime] = _ensure_optional_datetime(returned_at, "returned_at")
        for field_name, obj, cls in [
            ("approved_by_user", approved_by_user, userservices_users),
            ("cancelled_by_user", cancelled_by_user, userservices_users),
            ("created_by_user", created_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("last_updated_by_user", last_updated_by_user, userservices_users),
            ("received_by_user", received_by_user, userservices_users),
            ("returned_by_user", returned_by_user, userservices_users),
            ("supplier", supplier, userservices_users),
            ("updated_by_user", updated_by_user, userservices_users),
            ("warehouse", warehouse, inventoryservices_warehouse),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.approved_by_user: Optional[userservices_users] = approved_by_user
        self.cancelled_by_user: Optional[userservices_users] = cancelled_by_user
        self.created_by_user: Optional[userservices_users] = created_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.last_updated_by_user: Optional[userservices_users] = last_updated_by_user
        self.received_by_user: Optional[userservices_users] = received_by_user
        self.returned_by_user: Optional[userservices_users] = returned_by_user
        self.supplier: Optional[userservices_users] = supplier
        self.updated_by_user: Optional[userservices_users] = updated_by_user
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional[userservices_users] = None,
        cancelled_by_user: Optional[userservices_users] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        last_updated_by_user: Optional[userservices_users] = None,
        received_by_user: Optional[userservices_users] = None,
        returned_by_user: Optional[userservices_users] = None,
        po: Optional[orderservice_purchaseorder] = None,
        product: Optional[productservices_products] = None,
        updated_by_user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity_ordered: int = _ensure_non_negative_int(quantity_ordered, "quantity_ordered")
        self.quantity_received: int = _ensure_non_negative_int(quantity_received, "quantity_received")
        self.quantity_cancelled: int = _ensure_non_negative_int(quantity_cancelled, "quantity_cancelled")
        self.quantity_returned: int = _ensure_non_negative_int(quantity_returned, "quantity_returned")
        self.buying_price: Decimal = _ensure_non_negative_decimal(buying_price, "buying_price")
        self.selling_price: Decimal = _ensure_non_negative_decimal(selling_price, "selling_price")
        self.discount_amount: Decimal = _ensure_non_negative_decimal(discount_amount, "discount_amount")
        self.amount_paid: Decimal = _ensure_non_negative_decimal(amount_paid, "amount_paid")
        self.amount_returned: Decimal = _ensure_non_negative_decimal(amount_returned, "amount_returned")
        self.amount_cancelled: Decimal = _ensure_non_negative_decimal(amount_cancelled, "amount_cancelled")
        self.amount_ordered: Decimal = _ensure_non_negative_decimal(amount_ordered, "amount_ordered")
        self.tax_percentage: Decimal = _ensure_non_negative_decimal(tax_percentage, "tax_percentage")
        self.tax_amount: Decimal = _ensure_non_negative_decimal(tax_amount, "tax_amount")
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.shipping_amount: Decimal = _ensure_non_negative_decimal(shipping_amount, "shipping_amount")
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        if not isinstance(discount_type, str):
            raise ValidationError("discount_type must be str")
        if not isinstance(status, str):
            raise ValidationError("status must be str")
        if not isinstance(cancelled_reason, str):
            raise ValidationError("cancelled_reason must be str")
        self.discount_type: str = discount_type
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        self.status: str = status
        self.approved_at: Optional[datetime] = _ensure_optional_datetime(approved_at, "approved_at")
        self.cancelled_at: Optional[datetime] = _ensure_optional_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = _ensure_optional_datetime(received_at, "received_at")
        self.returned_at: Optional[datetime] = _ensure_optional_datetime(returned_at, "returned_at")
        for field_name, obj, cls in [
            ("approved_by_user", approved_by_user, userservices_users),
            ("cancelled_by_user", cancelled_by_user, userservices_users),
            ("created_by_user", created_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("last_updated_by_user", last_updated_by_user, userservices_users),
            ("received_by_user", received_by_user, userservices_users),
            ("returned_by_user", returned_by_user, userservices_users),
            ("po", po, orderservice_purchaseorder),
            ("product", product, productservices_products),
            ("updated_by_user", updated_by_user, userservices_users),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.approved_by_user: Optional[userservices_users] = approved_by_user
        self.cancelled_by_user: Optional[userservices_users] = cancelled_by_user
        self.created_by_user: Optional[userservices_users] = created_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.last_updated_by_user: Optional[userservices_users] = last_updated_by_user
        self.received_by_user: Optional[userservices_users] = received_by_user
        self.returned_by_user: Optional[userservices_users] = returned_by_user
        self.po: Optional[orderservice_purchaseorder] = po
        self.product: Optional[productservices_products] = product
        self.updated_by_user: Optional[userservices_users] = updated_by_user


class orderservice_purchaseorderlogs(IdEntity):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonDict],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        po: Optional[orderservice_purchaseorder] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(comment, str):
            raise ValidationError("comment must be str")
        self.comment: str = comment
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        for field_name, obj, cls in [
            ("created_by_user", created_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("po", po, orderservice_purchaseorder),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.created_by_user: Optional[userservices_users] = created_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.po: Optional[orderservice_purchaseorder] = po


class orderservice_purchaseorderinwardedlog(IdEntity):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: datetime,
        additional_details: Optional[JsonDict],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional[userservices_users] = None,
        inwarded_by_user: Optional[userservices_users] = None,
        po: Optional[orderservice_purchaseorder] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [("invoice_path", invoice_path), ("invoice_number", invoice_number), ("notes", notes), ("status", status)]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(inwarded_at, datetime):
            raise ValidationError("inwarded_at must be datetime")
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.inwarded_at: datetime = inwarded_at
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        self.status: str = status
        for field_name, obj, cls in [
            ("domain_user", domain_user, userservices_users),
            ("inwarded_by_user", inwarded_by_user, userservices_users),
            ("po", po, orderservice_purchaseorder),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.domain_user: Optional[userservices_users] = domain_user
        self.inwarded_by_user: Optional[userservices_users] = inwarded_by_user
        self.po: Optional[orderservice_purchaseorder] = po


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional[userservices_users] = None,
        po_item: Optional[orderservice_purchaseorderitems] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.inwarded_quantity: int = _ensure_non_negative_int(inwarded_quantity, "inwarded_quantity")
        self.price: Decimal = _ensure_non_negative_decimal(price, "price")
        self.tax_percentage: Decimal = _ensure_non_negative_decimal(tax_percentage, "tax_percentage")
        self.discount_amount: Decimal = _ensure_non_negative_decimal(discount_amount, "discount_amount")
        if not isinstance(discount_type, str):
            raise ValidationError("discount_type must be str")
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal(shipping_amount, "shipping_amount")
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        if not isinstance(status, str):
            raise ValidationError("status must be str")
        self.status: str = status
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        if po_item is not None and not isinstance(po_item, orderservice_purchaseorderitems):
            raise ValidationError("po_item must be orderservice_purchaseorderitems or None")
        self.domain_user: Optional[userservices_users] = domain_user
        self.po_item: Optional[orderservice_purchaseorderitems] = po_item


class orderservice_salesorder(IdEntity):
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional[userservices_users] = None,
        cancelled_by_user: Optional[userservices_users] = None,
        created_by_user: Optional[userservices_users] = None,
        customer: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        last_updated_by_user: Optional[userservices_users] = None,
        received_by_user: Optional[userservices_users] = None,
        returned_by_user: Optional[userservices_users] = None,
        po: Optional[orderservice_purchaseorder] = None,
        product: Optional[productservices_products] = None,
        updated_by_user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [
            ("so_code", so_code),
            ("payment_terms", payment_terms),
            ("payment_status", payment_status),
            ("discount_type", discount_type),
            ("shipping_type", shipping_type),
            ("status", status),
            ("cancelled_reason", cancelled_reason),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(so_date, datetime):
            raise ValidationError("so_date must be datetime")
        if not isinstance(expected_delivery_date, datetime):
            raise ValidationError("expected_delivery_date must be datetime")
        self.so_code: str = so_code
        self.so_date: datetime = so_date
        self.expected_delivery_date: datetime = expected_delivery_date
        self.payment_terms: str = payment_terms
        self.payment_status: str = payment_status
        self.total_amount: Decimal = _ensure_non_negative_decimal(total_amount, "total_amount")
        self.paid_amount: Decimal = _ensure_non_negative_decimal(paid_amount, "paid_amount")
        self.due_amount: Decimal = _ensure_non_negative_decimal(due_amount, "due_amount")
        self.discount_amount: Decimal = _ensure_non_negative_decimal(discount_amount, "discount_amount")
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal(shipping_amount, "shipping_amount")
        self.shipping_type: str = shipping_type
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        self.status: str = status
        self.approved_at: Optional[datetime] = _ensure_optional_datetime(approved_at, "approved_at")
        self.cancelled_at: Optional[datetime] = _ensure_optional_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason: str = cancelled_reason
        self.received_at: Optional[datetime] = _ensure_optional_datetime(received_at, "received_at")
        self.returned_at: Optional[datetime] = _ensure_optional_datetime(returned_at, "returned_at")
        for field_name, obj, cls in [
            ("approved_by_user", approved_by_user, userservices_users),
            ("cancelled_by_user", cancelled_by_user, userservices_users),
            ("created_by_user", created_by_user, userservices_users),
            ("customer", customer, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("last_updated_by_user", last_updated_by_user, userservices_users),
            ("received_by_user", received_by_user, userservices_users),
            ("returned_by_user", returned_by_user, userservices_users),
            ("po", po, orderservice_purchaseorder),
            ("product", product, productservices_products),
            ("updated_by_user", updated_by_user, userservices_users),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.approved_by_user: Optional[userservices_users] = approved_by_user
        self.cancelled_by_user: Optional[userservices_users] = cancelled_by_user
        self.created_by_user: Optional[userservices_users] = created_by_user
        self.customer: Optional[userservices_users] = customer
        self.domain_user: Optional[userservices_users] = domain_user
        self.last_updated_by_user: Optional[userservices_users] = last_updated_by_user
        self.received_by_user: Optional[userservices_users] = received_by_user
        self.returned_by_user: Optional[userservices_users] = returned_by_user
        self.po: Optional[orderservice_purchaseorder] = po
        self.product: Optional[productservices_products] = product
        self.updated_by_user: Optional[userservices_users] = updated_by_user


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        shipped_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional[userservices_users] = None,
        cancelled_by_user: Optional[userservices_users] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
        returned_by_user: Optional[userservices_users] = None,
        shipped_by_user: Optional[userservices_users] = None,
        so: Optional[orderservice_salesorder] = None,
        updated_by_user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity_ordered: int = _ensure_non_negative_int(quantity_ordered, "quantity_ordered")
        self.quantity_delivered: int = _ensure_non_negative_int(quantity_delivered, "quantity_delivered")
        self.quantity_shipped: int = _ensure_non_negative_int(quantity_shipped, "quantity_shipped")
        self.quantity_cancelled: int = _ensure_non_negative_int(quantity_cancelled, "quantity_cancelled")
        self.quantity_returned: int = _ensure_non_negative_int(quantity_returned, "quantity_returned")
        self.purchase_price: Decimal = _ensure_non_negative_decimal(purchase_price, "purchase_price")
        self.discount_amount: Decimal = _ensure_non_negative_decimal(discount_amount, "discount_amount")
        if not isinstance(discount_type, str):
            raise ValidationError("discount_type must be str")
        self.discount_type: str = discount_type
        self.amount_paid: Decimal = _ensure_non_negative_decimal(amount_paid, "amount_paid")
        self.amount_returned: Decimal = _ensure_non_negative_decimal(amount_returned, "amount_returned")
        self.amount_cancelled: Decimal = _ensure_non_negative_decimal(amount_cancelled, "amount_cancelled")
        self.amount_ordered: Decimal = _ensure_non_negative_decimal(amount_ordered, "amount_ordered")
        self.tax_percentage: Decimal = _ensure_non_negative_decimal(tax_percentage, "tax_percentage")
        self.tax_amount: Decimal = _ensure_non_negative_decimal(tax_amount, "tax_amount")
        self.shipping_amount: Decimal = _ensure_non_negative_decimal(shipping_amount, "shipping_amount")
        if not isinstance(shipping_type, str):
            raise ValidationError("shipping_type must be str")
        self.shipping_type: str = shipping_type
        self.shipping_tax_amount: Decimal = _ensure_non_negative_decimal(shipping_tax_amount, "shipping_tax_amount")
        self.shipping_cancelled_amount: Decimal = _ensure_non_negative_decimal(shipping_cancelled_amount, "shipping_cancelled_amount")
        self.shipping_cancelled_tax_amount: Decimal = _ensure_non_negative_decimal(
            shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount"
        )
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        if not isinstance(status, str):
            raise ValidationError("status must be str")
        self.status: str = status
        self.approved_at: Optional[datetime] = _ensure_optional_datetime(approved_at, "approved_at")
        self.cancelled_at: Optional[datetime] = _ensure_optional_datetime(cancelled_at, "cancelled_at")
        if not isinstance(cancelled_reason, str):
            raise ValidationError("cancelled_reason must be str")
        self.cancelled_reason: str = cancelled_reason
        self.shipped_at: Optional[datetime] = _ensure_optional_datetime(shipped_at, "shipped_at")
        self.returned_at: Optional[datetime] = _ensure_optional_datetime(returned_at, "returned_at")
        for field_name, obj, cls in [
            ("approved_by_user", approved_by_user, userservices_users),
            ("cancelled_by_user", cancelled_by_user, userservices_users),
            ("created_by_user", created_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("product", product, productservices_products),
            ("returned_by_user", returned_by_user, userservices_users),
            ("shipped_by_user", shipped_by_user, userservices_users),
            ("so", so, orderservice_salesorder),
            ("updated_by_user", updated_by_user, userservices_users),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.approved_by_user: Optional[userservices_users] = approved_by_user
        self.cancelled_by_user: Optional[userservices_users] = cancelled_by_user
        self.created_by_user: Optional[userservices_users] = created_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.product: Optional[productservices_products] = product
        self.returned_by_user: Optional[userservices_users] = returned_by_user
        self.shipped_by_user: Optional[userservices_users] = shipped_by_user
        self.so: Optional[orderservice_salesorder] = so
        self.updated_by_user: Optional[userservices_users] = updated_by_user


class orderservice_salesorderlogs(IdEntity):
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Optional[JsonDict],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        so: Optional[orderservice_salesorder] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        if not isinstance(comment, str):
            raise ValidationError("comment must be str")
        self.comment: str = comment
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        for field_name, obj, cls in [
            ("created_by_user", created_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("so", so, orderservice_salesorder),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.created_by_user: Optional[userservices_users] = created_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.so: Optional[orderservice_salesorder] = so


class orderservice_salesorderoutwardedlog(IdEntity):
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: datetime,
        additional_details: Optional[JsonDict],
        status: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional[userservices_users] = None,
        outwarded_by_user: Optional[userservices_users] = None,
        so: Optional[orderservice_salesorder] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        for field_name, v in [("invoice_path", invoice_path), ("invoice_number", invoice_number), ("notes", notes), ("status", status)]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(outwared_at, datetime):
            raise ValidationError("outwared_at must be datetime")
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.outwared_at: datetime = outwared_at
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        self.status: str = status
        for field_name, obj, cls in [
            ("domain_user", domain_user, userservices_users),
            ("outwarded_by_user", outwarded_by_user, userservices_users),
            ("so", so, orderservice_salesorder),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.domain_user: Optional[userservices_users] = domain_user
        self.outwarded_by_user: Optional[userservices_users] = outwarded_by_user
        self.so: Optional[orderservice_salesorder] = so


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional[userservices_users] = None,
        so_item: Optional[orderservice_salesorderorderitems] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.outwarded_quantity: int = _ensure_non_negative_int(outwarded_quantity, "outwarded_quantity")
        self.price: Decimal = _ensure_non_negative_decimal(price, "price")
        self.tax_percentage: Decimal = _ensure_non_negative_decimal(tax_percentage, "tax_percentage")
        self.discount_amount: Decimal = _ensure_non_negative_decimal(discount_amount, "discount_amount")
        if not isinstance(discount_type, str):
            raise ValidationError("discount_type must be str")
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = _ensure_non_negative_decimal(shipping_amount, "shipping_amount")
        self.shipping_tax_percentage: Decimal = _ensure_non_negative_decimal(shipping_tax_percentage, "shipping_tax_percentage")
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        if not isinstance(status, str):
            raise ValidationError("status must be str")
        self.status: str = status
        if domain_user is not None and not isinstance(domain_user, userservices_users):
            raise ValidationError("domain_user must be userservices_users or None")
        if so_item is not None and not isinstance(so_item, orderservice_salesorderorderitems):
            raise ValidationError("so_item must be orderservice_salesorderorderitems or None")
        self.domain_user: Optional[userservices_users] = domain_user
        self.so_item: Optional[orderservice_salesorderorderitems] = so_item


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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
        purchase_order: Optional[orderservice_purchaseorder] = None,
        purchase_order_item: Optional[orderservice_purchaseorderitems] = None,
        purchase_order_item_inwarded_item: Optional[orderservice_purchaseorderiteminwardedlog] = None,
        rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity: int = _ensure_non_negative_int(quantity, "quantity")
        for field_name, v in [
            ("mrp", mrp),
            ("batch_number", batch_number),
            ("discount_type", discount_type),
            ("sr_no", sr_no),
            ("uom", uom),
            ("ptr", ptr),
            ("stock_status", stock_status),
            ("inward_type", inward_type),
        ]:
            if not isinstance(v, str):
                raise ValidationError(f"{field_name} must be str")
        if not isinstance(discount_amout, (int, float)):
            raise ValidationError("discount_amout must be number")
        if not isinstance(mfg_date, datetime):
            raise ValidationError("mfg_date must be datetime")
        if not isinstance(received_date, datetime):
            raise ValidationError("received_date must be datetime")
        if not isinstance(expiry_date, datetime):
            raise ValidationError("expiry_date must be datetime")
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
        self.quantity_inwarded: int = _ensure_non_negative_int(quantity_inwarded, "quantity_inwarded")
        self.buy_price: Decimal = _ensure_non_negative_decimal(buy_price, "buy_price")
        self.sell_price: Decimal = _ensure_non_negative_decimal(sell_price, "sell_price")
        self.tax_percentage: Decimal = _ensure_non_negative_decimal(tax_percentage, "tax_percentage")
        self.stock_status: str = stock_status
        self.inward_type: str = inward_type
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        for field_name, obj, cls in [
            ("added_by_user", added_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("product", product, productservices_products),
            ("purchase_order", purchase_order, orderservice_purchaseorder),
            ("purchase_order_item", purchase_order_item, orderservice_purchaseorderitems),
            ("purchase_order_item_inwarded_item", purchase_order_item_inwarded_item, orderservice_purchaseorderiteminwardedlog),
            ("rack_shelf_floor", rack_shelf_floor, inventoryservices_rackandshelvesandfloor),
            ("warehouse", warehouse, inventoryservices_warehouse),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.added_by_user: Optional[userservices_users] = added_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.product: Optional[productservices_products] = product
        self.purchase_order: Optional[orderservice_purchaseorder] = purchase_order
        self.purchase_order_item: Optional[orderservice_purchaseorderitems] = purchase_order_item
        self.purchase_order_item_inwarded_item: Optional[orderservice_purchaseorderiteminwardedlog] = purchase_order_item_inwarded_item
        self.rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = rack_shelf_floor
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


class inventoryservices_inventorylog(IdEntity):
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Optional[JsonDict],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        inventory: Optional[inventoryservices_inventory] = None,
        po: Optional[orderservice_purchaseorder] = None,
        so: Optional[orderservice_salesorder] = None,
        rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.quantity: int = _ensure_non_negative_int(quantity, "quantity")
        if not isinstance(status, str):
            raise ValidationError("status must be str")
        self.status: str = status
        self.additional_details: Optional[JsonDict] = _ensure_optional_json(additional_details, "additional_details")
        for field_name, obj, cls in [
            ("added_by_user", added_by_user, userservices_users),
            ("domain_user", domain_user, userservices_users),
            ("inventory", inventory, inventoryservices_inventory),
            ("po", po, orderservice_purchaseorder),
            ("so", so, orderservice_salesorder),
            ("rack_shelf_floor", rack_shelf_floor, inventoryservices_rackandshelvesandfloor),
            ("warehouse", warehouse, inventoryservices_warehouse),
        ]:
            if obj is not None and not isinstance(obj, cls):
                raise ValidationError(f"{field_name} must be {cls.__name__} or None")
        self.added_by_user: Optional[userservices_users] = added_by_user
        self.domain_user: Optional[userservices_users] = domain_user
        self.inventory: Optional[inventoryservices_inventory] = inventory
        self.po: Optional[orderservice_purchaseorder] = po
        self.so: Optional[orderservice_salesorder] = so
        self.rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = rack_shelf_floor
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse