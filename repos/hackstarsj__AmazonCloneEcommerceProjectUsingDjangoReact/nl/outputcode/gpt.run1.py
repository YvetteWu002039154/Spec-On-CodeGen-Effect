from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone


User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=200)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True, default="")
    postal_code = models.CharField(max_length=30)
    country = models.CharField(max_length=2, default="US")
    phone = models.CharField(max_length=40, blank=True, default="")
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_default_shipping"]),
            models.Index(fields=["user", "is_default_billing"]),
        ]

    def clean(self) -> None:
        if self.is_default_shipping:
            Address.objects.filter(user=self.user, is_default_shipping=True).exclude(pk=self.pk).update(
                is_default_shipping=False
            )
        if self.is_default_billing:
            Address.objects.filter(user=self.user, is_default_billing=True).exclude(pk=self.pk).update(
                is_default_billing=False
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class Category(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Warehouse(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Product(TimeStampedModel):
    sku = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="products")
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    is_active = models.BooleanField(default=True)
    search_keywords = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["title"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.sku})"

    @staticmethod
    def search(query: str) -> models.QuerySet["Product"]:
        q = (query or "").strip()
        if not q:
            return Product.objects.filter(is_active=True)
        return Product.objects.filter(is_active=True).filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(search_keywords__icontains=q) | Q(sku__icontains=q)
        )


class Inventory(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventory_records")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inventory_records")
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("product", "warehouse")]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
            models.Index(fields=["warehouse"]),
        ]

    def clean(self) -> None:
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValidationError("Reserved quantity cannot exceed quantity on hand.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def quantity_available(self) -> int:
        return int(self.quantity_on_hand - self.quantity_reserved)

    @classmethod
    def get_or_create_record(cls, product: Product, warehouse: Warehouse) -> "Inventory":
        obj, _ = cls.objects.get_or_create(product=product, warehouse=warehouse, defaults={"quantity_on_hand": 0})
        return obj

    @classmethod
    def total_available(cls, product: Product) -> int:
        agg = cls.objects.filter(product=product).aggregate(
            available=Sum(F("quantity_on_hand") - F("quantity_reserved"))
        )
        return int(agg["available"] or 0)

    @classmethod
    def reserve(cls, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        with transaction.atomic():
            inv = cls.objects.select_for_update().get(product=product, warehouse=warehouse)
            if inv.quantity_available < quantity:
                raise ValidationError("Insufficient available inventory to reserve.")
            inv.quantity_reserved = F("quantity_reserved") + quantity
            inv.save(update_fields=["quantity_reserved", "updated_at"])
            inv.refresh_from_db(fields=["quantity_reserved", "quantity_on_hand"])

    @classmethod
    def release_reservation(cls, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        with transaction.atomic():
            inv = cls.objects.select_for_update().get(product=product, warehouse=warehouse)
            if inv.quantity_reserved < quantity:
                raise ValidationError("Cannot release more than reserved.")
            inv.quantity_reserved = F("quantity_reserved") - quantity
            inv.save(update_fields=["quantity_reserved", "updated_at"])
            inv.refresh_from_db(fields=["quantity_reserved", "quantity_on_hand"])

    @classmethod
    def increase_stock(cls, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        with transaction.atomic():
            inv = cls.objects.select_for_update().get(product=product, warehouse=warehouse)
            inv.quantity_on_hand = F("quantity_on_hand") + quantity
            inv.save(update_fields=["quantity_on_hand", "updated_at"])
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])

    @classmethod
    def decrease_stock(cls, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        with transaction.atomic():
            inv = cls.objects.select_for_update().get(product=product, warehouse=warehouse)
            if inv.quantity_on_hand < quantity:
                raise ValidationError("Insufficient stock to decrease.")
            if inv.quantity_on_hand - quantity < inv.quantity_reserved:
                raise ValidationError("Cannot decrease stock below reserved quantity.")
            inv.quantity_on_hand = F("quantity_on_hand") - quantity
            inv.save(update_fields=["quantity_on_hand", "updated_at"])
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")

    def __str__(self) -> str:
        return f"Cart({self.user_id})"

    @classmethod
    def for_user(cls, user: User) -> "Cart":
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    def clear(self) -> None:
        self.items.all().delete()

    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.select_related("product").all():
            total += item.line_total()
        return total

    def total_items(self) -> int:
        agg = self.items.aggregate(total=Sum("quantity"))
        return int(agg["total"] or 0)


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        unique_together = [("cart", "product")]
        indexes = [
            models.Index(fields=["cart", "product"]),
        ]

    def clean(self) -> None:
        if self.quantity <= 0:
            raise ValidationError("Quantity must be at least 1.")
        if not self.product.is_active:
            raise ValidationError("Product is not available.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def line_total(self) -> Decimal:
        return (self.product.price * Decimal(self.quantity)).quantize(Decimal("0.01"))


class OrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PLACED = "PLACED", "Placed"
    PAID = "PAID", "Paid"
    FULFILLED = "FULFILLED", "Fulfilled"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    billing_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    placed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Order({self.pk}) {self.status}"

    def clean(self) -> None:
        if self.shipping_address and self.shipping_address.user_id != self.user_id:
            raise ValidationError("Shipping address must belong to the order user.")
        if self.billing_address and self.billing_address.user_id != self.user_id:
            raise ValidationError("Billing address must belong to the order user.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.select_related("product").all():
            total += item.line_total
        return total.quantize(Decimal("0.01"))

    def total(self) -> Decimal:
        return self.subtotal()

    @transaction.atomic
    def place_from_cart(self, cart: Cart, shipping_address: Address, billing_address: Optional[Address] = None) -> None:
        if self.status != OrderStatus.DRAFT:
            raise ValidationError("Only draft orders can be placed.")
        if cart.user_id != self.user_id:
            raise ValidationError("Cart user mismatch.")
        if cart.items.count() == 0:
            raise ValidationError("Cart is empty.")
        if shipping_address.user_id != self.user_id:
            raise ValidationError("Shipping address must belong to the user.")
        if billing_address and billing_address.user_id != self.user_id:
            raise ValidationError("Billing address must belong to the user.")

        self.shipping_address = shipping_address
        self.billing_address = billing_address or shipping_address
        self.save(update_fields=["shipping_address", "billing_address", "updated_at"])

        self.items.all().delete()
        for ci in cart.items.select_related("product").all():
            OrderItem.objects.create(
                order=self,
                product=ci.product,
                unit_price=ci.product.price,
                quantity=ci.quantity,
            )

        self.status = OrderStatus.PLACED
        self.placed_at = timezone.now()
        self.save(update_fields=["status", "placed_at", "updated_at"])

        cart.clear()

    @transaction.atomic
    def cancel(self) -> None:
        if self.status in (OrderStatus.CANCELLED, OrderStatus.FULFILLED):
            raise ValidationError("Order cannot be cancelled.")
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_at", "updated_at"])


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
        ]

    def clean(self) -> None:
        if self.quantity <= 0:
            raise ValidationError("Quantity must be at least 1.")
        if self.unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.line_total = (self.unit_price * Decimal(self.quantity)).quantize(Decimal("0.01"))
        self.full_clean()
        super().save(*args, **kwargs)


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    RECEIVED = "RECEIVED", "Received"
    CANCELLED = "CANCELLED", "Cancelled"


class PurchaseOrder(TimeStampedModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=PurchaseOrderStatus.choices, default=PurchaseOrderStatus.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["supplier", "status"]),
            models.Index(fields=["warehouse", "status"]),
        ]

    def __str__(self) -> str:
        return f"PO({self.pk}) {self.status}"

    def total_cost(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.line_total
        return total.quantize(Decimal("0.01"))

    @transaction.atomic
    def submit(self) -> None:
        if self.status != PurchaseOrderStatus.DRAFT:
            raise ValidationError("Only draft purchase orders can be submitted.")
        if self.items.count() == 0:
            raise ValidationError("Purchase order has no items.")
        self.status = PurchaseOrderStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    @transaction.atomic
    def receive(self) -> None:
        if self.status != PurchaseOrderStatus.SUBMITTED:
            raise ValidationError("Only submitted purchase orders can be received.")
        for item in self.items.select_related("product").all():
            Inventory.get_or_create_record(item.product, self.warehouse)
        for item in self.items.select_related("product").all():
            Inventory.increase_stock(item.product, self.warehouse, item.quantity)
        self.status = PurchaseOrderStatus.RECEIVED
        self.received_at = timezone.now()
        self.save(update_fields=["status", "received_at", "updated_at"])

    @transaction.atomic
    def cancel(self) -> None:
        if self.status == PurchaseOrderStatus.RECEIVED:
            raise ValidationError("Received purchase orders cannot be cancelled.")
        if self.status == PurchaseOrderStatus.CANCELLED:
            return
        self.status = PurchaseOrderStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_at", "updated_at"])


class PurchaseOrderItem(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_order_items")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        unique_together = [("purchase_order", "product")]
        indexes = [
            models.Index(fields=["purchase_order"]),
            models.Index(fields=["product"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.line_total = (self.unit_cost * Decimal(self.quantity)).quantize(Decimal("0.01"))
        self.full_clean()
        super().save(*args, **kwargs)


class SalesOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    CONFIRMED = "CONFIRMED", "Confirmed"
    SHIPPED = "SHIPPED", "Shipped"
    CANCELLED = "CANCELLED", "Cancelled"


class SalesOrder(TimeStampedModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="sales_order")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="sales_orders")
    status = models.CharField(max_length=20, choices=SalesOrderStatus.choices, default=SalesOrderStatus.DRAFT)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["warehouse", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"SO({self.pk}) {self.status}"

    @transaction.atomic
    def confirm(self) -> None:
        if self.status != SalesOrderStatus.DRAFT:
            raise ValidationError("Only draft sales orders can be confirmed.")
        if self.order.status not in (OrderStatus.PLACED, OrderStatus.PAID):
            raise ValidationError("Order must be placed or paid to confirm sales order.")

        for item in self.order.items.select_related("product").all():
            Inventory.get_or_create_record(item.product, self.warehouse)

        for item in self.order.items.select_related("product").all():
            Inventory.reserve(item.product, self.warehouse, item.quantity)

        self.status = SalesOrderStatus.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at", "updated_at"])

    @transaction.atomic
    def ship(self) -> None:
        if self.status != SalesOrderStatus.CONFIRMED:
            raise ValidationError("Only confirmed sales orders can be shipped.")

        for item in self.order.items.select_related("product").all():
            Inventory.decrease_stock(item.product, self.warehouse, item.quantity)
            Inventory.release_reservation(item.product, self.warehouse, item.quantity)

        self.status = SalesOrderStatus.SHIPPED
        self.shipped_at = timezone.now()
        self.save(update_fields=["status", "shipped_at", "updated_at"])

        if self.order.status not in (OrderStatus.CANCELLED, OrderStatus.FULFILLED):
            self.order.status = OrderStatus.FULFILLED
            self.order.save(update_fields=["status", "updated_at"])

    @transaction.atomic
    def cancel(self) -> None:
        if self.status == SalesOrderStatus.SHIPPED:
            raise ValidationError("Shipped sales orders cannot be cancelled.")
        if self.status == SalesOrderStatus.CANCELLED:
            return

        if self.status == SalesOrderStatus.CONFIRMED:
            for item in self.order.items.select_related("product").all():
                Inventory.release_reservation(item.product, self.warehouse, item.quantity)

        self.status = SalesOrderStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_at", "updated_at"])


class UserManagementService:
    @staticmethod
    def create_user(username: str, email: str, password: str, is_staff: bool = False, is_superuser: bool = False) -> User:
        if not username or not username.strip():
            raise ValidationError("Username is required.")
        if not email or not email.strip():
            raise ValidationError("Email is required.")
        if not password:
            raise ValidationError("Password is required.")
        user_model = get_user_model()
        user = user_model(username=username.strip(), email=email.strip(), is_staff=is_staff, is_superuser=is_superuser)
        user.set_password(password)
        user.full_clean()
        user.save()
        return user

    @staticmethod
    def deactivate_user(user: User) -> None:
        user.is_active = False
        user.save(update_fields=["is_active"])


class CatalogService:
    @staticmethod
    def list_active_products(category: Optional[Category] = None) -> models.QuerySet[Product]:
        qs = Product.objects.filter(is_active=True)
        if category is not None:
            qs = qs.filter(category=category)
        return qs

    @staticmethod
    def search_products(query: str) -> models.QuerySet[Product]:
        return Product.search(query)


class CartService:
    @staticmethod
    @transaction.atomic
    def add_to_cart(user: User, product: Product, quantity: int) -> Cart:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if not product.is_active:
            raise ValidationError("Product is not available.")
        cart = Cart.for_user(user)
        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity = item.quantity + quantity
            item.save(update_fields=["quantity", "updated_at"])
        return cart

    @staticmethod
    @transaction.atomic
    def set_quantity(user: User, product: Product, quantity: int) -> Cart:
        cart = Cart.for_user(user)
        if quantity <= 0:
            CartItem.objects.filter(cart=cart, product=product).delete()
            return cart
        item, _ = CartItem.objects.select_for_update().get_or_create(cart=cart, product=product, defaults={"quantity": 0})
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
        return cart

    @staticmethod
    @transaction.atomic
    def remove_from_cart(user: User, product: Product) -> Cart:
        cart = Cart.for_user(user)
        CartItem.objects.filter(cart=cart, product=product).delete()
        return cart

    @staticmethod
    def get_cart(user: User) -> Cart:
        return Cart.for_user(user)


class CheckoutService:
    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user: User, shipping_address: Address, billing_address: Optional[Address] = None) -> Order:
        cart = Cart.for_user(user)
        order = Order.objects.create(user=user, status=OrderStatus.DRAFT)
        order.place_from_cart(cart=cart, shipping_address=shipping_address, billing_address=billing_address)
        return order


class InventoryAdminService:
    @staticmethod
    @transaction.atomic
    def create_purchase_order(supplier: Supplier, warehouse: Warehouse, items: List[Tuple[Product, int, Decimal]]) -> PurchaseOrder:
        if not items:
            raise ValidationError("Items are required.")
        po = PurchaseOrder.objects.create(supplier=supplier, warehouse=warehouse, status=PurchaseOrderStatus.DRAFT)
        for product, quantity, unit_cost in items:
            if quantity <= 0:
                raise ValidationError("Quantity must be positive.")
            if unit_cost < 0:
                raise ValidationError("Unit cost cannot be negative.")
            PurchaseOrderItem.objects.create(purchase_order=po, product=product, quantity=quantity, unit_cost=unit_cost)
        return po

    @staticmethod
    @transaction.atomic
    def receive_purchase_order(po: PurchaseOrder) -> None:
        po.receive()

    @staticmethod
    @transaction.atomic
    def create_sales_order_for_order(order: Order, warehouse: Warehouse) -> SalesOrder:
        if order.status not in (OrderStatus.PLACED, OrderStatus.PAID):
            raise ValidationError("Order must be placed or paid.")
        so, created = SalesOrder.objects.get_or_create(order=order, defaults={"warehouse": warehouse})
        if not created and so.warehouse_id != warehouse.id:
            raise ValidationError("Sales order already exists with a different warehouse.")
        return so

    @staticmethod
    @transaction.atomic
    def confirm_sales_order(so: SalesOrder) -> None:
        so.confirm()

    @staticmethod
    @transaction.atomic
    def ship_sales_order(so: SalesOrder) -> None:
        so.ship()


class MultiLevelEcommerceService:
    @staticmethod
    def get_category_tree(root: Optional[Category] = None) -> List[Dict[str, Any]]:
        def build(node: Category) -> Dict[str, Any]:
            return {
                "id": node.id,
                "name": node.name,
                "slug": node.slug,
                "children": [build(child) for child in node.children.filter(is_active=True).order_by("name")],
            }

        if root is not None:
            if not root.is_active:
                return []
            return [build(root)]
        roots = Category.objects.filter(parent__isnull=True, is_active=True).order_by("name")
        return [build(r) for r in roots]