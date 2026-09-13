from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
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


class InsufficientInventoryError(DomainError):
    pass


class OrderStateError(DomainError):
    pass


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    MANAGER = "manager"
    WAREHOUSE = "warehouse"


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


class InventoryMovementType(str, Enum):
    RECEIVE = "receive"
    RESERVE = "reserve"
    RELEASE = "release"
    SHIP = "ship"
    ADJUST = "adjust"


def _now() -> datetime:
    return datetime.utcnow()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    _require("@" in email and "." in email.split("@")[-1], "Invalid email")
    return email


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        _require(self.currency.strip() != "", "Currency required")
        _require(self.amount >= Decimal("0"), "Money amount cannot be negative")

    def __add__(self, other: "Money") -> "Money":
        _require(self.currency == other.currency, "Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, qty: int) -> "Money":
        _require(qty >= 0, "Quantity must be non-negative")
        return Money(self.amount * Decimal(qty), self.currency)


@dataclass
class User:
    id: int
    email: str
    password_salt: str
    password_hash: str
    roles: Tuple[Role, ...] = field(default_factory=lambda: (Role.CUSTOMER,))
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)

    def has_role(self, role: Role) -> bool:
        return role in self.roles

    def verify_password(self, password: str) -> bool:
        if not self.is_active:
            return False
        return _hash_password(password, self.password_salt) == self.password_hash


@dataclass
class Category:
    id: int
    name: str
    parent_id: Optional[int] = None

    def __post_init__(self) -> None:
        _require(self.name.strip() != "", "Category name required")


@dataclass
class Supplier:
    id: int
    name: str
    email: str

    def __post_init__(self) -> None:
        _require(self.name.strip() != "", "Supplier name required")
        self.email = _normalize_email(self.email)


@dataclass
class Warehouse:
    id: int
    name: str

    def __post_init__(self) -> None:
        _require(self.name.strip() != "", "Warehouse name required")


@dataclass
class Product:
    id: int
    sku: str
    name: str
    description: str
    price: Money
    category_id: Optional[int] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require(self.sku.strip() != "", "SKU required")
        _require(self.name.strip() != "", "Product name required")
        _require(self.description is not None, "Description required")


@dataclass
class InventoryRecord:
    product_id: int
    warehouse_id: int
    on_hand: int = 0
    reserved: int = 0

    def __post_init__(self) -> None:
        _require(self.on_hand >= 0, "On hand cannot be negative")
        _require(self.reserved >= 0, "Reserved cannot be negative")
        _require(self.reserved <= self.on_hand, "Reserved cannot exceed on hand")

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved

    def receive(self, qty: int) -> None:
        _require(qty > 0, "Receive quantity must be positive")
        self.on_hand += qty

    def reserve(self, qty: int) -> None:
        _require(qty > 0, "Reserve quantity must be positive")
        if qty > self.available:
            raise InsufficientInventoryError("Insufficient available inventory to reserve")
        self.reserved += qty

    def release(self, qty: int) -> None:
        _require(qty > 0, "Release quantity must be positive")
        _require(qty <= self.reserved, "Cannot release more than reserved")
        self.reserved -= qty

    def ship(self, qty: int) -> None:
        _require(qty > 0, "Ship quantity must be positive")
        _require(qty <= self.reserved, "Cannot ship more than reserved")
        self.reserved -= qty
        self.on_hand -= qty
        _require(self.on_hand >= 0, "On hand cannot be negative after ship")

    def adjust(self, new_on_hand: int) -> None:
        _require(new_on_hand >= 0, "New on hand cannot be negative")
        _require(new_on_hand >= self.reserved, "New on hand cannot be less than reserved")
        self.on_hand = new_on_hand


@dataclass(frozen=True)
class InventoryMovement:
    id: int
    movement_type: InventoryMovementType
    product_id: int
    warehouse_id: int
    quantity: int
    reference: str
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require(self.quantity > 0, "Movement quantity must be positive")
        _require(self.reference.strip() != "", "Movement reference required")


@dataclass
class CartItem:
    product_id: int
    quantity: int

    def __post_init__(self) -> None:
        _require(self.quantity > 0, "Cart item quantity must be positive")


@dataclass
class ShoppingCart:
    id: int
    user_id: int
    items: Dict[int, CartItem] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=_now)

    def add_item(self, product_id: int, quantity: int) -> None:
        _require(quantity > 0, "Quantity must be positive")
        if product_id in self.items:
            self.items[product_id].quantity += quantity
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def set_item_quantity(self, product_id: int, quantity: int) -> None:
        _require(quantity >= 0, "Quantity cannot be negative")
        if quantity == 0:
            self.items.pop(product_id, None)
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def remove_item(self, product_id: int) -> None:
        self.items.pop(product_id, None)
        self.updated_at = _now()

    def clear(self) -> None:
        self.items.clear()
        self.updated_at = _now()

    def list_items(self) -> List[CartItem]:
        return list(self.items.values())


@dataclass
class SalesOrderItem:
    product_id: int
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        _require(self.quantity > 0, "Order item quantity must be positive")


@dataclass
class SalesOrder:
    id: int
    user_id: int
    status: OrderStatus = OrderStatus.DRAFT
    items: List[SalesOrderItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def total(self) -> Money:
        if not self.items:
            return Money(Decimal("0"), "USD")
        currency = self.items[0].unit_price.currency
        total = Money(Decimal("0"), currency)
        for it in self.items:
            _require(it.unit_price.currency == currency, "Mixed currencies not supported")
            total = total + (it.unit_price * it.quantity)
        return total

    def _touch(self) -> None:
        self.updated_at = _now()

    def add_item(self, product_id: int, unit_price: Money, quantity: int) -> None:
        _require(self.status == OrderStatus.DRAFT, "Can only modify items in DRAFT status")
        _require(quantity > 0, "Quantity must be positive")
        self.items.append(SalesOrderItem(product_id=product_id, unit_price=unit_price, quantity=quantity))
        self._touch()

    def place(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderStateError("Order can only be placed from DRAFT")
        _require(len(self.items) > 0, "Cannot place empty order")
        self.status = OrderStatus.PLACED
        self._touch()

    def mark_paid(self) -> None:
        if self.status != OrderStatus.PLACED:
            raise OrderStateError("Order can only be paid after being PLACED")
        self.status = OrderStatus.PAID
        self._touch()

    def fulfill(self) -> None:
        if self.status != OrderStatus.PAID:
            raise OrderStateError("Order can only be fulfilled after being PAID")
        self.status = OrderStatus.FULFILLED
        self._touch()

    def cancel(self) -> None:
        if self.status in (OrderStatus.FULFILLED,):
            raise OrderStateError("Cannot cancel a fulfilled order")
        self.status = OrderStatus.CANCELLED
        self._touch()


@dataclass
class PurchaseOrderItem:
    product_id: int
    unit_cost: Money
    quantity: int

    def __post_init__(self) -> None:
        _require(self.quantity > 0, "PO item quantity must be positive")


@dataclass
class PurchaseOrder:
    id: int
    supplier_id: int
    warehouse_id: int
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    items: List[PurchaseOrderItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def _touch(self) -> None:
        self.updated_at = _now()

    def add_item(self, product_id: int, unit_cost: Money, quantity: int) -> None:
        _require(self.status == PurchaseOrderStatus.DRAFT, "Can only modify items in DRAFT status")
        _require(quantity > 0, "Quantity must be positive")
        self.items.append(PurchaseOrderItem(product_id=product_id, unit_cost=unit_cost, quantity=quantity))
        self._touch()

    def submit(self) -> None:
        if self.status != PurchaseOrderStatus.DRAFT:
            raise OrderStateError("PO can only be submitted from DRAFT")
        _require(len(self.items) > 0, "Cannot submit empty purchase order")
        self.status = PurchaseOrderStatus.SUBMITTED
        self._touch()

    def mark_received(self) -> None:
        if self.status != PurchaseOrderStatus.SUBMITTED:
            raise OrderStateError("PO can only be received after being SUBMITTED")
        self.status = PurchaseOrderStatus.RECEIVED
        self._touch()

    def cancel(self) -> None:
        if self.status == PurchaseOrderStatus.RECEIVED:
            raise OrderStateError("Cannot cancel a received purchase order")
        self.status = PurchaseOrderStatus.CANCELLED
        self._touch()


class InMemoryDB:
    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self.users: Dict[int, User] = {}
        self.categories: Dict[int, Category] = {}
        self.suppliers: Dict[int, Supplier] = {}
        self.warehouses: Dict[int, Warehouse] = {}
        self.products: Dict[int, Product] = {}
        self.inventory: Dict[Tuple[int, int], InventoryRecord] = {}
        self.inventory_movements: Dict[int, InventoryMovement] = {}
        self.carts: Dict[int, ShoppingCart] = {}
        self.sales_orders: Dict[int, SalesOrder] = {}
        self.purchase_orders: Dict[int, PurchaseOrder] = {}
        self.sessions: Dict[str, int] = {}
        self.email_index: Dict[str, int] = {}
        self.sku_index: Dict[str, int] = {}

    def next_id(self, entity: str) -> int:
        self._counters[entity] = self._counters.get(entity, 0) + 1
        return self._counters[entity]


class AuthService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def sign_up(self, email: str, password: str, roles: Optional[List[Role]] = None) -> User:
        email_n = _normalize_email(email)
        _require(password is not None and len(password) >= 8, "Password must be at least 8 characters")
        if email_n in self._db.email_index:
            raise ValidationError("Email already registered")
        salt = secrets.token_hex(16)
        pw_hash = _hash_password(password, salt)
        user_id = self._db.next_id("user")
        user_roles = tuple(roles) if roles else (Role.CUSTOMER,)
        user = User(id=user_id, email=email_n, password_salt=salt, password_hash=pw_hash, roles=user_roles)
        self._db.users[user_id] = user
        self._db.email_index[email_n] = user_id
        return user

    def login(self, email: str, password: str) -> str:
        email_n = _normalize_email(email)
        user_id = self._db.email_index.get(email_n)
        if not user_id:
            raise AuthenticationError("Invalid credentials")
        user = self._db.users[user_id]
        if not user.verify_password(password):
            raise AuthenticationError("Invalid credentials")
        token = secrets.token_urlsafe(32)
        self._db.sessions[token] = user.id
        return token

    def logout(self, token: str) -> None:
        self._db.sessions.pop(token, None)

    def get_user_for_token(self, token: str) -> User:
        user_id = self._db.sessions.get(token)
        if not user_id:
            raise AuthenticationError("Not authenticated")
        user = self._db.users.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Not authenticated")
        return user


class CatalogService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_category(self, actor: User, name: str, parent_id: Optional[int] = None) -> Category:
        self._require_admin(actor)
        if parent_id is not None and parent_id not in self._db.categories:
            raise NotFoundError("Parent category not found")
        cid = self._db.next_id("category")
        cat = Category(id=cid, name=name, parent_id=parent_id)
        self._db.categories[cid] = cat
        return cat

    def create_product(
        self,
        actor: User,
        sku: str,
        name: str,
        description: str,
        price: Money,
        category_id: Optional[int] = None,
    ) -> Product:
        self._require_admin(actor)
        sku_n = sku.strip()
        _require(sku_n != "", "SKU required")
        if sku_n in self._db.sku_index:
            raise ValidationError("SKU already exists")
        if category_id is not None and category_id not in self._db.categories:
            raise NotFoundError("Category not found")
        pid = self._db.next_id("product")
        p = Product(id=pid, sku=sku_n, name=name, description=description, price=price, category_id=category_id)
        self._db.products[pid] = p
        self._db.sku_index[sku_n] = pid
        return p

    def update_product_active(self, actor: User, product_id: int, is_active: bool) -> Product:
        self._require_admin(actor)
        p = self.get_product(product_id)
        p.is_active = bool(is_active)
        return p

    def get_product(self, product_id: int) -> Product:
        p = self._db.products.get(product_id)
        if not p:
            raise NotFoundError("Product not found")
        return p

    def list_products(self, active_only: bool = True) -> List[Product]:
        products = list(self._db.products.values())
        if active_only:
            products = [p for p in products if p.is_active]
        return sorted(products, key=lambda x: x.id)

    def search_products(self, query: str, active_only: bool = True) -> List[Product]:
        q = (query or "").strip().lower()
        if q == "":
            return self.list_products(active_only=active_only)
        res: List[Product] = []
        for p in self._db.products.values():
            if active_only and not p.is_active:
                continue
            hay = f"{p.sku} {p.name} {p.description}".lower()
            if q in hay:
                res.append(p)
        return sorted(res, key=lambda x: x.id)

    def _require_admin(self, actor: User) -> None:
        if not (actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER)):
            raise AuthorizationError("Admin privileges required")


class SupplierService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_supplier(self, actor: User, name: str, email: str) -> Supplier:
        self._require_admin(actor)
        sid = self._db.next_id("supplier")
        s = Supplier(id=sid, name=name, email=email)
        self._db.suppliers[sid] = s
        return s

    def get_supplier(self, supplier_id: int) -> Supplier:
        s = self._db.suppliers.get(supplier_id)
        if not s:
            raise NotFoundError("Supplier not found")
        return s

    def _require_admin(self, actor: User) -> None:
        if not (actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER)):
            raise AuthorizationError("Admin privileges required")


class WarehouseService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_warehouse(self, actor: User, name: str) -> Warehouse:
        self._require_admin(actor)
        wid = self._db.next_id("warehouse")
        w = Warehouse(id=wid, name=name)
        self._db.warehouses[wid] = w
        return w

    def get_warehouse(self, warehouse_id: int) -> Warehouse:
        w = self._db.warehouses.get(warehouse_id)
        if not w:
            raise NotFoundError("Warehouse not found")
        return w

    def _require_admin(self, actor: User) -> None:
        if not (actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER)):
            raise AuthorizationError("Admin privileges required")


class InventoryService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def get_record(self, product_id: int, warehouse_id: int) -> InventoryRecord:
        key = (product_id, warehouse_id)
        rec = self._db.inventory.get(key)
        if not rec:
            rec = InventoryRecord(product_id=product_id, warehouse_id=warehouse_id, on_hand=0, reserved=0)
            self._db.inventory[key] = rec
        return rec

    def list_inventory_for_product(self, product_id: int) -> List[InventoryRecord]:
        return [r for (pid, _), r in self._db.inventory.items() if pid == product_id]

    def list_inventory_for_warehouse(self, warehouse_id: int) -> List[InventoryRecord]:
        return [r for (_, wid), r in self._db.inventory.items() if wid == warehouse_id]

    def receive(self, actor: User, product_id: int, warehouse_id: int, quantity: int, reference: str) -> InventoryMovement:
        self._require_inventory_admin(actor)
        self._require_product_and_warehouse_exist(product_id, warehouse_id)
        rec = self.get_record(product_id, warehouse_id)
        rec.receive(quantity)
        return self._log(InventoryMovementType.RECEIVE, product_id, warehouse_id, quantity, reference)

    def reserve(self, actor: User, product_id: int, warehouse_id: int, quantity: int, reference: str) -> InventoryMovement:
        self._require_inventory_admin(actor)
        self._require_product_and_warehouse_exist(product_id, warehouse_id)
        rec = self.get_record(product_id, warehouse_id)
        rec.reserve(quantity)
        return self._log(InventoryMovementType.RESERVE, product_id, warehouse_id, quantity, reference)

    def release(self, actor: User, product_id: int, warehouse_id: int, quantity: int, reference: str) -> InventoryMovement:
        self._require_inventory_admin(actor)
        self._require_product_and_warehouse_exist(product_id, warehouse_id)
        rec = self.get_record(product_id, warehouse_id)
        rec.release(quantity)
        return self._log(InventoryMovementType.RELEASE, product_id, warehouse_id, quantity, reference)

    def ship(self, actor: User, product_id: int, warehouse_id: int, quantity: int, reference: str) -> InventoryMovement:
        self._require_inventory_admin(actor)
        self._require_product_and_warehouse_exist(product_id, warehouse_id)
        rec = self.get_record(product_id, warehouse_id)
        rec.ship(quantity)
        return self._log(InventoryMovementType.SHIP, product_id, warehouse_id, quantity, reference)

    def adjust(self, actor: User, product_id: int, warehouse_id: int, new_on_hand: int, reference: str) -> InventoryMovement:
        self._require_inventory_admin(actor)
        self._require_product_and_warehouse_exist(product_id, warehouse_id)
        rec = self.get_record(product_id, warehouse_id)
        current = rec.on_hand
        rec.adjust(new_on_hand)
        delta = new_on_hand - current
        qty = abs(delta)
        _require(qty > 0, "No adjustment needed")
        return self._log(InventoryMovementType.ADJUST, product_id, warehouse_id, qty, reference)

    def _log(
        self,
        movement_type: InventoryMovementType,
        product_id: int,
        warehouse_id: int,
        quantity: int,
        reference: str,
    ) -> InventoryMovement:
        mid = self._db.next_id("inventory_movement")
        mv = InventoryMovement(
            id=mid,
            movement_type=movement_type,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reference=reference,
        )
        self._db.inventory_movements[mid] = mv
        return mv

    def _require_product_and_warehouse_exist(self, product_id: int, warehouse_id: int) -> None:
        if product_id not in self._db.products:
            raise NotFoundError("Product not found")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("Warehouse not found")

    def _require_inventory_admin(self, actor: User) -> None:
        if not (actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER) or actor.has_role(Role.WAREHOUSE)):
            raise AuthorizationError("Inventory privileges required")


class CartService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def get_or_create_cart(self, user_id: int) -> ShoppingCart:
        cart = self._db.carts.get(user_id)
        if cart:
            return cart
        cid = self._db.next_id("cart")
        cart = ShoppingCart(id=cid, user_id=user_id)
        self._db.carts[user_id] = cart
        return cart

    def add_to_cart(self, actor: User, product_id: int, quantity: int) -> ShoppingCart:
        p = self._db.products.get(product_id)
        if not p or not p.is_active:
            raise NotFoundError("Product not found")
        cart = self.get_or_create_cart(actor.id)
        cart.add_item(product_id, quantity)
        return cart

    def update_quantity(self, actor: User, product_id: int, quantity: int) -> ShoppingCart:
        cart = self.get_or_create_cart(actor.id)
        cart.set_item_quantity(product_id, quantity)
        return cart

    def remove_from_cart(self, actor: User, product_id: int) -> ShoppingCart:
        cart = self.get_or_create_cart(actor.id)
        cart.remove_item(product_id)
        return cart

    def clear_cart(self, actor: User) -> ShoppingCart:
        cart = self.get_or_create_cart(actor.id)
        cart.clear()
        return cart


class OrderService:
    def __init__(self, db: InMemoryDB, inventory: InventoryService) -> None:
        self._db = db
        self._inventory = inventory

    def create_sales_order_from_cart(self, actor: User, warehouse_id: int) -> SalesOrder:
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("Warehouse not found")
        cart = self._db.carts.get(actor.id)
        _require(cart is not None and len(cart.items) > 0, "Cart is empty")
        for item in cart.list_items():
            p = self._db.products.get(item.product_id)
            if not p or not p.is_active:
                raise NotFoundError("Product not found")
            rec = self._inventory.get_record(item.product_id, warehouse_id)
            if item.quantity > rec.available:
                raise InsufficientInventoryError("Insufficient inventory for one or more items")

        oid = self._db.next_id("sales_order")
        order = SalesOrder(id=oid, user_id=actor.id)
        for item in cart.list_items():
            p = self._db.products[item.product_id]
            order.add_item(product_id=p.id, unit_price=p.price, quantity=item.quantity)
        order.place()

        for item in cart.list_items():
            self._inventory.reserve(
                actor=self._system_inventory_actor(),
                product_id=item.product_id,
                warehouse_id=warehouse_id,
                quantity=item.quantity,
                reference=f"SO#{order.id}",
            )

        cart.clear()
        self._db.sales_orders[order.id] = order
        return order

    def mark_sales_order_paid(self, actor: User, order_id: int) -> SalesOrder:
        order = self.get_sales_order(order_id)
        self._require_order_access(actor, order)
        order.mark_paid()
        return order

    def fulfill_sales_order(self, actor: User, order_id: int, warehouse_id: int) -> SalesOrder:
        order = self.get_sales_order(order_id)
        self._require_admin_or_warehouse(actor)
        _require(order.status == OrderStatus.PAID, "Order must be PAID to fulfill")
        for it in order.items:
            self._inventory.ship(
                actor=self._system_inventory_actor(),
                product_id=it.product_id,
                warehouse_id=warehouse_id,
                quantity=it.quantity,
                reference=f"SO#{order.id}",
            )
        order.fulfill()
        return order

    def cancel_sales_order(self, actor: User, order_id: int, warehouse_id: int) -> SalesOrder:
        order = self.get_sales_order(order_id)
        self._require_order_access(actor, order)
        if order.status in (OrderStatus.FULFILLED,):
            raise OrderStateError("Cannot cancel fulfilled order")
        if order.status in (OrderStatus.PLACED, OrderStatus.PAID):
            for it in order.items:
                rec = self._inventory.get_record(it.product_id, warehouse_id)
                if it.quantity <= rec.reserved:
                    self._inventory.release(
                        actor=self._system_inventory_actor(),
                        product_id=it.product_id,
                        warehouse_id=warehouse_id,
                        quantity=it.quantity,
                        reference=f"SO#{order.id}",
                    )
        order.cancel()
        return order

    def get_sales_order(self, order_id: int) -> SalesOrder:
        o = self._db.sales_orders.get(order_id)
        if not o:
            raise NotFoundError("Sales order not found")
        return o

    def list_sales_orders_for_user(self, actor: User) -> List[SalesOrder]:
        if actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER):
            return sorted(self._db.sales_orders.values(), key=lambda x: x.id)
        return sorted([o for o in self._db.sales_orders.values() if o.user_id == actor.id], key=lambda x: x.id)

    def create_purchase_order(self, actor: User, supplier_id: int, warehouse_id: int) -> PurchaseOrder:
        self._require_admin_or_warehouse(actor)
        if supplier_id not in self._db.suppliers:
            raise NotFoundError("Supplier not found")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("Warehouse not found")
        po_id = self._db.next_id("purchase_order")
        po = PurchaseOrder(id=po_id, supplier_id=supplier_id, warehouse_id=warehouse_id)
        self._db.purchase_orders[po.id] = po
        return po

    def add_item_to_purchase_order(self, actor: User, purchase_order_id: int, product_id: int, unit_cost: Money, quantity: int) -> PurchaseOrder:
        self._require_admin_or_warehouse(actor)
        po = self.get_purchase_order(purchase_order_id)
        if product_id not in self._db.products:
            raise NotFoundError("Product not found")
        po.add_item(product_id=product_id, unit_cost=unit_cost, quantity=quantity)
        return po

    def submit_purchase_order(self, actor: User, purchase_order_id: int) -> PurchaseOrder:
        self._require_admin_or_warehouse(actor)
        po = self.get_purchase_order(purchase_order_id)
        po.submit()
        return po

    def receive_purchase_order(self, actor: User, purchase_order_id: int, reference: Optional[str] = None) -> PurchaseOrder:
        self._require_admin_or_warehouse(actor)
        po = self.get_purchase_order(purchase_order_id)
        po.mark_received()
        ref = reference.strip() if reference else f"PO#{po.id}"
        for it in po.items:
            self._inventory.receive(
                actor=self._system_inventory_actor(),
                product_id=it.product_id,
                warehouse_id=po.warehouse_id,
                quantity=it.quantity,
                reference=ref,
            )
        return po

    def cancel_purchase_order(self, actor: User, purchase_order_id: int) -> PurchaseOrder:
        self._require_admin_or_warehouse(actor)
        po = self.get_purchase_order(purchase_order_id)
        po.cancel()
        return po

    def get_purchase_order(self, purchase_order_id: int) -> PurchaseOrder:
        po = self._db.purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        return po

    def list_purchase_orders(self, actor: User) -> List[PurchaseOrder]:
        self._require_admin_or_warehouse(actor)
        return sorted(self._db.purchase_orders.values(), key=lambda x: x.id)

    def _require_order_access(self, actor: User, order: SalesOrder) -> None:
        if actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER):
            return
        if order.user_id != actor.id:
            raise AuthorizationError("Not allowed")

    def _require_admin_or_warehouse(self, actor: User) -> None:
        if not (actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER) or actor.has_role(Role.WAREHOUSE)):
            raise AuthorizationError("Privileges required")

    def _system_inventory_actor(self) -> User:
        return User(
            id=0,
            email="system@local",
            password_salt="",
            password_hash="",
            roles=(Role.ADMIN,),
            is_active=True,
        )


class UserManagementService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def set_active(self, actor: User, user_id: int, is_active: bool) -> User:
        self._require_admin(actor)
        u = self._db.users.get(user_id)
        if not u:
            raise NotFoundError("User not found")
        u.is_active = bool(is_active)
        return u

    def set_roles(self, actor: User, user_id: int, roles: List[Role]) -> User:
        self._require_admin(actor)
        _require(roles is not None and len(roles) > 0, "At least one role required")
        u = self._db.users.get(user_id)
        if not u:
            raise NotFoundError("User not found")
        u.roles = tuple(roles)
        return u

    def list_users(self, actor: User) -> List[User]:
        self._require_admin(actor)
        return sorted(self._db.users.values(), key=lambda x: x.id)

    def _require_admin(self, actor: User) -> None:
        if not (actor.has_role(Role.ADMIN) or actor.has_role(Role.MANAGER)):
            raise AuthorizationError("Admin privileges required")


class AmazonCloneApp:
    def __init__(self) -> None:
        self.db = InMemoryDB()
        self.auth = AuthService(self.db)
        self.catalog = CatalogService(self.db)
        self.suppliers = SupplierService(self.db)
        self.warehouses = WarehouseService(self.db)
        self.inventory = InventoryService(self.db)
        self.carts = CartService(self.db)
        self.orders = OrderService(self.db, self.inventory)
        self.users = UserManagementService(self.db)

    def bootstrap_admin(self, email: str, password: str) -> User:
        if self.db.email_index.get(_normalize_email(email)):
            raise ValidationError("Admin already exists with this email")
        return self.auth.sign_up(email=email, password=password, roles=[Role.ADMIN])


def _demo_smoke_test() -> None:
    app = AmazonCloneApp()
    admin = app.bootstrap_admin("admin@example.com", "password123")
    token = app.auth.login("admin@example.com", "password123")
    admin_user = app.auth.get_user_for_token(token)

    wh = app.warehouses.create_warehouse(admin_user, "Main Warehouse")
    cat = app.catalog.create_category(admin_user, "Books")
    p = app.catalog.create_product(
        admin_user,
        sku="BOOK-001",
        name="Example Book",
        description="A book",
        price=Money(Decimal("19.99"), "USD"),
        category_id=cat.id,
    )
    sup = app.suppliers.create_supplier(admin_user, "Acme Supply", "supply@acme.com")
    po = app.orders.create_purchase_order(admin_user, supplier_id=sup.id, warehouse_id=wh.id)
    app.orders.add_item_to_purchase_order(admin_user, po.id, product_id=p.id, unit_cost=Money(Decimal("10.00"), "USD"), quantity=10)
    app.orders.submit_purchase_order(admin_user, po.id)
    app.orders.receive_purchase_order(admin_user, po.id)

    customer = app.auth.sign_up("user@example.com", "password123", roles=[Role.CUSTOMER])
    app.carts.add_to_cart(customer, p.id, 2)
    so = app.orders.create_sales_order_from_cart(customer, warehouse_id=wh.id)
    app.orders.mark_sales_order_paid(customer, so.id)
    app.orders.fulfill_sales_order(admin_user, so.id, warehouse_id=wh.id)


if __name__ == "__main__":
    _demo_smoke_test()