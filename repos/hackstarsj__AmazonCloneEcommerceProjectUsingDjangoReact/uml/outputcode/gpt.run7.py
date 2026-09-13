from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


class ValidationError(ValueError):
    pass


class Registry:
    def __init__(self) -> None:
        self._data: Dict[type, Dict[Any, Any]] = {}

    def add(self, obj: Any, pk: Any) -> None:
        cls = type(obj)
        if cls not in self._data:
            self._data[cls] = {}
        if pk in self._data[cls]:
            raise ValidationError(f"Duplicate primary key for {cls.__name__}: {pk}")
        self._data[cls][pk] = obj

    def get(self, cls: type, pk: Any) -> Any:
        try:
            return self._data[cls][pk]
        except KeyError as e:
            raise ValidationError(f"Missing referenced {cls.__name__} with id={pk}") from e

    def has(self, cls: type, pk: Any) -> bool:
        return cls in self._data and pk in self._data[cls]


GLOBAL_REGISTRY = Registry()


class BaseEntity:
    def validate(self) -> None:
        return

    def _require_fk(self, cls: type, pk: Any, field_name: str) -> None:
        if pk is None:
            raise ValidationError(f"{type(self).__name__}.{field_name} is required")
        if not GLOBAL_REGISTRY.has(cls, pk):
            raise ValidationError(
                f"{type(self).__name__}.{field_name} references missing {cls.__name__} id={pk}"
            )


class IntPKEntity(BaseEntity):
    id: int

    def __init__(self, id: int) -> None:
        if not isinstance(id, int):
            raise ValidationError("id must be int")
        self.id = id


class BigIntPKEntity(BaseEntity):
    id: int

    def __init__(self, id: int) -> None:
        if not isinstance(id, int):
            raise ValidationError("id must be int (bigint)")
        self.id = id


class StringPKEntity(BaseEntity):
    session_key: str

    def __init__(self, session_key: str) -> None:
        if not isinstance(session_key, str) or not session_key:
            raise ValidationError("session_key must be non-empty str")
        self.session_key = session_key


class AutoIncrement:
    def __init__(self, start: int = 1) -> None:
        self._next = start

    def next(self) -> int:
        v = self._next
        self._next += 1
        return v


AUTO_INT = AutoIncrement(1)
AUTO_BIGINT = AutoIncrement(1)


def _now() -> datetime:
    return datetime.now()


def _ensure_decimal(v: Optional[Any], field: str) -> Optional[Decimal]:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        try:
            return Decimal(str(v))
        except Exception as e:
            raise ValidationError(f"{field} must be Decimal-compatible") from e
    raise ValidationError(f"{field} must be Decimal-compatible")


def _ensure_datetime(v: Optional[Any], field: str) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    raise ValidationError(f"{field} must be datetime")


def _ensure_date(v: Optional[Any], field: str) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    raise ValidationError(f"{field} must be date")


def _ensure_json(v: Optional[Any], field: str) -> Optional[JsonDict]:
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    raise ValidationError(f"{field} must be dict (json)")


def _ensure_json_list_or_dict(v: Optional[Any], field: str) -> Optional[Any]:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    raise ValidationError(f"{field} must be dict or list (json)")


def _ensure_str(v: Optional[Any], field: str, allow_empty: bool = True) -> Optional[str]:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValidationError(f"{field} must be str")
    if not allow_empty and v == "":
        raise ValidationError(f"{field} must be non-empty str")
    return v


def _ensure_int(v: Optional[Any], field: str) -> Optional[int]:
    if v is None:
        return None
    if not isinstance(v, int):
        raise ValidationError(f"{field} must be int")
    return v


def _ensure_float(v: Optional[Any], field: str) -> Optional[float]:
    if v is None:
        return None
    if not isinstance(v, (int, float)):
        raise ValidationError(f"{field} must be float")
    return float(v)


def _ensure_bool(v: Optional[Any], field: str) -> Optional[bool]:
    if v is None:
        return None
    if not isinstance(v, bool):
        raise ValidationError(f"{field} must be bool")
    return v


class userservices_users(BigIntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
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
        domain_user_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id if id is not None else AUTO_BIGINT.next())
        self.is_superuser = bool(is_superuser)
        self.first_name = _ensure_str(first_name, "first_name") or ""
        self.last_name = _ensure_str(last_name, "last_name") or ""
        self.is_staff = bool(is_staff)
        self.is_active = bool(is_active)
        self.date_joined = _ensure_datetime(date_joined, "date_joined") or _now()
        self.name = _ensure_str(name, "name") or ""
        self.email = _ensure_str(email, "email") or ""
        self.phone = _ensure_str(phone, "phone") or ""
        self.address = _ensure_str(address, "address") or ""
        self.city = _ensure_str(city, "city") or ""
        self.state = _ensure_str(state, "state") or ""
        self.pincode = _ensure_str(pincode, "pincode") or ""
        self.country = _ensure_str(country, "country") or ""
        self.profile_pic = _ensure_str(profile_pic, "profile_pic") or ""
        self.account_status = _ensure_str(account_status, "account_status") or ""
        self.role = _ensure_str(role, "role") or ""
        self.dob = _ensure_date(dob, "dob")
        self.username = _ensure_str(username, "username") or ""
        self.password = _ensure_str(password, "password") or ""
        self.social_media_links = _ensure_json(social_media_links, "social_media_links") or {}
        self.addition_details = _ensure_json(addition_details, "addition_details") or {}
        self.language = _ensure_str(language, "language") or ""
        self.departMent = _ensure_str(departMent, "departMent") or ""
        self.designation = _ensure_str(designation, "designation") or ""
        self.time_zone = _ensure_str(time_zone, "time_zone") or ""
        self.last_login = _ensure_datetime(last_login, "last_login")
        self.last_device = _ensure_str(last_device, "last_device") or ""
        self.last_ip = _ensure_str(last_ip, "last_ip") or ""
        self.currency = _ensure_str(currency, "currency") or ""
        self.domain_name = _ensure_str(domain_name, "domain_name") or ""
        self.plan_type = _ensure_str(plan_type, "plan_type") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.domain_user_id_id = domain_user_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        if self.domain_user_id_id is not None:
            self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")


class userservices_usershippingaddress(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        address_type: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        pincode: str = "",
        country: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        user_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.address_type = _ensure_str(address_type, "address_type") or ""
        self.address = _ensure_str(address, "address") or ""
        self.city = _ensure_str(city, "city") or ""
        self.state = _ensure_str(state, "state") or ""
        self.pincode = _ensure_str(pincode, "pincode") or ""
        self.country = _ensure_str(country, "country") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.user_id = user_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.user_id, "user_id")


class userservices_activitylog(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        activity: str = "",
        activity_type: str = "",
        activity_date: Optional[datetime] = None,
        activity_ip: str = "",
        activity_device: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: int,
        user_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.activity = _ensure_str(activity, "activity") or ""
        self.activity_type = _ensure_str(activity_type, "activity_type") or ""
        self.activity_date = _ensure_datetime(activity_date, "activity_date") or _now()
        self.activity_ip = _ensure_str(activity_ip, "activity_ip") or ""
        self.activity_device = _ensure_str(activity_device, "activity_device") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.domain_user_id_id = domain_user_id_id
        self.user_id = user_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.user_id, "user_id")


class userservices_modules(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
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
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.module_name = _ensure_str(module_name, "module_name") or ""
        self.module_icon = _ensure_str(module_icon, "module_icon") or ""
        self.is_menu = bool(is_menu)
        self.is_active = bool(is_active)
        self.module_url = _ensure_str(module_url, "module_url") or ""
        self.display_order = _ensure_int(display_order, "display_order") or 0
        self.module_description = _ensure_str(module_description, "module_description") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.parent_id_id = parent_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        if self.parent_id_id is not None:
            self._require_fk(userservices_modules, self.parent_id_id, "parent_id_id")


class userservices_userpermissions(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        is_view: bool = False,
        is_add: bool = False,
        is_edit: bool = False,
        is_delete: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        module_id_id: int,
        domain_user_id_id: int,
        user_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.is_view = bool(is_view)
        self.is_add = bool(is_add)
        self.is_edit = bool(is_edit)
        self.is_delete = bool(is_delete)
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.module_id_id = module_id_id
        self.domain_user_id_id = domain_user_id_id
        self.user_id = user_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_modules, self.module_id_id, "module_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.user_id, "user_id")


class auth_group(IntPKEntity):
    def __init__(self, id: Optional[int] = None, *, name: str = "") -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.name = _ensure_str(name, "name") or ""
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)


class django_content_type(IntPKEntity):
    def __init__(self, id: Optional[int] = None, *, app_label: str = "", model: str = "") -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.app_label = _ensure_str(app_label, "app_label") or ""
        self.model = _ensure_str(model, "model") or ""
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)


class auth_permission(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        name: str = "",
        codename: str = "",
        content_type_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.name = _ensure_str(name, "name") or ""
        self.codename = _ensure_str(codename, "codename") or ""
        self.content_type_id = content_type_id
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(django_content_type, self.content_type_id, "content_type_id")


class auth_group_permissions(BigIntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        group_id: int,
        permission_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_BIGINT.next())
        self.group_id = group_id
        self.permission_id = permission_id
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(auth_group, self.group_id, "group_id")
        self._require_fk(auth_permission, self.permission_id, "permission_id")


class userservices_users_groups(BigIntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        users_id: int,
        group_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_BIGINT.next())
        self.users_id = users_id
        self.group_id = group_id
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.users_id, "users_id")
        self._require_fk(auth_group, self.group_id, "group_id")


class userservices_users_user_permissions(BigIntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        users_id: int,
        permission_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_BIGINT.next())
        self.users_id = users_id
        self.permission_id = permission_id
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.users_id, "users_id")
        self._require_fk(auth_permission, self.permission_id, "permission_id")


class django_admin_log(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        action_time: Optional[datetime] = None,
        object_id: str = "",
        object_repr: str = "",
        action_flag: int = 0,
        change_message: str = "",
        content_type_id: int,
        user_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.action_time = _ensure_datetime(action_time, "action_time") or _now()
        self.object_id = _ensure_str(object_id, "object_id") or ""
        self.object_repr = _ensure_str(object_repr, "object_repr") or ""
        self.action_flag = _ensure_int(action_flag, "action_flag") or 0
        self.change_message = _ensure_str(change_message, "change_message") or ""
        self.content_type_id = content_type_id
        self.user_id = user_id
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(django_content_type, self.content_type_id, "content_type_id")
        self._require_fk(userservices_users, self.user_id, "user_id")


class django_migrations(BigIntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        app: str = "",
        name: str = "",
        applied: Optional[datetime] = None,
    ) -> None:
        super().__init__(id if id is not None else AUTO_BIGINT.next())
        self.app = _ensure_str(app, "app") or ""
        self.name = _ensure_str(name, "name") or ""
        self.applied = _ensure_datetime(applied, "applied") or _now()
        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)


class django_session(StringPKEntity):
    def __init__(
        self,
        session_key: str,
        *,
        session_data: str = "",
        expire_date: Optional[datetime] = None,
    ) -> None:
        super().__init__(session_key)
        self.session_data = _ensure_str(session_data, "session_data") or ""
        self.expire_date = _ensure_datetime(expire_date, "expire_date") or _now()
        self.validate()
        GLOBAL_REGISTRY.add(self, self.session_key)


class productservices_categories(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        name: str = "",
        image: str = "",
        description: str = "",
        display_order: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: int,
        domain_user_id_id: int,
        parent_id_id: Optional[int] = None,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.name = _ensure_str(name, "name") or ""
        self.image = _ensure_str(image, "image") or ""
        self.description = _ensure_str(description, "description") or ""
        self.display_order = _ensure_int(display_order, "display_order") or 0
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.parent_id_id = parent_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.added_by_user_id_id, "added_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        if self.parent_id_id is not None:
            self._require_fk(productservices_categories, self.parent_id_id, "parent_id_id")


class productservices_products(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        name: str = "",
        image: Optional[Any] = None,
        description: str = "",
        specifications: Optional[JsonDict] = None,
        html_description: str = "",
        highlights: Optional[Any] = None,
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
        seo_keywords: Optional[Any] = None,
        addition_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: int = 0,
        category_id_id: int = 0,
        domain_user_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.name = _ensure_str(name, "name") or ""
        self.image = _ensure_json_list_or_dict(image, "image") if image is not None else {}
        self.description = _ensure_str(description, "description") or ""
        self.specifications = _ensure_json(specifications, "specifications") or {}
        self.html_description = _ensure_str(html_description, "html_description") or ""
        self.highlights = _ensure_json_list_or_dict(highlights, "highlights") if highlights is not None else []
        self.sku = _ensure_str(sku, "sku") or ""
        self.initial_buying_price = _ensure_float(initial_buying_price, "initial_buying_price") or 0.0
        self.initial_selling_price = _ensure_float(initial_selling_price, "initial_selling_price") or 0.0
        self.weight = _ensure_float(weight, "weight") or 0.0
        self.dimensions = _ensure_str(dimensions, "dimensions") or ""
        self.uom = _ensure_str(uom, "uom") or ""
        self.color = _ensure_str(color, "color") or ""
        self.tax_percentage = _ensure_float(tax_percentage, "tax_percentage") or 0.0
        self.brand = _ensure_str(brand, "brand") or ""
        self.brand_model = _ensure_str(brand_model, "brand_model") or ""
        self.status = _ensure_str(status, "status") or ""
        self.seo_title = _ensure_str(seo_title, "seo_title") or ""
        self.seo_description = _ensure_str(seo_description, "seo_description") or ""
        self.seo_keywords = _ensure_json_list_or_dict(seo_keywords, "seo_keywords") if seo_keywords is not None else []
        self.addition_details = _ensure_json(addition_details, "addition_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.added_by_user_id_id = added_by_user_id_id
        self.category_id_id = category_id_id
        self.domain_user_id_id = domain_user_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.added_by_user_id_id, "added_by_user_id_id")
        self._require_fk(productservices_categories, self.category_id_id, "category_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")


class productservices_productquestions(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        question: str = "",
        answer: str = "",
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        answer_user_id_id: int,
        domain_user_id_id: int,
        question_user_id_id: int,
        product_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.question = _ensure_str(question, "question") or ""
        self.answer = _ensure_str(answer, "answer") or ""
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.answer_user_id_id = answer_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.question_user_id_id = question_user_id_id
        self.product_id_id = product_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.answer_user_id_id, "answer_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.question_user_id_id, "question_user_id_id")
        self._require_fk(productservices_products, self.product_id_id, "product_id_id")


class productservices_productreviews(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        review_images: Optional[Any] = None,
        rating: float = 0.0,
        reviews: str = "",
        status: str = "",
        domain_user_id_id: int,
        review_user_id_id: int,
        product_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.review_images = _ensure_json_list_or_dict(review_images, "review_images") if review_images is not None else []
        self.rating = _ensure_float(rating, "rating") or 0.0
        self.reviews = _ensure_str(reviews, "reviews") or ""
        self.status = _ensure_str(status, "status") or ""
        self.domain_user_id_id = domain_user_id_id
        self.review_user_id_id = review_user_id_id
        self.product_id_id = product_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.review_user_id_id, "review_user_id_id")
        self._require_fk(productservices_products, self.product_id_id, "product_id_id")


class inventoryservices_warehouse(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
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
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: int,
        domain_user_id_id: int,
        warehouse_manager_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.name = _ensure_str(name, "name") or ""
        self.address = _ensure_str(address, "address") or ""
        self.city = _ensure_str(city, "city") or ""
        self.state = _ensure_str(state, "state") or ""
        self.country = _ensure_str(country, "country") or ""
        self.pincode = _ensure_str(pincode, "pincode") or ""
        self.phone = _ensure_str(phone, "phone") or ""
        self.email = _ensure_str(email, "email") or ""
        self.status = _ensure_str(status, "status") or ""
        self.size = _ensure_str(size, "size") or ""
        self.capacity = _ensure_str(capacity, "capacity") or ""
        self.warehouse_type = _ensure_str(warehouse_type, "warehouse_type") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.warehouse_manager_id = warehouse_manager_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.added_by_user_id_id, "added_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.warehouse_manager_id, "warehouse_manager_id")


class inventoryservices_rackandshelvesandfloor(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        name: str = "",
        rack: str = "",
        shelf: str = "",
        floor: str = "",
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: int,
        domain_user_id_id: int,
        warehouse_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.name = _ensure_str(name, "name") or ""
        self.rack = _ensure_str(rack, "rack") or ""
        self.shelf = _ensure_str(shelf, "shelf") or ""
        self.floor = _ensure_str(floor, "floor") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.warehouse_id_id = warehouse_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.added_by_user_id_id, "added_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(inventoryservices_warehouse, self.warehouse_id_id, "warehouse_id_id")


class orderservice_purchaseorder(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        po_code: str = "",
        po_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Optional[Any] = None,
        paid_amount: Optional[Any] = None,
        due_amount: Optional[Any] = None,
        discount_amount: Optional[Any] = None,
        discount_type: str = "",
        shipping_amount: Optional[Any] = None,
        shipping_type: str = "",
        shipping_tax_percentage: Optional[Any] = None,
        shipping_tax_amount: Optional[Any] = None,
        shipping_cancelled_amount: Optional[Any] = None,
        shipping_cancelled_tax_amount: Optional[Any] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: int = 0,
        cancelled_by_user_id_id: int = 0,
        created_by_user_id_id: int = 0,
        domain_user_id_id: int = 0,
        last_updated_by_user_id_id: int = 0,
        received_by_user_id_id: int = 0,
        returned_by_user_id_id: int = 0,
        supplier_id_id: int = 0,
        updated_by_user_id_id: int = 0,
        warehouse_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.po_code = _ensure_str(po_code, "po_code") or ""
        self.po_date = _ensure_datetime(po_date, "po_date") or _now()
        self.expected_delivery_date = _ensure_datetime(expected_delivery_date, "expected_delivery_date")
        self.payment_terms = _ensure_str(payment_terms, "payment_terms") or ""
        self.payment_status = _ensure_str(payment_status, "payment_status") or ""
        self.total_amount = _ensure_decimal(total_amount, "total_amount") or Decimal("0")
        self.paid_amount = _ensure_decimal(paid_amount, "paid_amount") or Decimal("0")
        self.due_amount = _ensure_decimal(due_amount, "due_amount") or Decimal("0")
        self.discount_amount = _ensure_decimal(discount_amount, "discount_amount") or Decimal("0")
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.shipping_amount = _ensure_decimal(shipping_amount, "shipping_amount") or Decimal("0")
        self.shipping_type = _ensure_str(shipping_type, "shipping_type") or ""
        self.shipping_tax_percentage = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage") or Decimal("0")
        self.shipping_tax_amount = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount") or Decimal("0")
        self.shipping_cancelled_amount = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount") or Decimal("0")
        self.shipping_cancelled_tax_amount = _ensure_decimal(shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount") or Decimal("0")
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.approved_at = _ensure_datetime(approved_at, "approved_at")
        self.cancelled_at = _ensure_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason = _ensure_str(cancelled_reason, "cancelled_reason") or ""
        self.received_at = _ensure_datetime(received_at, "received_at")
        self.returned_at = _ensure_datetime(returned_at, "returned_at")
        self.approved_by_user_id_id = approved_by_user_id_id
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.last_updated_by_user_id_id = last_updated_by_user_id_id
        self.received_by_user_id_id = received_by_user_id_id
        self.returned_by_user_id_id = returned_by_user_id_id
        self.supplier_id_id = supplier_id_id
        self.updated_by_user_id_id = updated_by_user_id_id
        self.warehouse_id_id = warehouse_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(inventoryservices_warehouse, self.warehouse_id_id, "warehouse_id_id")
        self._require_fk(userservices_users, self.supplier_id_id, "supplier_id_id")
        self._require_fk(userservices_users, self.created_by_user_id_id, "created_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.updated_by_user_id_id, "updated_by_user_id_id")
        self._require_fk(userservices_users, self.last_updated_by_user_id_id, "last_updated_by_user_id_id")
        self._require_fk(userservices_users, self.approved_by_user_id_id, "approved_by_user_id_id")
        self._require_fk(userservices_users, self.cancelled_by_user_id_id, "cancelled_by_user_id_id")
        self._require_fk(userservices_users, self.received_by_user_id_id, "received_by_user_id_id")
        self._require_fk(userservices_users, self.returned_by_user_id_id, "returned_by_user_id_id")


class orderservice_purchaseorderitems(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        quantity_ordered: int = 0,
        quantity_received: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        buying_price: Optional[Any] = None,
        selling_price: Optional[Any] = None,
        discount_amount: Optional[Any] = None,
        amount_paid: Optional[Any] = None,
        amount_returned: Optional[Any] = None,
        amount_cancelled: Optional[Any] = None,
        amount_ordered: Optional[Any] = None,
        tax_percentage: Optional[Any] = None,
        tax_amount: Optional[Any] = None,
        shipping_tax_percentage: Optional[Any] = None,
        shipping_amount: Optional[Any] = None,
        shipping_tax_amount: Optional[Any] = None,
        shipping_cancelled_amount: Optional[Any] = None,
        shipping_cancelled_tax_amount: Optional[Any] = None,
        discount_type: str = "",
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: int = 0,
        cancelled_by_user_id_id: int = 0,
        created_by_user_id_id: int = 0,
        domain_user_id_id: int = 0,
        last_updated_by_user_id_id: int = 0,
        received_by_user_id_id: int = 0,
        returned_by_user_id_id: int = 0,
        po_id_id: int = 0,
        product_id_id: int = 0,
        updated_by_user_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.quantity_ordered = _ensure_int(quantity_ordered, "quantity_ordered") or 0
        self.quantity_received = _ensure_int(quantity_received, "quantity_received") or 0
        self.quantity_cancelled = _ensure_int(quantity_cancelled, "quantity_cancelled") or 0
        self.quantity_returned = _ensure_int(quantity_returned, "quantity_returned") or 0
        self.buying_price = _ensure_decimal(buying_price, "buying_price") or Decimal("0")
        self.selling_price = _ensure_decimal(selling_price, "selling_price") or Decimal("0")
        self.discount_amount = _ensure_decimal(discount_amount, "discount_amount") or Decimal("0")
        self.amount_paid = _ensure_decimal(amount_paid, "amount_paid") or Decimal("0")
        self.amount_returned = _ensure_decimal(amount_returned, "amount_returned") or Decimal("0")
        self.amount_cancelled = _ensure_decimal(amount_cancelled, "amount_cancelled") or Decimal("0")
        self.amount_ordered = _ensure_decimal(amount_ordered, "amount_ordered") or Decimal("0")
        self.tax_percentage = _ensure_decimal(tax_percentage, "tax_percentage") or Decimal("0")
        self.tax_amount = _ensure_decimal(tax_amount, "tax_amount") or Decimal("0")
        self.shipping_tax_percentage = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage") or Decimal("0")
        self.shipping_amount = _ensure_decimal(shipping_amount, "shipping_amount") or Decimal("0")
        self.shipping_tax_amount = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount") or Decimal("0")
        self.shipping_cancelled_amount = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount") or Decimal("0")
        self.shipping_cancelled_tax_amount = _ensure_decimal(shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount") or Decimal("0")
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.approved_at = _ensure_datetime(approved_at, "approved_at")
        self.cancelled_at = _ensure_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason = _ensure_str(cancelled_reason, "cancelled_reason") or ""
        self.received_at = _ensure_datetime(received_at, "received_at")
        self.returned_at = _ensure_datetime(returned_at, "returned_at")
        self.approved_by_user_id_id = approved_by_user_id_id
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.last_updated_by_user_id_id = last_updated_by_user_id_id
        self.received_by_user_id_id = received_by_user_id_id
        self.returned_by_user_id_id = returned_by_user_id_id
        self.po_id_id = po_id_id
        self.product_id_id = product_id_id
        self.updated_by_user_id_id = updated_by_user_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(orderservice_purchaseorder, self.po_id_id, "po_id_id")
        self._require_fk(productservices_products, self.product_id_id, "product_id_id")
        self._require_fk(userservices_users, self.created_by_user_id_id, "created_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.updated_by_user_id_id, "updated_by_user_id_id")
        self._require_fk(userservices_users, self.last_updated_by_user_id_id, "last_updated_by_user_id_id")
        self._require_fk(userservices_users, self.approved_by_user_id_id, "approved_by_user_id_id")
        self._require_fk(userservices_users, self.cancelled_by_user_id_id, "cancelled_by_user_id_id")
        self._require_fk(userservices_users, self.received_by_user_id_id, "received_by_user_id_id")
        self._require_fk(userservices_users, self.returned_by_user_id_id, "returned_by_user_id_id")


class orderservice_purchaseorderlogs(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        comment: str = "",
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: int,
        domain_user_id_id: int,
        po_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.comment = _ensure_str(comment, "comment") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.po_id_id = po_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.created_by_user_id_id, "created_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(orderservice_purchaseorder, self.po_id_id, "po_id_id")


class orderservice_purchaseorderinwardedlog(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        inwarded_at: Optional[datetime] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: int,
        inwarded_by_user_id_id: int,
        po_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.invoice_path = _ensure_str(invoice_path, "invoice_path") or ""
        self.invoice_number = _ensure_str(invoice_number, "invoice_number") or ""
        self.notes = _ensure_str(notes, "notes") or ""
        self.inwarded_at = _ensure_datetime(inwarded_at, "inwarded_at") or _now()
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.domain_user_id_id = domain_user_id_id
        self.inwarded_by_user_id_id = inwarded_by_user_id_id
        self.po_id_id = po_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.inwarded_by_user_id_id, "inwarded_by_user_id_id")
        self._require_fk(orderservice_purchaseorder, self.po_id_id, "po_id_id")


class orderservice_purchaseorderiteminwardedlog(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        inwarded_quantity: int = 0,
        price: Optional[Any] = None,
        tax_percentage: Optional[Any] = None,
        discount_amount: Optional[Any] = None,
        discount_type: str = "",
        shipping_amount: Optional[Any] = None,
        shipping_tax_percentage: Optional[Any] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: int,
        po_item_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.inwarded_quantity = _ensure_int(inwarded_quantity, "inwarded_quantity") or 0
        self.price = _ensure_decimal(price, "price") or Decimal("0")
        self.tax_percentage = _ensure_decimal(tax_percentage, "tax_percentage") or Decimal("0")
        self.discount_amount = _ensure_decimal(discount_amount, "discount_amount") or Decimal("0")
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.shipping_amount = _ensure_decimal(shipping_amount, "shipping_amount") or Decimal("0")
        self.shipping_tax_percentage = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage") or Decimal("0")
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.domain_user_id_id = domain_user_id_id
        self.po_item_id_id = po_item_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(orderservice_purchaseorderitems, self.po_item_id_id, "po_item_id_id")


class orderservice_salesorder(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        so_code: str = "",
        so_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Optional[Any] = None,
        paid_amount: Optional[Any] = None,
        due_amount: Optional[Any] = None,
        discount_amount: Optional[Any] = None,
        discount_type: str = "",
        shipping_amount: Optional[Any] = None,
        shipping_type: str = "",
        shipping_tax_percentage: Optional[Any] = None,
        shipping_tax_amount: Optional[Any] = None,
        shipping_cancelled_amount: Optional[Any] = None,
        shipping_cancelled_tax_amount: Optional[Any] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: int = 0,
        cancelled_by_user_id_id: int = 0,
        created_by_user_id_id: int = 0,
        customer_id_id: int = 0,
        domain_user_id_id: int = 0,
        last_updated_by_user_id_id: int = 0,
        received_by_user_id_id: int = 0,
        returned_by_user_id_id: int = 0,
        po_id_id: int = 0,
        product_id_id: int = 0,
        updated_by_user_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.so_code = _ensure_str(so_code, "so_code") or ""
        self.so_date = _ensure_datetime(so_date, "so_date") or _now()
        self.expected_delivery_date = _ensure_datetime(expected_delivery_date, "expected_delivery_date")
        self.payment_terms = _ensure_str(payment_terms, "payment_terms") or ""
        self.payment_status = _ensure_str(payment_status, "payment_status") or ""
        self.total_amount = _ensure_decimal(total_amount, "total_amount") or Decimal("0")
        self.paid_amount = _ensure_decimal(paid_amount, "paid_amount") or Decimal("0")
        self.due_amount = _ensure_decimal(due_amount, "due_amount") or Decimal("0")
        self.discount_amount = _ensure_decimal(discount_amount, "discount_amount") or Decimal("0")
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.shipping_amount = _ensure_decimal(shipping_amount, "shipping_amount") or Decimal("0")
        self.shipping_type = _ensure_str(shipping_type, "shipping_type") or ""
        self.shipping_tax_percentage = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage") or Decimal("0")
        self.shipping_tax_amount = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount") or Decimal("0")
        self.shipping_cancelled_amount = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount") or Decimal("0")
        self.shipping_cancelled_tax_amount = _ensure_decimal(shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount") or Decimal("0")
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.approved_at = _ensure_datetime(approved_at, "approved_at")
        self.cancelled_at = _ensure_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason = _ensure_str(cancelled_reason, "cancelled_reason") or ""
        self.received_at = _ensure_datetime(received_at, "received_at")
        self.returned_at = _ensure_datetime(returned_at, "returned_at")
        self.approved_by_user_id_id = approved_by_user_id_id
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.created_by_user_id_id = created_by_user_id_id
        self.customer_id_id = customer_id_id
        self.domain_user_id_id = domain_user_id_id
        self.last_updated_by_user_id_id = last_updated_by_user_id_id
        self.received_by_user_id_id = received_by_user_id_id
        self.returned_by_user_id_id = returned_by_user_id_id
        self.po_id_id = po_id_id
        self.product_id_id = product_id_id
        self.updated_by_user_id_id = updated_by_user_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.customer_id_id, "customer_id_id")
        self._require_fk(userservices_users, self.created_by_user_id_id, "created_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.updated_by_user_id_id, "updated_by_user_id_id")
        self._require_fk(userservices_users, self.last_updated_by_user_id_id, "last_updated_by_user_id_id")
        self._require_fk(userservices_users, self.approved_by_user_id_id, "approved_by_user_id_id")
        self._require_fk(userservices_users, self.cancelled_by_user_id_id, "cancelled_by_user_id_id")
        self._require_fk(userservices_users, self.received_by_user_id_id, "received_by_user_id_id")
        self._require_fk(userservices_users, self.returned_by_user_id_id, "returned_by_user_id_id")
        self._require_fk(orderservice_purchaseorder, self.po_id_id, "po_id_id")
        self._require_fk(productservices_products, self.product_id_id, "product_id_id")


class orderservice_salesorderorderitems(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        quantity_ordered: int = 0,
        quantity_delivered: int = 0,
        quantity_shipped: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        purchase_price: Optional[Any] = None,
        discount_amount: Optional[Any] = None,
        discount_type: str = "",
        amount_paid: Optional[Any] = None,
        amount_returned: Optional[Any] = None,
        amount_cancelled: Optional[Any] = None,
        amount_ordered: Optional[Any] = None,
        tax_percentage: Optional[Any] = None,
        tax_amount: Optional[Any] = None,
        shipping_amount: Optional[Any] = None,
        shipping_type: str = "",
        shipping_tax_amount: Optional[Any] = None,
        shipping_cancelled_amount: Optional[Any] = None,
        shipping_cancelled_tax_amount: Optional[Any] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
        shipped_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user_id_id: int = 0,
        cancelled_by_user_id_id: int = 0,
        created_by_user_id_id: int = 0,
        domain_user_id_id: int = 0,
        product_id_id: int = 0,
        returned_by_user_id_id: int = 0,
        shipped_by_user_id_id: int = 0,
        so_id_id: int = 0,
        updated_by_user_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.quantity_ordered = _ensure_int(quantity_ordered, "quantity_ordered") or 0
        self.quantity_delivered = _ensure_int(quantity_delivered, "quantity_delivered") or 0
        self.quantity_shipped = _ensure_int(quantity_shipped, "quantity_shipped") or 0
        self.quantity_cancelled = _ensure_int(quantity_cancelled, "quantity_cancelled") or 0
        self.quantity_returned = _ensure_int(quantity_returned, "quantity_returned") or 0
        self.purchase_price = _ensure_decimal(purchase_price, "purchase_price") or Decimal("0")
        self.discount_amount = _ensure_decimal(discount_amount, "discount_amount") or Decimal("0")
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.amount_paid = _ensure_decimal(amount_paid, "amount_paid") or Decimal("0")
        self.amount_returned = _ensure_decimal(amount_returned, "amount_returned") or Decimal("0")
        self.amount_cancelled = _ensure_decimal(amount_cancelled, "amount_cancelled") or Decimal("0")
        self.amount_ordered = _ensure_decimal(amount_ordered, "amount_ordered") or Decimal("0")
        self.tax_percentage = _ensure_decimal(tax_percentage, "tax_percentage") or Decimal("0")
        self.tax_amount = _ensure_decimal(tax_amount, "tax_amount") or Decimal("0")
        self.shipping_amount = _ensure_decimal(shipping_amount, "shipping_amount") or Decimal("0")
        self.shipping_type = _ensure_str(shipping_type, "shipping_type") or ""
        self.shipping_tax_amount = _ensure_decimal(shipping_tax_amount, "shipping_tax_amount") or Decimal("0")
        self.shipping_cancelled_amount = _ensure_decimal(shipping_cancelled_amount, "shipping_cancelled_amount") or Decimal("0")
        self.shipping_cancelled_tax_amount = _ensure_decimal(shipping_cancelled_tax_amount, "shipping_cancelled_tax_amount") or Decimal("0")
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.approved_at = _ensure_datetime(approved_at, "approved_at")
        self.cancelled_at = _ensure_datetime(cancelled_at, "cancelled_at")
        self.cancelled_reason = _ensure_str(cancelled_reason, "cancelled_reason") or ""
        self.shipped_at = _ensure_datetime(shipped_at, "shipped_at")
        self.returned_at = _ensure_datetime(returned_at, "returned_at")
        self.approved_by_user_id_id = approved_by_user_id_id
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.product_id_id = product_id_id
        self.returned_by_user_id_id = returned_by_user_id_id
        self.shipped_by_user_id_id = shipped_by_user_id_id
        self.so_id_id = so_id_id
        self.updated_by_user_id_id = updated_by_user_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(orderservice_salesorder, self.so_id_id, "so_id_id")
        self._require_fk(productservices_products, self.product_id_id, "product_id_id")
        self._require_fk(userservices_users, self.created_by_user_id_id, "created_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.updated_by_user_id_id, "updated_by_user_id_id")
        self._require_fk(userservices_users, self.approved_by_user_id_id, "approved_by_user_id_id")
        self._require_fk(userservices_users, self.cancelled_by_user_id_id, "cancelled_by_user_id_id")
        self._require_fk(userservices_users, self.shipped_by_user_id_id, "shipped_by_user_id_id")
        self._require_fk(userservices_users, self.returned_by_user_id_id, "returned_by_user_id_id")


class orderservice_salesorderlogs(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        comment: str = "",
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: int,
        domain_user_id_id: int,
        so_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.comment = _ensure_str(comment, "comment") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.so_id_id = so_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.created_by_user_id_id, "created_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(orderservice_salesorder, self.so_id_id, "so_id_id")


class orderservice_salesorderoutwardedlog(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        outwared_at: Optional[datetime] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: int,
        outwarded_by_user_id_id: int,
        so_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.invoice_path = _ensure_str(invoice_path, "invoice_path") or ""
        self.invoice_number = _ensure_str(invoice_number, "invoice_number") or ""
        self.notes = _ensure_str(notes, "notes") or ""
        self.outwared_at = _ensure_datetime(outwared_at, "outwared_at") or _now()
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.domain_user_id_id = domain_user_id_id
        self.outwarded_by_user_id_id = outwarded_by_user_id_id
        self.so_id_id = so_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(userservices_users, self.outwarded_by_user_id_id, "outwarded_by_user_id_id")
        self._require_fk(orderservice_salesorder, self.so_id_id, "so_id_id")


class orderservice_salesorderitemoutwardedlog(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        outwarded_quantity: int = 0,
        price: Optional[Any] = None,
        tax_percentage: Optional[Any] = None,
        discount_amount: Optional[Any] = None,
        discount_type: str = "",
        shipping_amount: Optional[Any] = None,
        shipping_tax_percentage: Optional[Any] = None,
        additional_details: Optional[JsonDict] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: int,
        so_item_id_id: int,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.outwarded_quantity = _ensure_int(outwarded_quantity, "outwarded_quantity") or 0
        self.price = _ensure_decimal(price, "price") or Decimal("0")
        self.tax_percentage = _ensure_decimal(tax_percentage, "tax_percentage") or Decimal("0")
        self.discount_amount = _ensure_decimal(discount_amount, "discount_amount") or Decimal("0")
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.shipping_amount = _ensure_decimal(shipping_amount, "shipping_amount") or Decimal("0")
        self.shipping_tax_percentage = _ensure_decimal(shipping_tax_percentage, "shipping_tax_percentage") or Decimal("0")
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.status = _ensure_str(status, "status") or ""
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.domain_user_id_id = domain_user_id_id
        self.so_item_id_id = so_item_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(orderservice_salesorderorderitems, self.so_item_id_id, "so_item_id_id")


class inventoryservices_inventory(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
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
        buy_price: Optional[Any] = None,
        sell_price: Optional[Any] = None,
        tax_percentage: Optional[Any] = None,
        stock_status: str = "",
        inward_type: str = "",
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: int = 0,
        domain_user_id_id: int = 0,
        product_id_id: int = 0,
        purchase_order_id_id: int = 0,
        purchase_order_item_id_id: int = 0,
        purchase_order_item_inwarded_item_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: int = 0,
        warehouse_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.quantity = _ensure_int(quantity, "quantity") or 0
        self.mrp = _ensure_str(mrp, "mrp") or ""
        self.batch_number = _ensure_str(batch_number, "batch_number") or ""
        self.discount_type = _ensure_str(discount_type, "discount_type") or ""
        self.discount_amout = _ensure_float(discount_amout, "discount_amout") or 0.0
        self.sr_no = _ensure_str(sr_no, "sr_no") or ""
        self.mfg_date = _ensure_datetime(mfg_date, "mfg_date")
        self.uom = _ensure_str(uom, "uom") or ""
        self.ptr = _ensure_str(ptr, "ptr") or ""
        self.received_date = _ensure_datetime(received_date, "received_date")
        self.expiry_date = _ensure_datetime(expiry_date, "expiry_date")
        self.quantity_inwarded = _ensure_int(quantity_inwarded, "quantity_inwarded") or 0
        self.buy_price = _ensure_decimal(buy_price, "buy_price") or Decimal("0")
        self.sell_price = _ensure_decimal(sell_price, "sell_price") or Decimal("0")
        self.tax_percentage = _ensure_decimal(tax_percentage, "tax_percentage") or Decimal("0")
        self.stock_status = _ensure_str(stock_status, "stock_status") or ""
        self.inward_type = _ensure_str(inward_type, "inward_type") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.product_id_id = product_id_id
        self.purchase_order_id_id = purchase_order_id_id
        self.purchase_order_item_id_id = purchase_order_item_id_id
        self.purchase_order_item_inwarded_item_id_id = purchase_order_item_inwarded_item_id_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.warehouse_id_id = warehouse_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(productservices_products, self.product_id_id, "product_id_id")
        self._require_fk(inventoryservices_warehouse, self.warehouse_id_id, "warehouse_id_id")
        self._require_fk(inventoryservices_rackandshelvesandfloor, self.rack_shelf_floor_id_id, "rack_shelf_floor_id_id")
        self._require_fk(orderservice_purchaseorder, self.purchase_order_id_id, "purchase_order_id_id")
        self._require_fk(orderservice_purchaseorderitems, self.purchase_order_item_id_id, "purchase_order_item_id_id")
        if self.purchase_order_item_inwarded_item_id_id is not None:
            self._require_fk(
                orderservice_purchaseorderiteminwardedlog,
                self.purchase_order_item_inwarded_item_id_id,
                "purchase_order_item_inwarded_item_id_id",
            )
        self._require_fk(userservices_users, self.added_by_user_id_id, "added_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")


class inventoryservices_inventorylog(IntPKEntity):
    def __init__(
        self,
        id: Optional[int] = None,
        *,
        quantity: int = 0,
        status: str = "",
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: int,
        domain_user_id_id: int,
        inventory_id_id: int,
        po_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: int = 0,
        warehouse_id_id: int = 0,
    ) -> None:
        super().__init__(id if id is not None else AUTO_INT.next())
        self.quantity = _ensure_int(quantity, "quantity") or 0
        self.status = _ensure_str(status, "status") or ""
        self.additional_details = _ensure_json(additional_details, "additional_details") or {}
        self.created_at = _ensure_datetime(created_at, "created_at") or _now()
        self.updated_at = _ensure_datetime(updated_at, "updated_at") or _now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.inventory_id_id = inventory_id_id
        self.po_id_id = po_id_id
        self.so_id_id = so_id_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.warehouse_id_id = warehouse_id_id

        self.validate()
        GLOBAL_REGISTRY.add(self, self.id)

    def validate(self) -> None:
        self._require_fk(userservices_users, self.added_by_user_id_id, "added_by_user_id_id")
        self._require_fk(userservices_users, self.domain_user_id_id, "domain_user_id_id")
        self._require_fk(inventoryservices_inventory, self.inventory_id_id, "inventory_id_id")
        self._require_fk(inventoryservices_warehouse, self.warehouse_id_id, "warehouse_id_id")
        self._require_fk(inventoryservices_rackandshelvesandfloor, self.rack_shelf_floor_id_id, "rack_shelf_floor_id_id")
        if self.po_id_id is not None:
            self._require_fk(orderservice_purchaseorder, self.po_id_id, "po_id_id")
        if self.so_id_id is not None:
            self._require_fk(orderservice_salesorder, self.so_id_id, "so_id_id")