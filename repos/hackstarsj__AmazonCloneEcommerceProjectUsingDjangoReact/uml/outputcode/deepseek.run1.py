from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional


class Inventory:
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
        additional_details: dict,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: User,
        domain_user: User,
        product: Product,
        purchase_order: PurchaseOrder,
        purchase_order_item: PurchaseOrderItem,
        purchase_order_item_inwarded_item: PurchaseOrderItemInwardedLog,
        rack_shelf_floor: RackAndShelvesAndFloor,
        warehouse: Warehouse,
    ) -> None:
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
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.product = product
        self.purchase_order = purchase_order
        self.purchase_order_item = purchase_order_item
        self.purchase_order_item_inwarded_item = purchase_order_item_inwarded_item
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f'Inventory(id={self.id})'


class InventoryLog:
    def __init__(
        self,
        id: int,
        quantity: int,
        status: str,
        additional_details: dict,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: User,
        domain_user: User,
        inventory: Inventory,
        po: Optional[PurchaseOrder],
        so: Optional[SalesOrder],
        rack_shelf_floor: RackAndShelvesAndFloor,
        warehouse: Warehouse,
    ) -> None:
        self.id = id
        self.quantity = quantity
        self.status = status
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.inventory = inventory
        self.po = po
        self.so = so
        self.rack_shelf_floor = rack_shelf_floor
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f'InventoryLog(id={self.id})'


class RackAndShelvesAndFloor:
    def __init__(
        self,
        id: int,
        name: str,
        rack: str,
        shelf: str,
        floor: str,
        additional_details: dict,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: User,
        domain_user: User,
        warehouse: Warehouse,
    ) -> None:
        self.id = id
        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse = warehouse

    def __repr__(self) -> str:
        return f'RackAndShelvesAndFloor(id={self.id})'


class Warehouse:
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
        additional_details: dict,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: User,
        domain_user: User,
        warehouse_manager: User,
    ) -> None:
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
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.warehouse_manager = warehouse_manager

    def __repr__(self) -> str:
        return f'Warehouse(id={self.id})'


class PurchaseOrder:
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
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: datetime,
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[User],
        cancelled_by_user: Optional[User],
        created_by_user: User,
        domain_user: User,
        last_updated_by_user: User,
        received_by_user: Optional[User],
        returned_by_user: Optional[User],
        supplier: User,
        updated_by_user: User,
        warehouse: Warehouse,
    ) -> None:
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

    def __repr__(self) -> str:
        return f'PurchaseOrder(id={self.id})'


class PurchaseOrderItem:
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
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[User],
        cancelled_by_user: Optional[User],
        created_by_user: User,
        domain_user: User,
        last_updated_by_user: User,
        received_by_user: Optional[User],
        returned_by_user: Optional[User],
        po: PurchaseOrder,
        product: Product,
        updated_by_user: User,
    ) -> None:
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

    def __repr__(self) -> str:
        return f'PurchaseOrderItem(id={self.id})'


class PurchaseOrderLog:
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: dict,
        created_at: datetime,
        updated_at: datetime,
        created_by_user: User,
        domain_user: User,
        po: PurchaseOrder,
    ) -> None:
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.po = po

    def __repr__(self) -> str:
        return f'PurchaseOrderLog(id={self.id})'


class PurchaseOrderInwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        inwarded_at: datetime,
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: User,
        inwarded_by_user: User,
        po: PurchaseOrder,
    ) -> None:
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.inwarded_by_user = inwarded_by_user
        self.po = po

    def __repr__(self) -> str:
        return f'PurchaseOrderInwardedLog(id={self.id})'


class PurchaseOrderItemInwardedLog:
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
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: User,
        po_item: PurchaseOrderItem,
    ) -> None:
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
        self.domain_user = domain_user
        self.po_item = po_item

    def __repr__(self) -> str:
        return f'PurchaseOrderItemInwardedLog(id={self.id})'


class SalesOrder:
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
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        received_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[User],
        cancelled_by_user: Optional[User],
        created_by_user: User,
        customer: User,
        domain_user: User,
        last_updated_by_user: User,
        received_by_user: Optional[User],
        returned_by_user: Optional[User],
        po: Optional[PurchaseOrder],
        product: Optional[Product],
        updated_by_user: User,
    ) -> None:
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

    def __repr__(self) -> str:
        return f'SalesOrder(id={self.id})'


class SalesOrderItem:
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
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        approved_at: Optional[datetime],
        cancelled_at: Optional[datetime],
        cancelled_reason: Optional[str],
        shipped_at: Optional[datetime],
        returned_at: Optional[datetime],
        approved_by_user: Optional[User],
        cancelled_by_user: Optional[User],
        created_by_user: User,
        domain_user: User,
        product: Product,
        returned_by_user: Optional[User],
        shipped_by_user: Optional[User],
        so: SalesOrder,
        updated_by_user: User,
    ) -> None:
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
        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.product = product
        self.returned_by_user = returned_by_user
        self.shipped_by_user = shipped_by_user
        self.so = so
        self.updated_by_user = updated_by_user

    def __repr__(self) -> str:
        return f'SalesOrderItem(id={self.id})'


class SalesOrderLog:
    def __init__(
        self,
        id: int,
        comment: str,
        additional_details: dict,
        created_at: datetime,
        updated_at: datetime,
        created_by_user: User,
        domain_user: User,
        so: SalesOrder,
    ) -> None:
        self.id = id
        self.comment = comment
        self.additional_details = additional_details
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by_user = created_by_user
        self.domain_user = domain_user
        self.so = so

    def __repr__(self) -> str:
        return f'SalesOrderLog(id={self.id})'


class SalesOrderOutwardedLog:
    def __init__(
        self,
        id: int,
        invoice_path: str,
        invoice_number: str,
        notes: str,
        outwared_at: datetime,
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: User,
        outwarded_by_user: User,
        so: SalesOrder,
    ) -> None:
        self.id = id
        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at
        self.additional_details = additional_details
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.outwarded_by_user = outwarded_by_user
        self.so = so

    def __repr__(self) -> str:
        return f'SalesOrderOutwardedLog(id={self.id})'


class SalesOrderItemOutwardedLog:
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
        additional_details: dict,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: User,
        so_item: SalesOrderItem,
    ) -> None:
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
        self.domain_user = domain_user
        self.so_item = so_item

    def __repr__(self) -> str:
        return f'SalesOrderItemOutwardedLog(id={self.id})'


class Category:
    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        description: str,
        display_order: int,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: User,
        domain_user: User,
        parent: Optional[Category],
    ) -> None:
        self.id = id
        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.added_by_user = added_by_user
        self.domain_user = domain_user
        self.parent = parent

    def __repr__(self) -> str:
        return f'Category(id={self.id})'


class Product:
    def __init__(
        self,
        id: int,
        name: str,
        image: dict,
        description: str,
        specifications: dict,
        html_description: str,
        highlights: dict,
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
        seo_keywords: dict,
        addition_details: dict,
        created_at: datetime,
        updated_at: datetime,
        added_by_user: User,
        category: Category,
        domain_user: User,
    ) -> None:
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
        self.added_by_user = added_by_user
        self.category = category
        self.domain_user = domain_user

    def __repr__(self) -> str:
        return f'Product(id={self.id})'


class ProductQuestion:
    def __init__(
        self,
        id: int,
        question: str,
        answer: Optional[str],
        status: str,
        created_at: datetime,
        updated_at: datetime,
        answer_user: Optional[User],
        domain_user: User,
        question_user: User,
        product: Product,
    ) -> None:
        self.id = id
        self.question = question
        self.answer = answer
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.answer_user = answer_user
        self.domain_user = domain_user
        self.question_user = question_user
        self.product = product

    def __repr__(self) -> str:
        return f'ProductQuestion(id={self.id})'


class ProductReview:
    def __init__(
        self,
        id: int,
        review_images: dict,
        rating: float,
        reviews: str,
        status: str,
        domain_user: User,
        review_user: User,
        product: Product,
    ) -> None:
        self.id = id
        self.review_images = review_images
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.domain_user = domain_user
        self.review_user = review_user
        self.product = product

    def __repr__(self) -> str:
        return f'ProductReview(id={self.id})'


class User:
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
        social_media_links: dict,
        addition_details: dict,
        language: str,
        departMent: str,
        designation: str,
        time_zone: str,
        last_login: Optional[datetime],
        last_device: Optional[str],
        last_ip: Optional[str],
        currency: str,
        domain_name: str,
        plan_type: str,
        created_at: datetime,
        updated_at: datetime,
        domain_user: Optional[User],
    ) -> None:
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
        self.domain_user = domain_user

    def __repr__(self) -> str:
        return f'User(id={self.id})'


class UserShippingAddress:
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
        user: User,
    ) -> None:
        self.id = id
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.created_at = created_at
        self.updated_at = updated_at
        self.user = user

    def __repr__(self) -> str:
        return f'UserShippingAddress(id={self.id})'


class ActivityLog:
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
        domain_user: User,
        user: User,
    ) -> None:
        self.id = id
        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.created_at = created_at
        self.updated_at = updated_at
        self.domain_user = domain_user
        self.user = user

    def __repr__(self) -> str:
        return f'ActivityLog(id={self.id})'


class Module:
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
        parent: Optional[Module],
    ) -> None:
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
        self.parent = parent

    def __repr__(self) -> str:
        return f'Module(id={self.id})'


class UserPermission:
    def __init__(
        self,
        id: int,
        is_view: bool,
        is_add: bool,
        is_edit: bool,
        is_delete: bool,
        created_at: datetime,
        updated_at: datetime,
        module: Module,
        domain_user: User,
        user: User,
    ) -> None:
        self.id = id
        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.created_at = created_at
        self.updated_at = updated_at
        self.module = module
        self.domain_user = domain_user
        self.user = user

    def __repr__(self) -> str:
        return f'UserPermission(id={self.id})'


class UsersGroups:
    def __init__(
        self,
        id: int,
        users: User,
        group: AuthGroup,
    ) -> None:
        self.id = id
        self.users = users
        self.group = group

    def __repr__(self) -> str:
        return f'UsersGroups(id={self.id})'


class UsersUserPermissions:
    def __init__(
        self,
        id: int,
        users: User,
        permission: AuthPermission,
    ) -> None:
        self.id = id
        self.users = users
        self.permission = permission

    def __repr__(self) -> str:
        return f'UsersUserPermissions(id={self.id})'


class DjangoAdminLog:
    def __init__(
        self,
        id: int,
        action_time: datetime,
        object_id: str,
        object_repr: str,
        action_flag: int,
        change_message: str,
        content_type: DjangoContentType,
        user: User,
    ) -> None:
        self.id = id
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type = content_type
        self.user = user

    def __repr__(self) -> str:
        return f'DjangoAdminLog(id={self.id})'


class DjangoMigrations:
    def __init__(
        self,
        id: int,
        app: str,
        name: str,
        applied: datetime,
    ) -> None:
        self.id = id
        self.app = app
        self.name = name
        self.applied = applied

    def __repr__(self) -> str:
        return f'DjangoMigrations(id={self.id})'


class DjangoContentType:
    def __init__(
        self,
        id: int,
        app_label: str,
        model: str,
    ) -> None:
        self.id = id
        self.app_label = app_label
        self.model = model

    def __repr__(self) -> str:
        return f'DjangoContentType(id={self.id})'


class DjangoSession:
    def __init__(
        self,
        session_key: str,
        session_data: str,
        expire_date: datetime,
    ) -> None:
        self.session_key = session_key
        self.session_data = session_data
        self.expire_date = expire_date

    def __repr__(self) -> str:
        return f'DjangoSession(key={self.session_key})'


class AuthGroup:
    def __init__(
        self,
        id: int,
        name: str,
    ) -> None:
        self.id = id
        self.name = name

    def __repr__(self) -> str:
        return f'AuthGroup(id={self.id})'


class AuthGroupPermissions:
    def __init__(
        self,
        id: int,
        group: AuthGroup,
        permission: AuthPermission,
    ) -> None:
        self.id = id
        self.group = group
        self.permission = permission

    def __repr__(self) -> str:
        return f'AuthGroupPermissions(id={self.id})'


class AuthPermission:
    def __init__(
        self,
        id: int,
        name: str,
        codename: str,
        content_type: DjangoContentType,
    ) -> None:
        self.id = id
        self.name = name
        self.codename = codename
        self.content_type = content_type

    def __repr__(self) -> str:
        return f'AuthPermission(id={self.id})'