from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import hashlib
import secrets


class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class AuthorizationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class InventoryError(DomainError):
    pass


class OrderError(DomainError):
    pass


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    STAFF = "staff"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    PLACED = "placed"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    CANCELLED = "cancelled"


def _now() -> datetime:
    return datetime.utcnow()


def _ensure_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _ensure_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer")
    return value


def _ensure_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer")
    return value


def _ensure_money(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal")
    if value < Decimal("0"):
        raise ValidationError(f"{field_name} must be >= 0")
    return value


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()


@dataclass(frozen=True)
class Address:
    line1: str
    city: str
    state: str
    postal_code: str
    country: str = "US"
    line2: str = ""

    def __post_init__(self) -> None:
        _ensure_non_empty(self.line1, "line1")
        _ensure_non_empty(self.city, "city")
        _ensure_non_empty(self.state, "state")
        _ensure_non_empty(self.postal_code, "postal_code")
        _ensure_non_empty(self.country, "country")


@dataclass
class User:
    id: int
    email: str
    name: str
    role: Role
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    _password_salt: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)
    _password_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        self.email = _ensure_non_empty(self.email, "email").lower()
        self.name = _ensure_non_empty(self.name, "name")
        if not isinstance(self.role, Role):
            raise ValidationError("role must be a Role")

    def set_password(self, password: str) -> None:
        password = _ensure_non_empty(password, "password")
        if len(password) < 8:
            raise ValidationError("password must be at least 8 characters")
        self._password_hash = _hash_password(password, self._password_salt)

    def check_password(self, password: str) -> bool:
        if not self._password_hash:
            return False
        return _hash_password(password, self._password_salt) == self._password_hash

    def require_active(self) -> None:
        if not self.is_active:
            raise AuthorizationError("user is inactive")


@dataclass
class Supplier:
    id: int
    name: str
    email: str
    phone: str = ""
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.name = _ensure_non_empty(self.name, "name")
        self.email = _ensure_non_empty(self.email, "email").lower()


@dataclass
class Warehouse:
    id: int
    name: str
    address: Address
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.name = _ensure_non_empty(self.name, "name")
        if not isinstance(self.address, Address):
            raise ValidationError("address must be an Address")


@dataclass
class Category:
    id: int
    name: str
    parent_id: Optional[int] = None

    def __post_init__(self) -> None:
        self.name = _ensure_non_empty(self.name, "name")


@dataclass
class Product:
    id: int
    sku: str
    name: str
    description: str
    price: Decimal
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    category_ids: Set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.sku = _ensure_non_empty(self.sku, "sku")
        self.name = _ensure_non_empty(self.name, "name")
        self.description = self.description if isinstance(self.description, str) else ""
        self.price = _ensure_money(self.price, "price")

    def set_price(self, price: Decimal) -> None:
        self.price = _ensure_money(price, "price")


@dataclass
class InventoryItem:
    product_id: int
    warehouse_id: int
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.quantity_on_hand = _ensure_non_negative_int(self.quantity_on_hand, "quantity_on_hand")
        self.quantity_reserved = _ensure_non_negative_int(self.quantity_reserved, "quantity_reserved")
        if self.quantity_reserved > self.quantity_on_hand:
            raise InventoryError("reserved cannot exceed on_hand")

    @property
    def available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved

    def reserve(self, qty: int) -> None:
        qty = _ensure_positive_int(qty, "qty")
        if qty > self.available:
            raise InventoryError("insufficient available inventory to reserve")
        self.quantity_reserved += qty
        self.updated_at = _now()

    def release(self, qty: int) -> None:
        qty = _ensure_positive_int(qty, "qty")
        if qty > self.quantity_reserved:
            raise InventoryError("cannot release more than reserved")
        self.quantity_reserved -= qty
        self.updated_at = _now()

    def add_stock(self, qty: int) -> None:
        qty = _ensure_positive_int(qty, "qty")
        self.quantity_on_hand += qty
        self.updated_at = _now()

    def remove_stock(self, qty: int) -> None:
        qty = _ensure_positive_int(qty, "qty")
        if qty > self.quantity_on_hand:
            raise InventoryError("cannot remove more than on_hand")
        if self.quantity_on_hand - qty < self.quantity_reserved:
            raise InventoryError("cannot remove stock below reserved level")
        self.quantity_on_hand -= qty
        self.updated_at = _now()


@dataclass
class CartItem:
    product_id: int
    quantity: int

    def __post_init__(self) -> None:
        self.quantity = _ensure_positive_int(self.quantity, "quantity")


@dataclass
class Cart:
    id: int
    user_id: int
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    items: Dict[int, CartItem] = field(default_factory=dict)

    def add_item(self, product_id: int, quantity: int) -> None:
        quantity = _ensure_positive_int(quantity, "quantity")
        if product_id in self.items:
            self.items[product_id].quantity += quantity
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def set_quantity(self, product_id: int, quantity: int) -> None:
        quantity = _ensure_positive_int(quantity, "quantity")
        if product_id not in self.items:
            raise NotFoundError("product not in cart")
        self.items[product_id].quantity = quantity
        self.updated_at = _now()

    def remove_item(self, product_id: int) -> None:
        if product_id not in self.items:
            raise NotFoundError("product not in cart")
        del self.items[product_id]
        self.updated_at = _now()

    def clear(self) -> None:
        self.items.clear()
        self.updated_at = _now()

    def is_empty(self) -> bool:
        return not self.items


@dataclass
class OrderLine:
    product_id: int
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        self.unit_price = _ensure_money(self.unit_price, "unit_price")
        self.quantity = _ensure_positive_int(self.quantity, "quantity")

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * Decimal(self.quantity)


@dataclass
class SalesOrder:
    id: int
    user_id: int
    status: OrderStatus = OrderStatus.DRAFT
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    shipping_address: Optional[Address] = None
    lines: List[OrderLine] = field(default_factory=list)
    reserved_from_warehouse_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, OrderStatus):
            raise ValidationError("status must be an OrderStatus")

    def add_line(self, product_id: int, unit_price: Decimal, quantity: int) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderError("can only modify draft orders")
        self.lines.append(OrderLine(product_id=product_id, unit_price=unit_price, quantity=quantity))
        self.updated_at = _now()

    def set_shipping_address(self, address: Address) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderError("can only modify draft orders")
        if not isinstance(address, Address):
            raise ValidationError("address must be an Address")
        self.shipping_address = address
        self.updated_at = _now()

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0")
        for l in self.lines:
            total += l.line_total
        return total

    @property
    def total(self) -> Decimal:
        return self.subtotal

    def place(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderError("order is not in draft state")
        if not self.lines:
            raise OrderError("cannot place an order with no lines")
        if self.shipping_address is None:
            raise OrderError("shipping address required")
        self.status = OrderStatus.PLACED
        self.updated_at = _now()

    def mark_paid(self) -> None:
        if self.status != OrderStatus.PLACED:
            raise OrderError("can only pay a placed order")
        self.status = OrderStatus.PAID
        self.updated_at = _now()

    def ship(self) -> None:
        if self.status != OrderStatus.PAID:
            raise OrderError("can only ship a paid order")
        self.status = OrderStatus.SHIPPED
        self.updated_at = _now()

    def deliver(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise OrderError("can only deliver a shipped order")
        self.status = OrderStatus.DELIVERED
        self.updated_at = _now()

    def cancel(self) -> None:
        if self.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise OrderError("cannot cancel after shipment")
        if self.status == OrderStatus.CANCELLED:
            return
        self.status = OrderStatus.CANCELLED
        self.updated_at = _now()


@dataclass
class PurchaseOrderLine:
    product_id: int
    unit_cost: Decimal
    quantity: int

    def __post_init__(self) -> None:
        self.unit_cost = _ensure_money(self.unit_cost, "unit_cost")
        self.quantity = _ensure_positive_int(self.quantity, "quantity")

    @property
    def line_total(self) -> Decimal:
        return self.unit_cost * Decimal(self.quantity)


@dataclass
class PurchaseOrder:
    id: int
    supplier_id: int
    warehouse_id: int
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    lines: List[PurchaseOrderLine] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.status, PurchaseOrderStatus):
            raise ValidationError("status must be a PurchaseOrderStatus")

    def add_line(self, product_id: int, unit_cost: Decimal, quantity: int) -> None:
        if self.status != PurchaseOrderStatus.DRAFT:
            raise OrderError("can only modify draft purchase orders")
        self.lines.append(PurchaseOrderLine(product_id=product_id, unit_cost=unit_cost, quantity=quantity))
        self.updated_at = _now()

    @property
    def total_cost(self) -> Decimal:
        total = Decimal("0")
        for l in self.lines:
            total += l.line_total
        return total

    def submit(self) -> None:
        if self.status != PurchaseOrderStatus.DRAFT:
            raise OrderError("purchase order is not in draft state")
        if not self.lines:
            raise OrderError("cannot submit a purchase order with no lines")
        self.status = PurchaseOrderStatus.SUBMITTED
        self.updated_at = _now()

    def receive(self) -> None:
        if self.status != PurchaseOrderStatus.SUBMITTED:
            raise OrderError("can only receive a submitted purchase order")
        self.status = PurchaseOrderStatus.RECEIVED
        self.updated_at = _now()

    def cancel(self) -> None:
        if self.status == PurchaseOrderStatus.RECEIVED:
            raise OrderError("cannot cancel a received purchase order")
        if self.status == PurchaseOrderStatus.CANCELLED:
            return
        self.status = PurchaseOrderStatus.CANCELLED
        self.updated_at = _now()


class InMemoryDB:
    def __init__(self) -> None:
        self._next_ids: Dict[str, int] = {}
        self.users: Dict[int, User] = {}
        self.suppliers: Dict[int, Supplier] = {}
        self.warehouses: Dict[int, Warehouse] = {}
        self.categories: Dict[int, Category] = {}
        self.products: Dict[int, Product] = {}
        self.inventory: Dict[Tuple[int, int], InventoryItem] = {}
        self.carts: Dict[int, Cart] = {}
        self.sales_orders: Dict[int, SalesOrder] = {}
        self.purchase_orders: Dict[int, PurchaseOrder] = {}
        self.sessions: Dict[str, int] = {}

    def next_id(self, entity: str) -> int:
        current = self._next_ids.get(entity, 0) + 1
        self._next_ids[entity] = current
        return current


class AuthService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def sign_up(self, email: str, name: str, password: str, role: Role = Role.CUSTOMER) -> User:
        email_n = _ensure_non_empty(email, "email").lower()
        for u in self._db.users.values():
            if u.email == email_n:
                raise ValidationError("email already in use")
        user = User(id=self._db.next_id("user"), email=email_n, name=name, role=role)
        user.set_password(password)
        self._db.users[user.id] = user
        cart = Cart(id=self._db.next_id("cart"), user_id=user.id)
        self._db.carts[user.id] = cart
        return user

    def login(self, email: str, password: str) -> str:
        email_n = _ensure_non_empty(email, "email").lower()
        user = next((u for u in self._db.users.values() if u.email == email_n), None)
        if user is None or not user.check_password(password):
            raise AuthenticationError("invalid credentials")
        user.require_active()
        token = secrets.token_urlsafe(32)
        self._db.sessions[token] = user.id
        return token

    def logout(self, token: str) -> None:
        token = _ensure_non_empty(token, "token")
        self._db.sessions.pop(token, None)

    def get_user_for_token(self, token: str) -> User:
        token = _ensure_non_empty(token, "token")
        user_id = self._db.sessions.get(token)
        if user_id is None:
            raise AuthenticationError("invalid session")
        user = self._db.users.get(user_id)
        if user is None:
            raise AuthenticationError("invalid session")
        user.require_active()
        return user


class CatalogService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_category(self, actor: User, name: str, parent_id: Optional[int] = None) -> Category:
        self._require_admin_or_staff(actor)
        if parent_id is not None and parent_id not in self._db.categories:
            raise NotFoundError("parent category not found")
        cat = Category(id=self._db.next_id("category"), name=name, parent_id=parent_id)
        self._db.categories[cat.id] = cat
        return cat

    def create_product(
        self,
        actor: User,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        category_ids: Optional[Set[int]] = None,
        is_active: bool = True,
    ) -> Product:
        self._require_admin_or_staff(actor)
        sku_n = _ensure_non_empty(sku, "sku")
        for p in self._db.products.values():
            if p.sku == sku_n:
                raise ValidationError("sku already exists")
        if category_ids:
            for cid in category_ids:
                if cid not in self._db.categories:
                    raise NotFoundError(f"category {cid} not found")
        prod = Product(
            id=self._db.next_id("product"),
            sku=sku_n,
            name=name,
            description=description,
            price=price,
            is_active=is_active,
            category_ids=set(category_ids or set()),
        )
        self._db.products[prod.id] = prod
        return prod

    def update_product_price(self, actor: User, product_id: int, price: Decimal) -> None:
        self._require_admin_or_staff(actor)
        prod = self._get_product(product_id)
        prod.set_price(price)

    def set_product_active(self, actor: User, product_id: int, is_active: bool) -> None:
        self._require_admin_or_staff(actor)
        prod = self._get_product(product_id)
        prod.is_active = bool(is_active)

    def list_products(self, query: str = "", category_id: Optional[int] = None, active_only: bool = True) -> List[Product]:
        q = (query or "").strip().lower()
        results: List[Product] = []
        for p in self._db.products.values():
            if active_only and not p.is_active:
                continue
            if category_id is not None and category_id not in p.category_ids:
                continue
            if q:
                hay = f"{p.sku} {p.name} {p.description}".lower()
                if q not in hay:
                    continue
            results.append(p)
        results.sort(key=lambda x: x.id)
        return results

    def get_product_detail(self, product_id: int, active_only: bool = True) -> Product:
        p = self._get_product(product_id)
        if active_only and not p.is_active:
            raise NotFoundError("product not found")
        return p

    def _get_product(self, product_id: int) -> Product:
        if product_id not in self._db.products:
            raise NotFoundError("product not found")
        return self._db.products[product_id]

    @staticmethod
    def _require_admin_or_staff(actor: User) -> None:
        actor.require_active()
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthorizationError("insufficient permissions")


class WarehouseService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_warehouse(self, actor: User, name: str, address: Address) -> Warehouse:
        self._require_admin_or_staff(actor)
        wh = Warehouse(id=self._db.next_id("warehouse"), name=name, address=address)
        self._db.warehouses[wh.id] = wh
        return wh

    def create_supplier(self, actor: User, name: str, email: str, phone: str = "") -> Supplier:
        self._require_admin_or_staff(actor)
        email_n = _ensure_non_empty(email, "email").lower()
        for s in self._db.suppliers.values():
            if s.email == email_n:
                raise ValidationError("supplier email already exists")
        sup = Supplier(id=self._db.next_id("supplier"), name=name, email=email_n, phone=phone)
        self._db.suppliers[sup.id] = sup
        return sup

    def get_inventory_item(self, product_id: int, warehouse_id: int) -> InventoryItem:
        key = (product_id, warehouse_id)
        item = self._db.inventory.get(key)
        if item is None:
            item = InventoryItem(product_id=product_id, warehouse_id=warehouse_id, quantity_on_hand=0, quantity_reserved=0)
            self._db.inventory[key] = item
        return item

    def adjust_stock(self, actor: User, product_id: int, warehouse_id: int, delta: int) -> InventoryItem:
        self._require_admin_or_staff(actor)
        if product_id not in self._db.products:
            raise NotFoundError("product not found")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")
        if not isinstance(delta, int) or delta == 0:
            raise ValidationError("delta must be a non-zero integer")
        item = self.get_inventory_item(product_id, warehouse_id)
        if delta > 0:
            item.add_stock(delta)
        else:
            item.remove_stock(-delta)
        return item

    def list_warehouses(self) -> List[Warehouse]:
        res = list(self._db.warehouses.values())
        res.sort(key=lambda w: w.id)
        return res

    def list_inventory_for_warehouse(self, warehouse_id: int) -> List[InventoryItem]:
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")
        items = [it for (pid, wid), it in self._db.inventory.items() if wid == warehouse_id]
        items.sort(key=lambda x: x.product_id)
        return items

    @staticmethod
    def _require_admin_or_staff(actor: User) -> None:
        actor.require_active()
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthorizationError("insufficient permissions")


class CartService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def get_cart(self, user: User) -> Cart:
        user.require_active()
        cart = self._db.carts.get(user.id)
        if cart is None:
            cart = Cart(id=self._db.next_id("cart"), user_id=user.id)
            self._db.carts[user.id] = cart
        return cart

    def add_to_cart(self, user: User, product_id: int, quantity: int) -> None:
        user.require_active()
        product = self._db.products.get(product_id)
        if product is None or not product.is_active:
            raise NotFoundError("product not found")
        cart = self.get_cart(user)
        cart.add_item(product_id, quantity)

    def update_quantity(self, user: User, product_id: int, quantity: int) -> None:
        user.require_active()
        cart = self.get_cart(user)
        cart.set_quantity(product_id, quantity)

    def remove_from_cart(self, user: User, product_id: int) -> None:
        user.require_active()
        cart = self.get_cart(user)
        cart.remove_item(product_id)

    def clear_cart(self, user: User) -> None:
        user.require_active()
        cart = self.get_cart(user)
        cart.clear()


class OrderService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_sales_order_from_cart(self, user: User, shipping_address: Address, warehouse_id: int) -> SalesOrder:
        user.require_active()
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")
        cart = self._db.carts.get(user.id)
        if cart is None or cart.is_empty():
            raise OrderError("cart is empty")
        order = SalesOrder(id=self._db.next_id("sales_order"), user_id=user.id)
        order.set_shipping_address(shipping_address)

        for item in cart.items.values():
            product = self._db.products.get(item.product_id)
            if product is None or not product.is_active:
                raise OrderError("cart contains unavailable product")
            order.add_line(product_id=product.id, unit_price=product.price, quantity=item.quantity)

        self._reserve_inventory_for_order(order, warehouse_id)
        order.reserved_from_warehouse_id = warehouse_id
        order.place()
        self._db.sales_orders[order.id] = order
        cart.clear()
        return order

    def pay_order(self, user: User, order_id: int) -> None:
        user.require_active()
        order = self._get_sales_order(order_id)
        self._require_order_owner_or_admin(user, order)
        order.mark_paid()

    def ship_order(self, actor: User, order_id: int) -> None:
        self._require_admin_or_staff(actor)
        order = self._get_sales_order(order_id)
        order.ship()

    def deliver_order(self, actor: User, order_id: int) -> None:
        self._require_admin_or_staff(actor)
        order = self._get_sales_order(order_id)
        order.deliver()

    def cancel_order(self, user: User, order_id: int) -> None:
        user.require_active()
        order = self._get_sales_order(order_id)
        self._require_order_owner_or_admin(user, order)
        prev_status = order.status
        order.cancel()
        if prev_status != OrderStatus.CANCELLED and order.status == OrderStatus.CANCELLED:
            self._release_inventory_for_order(order)

    def list_orders_for_user(self, user: User) -> List[SalesOrder]:
        user.require_active()
        orders = [o for o in self._db.sales_orders.values() if o.user_id == user.id]
        orders.sort(key=lambda o: o.id)
        return orders

    def list_all_orders(self, actor: User) -> List[SalesOrder]:
        self._require_admin_or_staff(actor)
        orders = list(self._db.sales_orders.values())
        orders.sort(key=lambda o: o.id)
        return orders

    def create_purchase_order(self, actor: User, supplier_id: int, warehouse_id: int) -> PurchaseOrder:
        self._require_admin_or_staff(actor)
        if supplier_id not in self._db.suppliers:
            raise NotFoundError("supplier not found")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")
        po = PurchaseOrder(id=self._db.next_id("purchase_order"), supplier_id=supplier_id, warehouse_id=warehouse_id)
        self._db.purchase_orders[po.id] = po
        return po

    def add_purchase_order_line(self, actor: User, purchase_order_id: int, product_id: int, unit_cost: Decimal, quantity: int) -> None:
        self._require_admin_or_staff(actor)
        po = self._get_purchase_order(purchase_order_id)
        if product_id not in self._db.products:
            raise NotFoundError("product not found")
        po.add_line(product_id=product_id, unit_cost=unit_cost, quantity=quantity)

    def submit_purchase_order(self, actor: User, purchase_order_id: int) -> None:
        self._require_admin_or_staff(actor)
        po = self._get_purchase_order(purchase_order_id)
        po.submit()

    def receive_purchase_order(self, actor: User, purchase_order_id: int) -> None:
        self._require_admin_or_staff(actor)
        po = self._get_purchase_order(purchase_order_id)
        po.receive()
        for line in po.lines:
            item = self._get_or_create_inventory(line.product_id, po.warehouse_id)
            item.add_stock(line.quantity)

    def cancel_purchase_order(self, actor: User, purchase_order_id: int) -> None:
        self._require_admin_or_staff(actor)
        po = self._get_purchase_order(purchase_order_id)
        po.cancel()

    def list_purchase_orders(self, actor: User) -> List[PurchaseOrder]:
        self._require_admin_or_staff(actor)
        pos = list(self._db.purchase_orders.values())
        pos.sort(key=lambda p: p.id)
        return pos

    def _reserve_inventory_for_order(self, order: SalesOrder, warehouse_id: int) -> None:
        for line in order.lines:
            item = self._get_or_create_inventory(line.product_id, warehouse_id)
            item.reserve(line.quantity)

    def _release_inventory_for_order(self, order: SalesOrder) -> None:
        wid = order.reserved_from_warehouse_id
        if wid is None:
            return
        for line in order.lines:
            item = self._get_or_create_inventory(line.product_id, wid)
            item.release(line.quantity)

    def _get_or_create_inventory(self, product_id: int, warehouse_id: int) -> InventoryItem:
        key = (product_id, warehouse_id)
        item = self._db.inventory.get(key)
        if item is None:
            item = InventoryItem(product_id=product_id, warehouse_id=warehouse_id, quantity_on_hand=0, quantity_reserved=0)
            self._db.inventory[key] = item
        return item

    def _get_sales_order(self, order_id: int) -> SalesOrder:
        order = self._db.sales_orders.get(order_id)
        if order is None:
            raise NotFoundError("order not found")
        return order

    def _get_purchase_order(self, purchase_order_id: int) -> PurchaseOrder:
        po = self._db.purchase_orders.get(purchase_order_id)
        if po is None:
            raise NotFoundError("purchase order not found")
        return po

    @staticmethod
    def _require_admin_or_staff(actor: User) -> None:
        actor.require_active()
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthorizationError("insufficient permissions")

    @staticmethod
    def _require_order_owner_or_admin(user: User, order: SalesOrder) -> None:
        if user.role in (Role.ADMIN, Role.STAFF):
            return
        if order.user_id != user.id:
            raise AuthorizationError("not allowed")


class UserManagementService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def set_user_active(self, actor: User, user_id: int, is_active: bool) -> None:
        self._require_admin(actor)
        u = self._db.users.get(user_id)
        if u is None:
            raise NotFoundError("user not found")
        u.is_active = bool(is_active)

    def set_user_role(self, actor: User, user_id: int, role: Role) -> None:
        self._require_admin(actor)
        if not isinstance(role, Role):
            raise ValidationError("role must be a Role")
        u = self._db.users.get(user_id)
        if u is None:
            raise NotFoundError("user not found")
        u.role = role

    def list_users(self, actor: User) -> List[User]:
        self._require_admin(actor)
        users = list(self._db.users.values())
        users.sort(key=lambda x: x.id)
        return users

    @staticmethod
    def _require_admin(actor: User) -> None:
        actor.require_active()
        if actor.role != Role.ADMIN:
            raise AuthorizationError("admin required")


class EcommerceSystem:
    def __init__(self) -> None:
        self.db = InMemoryDB()
        self.auth = AuthService(self.db)
        self.catalog = CatalogService(self.db)
        self.warehouse = WarehouseService(self.db)
        self.cart = CartService(self.db)
        self.orders = OrderService(self.db)
        self.users = UserManagementService(self.db)

    def bootstrap_admin(self, email: str, name: str, password: str) -> User:
        if any(u.role == Role.ADMIN for u in self.db.users.values()):
            raise ValidationError("admin already exists")
        admin = self.auth.sign_up(email=email, name=name, password=password, role=Role.ADMIN)
        return admin


def _self_test() -> None:
    sys = EcommerceSystem()
    admin = sys.bootstrap_admin("admin@example.com", "Admin", "password123")
    token = sys.auth.login("admin@example.com", "password123")
    admin2 = sys.auth.get_user_for_token(token)

    wh = sys.warehouse.create_warehouse(
        admin2,
        "Main Warehouse",
        Address(line1="1 Warehouse Way", city="Seattle", state="WA", postal_code="98101", country="US"),
    )
    sup = sys.warehouse.create_supplier(admin2, "Acme Supply", "acme@example.com", "555-0100")
    cat = sys.catalog.create_category(admin2, "Books")
    prod = sys.catalog.create_product(admin2, "SKU-BOOK-1", "Book One", "A great book", Decimal("19.99"), {cat.id})
    sys.warehouse.adjust_stock(admin2, prod.id, wh.id, 50)

    user = sys.auth.sign_up("user@example.com", "User", "password123", role=Role.CUSTOMER)
    sys.cart.add_to_cart(user, prod.id, 2)
    order = sys.orders.create_sales_order_from_cart(
        user,
        Address(line1="10 Main St", city="Portland", state="OR", postal_code="97201", country="US"),
        warehouse_id=wh.id,
    )
    sys.orders.pay_order(user, order.id)
    sys.orders.ship_order(admin2, order.id)
    sys.orders.deliver_order(admin2, order.id)

    po = sys.orders.create_purchase_order(admin2, sup.id, wh.id)
    sys.orders.add_purchase_order_line(admin2, po.id, prod.id, Decimal("10.00"), 10)
    sys.orders.submit_purchase_order(admin2, po.id)
    sys.orders.receive_purchase_order(admin2, po.id)


if __name__ == "__main__":
    _self_test()