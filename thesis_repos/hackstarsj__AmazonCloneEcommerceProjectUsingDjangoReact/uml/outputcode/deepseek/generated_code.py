"""
Complete Python implementation of the ecommerce project entity model.
Derived from the PlantUML ER diagram.
All classes, relationships, and basic business rules are implemented.
Uses an in-memory storage (simple ORM) for demonstration.
"""

import datetime
import decimal
import json
from typing import Optional, List, Dict, Any, Union, TypeVar, Type, ClassVar

# ---------------------------------------------------------------------
# Base Model with simple in-memory storage
# ---------------------------------------------------------------------

class Model:
    """Minimal ORM-like base class. Each subclass manages its own objects."""
    _objects: ClassVar[Dict[int, 'Model']]
    _next_id: ClassVar[int]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._objects = {}
        cls._next_id = 1

    @classmethod
    def _get_next_id(cls) -> int:
        current = cls._next_id
        cls._next_id += 1
        return current

    def __init__(self, **kwargs) -> None:
        self._id: Optional[int] = None
        self._is_saved: bool = False
        # Subclasses will fill attributes

    def save(self) -> None:
        if self._is_saved and hasattr(self, 'id') and self.id is not None:
            # Update case: could update timestamp, but for simplicity keep
            self._updated_at = datetime.datetime.now()
            return
        if not hasattr(self, 'id') or self.id is None:
            self.id = self._get_next_id()
        cls = type(self)
        cls._objects[self.id] = self
        self._is_saved = True
        now = datetime.datetime.now()
        if not hasattr(self, 'created_at') or self.created_at is None:
            self.created_at = now
        if not hasattr(self, 'updated_at') or self.updated_at is None:
            self.updated_at = now

    @classmethod
    def all(cls) -> List['Model']:
        return list(cls._objects.values())

    @classmethod
    def get(cls, id: int) -> Optional['Model']:
        return cls._objects.get(id)

    @classmethod
    def filter(cls, **kwargs) -> List['Model']:
        results = []
        for obj in cls._objects.values():
            match = True
            for attr, val in kwargs.items():
                if getattr(obj, attr, None) != val:
                    match = False
                    break
            if match:
                results.append(obj)
        return results

    def delete(self) -> None:
        cls = type(self)
        if self.id in cls._objects:
            del cls._objects[self.id]
            self._is_saved = False


# ---------------------------------------------------------------------
# User Service Models
# ---------------------------------------------------------------------

class userservices_users(Model):
    def __init__(
        self,
        is_superuser: bool = False,
        first_name: str = '',
        last_name: str = '',
        is_staff: bool = False,
        is_active: bool = True,
        date_joined: Optional[datetime.datetime] = None,
        name: str = '',
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None,
        country: Optional[str] = None,
        profile_pic: Optional[str] = None,
        account_status: str = 'active',
        role: Optional[str] = None,
        dob: Optional[datetime.date] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        social_media_links: Optional[dict] = None,
        addition_details: Optional[dict] = None,
        language: Optional[str] = None,
        department: Optional[str] = None,
        designation: Optional[str] = None,
        time_zone: Optional[str] = None,
        last_login: Optional[datetime.datetime] = None,
        last_device: Optional[str] = None,
        last_ip: Optional[str] = None,
        currency: Optional[str] = None,
        domain_name: Optional[str] = None,
        plan_type: Optional[str] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        domain_user_id_id: Optional[int] = None,
        # Additional FK references
        domain_user: Optional['userservices_users'] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.is_superuser = is_superuser
        self.first_name = first_name
        self.last_name = last_name
        self.is_staff = is_staff
        self.is_active = is_active
        self.date_joined = date_joined if date_joined else datetime.datetime.now()
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.domain_user_id_id = domain_user_id_id
        self.domain_user = domain_user

    def validate(self) -> None:
        if not self.email and not self.username:
            raise ValueError("Either email or username must be provided")
        if self.email and '@' not in self.email:
            raise ValueError("Invalid email format")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        super().save(*args, **kwargs)


class userservices_usershippingaddress(Model):
    def __init__(
        self,
        address_type: str = 'home',
        address: str = '',
        city: str = '',
        state: str = '',
        pincode: str = '',
        country: str = '',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        user_id: Optional[int] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.user_id = user_id
        self.user = user

    def validate(self) -> None:
        if not self.address:
            raise ValueError("Address must not be empty")
        if not self.user_id and not self.user:
            raise ValueError("Shipping address must belong to a user")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.user and isinstance(self.user, userservices_users):
            self.user_id = self.user.id
        super().save(*args, **kwargs)


class userservices_activitylog(Model):
    def __init__(
        self,
        activity: str = '',
        activity_type: str = '',
        activity_date: Optional[datetime.datetime] = None,
        activity_ip: Optional[str] = None,
        activity_device: Optional[str] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None,
        domain_user: Optional[userservices_users] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date or datetime.datetime.now()
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.domain_user_id_id = domain_user_id_id
        self.user_id = user_id
        self.domain_user = domain_user
        self.user = user

    def validate(self) -> None:
        if not self.activity:
            raise ValueError("Activity description required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.user and isinstance(self.user, userservices_users):
            self.user_id = self.user.id
        super().save(*args, **kwargs)


class userservices_modules(Model):
    def __init__(
        self,
        module_name: str = '',
        module_icon: Optional[str] = None,
        is_menu: bool = False,
        is_active: bool = True,
        module_url: Optional[str] = None,
        display_order: int = 0,
        module_description: Optional[str] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        parent_id_id: Optional[int] = None,
        parent: Optional['userservices_modules'] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.module_name = module_name
        self.module_icon = module_icon
        self.is_menu = is_menu
        self.is_active = is_active
        self.module_url = module_url
        self.display_order = display_order
        self.module_description = module_description
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.parent_id_id = parent_id_id
        self.parent = parent

    def validate(self) -> None:
        if not self.module_name:
            raise ValueError("Module name required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.parent and isinstance(self.parent, userservices_modules):
            self.parent_id_id = self.parent.id
        super().save(*args, **kwargs)


class userservices_userpermissions(Model):
    def __init__(
        self,
        is_view: bool = False,
        is_add: bool = False,
        is_edit: bool = False,
        is_delete: bool = False,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        module_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None,
        module: Optional[userservices_modules] = None,
        domain_user: Optional[userservices_users] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.module_id_id = module_id_id
        self.domain_user_id_id = domain_user_id_id
        self.user_id = user_id
        self.module = module
        self.domain_user = domain_user
        self.user = user

    def validate(self) -> None:
        if not self.module_id_id and not self.module:
            raise ValueError("Permission must refer to a module")
        if not self.user_id and not self.user:
            raise ValueError("Permission must be assigned to a user")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.module and isinstance(self.module, userservices_modules):
            self.module_id_id = self.module.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.user and isinstance(self.user, userservices_users):
            self.user_id = self.user.id
        super().save(*args, **kwargs)


class userservices_users_groups(Model):
    def __init__(
        self,
        users_id: Optional[int] = None,
        group_id: Optional[int] = None,
        user: Optional[userservices_users] = None,
        group: Optional['auth_group'] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.users_id = users_id
        self.group_id = group_id
        self.user = user
        self.group = group

    def validate(self) -> None:
        if not self.users_id and not self.user:
            raise ValueError("User is required")
        if not self.group_id and not self.group:
            raise ValueError("Group is required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.user and isinstance(self.user, userservices_users):
            self.users_id = self.user.id
        if self.group and isinstance(self.group, auth_group):
            self.group_id = self.group.id
        super().save(*args, **kwargs)


class userservices_users_user_permissions(Model):
    def __init__(
        self,
        users_id: Optional[int] = None,
        permission_id: Optional[int] = None,
        user: Optional[userservices_users] = None,
        permission: Optional['auth_permission'] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.users_id = users_id
        self.permission_id = permission_id
        self.user = user
        self.permission = permission

    def validate(self) -> None:
        if not self.users_id and not self.user:
            raise ValueError("User is required")
        if not self.permission_id and not self.permission:
            raise ValueError("Permission is required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.user and isinstance(self.user, userservices_users):
            self.users_id = self.user.id
        if self.permission and isinstance(self.permission, auth_permission):
            self.permission_id = self.permission.id
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------
# Django / Auth Models
# ---------------------------------------------------------------------

class django_content_type(Model):
    def __init__(self, app_label: str = '', model: str = '') -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.app_label = app_label
        self.model = model

    def save(self, *args, **kwargs) -> None:
        if not self.app_label or not self.model:
            raise ValueError("content_type needs app_label and model")
        super().save(*args, **kwargs)


class auth_permission(Model):
    def __init__(
        self,
        name: str = '',
        codename: str = '',
        content_type_id: Optional[int] = None,
        content_type: Optional[django_content_type] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.name = name
        self.codename = codename
        self.content_type_id = content_type_id
        self.content_type = content_type

    def save(self, *args, **kwargs) -> None:
        if self.content_type and isinstance(self.content_type, django_content_type):
            self.content_type_id = self.content_type.id
        super().save(*args, **kwargs)


class auth_group(Model):
    def __init__(self, name: str = '') -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.name = name


class auth_group_permissions(Model):
    def __init__(
        self,
        group_id: Optional[int] = None,
        permission_id: Optional[int] = None,
        group: Optional[auth_group] = None,
        permission: Optional[auth_permission] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.group_id = group_id
        self.permission_id = permission_id
        self.group = group
        self.permission = permission

    def save(self, *args, **kwargs) -> None:
        if self.group and isinstance(self.group, auth_group):
            self.group_id = self.group.id
        if self.permission and isinstance(self.permission, auth_permission):
            self.permission_id = self.permission.id
        super().save(*args, **kwargs)


class django_admin_log(Model):
    def __init__(
        self,
        action_time: Optional[datetime.datetime] = None,
        object_id: str = '',
        object_repr: str = '',
        action_flag: int = 0,
        change_message: str = '',
        content_type_id: Optional[int] = None,
        user_id: Optional[int] = None,
        content_type: Optional[django_content_type] = None,
        user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.action_time = action_time or datetime.datetime.now()
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type_id = content_type_id
        self.user_id = user_id
        self.content_type = content_type
        self.user = user

    def save(self, *args, **kwargs) -> None:
        if self.content_type and isinstance(self.content_type, django_content_type):
            self.content_type_id = self.content_type.id
        if self.user and isinstance(self.user, userservices_users):
            self.user_id = self.user.id
        super().save(*args, **kwargs)


class django_migrations(Model):
    def __init__(self, app: str = '', name: str = '', applied: Optional[datetime.datetime] = None) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.app = app
        self.name = name
        self.applied = applied or datetime.datetime.now()


class django_session(Model):
    def __init__(self, session_key: str = '', session_data: str = '', expire_date: Optional[datetime.datetime] = None) -> None:
        super().__init__()
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date or datetime.datetime.now()
        # Override id logic: session_key is PK
        self.id = self.session_key

    def save(self, *args, **kwargs) -> None:
        if not self.session_key:
            raise ValueError("session_key required")
        cls = type(self)
        cls._objects[self.session_key] = self
        self._is_saved = True
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.datetime.now()


# ---------------------------------------------------------------------
# Product Service Models
# ---------------------------------------------------------------------

class productservices_categories(Model):
    def __init__(
        self,
        name: str = '',
        image: Optional[str] = None,
        description: Optional[str] = None,
        display_order: int = 0,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        parent_id_id: Optional[int] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        parent: Optional['productservices_categories'] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.parent_id_id = parent_id_id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.parent = parent

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Category name required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.added_by_user and isinstance(self.added_by_user, userservices_users):
            self.added_by_user_id_id = self.added_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.parent and isinstance(self.parent, productservices_categories):
            self.parent_id_id = self.parent.id
        super().save(*args, **kwargs)


class productservices_products(Model):
    def __init__(
        self,
        name: str = '',
        image: Optional[dict] = None,
        description: Optional[str] = None,
        specifications: Optional[dict] = None,
        html_description: Optional[str] = None,
        highlights: Optional[dict] = None,
        sku: str = '',
        initial_buying_price: float = 0.0,
        initial_selling_price: float = 0.0,
        weight: float = 0.0,
        dimensions: str = '',
        uom: str = '',
        color: str = '',
        tax_percentage: float = 0.0,
        brand: str = '',
        brand_model: str = '',
        status: str = 'draft',
        seo_title: str = '',
        seo_description: Optional[str] = None,
        seo_keywords: Optional[dict] = None,
        addition_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        category_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        added_by_user: Optional[userservices_users] = None,
        category: Optional[productservices_categories] = None,
        domain_user: Optional[userservices_users] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.added_by_user_id_id = added_by_user_id_id
        self.category_id_id = category_id_id
        self.domain_user_id_id = domain_user_id_id
        self.added_by_user = added_by_user
        self.category = category
        self.domain_user = domain_user

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Product name required")
        if not self.sku:
            raise ValueError("SKU required")
        if not self.category_id_id and not self.category:
            raise ValueError("Product must belong to a category")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.added_by_user and isinstance(self.added_by_user, userservices_users):
            self.added_by_user_id_id = self.added_by_user.id
        if self.category and isinstance(self.category, productservices_categories):
            self.category_id_id = self.category.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        super().save(*args, **kwargs)


class productservices_productquestions(Model):
    def __init__(
        self,
        question: str = '',
        answer: Optional[str] = None,
        status: str = 'pending',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        answer_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        question_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        answer_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        question_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.answer_user_id_id = answer_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.question_user_id_id = question_user_id_id
        self.product_id_id = product_id_id
        self.answer_user = answer_user
        self.domain_user = domain_user
        self.question_user = question_user
        self.product = product

    def validate(self) -> None:
        if not self.question:
            raise ValueError("Question cannot be empty")
        if not self.product_id_id and not self.product:
            raise ValueError("Product reference required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.answer_user and isinstance(self.answer_user, userservices_users):
            self.answer_user_id_id = self.answer_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.question_user and isinstance(self.question_user, userservices_users):
            self.question_user_id_id = self.question_user.id
        if self.product and isinstance(self.product, productservices_products):
            self.product_id_id = self.product.id
        super().save(*args, **kwargs)


class productservices_productreviews(Model):
    def __init__(
        self,
        review_images: Optional[dict] = None,
        rating: float = 0.0,
        reviews: Optional[str] = None,
        status: str = 'pending',
        domain_user_id_id: Optional[int] = None,
        review_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        domain_user: Optional[userservices_users] = None,
        review_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.review_images = review_images or {}
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user_id_id = domain_user_id_id
        self.review_user_id_id = review_user_id_id
        self.product_id_id = product_id_id
        self.domain_user = domain_user
        self.review_user = review_user
        self.product = product

    def validate(self) -> None:
        if not self.product_id_id and not self.product:
            raise ValueError("Product reference required")
        if self.rating < 0 or self.rating > 5:
            raise ValueError("Rating must be between 0 and 5")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.review_user and isinstance(self.review_user, userservices_users):
            self.review_user_id_id = self.review_user.id
        if self.product and isinstance(self.product, productservices_products):
            self.product_id_id = self.product.id
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------
# Inventory Service Models
# ---------------------------------------------------------------------

class inventoryservices_warehouse(Model):
    def __init__(
        self,
        name: str = '',
        address: Optional[str] = None,
        city: str = '',
        state: str = '',
        country: str = '',
        pincode: str = '',
        phone: Optional[str] = None,
        email: Optional[str] = None,
        status: str = 'active',
        size: Optional[str] = None,
        capacity: Optional[str] = None,
        warehouse_type: str = 'primary',
        additional_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_manager_id: Optional[int] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        warehouse_manager: Optional[userservices_users] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.warehouse_manager_id = warehouse_manager_id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse_manager = warehouse_manager

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Warehouse name required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.added_by_user and isinstance(self.added_by_user, userservices_users):
            self.added_by_user_id_id = self.added_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.warehouse_manager and isinstance(self.warehouse_manager, userservices_users):
            self.warehouse_manager_id = self.warehouse_manager.id
        super().save(*args, **kwargs)


class inventoryservices_rackandshelvesandfloor(Model):
    def __init__(
        self,
        name: str = '',
        rack: str = '',
        shelf: str = '',
        floor: str = '',
        additional_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details = additional_details or {}
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.warehouse_id_id = warehouse_id_id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse = warehouse

    def validate(self) -> None:
        if not self.warehouse_id_id and not self.warehouse:
            raise ValueError("Must belong to a warehouse")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.added_by_user and isinstance(self.added_by_user, userservices_users):
            self.added_by_user_id_id = self.added_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.warehouse and isinstance(self.warehouse, inventoryservices_warehouse):
            self.warehouse_id_id = self.warehouse.id
        super().save(*args, **kwargs)


class inventoryservices_inventory(Model):
    def __init__(
        self,
        quantity: int = 0,
        mrp: str = '',
        batch_number: str = '',
        discount_type: str = '',
        discount_amout: float = 0.0,
        sr_no: str = '',
        mfg_date: Optional[datetime.datetime] = None,
        uom: str = '',
        ptr: str = '',
        received_date: Optional[datetime.datetime] = None,
        expiry_date: Optional[datetime.datetime] = None,
        quantity_inwarded: int = 0,
        buy_price: decimal.Decimal = decimal.Decimal('0.00'),
        sell_price: decimal.Decimal = decimal.Decimal('0.00'),
        tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        stock_status: str = 'available',
        inward_type: str = '',
        additional_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        purchase_order_id_id: Optional[int] = None,
        purchase_order_item_id_id: Optional[int] = None,
        purchase_order_item_inwarded_item_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        product: Optional[productservices_products] = None,
        purchase_order: Optional['orderservice_purchaseorder'] = None,
        purchase_order_item: Optional['orderservice_purchaseorderitems'] = None,
        purchase_order_item_inwarded_item: Optional['orderservice_purchaseorderiteminwardedlog'] = None,
        rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.product_id_id = product_id_id
        self.purchase_order_id_id = purchase_order_id_id
        self.purchase_order_item_id_id = purchase_order_item_id_id
        self.purchase_order_item_inwarded_item_id_id = purchase_order_item_inwarded_item_id_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.warehouse_id_id = warehouse_id_id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.product = product
        self.purchase_order = purchase_order
        self.purchase_order_item = purchase_order_item
        self.purchase_order_item_inwarded_item = purchase_order_item_inwarded_item
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse = warehouse

    def validate(self) -> None:
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if not self.product_id_id and not self.product:
            raise ValueError("Inventory must have a product")
        if not self.warehouse_id_id and not self.warehouse:
            raise ValueError("Inventory must belong to a warehouse")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        # Resolve FK objects to IDs
        if self.added_by_user and isinstance(self.added_by_user, userservices_users):
            self.added_by_user_id_id = self.added_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.product and isinstance(self.product, productservices_products):
            self.product_id_id = self.product.id
        if self.purchase_order and isinstance(self.purchase_order, orderservice_purchaseorder):
            self.purchase_order_id_id = self.purchase_order.id
        if self.purchase_order_item and isinstance(self.purchase_order_item, orderservice_purchaseorderitems):
            self.purchase_order_item_id_id = self.purchase_order_item.id
        if self.purchase_order_item_inwarded_item and isinstance(self.purchase_order_item_inwarded_item, orderservice_purchaseorderiteminwardedlog):
            self.purchase_order_item_inwarded_item_id_id = self.purchase_order_item_inwarded_item.id
        if self.rack_shelf_floor and isinstance(self.rack_shelf_floor, inventoryservices_rackandshelvesandfloor):
            self.rack_shelf_floor_id_id = self.rack_shelf_floor.id
        if self.warehouse and isinstance(self.warehouse, inventoryservices_warehouse):
            self.warehouse_id_id = self.warehouse.id
        super().save(*args, **kwargs)


class inventoryservices_inventorylog(Model):
    def __init__(
        self,
        quantity: int = 0,
        status: str = '',
        additional_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        inventory_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
        added_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        inventory: Optional[inventoryservices_inventory] = None,
        po: Optional['orderservice_purchaseorder'] = None,
        so: Optional['orderservice_salesorder'] = None,
        rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.quantity = quantity
        self.status = status
        self.additional_details = additional_details or {}
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.inventory_id_id = inventory_id_id
        self.po_id_id = po_id_id
        self.so_id_id = so_id_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.warehouse_id_id = warehouse_id_id
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.inventory = inventory
        self.po = po
        self.so = so
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse = warehouse

    def validate(self) -> None:
        if not self.inventory_id_id and not self.inventory:
            raise ValueError("Inventory log must reference an inventory")
        if self.quantity <= 0:
            raise ValueError("Log quantity must be positive")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.added_by_user and isinstance(self.added_by_user, userservices_users):
            self.added_by_user_id_id = self.added_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.inventory and isinstance(self.inventory, inventoryservices_inventory):
            self.inventory_id_id = self.inventory.id
        if self.po and isinstance(self.po, orderservice_purchaseorder):
            self.po_id_id = self.po.id
        if self.so and isinstance(self.so, orderservice_salesorder):
            self.so_id_id = self.so.id
        if self.rack_shelf_floor and isinstance(self.rack_shelf_floor, inventoryservices_rackandshelvesandfloor):
            self.rack_shelf_floor_id_id = self.rack_shelf_floor.id
        if self.warehouse and isinstance(self.warehouse, inventoryservices_warehouse):
            self.warehouse_id_id = self.warehouse.id
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------
# Order Service Models - Purchase
# ---------------------------------------------------------------------

class orderservice_purchaseorder(Model):
    def __init__(
        self,
        po_code: str = '',
        po_date: Optional[datetime.datetime] = None,
        expected_delivery_date: Optional[datetime.datetime] = None,
        payment_terms: str = '',
        payment_status: str = 'unpaid',
        total_amount: decimal.Decimal = decimal.Decimal('0.00'),
        paid_amount: decimal.Decimal = decimal.Decimal('0.00'),
        due_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_type: str = '',
        shipping_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_type: str = '',
        shipping_tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        additional_details: Optional[dict] = None,
        status: str = 'draft',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        approved_at: Optional[datetime.datetime] = None,
        cancelled_at: Optional[datetime.datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime.datetime] = None,
        returned_at: Optional[datetime.datetime] = None,
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
        super().__init__()
        self.id: Optional[int] = None
        self.po_code = po_code
        self.po_date = po_date or datetime.datetime.now()
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
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

    def validate(self) -> None:
        if not self.po_code:
            raise ValueError("PO code required")
        if not self.supplier_id_id and not self.supplier:
            raise ValueError("Supplier required")
        if not self.warehouse_id_id and not self.warehouse:
            raise ValueError("Warehouse required")
        if self.total_amount < 0:
            raise ValueError("Total amount cannot be negative")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        # Set FK IDs from objects
        for user_field in ['approved_by_user', 'cancelled_by_user', 'created_by_user',
                           'domain_user', 'last_updated_by_user', 'received_by_user',
                           'returned_by_user', 'supplier', 'updated_by_user']:
            obj = getattr(self, user_field, None)
            if obj and isinstance(obj, userservices_users):
                setattr(self, user_field.replace('_user', '_user_id_id'), obj.id)
        if self.warehouse and isinstance(self.warehouse, inventoryservices_warehouse):
            self.warehouse_id_id = self.warehouse.id
        super().save(*args, **kwargs)


class orderservice_purchaseorderitems(Model):
    def __init__(
        self,
        quantity_ordered: int = 0,
        quantity_received: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        buying_price: decimal.Decimal = decimal.Decimal('0.00'),
        selling_price: decimal.Decimal = decimal.Decimal('0.00'),
        discount_amount: decimal.Decimal = decimal.Decimal('0.00'),
        amount_paid: decimal.Decimal = decimal.Decimal('0.00'),
        amount_returned: decimal.Decimal = decimal.Decimal('0.00'),
        amount_cancelled: decimal.Decimal = decimal.Decimal('0.00'),
        amount_ordered: decimal.Decimal = decimal.Decimal('0.00'),
        tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_type: str = '',
        additional_details: Optional[dict] = None,
        status: str = 'pending',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        approved_at: Optional[datetime.datetime] = None,
        cancelled_at: Optional[datetime.datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime.datetime] = None,
        returned_at: Optional[datetime.datetime] = None,
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
        super().__init__()
        self.id: Optional[int] = None
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
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

    def validate(self) -> None:
        if not self.po_id_id and not self.po:
            raise ValueError("PO item must belong to a purchase order")
        if not self.product_id_id and not self.product:
            raise ValueError("PO item must have a product")
        if self.quantity_ordered <= 0:
            raise ValueError("Ordered quantity must be > 0")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        user_fields = ['approved_by_user', 'cancelled_by_user', 'created_by_user',
                       'domain_user', 'last_updated_by_user', 'received_by_user',
                       'returned_by_user', 'updated_by_user']
        for uf in user_fields:
            obj = getattr(self, uf, None)
            if obj and isinstance(obj, userservices_users):
                setattr(self, uf.replace('_user', '_user_id_id'), obj.id)
        if self.po and isinstance(self.po, orderservice_purchaseorder):
            self.po_id_id = self.po.id
        if self.product and isinstance(self.product, productservices_products):
            self.product_id_id = self.product.id
        super().save(*args, **kwargs)


class orderservice_purchaseorderlogs(Model):
    def __init__(
        self,
        comment: Optional[str] = None,
        additional_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        po: Optional[orderservice_purchaseorder] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.comment = comment
        self.additional_details = additional_details or {}
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.po_id_id = po_id_id
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.po = po

    def save(self, *args, **kwargs) -> None:
        if self.created_by_user and isinstance(self.created_by_user, userservices_users):
            self.created_by_user_id_id = self.created_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.po and isinstance(self.po, orderservice_purchaseorder):
            self.po_id_id = self.po.id
        super().save(*args, **kwargs)


class orderservice_purchaseorderinwardedlog(Model):
    def __init__(
        self,
        invoice_path: Optional[str] = None,
        invoice_number: str = '',
        notes: Optional[str] = None,
        inwarded_at: Optional[datetime.datetime] = None,
        additional_details: Optional[dict] = None,
        status: str = 'draft',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        domain_user_id_id: Optional[int] = None,
        inwarded_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        domain_user: Optional[userservices_users] = None,
        inwarded_by_user: Optional[userservices_users] = None,
        po: Optional[orderservice_purchaseorder] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at or datetime.datetime.now()
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.domain_user_id_id = domain_user_id_id
        self.inwarded_by_user_id_id = inwarded_by_user_id_id
        self.po_id_id = po_id_id
        self.domain_user = domain_user
        self.inwarded_by_user = inwarded_by_user
        self.po = po

    def validate(self) -> None:
        if not self.po_id_id and not self.po:
            raise ValueError("Inwarded log must reference a PO")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.inwarded_by_user and isinstance(self.inwarded_by_user, userservices_users):
            self.inwarded_by_user_id_id = self.inwarded_by_user.id
        if self.po and isinstance(self.po, orderservice_purchaseorder):
            self.po_id_id = self.po.id
        super().save(*args, **kwargs)


class orderservice_purchaseorderiteminwardedlog(Model):
    def __init__(
        self,
        inwarded_quantity: int = 0,
        price: decimal.Decimal = decimal.Decimal('0.00'),
        tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        discount_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_type: str = '',
        shipping_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        additional_details: Optional[dict] = None,
        status: str = 'pending',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        domain_user_id_id: Optional[int] = None,
        po_item_id_id: Optional[int] = None,
        domain_user: Optional[userservices_users] = None,
        po_item: Optional[orderservice_purchaseorderitems] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.inwarded_quantity = inwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.domain_user_id_id = domain_user_id_id
        self.po_item_id_id = po_item_id_id
        self.domain_user = domain_user
        self.po_item = po_item

    def validate(self) -> None:
        if not self.po_item_id_id and not self.po_item:
            raise ValueError("Must reference a PO item")
        if self.inwarded_quantity <= 0:
            raise ValueError("Inwarded quantity must be positive")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.po_item and isinstance(self.po_item, orderservice_purchaseorderitems):
            self.po_item_id_id = self.po_item.id
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------
# Order Service Models - Sales
# ---------------------------------------------------------------------

class orderservice_salesorder(Model):
    def __init__(
        self,
        so_code: str = '',
        so_date: Optional[datetime.datetime] = None,
        expected_delivery_date: Optional[datetime.datetime] = None,
        payment_terms: str = '',
        payment_status: str = 'unpaid',
        total_amount: decimal.Decimal = decimal.Decimal('0.00'),
        paid_amount: decimal.Decimal = decimal.Decimal('0.00'),
        due_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_type: str = '',
        shipping_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_type: str = '',
        shipping_tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        additional_details: Optional[dict] = None,
        status: str = 'draft',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        approved_at: Optional[datetime.datetime] = None,
        cancelled_at: Optional[datetime.datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime.datetime] = None,
        returned_at: Optional[datetime.datetime] = None,
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
        super().__init__()
        self.id: Optional[int] = None
        self.so_code = so_code
        self.so_date = so_date or datetime.datetime.now()
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at
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

    def validate(self) -> None:
        if not self.so_code:
            raise ValueError("SO code required")
        if not self.customer_id_id and not self.customer:
            raise ValueError("Customer required")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        user_fields = ['approved_by_user', 'cancelled_by_user', 'created_by_user',
                       'domain_user', 'last_updated_by_user', 'received_by_user',
                       'returned_by_user', 'customer', 'updated_by_user']
        for uf in user_fields:
            obj = getattr(self, uf, None)
            if obj and isinstance(obj, userservices_users):
                setattr(self, uf.replace('_user', '_user_id_id'), obj.id)
        if self.po and isinstance(self.po, orderservice_purchaseorder):
            self.po_id_id = self.po.id
        if self.product and isinstance(self.product, productservices_products):
            self.product_id_id = self.product.id
        super().save(*args, **kwargs)


class orderservice_salesorderorderitems(Model):
    def __init__(
        self,
        quantity_ordered: int = 0,
        quantity_delivered: int = 0,
        quantity_shipped: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        purchase_price: decimal.Decimal = decimal.Decimal('0.00'),
        discount_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_type: str = '',
        amount_paid: decimal.Decimal = decimal.Decimal('0.00'),
        amount_returned: decimal.Decimal = decimal.Decimal('0.00'),
        amount_cancelled: decimal.Decimal = decimal.Decimal('0.00'),
        amount_ordered: decimal.Decimal = decimal.Decimal('0.00'),
        tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_type: str = '',
        shipping_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_cancelled_tax_amount: decimal.Decimal = decimal.Decimal('0.00'),
        additional_details: Optional[dict] = None,
        status: str = 'pending',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        approved_at: Optional[datetime.datetime] = None,
        cancelled_at: Optional[datetime.datetime] = None,
        cancelled_reason: Optional[str] = None,
        shipped_at: Optional[datetime.datetime] = None,
        returned_at: Optional[datetime.datetime] = None,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        shipped_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None,
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
        super().__init__()
        self.id: Optional[int] = None
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
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.shipped_at = shipped_at
        self.returned_at = returned_at
        self.approved_by_user_id_id = approved_by_user_id_id
        self.cancelled_by_user_id_id = cancelled_by_user_id_id
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.product_id_id = product_id_id
        self.returned_by_user_id_id = returned_by_user_id_id
        self.shipped_by_user_id_id = shipped_by_user_id_id
        self.so_id_id = so_id_id
        self.updated_by_user_id_id = updated_by_user_id_id
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.product = product
        self.returned_by_user = returned_by_user
        self.shipped_by_user = shipped_by_user
        self.so = so
        self.updated_by_user = updated_by_user

    def validate(self) -> None:
        if not self.so_id_id and not self.so:
            raise ValueError("SO item must belong to a sales order")
        if not self.product_id_id and not self.product:
            raise ValueError("SO item must have a product")
        if self.quantity_ordered <= 0:
            raise ValueError("Ordered quantity must be positive")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        user_fields = ['approved_by_user', 'cancelled_by_user', 'created_by_user',
                       'domain_user', 'returned_by_user', 'shipped_by_user', 'updated_by_user']
        for uf in user_fields:
            obj = getattr(self, uf, None)
            if obj and isinstance(obj, userservices_users):
                setattr(self, uf.replace('_user', '_user_id_id'), obj.id)
        if self.product and isinstance(self.product, productservices_products):
            self.product_id_id = self.product.id
        if self.so and isinstance(self.so, orderservice_salesorder):
            self.so_id_id = self.so.id
        super().save(*args, **kwargs)


class orderservice_salesorderlogs(Model):
    def __init__(
        self,
        comment: Optional[str] = None,
        additional_details: Optional[dict] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        created_by_user: Optional[userservices_users] = None,
        domain_user: Optional[userservices_users] = None,
        so: Optional[orderservice_salesorder] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.comment = comment
        self.additional_details = additional_details or {}
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.so_id_id = so_id_id
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.so = so

    def save(self, *args, **kwargs) -> None:
        if self.created_by_user and isinstance(self.created_by_user, userservices_users):
            self.created_by_user_id_id = self.created_by_user.id
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.so and isinstance(self.so, orderservice_salesorder):
            self.so_id_id = self.so.id
        super().save(*args, **kwargs)


class orderservice_salesorderoutwardedlog(Model):
    def __init__(
        self,
        invoice_path: Optional[str] = None,
        invoice_number: str = '',
        notes: Optional[str] = None,
        outwared_at: Optional[datetime.datetime] = None,
        additional_details: Optional[dict] = None,
        status: str = 'draft',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        domain_user_id_id: Optional[int] = None,
        outwarded_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        domain_user: Optional[userservices_users] = None,
        outwarded_by_user: Optional[userservices_users] = None,
        so: Optional[orderservice_salesorder] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at or datetime.datetime.now()
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.domain_user_id_id = domain_user_id_id
        self.outwarded_by_user_id_id = outwarded_by_user_id_id
        self.so_id_id = so_id_id
        self.domain_user = domain_user
        self.outwarded_by_user = outwarded_by_user
        self.so = so

    def validate(self) -> None:
        if not self.so_id_id and not self.so:
            raise ValueError("Outwarded log must reference a SO")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.outwarded_by_user and isinstance(self.outwarded_by_user, userservices_users):
            self.outwarded_by_user_id_id = self.outwarded_by_user.id
        if self.so and isinstance(self.so, orderservice_salesorder):
            self.so_id_id = self.so.id
        super().save(*args, **kwargs)


class orderservice_salesorderitemoutwardedlog(Model):
    def __init__(
        self,
        outwarded_quantity: int = 0,
        price: decimal.Decimal = decimal.Decimal('0.00'),
        tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        discount_amount: decimal.Decimal = decimal.Decimal('0.00'),
        discount_type: str = '',
        shipping_amount: decimal.Decimal = decimal.Decimal('0.00'),
        shipping_tax_percentage: decimal.Decimal = decimal.Decimal('0.00'),
        additional_details: Optional[dict] = None,
        status: str = 'pending',
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        domain_user_id_id: Optional[int] = None,
        so_item_id_id: Optional[int] = None,
        domain_user: Optional[userservices_users] = None,
        so_item: Optional[orderservice_salesorderorderitems] = None,
    ) -> None:
        super().__init__()
        self.id: Optional[int] = None
        self.outwarded_quantity = outwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = created_at or datetime.datetime.now()
        self.updated_at = updated_at or datetime.datetime.now()
        self.domain_user_id_id = domain_user_id_id
        self.so_item_id_id = so_item_id_id
        self.domain_user = domain_user
        self.so_item = so_item

    def validate(self) -> None:
        if not self.so_item_id_id and not self.so_item:
            raise ValueError("Must reference SO item")
        if self.outwarded_quantity <= 0:
            raise ValueError("Outwarded quantity must be positive")

    def save(self, *args, **kwargs) -> None:
        self.validate()
        if self.domain_user and isinstance(self.domain_user, userservices_users):
            self.domain_user_id_id = self.domain_user.id
        if self.so_item and isinstance(self.so_item, orderservice_salesorderorderitems):
            self.so_item_id_id = self.so_item.id
        super().save(*args, **kwargs)