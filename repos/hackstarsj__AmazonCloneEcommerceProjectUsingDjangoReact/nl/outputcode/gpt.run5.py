from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import hashlib
import secrets
import re


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


def _normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValidationError("Invalid email address.")
    return email


def _hash_password(password: str, salt: str) -> str:
    if not password or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def _money(value: Decimal | int | float | str) -> Decimal:
    d = Decimal(str(value))
    if d < 0:
        raise ValidationError("Money value cannot be negative.")
    return d.quantize(Decimal("0.01"))


def _qty(value: int) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValidationError("Quantity must be a positive integer.")
    return value


def _sku(value: str) -> str:
    v = (value or "").strip().upper()
    if not v or len(v) > 64:
        raise ValidationError("Invalid SKU.")
    if not re.match(r"^[A-Z0-9][A-Z0-9\-_\.]{0,63}$", v):
        raise ValidationError("Invalid SKU format.")
    return v


def _name(value: str, field: str = "name", max_len: int = 200) -> str:
    v = (value or "").strip()
    if not v:
        raise ValidationError(f"Invalid {field}.")
    if len(v) > max_len:
        raise ValidationError(f"{field} too long.")
    return v


def _nonempty(value: str, field: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValidationError(f"{field} is required.")
    return v


@dataclass(frozen=True)
class Address:
    line1: str
    line2: str
    city: str
    state: str
    postal_code: str
    country: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "line1", _nonempty(self.line1, "line1"))
        object.__setattr__(self, "line2", (self.line2 or "").strip())
        object.__setattr__(self, "city", _nonempty(self.city, "city"))
        object.__setattr__(self, "state", _nonempty(self.state, "state"))
        object.__setattr__(self, "postal_code", _nonempty(self.postal_code, "postal_code"))
        object.__setattr__(self, "country", _nonempty(self.country, "country"))


class User:
    def __init__(self, user_id: int, email: str, password: str, *, is_admin: bool = False) -> None:
        self._id = user_id
        self._email = _normalize_email(email)
        self._salt = secrets.token_hex(16)
        self._password_hash = _hash_password(password, self._salt)
        self._is_admin = bool(is_admin)
        self._created_at = _now()
        self._active = True

    @property
    def id(self) -> int:
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def check_password(self, password: str) -> bool:
        try:
            return _hash_password(password, self._salt) == self._password_hash
        except ValidationError:
            return False

    def set_password(self, new_password: str) -> None:
        self._password_hash = _hash_password(new_password, self._salt)


class Session:
    def __init__(self, token: str, user_id: int) -> None:
        self._token = token
        self._user_id = user_id
        self._created_at = _now()
        self._revoked = False

    @property
    def token(self) -> str:
        return self._token

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def is_active(self) -> bool:
        return not self._revoked

    def revoke(self) -> None:
        self._revoked = True


class AuthService:
    def __init__(self) -> None:
        self._users_by_id: Dict[int, User] = {}
        self._users_by_email: Dict[str, User] = {}
        self._sessions: Dict[str, Session] = {}
        self._next_user_id = 1

    def sign_up(self, email: str, password: str, *, is_admin: bool = False) -> User:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        user = User(self._next_user_id, email_n, password, is_admin=is_admin)
        self._next_user_id += 1
        self._users_by_id[user.id] = user
        self._users_by_email[user.email] = user
        return user

    def login(self, email: str, password: str) -> str:
        email_n = _normalize_email(email)
        user = self._users_by_email.get(email_n)
        if not user or not user.is_active or not user.check_password(password):
            raise AuthenticationError("Invalid credentials.")
        token = secrets.token_urlsafe(32)
        self._sessions[token] = Session(token, user.id)
        return token

    def logout(self, token: str) -> None:
        sess = self._sessions.get(token)
        if sess:
            sess.revoke()

    def get_user_by_token(self, token: str) -> User:
        sess = self._sessions.get(token)
        if not sess or not sess.is_active:
            raise AuthenticationError("Not authenticated.")
        user = self._users_by_id.get(sess.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Not authenticated.")
        return user

    def get_user(self, user_id: int) -> User:
        user = self._users_by_id.get(user_id)
        if not user:
            raise NotFoundError("User not found.")
        return user

    def list_users(self, requester: User) -> List[User]:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        return list(self._users_by_id.values())


class Category:
    def __init__(self, category_id: int, name: str, *, parent_id: Optional[int] = None) -> None:
        self._id = category_id
        self._name = _name(name, "category name", 120)
        self._parent_id = parent_id

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent_id(self) -> Optional[int]:
        return self._parent_id


class Product:
    def __init__(
        self,
        product_id: int,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        category_id: int,
        *,
        active: bool = True,
    ) -> None:
        self._id = product_id
        self._sku = _sku(sku)
        self._name = _name(name, "product name", 200)
        self._description = (description or "").strip()
        self._price = _money(price)
        self._category_id = category_id
        self._active = bool(active)
        self._created_at = _now()

    @property
    def id(self) -> int:
        return self._id

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def price(self) -> Decimal:
        return self._price

    @property
    def category_id(self) -> int:
        return self._category_id

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def update_price(self, new_price: Decimal) -> None:
        self._price = _money(new_price)

    def update_details(self, *, name: Optional[str] = None, description: Optional[str] = None) -> None:
        if name is not None:
            self._name = _name(name, "product name", 200)
        if description is not None:
            self._description = (description or "").strip()


class CatalogService:
    def __init__(self) -> None:
        self._categories: Dict[int, Category] = {}
        self._products: Dict[int, Product] = {}
        self._products_by_sku: Dict[str, Product] = {}
        self._next_category_id = 1
        self._next_product_id = 1

    def create_category(self, requester: User, name: str, *, parent_id: Optional[int] = None) -> Category:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        if parent_id is not None and parent_id not in self._categories:
            raise NotFoundError("Parent category not found.")
        cat = Category(self._next_category_id, name, parent_id=parent_id)
        self._next_category_id += 1
        self._categories[cat.id] = cat
        return cat

    def create_product(
        self,
        requester: User,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        category_id: int,
        *,
        active: bool = True,
    ) -> Product:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        if category_id not in self._categories:
            raise NotFoundError("Category not found.")
        sku_n = _sku(sku)
        if sku_n in self._products_by_sku:
            raise ValidationError("SKU already exists.")
        p = Product(self._next_product_id, sku_n, name, description, price, category_id, active=active)
        self._next_product_id += 1
        self._products[p.id] = p
        self._products_by_sku[p.sku] = p
        return p

    def get_product(self, product_id: int) -> Product:
        p = self._products.get(product_id)
        if not p:
            raise NotFoundError("Product not found.")
        return p

    def get_product_by_sku(self, sku: str) -> Product:
        p = self._products_by_sku.get(_sku(sku))
        if not p:
            raise NotFoundError("Product not found.")
        return p

    def list_products(self, *, include_inactive: bool = False) -> List[Product]:
        if include_inactive:
            return list(self._products.values())
        return [p for p in self._products.values() if p.is_active]

    def search_products(self, query: str, *, include_inactive: bool = False) -> List[Product]:
        q = (query or "").strip().lower()
        if not q:
            return self.list_products(include_inactive=include_inactive)
        res: List[Product] = []
        for p in self._products.values():
            if not include_inactive and not p.is_active:
                continue
            if q in p.name.lower() or q in p.description.lower() or q in p.sku.lower():
                res.append(p)
        return res

    def product_detail(self, product_id: int) -> Product:
        p = self.get_product(product_id)
        if not p.is_active:
            raise NotFoundError("Product not found.")
        return p


class Supplier:
    def __init__(self, supplier_id: int, name: str, contact_email: str) -> None:
        self._id = supplier_id
        self._name = _name(name, "supplier name", 200)
        self._contact_email = _normalize_email(contact_email)
        self._active = True
        self._created_at = _now()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def contact_email(self) -> str:
        return self._contact_email

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False


class Warehouse:
    def __init__(self, warehouse_id: int, name: str, address: Address) -> None:
        self._id = warehouse_id
        self._name = _name(name, "warehouse name", 200)
        self._address = address
        self._active = True
        self._created_at = _now()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> Address:
        return self._address

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False


@dataclass(frozen=True)
class InventoryMovement:
    timestamp: datetime
    warehouse_id: int
    product_id: int
    delta: int
    reason: str
    reference: str


class InventoryService:
    def __init__(self) -> None:
        self._suppliers: Dict[int, Supplier] = {}
        self._warehouses: Dict[int, Warehouse] = {}
        self._stock: Dict[Tuple[int, int], int] = {}
        self._movements: List[InventoryMovement] = []
        self._next_supplier_id = 1
        self._next_warehouse_id = 1

    def create_supplier(self, requester: User, name: str, contact_email: str) -> Supplier:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        s = Supplier(self._next_supplier_id, name, contact_email)
        self._next_supplier_id += 1
        self._suppliers[s.id] = s
        return s

    def create_warehouse(self, requester: User, name: str, address: Address) -> Warehouse:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        w = Warehouse(self._next_warehouse_id, name, address)
        self._next_warehouse_id += 1
        self._warehouses[w.id] = w
        return w

    def get_supplier(self, supplier_id: int) -> Supplier:
        s = self._suppliers.get(supplier_id)
        if not s:
            raise NotFoundError("Supplier not found.")
        return s

    def get_warehouse(self, warehouse_id: int) -> Warehouse:
        w = self._warehouses.get(warehouse_id)
        if not w:
            raise NotFoundError("Warehouse not found.")
        return w

    def get_stock(self, warehouse_id: int, product_id: int) -> int:
        self.get_warehouse(warehouse_id)
        return self._stock.get((warehouse_id, product_id), 0)

    def adjust_stock(
        self,
        requester: User,
        warehouse_id: int,
        product_id: int,
        delta: int,
        *,
        reason: str,
        reference: str,
    ) -> None:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        if not isinstance(delta, int) or delta == 0:
            raise ValidationError("Delta must be a non-zero integer.")
        w = self.get_warehouse(warehouse_id)
        if not w.is_active:
            raise InventoryError("Warehouse inactive.")
        key = (warehouse_id, product_id)
        current = self._stock.get(key, 0)
        new = current + delta
        if new < 0:
            raise InventoryError("Insufficient stock.")
        self._stock[key] = new
        self._movements.append(
            InventoryMovement(timestamp=_now(), warehouse_id=warehouse_id, product_id=product_id, delta=delta, reason=_nonempty(reason, "reason"), reference=_nonempty(reference, "reference"))
        )

    def list_movements(
        self,
        requester: User,
        *,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> List[InventoryMovement]:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        res = self._movements
        if warehouse_id is not None:
            res = [m for m in res if m.warehouse_id == warehouse_id]
        if product_id is not None:
            res = [m for m in res if m.product_id == product_id]
        return list(res)


class CartItem:
    def __init__(self, product_id: int, quantity: int) -> None:
        self._product_id = product_id
        self._quantity = _qty(quantity)

    @property
    def product_id(self) -> int:
        return self._product_id

    @property
    def quantity(self) -> int:
        return self._quantity

    def set_quantity(self, quantity: int) -> None:
        self._quantity = _qty(quantity)

    def increment(self, delta: int) -> None:
        if not isinstance(delta, int) or delta == 0:
            raise ValidationError("Delta must be a non-zero integer.")
        new = self._quantity + delta
        if new <= 0:
            raise ValidationError("Resulting quantity must be positive.")
        self._quantity = new


class ShoppingCart:
    def __init__(self, user_id: int) -> None:
        self._user_id = user_id
        self._items: Dict[int, CartItem] = {}
        self._updated_at = _now()

    @property
    def user_id(self) -> int:
        return self._user_id

    def items(self) -> List[CartItem]:
        return list(self._items.values())

    def add_item(self, product_id: int, quantity: int) -> None:
        q = _qty(quantity)
        if product_id in self._items:
            self._items[product_id].increment(q)
        else:
            self._items[product_id] = CartItem(product_id, q)
        self._updated_at = _now()

    def set_item_quantity(self, product_id: int, quantity: int) -> None:
        q = _qty(quantity)
        if product_id not in self._items:
            raise NotFoundError("Item not in cart.")
        self._items[product_id].set_quantity(q)
        self._updated_at = _now()

    def remove_item(self, product_id: int) -> None:
        if product_id in self._items:
            del self._items[product_id]
            self._updated_at = _now()

    def clear(self) -> None:
        self._items.clear()
        self._updated_at = _now()

    def is_empty(self) -> bool:
        return not self._items


class CartService:
    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog
        self._carts: Dict[int, ShoppingCart] = {}

    def get_cart(self, user: User) -> ShoppingCart:
        cart = self._carts.get(user.id)
        if not cart:
            cart = ShoppingCart(user.id)
            self._carts[user.id] = cart
        return cart

    def add_to_cart(self, user: User, product_id: int, quantity: int) -> None:
        p = self._catalog.get_product(product_id)
        if not p.is_active:
            raise ValidationError("Product is not available.")
        self.get_cart(user).add_item(product_id, quantity)

    def remove_from_cart(self, user: User, product_id: int) -> None:
        self.get_cart(user).remove_item(product_id)

    def clear_cart(self, user: User) -> None:
        self.get_cart(user).clear()


class PurchaseOrderStatus:
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class SalesOrderStatus:
    PENDING = "PENDING"
    PAID = "PAID"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class OrderLine:
    def __init__(self, product_id: int, quantity: int, unit_price: Decimal) -> None:
        self._product_id = product_id
        self._quantity = _qty(quantity)
        self._unit_price = _money(unit_price)

    @property
    def product_id(self) -> int:
        return self._product_id

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def unit_price(self) -> Decimal:
        return self._unit_price

    @property
    def line_total(self) -> Decimal:
        return _money(self._unit_price * Decimal(self._quantity))


class PurchaseOrder:
    def __init__(self, po_id: int, supplier_id: int, warehouse_id: int, created_by: int) -> None:
        self._id = po_id
        self._supplier_id = supplier_id
        self._warehouse_id = warehouse_id
        self._created_by = created_by
        self._status = PurchaseOrderStatus.DRAFT
        self._lines: Dict[int, OrderLine] = {}
        self._created_at = _now()
        self._updated_at = self._created_at

    @property
    def id(self) -> int:
        return self._id

    @property
    def supplier_id(self) -> int:
        return self._supplier_id

    @property
    def warehouse_id(self) -> int:
        return self._warehouse_id

    @property
    def status(self) -> str:
        return self._status

    def lines(self) -> List[OrderLine]:
        return list(self._lines.values())

    def add_line(self, product_id: int, quantity: int, unit_price: Decimal) -> None:
        if self._status != PurchaseOrderStatus.DRAFT:
            raise OrderError("Cannot modify purchase order unless in DRAFT.")
        if product_id in self._lines:
            existing = self._lines[product_id]
            new_qty = existing.quantity + _qty(quantity)
            self._lines[product_id] = OrderLine(product_id, new_qty, existing.unit_price)
        else:
            self._lines[product_id] = OrderLine(product_id, quantity, unit_price)
        self._updated_at = _now()

    def submit(self) -> None:
        if self._status != PurchaseOrderStatus.DRAFT:
            raise OrderError("Purchase order cannot be submitted.")
        if not self._lines:
            raise OrderError("Purchase order must have at least one line.")
        self._status = PurchaseOrderStatus.SUBMITTED
        self._updated_at = _now()

    def cancel(self) -> None:
        if self._status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED):
            raise OrderError("Purchase order cannot be cancelled.")
        self._status = PurchaseOrderStatus.CANCELLED
        self._updated_at = _now()

    def mark_received(self) -> None:
        if self._status != PurchaseOrderStatus.SUBMITTED:
            raise OrderError("Purchase order can only be received after submission.")
        self._status = PurchaseOrderStatus.RECEIVED
        self._updated_at = _now()

    @property
    def total(self) -> Decimal:
        return _money(sum((l.line_total for l in self._lines.values()), Decimal("0.00")))


class SalesOrder:
    def __init__(self, so_id: int, user_id: int, shipping_address: Address) -> None:
        self._id = so_id
        self._user_id = user_id
        self._shipping_address = shipping_address
        self._status = SalesOrderStatus.PENDING
        self._lines: List[OrderLine] = []
        self._created_at = _now()
        self._updated_at = self._created_at

    @property
    def id(self) -> int:
        return self._id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def status(self) -> str:
        return self._status

    def lines(self) -> List[OrderLine]:
        return list(self._lines)

    def add_line(self, product_id: int, quantity: int, unit_price: Decimal) -> None:
        if self._status != SalesOrderStatus.PENDING:
            raise OrderError("Cannot modify sales order unless PENDING.")
        self._lines.append(OrderLine(product_id, quantity, unit_price))
        self._updated_at = _now()

    def mark_paid(self) -> None:
        if self._status != SalesOrderStatus.PENDING:
            raise OrderError("Sales order cannot be marked paid.")
        if not self._lines:
            raise OrderError("Sales order must have at least one line.")
        self._status = SalesOrderStatus.PAID
        self._updated_at = _now()

    def mark_fulfilled(self) -> None:
        if self._status != SalesOrderStatus.PAID:
            raise OrderError("Sales order can only be fulfilled after payment.")
        self._status = SalesOrderStatus.FULFILLED
        self._updated_at = _now()

    def cancel(self) -> None:
        if self._status in (SalesOrderStatus.FULFILLED, SalesOrderStatus.CANCELLED):
            raise OrderError("Sales order cannot be cancelled.")
        self._status = SalesOrderStatus.CANCELLED
        self._updated_at = _now()

    @property
    def total(self) -> Decimal:
        return _money(sum((l.line_total for l in self._lines), Decimal("0.00")))


class OrderService:
    def __init__(self, catalog: CatalogService, inventory: InventoryService, cart_service: CartService) -> None:
        self._catalog = catalog
        self._inventory = inventory
        self._cart_service = cart_service
        self._purchase_orders: Dict[int, PurchaseOrder] = {}
        self._sales_orders: Dict[int, SalesOrder] = {}
        self._next_po_id = 1
        self._next_so_id = 1

    def create_purchase_order(self, requester: User, supplier_id: int, warehouse_id: int) -> PurchaseOrder:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        supplier = self._inventory.get_supplier(supplier_id)
        if not supplier.is_active:
            raise ValidationError("Supplier inactive.")
        warehouse = self._inventory.get_warehouse(warehouse_id)
        if not warehouse.is_active:
            raise ValidationError("Warehouse inactive.")
        po = PurchaseOrder(self._next_po_id, supplier_id, warehouse_id, requester.id)
        self._next_po_id += 1
        self._purchase_orders[po.id] = po
        return po

    def add_purchase_order_line(self, requester: User, po_id: int, product_id: int, quantity: int, unit_price: Decimal) -> None:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        po = self.get_purchase_order(requester, po_id)
        product = self._catalog.get_product(product_id)
        if not product.is_active:
            raise ValidationError("Product inactive.")
        po.add_line(product_id, quantity, unit_price)

    def submit_purchase_order(self, requester: User, po_id: int) -> None:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        po = self.get_purchase_order(requester, po_id)
        po.submit()

    def receive_purchase_order(self, requester: User, po_id: int) -> None:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        po = self.get_purchase_order(requester, po_id)
        po.mark_received()
        for line in po.lines():
            self._inventory.adjust_stock(
                requester,
                po.warehouse_id,
                line.product_id,
                line.quantity,
                reason="PURCHASE_ORDER_RECEIPT",
                reference=f"PO:{po.id}",
            )

    def get_purchase_order(self, requester: User, po_id: int) -> PurchaseOrder:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        po = self._purchase_orders.get(po_id)
        if not po:
            raise NotFoundError("Purchase order not found.")
        return po

    def list_purchase_orders(self, requester: User) -> List[PurchaseOrder]:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        return list(self._purchase_orders.values())

    def create_sales_order_from_cart(self, user: User, shipping_address: Address) -> SalesOrder:
        cart = self._cart_service.get_cart(user)
        if cart.is_empty():
            raise OrderError("Cart is empty.")
        so = SalesOrder(self._next_so_id, user.id, shipping_address)
        self._next_so_id += 1

        for item in cart.items():
            product = self._catalog.get_product(item.product_id)
            if not product.is_active:
                raise ValidationError("Cart contains unavailable product.")
            so.add_line(product.id, item.quantity, product.price)

        self._sales_orders[so.id] = so
        cart.clear()
        return so

    def pay_sales_order(self, user: User, so_id: int) -> None:
        so = self.get_sales_order(user, so_id)
        if so.user_id != user.id and not user.is_admin:
            raise AuthorizationError("Not allowed.")
        so.mark_paid()

    def fulfill_sales_order(self, requester: User, so_id: int, warehouse_id: int) -> None:
        if not requester.is_admin:
            raise AuthorizationError("Admin required.")
        so = self.get_sales_order(requester, so_id)
        warehouse = self._inventory.get_warehouse(warehouse_id)
        if not warehouse.is_active:
            raise ValidationError("Warehouse inactive.")
        if so.status != SalesOrderStatus.PAID:
            raise OrderError("Sales order must be PAID to fulfill.")

        for line in so.lines():
            available = self._inventory.get_stock(warehouse_id, line.product_id)
            if available < line.quantity:
                raise InventoryError("Insufficient stock to fulfill order.")

        for line in so.lines():
            self._inventory.adjust_stock(
                requester,
                warehouse_id,
                line.product_id,
                -line.quantity,
                reason="SALES_ORDER_FULFILLMENT",
                reference=f"SO:{so.id}",
            )

        so.mark_fulfilled()

    def cancel_sales_order(self, user: User, so_id: int) -> None:
        so = self.get_sales_order(user, so_id)
        if so.user_id != user.id and not user.is_admin:
            raise AuthorizationError("Not allowed.")
        so.cancel()

    def get_sales_order(self, requester: User, so_id: int) -> SalesOrder:
        so = self._sales_orders.get(so_id)
        if not so:
            raise NotFoundError("Sales order not found.")
        if requester.is_admin or so.user_id == requester.id:
            return so
        raise AuthorizationError("Not allowed.")

    def list_sales_orders(self, requester: User, *, user_id: Optional[int] = None) -> List[SalesOrder]:
        if requester.is_admin:
            if user_id is None:
                return list(self._sales_orders.values())
            return [o for o in self._sales_orders.values() if o.user_id == user_id]
        return [o for o in self._sales_orders.values() if o.user_id == requester.id]


class AmazonCloneApp:
    def __init__(self) -> None:
        self.auth = AuthService()
        self.catalog = CatalogService()
        self.inventory = InventoryService()
        self.cart = CartService(self.catalog)
        self.orders = OrderService(self.catalog, self.inventory, self.cart)

    def require_admin(self, user: User) -> None:
        if not user.is_admin:
            raise AuthorizationError("Admin required.")