from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import secrets


class DomainError(ValueError):
    pass


class AuthError(PermissionError):
    pass


class NotFoundError(LookupError):
    pass


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    STAFF = "staff"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    PLACED = "placed"
    PAID = "paid"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    CANCELLED = "cancelled"


def _now() -> datetime:
    return datetime.utcnow()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DomainError(message)


def _normalize_email(email: str) -> str:
    _require(isinstance(email, str) and email.strip(), "Email is required")
    return email.strip().lower()


def _hash_password(password: str, salt: str) -> str:
    _require(isinstance(password, str) and len(password) >= 8, "Password must be at least 8 characters")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()


def _money(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        v = value
    else:
        v = Decimal(str(value))
    _require(v >= Decimal("0"), "Money value cannot be negative")
    return v.quantize(Decimal("0.01"))


def _qty(value: int) -> int:
    _require(isinstance(value, int), "Quantity must be an integer")
    _require(value >= 0, "Quantity cannot be negative")
    return value


@dataclass(frozen=True)
class Address:
    line1: str
    city: str
    state: str
    postal_code: str
    country: str
    line2: str = ""

    def __post_init__(self) -> None:
        _require(self.line1.strip(), "Address line1 is required")
        _require(self.city.strip(), "City is required")
        _require(self.state.strip(), "State is required")
        _require(self.postal_code.strip(), "Postal code is required")
        _require(self.country.strip(), "Country is required")


@dataclass
class User:
    id: int
    email: str
    role: Role
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    _password_salt: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)
    _password_hash: str = field(default="", repr=False)

    def set_password(self, password: str) -> None:
        self._password_hash = _hash_password(password, self._password_salt)

    def check_password(self, password: str) -> bool:
        if not self._password_hash:
            return False
        return secrets.compare_digest(self._password_hash, _hash_password(password, self._password_salt))

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class Supplier:
    id: int
    name: str
    email: str
    phone: str = ""
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require(self.name.strip(), "Supplier name is required")
        self.email = _normalize_email(self.email)


@dataclass
class Warehouse:
    id: int
    name: str
    address: Address
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require(self.name.strip(), "Warehouse name is required")


@dataclass
class Product:
    id: int
    sku: str
    name: str
    description: str
    price: Decimal
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require(self.sku.strip(), "SKU is required")
        _require(self.name.strip(), "Product name is required")
        self.price = _money(self.price)

    def set_price(self, price: Decimal | int | str) -> None:
        self.price = _money(price)

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class InventoryTransaction:
    id: int
    product_id: int
    warehouse_id: int
    delta: int
    reason: str
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require(self.reason.strip(), "Transaction reason is required")
        _require(isinstance(self.delta, int) and self.delta != 0, "Delta must be a non-zero integer")


@dataclass
class InventoryItem:
    product_id: int
    warehouse_id: int
    quantity_on_hand: int = 0
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.quantity_on_hand = _qty(self.quantity_on_hand)

    def apply_delta(self, delta: int) -> None:
        _require(isinstance(delta, int) and delta != 0, "Delta must be a non-zero integer")
        new_qty = self.quantity_on_hand + delta
        _require(new_qty >= 0, "Insufficient inventory")
        self.quantity_on_hand = new_qty
        self.updated_at = _now()


@dataclass
class CartItem:
    product_id: int
    quantity: int

    def __post_init__(self) -> None:
        _require(self.quantity > 0, "Cart item quantity must be positive")


@dataclass
class Cart:
    user_id: int
    items: Dict[int, CartItem] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=_now)

    def add(self, product_id: int, quantity: int = 1) -> None:
        _require(quantity > 0, "Quantity must be positive")
        if product_id in self.items:
            self.items[product_id].quantity += quantity
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def set_quantity(self, product_id: int, quantity: int) -> None:
        _require(quantity >= 0, "Quantity cannot be negative")
        if quantity == 0:
            self.items.pop(product_id, None)
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def remove(self, product_id: int) -> None:
        self.items.pop(product_id, None)
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
        self.unit_price = _money(self.unit_price)
        _require(self.quantity > 0, "Order line quantity must be positive")

    @property
    def line_total(self) -> Decimal:
        return _money(self.unit_price * self.quantity)


@dataclass
class SalesOrder:
    id: int
    user_id: int
    status: OrderStatus
    shipping_address: Address
    lines: List[OrderLine] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    paid_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        _require(self.status in OrderStatus, "Invalid order status")

    @property
    def total(self) -> Decimal:
        total = sum((line.line_total for line in self.lines), Decimal("0.00"))
        return _money(total)

    def place(self) -> None:
        _require(self.status == OrderStatus.DRAFT, "Only draft orders can be placed")
        _require(len(self.lines) > 0, "Cannot place an order with no lines")
        self.status = OrderStatus.PLACED
        self.updated_at = _now()

    def mark_paid(self) -> None:
        _require(self.status in (OrderStatus.PLACED,), "Only placed orders can be paid")
        self.status = OrderStatus.PAID
        self.paid_at = _now()
        self.updated_at = self.paid_at

    def fulfill(self) -> None:
        _require(self.status == OrderStatus.PAID, "Only paid orders can be fulfilled")
        self.status = OrderStatus.FULFILLED
        self.fulfilled_at = _now()
        self.updated_at = self.fulfilled_at

    def cancel(self) -> None:
        _require(self.status in (OrderStatus.DRAFT, OrderStatus.PLACED), "Only draft or placed orders can be cancelled")
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = _now()
        self.updated_at = self.cancelled_at


@dataclass
class PurchaseOrderLine:
    product_id: int
    unit_cost: Decimal
    quantity: int

    def __post_init__(self) -> None:
        self.unit_cost = _money(self.unit_cost)
        _require(self.quantity > 0, "Purchase order line quantity must be positive")

    @property
    def line_total(self) -> Decimal:
        return _money(self.unit_cost * self.quantity)


@dataclass
class PurchaseOrder:
    id: int
    supplier_id: int
    warehouse_id: int
    status: PurchaseOrderStatus
    lines: List[PurchaseOrderLine] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    submitted_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        _require(self.status in PurchaseOrderStatus, "Invalid purchase order status")

    @property
    def total(self) -> Decimal:
        total = sum((line.line_total for line in self.lines), Decimal("0.00"))
        return _money(total)

    def submit(self) -> None:
        _require(self.status == PurchaseOrderStatus.DRAFT, "Only draft purchase orders can be submitted")
        _require(len(self.lines) > 0, "Cannot submit a purchase order with no lines")
        self.status = PurchaseOrderStatus.SUBMITTED
        self.submitted_at = _now()
        self.updated_at = self.submitted_at

    def receive(self) -> None:
        _require(self.status == PurchaseOrderStatus.SUBMITTED, "Only submitted purchase orders can be received")
        self.status = PurchaseOrderStatus.RECEIVED
        self.received_at = _now()
        self.updated_at = self.received_at

    def cancel(self) -> None:
        _require(self.status in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.SUBMITTED), "Only draft or submitted purchase orders can be cancelled")
        self.status = PurchaseOrderStatus.CANCELLED
        self.cancelled_at = _now()
        self.updated_at = self.cancelled_at


class InMemoryDB:
    def __init__(self) -> None:
        self._next_ids: Dict[str, int] = {}
        self.users: Dict[int, User] = {}
        self.products: Dict[int, Product] = {}
        self.suppliers: Dict[int, Supplier] = {}
        self.warehouses: Dict[int, Warehouse] = {}
        self.carts: Dict[int, Cart] = {}
        self.sales_orders: Dict[int, SalesOrder] = {}
        self.purchase_orders: Dict[int, PurchaseOrder] = {}
        self.inventory: Dict[Tuple[int, int], InventoryItem] = {}
        self.inventory_txns: Dict[int, InventoryTransaction] = {}

    def next_id(self, entity: str) -> int:
        n = self._next_ids.get(entity, 1)
        self._next_ids[entity] = n + 1
        return n


class AuthService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db
        self._sessions: Dict[str, int] = {}

    def signup(self, email: str, password: str, role: Role = Role.CUSTOMER) -> User:
        email_n = _normalize_email(email)
        _require(role in Role, "Invalid role")
        for u in self._db.users.values():
            if u.email == email_n:
                raise DomainError("Email already in use")
        user = User(id=self._db.next_id("user"), email=email_n, role=role)
        user.set_password(password)
        self._db.users[user.id] = user
        self._db.carts[user.id] = Cart(user_id=user.id)
        return user

    def login(self, email: str, password: str) -> str:
        email_n = _normalize_email(email)
        user = next((u for u in self._db.users.values() if u.email == email_n), None)
        if user is None or not user.is_active or not user.check_password(password):
            raise AuthError("Invalid credentials")
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user.id
        return token

    def logout(self, token: str) -> None:
        self._sessions.pop(token, None)

    def get_user_for_token(self, token: str) -> User:
        uid = self._sessions.get(token)
        if uid is None:
            raise AuthError("Not authenticated")
        user = self._db.users.get(uid)
        if user is None or not user.is_active:
            raise AuthError("User inactive or not found")
        return user


class CatalogService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def list_products(self, include_inactive: bool = False) -> List[Product]:
        products = list(self._db.products.values())
        if not include_inactive:
            products = [p for p in products if p.is_active]
        products.sort(key=lambda p: (p.name.lower(), p.id))
        return products

    def search_products(self, query: str) -> List[Product]:
        q = (query or "").strip().lower()
        _require(q, "Query is required")
        results: List[Product] = []
        for p in self._db.products.values():
            if not p.is_active:
                continue
            hay = f"{p.sku} {p.name} {p.description}".lower()
            if q in hay:
                results.append(p)
        results.sort(key=lambda p: (p.name.lower(), p.id))
        return results

    def get_product_detail(self, product_id: int) -> Product:
        p = self._db.products.get(product_id)
        if p is None or not p.is_active:
            raise NotFoundError("Product not found")
        return p


class AdminService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def _require_admin(self, user: User) -> None:
        if user.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("Admin privileges required")

    def create_product(self, admin: User, sku: str, name: str, description: str, price: Decimal | int | str) -> Product:
        self._require_admin(admin)
        sku_n = sku.strip()
        _require(sku_n, "SKU is required")
        for p in self._db.products.values():
            if p.sku == sku_n:
                raise DomainError("SKU already exists")
        product = Product(
            id=self._db.next_id("product"),
            sku=sku_n,
            name=name.strip(),
            description=(description or "").strip(),
            price=_money(price),
        )
        self._db.products[product.id] = product
        return product

    def update_product_price(self, admin: User, product_id: int, price: Decimal | int | str) -> Product:
        self._require_admin(admin)
        p = self._db.products.get(product_id)
        if p is None:
            raise NotFoundError("Product not found")
        p.set_price(price)
        return p

    def set_product_active(self, admin: User, product_id: int, is_active: bool) -> Product:
        self._require_admin(admin)
        p = self._db.products.get(product_id)
        if p is None:
            raise NotFoundError("Product not found")
        p.is_active = bool(is_active)
        return p

    def create_supplier(self, admin: User, name: str, email: str, phone: str = "") -> Supplier:
        self._require_admin(admin)
        supplier = Supplier(id=self._db.next_id("supplier"), name=name.strip(), email=email, phone=(phone or "").strip())
        self._db.suppliers[supplier.id] = supplier
        return supplier

    def create_warehouse(self, admin: User, name: str, address: Address) -> Warehouse:
        self._require_admin(admin)
        wh = Warehouse(id=self._db.next_id("warehouse"), name=name.strip(), address=address)
        self._db.warehouses[wh.id] = wh
        return wh

    def adjust_inventory(self, admin: User, product_id: int, warehouse_id: int, delta: int, reason: str) -> InventoryTransaction:
        self._require_admin(admin)
        _require(product_id in self._db.products, "Product not found")
        _require(warehouse_id in self._db.warehouses, "Warehouse not found")
        _require(isinstance(delta, int) and delta != 0, "Delta must be a non-zero integer")
        key = (product_id, warehouse_id)
        item = self._db.inventory.get(key)
        if item is None:
            item = InventoryItem(product_id=product_id, warehouse_id=warehouse_id, quantity_on_hand=0)
            self._db.inventory[key] = item
        item.apply_delta(delta)
        txn = InventoryTransaction(
            id=self._db.next_id("inventory_txn"),
            product_id=product_id,
            warehouse_id=warehouse_id,
            delta=delta,
            reason=reason.strip(),
        )
        self._db.inventory_txns[txn.id] = txn
        return txn

    def list_inventory(self, admin: User, warehouse_id: Optional[int] = None) -> List[InventoryItem]:
        self._require_admin(admin)
        items = list(self._db.inventory.values())
        if warehouse_id is not None:
            items = [i for i in items if i.warehouse_id == warehouse_id]
        items.sort(key=lambda i: (i.warehouse_id, i.product_id))
        return items

    def list_users(self, admin: User) -> List[User]:
        self._require_admin(admin)
        users = list(self._db.users.values())
        users.sort(key=lambda u: (u.email, u.id))
        return users

    def set_user_active(self, admin: User, user_id: int, is_active: bool) -> User:
        self._require_admin(admin)
        u = self._db.users.get(user_id)
        if u is None:
            raise NotFoundError("User not found")
        u.is_active = bool(is_active)
        return u


class CartService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def get_cart(self, user: User) -> Cart:
        cart = self._db.carts.get(user.id)
        if cart is None:
            cart = Cart(user_id=user.id)
            self._db.carts[user.id] = cart
        return cart

    def add_to_cart(self, user: User, product_id: int, quantity: int = 1) -> Cart:
        p = self._db.products.get(product_id)
        if p is None or not p.is_active:
            raise NotFoundError("Product not found")
        cart = self.get_cart(user)
        cart.add(product_id, quantity)
        return cart

    def set_cart_quantity(self, user: User, product_id: int, quantity: int) -> Cart:
        cart = self.get_cart(user)
        cart.set_quantity(product_id, quantity)
        return cart

    def remove_from_cart(self, user: User, product_id: int) -> Cart:
        cart = self.get_cart(user)
        cart.remove(product_id)
        return cart

    def clear_cart(self, user: User) -> Cart:
        cart = self.get_cart(user)
        cart.clear()
        return cart

    def cart_total(self, user: User) -> Decimal:
        cart = self.get_cart(user)
        total = Decimal("0.00")
        for item in cart.items.values():
            p = self._db.products.get(item.product_id)
            if p is None or not p.is_active:
                continue
            total += p.price * item.quantity
        return _money(total)


class OrderService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def _available_stock(self, product_id: int, warehouse_id: int) -> int:
        item = self._db.inventory.get((product_id, warehouse_id))
        return item.quantity_on_hand if item else 0

    def _reserve_stock(self, product_id: int, warehouse_id: int, quantity: int, reason: str) -> None:
        _require(quantity > 0, "Quantity must be positive")
        key = (product_id, warehouse_id)
        item = self._db.inventory.get(key)
        if item is None:
            item = InventoryItem(product_id=product_id, warehouse_id=warehouse_id, quantity_on_hand=0)
            self._db.inventory[key] = item
        item.apply_delta(-quantity)
        txn = InventoryTransaction(
            id=self._db.next_id("inventory_txn"),
            product_id=product_id,
            warehouse_id=warehouse_id,
            delta=-quantity,
            reason=reason,
        )
        self._db.inventory_txns[txn.id] = txn

    def _release_stock(self, product_id: int, warehouse_id: int, quantity: int, reason: str) -> None:
        _require(quantity > 0, "Quantity must be positive")
        key = (product_id, warehouse_id)
        item = self._db.inventory.get(key)
        if item is None:
            item = InventoryItem(product_id=product_id, warehouse_id=warehouse_id, quantity_on_hand=0)
            self._db.inventory[key] = item
        item.apply_delta(quantity)
        txn = InventoryTransaction(
            id=self._db.next_id("inventory_txn"),
            product_id=product_id,
            warehouse_id=warehouse_id,
            delta=quantity,
            reason=reason,
        )
        self._db.inventory_txns[txn.id] = txn

    def create_sales_order_from_cart(self, user: User, shipping_address: Address, warehouse_id: int) -> SalesOrder:
        _require(warehouse_id in self._db.warehouses, "Warehouse not found")
        cart = self._db.carts.get(user.id)
        if cart is None or cart.is_empty():
            raise DomainError("Cart is empty")

        lines: List[OrderLine] = []
        for ci in cart.items.values():
            p = self._db.products.get(ci.product_id)
            if p is None or not p.is_active:
                raise DomainError("Cart contains unavailable product")
            _require(ci.quantity > 0, "Invalid cart quantity")
            available = self._available_stock(p.id, warehouse_id)
            _require(available >= ci.quantity, f"Insufficient inventory for product {p.sku}")
            lines.append(OrderLine(product_id=p.id, unit_price=p.price, quantity=ci.quantity))

        order = SalesOrder(
            id=self._db.next_id("sales_order"),
            user_id=user.id,
            status=OrderStatus.DRAFT,
            shipping_address=shipping_address,
            lines=lines,
        )
        self._db.sales_orders[order.id] = order
        return order

    def place_order(self, user: User, order_id: int, warehouse_id: int) -> SalesOrder:
        _require(warehouse_id in self._db.warehouses, "Warehouse not found")
        order = self._db.sales_orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Order not found")
        _require(order.status == OrderStatus.DRAFT, "Order cannot be placed")
        for line in order.lines:
            available = self._available_stock(line.product_id, warehouse_id)
            _require(available >= line.quantity, "Insufficient inventory to place order")
        for line in order.lines:
            self._reserve_stock(line.product_id, warehouse_id, line.quantity, reason=f"Reserve for sales order {order.id}")
        order.place()
        cart = self._db.carts.get(user.id)
        if cart:
            cart.clear()
        return order

    def pay_order(self, user: User, order_id: int) -> SalesOrder:
        order = self._db.sales_orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Order not found")
        order.mark_paid()
        return order

    def fulfill_order(self, admin: User, order_id: int) -> SalesOrder:
        if admin.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("Admin privileges required")
        order = self._db.sales_orders.get(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        order.fulfill()
        return order

    def cancel_order(self, user: User, order_id: int, warehouse_id: int) -> SalesOrder:
        _require(warehouse_id in self._db.warehouses, "Warehouse not found")
        order = self._db.sales_orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Order not found")
        _require(order.status in (OrderStatus.DRAFT, OrderStatus.PLACED), "Order cannot be cancelled")
        if order.status == OrderStatus.PLACED:
            for line in order.lines:
                self._release_stock(line.product_id, warehouse_id, line.quantity, reason=f"Release for cancelled sales order {order.id}")
        order.cancel()
        return order

    def list_orders_for_user(self, user: User) -> List[SalesOrder]:
        orders = [o for o in self._db.sales_orders.values() if o.user_id == user.id]
        orders.sort(key=lambda o: (o.created_at, o.id))
        return orders

    def list_all_orders(self, admin: User) -> List[SalesOrder]:
        if admin.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("Admin privileges required")
        orders = list(self._db.sales_orders.values())
        orders.sort(key=lambda o: (o.created_at, o.id))
        return orders


class ProcurementService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def _require_admin(self, user: User) -> None:
        if user.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("Admin privileges required")

    def create_purchase_order(
        self,
        admin: User,
        supplier_id: int,
        warehouse_id: int,
        lines: List[Tuple[int, Decimal | int | str, int]],
    ) -> PurchaseOrder:
        self._require_admin(admin)
        _require(supplier_id in self._db.suppliers, "Supplier not found")
        _require(warehouse_id in self._db.warehouses, "Warehouse not found")
        _require(lines and len(lines) > 0, "Purchase order lines are required")

        po_lines: List[PurchaseOrderLine] = []
        for product_id, unit_cost, quantity in lines:
            _require(product_id in self._db.products, "Product not found")
            po_lines.append(PurchaseOrderLine(product_id=product_id, unit_cost=_money(unit_cost), quantity=int(quantity)))

        po = PurchaseOrder(
            id=self._db.next_id("purchase_order"),
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            status=PurchaseOrderStatus.DRAFT,
            lines=po_lines,
        )
        self._db.purchase_orders[po.id] = po
        return po

    def submit_purchase_order(self, admin: User, purchase_order_id: int) -> PurchaseOrder:
        self._require_admin(admin)
        po = self._db.purchase_orders.get(purchase_order_id)
        if po is None:
            raise NotFoundError("Purchase order not found")
        po.submit()
        return po

    def receive_purchase_order(self, admin: User, purchase_order_id: int) -> PurchaseOrder:
        self._require_admin(admin)
        po = self._db.purchase_orders.get(purchase_order_id)
        if po is None:
            raise NotFoundError("Purchase order not found")
        _require(po.status == PurchaseOrderStatus.SUBMITTED, "Purchase order cannot be received")
        for line in po.lines:
            key = (line.product_id, po.warehouse_id)
            item = self._db.inventory.get(key)
            if item is None:
                item = InventoryItem(product_id=line.product_id, warehouse_id=po.warehouse_id, quantity_on_hand=0)
                self._db.inventory[key] = item
            item.apply_delta(line.quantity)
            txn = InventoryTransaction(
                id=self._db.next_id("inventory_txn"),
                product_id=line.product_id,
                warehouse_id=po.warehouse_id,
                delta=line.quantity,
                reason=f"Receive purchase order {po.id}",
            )
            self._db.inventory_txns[txn.id] = txn
        po.receive()
        return po

    def cancel_purchase_order(self, admin: User, purchase_order_id: int) -> PurchaseOrder:
        self._require_admin(admin)
        po = self._db.purchase_orders.get(purchase_order_id)
        if po is None:
            raise NotFoundError("Purchase order not found")
        po.cancel()
        return po

    def list_purchase_orders(self, admin: User) -> List[PurchaseOrder]:
        self._require_admin(admin)
        pos = list(self._db.purchase_orders.values())
        pos.sort(key=lambda p: (p.created_at, p.id))
        return pos


class AmazonCloneSystem:
    def __init__(self) -> None:
        self.db = InMemoryDB()
        self.auth = AuthService(self.db)
        self.catalog = CatalogService(self.db)
        self.admin = AdminService(self.db)
        self.cart = CartService(self.db)
        self.orders = OrderService(self.db)
        self.procurement = ProcurementService(self.db)

    def seed_admin(self, email: str, password: str) -> User:
        admin = self.auth.signup(email=email, password=password, role=Role.ADMIN)
        return admin


def _demo_smoke_test() -> None:
    system = AmazonCloneSystem()
    admin = system.seed_admin("admin@example.com", "password123")

    wh = system.admin.create_warehouse(
        admin,
        "Main Warehouse",
        Address(line1="1 Warehouse Way", city="Seattle", state="WA", postal_code="98101", country="US"),
    )
    supplier = system.admin.create_supplier(admin, "Acme Supply", "supplier@acme.com")

    p1 = system.admin.create_product(admin, "SKU-1", "Widget", "A useful widget", "19.99")
    p2 = system.admin.create_product(admin, "SKU-2", "Gadget", "A fancy gadget", "49.50")

    po = system.procurement.create_purchase_order(
        admin,
        supplier_id=supplier.id,
        warehouse_id=wh.id,
        lines=[(p1.id, "10.00", 100), (p2.id, "30.00", 50)],
    )
    system.procurement.submit_purchase_order(admin, po.id)
    system.procurement.receive_purchase_order(admin, po.id)

    user = system.auth.signup("user@example.com", "password123", role=Role.CUSTOMER)
    system.cart.add_to_cart(user, p1.id, 2)
    system.cart.add_to_cart(user, p2.id, 1)

    order = system.orders.create_sales_order_from_cart(
        user,
        shipping_address=Address(line1="123 Main St", city="Portland", state="OR", postal_code="97201", country="US"),
        warehouse_id=wh.id,
    )
    system.orders.place_order(user, order.id, warehouse_id=wh.id)
    system.orders.pay_order(user, order.id)
    system.orders.fulfill_order(admin, order.id)


if __name__ == "__main__":
    _demo_smoke_test()