from datetime import datetime, date
from typing import Optional, Dict, Any, List, Union

class ProductServicesCategories:
    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        description: str,
        display_order: int,
        created_at: datetime,
        updated_at: datetime,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        parent_id_id: Optional[int] = None
    ):
        self.id = id
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.parent_id_id = parent_id_id

        self._added_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._parent: Optional['ProductServicesCategories'] = None

    @property
    def added_by_user(self) -> Optional['UserservicesUsers']:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._added_by_user = value
        self.added_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def parent(self) -> Optional['ProductServicesCategories']:
        return self._parent

    @parent.setter
    def parent(self, value: Optional['ProductServicesCategories']) -> None:
        self._parent = value
        self.parent_id_id = value.id if value else None


class ProductServicesProducts:
    def __init__(
        self,
        id: int,
        name: str,
        image: Union[Dict[str, Any], List[Any]],
        description: str,
        specifications: Union[Dict[str, Any], List[Any]],
        html_description: str,
        highlights: Union[Dict[str, Any], List[Any]],
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
        seo_keywords: Union[Dict[str, Any], List[Any]],
        addition_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user_id_id: Optional[int] = None,
        category_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None
    ):
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
        self.added_by_user_id_id = added_by_user_id_id
        self.category_id_id = category_id_id
        self.domain_user_id_id = domain_user_id_id

        self._added_by_user: Optional['UserservicesUsers'] = None
        self._category: Optional['ProductServicesCategories'] = None
        self._domain_user: Optional['UserservicesUsers'] = None

    @property
    def added_by_user(self) -> Optional['UserservicesUsers']:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._added_by_user = value
        self.added_by_user_id_id = value.id if value else None

    @property
    def category(self) -> Optional['ProductServicesCategories']:
        return self._category

    @category.setter
    def category(self, value: Optional['ProductServicesCategories']) -> None:
        self._category = value
        self.category_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None


class ProductServicesProductQuestions:
    def __init__(
        self,
        id: int,
        question: str,
        answer: str,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        answer_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        question_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None
    ):
        self.id = id
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.answer_user_id_id = answer_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.question_user_id_id = question_user_id_id
        self.product_id_id = product_id_id

        self._answer_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._question_user: Optional['UserservicesUsers'] = None
        self._product: Optional['ProductServicesProducts'] = None

    @property
    def answer_user(self) -> Optional['UserservicesUsers']:
        return self._answer_user

    @answer_user.setter
    def answer_user(self, value: Optional['UserservicesUsers']) -> None:
        self._answer_user = value
        self.answer_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def question_user(self) -> Optional['UserservicesUsers']:
        return self._question_user

    @question_user.setter
    def question_user(self, value: Optional['UserservicesUsers']) -> None:
        self._question_user = value
        self.question_user_id_id = value.id if value else None

    @property
    def product(self) -> Optional['ProductServicesProducts']:
        return self._product

    @product.setter
    def product(self, value: Optional['ProductServicesProducts']) -> None:
        self._product = value
        self.product_id_id = value.id if value else None


class ProductServicesProductReviews:
    def __init__(
        self,
        id: int,
        review_images: Union[Dict[str, Any], List[Any]],
        rating: float,
        reviews: str,
        status: str,
        domain_user_id_id: Optional[int] = None,
        review_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None
    ):
        self.id = id
        self.review_images = review_images
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user_id_id = domain_user_id_id
        self.review_user_id_id = review_user_id_id
        self.product_id_id = product_id_id

        self._domain_user: Optional['UserservicesUsers'] = None
        self._review_user: Optional['UserservicesUsers'] = None
        self._product: Optional['ProductServicesProducts'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def review_user(self) -> Optional['UserservicesUsers']:
        return self._review_user

    @review_user.setter
    def review_user(self, value: Optional['UserservicesUsers']) -> None:
        self._review_user = value
        self.review_user_id_id = value.id if value else None

    @property
    def product(self) -> Optional['ProductServicesProducts']:
        return self._product

    @product.setter
    def product(self, value: Optional['ProductServicesProducts']) -> None:
        self._product = value
        self.product_id_id = value.id if value else None


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
        profile_pic: str,
        account_status: str,
        role: str,
        dob: date,
        username: str,
        password: str,
        social_media_links: Union[Dict[str, Any], List[Any]],
        addition_details: Union[Dict[str, Any], List[Any]],
        language: str,
        departMent: str,
        designation: str,
        time_zone: str,
        last_login: datetime,
        last_device: str,
        last_ip: str,
        currency: str,
        domain_name: str,
        plan_type: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user_id_id: Optional[int] = None
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
        self.social_media_links = social_media_links
        self.addition_details = addition_details
        self.language = language
        self.departMent = departMent
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

        self._domain_user: Optional['UserservicesUsers'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None


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
        user_id: Optional[int] = None
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

        self._user: Optional['UserservicesUsers'] = None

    @property
    def user(self) -> Optional['UserservicesUsers']:
        return self._user

    @user.setter
    def user(self, value: Optional['UserservicesUsers']) -> None:
        self._user = value
        self.user_id = value.id if value else None


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
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None
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
        self.user_id = user_id

        self._domain_user: Optional['UserservicesUsers'] = None
        self._user: Optional['UserservicesUsers'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def user(self) -> Optional['UserservicesUsers']:
        return self._user

    @user.setter
    def user(self, value: Optional['UserservicesUsers']) -> None:
        self._user = value
        self.user_id = value.id if value else None


class UserservicesModules:
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
        created_at: datetime,
        updated_at: datetime,
        parent_id_id: Optional[int] = None
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

        self._parent: Optional['UserservicesModules'] = None

    @property
    def parent(self) -> Optional['UserservicesModules']:
        return self._parent

    @parent.setter
    def parent(self, value: Optional['UserservicesModules']) -> None:
        self._parent = value
        self.parent_id_id = value.id if value else None


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
        module_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        self.id = id
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = created_at
        self.updated_at = updated_at
        self.module_id_id = module_id_id
        self.domain_user_id_id = domain_user_id_id
        self.user_id = user_id

        self._module: Optional['UserservicesModules'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._user: Optional['UserservicesUsers'] = None

    @property
    def module(self) -> Optional['UserservicesModules']:
        return self._module

    @module.setter
    def module(self, value: Optional['UserservicesModules']) -> None:
        self._module = value
        self.module_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def user(self) -> Optional['UserservicesUsers']:
        return self._user

    @user.setter
    def user(self, value: Optional['UserservicesUsers']) -> None:
        self._user = value
        self.user_id = value.id if value else None


class AuthGroup:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class UserservicesUsersGroups:
    def __init__(
        self,
        id: int,
        users_id: Optional[int] = None,
        group_id: Optional[int] = None
    ):
        self.id = id
        self.users_id = users_id
        self.group_id = group_id

        self._user: Optional['UserservicesUsers'] = None
        self._group: Optional['AuthGroup'] = None

    @property
    def user(self) -> Optional['UserservicesUsers']:
        return self._user

    @user.setter
    def user(self, value: Optional['UserservicesUsers']) -> None:
        self._user = value
        self.users_id = value.id if value else None

    @property
    def group(self) -> Optional['AuthGroup']:
        return self._group

    @group.setter
    def group(self, value: Optional['AuthGroup']) -> None:
        self._group = value
        self.group_id = value.id if value else None


class DjangoContentType:
    def __init__(self, id: int, app_label: str, model: str):
        self.id = id
        self.app_label = app_label
        self.model = model


class AuthPermission:
    def __init__(
        self,
        id: int,
        name: str,
        codename: str,
        content_type_id: Optional[int] = None
    ):
        self.id = id
        self.name = name
        self.codename = codename
        self.content_type_id = content_type_id

        self._content_type: Optional['DjangoContentType'] = None

    @property
    def content_type(self) -> Optional['DjangoContentType']:
        return self._content_type

    @content_type.setter
    def content_type(self, value: Optional['DjangoContentType']) -> None:
        self._content_type = value
        self.content_type_id = value.id if value else None


class UserservicesUsersUserPermissions:
    def __init__(
        self,
        id: int,
        users_id: Optional[int] = None,
        permission_id: Optional[int] = None
    ):
        self.id = id
        self.users_id = users_id
        self.permission_id = permission_id

        self._user: Optional['UserservicesUsers'] = None
        self._permission: Optional['AuthPermission'] = None

    @property
    def user(self) -> Optional['UserservicesUsers']:
        return self._user

    @user.setter
    def user(self, value: Optional['UserservicesUsers']) -> None:
        self._user = value
        self.users_id = value.id if value else None

    @property
    def permission(self) -> Optional['AuthPermission']:
        return self._permission

    @permission.setter
    def permission(self, value: Optional['AuthPermission']) -> None:
        self._permission = value
        self.permission_id = value.id if value else None


class AuthGroupPermissions:
    def __init__(
        self,
        id: int,
        group_id: Optional[int] = None,
        permission_id: Optional[int] = None
    ):
        self.id = id
        self.group_id = group_id
        self.permission_id = permission_id

        self._group: Optional['AuthGroup'] = None
        self._permission: Optional['AuthPermission'] = None

    @property
    def group(self) -> Optional['AuthGroup']:
        return self._group

    @group.setter
    def group(self, value: Optional['AuthGroup']) -> None:
        self._group = value
        self.group_id = value.id if value else None

    @property
    def permission(self) -> Optional['AuthPermission']:
        return self._permission

    @permission.setter
    def permission(self, value: Optional['AuthPermission']) -> None:
        self._permission = value
        self.permission_id = value.id if value else None


class DjangoAdminLog:
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str,
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type_id: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        self.id = id
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type_id = content_type_id
        self.user_id = user_id

        self._content_type: Optional['DjangoContentType'] = None
        self._user: Optional['UserservicesUsers'] = None

    @property
    def content_type(self) -> Optional['DjangoContentType']:
        return self._content_type

    @content_type.setter
    def content_type(self, value: Optional['DjangoContentType']) -> None:
        self._content_type = value
        self.content_type_id = value.id if value else None

    @property
    def user(self) -> Optional['UserservicesUsers']:
        return self._user

    @user.setter
    def user(self, value: Optional['UserservicesUsers']) -> None:
        self._user = value
        self.user_id = value.id if value else None


class DjangoMigrations:
    def __init__(self, id: int, app: str, name: str, applied: datetime):
        self.id = id
        self.app = app
        self.name = name
        self.applied = applied


class DjangoSession:
    def __init__(self, session_key: str, session_data: str, expire_date: datetime):
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date


class InventoryServicesWarehouse:
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
        additional_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_manager_id: Optional[int] = None
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
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.warehouse_manager_id = warehouse_manager_id

        self._added_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._warehouse_manager: Optional['UserservicesUsers'] = None

    @property
    def added_by_user(self) -> Optional['UserservicesUsers']:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._added_by_user = value
        self.added_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def warehouse_manager(self) -> Optional['UserservicesUsers']:
        return self._warehouse_manager

    @warehouse_manager.setter
    def warehouse_manager(self, value: Optional['UserservicesUsers']) -> None:
        self._warehouse_manager = value
        self.warehouse_manager_id = value.id if value else None


class InventoryServicesRackAndShelvesAndFloor:
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None
    ):
        self.id = id
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.warehouse_id_id = warehouse_id_id

        self._added_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._warehouse: Optional['InventoryServicesWarehouse'] = None

    @property
    def added_by_user(self) -> Optional['UserservicesUsers']:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._added_by_user = value
        self.added_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def warehouse(self) -> Optional['InventoryServicesWarehouse']:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional['InventoryServicesWarehouse']) -> None:
        self._warehouse = value
        self.warehouse_id_id = value.id if value else None


class OrderServicePurchaseOrder:
    def __init__(
        self,
        id: int,
        po_code: str,
        po_date: datetime,
        expected_delivery_date: datetime,
        payment_terms: str,
        payment_status: str,
        total_amount: float,
        paid_amount: float,
        due_amount: float,
        discount_amount: float,
        discount_type: str,
        shipping_amount: float,
        shipping_type: str,
        shipping_tax_percentage: float,
        shipping_tax_amount: float,
        shipping_cancelled_amount: float,
        shipping_cancelled_tax_amount: float,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: datetime,
        cancelled_at: datetime,
        cancelled_reason: str,
        received_at: datetime,
        returned_at: datetime,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        received_by_user_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        supplier_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
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

        self._approved_by_user: Optional['UserservicesUsers'] = None
        self._cancelled_by_user: Optional['UserservicesUsers'] = None
        self._created_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._last_updated_by_user: Optional['UserservicesUsers'] = None
        self._received_by_user: Optional['UserservicesUsers'] = None
        self._returned_by_user: Optional['UserservicesUsers'] = None
        self._supplier: Optional['UserservicesUsers'] = None
        self._updated_by_user: Optional['UserservicesUsers'] = None
        self._warehouse: Optional['InventoryServicesWarehouse'] = None

    @property
    def approved_by_user(self) -> Optional['UserservicesUsers']:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._approved_by_user = value
        self.approved_by_user_id_id = value.id if value else None

    @property
    def cancelled_by_user(self) -> Optional['UserservicesUsers']:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._cancelled_by_user = value
        self.cancelled_by_user_id_id = value.id if value else None

    @property
    def created_by_user(self) -> Optional['UserservicesUsers']:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._created_by_user = value
        self.created_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def last_updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._last_updated_by_user

    @last_updated_by_user.setter
    def last_updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._last_updated_by_user = value
        self.last_updated_by_user_id_id = value.id if value else None

    @property
    def received_by_user(self) -> Optional['UserservicesUsers']:
        return self._received_by_user

    @received_by_user.setter
    def received_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._received_by_user = value
        self.received_by_user_id_id = value.id if value else None

    @property
    def returned_by_user(self) -> Optional['UserservicesUsers']:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._returned_by_user = value
        self.returned_by_user_id_id = value.id if value else None

    @property
    def supplier(self) -> Optional['UserservicesUsers']:
        return self._supplier

    @supplier.setter
    def supplier(self, value: Optional['UserservicesUsers']) -> None:
        self._supplier = value
        self.supplier_id_id = value.id if value else None

    @property
    def updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._updated_by_user = value
        self.updated_by_user_id_id = value.id if value else None

    @property
    def warehouse(self) -> Optional['InventoryServicesWarehouse']:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional['InventoryServicesWarehouse']) -> None:
        self._warehouse = value
        self.warehouse_id_id = value.id if value else None


class OrderServicePurchaseOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: int,
        quantity_received: int,
        quantity_cancelled: int,
        quantity_returned: int,
        buying_price: float,
        selling_price: float,
        discount_amount: float,
        amount_paid: float,
        amount_returned: float,
        amount_cancelled: float,
        amount_ordered: float,
        tax_percentage: float,
        tax_amount: float,
        shipping_tax_percentage: float,
        shipping_amount: float,
        shipping_tax_amount: float,
        shipping_cancelled_amount: float,
        shipping_cancelled_tax_amount: float,
        discount_type: str,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: datetime,
        cancelled_at: datetime,
        cancelled_reason: str,
        received_at: datetime,
        returned_at: datetime,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        last_updated_by_user_id_id: Optional[int] = None,
        received_by_user_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
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

        self._approved_by_user: Optional['UserservicesUsers'] = None
        self._cancelled_by_user: Optional['UserservicesUsers'] = None
        self._created_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._last_updated_by_user: Optional['UserservicesUsers'] = None
        self._received_by_user: Optional['UserservicesUsers'] = None
        self._returned_by_user: Optional['UserservicesUsers'] = None
        self._po: Optional['OrderServicePurchaseOrder'] = None
        self._product: Optional['ProductServicesProducts'] = None
        self._updated_by_user: Optional['UserservicesUsers'] = None

    @property
    def approved_by_user(self) -> Optional['UserservicesUsers']:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._approved_by_user = value
        self.approved_by_user_id_id = value.id if value else None

    @property
    def cancelled_by_user(self) -> Optional['UserservicesUsers']:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._cancelled_by_user = value
        self.cancelled_by_user_id_id = value.id if value else None

    @property
    def created_by_user(self) -> Optional['UserservicesUsers']:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._created_by_user = value
        self.created_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def last_updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._last_updated_by_user

    @last_updated_by_user.setter
    def last_updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._last_updated_by_user = value
        self.last_updated_by_user_id_id = value.id if value else None

    @property
    def received_by_user(self) -> Optional['UserservicesUsers']:
        return self._received_by_user

    @received_by_user.setter
    def received_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._received_by_user = value
        self.received_by_user_id_id = value.id if value else None

    @property
    def returned_by_user(self) -> Optional['UserservicesUsers']:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._returned_by_user = value
        self.returned_by_user_id_id = value.id if value else None

    @property
    def po(self) -> Optional['OrderServicePurchaseOrder']:
        return self._po

    @po.setter
    def po(self, value: Optional['OrderServicePurchaseOrder']) -> None:
        self._po = value
        self.po_id_id = value.id if value else None

    @property
    def product(self) -> Optional['ProductServicesProducts']:
        return self._product

    @product.setter
    def product(self, value: Optional['ProductServicesProducts']) -> None:
        self._product = value
        self.product_id_id = value.id if value else None

    @property
    def updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._updated_by_user = value
        self.updated_by_user_id_id = value.id if value else None


class OrderServicePurchaseOrderLogs:
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None
    ):
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.po_id_id = po_id_id

        self._created_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._po: Optional['OrderServicePurchaseOrder'] = None

    @property
    def created_by_user(self) -> Optional['UserservicesUsers']:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._created_by_user = value
        self.created_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def po(self) -> Optional['OrderServicePurchaseOrder']:
        return self._po

    @po.setter
    def po(self, value: Optional['OrderServicePurchaseOrder']) -> None:
        self._po = value
        self.po_id_id = value.id if value else None


class OrderServicePurchaseOrderInwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: datetime,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user_id_id: Optional[int] = None,
        inwarded_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None
    ):
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.inwarded_by_user_id_id = inwarded_by_user_id_id
        self.po_id_id = po_id_id

        self._domain_user: Optional['UserservicesUsers'] = None
        self._inwarded_by_user: Optional['UserservicesUsers'] = None
        self._po: Optional['OrderServicePurchaseOrder'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def inwarded_by_user(self) -> Optional['UserservicesUsers']:
        return self._inwarded_by_user

    @inwarded_by_user.setter
    def inwarded_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._inwarded_by_user = value
        self.inwarded_by_user_id_id = value.id if value else None

    @property
    def po(self) -> Optional['OrderServicePurchaseOrder']:
        return self._po

    @po.setter
    def po(self, value: Optional['OrderServicePurchaseOrder']) -> None:
        self._po = value
        self.po_id_id = value.id if value else None


class OrderServicePurchaseOrderItemInwardedLog:
    def __init__(
        self,
        id: int,
        inwarded_quantity: int,
        price: float,
        tax_percentage: float,
        discount_amount: float,
        discount_type: str,
        shipping_amount: float,
        shipping_tax_percentage: float,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user_id_id: Optional[int] = None,
        po_item_id_id: Optional[int] = None
    ):
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
        self.domain_user_id_id = domain_user_id_id
        self.po_item_id_id = po_item_id_id

        self._domain_user: Optional['UserservicesUsers'] = None
        self._po_item: Optional['OrderServicePurchaseOrderItems'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def po_item(self) -> Optional['OrderServicePurchaseOrderItems']:
        return self._po_item

    @po_item.setter
    def po_item(self, value: Optional['OrderServicePurchaseOrderItems']) -> None:
        self._po_item = value
        self.po_item_id_id = value.id if value else None


class InventoryServicesInventory:
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
        buy_price: float,
        sell_price: float,
        tax_percentage: float,
        stock_status: str,
        inward_type: str,
        additional_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        purchase_order_id_id: Optional[int] = None,
        purchase_order_item_id_id: Optional[int] = None,
        purchase_order_item_inwarded_item_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None
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
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.product_id_id = product_id_id
        self.purchase_order_id_id = purchase_order_id_id
        self.purchase_order_item_id_id = purchase_order_item_id_id
        self.purchase_order_item_inwarded_item_id_id = purchase_order_item_inwarded_item_id_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.warehouse_id_id = warehouse_id_id

        self._added_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._product: Optional['ProductServicesProducts'] = None
        self._purchase_order: Optional['OrderServicePurchaseOrder'] = None
        self._purchase_order_item: Optional['OrderServicePurchaseOrderItems'] = None
        self._purchase_order_item_inwarded_item: Optional['OrderServicePurchaseOrderItemInwardedLog'] = None
        self._rack_shelf_floor: Optional['InventoryServicesRackAndShelvesAndFloor'] = None
        self._warehouse: Optional['InventoryServicesWarehouse'] = None

    @property
    def added_by_user(self) -> Optional['UserservicesUsers']:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._added_by_user = value
        self.added_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def product(self) -> Optional['ProductServicesProducts']:
        return self._product

    @product.setter
    def product(self, value: Optional['ProductServicesProducts']) -> None:
        self._product = value
        self.product_id_id = value.id if value else None

    @property
    def purchase_order(self) -> Optional['OrderServicePurchaseOrder']:
        return self._purchase_order

    @purchase_order.setter
    def purchase_order(self, value: Optional['OrderServicePurchaseOrder']) -> None:
        self._purchase_order = value
        self.purchase_order_id_id = value.id if value else None

    @property
    def purchase_order_item(self) -> Optional['OrderServicePurchaseOrderItems']:
        return self._purchase_order_item

    @purchase_order_item.setter
    def purchase_order_item(self, value: Optional['OrderServicePurchaseOrderItems']) -> None:
        self._purchase_order_item = value
        self.purchase_order_item_id_id = value.id if value else None

    @property
    def purchase_order_item_inwarded_item(self) -> Optional['OrderServicePurchaseOrderItemInwardedLog']:
        return self._purchase_order_item_inwarded_item

    @purchase_order_item_inwarded_item.setter
    def purchase_order_item_inwarded_item(self, value: Optional['OrderServicePurchaseOrderItemInwardedLog']) -> None:
        self._purchase_order_item_inwarded_item = value
        self.purchase_order_item_inwarded_item_id_id = value.id if value else None

    @property
    def rack_shelf_floor(self) -> Optional['InventoryServicesRackAndShelvesAndFloor']:
        return self._rack_shelf_floor

    @rack_shelf_floor.setter
    def rack_shelf_floor(self, value: Optional['InventoryServicesRackAndShelvesAndFloor']) -> None:
        self._rack_shelf_floor = value
        self.rack_shelf_floor_id_id = value.id if value else None

    @property
    def warehouse(self) -> Optional['InventoryServicesWarehouse']:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional['InventoryServicesWarehouse']) -> None:
        self._warehouse = value
        self.warehouse_id_id = value.id if value else None


class OrderServiceSalesOrder:
    def __init__(
        self,
        id: int,
        so_code: str,
        so_date: datetime,
        expected_delivery_date: datetime,
        payment_terms: str,
        payment_status: str,
        total_amount: float,
        paid_amount: float,
        due_amount: float,
        discount_amount: float,
        discount_type: str,
        shipping_amount: float,
        shipping_type: str,
        shipping_tax_percentage: float,
        shipping_tax_amount: float,
        shipping_cancelled_amount: float,
        shipping_cancelled_tax_amount: float,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: datetime,
        cancelled_at: datetime,
        cancelled_reason: str,
        received_at: datetime,
        returned_at: datetime,
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
        updated_by_user_id_id: Optional[int] = None
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
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

        self._approved_by_user: Optional['UserservicesUsers'] = None
        self._cancelled_by_user: Optional['UserservicesUsers'] = None
        self._created_by_user: Optional['UserservicesUsers'] = None
        self._customer: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._last_updated_by_user: Optional['UserservicesUsers'] = None
        self._received_by_user: Optional['UserservicesUsers'] = None
        self._returned_by_user: Optional['UserservicesUsers'] = None
        self._po: Optional['OrderServicePurchaseOrder'] = None
        self._product: Optional['ProductServicesProducts'] = None
        self._updated_by_user: Optional['UserservicesUsers'] = None

    @property
    def approved_by_user(self) -> Optional['UserservicesUsers']:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._approved_by_user = value
        self.approved_by_user_id_id = value.id if value else None

    @property
    def cancelled_by_user(self) -> Optional['UserservicesUsers']:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._cancelled_by_user = value
        self.cancelled_by_user_id_id = value.id if value else None

    @property
    def created_by_user(self) -> Optional['UserservicesUsers']:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._created_by_user = value
        self.created_by_user_id_id = value.id if value else None

    @property
    def customer(self) -> Optional['UserservicesUsers']:
        return self._customer

    @customer.setter
    def customer(self, value: Optional['UserservicesUsers']) -> None:
        self._customer = value
        self.customer_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def last_updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._last_updated_by_user

    @last_updated_by_user.setter
    def last_updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._last_updated_by_user = value
        self.last_updated_by_user_id_id = value.id if value else None

    @property
    def received_by_user(self) -> Optional['UserservicesUsers']:
        return self._received_by_user

    @received_by_user.setter
    def received_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._received_by_user = value
        self.received_by_user_id_id = value.id if value else None

    @property
    def returned_by_user(self) -> Optional['UserservicesUsers']:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._returned_by_user = value
        self.returned_by_user_id_id = value.id if value else None

    @property
    def po(self) -> Optional['OrderServicePurchaseOrder']:
        return self._po

    @po.setter
    def po(self, value: Optional['OrderServicePurchaseOrder']) -> None:
        self._po = value
        self.po_id_id = value.id if value else None

    @property
    def product(self) -> Optional['ProductServicesProducts']:
        return self._product

    @product.setter
    def product(self, value: Optional['ProductServicesProducts']) -> None:
        self._product = value
        self.product_id_id = value.id if value else None

    @property
    def updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._updated_by_user = value
        self.updated_by_user_id_id = value.id if value else None


class InventoryServicesInventoryLog:
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        inventory_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None
    ):
        self.id = id
        self.quantity = quantity
        self.status = status
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user_id_id = added_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.inventory_id_id = inventory_id_id
        self.po_id_id = po_id_id
        self.so_id_id = so_id_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id_id
        self.warehouse_id_id = warehouse_id_id

        self._added_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._inventory: Optional['InventoryServicesInventory'] = None
        self._po: Optional['OrderServicePurchaseOrder'] = None
        self._so: Optional['OrderServiceSalesOrder'] = None
        self._rack_shelf_floor: Optional['InventoryServicesRackAndShelvesAndFloor'] = None
        self._warehouse: Optional['InventoryServicesWarehouse'] = None

    @property
    def added_by_user(self) -> Optional['UserservicesUsers']:
        return self._added_by_user

    @added_by_user.setter
    def added_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._added_by_user = value
        self.added_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def inventory(self) -> Optional['InventoryServicesInventory']:
        return self._inventory

    @inventory.setter
    def inventory(self, value: Optional['InventoryServicesInventory']) -> None:
        self._inventory = value
        self.inventory_id_id = value.id if value else None

    @property
    def po(self) -> Optional['OrderServicePurchaseOrder']:
        return self._po

    @po.setter
    def po(self, value: Optional['OrderServicePurchaseOrder']) -> None:
        self._po = value
        self.po_id_id = value.id if value else None

    @property
    def so(self) -> Optional['OrderServiceSalesOrder']:
        return self._so

    @so.setter
    def so(self, value: Optional['OrderServiceSalesOrder']) -> None:
        self._so = value
        self.so_id_id = value.id if value else None

    @property
    def rack_shelf_floor(self) -> Optional['InventoryServicesRackAndShelvesAndFloor']:
        return self._rack_shelf_floor

    @rack_shelf_floor.setter
    def rack_shelf_floor(self, value: Optional['InventoryServicesRackAndShelvesAndFloor']) -> None:
        self._rack_shelf_floor = value
        self.rack_shelf_floor_id_id = value.id if value else None

    @property
    def warehouse(self) -> Optional['InventoryServicesWarehouse']:
        return self._warehouse

    @warehouse.setter
    def warehouse(self, value: Optional['InventoryServicesWarehouse']) -> None:
        self._warehouse = value
        self.warehouse_id_id = value.id if value else None


class OrderServiceSalesOrderOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: int,
        quantity_delivered: int,
        quantity_shipped: int,
        quantity_cancelled: int,
        quantity_returned: int,
        purchase_price: float,
        discount_amount: float,
        discount_type: str,
        amount_paid: float,
        amount_returned: float,
        amount_cancelled: float,
        amount_ordered: float,
        tax_percentage: float,
        tax_amount: float,
        shipping_amount: float,
        shipping_type: str,
        shipping_tax_amount: float,
        shipping_cancelled_amount: float,
        shipping_cancelled_tax_amount: float,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: datetime,
        cancelled_at: datetime,
        cancelled_reason: str,
        shipped_at: datetime,
        returned_at: datetime,
        approved_by_user_id_id: Optional[int] = None,
        cancelled_by_user_id_id: Optional[int] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
        returned_by_user_id_id: Optional[int] = None,
        shipped_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        updated_by_user_id_id: Optional[int] = None
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
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
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

        self._approved_by_user: Optional['UserservicesUsers'] = None
        self._cancelled_by_user: Optional['UserservicesUsers'] = None
        self._created_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._product: Optional['ProductServicesProducts'] = None
        self._returned_by_user: Optional['UserservicesUsers'] = None
        self._shipped_by_user: Optional['UserservicesUsers'] = None
        self._so: Optional['OrderServiceSalesOrder'] = None
        self._updated_by_user: Optional['UserservicesUsers'] = None

    @property
    def approved_by_user(self) -> Optional['UserservicesUsers']:
        return self._approved_by_user

    @approved_by_user.setter
    def approved_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._approved_by_user = value
        self.approved_by_user_id_id = value.id if value else None

    @property
    def cancelled_by_user(self) -> Optional['UserservicesUsers']:
        return self._cancelled_by_user

    @cancelled_by_user.setter
    def cancelled_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._cancelled_by_user = value
        self.cancelled_by_user_id_id = value.id if value else None

    @property
    def created_by_user(self) -> Optional['UserservicesUsers']:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._created_by_user = value
        self.created_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def product(self) -> Optional['ProductServicesProducts']:
        return self._product

    @product.setter
    def product(self, value: Optional['ProductServicesProducts']) -> None:
        self._product = value
        self.product_id_id = value.id if value else None

    @property
    def returned_by_user(self) -> Optional['UserservicesUsers']:
        return self._returned_by_user

    @returned_by_user.setter
    def returned_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._returned_by_user = value
        self.returned_by_user_id_id = value.id if value else None

    @property
    def shipped_by_user(self) -> Optional['UserservicesUsers']:
        return self._shipped_by_user

    @shipped_by_user.setter
    def shipped_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._shipped_by_user = value
        self.shipped_by_user_id_id = value.id if value else None

    @property
    def so(self) -> Optional['OrderServiceSalesOrder']:
        return self._so

    @so.setter
    def so(self, value: Optional['OrderServiceSalesOrder']) -> None:
        self._so = value
        self.so_id_id = value.id if value else None

    @property
    def updated_by_user(self) -> Optional['UserservicesUsers']:
        return self._updated_by_user

    @updated_by_user.setter
    def updated_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._updated_by_user = value
        self.updated_by_user_id_id = value.id if value else None


class OrderServiceSalesOrderLogs:
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: Union[Dict[str, Any], List[Any]],
        created_at: datetime,
        updated_at: datetime,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None
    ):
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.so_id_id = so_id_id

        self._created_by_user: Optional['UserservicesUsers'] = None
        self._domain_user: Optional['UserservicesUsers'] = None
        self._so: Optional['OrderServiceSalesOrder'] = None

    @property
    def created_by_user(self) -> Optional['UserservicesUsers']:
        return self._created_by_user

    @created_by_user.setter
    def created_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._created_by_user = value
        self.created_by_user_id_id = value.id if value else None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def so(self) -> Optional['OrderServiceSalesOrder']:
        return self._so

    @so.setter
    def so(self, value: Optional['OrderServiceSalesOrder']) -> None:
        self._so = value
        self.so_id_id = value.id if value else None


class OrderServiceSalesOrderOutwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: datetime,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user_id_id: Optional[int] = None,
        outwarded_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None
    ):
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user_id_id = domain_user_id_id
        self.outwarded_by_user_id_id = outwarded_by_user_id_id
        self.so_id_id = so_id_id

        self._domain_user: Optional['UserservicesUsers'] = None
        self._outwarded_by_user: Optional['UserservicesUsers'] = None
        self._so: Optional['OrderServiceSalesOrder'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def outwarded_by_user(self) -> Optional['UserservicesUsers']:
        return self._outwarded_by_user

    @outwarded_by_user.setter
    def outwarded_by_user(self, value: Optional['UserservicesUsers']) -> None:
        self._outwarded_by_user = value
        self.outwarded_by_user_id_id = value.id if value else None

    @property
    def so(self) -> Optional['OrderServiceSalesOrder']:
        return self._so

    @so.setter
    def so(self, value: Optional['OrderServiceSalesOrder']) -> None:
        self._so = value
        self.so_id_id = value.id if value else None


class OrderServiceSalesOrderItemOutwardedLog:
    def __init__(
        self,
        id: int,
        outwarded_quantity: int,
        price: float,
        tax_percentage: float,
        discount_amount: float,
        discount_type: str,
        shipping_amount: float,
        shipping_tax_percentage: float,
        additional_details: Union[Dict[str, Any], List[Any]],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user_id_id: Optional[int] = None,
        so_item_id_id: Optional[int] = None
    ):
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
        self.domain_user_id_id = domain_user_id_id
        self.so_item_id_id = so_item_id_id

        self._domain_user: Optional['UserservicesUsers'] = None
        self._so_item: Optional['OrderServiceSalesOrderOrderItems'] = None

    @property
    def domain_user(self) -> Optional['UserservicesUsers']:
        return self._domain_user

    @domain_user.setter
    def domain_user(self, value: Optional['UserservicesUsers']) -> None:
        self._domain_user = value
        self.domain_user_id_id = value.id if value else None

    @property
    def so_item(self) -> Optional['OrderServiceSalesOrderOrderItems']:
        return self._so_item

    @so_item.setter
    def so_item(self, value: Optional['OrderServiceSalesOrderOrderItems']) -> None:
        self._so_item = value
        self.so_item_id_id = value.id if value else None