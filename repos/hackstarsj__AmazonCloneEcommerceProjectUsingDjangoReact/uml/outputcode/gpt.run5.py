from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


class ValidationError(ValueError):
    pass


class BaseEntity:
    def __init__(self, id: Any):
        self.id = id


class TimestampedEntity(BaseEntity):
    def __init__(self, id: Any, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        super().__init__(id=id)
        self.created_at: datetime = created_at or datetime.utcnow()
        self.updated_at: datetime = updated_at or self.created_at

    def touch(self, when: Optional[datetime] = None) -> None:
        self.updated_at = when or datetime.utcnow()


class DomainBound:
    def __init__(self, domain_user: Optional["userservices_users"] = None):
        self.domain_user: Optional["userservices_users"] = domain_user


class UserBound:
    def __init__(self, added_by_user: Optional["userservices_users"] = None):
        self.added_by_user: Optional["userservices_users"] = added_by_user


class ParentBound:
    def __init__(self, parent: Optional[Any] = None):
        self.parent = parent


class inventoryservices_warehouse(TimestampedEntity, DomainBound, UserBound):
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
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        warehouse_manager: Optional["userservices_users"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)
        UserBound.__init__(self, added_by_user=added_by_user)

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
        self.additional_details: JsonDict = additional_details or {}
        self.warehouse_manager: Optional["userservices_users"] = warehouse_manager


class inventoryservices_rackandshelvesandfloor(TimestampedEntity, DomainBound, UserBound):
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        rack: Optional[str] = None,
        shelf: Optional[str] = None,
        floor: Optional[str] = None,
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)
        UserBound.__init__(self, added_by_user=added_by_user)

        self.name = name
        self.rack = rack
        self.shelf = shelf
        self.floor = floor
        self.additional_details: JsonDict = additional_details or {}
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


class productservices_categories(TimestampedEntity, DomainBound, UserBound, ParentBound):
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        image: Optional[str] = None,
        description: Optional[str] = None,
        display_order: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        parent: Optional["productservices_categories"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)
        UserBound.__init__(self, added_by_user=added_by_user)
        ParentBound.__init__(self, parent=parent)

        self.name = name
        self.image = image
        self.description = description
        self.display_order = display_order


class productservices_products(TimestampedEntity, DomainBound, UserBound):
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        image: Optional[Any] = None,
        description: Optional[str] = None,
        specifications: Optional[Any] = None,
        html_description: Optional[str] = None,
        highlights: Optional[Any] = None,
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
        seo_keywords: Optional[Any] = None,
        addition_details: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional["userservices_users"] = None,
        category: Optional[productservices_categories] = None,
        domain_user: Optional["userservices_users"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)
        UserBound.__init__(self, added_by_user=added_by_user)

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
        self.category: Optional[productservices_categories] = category


class orderservice_purchaseorder(TimestampedEntity, DomainBound):
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
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional["userservices_users"] = None,
        cancelled_by_user: Optional["userservices_users"] = None,
        created_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        last_updated_by_user: Optional["userservices_users"] = None,
        received_by_user: Optional["userservices_users"] = None,
        returned_by_user: Optional["userservices_users"] = None,
        supplier: Optional["userservices_users"] = None,
        updated_by_user: Optional["userservices_users"] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

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
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at

        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.supplier = supplier
        self.updated_by_user = updated_by_user
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


class orderservice_purchaseorderitems(TimestampedEntity, DomainBound):
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
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional["userservices_users"] = None,
        cancelled_by_user: Optional["userservices_users"] = None,
        created_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        last_updated_by_user: Optional["userservices_users"] = None,
        received_by_user: Optional["userservices_users"] = None,
        returned_by_user: Optional["userservices_users"] = None,
        po: Optional[orderservice_purchaseorder] = None,
        product: Optional[productservices_products] = None,
        updated_by_user: Optional["userservices_users"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

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
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at

        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.po: Optional[orderservice_purchaseorder] = po
        self.product: Optional[productservices_products] = product
        self.updated_by_user = updated_by_user


class orderservice_purchaseorderlogs(TimestampedEntity, DomainBound):
    def __init__(
        self,
        id: int,
        comment: Optional[str] = None,
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        po: Optional[orderservice_purchaseorder] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.comment = comment
        self.additional_details: JsonDict = additional_details or {}
        self.created_by_user = created_by_user
        self.po: Optional[orderservice_purchaseorder] = po


class orderservice_purchaseorderinwardedlog(TimestampedEntity, DomainBound):
    def __init__(
        self,
        id: int,
        invoice_path: Optional[str] = None,
        invoice_number: Optional[str] = None,
        notes: Optional[str] = None,
        inwarded_at: Optional[datetime] = None,
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional["userservices_users"] = None,
        inwarded_by_user: Optional["userservices_users"] = None,
        po: Optional[orderservice_purchaseorder] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.inwarded_at = inwarded_at
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.inwarded_by_user = inwarded_by_user
        self.po: Optional[orderservice_purchaseorder] = po


class orderservice_purchaseorderiteminwardedlog(TimestampedEntity, DomainBound):
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
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional["userservices_users"] = None,
        po_item: Optional[orderservice_purchaseorderitems] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.inwarded_quantity = inwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.po_item: Optional[orderservice_purchaseorderitems] = po_item


class orderservice_salesorder(TimestampedEntity, DomainBound):
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
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        received_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional["userservices_users"] = None,
        cancelled_by_user: Optional["userservices_users"] = None,
        created_by_user: Optional["userservices_users"] = None,
        customer: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        last_updated_by_user: Optional["userservices_users"] = None,
        received_by_user: Optional["userservices_users"] = None,
        returned_by_user: Optional["userservices_users"] = None,
        po: Optional[orderservice_purchaseorder] = None,
        product: Optional[productservices_products] = None,
        updated_by_user: Optional["userservices_users"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

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
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.received_at = received_at
        self.returned_at = returned_at

        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.customer = customer
        self.last_updated_by_user = last_updated_by_user
        self.received_by_user = received_by_user
        self.returned_by_user = returned_by_user
        self.po: Optional[orderservice_purchaseorder] = po
        self.product: Optional[productservices_products] = product
        self.updated_by_user = updated_by_user


class orderservice_salesorderorderitems(TimestampedEntity, DomainBound):
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
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        cancelled_reason: Optional[str] = None,
        shipped_at: Optional[datetime] = None,
        returned_at: Optional[datetime] = None,
        approved_by_user: Optional["userservices_users"] = None,
        cancelled_by_user: Optional["userservices_users"] = None,
        created_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        product: Optional[productservices_products] = None,
        returned_by_user: Optional["userservices_users"] = None,
        shipped_by_user: Optional["userservices_users"] = None,
        so: Optional[orderservice_salesorder] = None,
        updated_by_user: Optional["userservices_users"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

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
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.approved_at = approved_at
        self.cancelled_at = cancelled_at
        self.cancelled_reason = cancelled_reason
        self.shipped_at = shipped_at
        self.returned_at = returned_at

        self.approved_by_user = approved_by_user
        self.cancelled_by_user = cancelled_by_user
        self.created_by_user = created_by_user
        self.product: Optional[productservices_products] = product
        self.returned_by_user = returned_by_user
        self.shipped_by_user = shipped_by_user
        self.so: Optional[orderservice_salesorder] = so
        self.updated_by_user = updated_by_user


class orderservice_salesorderlogs(TimestampedEntity, DomainBound):
    def __init__(
        self,
        id: int,
        comment: Optional[str] = None,
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        so: Optional[orderservice_salesorder] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.comment = comment
        self.additional_details: JsonDict = additional_details or {}
        self.created_by_user = created_by_user
        self.so: Optional[orderservice_salesorder] = so


class orderservice_salesorderoutwardedlog(TimestampedEntity, DomainBound):
    def __init__(
        self,
        id: int,
        invoice_path: Optional[str] = None,
        invoice_number: Optional[str] = None,
        notes: Optional[str] = None,
        outwared_at: Optional[datetime] = None,
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional["userservices_users"] = None,
        outwarded_by_user: Optional["userservices_users"] = None,
        so: Optional[orderservice_salesorder] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.invoice_path = invoice_path
        self.invoice_number = invoice_number
        self.notes = notes
        self.outwared_at = outwared_at
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.outwarded_by_user = outwarded_by_user
        self.so: Optional[orderservice_salesorder] = so


class orderservice_salesorderitemoutwardedlog(TimestampedEntity, DomainBound):
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
        additional_details: Optional[JsonDict] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        domain_user: Optional["userservices_users"] = None,
        so_item: Optional[orderservice_salesorderorderitems] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.outwarded_quantity = outwarded_quantity
        self.price = price
        self.tax_percentage = tax_percentage
        self.discount_amount = discount_amount
        self.discount_type = discount_type
        self.shipping_amount = shipping_amount
        self.shipping_tax_percentage = shipping_tax_percentage
        self.additional_details: JsonDict = additional_details or {}
        self.status = status
        self.so_item: Optional[orderservice_salesorderorderitems] = so_item


class inventoryservices_inventory(TimestampedEntity, DomainBound, UserBound):
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
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        product: Optional[productservices_products] = None,
        purchase_order: Optional[orderservice_purchaseorder] = None,
        purchase_order_item: Optional[orderservice_purchaseorderitems] = None,
        purchase_order_item_inwarded_item: Optional[orderservice_purchaseorderiteminwardedlog] = None,
        rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)
        UserBound.__init__(self, added_by_user=added_by_user)

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
        self.additional_details: JsonDict = additional_details or {}

        self.product: Optional[productservices_products] = product
        self.purchase_order: Optional[orderservice_purchaseorder] = purchase_order
        self.purchase_order_item: Optional[orderservice_purchaseorderitems] = purchase_order_item
        self.purchase_order_item_inwarded_item: Optional[orderservice_purchaseorderiteminwardedlog] = (
            purchase_order_item_inwarded_item
        )
        self.rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = rack_shelf_floor
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


class inventoryservices_inventorylog(TimestampedEntity, DomainBound, UserBound):
    def __init__(
        self,
        id: int,
        quantity: Optional[int] = None,
        status: Optional[str] = None,
        additional_details: Optional[JsonDict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        added_by_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        inventory: Optional[inventoryservices_inventory] = None,
        po: Optional[orderservice_purchaseorder] = None,
        so: Optional[orderservice_salesorder] = None,
        rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = None,
        warehouse: Optional[inventoryservices_warehouse] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)
        UserBound.__init__(self, added_by_user=added_by_user)

        self.quantity = quantity
        self.status = status
        self.additional_details: JsonDict = additional_details or {}

        self.inventory: Optional[inventoryservices_inventory] = inventory
        self.po: Optional[orderservice_purchaseorder] = po
        self.so: Optional[orderservice_salesorder] = so
        self.rack_shelf_floor: Optional[inventoryservices_rackandshelvesandfloor] = rack_shelf_floor
        self.warehouse: Optional[inventoryservices_warehouse] = warehouse


class productservices_productquestions(TimestampedEntity, DomainBound):
    def __init__(
        self,
        id: int,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        status: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        answer_user: Optional["userservices_users"] = None,
        domain_user: Optional["userservices_users"] = None,
        question_user: Optional["userservices_users"] = None,
        product: Optional[productservices_products] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.question = question
        self.answer = answer
        self.status = status
        self.answer_user = answer_user
        self.question_user = question_user
        self.product: Optional[productservices_products] = product


class productservices_productreviews(BaseEntity, DomainBound):
    def __init__(
        self,
        id: int,
        review_images: Optional[Any] = None,
        rating: Optional[float] = None,
        reviews: Optional[str] = None,
        status: Optional[str] = None,
        domain_user: Optional["userservices_users"] = None,
        review_user: Optional["userservices_users"] = None,
        product: Optional[productservices_products] = None,
    ):
        BaseEntity.__init__(self, id=id)
        DomainBound.__init__(self, domain_user=domain_user)

        self.review_images = review_images
        self.rating = rating
        self.reviews = reviews
        self.status = status
        self.review_user = review_user
        self.product: Optional[productservices_products] = product


class userservices_users(TimestampedEntity, DomainBound):
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
        social_media_links: Optional[Any] = None,
        addition_details: Optional[Any] = None,
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
        domain_user: Optional["userservices_users"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

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


class userservices_usershippingaddress(TimestampedEntity):
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
        user: Optional[userservices_users] = None,
    ):
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.address_type = address_type
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
        self.user: Optional[userservices_users] = user


class userservices_activitylog(TimestampedEntity, DomainBound):
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
        domain_user: Optional[userservices_users] = None,
        user: Optional[userservices_users] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.activity = activity
        self.activity_type = activity_type
        self.activity_date = activity_date
        self.activity_ip = activity_ip
        self.activity_device = activity_device
        self.user: Optional[userservices_users] = user


class userservices_modules(TimestampedEntity, ParentBound):
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
        parent: Optional["userservices_modules"] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        ParentBound.__init__(self, parent=parent)

        self.module_name = module_name
        self.module_icon = module_icon
        self.is_menu = is_menu
        self.is_active = is_active
        self.module_url = module_url
        self.display_order = display_order
        self.module_description = module_description


class userservices_userpermissions(TimestampedEntity, DomainBound):
    def __init__(
        self,
        id: int,
        is_view: Optional[bool] = None,
        is_add: Optional[bool] = None,
        is_edit: Optional[bool] = None,
        is_delete: Optional[bool] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        module: Optional[userservices_modules] = None,
        domain_user: Optional[userservices_users] = None,
        user: Optional[userservices_users] = None,
    ):
        TimestampedEntity.__init__(self, id=id, created_at=created_at, updated_at=updated_at)
        DomainBound.__init__(self, domain_user=domain_user)

        self.is_view = is_view
        self.is_add = is_add
        self.is_edit = is_edit
        self.is_delete = is_delete
        self.module: Optional[userservices_modules] = module
        self.user: Optional[userservices_users] = user


class auth_group(BaseEntity):
    def __init__(self, id: int, name: Optional[str] = None):
        super().__init__(id=id)
        self.name = name


class django_content_type(BaseEntity):
    def __init__(self, id: int, app_label: Optional[str] = None, model: Optional[str] = None):
        super().__init__(id=id)
        self.app_label = app_label
        self.model = model


class auth_permission(BaseEntity):
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        codename: Optional[str] = None,
        content_type: Optional[django_content_type] = None,
    ):
        super().__init__(id=id)
        self.name = name
        self.codename = codename
        self.content_type: Optional[django_content_type] = content_type


class auth_group_permissions(BaseEntity):
    def __init__(
        self,
        id: int,
        group: Optional[auth_group] = None,
        permission: Optional[auth_permission] = None,
    ):
        super().__init__(id=id)
        self.group: Optional[auth_group] = group
        self.permission: Optional[auth_permission] = permission


class userservices_users_groups(BaseEntity):
    def __init__(self, id: int, users: Optional[userservices_users] = None, group: Optional[auth_group] = None):
        super().__init__(id=id)
        self.users: Optional[userservices_users] = users
        self.group: Optional[auth_group] = group


class userservices_users_user_permissions(BaseEntity):
    def __init__(
        self,
        id: int,
        users: Optional[userservices_users] = None,
        permission: Optional[auth_permission] = None,
    ):
        super().__init__(id=id)
        self.users: Optional[userservices_users] = users
        self.permission: Optional[auth_permission] = permission


class django_admin_log(BaseEntity):
    def __init__(
        self,
        id: int,
        action_time: Optional[datetime] = None,
        object_id: Optional[str] = None,
        object_repr: Optional[str] = None,
        action_flag: Optional[int] = None,
        change_message: Optional[str] = None,
        content_type: Optional[django_content_type] = None,
        user: Optional[userservices_users] = None,
    ):
        super().__init__(id=id)
        self.action_time = action_time
        self.object_id = object_id
        self.object_repr = object_repr
        self.action_flag = action_flag
        self.change_message = change_message
        self.content_type: Optional[django_content_type] = content_type
        self.user: Optional[userservices_users] = user


class django_migrations(BaseEntity):
    def __init__(self, id: int, app: Optional[str] = None, name: Optional[str] = None, applied: Optional[datetime] = None):
        super().__init__(id=id)
        self.app = app
        self.name = name
        self.applied = applied


class django_session(BaseEntity):
    def __init__(self, session_key: str, session_data: Optional[str] = None, expire_date: Optional[datetime] = None):
        super().__init__(id=session_key)
        self.session_key: str = session_key
        self.session_data = session_data
        self.expire_date = expire_date


__all__ = [
    "ValidationError",
    "inventoryservices_inventory",
    "inventoryservices_inventorylog",
    "inventoryservices_rackandshelvesandfloor",
    "inventoryservices_warehouse",
    "orderservice_purchaseorder",
    "orderservice_purchaseorderitems",
    "orderservice_purchaseorderlogs",
    "orderservice_purchaseorderinwardedlog",
    "orderservice_purchaseorderiteminwardedlog",
    "orderservice_salesorder",
    "orderservice_salesorderorderitems",
    "orderservice_salesorderlogs",
    "orderservice_salesorderoutwardedlog",
    "orderservice_salesorderitemoutwardedlog",
    "productservices_categories",
    "productservices_products",
    "productservices_productquestions",
    "productservices_productreviews",
    "userservices_users",
    "userservices_usershippingaddress",
    "userservices_activitylog",
    "userservices_modules",
    "userservices_userpermissions",
    "userservices_users_groups",
    "userservices_users_user_permissions",
    "django_admin_log",
    "django_migrations",
    "django_content_type",
    "django_session",
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
]