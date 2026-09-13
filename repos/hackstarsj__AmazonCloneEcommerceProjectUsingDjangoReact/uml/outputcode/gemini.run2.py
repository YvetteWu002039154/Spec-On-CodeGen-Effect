import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

class ContentType:
    def __init__(self, id: int, app_label: str, model: str):
        self.id: int = id
        self.app_label: str = app_label
        self.model: str = model
        self.admin_logs: List['AdminLog'] = []
        self.permissions: List['Permission'] = []

class Permission:
    def __init__(self, id: int, name: str, codename: str, content_type_id: int):
        self.id: int = id
        self.name: str = name
        self.codename: str = codename
        self.content_type_id: int = content_type_id
        self.content_type: Optional['ContentType'] = None
        self.group_permissions: List['GroupPermissions'] = []
        self.user_permissions: List['UsersUserPermissions'] = []

class Group:
    def __init__(self, id: int, name: str):
        self.id: int = id
        self.name: str = name
        self.group_permissions: List['GroupPermissions'] = []
        self.users_groups: List['UsersGroups'] = []

class GroupPermissions:
    def __init__(self, id: int, group_id: int, permission_id: int):
        self.id: int = id
        self.group_id: int = group_id
        self.permission_id: int = permission_id
        self.group: Optional['Group'] = None
        self.permission: Optional['Permission'] = None

class Session:
    def __init__(self, session_key: str, session_data: str, expire_date: datetime.datetime):
        self.session_key: str = session_key
        self.session_data: str = session_data
        self.expire_date: datetime.datetime = expire_date

class Migrations:
    def __init__(self, id: int, app: str, name: str, applied: datetime.datetime):
        self.id: int = id
        self.app: str = app
        self.name: str = name
        self.applied: datetime.datetime = applied

class AdminLog:
    def __init__(self, id: int, action_time: datetime.datetime, object_id: str, object_repr: str, action_flag: int, change_message: str, content_type_id: int, user_id: int):
        self.id: int = id
        self.action_time: datetime.datetime = action_time
        self.object_id: str = object_id
        self.object_repr: str = object_repr
        self.action_flag: int = action_flag
        self.change_message: str = change_message
        self.content_type_id: int = content_type_id
        self.user_id: int = user_id
        self.content_type: Optional['ContentType'] = None
        self.user: Optional['Users'] = None

class Users:
    def __init__(self, id: int, is_superuser: bool, first_name: str, last_name: str, is_staff: bool, is_active: bool, date_joined: datetime.datetime, name: str, email: str, phone: str, address: str, city: str, state: str, pincode: str, country: str, profile_pic: str, account_status: str, role: str, dob: datetime.date, username: str, password: str, social_media_links: Dict[str, Any], addition_details: Dict[str, Any], language: str, departMent: str, designation: str, time_zone: str, last_login: datetime.datetime, last_device: str, last_ip: str, currency: str, domain_name: str, plan_type: str, created_at: datetime.datetime, updated_at: datetime.datetime, domain_user_id_id: Optional[int]):
        self.id: int = id
        self.is_superuser: bool = is_superuser
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.is_staff: bool = is_staff
        self.is_active: bool = is_active
        self.date_joined: datetime.datetime = date_joined
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
        self.dob: datetime.date = dob
        self.username: str = username
        self.password: str = password
        self.social_media_links: Dict[str, Any] = social_media_links
        self.addition_details: Dict[str, Any] = addition_details
        self.language: str = language
        self.departMent: str = departMent
        self.designation: str = designation
        self.time_zone: str = time_zone
        self.last_login: datetime.datetime = last_login
        self.last_device: str = last_device
        self.last_ip: str = last_ip
        self.currency: str = currency
        self.domain_name: str = domain_name
        self.plan_type: str = plan_type
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.domain_user_id_id: Optional[int] = domain_user_id_id
        self.domain_user: Optional['Users'] = None
        self.sub_users: List['Users'] = []
        self.shipping_addresses: List['UserShippingAddress'] = []
        self.activity_logs: List['ActivityLog'] = []
        self.user_permissions: List['UserPermissions'] = []
        self.users_groups: List['UsersGroups'] = []
        self.users_user_permissions: List['UsersUserPermissions'] = []
        self.admin_logs: List['AdminLog'] = []
        self.inventories_added: List['Inventory'] = []
        self.inventory_logs_added: List['InventoryLog'] = []
        self.racks_added: List['RackAndShelvesAndFloor'] = []
        self.warehouses_managed: List['Warehouse'] = []
        self.warehouses_added: List['Warehouse'] = []
        self.purchase_orders_created: List['PurchaseOrder'] = []
        self.purchase_orders_approved: List['PurchaseOrder'] = []
        self.purchase_orders_cancelled: List['PurchaseOrder'] = []
        self.purchase_orders_received: List['PurchaseOrder'] = []
        self.purchase_orders_returned: List['PurchaseOrder'] = []
        self.purchase_orders_updated: List['PurchaseOrder'] = []
        self.purchase_orders_supplied: List['PurchaseOrder'] = []
        self.sales_orders_created: List['SalesOrder'] = []
        self.sales_orders_customer: List['SalesOrder'] = []
        self.categories_added: List['Categories'] = []
        self.products_added: List['Products'] = []
        self.product_questions_asked: List['ProductQuestions'] = []
        self.product_questions_answered: List['ProductQuestions'] = []
        self.product_reviews: List['ProductReviews'] = []

class UserShippingAddress:
    def __init__(self, id: int, address_type: str, address: str, city: str, state: str, pincode: str, country: str, created_at: datetime.datetime, updated_at: datetime.datetime, user_id: int):
        self.id: int = id
        self.address_type: str = address_type
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.pincode: str = pincode
        self.country: str = country
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.user_id: int = user_id
        self.user: Optional['Users'] = None

class ActivityLog:
    def __init__(self, id: int, activity: str, activity_type: str, activity_date: datetime.datetime, activity_ip: str, activity_device: str, created_at: datetime.datetime, updated_at: datetime.datetime, domain_user_id_id: int, user_id: int):
        self.id: int = id
        self.activity: str = activity
        self.activity_type: str = activity_type
        self.activity_date: datetime.datetime = activity_date
        self.activity_ip: str = activity_ip
        self.activity_device: str = activity_device
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.domain_user_id_id: int = domain_user_id_id
        self.user_id: int = user_id
        self.domain_user: Optional['Users'] = None
        self.user: Optional['Users'] = None

class Modules:
    def __init__(self, id: int, module_name: str, module_icon: str, is_menu: bool, is_active: bool, module_url: str, display_order: int, module_description: str, created_at: datetime.datetime, updated_at: datetime.datetime, parent_id_id: Optional[int]):
        self.id: int = id
        self.module_name: str = module_name
        self.module_icon: str = module_icon
        self.is_menu: bool = is_menu
        self.is_active: bool = is_active
        self.module_url: str = module_url
        self.display_order: int = display_order
        self.module_description: str = module_description
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.parent_id_id: Optional[int] = parent_id_id
        self.parent: Optional['Modules'] = None
        self.sub_modules: List['Modules'] = []
        self.user_permissions: List['UserPermissions'] = []

class UserPermissions:
    def __init__(self, id: int, is_view: bool, is_add: bool, is_edit: bool, is_delete: bool, created_at: datetime.datetime, updated_at: datetime.datetime, module_id_id: int, domain_user_id_id: int, user_id: int):
        self.id: int = id
        self.is_view: bool = is_view
        self.is_add: bool = is_add
        self.is_edit: bool = is_edit
        self.is_delete: bool = is_delete
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.module_id_id: int = module_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.user_id: int = user_id
        self.module: Optional['Modules'] = None
        self.domain_user: Optional['Users'] = None
        self.user: Optional['Users'] = None

class UsersGroups:
    def __init__(self, id: int, users_id: int, group_id: int):
        self.id: int = id
        self.users_id: int = users_id
        self.group_id: int = group_id
        self.user: Optional['Users'] = None
        self.group: Optional['Group'] = None

class UsersUserPermissions:
    def __init__(self, id: int, users_id: int, permission_id: int):
        self.id: int = id
        self.users_id: int = users_id
        self.permission_id: int = permission_id
        self.user: Optional['Users'] = None
        self.permission: Optional['Permission'] = None

class Categories:
    def __init__(self, id: int, name: str, image: str, description: str, display_order: int, created_at: datetime.datetime, updated_at: datetime.datetime, added_by_user_id_id: int, domain_user_id_id: int, parent_id_id: Optional[int]):
        self.id: int = id
        self.name: str = name
        self.image: str = image
        self.description: str = description
        self.display_order: int = display_order
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.added_by_user_id_id: int = added_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.parent_id_id: Optional[int] = parent_id_id
        self.added_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.parent: Optional['Categories'] = None
        self.sub_categories: List['Categories'] = []
        self.products: List['Products'] = []

class Products:
    def __init__(self, id: int, name: str, image: Dict[str, Any], description: str, specifications: Dict[str, Any], html_description: str, highlights: Dict[str, Any], sku: str, initial_buying_price: float, initial_selling_price: float, weight: float, dimensions: str, uom: str, color: str, tax_percentage: float, brand: str, brand_model: str, status: str, seo_title: str, seo_description: str, seo_keywords: Dict[str, Any], addition_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, added_by_user_id_id: int, category_id_id: int, domain_user_id_id: int):
        self.id: int = id
        self.name: str = name
        self.image: Dict[str, Any] = image
        self.description: str = description
        self.specifications: Dict[str, Any] = specifications
        self.html_description: str = html_description
        self.highlights: Dict[str, Any] = highlights
        self.sku: str = sku
        self.initial_buying_price: float = initial_buying_price
        self.initial_selling_price: float = initial_selling_price
        self.weight: float = weight
        self.dimensions: str = dimensions
        self.uom: str = uom
        self.color: str = color
        self.tax_percentage: float = tax_percentage
        self.brand: str = brand
        self.brand_model: str = brand_model
        self.status: str = status
        self.seo_title: str = seo_title
        self.seo_description: str = seo_description
        self.seo_keywords: Dict[str, Any] = seo_keywords
        self.addition_details: Dict[str, Any] = addition_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.added_by_user_id_id: int = added_by_user_id_id
        self.category_id_id: int = category_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.added_by_user: Optional['Users'] = None
        self.category: Optional['Categories'] = None
        self.domain_user: Optional['Users'] = None
        self.inventories: List['Inventory'] = []
        self.purchase_order_items: List['PurchaseOrderItems'] = []
        self.sales_order_items: List['SalesOrderOrderItems'] = []
        self.questions: List['ProductQuestions'] = []
        self.reviews: List['ProductReviews'] = []

class ProductQuestions:
    def __init__(self, id: int, question: str, answer: str, status: str, created_at: datetime.datetime, updated_at: datetime.datetime, answer_user_id_id: int, domain_user_id_id: int, question_user_id_id: int, product_id_id: int):
        self.id: int = id
        self.question: str = question
        self.answer: str = answer
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.answer_user_id_id: int = answer_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.question_user_id_id: int = question_user_id_id
        self.product_id_id: int = product_id_id
        self.answer_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.question_user: Optional['Users'] = None
        self.product: Optional['Products'] = None

class ProductReviews:
    def __init__(self, id: int, review_images: Dict[str, Any], rating: float, reviews: str, status: str, domain_user_id_id: int, review_user_id_id: int, product_id_id: int):
        self.id: int = id
        self.review_images: Dict[str, Any] = review_images
        self.rating: float = rating
        self.reviews: str = reviews
        self.status: str = status
        self.domain_user_id_id: int = domain_user_id_id
        self.review_user_id_id: int = review_user_id_id
        self.product_id_id: int = product_id_id
        self.domain_user: Optional['Users'] = None
        self.review_user: Optional['Users'] = None
        self.product: Optional['Products'] = None

class Warehouse:
    def __init__(self, id: int, name: str, address: str, city: str, state: str, country: str, pincode: str, phone: str, email: str, status: str, size: str, capacity: str, warehouse_type: str, additional_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, added_by_user_id_id: int, domain_user_id_id: int, warehouse_manager_id: int):
        self.id: int = id
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
        self.additional_details: Dict[str, Any] = additional_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.added_by_user_id_id: int = added_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.warehouse_manager_id: int = warehouse_manager_id
        self.added_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.warehouse_manager: Optional['Users'] = None
        self.inventories: List['Inventory'] = []
        self.inventory_logs: List['InventoryLog'] = []
        self.racks_shelves_floors: List['RackAndShelvesAndFloor'] = []
        self.purchase_orders: List['PurchaseOrder'] = []

class RackAndShelvesAndFloor:
    def __init__(self, id: int, name: str, rack: str, shelf: str, floor: str, additional_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, added_by_user_id_id: int, domain_user_id_id: int, warehouse_id_id: int):
        self.id: int = id
        self.name: str = name
        self.rack: str = rack
        self.shelf: str = shelf
        self.floor: str = floor
        self.additional_details: Dict[str, Any] = additional_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.added_by_user_id_id: int = added_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.warehouse_id_id: int = warehouse_id_id
        self.added_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.warehouse: Optional['Warehouse'] = None
        self.inventories: List['Inventory'] = []
        self.inventory_logs: List['InventoryLog'] = []

class Inventory:
    def __init__(self, id: int, quantity: int, mrp: str, batch_number: str, discount_type: str, discount_amout: float, sr_no: str, mfg_date: datetime.datetime, uom: str, ptr: str, received_date: datetime.datetime, expiry_date: datetime.datetime, quantity_inwarded: int, buy_price: Decimal, sell_price: Decimal, tax_percentage: Decimal, stock_status: str, inward_type: str, additional_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, added_by_user_id_id: int, domain_user_id_id: int, product_id_id: int, purchase_order_id_id: int, purchase_order_item_id_id: int, purchase_order_item_inwarded_item_id_id: int, rack_shelf_floor_id_id: int, warehouse_id_id: int):
        self.id: int = id
        self.quantity: int = quantity
        self.mrp: str = mrp
        self.batch_number: str = batch_number
        self.discount_type: str = discount_type
        self.discount_amout: float = discount_amout
        self.sr_no: str = sr_no
        self.mfg_date: datetime.datetime = mfg_date
        self.uom: str = uom
        self.ptr: str = ptr
        self.received_date: datetime.datetime = received_date
        self.expiry_date: datetime.datetime = expiry_date
        self.quantity_inwarded: int = quantity_inwarded
        self.buy_price: Decimal = buy_price
        self.sell_price: Decimal = sell_price
        self.tax_percentage: Decimal = tax_percentage
        self.stock_status: str = stock_status
        self.inward_type: str = inward_type
        self.additional_details: Dict[str, Any] = additional_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.added_by_user_id_id: int = added_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.product_id_id: int = product_id_id
        self.purchase_order_id_id: int = purchase_order_id_id
        self.purchase_order_item_id_id: int = purchase_order_item_id_id
        self.purchase_order_item_inwarded_item_id_id: int = purchase_order_item_inwarded_item_id_id
        self.rack_shelf_floor_id_id: int = rack_shelf_floor_id_id
        self.warehouse_id_id: int = warehouse_id_id
        self.added_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.product: Optional['Products'] = None
        self.purchase_order: Optional['PurchaseOrder'] = None
        self.purchase_order_item: Optional['PurchaseOrderItems'] = None
        self.purchase_order_item_inwarded: Optional['PurchaseOrderItemInwardedLog'] = None
        self.rack_shelf_floor: Optional['RackAndShelvesAndFloor'] = None
        self.warehouse: Optional['Warehouse'] = None
        self.inventory_logs: List['InventoryLog'] = []

class InventoryLog:
    def __init__(self, id: int, quantity: int, status: str, additional_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, added_by_user_id_id: int, domain_user_id_id: int, inventory_id_id: int, po_id_id: Optional[int], so_id_id: Optional[int], rack_shelf_floor_id_id: int, warehouse_id_id: int):
        self.id: int = id
        self.quantity: int = quantity
        self.status: str = status
        self.additional_details: Dict[str, Any] = additional_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.added_by_user_id_id: int = added_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.inventory_id_id: int = inventory_id_id
        self.po_id_id: Optional[int] = po_id_id
        self.so_id_id: Optional[int] = so_id_id
        self.rack_shelf_floor_id_id: int = rack_shelf_floor_id_id
        self.warehouse_id_id: int = warehouse_id_id
        self.added_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.inventory: Optional['Inventory'] = None
        self.purchase_order: Optional['PurchaseOrder'] = None
        self.sales_order: Optional['SalesOrder'] = None
        self.rack_shelf_floor: Optional['RackAndShelvesAndFloor'] = None
        self.warehouse: Optional['Warehouse'] = None

class PurchaseOrder:
    def __init__(self, id: int, po_code: str, po_date: datetime.datetime, expected_delivery_date: datetime.datetime, payment_terms: str, payment_status: str, total_amount: Decimal, paid_amount: Decimal, due_amount: Decimal, discount_amount: Decimal, discount_type: str, shipping_amount: Decimal, shipping_type: str, shipping_tax_percentage: Decimal, shipping_tax_amount: Decimal, shipping_cancelled_amount: Decimal, shipping_cancelled_tax_amount: Decimal, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, approved_at: datetime.datetime, cancelled_at: datetime.datetime, cancelled_reason: str, received_at: datetime.datetime, returned_at: datetime.datetime, approved_by_user_id_id: int, cancelled_by_user_id_id: int, created_by_user_id_id: int, domain_user_id_id: int, last_updated_by_user_id_id: int, received_by_user_id_id: int, returned_by_user_id_id: int, supplier_id_id: int, updated_by_user_id_id: int, warehouse_id_id: int):
        self.id: int = id
        self.po_code: str = po_code
        self.po_date: datetime.datetime = po_date
        self.expected_delivery_date: datetime.datetime = expected_delivery_date
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
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.approved_at: datetime.datetime = approved_at
        self.cancelled_at: datetime.datetime = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: datetime.datetime = received_at
        self.returned_at: datetime.datetime = returned_at
        self.approved_by_user_id_id: int = approved_by_user_id_id
        self.cancelled_by_user_id_id: int = cancelled_by_user_id_id
        self.created_by_user_id_id: int = created_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.last_updated_by_user_id_id: int = last_updated_by_user_id_id
        self.received_by_user_id_id: int = received_by_user_id_id
        self.returned_by_user_id_id: int = returned_by_user_id_id
        self.supplier_id_id: int = supplier_id_id
        self.updated_by_user_id_id: int = updated_by_user_id_id
        self.warehouse_id_id: int = warehouse_id_id
        self.approved_by_user: Optional['Users'] = None
        self.cancelled_by_user: Optional['Users'] = None
        self.created_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.last_updated_by_user: Optional['Users'] = None
        self.received_by_user: Optional['Users'] = None
        self.returned_by_user: Optional['Users'] = None
        self.supplier: Optional['Users'] = None
        self.updated_by_user: Optional['Users'] = None
        self.warehouse: Optional['Warehouse'] = None
        self.items: List['PurchaseOrderItems'] = []
        self.logs: List['PurchaseOrderLogs'] = []
        self.inwarded_logs: List['PurchaseOrderInwardedLog'] = []
        self.inventories: List['Inventory'] = []
        self.inventory_logs: List['InventoryLog'] = []

class PurchaseOrderItems:
    def __init__(self, id: int, quantity_ordered: int, quantity_received: int, quantity_cancelled: int, quantity_returned: int, buying_price: Decimal, selling_price: Decimal, discount_amount: Decimal, amount_paid: Decimal, amount_returned: Decimal, amount_cancelled: Decimal, amount_ordered: Decimal, tax_percentage: Decimal, tax_amount: Decimal, shipping_tax_percentage: Decimal, shipping_amount: Decimal, shipping_tax_amount: Decimal, shipping_cancelled_amount: Decimal, shipping_cancelled_tax_amount: Decimal, discount_type: str, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, approved_at: datetime.datetime, cancelled_at: datetime.datetime, cancelled_reason: str, received_at: datetime.datetime, returned_at: datetime.datetime, approved_by_user_id_id: int, cancelled_by_user_id_id: int, created_by_user_id_id: int, domain_user_id_id: int, last_updated_by_user_id_id: int, received_by_user_id_id: int, returned_by_user_id_id: int, po_id_id: int, product_id_id: int, updated_by_user_id_id: int):
        self.id: int = id
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
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.approved_at: datetime.datetime = approved_at
        self.cancelled_at: datetime.datetime = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: datetime.datetime = received_at
        self.returned_at: datetime.datetime = returned_at
        self.approved_by_user_id_id: int = approved_by_user_id_id
        self.cancelled_by_user_id_id: int = cancelled_by_user_id_id
        self.created_by_user_id_id: int = created_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.last_updated_by_user_id_id: int = last_updated_by_user_id_id
        self.received_by_user_id_id: int = received_by_user_id_id
        self.returned_by_user_id_id: int = returned_by_user_id_id
        self.po_id_id: int = po_id_id
        self.product_id_id: int = product_id_id
        self.updated_by_user_id_id: int = updated_by_user_id_id
        self.approved_by_user: Optional['Users'] = None
        self.cancelled_by_user: Optional['Users'] = None
        self.created_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.last_updated_by_user: Optional['Users'] = None
        self.received_by_user: Optional['Users'] = None
        self.returned_by_user: Optional['Users'] = None
        self.purchase_order: Optional['PurchaseOrder'] = None
        self.product: Optional['Products'] = None
        self.updated_by_user: Optional['Users'] = None
        self.inwarded_logs: List['PurchaseOrderItemInwardedLog'] = []
        self.inventories: List['Inventory'] = []

class PurchaseOrderLogs:
    def __init__(self, id: int, comment: str, additional_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, created_by_user_id_id: int, domain_user_id_id: int, po_id_id: int):
        self.id: int = id
        self.comment: str = comment
        self.additional_details: Dict[str, Any] = additional_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.created_by_user_id_id: int = created_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.po_id_id: int = po_id_id
        self.created_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.purchase_order: Optional['PurchaseOrder'] = None

class PurchaseOrderInwardedLog:
    def __init__(self, id: int, invoice_path: str, invoice_number: str, notes: str, inwarded_at: datetime.datetime, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, domain_user_id_id: int, inwarded_by_user_id_id: int, po_id_id: int):
        self.id: int = id
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.inwarded_at: datetime.datetime = inwarded_at
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.domain_user_id_id: int = domain_user_id_id
        self.inwarded_by_user_id_id: int = inwarded_by_user_id_id
        self.po_id_id: int = po_id_id
        self.domain_user: Optional['Users'] = None
        self.inwarded_by_user: Optional['Users'] = None
        self.purchase_order: Optional['PurchaseOrder'] = None

class PurchaseOrderItemInwardedLog:
    def __init__(self, id: int, inwarded_quantity: int, price: Decimal, tax_percentage: Decimal, discount_amount: Decimal, discount_type: str, shipping_amount: Decimal, shipping_tax_percentage: Decimal, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, domain_user_id_id: int, po_item_id_id: int):
        self.id: int = id
        self.inwarded_quantity: int = inwarded_quantity
        self.price: Decimal = price
        self.tax_percentage: Decimal = tax_percentage
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.domain_user_id_id: int = domain_user_id_id
        self.po_item_id_id: int = po_item_id_id
        self.domain_user: Optional['Users'] = None
        self.purchase_order_item: Optional['PurchaseOrderItems'] = None
        self.inventories: List['Inventory'] = []

class SalesOrder:
    def __init__(self, id: int, so_code: str, so_date: datetime.datetime, expected_delivery_date: datetime.datetime, payment_terms: str, payment_status: str, total_amount: Decimal, paid_amount: Decimal, due_amount: Decimal, discount_amount: Decimal, discount_type: str, shipping_amount: Decimal, shipping_type: str, shipping_tax_percentage: Decimal, shipping_tax_amount: Decimal, shipping_cancelled_amount: Decimal, shipping_cancelled_tax_amount: Decimal, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, approved_at: datetime.datetime, cancelled_at: datetime.datetime, cancelled_reason: str, received_at: datetime.datetime, returned_at: datetime.datetime, approved_by_user_id_id: int, cancelled_by_user_id_id: int, created_by_user_id_id: int, customer_id_id: int, domain_user_id_id: int, last_updated_by_user_id_id: int, received_by_user_id_id: int, returned_by_user_id_id: int, po_id_id: int, product_id_id: int, updated_by_user_id_id: int):
        self.id: int = id
        self.so_code: str = so_code
        self.so_date: datetime.datetime = so_date
        self.expected_delivery_date: datetime.datetime = expected_delivery_date
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
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.approved_at: datetime.datetime = approved_at
        self.cancelled_at: datetime.datetime = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.received_at: datetime.datetime = received_at
        self.returned_at: datetime.datetime = returned_at
        self.approved_by_user_id_id: int = approved_by_user_id_id
        self.cancelled_by_user_id_id: int = cancelled_by_user_id_id
        self.created_by_user_id_id: int = created_by_user_id_id
        self.customer_id_id: int = customer_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.last_updated_by_user_id_id: int = last_updated_by_user_id_id
        self.received_by_user_id_id: int = received_by_user_id_id
        self.returned_by_user_id_id: int = returned_by_user_id_id
        self.po_id_id: int = po_id_id
        self.product_id_id: int = product_id_id
        self.updated_by_user_id_id: int = updated_by_user_id_id
        self.approved_by_user: Optional['Users'] = None
        self.cancelled_by_user: Optional['Users'] = None
        self.created_by_user: Optional['Users'] = None
        self.customer: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.last_updated_by_user: Optional['Users'] = None
        self.received_by_user: Optional['Users'] = None
        self.returned_by_user: Optional['Users'] = None
        self.updated_by_user: Optional['Users'] = None
        self.items: List['SalesOrderOrderItems'] = []
        self.logs: List['SalesOrderLogs'] = []
        self.outwarded_logs: List['SalesOrderOutwardedLog'] = []
        self.inventory_logs: List['InventoryLog'] = []

class SalesOrderOrderItems:
    def __init__(self, id: int, quantity_ordered: int, quantity_delivered: int, quantity_shipped: int, quantity_cancelled: int, quantity_returned: int, purchase_price: Decimal, discount_amount: Decimal, discount_type: str, amount_paid: Decimal, amount_returned: Decimal, amount_cancelled: Decimal, amount_ordered: Decimal, tax_percentage: Decimal, tax_amount: Decimal, shipping_amount: Decimal, shipping_type: str, shipping_tax_amount: Decimal, shipping_cancelled_amount: Decimal, shipping_cancelled_tax_amount: Decimal, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, approved_at: datetime.datetime, cancelled_at: datetime.datetime, cancelled_reason: str, shipped_at: datetime.datetime, returned_at: datetime.datetime, approved_by_user_id_id: int, cancelled_by_user_id_id: int, created_by_user_id_id: int, domain_user_id_id: int, product_id_id: int, returned_by_user_id_id: int, shipped_by_user_id_id: int, so_id_id: int, updated_by_user_id_id: int):
        self.id: int = id
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
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.approved_at: datetime.datetime = approved_at
        self.cancelled_at: datetime.datetime = cancelled_at
        self.cancelled_reason: str = cancelled_reason
        self.shipped_at: datetime.datetime = shipped_at
        self.returned_at: datetime.datetime = returned_at
        self.approved_by_user_id_id: int = approved_by_user_id_id
        self.cancelled_by_user_id_id: int = cancelled_by_user_id_id
        self.created_by_user_id_id: int = created_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.product_id_id: int = product_id_id
        self.returned_by_user_id_id: int = returned_by_user_id_id
        self.shipped_by_user_id_id: int = shipped_by_user_id_id
        self.so_id_id: int = so_id_id
        self.updated_by_user_id_id: int = updated_by_user_id_id
        self.approved_by_user: Optional['Users'] = None
        self.cancelled_by_user: Optional['Users'] = None
        self.created_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.product: Optional['Products'] = None
        self.returned_by_user: Optional['Users'] = None
        self.shipped_by_user: Optional['Users'] = None
        self.sales_order: Optional['SalesOrder'] = None
        self.updated_by_user: Optional['Users'] = None
        self.outwarded_logs: List['SalesOrderItemOutwardedLog'] = []

class SalesOrderLogs:
    def __init__(self, id: int, comment: str, additional_details: Dict[str, Any], created_at: datetime.datetime, updated_at: datetime.datetime, created_by_user_id_id: int, domain_user_id_id: int, so_id_id: int):
        self.id: int = id
        self.comment: str = comment
        self.additional_details: Dict[str, Any] = additional_details
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.created_by_user_id_id: int = created_by_user_id_id
        self.domain_user_id_id: int = domain_user_id_id
        self.so_id_id: int = so_id_id
        self.created_by_user: Optional['Users'] = None
        self.domain_user: Optional['Users'] = None
        self.sales_order: Optional['SalesOrder'] = None

class SalesOrderOutwardedLog:
    def __init__(self, id: int, invoice_path: str, invoice_number: str, notes: str, outwared_at: datetime.datetime, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, domain_user_id_id: int, outwarded_by_user_id_id: int, so_id_id: int):
        self.id: int = id
        self.invoice_path: str = invoice_path
        self.invoice_number: str = invoice_number
        self.notes: str = notes
        self.outwared_at: datetime.datetime = outwared_at
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.domain_user_id_id: int = domain_user_id_id
        self.outwarded_by_user_id_id: int = outwarded_by_user_id_id
        self.so_id_id: int = so_id_id
        self.domain_user: Optional['Users'] = None
        self.outwarded_by_user: Optional['Users'] = None
        self.sales_order: Optional['SalesOrder'] = None

class SalesOrderItemOutwardedLog:
    def __init__(self, id: int, outwarded_quantity: int, price: Decimal, tax_percentage: Decimal, discount_amount: Decimal, discount_type: str, shipping_amount: Decimal, shipping_tax_percentage: Decimal, additional_details: Dict[str, Any], status: str, created_at: datetime.datetime, updated_at: datetime.datetime, domain_user_id_id: int, so_item_id_id: int):
        self.id: int = id
        self.outwarded_quantity: int = outwarded_quantity
        self.price: Decimal = price
        self.tax_percentage: Decimal = tax_percentage
        self.discount_amount: Decimal = discount_amount
        self.discount_type: str = discount_type
        self.shipping_amount: Decimal = shipping_amount
        self.shipping_tax_percentage: Decimal = shipping_tax_percentage
        self.additional_details: Dict[str, Any] = additional_details
        self.status: str = status
        self.created_at: datetime.datetime = created_at
        self.updated_at: datetime.datetime = updated_at
        self.domain_user_id_id: int = domain_user_id_id
        self.so_item_id_id: int = so_item_id_id
        self.domain_user: Optional['Users'] = None
        self.sales_order_item: Optional['SalesOrderOrderItems'] = None