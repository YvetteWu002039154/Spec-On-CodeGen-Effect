from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

# ============================================================
#  DJANGO FRAMEWORK / AUTH
# ============================================================

class DjangoContentType:
    def __init__(
        self,
        id: int,
        app_label: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.id = id
        self.app_label = app_label
        self.model = model


class DjangoMigrations:
    def __init__(
        self,
        id: int,
        app: Optional[str] = None,
        name: Optional[str] = None,
        applied: Optional[datetime] = None
    ):
        self.id = id
        self.app = app
        self.name = name
        self.applied = applied


class DjangoSession:
    def __init__(
        self,
        session_key: str,
        session_data: Optional[str] = None,
        expire_date: Optional[datetime] = None
    ):
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date


class AuthGroup:
    def __init__(
        self,
        id: int,
        name: Optional[str] = None
    ):
        self.id = id
        self.name = name


class AuthPermission:
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        codename: Optional[str] = None,
        content_type_id: Optional[int] = None
    ):
        self.id = id
        self.name = name
        self.codename = codename
        self.content_type_id = content_type_id
        
        self.content_type: Optional[DjangoContentType] = None


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
        
        self.group: Optional[AuthGroup] = None
        self.permission: Optional[AuthPermission] = None


class DjangoAdminLog:
    def __init__(
        self,
        id: int,
        action_time: Optional[datetime] = None,
        object_id: Optional[str] = None,
        object_repr: Optional[str] = None,
        action_flag: Optional[int] = None,
        change_message: Optional[str] = None,
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
        
        self.content_type: Optional[DjangoContentType] = None
        self.user: Optional[UserServicesUsers] = None


# ============================================================
#  USER SERVICE
# ============================================================

class UserServicesUsers:
    def __init__(
        self,
        id: int,
        is_superuser: Optional[bool] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_staff: Optional[bool] = None,
        is_active: Optional[bool] = None,
        date_joined: Optional[datetime] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None,
        country: Optional[str] = None,
        profile_pic: Optional[str] = None,
        account_status: Optional[str] = None,
        role: Optional[str] = None,
        dob: Optional[date] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        social_media_links: Optional[Dict[str, Any]] = None,
        addition_details: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        departMent: Optional[str] = None,
        designation: Optional[str] = None,
        time_zone: Optional[str] = None,
        last_login: Optional[datetime] = None,
        last_device: Optional[str] = None,
        last_ip: Optional[str] = None,
        currency: Optional[str] = None,
        domain_name: Optional[str] = None,
        plan_type: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None


class UserServicesUserShippingAddress:
    def __init__(
        self,
        id: int,
        address_type: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None,
        country: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.user: Optional[UserServicesUsers] = None


class UserServicesActivityLog:
    def __init__(
        self,
        id: int,
        activity: Optional[str] = None,
        activity_type: Optional[str] = None,
        activity_date: Optional[datetime] = None,
        activity_ip: Optional[str] = None,
        activity_device: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None
        self.user: Optional[UserServicesUsers] = None


class UserServicesModules:
    def __init__(
        self,
        id: int,
        module_name: Optional[str] = None,
        module_icon: Optional[str] = None,
        is_menu: Optional[bool] = None,
        is_active: Optional[bool] = None,
        module_url: Optional[str] = None,
        display_order: Optional[int] = None,
        module_description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.parent: Optional[UserServicesModules] = None


class UserServicesUserPermissions:
    def __init__(
        self,
        id: int,
        is_view: Optional[bool] = None,
        is_add: Optional[bool] = None,
        is_edit: Optional[bool] = None,
        is_delete: Optional[bool] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.module: Optional[UserServicesModules] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.user: Optional[UserServicesUsers] = None


class UserServicesUsersGroups:
    def __init__(
        self,
        id: int,
        users_id: Optional[int] = None,
        group_id: Optional[int] = None
    ):
        self.id = id
        self.users_id = users_id
        self.group_id = group_id
        
        self.users: Optional[UserServicesUsers] = None
        self.group: Optional[AuthGroup] = None


class UserServicesUsersUserPermissions:
    def __init__(
        self,
        id: int,
        users_id: Optional[int] = None,
        permission_id: Optional[int] = None
    ):
        self.id = id
        self.users_id = users_id
        self.permission_id = permission_id
        
        self.users: Optional[UserServicesUsers] = None
        self.permission: Optional[AuthPermission] = None


# ============================================================
#  PRODUCT SERVICE
# ============================================================

class ProductServicesCategories:
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        image: Optional[str] = None,
        description: Optional[str] = None,
        display_order: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.added_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.parent: Optional[ProductServicesCategories] = None


class ProductServicesProducts:
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        image: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        specifications: Optional[Dict[str, Any]] = None,
        html_description: Optional[str] = None,
        highlights: Optional[Dict[str, Any]] = None,
        sku: Optional[str] = None,
        initial_buying_price: Optional[float] = None,
        initial_selling_price: Optional[float] = None,
        weight: Optional[float] = None,
        dimensions: Optional[str] = None,
        uom: Optional[str] = None,
        color: Optional[str] = None,
        tax_percentage: Optional[float] = None,
        brand: Optional[str] = None,
        brand_model: Optional[str] = None,
        status: Optional[str] = None,
        seo_title: Optional[str] = None,
        seo_description: Optional[str] = None,
        seo_keywords: Optional[Dict[str, Any]] = None,
        addition_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.added_by_user: Optional[UserServicesUsers] = None
        self.category: Optional[ProductServicesCategories] = None
        self.domain_user: Optional[UserServicesUsers] = None


class ProductServicesProductQuestions:
    def __init__(
        self,
        id: int,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.answer_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.question_user: Optional[UserServicesUsers] = None
        self.product: Optional[ProductServicesProducts] = None


class ProductServicesProductReviews:
    def __init__(
        self,
        id: int,
        review_images: Optional[Dict[str, Any]] = None,
        rating: Optional[float] = None,
        reviews: Optional[str] = None,
        status: Optional[str] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None
        self.review_user: Optional[UserServicesUsers] = None
        self.product: Optional[ProductServicesProducts] = None


# ============================================================
#  INVENTORY SERVICE
# ============================================================

class InventoryServicesWarehouse:
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        pincode: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        status: Optional[str] = None,
        size: Optional[str] = None,
        capacity: Optional[str] = None,
        warehouse_type: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.added_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.warehouse_manager: Optional[UserServicesUsers] = None


class InventoryServicesRackAndShelvesAndFloor:
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        rack: Optional[str] = None,
        shelf: Optional[str] = None,
        floor: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.added_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.warehouse: Optional[InventoryServicesWarehouse] = None


class InventoryServicesInventory:
    def __init__(
        self,
        id: int,
        quantity: Optional[int] = None,
        mrp: Optional[str] = None,
        batch_number: Optional[str] = None,
        discount_type: Optional[str] = None,
        discount_amout: Optional[float] = None,
        sr_no: Optional[str] = None,
        mfg_date: Optional[datetime] = None,
        uom: Optional[str] = None,
        ptr: Optional[str] = None,
        received_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        quantity_inwarded: Optional[int] = None,
        buy_price: Optional[Decimal] = None,
        sell_price: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        stock_status: Optional[str] = None,
        inward_type: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.added_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.product: Optional[ProductServicesProducts] = None
        self.purchase_order: Optional[OrderServicePurchaseOrder] = None
        self.purchase_order_item: Optional[OrderServicePurchaseOrderItems] = None
        self.po_item_inwarded: Optional[OrderServicePurchaseOrderItemInwardedLog] = None
        self.rack_shelf_floor: Optional[InventoryServicesRackAndShelvesAndFloor] = None
        self.warehouse: Optional[InventoryServicesWarehouse] = None


class InventoryServicesInventoryLog:
    def __init__(
        self,
        id: int,
        quantity: Optional[int] = None,
        status: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.added_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.inventory: Optional[InventoryServicesInventory] = None
        self.po: Optional[OrderServicePurchaseOrder] = None
        self.so: Optional[OrderServiceSalesOrder] = None
        self.rack_shelf_floor: Optional[InventoryServicesRackAndShelvesAndFloor] = None
        self.warehouse: Optional[InventoryServicesWarehouse] = None


# ============================================================
#  ORDER SERVICE
# ============================================================

class OrderServicePurchaseOrder:
    def __init__(
        self,
        id: int,
        po_code: Optional[str] = None,
        po_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: Optional[str] = None,
        payment_status: Optional[str] = None,
        total_amount: Optional[Decimal] = None,
        paid_amount: Optional[Decimal] = None,
        due_amount: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: Optional[str] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_type: Optional[str] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
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
        
        self.approved_by_user: Optional[UserServicesUsers] = None
        self.cancelled_by_user: Optional[UserServicesUsers] = None
        self.created_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.last_updated_by_user: Optional[UserServicesUsers] = None
        self.received_by_user: Optional[UserServicesUsers] = None
        self.returned_by_user: Optional[UserServicesUsers] = None
        self.supplier: Optional[UserServicesUsers] = None
        self.updated_by_user: Optional[UserServicesUsers] = None
        self.warehouse: Optional[InventoryServicesWarehouse] = None


class OrderServicePurchaseOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: Optional[int] = None,
        quantity_received: Optional[int] = None,
        quantity_cancelled: Optional[int] = None,
        quantity_returned: Optional[int] = None,
        buying_price: Optional[Decimal] = None,
        selling_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        amount_paid: Optional[Decimal] = None,
        amount_returned: Optional[Decimal] = None,
        amount_cancelled: Optional[Decimal] = None,
        amount_ordered: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        discount_type: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
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
        
        self.approved_by_user: Optional[UserServicesUsers] = None
        self.cancelled_by_user: Optional[UserServicesUsers] = None
        self.created_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.last_updated_by_user: Optional[UserServicesUsers] = None
        self.received_by_user: Optional[UserServicesUsers] = None
        self.returned_by_user: Optional[UserServicesUsers] = None
        self.po: Optional[OrderServicePurchaseOrder] = None
        self.product: Optional[ProductServicesProducts] = None
        self.updated_by_user: Optional[UserServicesUsers] = None


class OrderServicePurchaseOrderLogs:
    def __init__(
        self,
        id: int,
        comment: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.created_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.po: Optional[OrderServicePurchaseOrder] = None


class OrderServicePurchaseOrderInwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: Optional[str] = None,
        invoice_number: Optional[str] = None,
        notes: Optional[str] = None,
        inwarded_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None
        self.inwarded_by_user: Optional[UserServicesUsers] = None
        self.po: Optional[OrderServicePurchaseOrder] = None


class OrderServicePurchaseOrderItemInwardedLog:
    def __init__(
        self,
        id: int,
        inwarded_quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: Optional[str] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None
        self.po_item: Optional[OrderServicePurchaseOrderItems] = None


class OrderServiceSalesOrder:
    def __init__(
        self,
        id: int,
        so_code: Optional[str] = None,
        so_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: Optional[str] = None,
        payment_status: Optional[str] = None,
        total_amount: Optional[Decimal] = None,
        paid_amount: Optional[Decimal] = None,
        due_amount: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: Optional[str] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_type: Optional[str] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
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
        
        self.approved_by_user: Optional[UserServicesUsers] = None
        self.cancelled_by_user: Optional[UserServicesUsers] = None
        self.created_by_user: Optional[UserServicesUsers] = None
        self.customer: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.last_updated_by_user: Optional[UserServicesUsers] = None
        self.received_by_user: Optional[UserServicesUsers] = None
        self.returned_by_user: Optional[UserServicesUsers] = None
        self.po: Optional[OrderServicePurchaseOrder] = None
        self.product: Optional[ProductServicesProducts] = None
        self.updated_by_user: Optional[UserServicesUsers] = None


class OrderServiceSalesOrderOrderItems:
    def __init__(
        self,
        id: int,
        quantity_ordered: Optional[int] = None,
        quantity_delivered: Optional[int] = None,
        quantity_shipped: Optional[int] = None,
        quantity_cancelled: Optional[int] = None,
        quantity_returned: Optional[int] = None,
        purchase_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: Optional[str] = None,
        amount_paid: Optional[Decimal] = None,
        amount_returned: Optional[Decimal] = None,
        amount_cancelled: Optional[Decimal] = None,
        amount_ordered: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_type: Optional[str] = None,
        shipping_tax_amount: Optional[Decimal] = None,
        shipping_cancelled_amount: Optional[Decimal] = None,
        shipping_cancelled_tax_amount: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
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
        
        self.approved_by_user: Optional[UserServicesUsers] = None
        self.cancelled_by_user: Optional[UserServicesUsers] = None
        self.created_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.product: Optional[ProductServicesProducts] = None
        self.returned_by_user: Optional[UserServicesUsers] = None
        self.shipped_by_user: Optional[UserServicesUsers] = None
        self.so: Optional[OrderServiceSalesOrder] = None
        self.updated_by_user: Optional[UserServicesUsers] = None


class OrderServiceSalesOrderLogs:
    def __init__(
        self,
        id: int,
        comment: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.created_by_user: Optional[UserServicesUsers] = None
        self.domain_user: Optional[UserServicesUsers] = None
        self.so: Optional[OrderServiceSalesOrder] = None


class OrderServiceSalesOrderOutwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: Optional[str] = None,
        invoice_number: Optional[str] = None,
        notes: Optional[str] = None,
        outwared_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None
        self.outwarded_by_user: Optional[UserServicesUsers] = None
        self.so: Optional[OrderServiceSalesOrder] = None


class OrderServiceSalesOrderItemOutwardedLog:
    def __init__(
        self,
        id: int,
        outwarded_quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        tax_percentage: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        discount_type: Optional[str] = None,
        shipping_amount: Optional[Decimal] = None,
        shipping_tax_percentage: Optional[Decimal] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
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
        
        self.domain_user: Optional[UserServicesUsers] = None
        self.so_item: Optional[OrderServiceSalesOrderOrderItems] = None