from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional, Dict
import uuid

class BaseModel:
    id: int

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)

class TimestampMixin:
    created_at: datetime
    updated_at: datetime

    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None, **kwargs):
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        super().__init__(**kwargs)

class UserAwareMixin:
    added_by_user_id_id: int
    domain_user_id_id: int

    def __init__(self, added_by_user_id: int = None, domain_user_id: int = None, **kwargs):
        self.added_by_user_id_id = added_by_user_id
        self.domain_user_id_id = domain_user_id
        super().__init__(**kwargs)

class InventoryWarehouse(BaseModel):
    name: str
    address: str
    city: str
    state: str
    country: str
    pincode: str
    phone: str
    email: str
    status: str
    size: str
    capacity: str
    warehouse_type: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    warehouse_manager_id: int

    def __init__(self, name: str = "", address: str = "", city: str = "", state: str = "", country: str = "",
                 pincode: str = "", phone: str = "", email: str = "", status: str = "", size: str = "",
                 capacity: str = "", warehouse_type: str = "", additional_details: Optional[Dict] = None,
                 added_by_user_id: int = None, domain_user_id: int = None, warehouse_manager_id: int = None, **kwargs):
        super().__init__(**kwargs)
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
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.added_by_user_id_id = added_by_user_id
        self.domain_user_id_id = domain_user_id
        self.warehouse_manager_id = warehouse_manager_id

class InventoryRackAndShelvesAndFloor(BaseModel):
    name: str
    rack: str
    shelf: str
    floor: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    warehouse_id_id: int

    def __init__(self, name: str = "", rack: str = "", shelf: str = "", floor: str = "",
                 additional_details: Optional[Dict] = None,
                 added_by_user_id: int = None, domain_user_id: int = None,
                 warehouse_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details = additional_details or {}
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.added_by_user_id_id = added_by_user_id
        self.domain_user_id_id = domain_user_id
        self.warehouse_id_id = warehouse_id

class Inventory(BaseModel):
    quantity: int
    mrp: str
    batch_number: str
    discount_type: str
    discount_amout: float
    sr_no: str
    mfg_date: datetime
    uom: str
    ptr: str
    received_date: datetime
    expiry_date: datetime
    quantity_inwarded: int
    buy_price: Decimal
    sell_price: Decimal
    tax_percentage: Decimal
    stock_status: str
    inward_type: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    product_id_id: int
    purchase_order_id_id: int
    purchase_order_item_id_id: int
    purchase_order_item_inwarded_item_id_id: int
    rack_shelf_floor_id_id: int
    warehouse_id_id: int

    def __init__(self, quantity: int = 0, mrp: str = "", batch_number: str = "",
                 discount_type: str = "", discount_amout: float = 0.0, sr_no: str = "",
                 mfg_date: Optional[datetime] = None, uom: str = "", ptr: str = "",
                 received_date: Optional[datetime] = None, expiry_date: Optional[datetime] = None,
                 quantity_inwarded: int = 0, buy_price: Decimal = Decimal('0.00'),
                 sell_price: Decimal = Decimal('0.00'), tax_percentage: Decimal = Decimal('0.00'),
                 stock_status: str = "", inward_type: str = "",
                 additional_details: Optional[Dict] = None,
                 added_by_user_id: int = None, domain_user_id: int = None,
                 product_id: int = None, purchase_order_id: int = None,
                 purchase_order_item_id: int = None,
                 purchase_order_item_inwarded_item_id: int = None,
                 rack_shelf_floor_id: int = None, warehouse_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.quantity = quantity
        self.mrp = mrp
        self.batch_number = batch_number
        self.discount_type = discount_type
        self.discount_amout = discount_amout
        self.sr_no = sr_no
        self.mfg_date = mfg_date or datetime.now()
        self.uom = uom
        self.ptr = ptr
        self.received_date = received_date or datetime.now()
        self.expiry_date = expiry_date or datetime.now()
        self.quantity_inwarded = quantity_inwarded
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.tax_percentage = tax_percentage
        self.stock_status = stock_status
        self.inward_type = inward_type
        self.additional_details = additional_details or {}
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.added_by_user_id_id = added_by_user_id
        self.domain_user_id_id = domain_user_id
        self.product_id_id = product_id
        self.purchase_order_id_id = purchase_order_id
        self.purchase_order_item_id_id = purchase_order_item_id
        self.purchase_order_item_inwarded_item_id_id = purchase_order_item_inwarded_item_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id
        self.warehouse_id_id = warehouse_id

class InventoryLog(BaseModel):
    quantity: int
    status: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    inventory_id_id: int
    po_id_id: int
    so_id_id: int
    rack_shelf_floor_id_id: int
    warehouse_id_id: int

    def __init__(self, quantity: int = 0, status: str = "", additional_details: Optional[Dict] = None,
                 added_by_user_id: int = None, domain_user_id: int = None,
                 inventory_id: int = None, po_id: int = None, so_id: int = None,
                 rack_shelf_floor_id: int = None, warehouse_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.quantity = quantity
        self.status = status
        self.additional_details = additional_details or {}
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.added_by_user_id_id = added_by_user_id
        self.domain_user_id_id = domain_user_id
        self.inventory_id_id = inventory_id
        self.po_id_id = po_id
        self.so_id_id = so_id
        self.rack_shelf_floor_id_id = rack_shelf_floor_id
        self.warehouse_id_id = warehouse_id

class PurchaseOrder(BaseModel):
    po_code: str
    po_date: datetime
    expected_delivery_date: datetime
    payment_terms: str
    payment_status: str
    total_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_type: str
    shipping_tax_percentage: Decimal
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    received_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: int
    cancelled_by_user_id_id: int
    created_by_user_id_id: int
    domain_user_id_id: int
    last_updated_by_user_id_id: int
    received_by_user_id_id: int
    returned_by_user_id_id: int
    supplier_id_id: int
    updated_by_user_id_id: int
    warehouse_id_id: int

    def __init__(self, po_code: str = "", po_date: Optional[datetime] = None,
                 expected_delivery_date: Optional[datetime] = None,
                 payment_terms: str = "", payment_status: str = "",
                 total_amount: Decimal = Decimal('0.00'), paid_amount: Decimal = Decimal('0.00'),
                 due_amount: Decimal = Decimal('0.00'), discount_amount: Decimal = Decimal('0.00'),
                 discount_type: str = "", shipping_amount: Decimal = Decimal('0.00'),
                 shipping_type: str = "", shipping_tax_percentage: Decimal = Decimal('0.00'),
                 shipping_tax_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_tax_amount: Decimal = Decimal('0.00'),
                 additional_details: Optional[Dict] = None, status: str = "",
                 approved_by_user_id: int = None, cancelled_by_user_id: int = None,
                 created_by_user_id: int = None, domain_user_id: int = None,
                 last_updated_by_user_id: int = None, received_by_user_id: int = None,
                 returned_by_user_id: int = None, supplier_id: int = None,
                 updated_by_user_id: int = None, warehouse_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.po_code = po_code
        self.po_date = po_date or datetime.now()
        self.expected_delivery_date = expected_delivery_date or datetime.now()
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
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.approved_at = None
        self.cancelled_at = None
        self.cancelled_reason = None
        self.received_at = None
        self.returned_at = None
        self.approved_by_user_id_id = approved_by_user_id
        self.cancelled_by_user_id_id = cancelled_by_user_id
        self.created_by_user_id_id = created_by_user_id
        self.domain_user_id_id = domain_user_id
        self.last_updated_by_user_id_id = last_updated_by_user_id
        self.received_by_user_id_id = received_by_user_id
        self.returned_by_user_id_id = returned_by_user_id
        self.supplier_id_id = supplier_id
        self.updated_by_user_id_id = updated_by_user_id
        self.warehouse_id_id = warehouse_id

    def approve(self, user_id: int) -> None:
        if self.status != 'draft':
            raise ValueError("Only draft orders can be approved")
        self.status = 'approved'
        self.approved_at = datetime.now()
        self.approved_by_user_id_id = user_id
        self.updated_at = datetime.now()

    def cancel(self, user_id: int, reason: str) -> None:
        if self.status in ['approved', 'received']:
            raise ValueError("Already approved/received orders cannot be cancelled")
        self.status = 'cancelled'
        self.cancelled_at = datetime.now()
        self.cancelled_reason = reason
        self.cancelled_by_user_id_id = user_id
        self.updated_at = datetime.now()

    def receive(self, user_id: int) -> None:
        if self.status != 'approved':
            raise ValueError("Only approved orders can be received")
        self.status = 'received'
        self.received_at = datetime.now()
        self.received_by_user_id_id = user_id
        self.updated_at = datetime.now()

    def return_order(self, user_id: int) -> None:
        if self.status != 'received':
            raise ValueError("Only received orders can be returned")
        self.status = 'returned'
        self.returned_at = datetime.now()
        self.returned_by_user_id_id = user_id
        self.updated_at = datetime.now()

class PurchaseOrderItems(BaseModel):
    quantity_ordered: int
    quantity_received: int
    quantity_cancelled: int
    quantity_returned: int
    buying_price: Decimal
    selling_price: Decimal
    discount_amount: Decimal
    amount_paid: Decimal
    amount_returned: Decimal
    amount_cancelled: Decimal
    amount_ordered: Decimal
    tax_percentage: Decimal
    tax_amount: Decimal
    shipping_tax_percentage: Decimal
    shipping_amount: Decimal
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    discount_type: str
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    received_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: int
    cancelled_by_user_id_id: int
    created_by_user_id_id: int
    domain_user_id_id: int
    last_updated_by_user_id_id: int
    received_by_user_id_id: int
    returned_by_user_id_id: int
    po_id_id: int
    product_id_id: int
    updated_by_user_id_id: int

    def __init__(self, quantity_ordered: int = 0, quantity_received: int = 0,
                 quantity_cancelled: int = 0, quantity_returned: int = 0,
                 buying_price: Decimal = Decimal('0.00'), selling_price: Decimal = Decimal('0.00'),
                 discount_amount: Decimal = Decimal('0.00'), amount_paid: Decimal = Decimal('0.00'),
                 amount_returned: Decimal = Decimal('0.00'), amount_cancelled: Decimal = Decimal('0.00'),
                 amount_ordered: Decimal = Decimal('0.00'), tax_percentage: Decimal = Decimal('0.00'),
                 tax_amount: Decimal = Decimal('0.00'), shipping_tax_percentage: Decimal = Decimal('0.00'),
                 shipping_amount: Decimal = Decimal('0.00'), shipping_tax_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_tax_amount: Decimal = Decimal('0.00'),
                 discount_type: str = "", additional_details: Optional[Dict] = None, status: str = "",
                 approved_by_user_id: int = None, cancelled_by_user_id: int = None,
                 created_by_user_id: int = None, domain_user_id: int = None,
                 last_updated_by_user_id: int = None, received_by_user_id: int = None,
                 returned_by_user_id: int = None, po_id: int = None, product_id: int = None,
                 updated_by_user_id: int = None, **kwargs):
        super().__init__(**kwargs)
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
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.approved_at = None
        self.cancelled_at = None
        self.cancelled_reason = None
        self.received_at = None
        self.returned_at = None
        self.approved_by_user_id_id = approved_by_user_id
        self.cancelled_by_user_id_id = cancelled_by_user_id
        self.created_by_user_id_id = created_by_user_id
        self.domain_user_id_id = domain_user_id
        self.last_updated_by_user_id_id = last_updated_by_user_id
        self.received_by_user_id_id = received_by_user_id
        self.returned_by_user_id_id = returned_by_user_id
        self.po_id_id = po_id
        self.product_id_id = product_id
        self.updated_by_user_id_id = updated_by_user_id

class PurchaseOrderLogs(BaseModel):
    comment: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by_user_id_id: int
    domain_user_id_id: int
    po_id_id: int

    def __init__(self, comment: str = "", additional_details: Optional[Dict] = None,
                 created_by_user_id: int = None, domain_user_id: int = None,
                 po_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.comment = comment
        self.additional_details = additional_details or {}
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.created_by_user_id_id = created_by_user_id
        self.domain_user_id_id = domain_user_id
        self.po_id_id = po_id

class PurchaseOrderInwardedLog(BaseModel):
    invoice_path: str
    invoice_number: str
    notes: str
    inwarded_at: datetime
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    inwarded_by_user_id_id: int
    po_id_id: int

    def __init__(self, invoice_path: str = "", invoice_number: str = "", notes: str = "",
                 inwarded_at: Optional[datetime] = None, additional_details: Optional[Dict] = None,
                 status: str = "", domain_user_id: int = None, inwarded_by_user_id: int = None,
                 po_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at or datetime.now()
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.domain_user_id_id = domain_user_id
        self.inwarded_by_user_id_id = inwarded_by_user_id
        self.po_id_id = po_id

class PurchaseOrderItemInwardedLog(BaseModel):
    inwarded_quantity: int
    price: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_tax_percentage: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    po_item_id_id: int

    def __init__(self, inwarded_quantity: int = 0, price: Decimal = Decimal('0.00'),
                 tax_percentage: Decimal = Decimal('0.00'), discount_amount: Decimal = Decimal('0.00'),
                 discount_type: str = "", shipping_amount: Decimal = Decimal('0.00'),
                 shipping_tax_percentage: Decimal = Decimal('0.00'),
                 additional_details: Optional[Dict] = None, status: str = "",
                 domain_user_id: int = None, po_item_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.inwarded_quantity = inwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.domain_user_id_id = domain_user_id
        self.po_item_id_id = po_item_id

class SalesOrder(BaseModel):
    so_code: str
    so_date: datetime
    expected_delivery_date: datetime
    payment_terms: str
    payment_status: str
    total_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_type: str
    shipping_tax_percentage: Decimal
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    received_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: int
    cancelled_by_user_id_id: int
    created_by_user_id_id: int
    customer_id_id: int
    domain_user_id_id: int
    last_updated_by_user_id_id: int
    received_by_user_id_id: int
    returned_by_user_id_id: int
    po_id_id: int
    product_id_id: int
    updated_by_user_id_id: int

    def __init__(self, so_code: str = "", so_date: Optional[datetime] = None,
                 expected_delivery_date: Optional[datetime] = None,
                 payment_terms: str = "", payment_status: str = "",
                 total_amount: Decimal = Decimal('0.00'), paid_amount: Decimal = Decimal('0.00'),
                 due_amount: Decimal = Decimal('0.00'), discount_amount: Decimal = Decimal('0.00'),
                 discount_type: str = "", shipping_amount: Decimal = Decimal('0.00'),
                 shipping_type: str = "", shipping_tax_percentage: Decimal = Decimal('0.00'),
                 shipping_tax_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_tax_amount: Decimal = Decimal('0.00'),
                 additional_details: Optional[Dict] = None, status: str = "",
                 approved_by_user_id: int = None, cancelled_by_user_id: int = None,
                 created_by_user_id: int = None, customer_id: int = None,
                 domain_user_id: int = None, last_updated_by_user_id: int = None,
                 received_by_user_id: int = None, returned_by_user_id: int = None,
                 po_id: int = None, product_id: int = None,
                 updated_by_user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.so_code = so_code
        self.so_date = so_date or datetime.now()
        self.expected_delivery_date = expected_delivery_date or datetime.now()
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
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.approved_at = None
        self.cancelled_at = None
        self.cancelled_reason = None
        self.received_at = None
        self.returned_at = None
        self.approved_by_user_id_id = approved_by_user_id
        self.cancelled_by_user_id_id = cancelled_by_user_id
        self.created_by_user_id_id = created_by_user_id
        self.customer_id_id = customer_id
        self.domain_user_id_id = domain_user_id
        self.last_updated_by_user_id_id = last_updated_by_user_id
        self.received_by_user_id_id = received_by_user_id
        self.returned_by_user_id_id = returned_by_user_id
        self.po_id_id = po_id
        self.product_id_id = product_id
        self.updated_by_user_id_id = updated_by_user_id

    def approve(self, user_id: int) -> None:
        if self.status != 'draft':
            raise ValueError("Only draft orders can be approved")
        self.status = 'approved'
        self.approved_at = datetime.now()
        self.approved_by_user_id_id = user_id
        self.updated_at = datetime.now()

    def cancel(self, user_id: int, reason: str) -> None:
        if self.status in ['approved', 'shipped']:
            raise ValueError("Cannot cancel approved/shipped orders")
        self.status = 'cancelled'
        self.cancelled_at = datetime.now()
        self.cancelled_reason = reason
        self.cancelled_by_user_id_id = user_id
        self.updated_at = datetime.now()

    def receive(self, user_id: int) -> None:
        if self.status != 'shipped':
            raise ValueError("Only shipped orders can be received")
        self.status = 'received'
        self.received_at = datetime.now()
        self.received_by_user_id_id = user_id
        self.updated_at = datetime.now()

    def return_order(self, user_id: int) -> None:
        if self.status != 'received':
            raise ValueError("Only received orders can be returned")
        self.status = 'returned'
        self.returned_at = datetime.now()
        self.returned_by_user_id_id = user_id
        self.updated_at = datetime.now()

class SalesOrderOrderItems(BaseModel):
    quantity_ordered: int
    quantity_delivered: int
    quantity_shipped: int
    quantity_cancelled: int
    quantity_returned: int
    purchase_price: Decimal
    discount_amount: Decimal
    discount_type: str
    amount_paid: Decimal
    amount_returned: Decimal
    amount_cancelled: Decimal
    amount_ordered: Decimal
    tax_percentage: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    shipping_type: str
    shipping_tax_amount: Decimal
    shipping_cancelled_amount: Decimal
    shipping_cancelled_tax_amount: Decimal
    discount_type: str
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    shipped_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_user_id_id: int
    cancelled_by_user_id_id: int
    created_by_user_id_id: int
    domain_user_id_id: int
    product_id_id: int
    returned_by_user_id_id: int
    shipped_by_user_id_id: int
    so_id_id: int
    updated_by_user_id_id: int

    def __init__(self, quantity_ordered: int = 0, quantity_delivered: int = 0,
                 quantity_shipped: int = 0, quantity_cancelled: int = 0,
                 quantity_returned: int = 0, purchase_price: Decimal = Decimal('0.00'),
                 discount_amount: Decimal = Decimal('0.00'), discount_type: str = "",
                 amount_paid: Decimal = Decimal('0.00'), amount_returned: Decimal = Decimal('0.00'),
                 amount_cancelled: Decimal = Decimal('0.00'), amount_ordered: Decimal = Decimal('0.00'),
                 tax_percentage: Decimal = Decimal('0.00'), tax_amount: Decimal = Decimal('0.00'),
                 shipping_amount: Decimal = Decimal('0.00'), shipping_type: str = "",
                 shipping_tax_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_amount: Decimal = Decimal('0.00'),
                 shipping_cancelled_tax_amount: Decimal = Decimal('0.00'),
                 additional_details: Optional[Dict] = None, status: str = "",
                 approved_by_user_id: int = None, cancelled_by_user_id: int = None,
                 created_by_user_id: int = None, domain_user_id: int = None,
                 product_id: int = None, returned_by_user_id: int = None,
                 shipped_by_user_id: int = None, so_id: int = None,
                 updated_by_user_id: int = None, **kwargs):
        super().__init__(**kwargs)
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
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.approved_at = None
        self.cancelled_at = None
        self.cancelled_reason = None
        self.shipped_at = None
        self.returned_at = None
        self.approved_by_user_id_id = approved_by_user_id
        self.cancelled_by_user_id_id = cancelled_by_user_id
        self.created_by_user_id_id = created_by_user_id
        self.domain_user_id_id = domain_user_id
        self.product_id_id = product_id
        self.returned_by_user_id_id = returned_by_user_id
        self.shipped_by_user_id_id = shipped_by_user_id
        self.so_id_id = so_id
        self.updated_by_user_id_id = updated_by_user_id

class SalesOrderLogs(BaseModel):
    comment: str
    additional_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by_user_id_id: int
    domain_user_id_id: int
    so_id_id: int

    def __init__(self, comment: str = "", additional_details: Optional[Dict] = None,
                 created_by_user_id: int = None, domain_user_id: int = None,
                 so_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.comment = comment
        self.additional_details = additional_details or {}
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.created_by_user_id_id = created_by_user_id
        self.domain_user_id_id = domain_user_id
        self.so_id_id = so_id

class SalesOrderOutwardedLog(BaseModel):
    invoice_path: str
    invoice_number: str
    notes: str
    outwared_at: datetime
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    outwarded_by_user_id_id: int
    so_id_id: int

    def __init__(self, invoice_path: str = "", invoice_number: str = "", notes: str = "",
                 outwared_at: Optional[datetime] = None, additional_details: Optional[Dict] = None,
                 status: str = "", domain_user_id: int = None,
                 outwarded_by_user_id: int = None, so_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at or datetime.now()
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.domain_user_id_id = domain_user_id
        self.outwarded_by_user_id_id = outwarded_by_user_id
        self.so_id_id = so_id

class SalesOrderItemOutwardedLog(BaseModel):
    outwarded_quantity: int
    price: Decimal
    tax_percentage: Decimal
    discount_amount: Decimal
    discount_type: str
    shipping_amount: Decimal
    shipping_tax_percentage: Decimal
    additional_details: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    so_item_id_id: int

    def __init__(self, outwarded_quantity: int = 0, price: Decimal = Decimal('0.00'),
                 tax_percentage: Decimal = Decimal('0.00'), discount_amount: Decimal = Decimal('0.00'),
                 discount_type: str = "", shipping_amount: Decimal = Decimal('0.00'),
                 shipping_tax_percentage: Decimal = Decimal('0.00'),
                 additional_details: Optional[Dict] = None, status: str = "",
                 domain_user_id: int = None, so_item_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.outwarded_quantity = outwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details = additional_details or {}
        self.status = status
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.domain_user_id_id = domain_user_id
        self.so_item_id_id = so_item_id

class Categories(BaseModel):
    name: str
    image: str
    description: str
    display_order: int
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    domain_user_id_id: int
    parent_id_id: int

    def __init__(self, name: str = "", image: str = "", description: str = "",
                 display_order: int = 0, added_by_user_id: int = None,
                 domain_user_id: int = None, parent_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.added_by_user_id_id = added_by_user_id
        self.domain_user_id_id = domain_user_id
        self.parent_id_id = parent_id

class Products(BaseModel):
    name: str
    image: Dict[str, Any]
    description: str
    specifications: Dict[str, Any]
    html_description: str
    highlights: Dict[str, Any]
    sku: str
    initial_buying_price: float
    initial_selling_price: float
    weight: float
    dimensions: str
    uom: str
    color: str
    tax_percentage: float
    brand: str
    brand_model: str
    status: str
    seo_title: str
    seo_description: str
    seo_keywords: Dict[str, Any]
    addition_details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    added_by_user_id_id: int
    category_id_id: int
    domain_user_id_id: int

    def __init__(self, name: str = "", image: Optional[Dict] = None,
                 description: str = "", specifications: Optional[Dict] = None,
                 html_description: str = "", highlights: Optional[Dict] = None,
                 sku: str = "", initial_buying_price: float = 0.0,
                 initial_selling_price: float = 0.0, weight: float = 0.0,
                 dimensions: str = "", uom: str = "", color: str = "",
                 tax_percentage: float = 0.0, brand: str = "", brand_model: str = "",
                 status: str = "", seo_title: str = "", seo_description: str = "",
                 seo_keywords: Optional[Dict] = None, addition_details: Optional[Dict] = None,
                 added_by_user_id: int = None, category_id: int = None,
                 domain_user_id: int = None, **kwargs):
        super().__init__(**kwargs)
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
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.added_by_user_id_id = added_by_user_id
        self.category_id_id = category_id
        self.domain_user_id_id = domain_user_id

class ProductQuestions(BaseModel):
    question: str
    answer: str
    status: str
    created_at: datetime
    updated_at: datetime
    answer_user_id_id: int
    domain_user_id_id: int
    question_user_id_id: int
    product_id_id: int

    def __init__(self, question: str = "", answer: str = "", status: str = "",
                 answer_user_id: int = None, domain_user_id: int = None,
                 question_user_id: int = None, product_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.answer_user_id_id = answer_user_id
        self.domain_user_id_id = domain_user_id
        self.question_user_id_id = question_user_id
        self.product_id_id = product_id

class ProductReviews(BaseModel):
    review_images: Dict[str, Any]
    rating: float
    reviews: str
    status: str
    domain_user_id_id: int
    review_user_id_id: int
    product_id_id: int

    def __init__(self, review_images: Optional[Dict] = None, rating: float = 0.0,
                 reviews: str = "", status: str = "", domain_user_id: int = None,
                 review_user_id: int = None, product_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.review_images = review_images or {}
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user_id_id = domain_user_id
        self.review_user_id_id = review_user_id
        self.product_id_id = product_id

class Users(BaseModel):
    is_superuser: bool
    first_name: str
    last_name: str
    is_staff: bool
    is_active: bool
    date_joined: datetime
    name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    profile_pic: str
    account_status: str
    role: str
    dob: date
    username: str
    password: str
    social_media_links: Dict[str, Any]
    addition_details: Dict[str, Any]
    language: str
    departMent: str
    designation: str
    time_zone: str
    last_login: datetime
    last_device: str
    last_ip: str
    currency: str
    domain_name: str
    plan_type: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int

    def __init__(self, is_superuser: bool = False, first_name: str = "", last_name: str = "",
                 is_staff: bool = False, is_active: bool = True,
                 date_joined: Optional[datetime] = None, name: str = "", email: str = "",
                 phone: str = "", address: str = "", city: str = "", state: str = "",
                 pincode: str = "", country: str = "", profile_pic: str = "",
                 account_status: str = "", role: str = "", dob: Optional[date] = None,
                 username: str = "", password: str = "", social_media_links: Optional[Dict] = None,
                 addition_details: Optional[Dict] = None, language: str = "",
                 departMent: str = "", designation: str = "", time_zone: str = "",
                 last_login: Optional[datetime] = None, last_device: str = "", last_ip: str = "",
                 currency: str = "", domain_name: str = "", plan_type: str = "",
                 domain_user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.is_superuser = is_superuser
        self.first_name = first_name
        self.last_name = last_name
        self.is_staff = is_staff
        self.is_active = is_active
        self.date_joined = date_joined or datetime.now()
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
        self.dob = dob or date.today()
        self.username = username
        self.password = password
        self.social_media_links = social_media_links or {}
        self.addition_details = addition_details or {}
        self.language = language
        self.departMent = departMent
        self.designation = designation
        self.time_zone = time_zone
        self.last_login = last_login or datetime.now()
        self.last_device = last_device
        self.last_ip = last_ip
        self.currency = currency
        self.domain_name = domain_name
        self.plan_type = plan_type
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.domain_user_id_id = domain_user_id

class UserShippingAddress(BaseModel):
    address_type: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    created_at: datetime
    updated_at: datetime
    user_id: int

    def __init__(self, address_type: str = "", address: str = "", city: str = "",
                 state: str = "", pincode: str = "", country: str = "",
                 user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.user_id = user_id

class ActivityLog(BaseModel):
    activity: str
    activity_type: str
    activity_date: datetime
    activity_ip: str
    activity_device: str
    created_at: datetime
    updated_at: datetime
    domain_user_id_id: int
    user_id: int

    def __init__(self, activity: str = "", activity_type: str = "",
                 activity_date: Optional[datetime] = None, activity_ip: str = "",
                 activity_device: str = "", domain_user_id: int = None,
                 user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date or datetime.now()
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.domain_user_id_id = domain_user_id
        self.user_id = user_id

class Modules(BaseModel):
    module_name: str
    module_icon: str
    is_menu: bool
    is_active: bool
    module_url: str
    display_order: int
    module_description: str
    created_at: datetime
    updated_at: datetime
    parent_id_id: int

    def __init__(self, module_name: str = "", module_icon: str = "", is_menu: bool = False,
                 is_active: bool = True, module_url: str = "", display_order: int = 0,
                 module_description: str = "", parent_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.module_name = module_name
        self.module_icon = module_icon
        self.is_menu = is_menu
        self.is_active = is_active
        self.module_url = module_url
        self.display_order = display_order
        self.module_description = module_description
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.parent_id_id = parent_id

class UserPermissions(BaseModel):
    is_view: bool
    is_add: bool
    is_edit: bool
    is_delete: bool
    created_at: datetime
    updated_at: datetime
    module_id_id: int
    domain_user_id_id: int
    user_id: int

    def __init__(self, is_view: bool = False, is_add: bool = False, is_edit: bool = False,
                 is_delete: bool = False, module_id: int = None,
                 domain_user_id: int = None, user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.module_id_id = module_id
        self.domain_user_id_id = domain_user_id
        self.user_id = user_id

class Users_Groups(BaseModel):
    users_id: int
    group_id: int

    def __init__(self, users_id: int = None, group_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.users_id = users_id
        self.group_id = group_id

class Users_User_Permissions(BaseModel):
    users_id: int
    permission_id: int

    def __init__(self, users_id: int = None, permission_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.users_id = users_id
        self.permission_id = permission_id

# Django framework entities

class DjangoContentType(BaseModel):
    app_label: str
    model: str

    def __init__(self, app_label: str = "", model: str = "", **kwargs):
        super().__init__(**kwargs)
        self.app_label = app_label
        self.model = model

class DjangoSession(BaseModel):
    session_key: str
    session_data: str
    expire_date: datetime

    def __init__(self, session_key: str = "", session_data: str = "",
                 expire_date: Optional[datetime] = None, **kwargs):
        super().__init__(**kwargs)
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date or datetime.now()

class DjangoAdminLog(BaseModel):
    action_time: datetime
    object_id: str
    object_repr: str
    action_flag: int
    change_message: str
    content_type_id: int
    user_id: int

    def __init__(self, action_time: Optional[datetime] = None, object_id: str = "",
                 object_repr: str = "", action_flag: int = 0, change_message: str = "",
                 content_type_id: int = None, user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.action_time = action_time or datetime.now()
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type_id = content_type_id
        self.user_id = user_id

class DjangoMigrations(BaseModel):
    app: str
    name: str
    applied: datetime

    def __init__(self, app: str = "", name: str = "", applied: Optional[datetime] = None, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.name = name
        self.applied = applied or datetime.now()

class AuthGroup(BaseModel):
    name: str

    def __init__(self, name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.name = name

class AuthPermission(BaseModel):
    name: str
    codename: str
    content_type_id: int

    def __init__(self, name: str = "", codename: str = "", content_type_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.codename = codename
        self.content_type_id = content_type_id

class AuthGroupPermissions(BaseModel):
    group_id: int
    permission_id: int

    def __init__(self, group_id: int = None, permission_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.group_id = group_id
        self.permission_id = permission_id