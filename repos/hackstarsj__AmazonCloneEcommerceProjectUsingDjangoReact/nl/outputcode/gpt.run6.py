from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import secrets
import re


class DomainError(ValueError):
    pass


class AuthError(PermissionError):
    pass


class NotFoundError(LookupError):
    pass


class Validation:
    EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @staticmethod
    def require_non_empty(value: str, field_name: str) -> str:
        if value is None or not str(value).strip():
            raise DomainError(f"{field_name} is required")
        return str(value).strip()

    @staticmethod
    def require_email(email: str) -> str:
        email = Validation.require_non_empty(email, "email").lower()
        if not Validation.EMAIL_RE.match(email):
            raise DomainError("invalid email")
        return email

    @staticmethod
    def require_positive_int(value: int, field_name: str) -> int:
        if not isinstance(value, int) or value <= 0:
            raise DomainError(f"{field_name} must be a positive integer")
        return value

    @staticmethod
    def require_non_negative_int(value: int, field_name: str) -> int:
        if not isinstance(value, int) or value < 0:
            raise DomainError(f"{field_name} must be a non-negative integer")
        return value

    @staticmethod
    def require_money(value: Decimal, field_name: str) -> Decimal:
        if not isinstance(value, Decimal):
            raise DomainError(f"{field_name} must be a Decimal")
        if value < Decimal("0.00"):
            raise DomainError(f"{field_name} must be >= 0")
        return value.quantize(Decimal("0.01"))

    @staticmethod
    def require_positive_money(value: Decimal, field_name: str) -> Decimal:
        value = Validation.require_money(value, field_name)
        if value <= Decimal("0.00"):
            raise DomainError(f"{field_name} must be > 0")
        return value


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    STAFF = "staff"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    PLACED = "placed"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class InventoryMovementType(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    ADJUSTMENT = "adjustment"


def _now() -> datetime:
    return datetime.utcnow()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    password = Validation.require_non_empty(password, "password")
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return salt, digest


def _verify_password(password: str, salt: str, digest: str) -> bool:
    _, computed = _hash_password(password, salt=salt)
    return secrets.compare_digest(computed, digest)


@dataclass(frozen=True)
class User:
    id: str
    email: str
    name: str
    role: Role
    is_active: bool
    created_at: datetime


@dataclass
class _UserRecord:
    id: str
    email: str
    name: str
    role: Role
    is_active: bool
    created_at: datetime
    password_salt: str
    password_digest: str


@dataclass(frozen=True)
class Session:
    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    parent_id: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class Product:
    id: str
    sku: str
    name: str
    description: str
    price: Decimal
    is_active: bool
    category_id: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class Supplier:
    id: str
    name: str
    email: str
    phone: str
    created_at: datetime


@dataclass(frozen=True)
class Warehouse:
    id: str
    name: str
    location: str
    created_at: datetime


@dataclass(frozen=True)
class InventoryLevel:
    product_id: str
    warehouse_id: str
    quantity: int
    updated_at: datetime


@dataclass(frozen=True)
class InventoryMovement:
    id: str
    movement_type: InventoryMovementType
    product_id: str
    warehouse_id: str
    quantity: int
    reference: str
    created_at: datetime


@dataclass(frozen=True)
class CartItem:
    product_id: str
    quantity: int


@dataclass
class Cart:
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=_now)

    def add_item(self, product_id: str, quantity: int) -> None:
        Validation.require_non_empty(product_id, "product_id")
        Validation.require_positive_int(quantity, "quantity")
        existing = self.items.get(product_id)
        if existing:
            new_qty = existing.quantity + quantity
            self.items[product_id] = CartItem(product_id=product_id, quantity=new_qty)
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def set_item_quantity(self, product_id: str, quantity: int) -> None:
        Validation.require_non_empty(product_id, "product_id")
        Validation.require_non_negative_int(quantity, "quantity")
        if quantity == 0:
            self.items.pop(product_id, None)
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def remove_item(self, product_id: str) -> None:
        Validation.require_non_empty(product_id, "product_id")
        self.items.pop(product_id, None)
        self.updated_at = _now()

    def clear(self) -> None:
        self.items.clear()
        self.updated_at = _now()

    def list_items(self) -> List[CartItem]:
        return list(self.items.values())


@dataclass(frozen=True)
class OrderItem:
    product_id: str
    sku: str
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class SalesOrder:
    id: str
    user_id: str
    status: OrderStatus
    items: Tuple[OrderItem, ...]
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PurchaseOrderItem:
    product_id: str
    sku: str
    name: str
    unit_cost: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class PurchaseOrder:
    id: str
    supplier_id: str
    warehouse_id: str
    status: PurchaseOrderStatus
    items: Tuple[PurchaseOrderItem, ...]
    total_cost: Decimal
    created_at: datetime
    updated_at: datetime


class InMemoryDB:
    def __init__(self) -> None:
        self.users: Dict[str, _UserRecord] = {}
        self.users_by_email: Dict[str, str] = {}
        self.sessions: Dict[str, Session] = {}

        self.categories: Dict[str, Category] = {}
        self.products: Dict[str, Product] = {}
        self.products_by_sku: Dict[str, str] = {}

        self.suppliers: Dict[str, Supplier] = {}
        self.warehouses: Dict[str, Warehouse] = {}

        self.inventory: Dict[Tuple[str, str], InventoryLevel] = {}
        self.movements: Dict[str, InventoryMovement] = {}

        self.carts: Dict[str, Cart] = {}

        self.sales_orders: Dict[str, SalesOrder] = {}
        self.purchase_orders: Dict[str, PurchaseOrder] = {}


class AuthService:
    def __init__(self, db: InMemoryDB, session_ttl_seconds: int = 60 * 60 * 24) -> None:
        self._db = db
        self._session_ttl_seconds = Validation.require_positive_int(session_ttl_seconds, "session_ttl_seconds")

    def sign_up(self, email: str, password: str, name: str, role: Role = Role.CUSTOMER) -> User:
        email = Validation.require_email(email)
        name = Validation.require_non_empty(name, "name")
        if email in self._db.users_by_email:
            raise DomainError("email already registered")
        user_id = _new_id("usr")
        salt, digest = _hash_password(password)
        rec = _UserRecord(
            id=user_id,
            email=email,
            name=name,
            role=role,
            is_active=True,
            created_at=_now(),
            password_salt=salt,
            password_digest=digest,
        )
        self._db.users[user_id] = rec
        self._db.users_by_email[email] = user_id
        return User(id=rec.id, email=rec.email, name=rec.name, role=rec.role, is_active=rec.is_active, created_at=rec.created_at)

    def login(self, email: str, password: str) -> Session:
        email = Validation.require_email(email)
        user_id = self._db.users_by_email.get(email)
        if not user_id:
            raise AuthError("invalid credentials")
        rec = self._db.users[user_id]
        if not rec.is_active:
            raise AuthError("user inactive")
        if not _verify_password(password, rec.password_salt, rec.password_digest):
            raise AuthError("invalid credentials")
        token = secrets.token_urlsafe(32)
        created_at = _now()
        expires_at = datetime.utcfromtimestamp(created_at.timestamp() + self._session_ttl_seconds)
        session = Session(token=token, user_id=rec.id, created_at=created_at, expires_at=expires_at)
        self._db.sessions[token] = session
        return session

    def logout(self, token: str) -> None:
        Validation.require_non_empty(token, "token")
        self._db.sessions.pop(token, None)

    def get_user_for_session(self, token: str) -> User:
        Validation.require_non_empty(token, "token")
        session = self._db.sessions.get(token)
        if not session:
            raise AuthError("invalid session")
        if session.expires_at <= _now():
            self._db.sessions.pop(token, None)
            raise AuthError("session expired")
        rec = self._db.users.get(session.user_id)
        if not rec or not rec.is_active:
            raise AuthError("user inactive")
        return User(id=rec.id, email=rec.email, name=rec.name, role=rec.role, is_active=rec.is_active, created_at=rec.created_at)


class UserManagementService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def _require_admin(self, actor: User) -> None:
        if actor.role != Role.ADMIN:
            raise AuthError("admin required")

    def list_users(self, actor: User) -> List[User]:
        self._require_admin(actor)
        return [
            User(id=u.id, email=u.email, name=u.name, role=u.role, is_active=u.is_active, created_at=u.created_at)
            for u in self._db.users.values()
        ]

    def set_active(self, actor: User, user_id: str, is_active: bool) -> User:
        self._require_admin(actor)
        Validation.require_non_empty(user_id, "user_id")
        rec = self._db.users.get(user_id)
        if not rec:
            raise NotFoundError("user not found")
        rec.is_active = bool(is_active)
        return User(id=rec.id, email=rec.email, name=rec.name, role=rec.role, is_active=rec.is_active, created_at=rec.created_at)

    def set_role(self, actor: User, user_id: str, role: Role) -> User:
        self._require_admin(actor)
        Validation.require_non_empty(user_id, "user_id")
        rec = self._db.users.get(user_id)
        if not rec:
            raise NotFoundError("user not found")
        rec.role = role
        return User(id=rec.id, email=rec.email, name=rec.name, role=rec.role, is_active=rec.is_active, created_at=rec.created_at)


class CatalogService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_category(self, actor: User, name: str, parent_id: Optional[str] = None) -> Category:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        name = Validation.require_non_empty(name, "name")
        if parent_id is not None:
            Validation.require_non_empty(parent_id, "parent_id")
            if parent_id not in self._db.categories:
                raise NotFoundError("parent category not found")
        cat = Category(id=_new_id("cat"), name=name, parent_id=parent_id, created_at=_now())
        self._db.categories[cat.id] = cat
        return cat

    def list_categories(self) -> List[Category]:
        return list(self._db.categories.values())

    def create_product(
        self,
        actor: User,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        category_id: Optional[str] = None,
        is_active: bool = True,
    ) -> Product:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        sku = Validation.require_non_empty(sku, "sku")
        name = Validation.require_non_empty(name, "name")
        description = Validation.require_non_empty(description, "description")
        price = Validation.require_positive_money(price, "price")
        if sku in self._db.products_by_sku:
            raise DomainError("sku already exists")
        if category_id is not None:
            Validation.require_non_empty(category_id, "category_id")
            if category_id not in self._db.categories:
                raise NotFoundError("category not found")
        prod = Product(
            id=_new_id("prd"),
            sku=sku,
            name=name,
            description=description,
            price=price,
            is_active=bool(is_active),
            category_id=category_id,
            created_at=_now(),
        )
        self._db.products[prod.id] = prod
        self._db.products_by_sku[sku] = prod.id
        return prod

    def update_product(
        self,
        actor: User,
        product_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Decimal] = None,
        category_id: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Product:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        Validation.require_non_empty(product_id, "product_id")
        prod = self._db.products.get(product_id)
        if not prod:
            raise NotFoundError("product not found")

        new_name = prod.name if name is None else Validation.require_non_empty(name, "name")
        new_desc = prod.description if description is None else Validation.require_non_empty(description, "description")
        new_price = prod.price if price is None else Validation.require_positive_money(price, "price")
        new_active = prod.is_active if is_active is None else bool(is_active)

        new_category_id = prod.category_id
        if category_id is not None:
            if category_id == "":
                new_category_id = None
            else:
                Validation.require_non_empty(category_id, "category_id")
                if category_id not in self._db.categories:
                    raise NotFoundError("category not found")
                new_category_id = category_id

        updated = Product(
            id=prod.id,
            sku=prod.sku,
            name=new_name,
            description=new_desc,
            price=new_price,
            is_active=new_active,
            category_id=new_category_id,
            created_at=prod.created_at,
        )
        self._db.products[product_id] = updated
        return updated

    def list_products(self, *, active_only: bool = True, category_id: Optional[str] = None) -> List[Product]:
        products = list(self._db.products.values())
        if active_only:
            products = [p for p in products if p.is_active]
        if category_id is not None:
            Validation.require_non_empty(category_id, "category_id")
            products = [p for p in products if p.category_id == category_id]
        return products

    def search_products(self, query: str, *, active_only: bool = True) -> List[Product]:
        query = Validation.require_non_empty(query, "query").lower()
        products = self.list_products(active_only=active_only)
        out: List[Product] = []
        for p in products:
            hay = f"{p.sku} {p.name} {p.description}".lower()
            if query in hay:
                out.append(p)
        return out

    def get_product_detail(self, product_id: str) -> Product:
        Validation.require_non_empty(product_id, "product_id")
        prod = self._db.products.get(product_id)
        if not prod:
            raise NotFoundError("product not found")
        return prod


class SupplierService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_supplier(self, actor: User, name: str, email: str, phone: str) -> Supplier:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        name = Validation.require_non_empty(name, "name")
        email = Validation.require_email(email)
        phone = Validation.require_non_empty(phone, "phone")
        sup = Supplier(id=_new_id("sup"), name=name, email=email, phone=phone, created_at=_now())
        self._db.suppliers[sup.id] = sup
        return sup

    def list_suppliers(self, actor: User) -> List[Supplier]:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        return list(self._db.suppliers.values())

    def get_supplier(self, actor: User, supplier_id: str) -> Supplier:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        Validation.require_non_empty(supplier_id, "supplier_id")
        sup = self._db.suppliers.get(supplier_id)
        if not sup:
            raise NotFoundError("supplier not found")
        return sup


class WarehouseService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def create_warehouse(self, actor: User, name: str, location: str) -> Warehouse:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        name = Validation.require_non_empty(name, "name")
        location = Validation.require_non_empty(location, "location")
        wh = Warehouse(id=_new_id("wh"), name=name, location=location, created_at=_now())
        self._db.warehouses[wh.id] = wh
        return wh

    def list_warehouses(self, actor: User) -> List[Warehouse]:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        return list(self._db.warehouses.values())

    def get_warehouse(self, actor: User, warehouse_id: str) -> Warehouse:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        Validation.require_non_empty(warehouse_id, "warehouse_id")
        wh = self._db.warehouses.get(warehouse_id)
        if not wh:
            raise NotFoundError("warehouse not found")
        return wh


class InventoryService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def _require_staff(self, actor: User) -> None:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")

    def get_inventory_level(self, product_id: str, warehouse_id: str) -> InventoryLevel:
        Validation.require_non_empty(product_id, "product_id")
        Validation.require_non_empty(warehouse_id, "warehouse_id")
        key = (product_id, warehouse_id)
        lvl = self._db.inventory.get(key)
        if not lvl:
            return InventoryLevel(product_id=product_id, warehouse_id=warehouse_id, quantity=0, updated_at=_now())
        return lvl

    def list_inventory_for_product(self, actor: User, product_id: str) -> List[InventoryLevel]:
        self._require_staff(actor)
        Validation.require_non_empty(product_id, "product_id")
        return [lvl for (pid, _), lvl in self._db.inventory.items() if pid == product_id]

    def list_inventory_for_warehouse(self, actor: User, warehouse_id: str) -> List[InventoryLevel]:
        self._require_staff(actor)
        Validation.require_non_empty(warehouse_id, "warehouse_id")
        return [lvl for (_, wid), lvl in self._db.inventory.items() if wid == warehouse_id]

    def _apply_movement(
        self,
        movement_type: InventoryMovementType,
        product_id: str,
        warehouse_id: str,
        quantity: int,
        reference: str,
    ) -> InventoryMovement:
        Validation.require_non_empty(product_id, "product_id")
        Validation.require_non_empty(warehouse_id, "warehouse_id")
        Validation.require_non_empty(reference, "reference")
        Validation.require_positive_int(quantity, "quantity")

        if product_id not in self._db.products:
            raise NotFoundError("product not found")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")

        key = (product_id, warehouse_id)
        current = self._db.inventory.get(key)
        current_qty = current.quantity if current else 0

        if movement_type == InventoryMovementType.INBOUND:
            new_qty = current_qty + quantity
        elif movement_type == InventoryMovementType.OUTBOUND:
            if current_qty < quantity:
                raise DomainError("insufficient inventory")
            new_qty = current_qty - quantity
        else:
            new_qty = current_qty + quantity

        lvl = InventoryLevel(product_id=product_id, warehouse_id=warehouse_id, quantity=new_qty, updated_at=_now())
        self._db.inventory[key] = lvl

        mv = InventoryMovement(
            id=_new_id("mov"),
            movement_type=movement_type,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            reference=reference,
            created_at=_now(),
        )
        self._db.movements[mv.id] = mv
        return mv

    def receive_stock(self, actor: User, product_id: str, warehouse_id: str, quantity: int, reference: str) -> InventoryMovement:
        self._require_staff(actor)
        return self._apply_movement(InventoryMovementType.INBOUND, product_id, warehouse_id, quantity, reference)

    def ship_stock(self, actor: User, product_id: str, warehouse_id: str, quantity: int, reference: str) -> InventoryMovement:
        self._require_staff(actor)
        return self._apply_movement(InventoryMovementType.OUTBOUND, product_id, warehouse_id, quantity, reference)

    def list_movements(self, actor: User, *, product_id: Optional[str] = None, warehouse_id: Optional[str] = None) -> List[InventoryMovement]:
        self._require_staff(actor)
        movements = list(self._db.movements.values())
        if product_id is not None:
            Validation.require_non_empty(product_id, "product_id")
            movements = [m for m in movements if m.product_id == product_id]
        if warehouse_id is not None:
            Validation.require_non_empty(warehouse_id, "warehouse_id")
            movements = [m for m in movements if m.warehouse_id == warehouse_id]
        movements.sort(key=lambda m: m.created_at)
        return movements


class CartService:
    def __init__(self, db: InMemoryDB) -> None:
        self._db = db

    def get_cart(self, user: User) -> Cart:
        cart = self._db.carts.get(user.id)
        if not cart:
            cart = Cart(user_id=user.id)
            self._db.carts[user.id] = cart
        return cart

    def add_to_cart(self, user: User, product_id: str, quantity: int) -> Cart:
        Validation.require_non_empty(product_id, "product_id")
        prod = self._db.products.get(product_id)
        if not prod or not prod.is_active:
            raise NotFoundError("product not found")
        cart = self.get_cart(user)
        cart.add_item(product_id, quantity)
        return cart

    def update_quantity(self, user: User, product_id: str, quantity: int) -> Cart:
        Validation.require_non_empty(product_id, "product_id")
        cart = self.get_cart(user)
        cart.set_item_quantity(product_id, quantity)
        return cart

    def remove_from_cart(self, user: User, product_id: str) -> Cart:
        cart = self.get_cart(user)
        cart.remove_item(product_id)
        return cart

    def clear_cart(self, user: User) -> Cart:
        cart = self.get_cart(user)
        cart.clear()
        return cart


class OrderService:
    def __init__(self, db: InMemoryDB, inventory: InventoryService) -> None:
        self._db = db
        self._inventory = inventory

    def _compute_order_items(self, cart: Cart) -> Tuple[OrderItem, ...]:
        items: List[OrderItem] = []
        for ci in cart.list_items():
            prod = self._db.products.get(ci.product_id)
            if not prod or not prod.is_active:
                raise DomainError("cart contains unavailable product")
            qty = Validation.require_positive_int(ci.quantity, "quantity")
            unit_price = prod.price
            line_total = (unit_price * Decimal(qty)).quantize(Decimal("0.01"))
            items.append(
                OrderItem(
                    product_id=prod.id,
                    sku=prod.sku,
                    name=prod.name,
                    unit_price=unit_price,
                    quantity=qty,
                    line_total=line_total,
                )
            )
        if not items:
            raise DomainError("cart is empty")
        return tuple(items)

    def _subtotal(self, items: Tuple[OrderItem, ...]) -> Decimal:
        total = sum((i.line_total for i in items), Decimal("0.00"))
        return Decimal(total).quantize(Decimal("0.01"))

    def place_order(self, user: User, warehouse_id: str) -> SalesOrder:
        Validation.require_non_empty(warehouse_id, "warehouse_id")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")

        cart = self._db.carts.get(user.id)
        if not cart:
            raise DomainError("cart is empty")

        items = self._compute_order_items(cart)

        for it in items:
            lvl = self._inventory.get_inventory_level(it.product_id, warehouse_id)
            if lvl.quantity < it.quantity:
                raise DomainError("insufficient inventory")

        order_id = _new_id("so")
        created = _now()
        order = SalesOrder(
            id=order_id,
            user_id=user.id,
            status=OrderStatus.PLACED,
            items=items,
            subtotal=self._subtotal(items),
            created_at=created,
            updated_at=created,
        )
        self._db.sales_orders[order.id] = order

        for it in items:
            self._inventory.ship_stock(
                actor=User(id=user.id, email=user.email, name=user.name, role=Role.STAFF if user.role != Role.CUSTOMER else Role.STAFF, is_active=True, created_at=user.created_at),
                product_id=it.product_id,
                warehouse_id=warehouse_id,
                quantity=it.quantity,
                reference=f"sales_order:{order.id}",
            )

        cart.clear()
        return order

    def get_order(self, user: User, order_id: str) -> SalesOrder:
        Validation.require_non_empty(order_id, "order_id")
        order = self._db.sales_orders.get(order_id)
        if not order:
            raise NotFoundError("order not found")
        if user.role not in (Role.ADMIN, Role.STAFF) and order.user_id != user.id:
            raise AuthError("not allowed")
        return order

    def list_orders(self, user: User) -> List[SalesOrder]:
        orders = list(self._db.sales_orders.values())
        if user.role in (Role.ADMIN, Role.STAFF):
            orders.sort(key=lambda o: o.created_at, reverse=True)
            return orders
        orders = [o for o in orders if o.user_id == user.id]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders

    def set_order_status(self, actor: User, order_id: str, status: OrderStatus) -> SalesOrder:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")
        Validation.require_non_empty(order_id, "order_id")
        order = self._db.sales_orders.get(order_id)
        if not order:
            raise NotFoundError("order not found")
        updated = SalesOrder(
            id=order.id,
            user_id=order.user_id,
            status=status,
            items=order.items,
            subtotal=order.subtotal,
            created_at=order.created_at,
            updated_at=_now(),
        )
        self._db.sales_orders[order_id] = updated
        return updated


class PurchaseOrderService:
    def __init__(self, db: InMemoryDB, inventory: InventoryService) -> None:
        self._db = db
        self._inventory = inventory

    def _require_staff(self, actor: User) -> None:
        if actor.role not in (Role.ADMIN, Role.STAFF):
            raise AuthError("staff or admin required")

    def create_purchase_order(
        self,
        actor: User,
        supplier_id: str,
        warehouse_id: str,
        items: List[Tuple[str, int, Decimal]],
    ) -> PurchaseOrder:
        self._require_staff(actor)
        Validation.require_non_empty(supplier_id, "supplier_id")
        Validation.require_non_empty(warehouse_id, "warehouse_id")
        if supplier_id not in self._db.suppliers:
            raise NotFoundError("supplier not found")
        if warehouse_id not in self._db.warehouses:
            raise NotFoundError("warehouse not found")
        if not items:
            raise DomainError("items required")

        po_items: List[PurchaseOrderItem] = []
        for product_id, qty, unit_cost in items:
            Validation.require_non_empty(product_id, "product_id")
            Validation.require_positive_int(qty, "quantity")
            unit_cost = Validation.require_positive_money(unit_cost, "unit_cost")
            prod = self._db.products.get(product_id)
            if not prod:
                raise NotFoundError("product not found")
            line_total = (unit_cost * Decimal(qty)).quantize(Decimal("0.01"))
            po_items.append(
                PurchaseOrderItem(
                    product_id=prod.id,
                    sku=prod.sku,
                    name=prod.name,
                    unit_cost=unit_cost,
                    quantity=qty,
                    line_total=line_total,
                )
            )

        total_cost = sum((i.line_total for i in po_items), Decimal("0.00")).quantize(Decimal("0.01"))
        po_id = _new_id("po")
        created = _now()
        po = PurchaseOrder(
            id=po_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            status=PurchaseOrderStatus.SUBMITTED,
            items=tuple(po_items),
            total_cost=total_cost,
            created_at=created,
            updated_at=created,
        )
        self._db.purchase_orders[po.id] = po
        return po

    def receive_purchase_order(self, actor: User, purchase_order_id: str) -> PurchaseOrder:
        self._require_staff(actor)
        Validation.require_non_empty(purchase_order_id, "purchase_order_id")
        po = self._db.purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("purchase order not found")
        if po.status in (PurchaseOrderStatus.CANCELLED, PurchaseOrderStatus.RECEIVED):
            raise DomainError("purchase order not receivable")

        for it in po.items:
            self._inventory.receive_stock(
                actor=actor,
                product_id=it.product_id,
                warehouse_id=po.warehouse_id,
                quantity=it.quantity,
                reference=f"purchase_order:{po.id}",
            )

        updated = PurchaseOrder(
            id=po.id,
            supplier_id=po.supplier_id,
            warehouse_id=po.warehouse_id,
            status=PurchaseOrderStatus.RECEIVED,
            items=po.items,
            total_cost=po.total_cost,
            created_at=po.created_at,
            updated_at=_now(),
        )
        self._db.purchase_orders[po.id] = updated
        return updated

    def cancel_purchase_order(self, actor: User, purchase_order_id: str) -> PurchaseOrder:
        self._require_staff(actor)
        Validation.require_non_empty(purchase_order_id, "purchase_order_id")
        po = self._db.purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("purchase order not found")
        if po.status == PurchaseOrderStatus.RECEIVED:
            raise DomainError("cannot cancel received purchase order")
        updated = PurchaseOrder(
            id=po.id,
            supplier_id=po.supplier_id,
            warehouse_id=po.warehouse_id,
            status=PurchaseOrderStatus.CANCELLED,
            items=po.items,
            total_cost=po.total_cost,
            created_at=po.created_at,
            updated_at=_now(),
        )
        self._db.purchase_orders[po.id] = updated
        return updated

    def get_purchase_order(self, actor: User, purchase_order_id: str) -> PurchaseOrder:
        self._require_staff(actor)
        Validation.require_non_empty(purchase_order_id, "purchase_order_id")
        po = self._db.purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("purchase order not found")
        return po

    def list_purchase_orders(self, actor: User) -> List[PurchaseOrder]:
        self._require_staff(actor)
        pos = list(self._db.purchase_orders.values())
        pos.sort(key=lambda p: p.created_at, reverse=True)
        return pos


class AmazonCloneApp:
    def __init__(self) -> None:
        self.db = InMemoryDB()
        self.auth = AuthService(self.db)
        self.user_mgmt = UserManagementService(self.db)
        self.catalog = CatalogService(self.db)
        self.suppliers = SupplierService(self.db)
        self.warehouses = WarehouseService(self.db)
        self.inventory = InventoryService(self.db)
        self.carts = CartService(self.db)
        self.orders = OrderService(self.db, self.inventory)
        self.purchase_orders = PurchaseOrderService(self.db, self.inventory)

    def bootstrap_admin(self, email: str, password: str, name: str) -> User:
        email = Validation.require_email(email)
        if email in self.db.users_by_email:
            user_id = self.db.users_by_email[email]
            rec = self.db.users[user_id]
            if rec.role != Role.ADMIN:
                rec.role = Role.ADMIN
            if not rec.is_active:
                rec.is_active = True
            return User(id=rec.id, email=rec.email, name=rec.name, role=rec.role, is_active=rec.is_active, created_at=rec.created_at)
        return self.auth.sign_up(email=email, password=password, name=name, role=Role.ADMIN)


def _demo() -> None:
    app = AmazonCloneApp()
    admin = app.bootstrap_admin("admin@example.com", "AdminPass123", "Admin")
    staff = app.auth.sign_up("staff@example.com", "StaffPass123", "Staff", role=Role.STAFF)
    customer = app.auth.sign_up("alice@example.com", "AlicePass123", "Alice", role=Role.CUSTOMER)

    wh = app.warehouses.create_warehouse(admin, "Main Warehouse", "NY")
    sup = app.suppliers.create_supplier(staff, "Acme Supply", "acme@example.com", "555-0100")
    cat = app.catalog.create_category(staff, "Electronics")
    prod = app.catalog.create_product(staff, "SKU-1", "Headphones", "Noise cancelling", Decimal("99.99"), category_id=cat.id)

    po = app.purchase_orders.create_purchase_order(staff, sup.id, wh.id, [(prod.id, 10, Decimal("50.00"))])
    app.purchase_orders.receive_purchase_order(staff, po.id)

    app.carts.add_to_cart(customer, prod.id, 2)
    so = app.orders.place_order(customer, wh.id)
    _ = so


if __name__ == "__main__":
    _demo()