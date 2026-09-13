from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, Dict, List
from datetime import datetime, date
from decimal import Decimal

@dataclass
class DjangoContentType:
    id: Optional[int] = None
    app_label: Optional[str] = None
    model: Optional[str] = None

@dataclass
class DjangoMigrations:
    id: Optional[int] = None
    app: Optional[str] = None
    name: Optional[str] = None
    applied: Optional[datetime] = None

@dataclass
class DjangoSession:
    session_key: Optional[str] = None
    session_data: Optional[str] = None
    expire_date: Optional[datetime] = None

@dataclass
class AuthGroup:
    id: Optional[int] = None
    name: Optional[str] = None

@dataclass
class AuthPermission:
    id: Optional[int] = None
    name: Optional[str] = None
    codename: Optional[str] = None
    content_type_id: Optional[int] = None
    content_type: Optional[DjangoContentType] = None

@dataclass
class AuthGroupPermissions:
    id: Optional[int] = None
    group_id: Optional[int] = None
    permission_id: Optional[int] = None
    group: Optional[AuthGroup] = None
    permission: Optional[AuthPermission] = None

@dataclass
class UserServicesUsers:
    id: Optional[int] = None
    is_superuser: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_staff: Optional[bool] = None
    is_active: Optional[bool] = None
    date_joined: Optional[datetime] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    profile_pic: Optional[str] = None
    account_status: Optional[str] = None
    role: Optional[str] = None
    dob: Optional[date] = None
    username: Optional[str] = None
    password: Optional[str] = None
    social_media_links: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    departMent: Optional[str] = None
    designation: Optional[str] = None
    time_zone: Optional[str] = None
    last_login: Optional[datetime] = None
    last_device: Optional[str] = None
    last_ip: Optional[str] = None
    currency: Optional[str] = None
    domain_name: Optional[str] = None
    plan_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None

@dataclass
class DjangoAdminLog:
    id: Optional[int] = None
    action_time: Optional[datetime] = None
    object_id: Optional[str] = None
    object_repr: Optional[str] = None
    action_flag: Optional[int] = None
    change_message: Optional[str] = None
    content_type_id: Optional[int] = None
    user_id: Optional[int] = None
    content_type: Optional[DjangoContentType] = None
    user: Optional[UserServicesUsers] = None

@dataclass
class UserServicesUserShippingAddress:
    id: Optional[int] = None
    address_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[int] = None
    user: Optional[UserServicesUsers] = None

@dataclass
class UserServicesActivityLog:
    id: Optional[int] = None
    activity: Optional[str] = None
    activity_type: Optional[str] = None
    activity_date: Optional[datetime] = None
    activity_ip: Optional[str] = None
    activity_device: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None
    user: Optional[UserServicesUsers] = None

@dataclass
class UserServicesModules:
    id: Optional[int] = None
    module_name: Optional[str] = None
    module_icon: Optional[str] = None
    is_menu: Optional[bool] = None
    is_active: Optional[bool] = None
    module_url: Optional[str] = None
    display_order: Optional[int] = None
    module_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id_id: Optional[int] = None
    parent: Optional[UserServicesModules] = None

@dataclass
class UserServicesUserPermissions:
    id: Optional[int] = None
    is_view: Optional[bool] = None
    is_add: Optional[bool] = None
    is_edit: Optional[bool] = None
    is_delete: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    user_id: Optional[int] = None
    module: Optional[UserServicesModules] = None
    domain_user: Optional[UserServicesUsers] = None
    user: Optional[UserServicesUsers] = None

@dataclass
class UserServicesUsersGroups:
    id: Optional[int] = None
    users_id: Optional[int] = None
    group_id: Optional[int] = None
    user: Optional[UserServicesUsers] = None
    group: Optional[AuthGroup] = None

@dataclass
class UserServicesUsersUserPermissions:
    id: Optional[int] = None
    users_id: Optional[int] = None
    permission_id: Optional[int] = None
    user: Optional[UserServicesUsers] = None
    permission: Optional[AuthPermission] = None

@dataclass
class ProductServicesCategories:
    id: Optional[int] = None
    name: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    parent_id_id: Optional[int] = None
    added_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    parent: Optional[ProductServicesCategories] = None

@dataclass
class ProductServicesProducts:
    id: Optional[int] = None
    name: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    html_description: Optional[str] = None
    highlights: Optional[Dict[str, Any]] = None
    sku: Optional[str] = None
    initial_buying_price: Optional[float] = None
    initial_selling_price: Optional[float] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    uom: Optional[str] = None
    color: Optional[str] = None
    tax_percentage: Optional[float] = None
    brand: Optional[str] = None
    brand_model: Optional[str] = None
    status: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[Dict[str, Any]] = None
    addition_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    category_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    added_by_user: Optional[UserServicesUsers] = None
    category: Optional[ProductServicesCategories] = None
    domain_user: Optional[UserServicesUsers] = None

@dataclass
class ProductServicesProductQuestions:
    id: Optional[int] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    answer_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    question_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    answer_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    question_user: Optional[UserServicesUsers] = None
    product: Optional[ProductServicesProducts] = None

@dataclass
class ProductServicesProductReviews:
    id: Optional[int] = None
    review_images: Optional[Dict[str, Any]] = None
    rating: Optional[float] = None
    reviews: Optional[str] = None
    status: Optional[str] = None
    domain_user_id_id: Optional[int] = None
    review_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None
    review_user: Optional[UserServicesUsers] = None
    product: Optional[ProductServicesProducts] = None

@dataclass
class InventoryServicesWarehouse:
    id: Optional[int] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    size: Optional[str] = None
    capacity: Optional[str] = None
    warehouse_type: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_manager_id: Optional[int] = None
    added_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    warehouse_manager: Optional[UserServicesUsers] = None

@dataclass
class InventoryServicesRackAndShelvesAndFloor:
    id: Optional[int] = None
    name: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    floor: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    added_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    warehouse: Optional[InventoryServicesWarehouse] = None

@dataclass
class OrderServicePurchaseOrder:
    id: Optional[int] = None
    po_code: Optional[str] = None
    po_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    payment_status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    due_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: Optional[str] = None
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    supplier_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    approved_by_user: Optional[UserServicesUsers] = None
    cancelled_by_user: Optional[UserServicesUsers] = None
    created_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    last_updated_by_user: Optional[UserServicesUsers] = None
    received_by_user: Optional[UserServicesUsers] = None
    returned_by_user: Optional[UserServicesUsers] = None
    supplier: Optional[UserServicesUsers] = None
    updated_by_user: Optional[UserServicesUsers] = None
    warehouse: Optional[InventoryServicesWarehouse] = None

@dataclass
class OrderServicePurchaseOrderItems:
    id: Optional[int] = None
    quantity_ordered: Optional[int] = None
    quantity_received: Optional[int] = None
    quantity_cancelled: Optional[int] = None
    quantity_returned: Optional[int] = None
    buying_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    amount_returned: Optional[Decimal] = None
    amount_cancelled: Optional[Decimal] = None
    amount_ordered: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_amount: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserServicesUsers] = None
    cancelled_by_user: Optional[UserServicesUsers] = None
    created_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    last_updated_by_user: Optional[UserServicesUsers] = None
    received_by_user: Optional[UserServicesUsers] = None
    returned_by_user: Optional[UserServicesUsers] = None
    po: Optional[OrderServicePurchaseOrder] = None
    product: Optional[ProductServicesProducts] = None
    updated_by_user: Optional[UserServicesUsers] = None

@dataclass
class OrderServicePurchaseOrderLogs:
    id: Optional[int] = None
    comment: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    created_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    po: Optional[OrderServicePurchaseOrder] = None

@dataclass
class OrderServicePurchaseOrderInwardedLog:
    id: Optional[int] = None
    invoice_path: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    inwarded_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    inwarded_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None
    inwarded_by_user: Optional[UserServicesUsers] = None
    po: Optional[OrderServicePurchaseOrder] = None

@dataclass
class OrderServicePurchaseOrderItemInwardedLog:
    id: Optional[int] = None
    inwarded_quantity: Optional[int] = None
    price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    po_item_id_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None
    po_item: Optional[OrderServicePurchaseOrderItems] = None

@dataclass
class OrderServiceSalesOrder:
    id: Optional[int] = None
    so_code: Optional[str] = None
    so_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    payment_status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    due_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: Optional[str] = None
    shipping_tax_percentage: Optional[Decimal] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    received_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    customer_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    last_updated_by_user_id_id: Optional[int] = None
    received_by_user_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserServicesUsers] = None
    cancelled_by_user: Optional[UserServicesUsers] = None
    created_by_user: Optional[UserServicesUsers] = None
    customer: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    last_updated_by_user: Optional[UserServicesUsers] = None
    received_by_user: Optional[UserServicesUsers] = None
    returned_by_user: Optional[UserServicesUsers] = None
    po: Optional[OrderServicePurchaseOrder] = None
    product: Optional[ProductServicesProducts] = None
    updated_by_user: Optional[UserServicesUsers] = None

@dataclass
class OrderServiceSalesOrderOrderItems:
    id: Optional[int] = None
    quantity_ordered: Optional[int] = None
    quantity_delivered: Optional[int] = None
    quantity_shipped: Optional[int] = None
    quantity_cancelled: Optional[int] = None
    quantity_returned: Optional[int] = None
    purchase_price: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    amount_paid: Optional[Decimal] = None
    amount_returned: Optional[Decimal] = None
    amount_cancelled: Optional[Decimal] = None
    amount_ordered: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_amount: Optional[Decimal] = None
    shipping_type: Optional[str] = None
    shipping_tax_amount: Optional[Decimal] = None
    shipping_cancelled_amount: Optional[Decimal] = None
    shipping_cancelled_tax_amount: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    approved_by_user_id_id: Optional[int] = None
    cancelled_by_user_id_id: Optional[int] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    returned_by_user_id_id: Optional[int] = None
    shipped_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    updated_by_user_id_id: Optional[int] = None
    approved_by_user: Optional[UserServicesUsers] = None
    cancelled_by_user: Optional[UserServicesUsers] = None
    created_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    product: Optional[ProductServicesProducts] = None
    returned_by_user: Optional[UserServicesUsers] = None
    shipped_by_user: Optional[UserServicesUsers] = None
    so: Optional[OrderServiceSalesOrder] = None
    updated_by_user: Optional[UserServicesUsers] = None

@dataclass
class OrderServiceSalesOrderLogs:
    id: Optional[int] = None
    comment: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    created_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    so: Optional[OrderServiceSalesOrder] = None

@dataclass
class OrderServiceSalesOrderOutwardedLog:
    id: Optional[int] = None
    invoice_path: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    outwared_at: Optional[datetime] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    outwarded_by_user_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None
    outwarded_by_user: Optional[UserServicesUsers] = None
    so: Optional[OrderServiceSalesOrder] = None

@dataclass
class OrderServiceSalesOrderItemOutwardedLog:
    id: Optional[int] = None
    outwarded_quantity: Optional[int] = None
    price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discount_type: Optional[str] = None
    shipping_amount: Optional[Decimal] = None
    shipping_tax_percentage: Optional[Decimal] = None
    additional_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    domain_user_id_id: Optional[int] = None
    so_item_id_id: Optional[int] = None
    domain_user: Optional[UserServicesUsers] = None
    so_item: Optional[OrderServiceSalesOrderOrderItems] = None

@dataclass
class InventoryServicesInventory:
    id: Optional[int] = None
    quantity: Optional[int] = None
    mrp: Optional[str] = None
    batch_number: Optional[str] = None
    discount_type: Optional[str] = None
    discount_amout: Optional[float] = None
    sr_no: Optional[str] = None
    mfg_date: Optional[datetime] = None
    uom: Optional[str] = None
    ptr: Optional[str] = None
    received_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    quantity_inwarded: Optional[int] = None
    buy_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    tax_percentage: Optional[Decimal] = None
    stock_status: Optional[str] = None
    inward_type: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    product_id_id: Optional[int] = None
    purchase_order_id_id: Optional[int] = None
    purchase_order_item_id_id: Optional[int] = None
    purchase_order_item_inwarded_item_id_id: Optional[int] = None
    rack_shelf_floor_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    added_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    product: Optional[ProductServicesProducts] = None
    purchase_order: Optional[OrderServicePurchaseOrder] = None
    purchase_order_item: Optional[OrderServicePurchaseOrderItems] = None
    purchase_order_item_inwarded_item: Optional[OrderServicePurchaseOrderItemInwardedLog] = None
    rack_shelf_floor: Optional[InventoryServicesRackAndShelvesAndFloor] = None
    warehouse: Optional[InventoryServicesWarehouse] = None

@dataclass
class InventoryServicesInventoryLog:
    id: Optional[int] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    added_by_user_id_id: Optional[int] = None
    domain_user_id_id: Optional[int] = None
    inventory_id_id: Optional[int] = None
    po_id_id: Optional[int] = None
    so_id_id: Optional[int] = None
    rack_shelf_floor_id_id: Optional[int] = None
    warehouse_id_id: Optional[int] = None
    added_by_user: Optional[UserServicesUsers] = None
    domain_user: Optional[UserServicesUsers] = None
    inventory: Optional[InventoryServicesInventory] = None
    po: Optional[OrderServicePurchaseOrder] = None
    so: Optional[OrderServiceSalesOrder] = None
    rack_shelf_floor: Optional[InventoryServicesRackAndShelvesAndFloor] = None
    warehouse: Optional[InventoryServicesWarehouse] = None