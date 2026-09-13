"""Per-model driver bodies for `AmazonClone` NL track — appended to adapter.py.

All four generations are Django schemas, so every behaviour is an ORM call; the
differences are in model and field names:

  claude    Product(name, slug, sku, description, category, price); Cart.add_item
            + get_total(); Order needs an order_number; Inventory(quantity).
  gpt       Product(category, name, slug, sku, price); Cart.add_product +
            subtotal(); Order/SalesOrder/PurchaseOrder carry STATUS_* constants.
  deepseek  Product(name, slug, category, description, price, sku); stock is
            `Stock`, NOT Inventory; the cart is a plain session object, so the
            cart total is read from OrderItem.subtotal().
  gemini    Product uses `title` rather than `name`; Supplier.contact_email;
            Warehouse(name, location); orders are SalesOrder.

The probe harness (loader.run_probes) executes these in a subprocess with Django
configured and the tables created, so ORM writes are real.
"""

import itertools

from decimal import Decimal

PRICE = Decimal("49.50")
QTY = 3

# Every probe runs in the same database, and these schemas put unique
# constraints on category name/slug, warehouse code and product sku — so each
# helper mints a fresh suffix rather than reusing a fixed literal.
_seq = itertools.count(1)


def _uniq(prefix):
    return f"{prefix}{next(_seq)}"


class _DjangoBase:
    """Shared observation helpers. Subclasses name their own models."""

    def __init__(self, module):
        self.m = module

    # each subclass fills these in
    def _category(self):
        raise NotImplementedError

    def _product(self, category=None, price=PRICE):
        raise NotImplementedError

    def _warehouse(self):
        raise NotImplementedError

    def _supplier(self):
        raise NotImplementedError

    def _user(self, name="buyer"):
        """Use Django's configured auth user: several generations point their
        FKs at settings.AUTH_USER_MODEL, so module.User is not always the class
        the ORM will accept."""
        from django.contrib.auth import get_user_model
        U = get_user_model()
        u = U.objects.create(username=_uniq(name))
        u.set_password("pw12345")
        u.save()
        return u

    # ---- behaviours ------------------------------------------------------
    def product_listing(self):
        self._product()
        return type(self._product()).objects.count()

    def product_price(self):
        p = self._product()
        p.refresh_from_db()
        return float(getattr(p, self.PRICE_FIELD))

    def product_category_link(self):
        c = self._category()
        p = self._product(category=c)
        p.refresh_from_db()
        return p.category_id == c.id

    def inventory_quantity(self):
        rec = self._stock()
        rec.refresh_from_db()
        return int(rec.quantity) == QTY

    def warehouse_named(self):
        w = self._warehouse()
        w.refresh_from_db()
        return bool(getattr(w, "name", ""))

    def purchase_order_supplier(self):
        po = self._purchase_order()
        po.refresh_from_db()
        return po.supplier_id is not None

    def order_status(self):
        o = self._order()
        o.refresh_from_db()
        return str(o.status)

    def password_hashed(self):
        u = self._user("hashcheck")
        return {"differs": u.password != "pw12345",
                "verifies": u.check_password("pw12345")}


class ClaudeDriver(_DjangoBase):
    PRICE_FIELD = "price"

    def _category(self, n=None):
        n = n or _uniq("cat")
        return self.m.Category.objects.create(name=n, slug=n)

    def _product(self, category=None, price=PRICE):
        c = category or self._category()
        n = _uniq("p")
        return self.m.Product.objects.create(
            name=n, slug=n, sku=n, description="d", category=c, price=price)

    def _warehouse(self):
        return self.m.Warehouse.objects.create(
            name=_uniq("WH"), code=_uniq("WHC"), address="a", city="c", state="s",
            country="co", zip_code="1")

    def _supplier(self):
        return self.m.Supplier.objects.create(
            name=_uniq("Sup"), email="s@e.com", phone="1", address="a", city="c",
            state="s", country="co", zip_code="1")

    def _stock(self):
        return self.m.Inventory.objects.create(
            product=self._product(), warehouse=self._warehouse(), quantity=QTY)

    def _purchase_order(self):
        return self.m.PurchaseOrder.objects.create(
            order_number=_uniq("PO"), supplier=self._supplier(),
            warehouse=self._warehouse(), status="draft")

    def _order(self):
        # this generation's Order carries a full shipping block, all NOT NULL
        return self.m.Order.objects.create(
            order_number=_uniq("O"), user=self._user("ord"), status="pending",
            subtotal=PRICE, total_amount=PRICE,
            shipping_full_name="A B", shipping_phone="1",
            shipping_address_line1="1 St", shipping_city="C",
            shipping_state="S", shipping_country="CO", shipping_zip_code="1")

    def cart_total(self):
        cart = self.m.Cart.objects.create(user=self._user("cart"))
        p = self._product()
        cart.add_item(p, QTY)
        return {"total": float(cart.get_total()), "expected": float(PRICE * QTY)}


class GptDriver(_DjangoBase):
    PRICE_FIELD = "price"

    def _category(self, n=None):
        n = n or _uniq("cat")
        return self.m.Category.objects.create(name=n, slug=n)

    def _product(self, category=None, price=PRICE):
        c = category or self._category()
        n = _uniq("p")
        return self.m.Product.objects.create(
            category=c, name=n, slug=n, sku=n, price=price)

    def _warehouse(self):
        return self.m.Warehouse.objects.create(name=_uniq("WH"), code=_uniq("WHC"))

    def _supplier(self):
        return self.m.Supplier.objects.create(name=_uniq("Sup"))

    def _stock(self):
        return self.m.Inventory.objects.create(
            product=self._product(), warehouse=self._warehouse(), quantity=QTY)

    def _purchase_order(self):
        return self.m.PurchaseOrder.objects.create(
            supplier=self._supplier(), warehouse=self._warehouse(),
            status=self.m.PurchaseOrder.STATUS_DRAFT)

    def _order(self):
        return self.m.Order.objects.create(
            user=self._user("ord"), status=self.m.Order.STATUS_PENDING)

    def cart_total(self):
        cart = self.m.Cart.objects.create(user=self._user("cart"))
        cart.add_product(self._product(), QTY)
        sub = cart.subtotal
        return {"total": float(sub() if callable(sub) else sub),
                "expected": float(PRICE * QTY)}


class _AppRegistry:
    """Model lookup for a generation delivered as a full Django PROJECT.

    loader._load_project() returns None instead of a module (the models live in
    the project's own app packages), so `self.m` is None here and models are
    resolved by name through Django's app registry instead."""

    def __getattr__(self, name):
        from django.apps import apps
        for model in apps.get_models():
            if model.__name__ == name:
                return model
        raise AttributeError(name)


class DeepseekDriver(_DjangoBase):
    """Delivered as a full Django project. Stock is `Stock`, not Inventory; the
    cart is a session object, so the cart total is observed through
    OrderItem.subtotal()."""

    PRICE_FIELD = "price"

    def __init__(self, module):
        super().__init__(module or _AppRegistry())

    def _user(self, name="buyer"):
        name = _uniq(name)
        u = self.m.CustomUser.objects.create(username=name, email=f"{name}@e.com")
        u.set_password("pw12345")
        u.save()
        return u

    def _category(self, n=None):
        n = n or _uniq("cat")
        return self.m.Category.objects.create(name=n, slug=n)

    def _product(self, category=None, price=PRICE):
        c = category or self._category()
        n = _uniq("p")
        return self.m.Product.objects.create(
            name=n, slug=n, category=c, description="d", price=price, sku=n)

    def _warehouse(self):
        return self.m.Warehouse.objects.create(name=_uniq("WH"), location="loc")

    def _supplier(self):
        return self.m.Supplier.objects.create(
            name=_uniq("Sup"), contact_person="P", email="s@e.com", phone="1", address="a")

    def _stock(self):
        return self.m.Stock.objects.create(
            product=self._product(), warehouse=self._warehouse(), quantity=QTY)

    def _purchase_order(self):
        return self.m.PurchaseOrder.objects.create(
            supplier=self._supplier(), created_by=self._user("po"), status="PENDING")

    def _order(self):
        return self.m.Order.objects.create(
            user=self._user("ord"), status="PENDING", shipping_address="a")

    def cart_total(self):
        order = self._order()
        item = self.m.OrderItem.objects.create(
            order=order, product=self._product(), quantity=QTY, unit_price=PRICE)
        sub = item.subtotal
        return {"total": float(sub() if callable(sub) else sub),
                "expected": float(PRICE * QTY)}


class GeminiDriver(_DjangoBase):
    """Product uses `title`; orders are SalesOrder. This generation declares its
    own User model, so FKs reject Django's default auth user."""

    PRICE_FIELD = "price"

    def _user(self, name="buyer"):
        u = self.m.User.objects.create(username=_uniq(name))
        u.set_password("pw12345")
        u.save()
        return u

    def _category(self, n=None):
        n = n or _uniq("cat")
        return self.m.Category.objects.create(name=n)

    def _product(self, category=None, price=PRICE):
        c = category or self._category()
        n = _uniq("p")
        return self.m.Product.objects.create(
            title=n, description="d", price=price, category=c,
            supplier=self._supplier())

    def _warehouse(self):
        return self.m.Warehouse.objects.create(name=_uniq("WH"), location="loc")

    def _supplier(self):
        return self.m.Supplier.objects.create(
            name=_uniq("Sup"), contact_email="s@e.com")

    def _stock(self):
        return self.m.Inventory.objects.create(
            product=self._product(), warehouse=self._warehouse(), quantity=QTY)

    def _purchase_order(self):
        return self.m.PurchaseOrder.objects.create(
            supplier=self._supplier(), warehouse=self._warehouse(), status="PENDING")

    def _order(self):
        return self.m.SalesOrder.objects.create(user=self._user("ord"), status="PENDING")

    def cart_total(self):
        cart = self.m.Cart.objects.create(user=self._user("cart"))
        p = self._product()
        cart.add_item(p, QTY)
        total = sum(float(i.product.price) * i.quantity
                    for i in self.m.CartItem.objects.filter(cart=cart))
        return {"total": total, "expected": float(PRICE * QTY)}


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



GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
