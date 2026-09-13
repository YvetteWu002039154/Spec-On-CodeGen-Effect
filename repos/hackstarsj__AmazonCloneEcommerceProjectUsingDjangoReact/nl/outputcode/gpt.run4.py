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


def _now() -> datetime:
    return datetime.utcnow()


def _hash_password(password: str, salt: str) -> str:
    if not password:
        raise ValidationError("Password cannot be empty.")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def _require_positive_money(amount: Decimal, field_name: str) -> None:
    if amount is None:
        raise ValidationError(f"{field_name} is required.")
    if amount < Decimal("0"):
        raise ValidationError(f"{field_name} cannot be negative.")


def _require_positive_int(value: int, field_name: str) -> None:
    if value is None:
        raise ValidationError(f"{field_name} is required.")
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative.")


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    SUPPLIER = "supplier"
    WAREHOUSE_MANAGER = "warehouse_manager"


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


@dataclass(frozen=True)
class Address:
    line1: str
    city: str
    state: str
    postal_code: str
    country: str
    line2: str = ""

    def __post_init__(self) -> None:
        if not self.line1.strip():
            raise ValidationError("Address line1 is required.")
        if not self.city.strip():
            raise ValidationError("City is required.")
        if not self.state.strip():
            raise ValidationError("State is required.")
        if not self.postal_code.strip():
            raise ValidationError("Postal code is required.")
        if not self.country.strip():
            raise ValidationError("Country is required.")


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

    def set_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        self._password_hash = _hash_password(password, self._password_salt)

    def check_password(self, password: str) -> bool:
        if not self._password_hash:
            return False
        return _hash_password(password, self._password_salt) == self._password_hash

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class Category:
    id: int
    name: str
    parent_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Category name is required.")


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
        if not self.sku.strip():
            raise ValidationError("SKU is required.")
        if not self.name.strip():
            raise ValidationError("Product name is required.")
        _require_positive_money(self.price, "price")

    def set_price(self, price: Decimal) -> None:
        _require_positive_money(price, "price")
        self.price = price

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class Supplier:
    id: int
    name: str
    contact_email: str
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Supplier name is required.")
        if not self.contact_email.strip():
            raise ValidationError("Supplier contact_email is required.")

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class Warehouse:
    id: int
    name: str
    address: Address
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Warehouse name is required.")

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class InventoryItem:
    product_id: int
    warehouse_id: int
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        _require_positive_int(self.quantity_on_hand, "quantity_on_hand")
        _require_positive_int(self.quantity_reserved, "quantity_reserved")
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValidationError("quantity_reserved cannot exceed quantity_on_hand.")

    @property
    def available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved

    def add_stock(self, qty: int) -> None:
        if qty <= 0:
            raise ValidationError("Stock increment must be positive.")
        self.quantity_on_hand += qty
        self.updated_at = _now()

    def remove_stock(self, qty: int) -> None:
        if qty <= 0:
            raise ValidationError("Stock decrement must be positive.")
        if qty > self.available:
            raise InventoryError("Insufficient available stock.")
        self.quantity_on_hand -= qty
        if self.quantity_reserved > self.quantity_on_hand:
            self.quantity_reserved = self.quantity_on_hand
        self.updated_at = _now()

    def reserve(self, qty: int) -> None:
        if qty <= 0:
            raise ValidationError("Reserve quantity must be positive.")
        if qty > self.available:
            raise InventoryError("Insufficient available stock to reserve.")
        self.quantity_reserved += qty
        self.updated_at = _now()

    def release(self, qty: int) -> None:
        if qty <= 0:
            raise ValidationError("Release quantity must be positive.")
        if qty > self.quantity_reserved:
            raise InventoryError("Cannot release more than reserved.")
        self.quantity_reserved -= qty
        self.updated_at = _now()


@dataclass
class CartItem:
    product_id: int
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationError("Cart item quantity must be positive.")


@dataclass
class ShoppingCart:
    user_id: int
    items: Dict[int, CartItem] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=_now)

    def add_item(self, product_id: int, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if product_id in self.items:
            self.items[product_id].quantity += quantity
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = _now()

    def set_quantity(self, product_id: int, quantity: int) -> None:
        if quantity <= 0:
            self.remove_item(product_id)
            return
        if product_id not in self.items:
            raise NotFoundError("Product not in cart.")
        self.items[product_id].quantity = quantity
        self.updated_at = _now()

    def remove_item(self, product_id: int) -> None:
        if product_id in self.items:
            del self.items[product_id]
            self.updated_at = _now()

    def clear(self) -> None:
        self.items.clear()
        self.updated_at = _now()

    def is_empty(self) -> bool:
        return not self.items

    def list_items(self) -> List[CartItem]:
        return list(self.items.values())


@dataclass
class OrderItem:
    product_id: int
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        _require_positive_money(self.unit_price, "unit_price")
        if self.quantity <= 0:
            raise ValidationError("Order item quantity must be positive.")

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * Decimal(self.quantity)


@dataclass
class SalesOrder:
    id: int
    user_id: int
    status: OrderStatus
    shipping_address: Address
    items: List[OrderItem]
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.items:
            raise ValidationError("Order must have at least one item.")

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0")
        for it in self.items:
            total += it.line_total
        return total

    def mark_placed(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise OrderError("Only draft orders can be placed.")
        self.status = OrderStatus.PLACED
        self.updated_at = _now()

    def mark_paid(self) -> None:
        if self.status not in (OrderStatus.PLACED, OrderStatus.DRAFT):
            raise OrderError("Order must be placed (or draft) to be paid.")
        self.status = OrderStatus.PAID
        self.paid_at = _now()
        self.updated_at = self.paid_at

    def mark_shipped(self) -> None:
        if self.status != OrderStatus.PAID:
            raise OrderError("Only paid orders can be shipped.")
        self.status = OrderStatus.SHIPPED
        self.shipped_at = _now()
        self.updated_at = self.shipped_at

    def mark_completed(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise OrderError("Only shipped orders can be completed.")
        self.status = OrderStatus.COMPLETED
        self.completed_at = _now()
        self.updated_at = self.completed_at

    def cancel(self) -> None:
        if self.status in (OrderStatus.SHIPPED, OrderStatus.COMPLETED):
            raise OrderError("Cannot cancel shipped or completed orders.")
        if self.status == OrderStatus.CANCELLED:
            return
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = _now()
        self.updated_at = self.cancelled_at


@dataclass
class PurchaseOrderItem:
    product_id: int
    unit_cost: Decimal
    quantity: int

    def __post_init__(self) -> None:
        _require_positive_money(self.unit_cost, "unit_cost")
        if self.quantity <= 0:
            raise ValidationError("Purchase order item quantity must be positive.")

    @property
    def line_total(self) -> Decimal:
        return self.unit_cost * Decimal(self.quantity)


@dataclass
class PurchaseOrder:
    id: int
    supplier_id: int
    warehouse_id: int
    status: PurchaseOrderStatus
    items: List[PurchaseOrderItem]
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    submitted_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.items:
            raise ValidationError("Purchase order must have at least one item.")

    @property
    def total_cost(self) -> Decimal:
        total = Decimal("0")
        for it in self.items:
            total += it.line_total
        return total

    def submit(self) -> None:
        if self.status != PurchaseOrderStatus.DRAFT:
            raise OrderError("Only draft purchase orders can be submitted.")
        self.status = PurchaseOrderStatus.SUBMITTED
        self.submitted_at = _now()
        self.updated_at = self.submitted_at

    def receive(self) -> None:
        if self.status != PurchaseOrderStatus.SUBMITTED:
            raise OrderError("Only submitted purchase orders can be received.")
        self.status = PurchaseOrderStatus.RECEIVED
        self.received_at = _now()
        self.updated_at = self.received_at

    def cancel(self) -> None:
        if self.status == PurchaseOrderStatus.RECEIVED:
            raise OrderError("Cannot cancel a received purchase order.")
        if self.status == PurchaseOrderStatus.CANCELLED:
            return
        self.status = PurchaseOrderStatus.CANCELLED
        self.cancelled_at = _now()
        self.updated_at = self.cancelled_at


class AuthService:
    def __init__(self) -> None:
        self._sessions: Dict[str, int] = {}

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user_id
        return token

    def destroy_session(self, token: str) -> None:
        self._sessions.pop(token, None)

    def get_user_id(self, token: str) -> int:
        if token not in self._sessions:
            raise AuthenticationError("Invalid session.")
        return self._sessions[token]


class AmazonCloneSystem:
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}
        self._users_by_email: Dict[str, int] = {}
        self._categories: Dict[int, Category] = {}
        self._products: Dict[int, Product] = {}
        self._products_by_sku: Dict[str, int] = {}
        self._suppliers: Dict[int, Supplier] = {}
        self._warehouses: Dict[int, Warehouse] = {}
        self._inventory: Dict[Tuple[int, int], InventoryItem] = {}
        self._carts: Dict[int, ShoppingCart] = {}
        self._sales_orders: Dict[int, SalesOrder] = {}
        self._purchase_orders: Dict[int, PurchaseOrder] = {}

        self._user_id_seq = 1
        self._category_id_seq = 1
        self._product_id_seq = 1
        self._supplier_id_seq = 1
        self._warehouse_id_seq = 1
        self._sales_order_id_seq = 1
        self._purchase_order_id_seq = 1

        self.auth = AuthService()

    def _require_role(self, user: User, allowed: Set[Role]) -> None:
        if user.role not in allowed:
            raise AuthorizationError("Insufficient permissions.")

    def _get_user(self, user_id: int) -> User:
        u = self._users.get(user_id)
        if not u:
            raise NotFoundError("User not found.")
        return u

    def _get_product(self, product_id: int) -> Product:
        p = self._products.get(product_id)
        if not p:
            raise NotFoundError("Product not found.")
        return p

    def _get_warehouse(self, warehouse_id: int) -> Warehouse:
        w = self._warehouses.get(warehouse_id)
        if not w:
            raise NotFoundError("Warehouse not found.")
        return w

    def _get_supplier(self, supplier_id: int) -> Supplier:
        s = self._suppliers.get(supplier_id)
        if not s:
            raise NotFoundError("Supplier not found.")
        return s

    def _get_inventory_item(self, product_id: int, warehouse_id: int) -> InventoryItem:
        key = (product_id, warehouse_id)
        if key not in self._inventory:
            self._inventory[key] = InventoryItem(product_id=product_id, warehouse_id=warehouse_id)
        return self._inventory[key]

    def sign_up(self, email: str, name: str, password: str, role: Role = Role.CUSTOMER) -> User:
        email_norm = email.strip().lower()
        if not email_norm:
            raise ValidationError("Email is required.")
        if email_norm in self._users_by_email:
            raise ValidationError("Email already registered.")
        if not name.strip():
            raise ValidationError("Name is required.")
        if role not in (Role.CUSTOMER, Role.SUPPLIER):
            raise ValidationError("Invalid role for self sign-up.")
        user = User(id=self._user_id_seq, email=email_norm, name=name.strip(), role=role)
        user.set_password(password)
        self._users[user.id] = user
        self._users_by_email[email_norm] = user.id
        self._user_id_seq += 1
        return user

    def admin_create_user(self, admin_user_id: int, email: str, name: str, password: str, role: Role) -> User:
        admin = self._get_user(admin_user_id)
        self._require_role(admin, {Role.ADMIN})
        email_norm = email.strip().lower()
        if not email_norm:
            raise ValidationError("Email is required.")
        if email_norm in self._users_by_email:
            raise ValidationError("Email already registered.")
        if not name.strip():
            raise ValidationError("Name is required.")
        user = User(id=self._user_id_seq, email=email_norm, name=name.strip(), role=role)
        user.set_password(password)
        self._users[user.id] = user
        self._users_by_email[email_norm] = user.id
        self._user_id_seq += 1
        return user

    def login(self, email: str, password: str) -> str:
        email_norm = email.strip().lower()
        user_id = self._users_by_email.get(email_norm)
        if not user_id:
            raise AuthenticationError("Invalid credentials.")
        user = self._users[user_id]
        if not user.is_active:
            raise AuthenticationError("User is inactive.")
        if not user.check_password(password):
            raise AuthenticationError("Invalid credentials.")
        return self.auth.create_session(user.id)

    def logout(self, session_token: str) -> None:
        self.auth.destroy_session(session_token)

    def get_current_user(self, session_token: str) -> User:
        user_id = self.auth.get_user_id(session_token)
        return self._get_user(user_id)

    def create_category(self, admin_user_id: int, name: str, parent_id: Optional[int] = None) -> Category:
        admin = self._get_user(admin_user_id)
        self._require_role(admin, {Role.ADMIN})
        if parent_id is not None and parent_id not in self._categories:
            raise NotFoundError("Parent category not found.")
        cat = Category(id=self._category_id_seq, name=name.strip(), parent_id=parent_id)
        self._categories[cat.id] = cat
        self._category_id_seq += 1
        return cat

    def create_product(
        self,
        admin_user_id: int,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        category_ids: Optional[Set[int]] = None,
    ) -> Product:
        admin = self._get_user(admin_user_id)
        self._require_role(admin, {Role.ADMIN})
        sku_norm = sku.strip()
        if not sku_norm:
            raise ValidationError("SKU is required.")
        if sku_norm in self._products_by_sku:
            raise ValidationError("SKU already exists.")
        if category_ids:
            for cid in category_ids:
                if cid not in self._categories:
                    raise NotFoundError("Category not found.")
        prod = Product(
            id=self._product_id_seq,
            sku=sku_norm,
            name=name.strip(),
            description=description or "",
            price=price,
            category_ids=set(category_ids or set()),
        )
        self._products[prod.id] = prod
        self._products_by_sku[sku_norm] = prod.id
        self._product_id_seq += 1
        return prod

    def update_product_price(self, admin_user_id: int, product_id: int, new_price: Decimal) -> None:
        admin = self._get_user(admin_user_id)
        self._require_role(admin, {Role.ADMIN})
        prod = self._get_product(product_id)
        prod.set_price(new_price)

    def search_products(self, query: str) -> List[Product]:
        q = (query or "").strip().lower()
        results: List[Product] = []
        for p in self._products.values():
            if not p.is_active:
                continue
            if not q:
                results.append(p)
                continue
            hay = f"{p.name} {p.description} {p.sku}".lower()
            if q in hay:
                results.append(p)
        results.sort(key=lambda x: x.id)
        return results

    def get_product_detail(self, product_id: int) -> Product:
        p = self._get_product(product_id)
        if not p.is_active:
            raise NotFoundError("Product not found.")
        return p

    def create_supplier(self, admin_user_id: int, name: str, contact_email: str) -> Supplier:
        admin = self._get_user(admin_user_id)
        self._require_role(admin, {Role.ADMIN})
        sup = Supplier(id=self._supplier_id_seq, name=name.strip(), contact_email=contact_email.strip())
        self._suppliers[sup.id] = sup
        self._supplier_id_seq += 1
        return sup

    def create_warehouse(self, admin_user_id: int, name: str, address: Address) -> Warehouse:
        admin = self._get_user(admin_user_id)
        self._require_role(admin, {Role.ADMIN})
        wh = Warehouse(id=self._warehouse_id_seq, name=name.strip(), address=address)
        self._warehouses[wh.id] = wh
        self._warehouse_id_seq += 1
        return wh

    def adjust_inventory(self, manager_user_id: int, product_id: int, warehouse_id: int, delta: int) -> InventoryItem:
        user = self._get_user(manager_user_id)
        self._require_role(user, {Role.ADMIN, Role.WAREHOUSE_MANAGER})
        prod = self._get_product(product_id)
        if not prod.is_active:
            raise ValidationError("Cannot adjust inventory for inactive product.")
        wh = self._get_warehouse(warehouse_id)
        if not wh.is_active:
            raise ValidationError("Cannot adjust inventory for inactive warehouse.")
        item = self._get_inventory_item(product_id, warehouse_id)
        if delta == 0:
            return item
        if delta > 0:
            item.add_stock(delta)
        else:
            item.remove_stock(-delta)
        return item

    def get_inventory(self, user_id: int, product_id: int, warehouse_id: int) -> InventoryItem:
        user = self._get_user(user_id)
        self._require_role(user, {Role.ADMIN, Role.WAREHOUSE_MANAGER})
        self._get_product(product_id)
        self._get_warehouse(warehouse_id)
        return self._get_inventory_item(product_id, warehouse_id)

    def get_or_create_cart(self, user_id: int) -> ShoppingCart:
        user = self._get_user(user_id)
        if user.role != Role.CUSTOMER:
            raise AuthorizationError("Only customers can have carts.")
        if user_id not in self._carts:
            self._carts[user_id] = ShoppingCart(user_id=user_id)
        return self._carts[user_id]

    def cart_add_item(self, user_id: int, product_id: int, quantity: int) -> None:
        user = self._get_user(user_id)
        if user.role != Role.CUSTOMER:
            raise AuthorizationError("Only customers can add to cart.")
        prod = self._get_product(product_id)
        if not prod.is_active:
            raise ValidationError("Product is not available.")
        cart = self.get_or_create_cart(user_id)
        cart.add_item(product_id, quantity)

    def cart_remove_item(self, user_id: int, product_id: int) -> None:
        cart = self.get_or_create_cart(user_id)
        cart.remove_item(product_id)

    def cart_clear(self, user_id: int) -> None:
        cart = self.get_or_create_cart(user_id)
        cart.clear()

    def _choose_warehouse_for_fulfillment(self, items: List[CartItem]) -> int:
        if not self._warehouses:
            raise InventoryError("No warehouses available.")
        active_warehouses = [w for w in self._warehouses.values() if w.is_active]
        if not active_warehouses:
            raise InventoryError("No active warehouses available.")
        for wh in sorted(active_warehouses, key=lambda w: w.id):
            ok = True
            for it in items:
                inv = self._get_inventory_item(it.product_id, wh.id)
                if inv.available < it.quantity:
                    ok = False
                    break
            if ok:
                return wh.id
        raise InventoryError("Insufficient stock to fulfill order from any warehouse.")

    def place_order_from_cart(self, user_id: int, shipping_address: Address) -> SalesOrder:
        user = self._get_user(user_id)
        if user.role != Role.CUSTOMER:
            raise AuthorizationError("Only customers can place orders.")
        cart = self.get_or_create_cart(user_id)
        if cart.is_empty():
            raise OrderError("Cart is empty.")
        cart_items = cart.list_items()
        for it in cart_items:
            prod = self._get_product(it.product_id)
            if not prod.is_active:
                raise ValidationError("Cart contains inactive product.")
        warehouse_id = self._choose_warehouse_for_fulfillment(cart_items)
        for it in cart_items:
            inv = self._get_inventory_item(it.product_id, warehouse_id)
            inv.reserve(it.quantity)
        order_items: List[OrderItem] = []
        for it in cart_items:
            prod = self._get_product(it.product_id)
            order_items.append(OrderItem(product_id=it.product_id, unit_price=prod.price, quantity=it.quantity))
        order = SalesOrder(
            id=self._sales_order_id_seq,
            user_id=user_id,
            status=OrderStatus.DRAFT,
            shipping_address=shipping_address,
            items=order_items,
        )
        order.mark_placed()
        self._sales_orders[order.id] = order
        self._sales_order_id_seq += 1
        cart.clear()
        return order

    def pay_order(self, user_id: int, order_id: int) -> None:
        user = self._get_user(user_id)
        order = self._sales_orders.get(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if user.role != Role.ADMIN and order.user_id != user_id:
            raise AuthorizationError("Cannot pay for another user's order.")
        if order.status == OrderStatus.CANCELLED:
            raise OrderError("Cannot pay a cancelled order.")
        order.mark_paid()

    def ship_order(self, staff_user_id: int, order_id: int) -> None:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN, Role.WAREHOUSE_MANAGER})
        order = self._sales_orders.get(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        order.mark_shipped()

    def complete_order(self, staff_user_id: int, order_id: int) -> None:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN})
        order = self._sales_orders.get(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        order.mark_completed()

    def cancel_order(self, user_id: int, order_id: int) -> None:
        user = self._get_user(user_id)
        order = self._sales_orders.get(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if user.role != Role.ADMIN and order.user_id != user_id:
            raise AuthorizationError("Cannot cancel another user's order.")
        if order.status in (OrderStatus.SHIPPED, OrderStatus.COMPLETED):
            raise OrderError("Cannot cancel shipped or completed orders.")
        if order.status == OrderStatus.CANCELLED:
            return
        warehouse_id = None
        for wh in sorted(self._warehouses.values(), key=lambda w: w.id):
            ok = True
            for it in order.items:
                inv = self._get_inventory_item(it.product_id, wh.id)
                if inv.quantity_reserved < it.quantity:
                    ok = False
                    break
            if ok:
                warehouse_id = wh.id
                break
        if warehouse_id is not None:
            for it in order.items:
                inv = self._get_inventory_item(it.product_id, warehouse_id)
                inv.release(it.quantity)
        order.cancel()

    def list_orders_for_user(self, user_id: int) -> List[SalesOrder]:
        user = self._get_user(user_id)
        if user.role == Role.ADMIN:
            orders = list(self._sales_orders.values())
        else:
            orders = [o for o in self._sales_orders.values() if o.user_id == user_id]
        orders.sort(key=lambda o: o.id)
        return orders

    def create_purchase_order(
        self,
        staff_user_id: int,
        supplier_id: int,
        warehouse_id: int,
        items: List[Tuple[int, Decimal, int]],
    ) -> PurchaseOrder:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN})
        supplier = self._get_supplier(supplier_id)
        if not supplier.is_active:
            raise ValidationError("Supplier is inactive.")
        wh = self._get_warehouse(warehouse_id)
        if not wh.is_active:
            raise ValidationError("Warehouse is inactive.")
        if not items:
            raise ValidationError("Items are required.")
        po_items: List[PurchaseOrderItem] = []
        for product_id, unit_cost, qty in items:
            prod = self._get_product(product_id)
            if not prod.is_active:
                raise ValidationError("Cannot purchase inactive product.")
            po_items.append(PurchaseOrderItem(product_id=product_id, unit_cost=unit_cost, quantity=qty))
        po = PurchaseOrder(
            id=self._purchase_order_id_seq,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            status=PurchaseOrderStatus.DRAFT,
            items=po_items,
        )
        self._purchase_orders[po.id] = po
        self._purchase_order_id_seq += 1
        return po

    def submit_purchase_order(self, staff_user_id: int, purchase_order_id: int) -> None:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN})
        po = self._purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("Purchase order not found.")
        po.submit()

    def receive_purchase_order(self, staff_user_id: int, purchase_order_id: int) -> None:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN, Role.WAREHOUSE_MANAGER})
        po = self._purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("Purchase order not found.")
        po.receive()
        for it in po.items:
            inv = self._get_inventory_item(it.product_id, po.warehouse_id)
            inv.add_stock(it.quantity)

    def cancel_purchase_order(self, staff_user_id: int, purchase_order_id: int) -> None:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN})
        po = self._purchase_orders.get(purchase_order_id)
        if not po:
            raise NotFoundError("Purchase order not found.")
        po.cancel()

    def list_purchase_orders(self, staff_user_id: int) -> List[PurchaseOrder]:
        staff = self._get_user(staff_user_id)
        self._require_role(staff, {Role.ADMIN, Role.WAREHOUSE_MANAGER})
        pos = list(self._purchase_orders.values())
        pos.sort(key=lambda p: p.id)
        return pos

    def bootstrap_admin(self, email: str, name: str, password: str) -> User:
        email_norm = email.strip().lower()
        if not email_norm:
            raise ValidationError("Email is required.")
        if email_norm in self._users_by_email:
            raise ValidationError("Email already registered.")
        if not name.strip():
            raise ValidationError("Name is required.")
        user = User(id=self._user_id_seq, email=email_norm, name=name.strip(), role=Role.ADMIN)
        user.set_password(password)
        self._users[user.id] = user
        self._users_by_email[email_norm] = user.id
        self._user_id_seq += 1
        return user


def _self_test() -> None:
    sys = AmazonCloneSystem()
    admin = sys.bootstrap_admin("admin@example.com", "Admin", "password123")
    wh = sys.create_warehouse(admin.id, "Main WH", Address("1 Road", "City", "State", "00000", "US"))
    cat = sys.create_category(admin.id, "Books")
    p1 = sys.create_product(admin.id, "SKU1", "Book A", "A book", Decimal("10.00"), {cat.id})
    sup = sys.create_supplier(admin.id, "SupplierCo", "sup@example.com")
    po = sys.create_purchase_order(admin.id, sup.id, wh.id, [(p1.id, Decimal("5.00"), 10)])
    sys.submit_purchase_order(admin.id, po.id)
    sys.receive_purchase_order(admin.id, po.id)

    cust = sys.sign_up("c@example.com", "Customer", "password123", Role.CUSTOMER)
    sys.cart_add_item(cust.id, p1.id, 2)
    order = sys.place_order_from_cart(cust.id, Address("2 Ave", "City", "State", "11111", "US"))
    sys.pay_order(cust.id, order.id)
    sys.ship_order(admin.id, order.id)
    sys.complete_order(admin.id, order.id)


if __name__ == "__main__":
    _self_test()