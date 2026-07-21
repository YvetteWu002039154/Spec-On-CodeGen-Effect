import datetime
import decimal
import itertools
import uuid

_counter = itertools.count(1)


# ============================================================================
# Shared helpers: build/persist Django model instances for the drivers.
# ============================================================================

def _scalar(f):
    """A valid throwaway value for a required scalar field, by Django type."""
    n = next(_counter)
    if getattr(f, "choices", None):
        return f.choices[0][0]
    t = f.get_internal_type()
    if "Email" in t:
        return f"u{n}@example.com"
    if t in ("CharField", "TextField", "SlugField", "FilePathField", "URLField"):
        v = f"v{n}"
        ml = getattr(f, "max_length", None)
        return v[:ml] if ml else v
    if t in ("IntegerField", "BigIntegerField", "SmallIntegerField",
             "PositiveIntegerField", "PositiveSmallIntegerField",
             "PositiveBigIntegerField", "AutoField", "BigAutoField"):
        return n
    if t == "FloatField":
        return float(n)
    if t == "DecimalField":
        return decimal.Decimal("1.00")
    if t == "BooleanField":
        return True
    if t == "DateTimeField":
        return datetime.datetime(2020, 1, 1, 12, 0, 0)
    if t == "DateField":
        return datetime.date(2020, 1, 1)
    if t == "TimeField":
        return datetime.time(12, 0, 0)
    if t == "JSONField":
        return {}
    if t == "GenericIPAddressField":
        return "127.0.0.1"
    if t == "UUIDField":
        return uuid.uuid4()
    if t == "DurationField":
        return datetime.timedelta(days=1)
    if t == "BinaryField":
        return b"x"
    return f"v{n}"


def _new_user():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    n = next(_counter)
    return User.objects.create_user(
        username=f"user{n}", email=f"user{n}@example.com", password="Sekr3t!pw")


def _build(model, depth=0, **overrides):
    """Save an instance of a concrete Django model, filling required scalar
    columns by type and recursively building required foreign keys. Explicit
    field values (FK links, price, …) are passed as ``overrides``."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if model is User or (isinstance(model, type) and issubclass(model, User)):
        return _new_user()
    if depth > 6:
        raise RuntimeError(f"{model.__name__}: FK graph too deep")
    kwargs = dict(overrides)
    for f in model._meta.concrete_fields:
        if f.name in kwargs or f.primary_key:
            continue
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        if f.has_default() or f.null:
            continue
        if f.is_relation:
            kwargs[f.name] = _build(f.related_model, depth + 1)
        else:
            kwargs[f.name] = _scalar(f)
    obj = model(**kwargs)
    obj.save()
    return obj


def _hash_check(user, raw):
    from django.contrib.auth.hashers import check_password
    stored = getattr(user, "password", None)
    return {"differs": stored != raw, "verifies": bool(check_password(raw, stored))}


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def product_listing(self):
        _build(self.m.Product)
        return self.m.Product.objects.count()

    def product_price(self):
        product = _build(self.m.Product, price=decimal.Decimal("49.50"))
        return float(product.price)

    def product_category_link(self):
        category = _build(self.m.Category)
        product = _build(self.m.Product, category=category)
        reread = self.m.Product.objects.get(pk=product.pk)
        return reread.category_id == category.pk

    def cart_total(self):
        product = _build(self.m.Product, price=decimal.Decimal("10.00"))
        cart = _build(self.m.Cart)
        cart.add_item(product, 3)
        return {"total": float(cart.get_total()), "expected": 30.0}

    def inventory_quantity(self):
        inv = _build(self.m.Inventory)
        return isinstance(inv.quantity, (int, float, decimal.Decimal))

    def order_status(self):
        order = _build(self.m.Order)
        return str(order.status)

    def purchase_order_supplier(self):
        po = _build(self.m.PurchaseOrder)
        reread = self.m.PurchaseOrder.objects.get(pk=po.pk)
        return reread.supplier_id is not None

    def warehouse_named(self):
        warehouse = _build(self.m.Warehouse)
        return bool(warehouse.name) and \
            self.m.Warehouse.objects.filter(pk=warehouse.pk).exists()

    def password_hashed(self):
        raw = "Pla1ntext-Pw!"
        user = _new_user()
        user.set_password(raw)
        user.save()
        return _hash_check(user, raw)


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def product_listing(self):
        _build(self.m.Product)
        return self.m.Product.objects.count()

    def product_price(self):
        product = _build(self.m.Product, price=decimal.Decimal("49.50"))
        return float(product.price)

    def product_category_link(self):
        category = _build(self.m.Category)
        product = _build(self.m.Product, category=category)
        reread = self.m.Product.objects.get(pk=product.pk)
        return reread.category_id == category.pk

    def cart_total(self):
        product = _build(self.m.Product, price=decimal.Decimal("10.00"))
        cart = _build(self.m.Cart)
        cart.add_product(product, 3)
        return {"total": float(cart.subtotal), "expected": 30.0}

    def inventory_quantity(self):
        inv = _build(self.m.Inventory)
        return isinstance(inv.quantity, (int, float, decimal.Decimal))

    def order_status(self):
        order = _build(self.m.Order)
        return str(order.status)

    def purchase_order_supplier(self):
        po = _build(self.m.PurchaseOrder)
        reread = self.m.PurchaseOrder.objects.get(pk=po.pk)
        return reread.supplier_id is not None

    def warehouse_named(self):
        warehouse = _build(self.m.Warehouse)
        return bool(warehouse.name) and \
            self.m.Warehouse.objects.filter(pk=warehouse.pk).exists()

    def password_hashed(self):
        raw = "Pla1ntext-Pw!"
        n = next(_counter)
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username=f"auth{n}", email=f"auth{n}@example.com", password=raw)
        return _hash_check(user, raw)


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def product_listing(self):
        _build(self.m.Product)
        return self.m.Product.objects.count()

    def product_price(self):
        product = _build(self.m.Product, price=decimal.Decimal("49.50"))
        return float(product.price)

    def product_category_link(self):
        category = _build(self.m.Category)
        product = _build(self.m.Product, category=category)
        reread = self.m.Product.objects.get(pk=product.pk)
        return reread.category_id == category.pk

    def cart_total(self):
        product = _build(self.m.Product, price=decimal.Decimal("10.00"))
        cart = _build(self.m.Cart)
        cart.add_item(product, 3)
        return {"total": float(cart.get_total()), "expected": 30.0}

    def inventory_quantity(self):
        inv = _build(self.m.Inventory)
        return isinstance(inv.quantity, (int, float, decimal.Decimal))

    def order_status(self):
        order = _build(self.m.SalesOrder)
        return str(order.status)

    def purchase_order_supplier(self):
        po = _build(self.m.PurchaseOrder)
        reread = self.m.PurchaseOrder.objects.get(pk=po.pk)
        return reread.supplier_id is not None

    def warehouse_named(self):
        warehouse = _build(self.m.Warehouse)
        return bool(warehouse.name) and \
            self.m.Warehouse.objects.filter(pk=warehouse.pk).exists()

    def password_hashed(self):
        raw = "Pla1ntext-Pw!"
        n = next(_counter)
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username=f"auth{n}", email=f"auth{n}@example.com", password=raw)
        return _hash_check(user, raw)


class DeepseekDriver:
    """deepseek shipped a full multi-app Django project, so models are imported
    from their app packages (products.models, orders.models, …) rather than a
    single module. `m` is None (see loader._load_project)."""

    model = "deepseek"

    def __init__(self, m):
        pass

    def product_listing(self):
        from products.models import Product
        _build(Product)
        return Product.objects.count()

    def product_price(self):
        from products.models import Product
        product = _build(Product, price=decimal.Decimal("49.50"))
        return float(product.price)

    def product_category_link(self):
        from products.models import Product, Category
        category = _build(Category)
        product = _build(Product, category=category)
        reread = Product.objects.get(pk=product.pk)
        return reread.category_id == category.pk

    def cart_total(self):
        # deepseek has no Cart model (it uses Order/OrderItem); the import fails,
        # so the cart-total behavior fails naturally.
        from cart.models import Cart
        from products.models import Product
        product = _build(Product, price=decimal.Decimal("10.00"))
        cart = _build(Cart)
        cart.add_item(product, 3)
        return {"total": float(cart.get_total()), "expected": 30.0}

    def inventory_quantity(self):
        from inventory.models import Stock
        inv = _build(Stock)
        return isinstance(inv.quantity, (int, float, decimal.Decimal))

    def order_status(self):
        from orders.models import Order
        order = _build(Order)
        return str(order.status)

    def purchase_order_supplier(self):
        from suppliers.models import PurchaseOrder
        po = _build(PurchaseOrder)
        reread = PurchaseOrder.objects.get(pk=po.pk)
        return reread.supplier_id is not None

    def warehouse_named(self):
        from warehouse.models import Warehouse
        warehouse = _build(Warehouse)
        return bool(warehouse.name) and \
            Warehouse.objects.filter(pk=warehouse.pk).exists()

    def password_hashed(self):
        raw = "Pla1ntext-Pw!"
        user = _new_user()
        user.set_password(raw)
        user.save()
        return _hash_check(user, raw)


# Contract order N1..N9: (probe name, driver method).
BEHAVIORS = [
    ("N1_product_listing", "product_listing"),
    ("N2_product_price", "product_price"),
    ("N3_product_category_link", "product_category_link"),
    ("N4_cart_total", "cart_total"),
    ("N5_inventory_quantity", "inventory_quantity"),
    ("N6_order_status", "order_status"),
    ("N7_purchase_order_supplier", "purchase_order_supplier"),
    ("N8_warehouse_named", "warehouse_named"),
    ("N9_password_hashed", "password_hashed"),
]

DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
