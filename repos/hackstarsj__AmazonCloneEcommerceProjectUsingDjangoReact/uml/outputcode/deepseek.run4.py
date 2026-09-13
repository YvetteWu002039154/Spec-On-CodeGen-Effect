from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any

class Inventory:
    def __init__(
        self,
        id: Optional[int] = None,
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
        buy_price: Decimal = Decimal("0.00"),
        sell_price: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        stock_status: str = "",
        inward_type: str = "",
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
        warehouse_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<Inventory id={self.id} quantity={self.quantity}>"


class InventoryLog:
    def __init__(
        self,
        id: Optional[int] = None,
        quantity: int = 0,
        status: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        inventory_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
        rack_shelf_floor_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<InventoryLog id={self.id} status={self.status}>"


class RackAndShelvesAndFloor:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        rack: str = "",
        shelf: str = "",
        floor: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<RackAndShelvesAndFloor id={self.id} name={self.name}>"


class Warehouse:
    def __init__(
        self,
        id: Optional[int] = None,
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
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        warehouse_manager_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<Warehouse id={self.id} name={self.name}>"


class PurchaseOrder:
    def __init__(
        self,
        id: Optional[int] = None,
        po_code: str = "",
        po_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Decimal = Decimal("0.00"),
        paid_amount: Decimal = Decimal("0.00"),
        due_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_type: str = "",
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
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
        warehouse_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<PurchaseOrder id={self.id} po_code={self.po_code}>"


class PurchaseOrderItem:
    def __init__(
        self,
        id: Optional[int] = None,
        quantity_ordered: int = 0,
        quantity_received: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        buying_price: Decimal = Decimal("0.00"),
        selling_price: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        amount_paid: Decimal = Decimal("0.00"),
        amount_returned: Decimal = Decimal("0.00"),
        amount_cancelled: Decimal = Decimal("0.00"),
        amount_ordered: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        tax_amount: Decimal = Decimal("0.00"),
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
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
        updated_by_user_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<PurchaseOrderItem id={self.id} po_id={self.po_id_id}>"


class PurchaseOrderLog:
    def __init__(
        self,
        id: Optional[int] = None,
        comment: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
    ):
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.po_id_id = po_id_id

    def __repr__(self):
        return f"<PurchaseOrderLog id={self.id} po_id={self.po_id_id}>"


class PurchaseOrderInwardedLog:
    def __init__(
        self,
        id: Optional[int] = None,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        inwarded_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        inwarded_by_user_id_id: Optional[int] = None,
        po_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<PurchaseOrderInwardedLog id={self.id} po_id={self.po_id_id}>"


class PurchaseOrderItemInwardedLog:
    def __init__(
        self,
        id: Optional[int] = None,
        inwarded_quantity: int = 0,
        price: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        po_item_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<PurchaseOrderItemInwardedLog id={self.id} po_item_id={self.po_item_id_id}>"


class SalesOrder:
    def __init__(
        self,
        id: Optional[int] = None,
        so_code: str = "",
        so_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        payment_terms: str = "",
        payment_status: str = "",
        total_amount: Decimal = Decimal("0.00"),
        paid_amount: Decimal = Decimal("0.00"),
        due_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_type: str = "",
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
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
        updated_by_user_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<SalesOrder id={self.id} so_code={self.so_code}>"


class SalesOrderItem:
    def __init__(
        self,
        id: Optional[int] = None,
        quantity_ordered: int = 0,
        quantity_delivered: int = 0,
        quantity_shipped: int = 0,
        quantity_cancelled: int = 0,
        quantity_returned: int = 0,
        purchase_price: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        amount_paid: Decimal = Decimal("0.00"),
        amount_returned: Decimal = Decimal("0.00"),
        amount_cancelled: Decimal = Decimal("0.00"),
        amount_ordered: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        tax_amount: Decimal = Decimal("0.00"),
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_type: str = "",
        shipping_tax_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_amount: Decimal = Decimal("0.00"),
        shipping_cancelled_tax_amount: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: str = "",
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
        updated_by_user_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<SalesOrderItem id={self.id} so_id={self.so_id_id}>"


class SalesOrderLog:
    def __init__(
        self,
        id: Optional[int] = None,
        comment: str = "",
        additional_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
    ):
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user_id_id = created_by_user_id_id
        self.domain_user_id_id = domain_user_id_id
        self.so_id_id = so_id_id

    def __repr__(self):
        return f"<SalesOrderLog id={self.id} so_id={self.so_id_id}>"


class SalesOrderOutwardedLog:
    def __init__(
        self,
        id: Optional[int] = None,
        invoice_path: str = "",
        invoice_number: str = "",
        notes: str = "",
        outwared_at: Optional[datetime] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        outwarded_by_user_id_id: Optional[int] = None,
        so_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<SalesOrderOutwardedLog id={self.id} so_id={self.so_id_id}>"


class SalesOrderItemOutwardedLog:
    def __init__(
        self,
        id: Optional[int] = None,
        outwarded_quantity: int = 0,
        price: Decimal = Decimal("0.00"),
        tax_percentage: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        discount_type: str = "",
        shipping_amount: Decimal = Decimal("0.00"),
        shipping_tax_percentage: Decimal = Decimal("0.00"),
        additional_details: Optional[Dict[str, Any]] = None,
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        so_item_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<SalesOrderItemOutwardedLog id={self.id} so_item_id={self.so_item_id_id}>"


class Category:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        image: str = "",
        description: str = "",
        display_order: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        parent_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"


class Product:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        image: Optional[Dict[str, Any]] = None,
        description: str = "",
        specifications: Optional[Dict[str, Any]] = None,
        html_description: str = "",
        highlights: Optional[Dict[str, Any]] = None,
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
        seo_keywords: Optional[Dict[str, Any]] = None,
        addition_details: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user_id_id: Optional[int] = None,
        category_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<Product id={self.id} name={self.name}>"


class ProductQuestion:
    def __init__(
        self,
        id: Optional[int] = None,
        question: str = "",
        answer: str = "",
        status: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        answer_user_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        question_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<ProductQuestion id={self.id} product_id={self.product_id_id}>"


class ProductReview:
    def __init__(
        self,
        id: Optional[int] = None,
        review_images: Optional[Dict[str, Any]] = None,
        rating: float = 0.0,
        reviews: str = "",
        status: str = "",
        domain_user_id_id: Optional[int] = None,
        review_user_id_id: Optional[int] = None,
        product_id_id: Optional[int] = None,
    ):
        self.id = id
        self.review_images = review_images
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user_id_id = domain_user_id_id
        self.review_user_id_id = review_user_id_id
        self.product_id_id = product_id_id

    def __repr__(self):
        return f"<ProductReview id={self.id} product_id={self.product_id_id}>"


class User:
    def __init__(
        self,
        id: Optional[int] = None,
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
        social_media_links: Optional[Dict[str, Any]] = None,
        addition_details: Optional[Dict[str, Any]] = None,
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

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class UserShippingAddress:
    def __init__(
        self,
        id: Optional[int] = None,
        address_type: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        pincode: str = "",
        country: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        user_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<UserShippingAddress id={self.id} user_id={self.user_id}>"


class ActivityLog:
    def __init__(
        self,
        id: Optional[int] = None,
        activity: str = "",
        activity_type: str = "",
        activity_date: Optional[datetime] = None,
        activity_ip: str = "",
        activity_device: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<ActivityLog id={self.id} user_id={self.user_id}>"


class Module:
    def __init__(
        self,
        id: Optional[int] = None,
        module_name: str = "",
        module_icon: str = "",
        is_menu: bool = True,
        is_active: bool = True,
        module_url: str = "",
        display_order: int = 0,
        module_description: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        parent_id_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<Module id={self.id} name={self.module_name}>"


class UserPermission:
    def __init__(
        self,
        id: Optional[int] = None,
        is_view: bool = False,
        is_add: bool = False,
        is_edit: bool = False,
        is_delete: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        module_id_id: Optional[int] = None,
        domain_user_id_id: Optional[int] = None,
        user_id: Optional[int] = None,
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

    def __repr__(self):
        return f"<UserPermission id={self.id} user_id={self.user_id}>"


class UserGroup:
    def __init__(
        self,
        id: Optional[int] = None,
        users_id: Optional[int] = None,
        group_id: Optional[int] = None,
    ):
        self.id = id
        self.users_id = users_id
        self.group_id = group_id

    def __repr__(self):
        return f"<UserGroup id={self.id} user_id={self.users_id} group_id={self.group_id}>"


class UserUserPermission:
    def __init__(
        self,
        id: Optional[int] = None,
        users_id: Optional[int] = None,
        permission_id: Optional[int] = None,
    ):
        self.id = id
        self.users_id = users_id
        self.permission_id = permission_id

    def __repr__(self):
        return f"<UserUserPermission id={self.id} user_id={self.users_id} perm_id={self.permission_id}>"


class DjangoAdminLog:
    def __init__(
        self,
        id: Optional[int] = None,
        action_time: Optional[datetime] = None,
        object_id: str = "",
        object_repr: str = "",
        action_flag: int = 0,
        change_message: str = "",
        content_type_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ):
        self.id = id
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type_id = content_type_id
        self.user_id = user_id

    def __repr__(self):
        return f"<DjangoAdminLog id={self.id} user_id={self.user_id}>"


class DjangoMigrations:
    def __init__(
        self,
        id: Optional[int] = None,
        app: str = "",
        name: str = "",
        applied: Optional[datetime] = None,
    ):
        self.id = id
        self.app = app
        self.name = name
        self.applied = applied

    def __repr__(self):
        return f"<DjangoMigrations id={self.id} app={self.app} name={self.name}>"


class DjangoContentType:
    def __init__(
        self,
        id: Optional[int] = None,
        app_label: str = "",
        model: str = "",
    ):
        self.id = id
        self.app_label = app_label
        self.model = model

    def __repr__(self):
        return f"<DjangoContentType id={self.id} app_label={self.app_label} model={self.model}>"


class DjangoSession:
    def __init__(
        self,
        session_key: str = "",
        session_data: str = "",
        expire_date: Optional[datetime] = None,
    ):
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date

    def __repr__(self):
        return f"<DjangoSession key={self.session_key}>"


class AuthGroup:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
    ):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"<AuthGroup id={self.id} name={self.name}>"


class AuthGroupPermission:
    def __init__(
        self,
        id: Optional[int] = None,
        group_id: Optional[int] = None,
        permission_id: Optional[int] = None,
    ):
        self.id = id
        self.group_id = group_id
        self.permission_id = permission_id

    def __repr__(self):
        return f"<AuthGroupPermission id={self.id} group_id={self.group_id} perm_id={self.permission_id}>"


class AuthPermission:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        codename: str = "",
        content_type_id: Optional[int] = None,
    ):
        self.id = id
        self.name = name
        self.codename = codename
        self.content_type_id = content_type_id

    def __repr__(self):
        return f"<AuthPermission id={self.id} name={self.name}>"