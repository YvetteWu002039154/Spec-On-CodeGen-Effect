from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone


User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["is_active"])]

    def __str__(self) -> str:
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self) -> str:
        return self.name


class Warehouse(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["code"]), models.Index(fields=["is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Product(TimeStampedModel):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
        ]

    def clean(self) -> None:
        if self.price is None or self.price < 0:
            raise ValidationError({"price": "Price must be non-negative."})

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"


class Inventory(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventories")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventories")
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("product", "warehouse")]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
        ]

    def clean(self) -> None:
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValidationError("Reserved quantity cannot exceed quantity on hand.")

    @property
    def quantity_available(self) -> int:
        qoh = int(self.quantity_on_hand or 0)
        qr = int(self.quantity_reserved or 0)
        return max(0, qoh - qr)

    def __str__(self) -> str:
        return f"{self.product.sku} @ {self.warehouse.code}"


class InventoryMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        PURCHASE_RECEIPT = "PURCHASE_RECEIPT", "Purchase Receipt"
        SALES_SHIPMENT = "SALES_SHIPMENT", "Sales Shipment"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        RESERVATION = "RESERVATION", "Reservation"
        RELEASE = "RELEASE", "Release"

    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=32, choices=MovementType.choices)
    quantity_delta_on_hand = models.IntegerField(default=0)
    quantity_delta_reserved = models.IntegerField(default=0)
    reference = models.CharField(max_length=64, blank=True, default="")
    note = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["movement_type"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["created_at"]),
        ]

    def clean(self) -> None:
        if self.quantity_delta_on_hand == 0 and self.quantity_delta_reserved == 0:
            raise ValidationError("Movement must change on-hand or reserved quantity.")

    def __str__(self) -> str:
        return f"{self.movement_type} {self.inventory} ({self.quantity_delta_on_hand}/{self.quantity_delta_reserved})"


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")

    def __str__(self) -> str:
        return f"Cart({self.user_id})"

    @transaction.atomic
    def add_item(self, product: Product, quantity: int = 1) -> "CartItem":
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if not product.is_active:
            raise ValidationError("Product is not active.")
        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=self, product=product, defaults={"quantity": 0}
        )
        item.quantity = F("quantity") + quantity
        item.save(update_fields=["quantity"])
        item.refresh_from_db(fields=["quantity"])
        return item

    @transaction.atomic
    def set_item_quantity(self, product: Product, quantity: int) -> Optional["CartItem"]:
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative.")
        try:
            item = CartItem.objects.select_for_update().get(cart=self, product=product)
        except CartItem.DoesNotExist:
            if quantity == 0:
                return None
            if not product.is_active:
                raise ValidationError("Product is not active.")
            return CartItem.objects.create(cart=self, product=product, quantity=quantity)
        if quantity == 0:
            item.delete()
            return None
        item.quantity = quantity
        item.full_clean()
        item.save(update_fields=["quantity"])
        return item

    def clear(self) -> None:
        self.items.all().delete()

    def total_items(self) -> int:
        agg = self.items.aggregate(total=Sum("quantity"))
        return int(agg["total"] or 0)

    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.select_related("product").all():
            total += (item.product.price or Decimal("0.00")) * item.quantity
        return total


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("cart", "product")]
        indexes = [models.Index(fields=["cart", "product"])]

    def clean(self) -> None:
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be positive."})
        if not self.product.is_active:
            raise ValidationError("Product is not active.")

    def __str__(self) -> str:
        return f"{self.product.sku} x {self.quantity}"


class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=64, unique=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["created_at"]),
        ]

    def clean(self) -> None:
        if not self.supplier.is_active:
            raise ValidationError("Supplier is not active.")
        if not self.warehouse.is_active:
            raise ValidationError("Warehouse is not active.")

    def __str__(self) -> str:
        return f"PO {self.reference} ({self.status})"

    def total_cost(self) -> Decimal:
        total = Decimal("0.00")
        for line in self.lines.select_related("product").all():
            total += (line.unit_cost or Decimal("0.00")) * line.quantity
        return total

    @transaction.atomic
    def submit(self) -> None:
        po = PurchaseOrder.objects.select_for_update().get(pk=self.pk)
        if po.status != PurchaseOrder.Status.DRAFT:
            raise ValidationError("Only draft purchase orders can be submitted.")
        if not po.lines.exists():
            raise ValidationError("Purchase order must have at least one line.")
        po.status = PurchaseOrder.Status.SUBMITTED
        po.ordered_at = timezone.now()
        po.save(update_fields=["status", "ordered_at", "updated_at"])
        self.refresh_from_db()

    @transaction.atomic
    def receive(self) -> None:
        po = PurchaseOrder.objects.select_for_update().get(pk=self.pk)
        if po.status != PurchaseOrder.Status.SUBMITTED:
            raise ValidationError("Only submitted purchase orders can be received.")
        lines = list(po.lines.select_related("product").all())
        if not lines:
            raise ValidationError("Purchase order must have at least one line.")
        for line in lines:
            inv, _ = Inventory.objects.select_for_update().get_or_create(
                product=line.product, warehouse=po.warehouse, defaults={"quantity_on_hand": 0, "quantity_reserved": 0}
            )
            Inventory.objects.filter(pk=inv.pk).update(quantity_on_hand=F("quantity_on_hand") + line.quantity)
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
            InventoryMovement.objects.create(
                inventory=inv,
                movement_type=InventoryMovement.MovementType.PURCHASE_RECEIPT,
                quantity_delta_on_hand=int(line.quantity),
                quantity_delta_reserved=0,
                reference=po.reference,
                note="Purchase order received",
            )
        po.status = PurchaseOrder.Status.RECEIVED
        po.received_at = timezone.now()
        po.save(update_fields=["status", "received_at", "updated_at"])
        self.refresh_from_db()

    @transaction.atomic
    def cancel(self) -> None:
        po = PurchaseOrder.objects.select_for_update().get(pk=self.pk)
        if po.status in (PurchaseOrder.Status.RECEIVED, PurchaseOrder.Status.CANCELLED):
            raise ValidationError("Cannot cancel a received or already cancelled purchase order.")
        po.status = PurchaseOrder.Status.CANCELLED
        po.save(update_fields=["status", "updated_at"])
        self.refresh_from_db()


class PurchaseOrderLine(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_order_lines")
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [("purchase_order", "product")]
        indexes = [models.Index(fields=["purchase_order", "product"])]

    def clean(self) -> None:
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be positive."})
        if self.unit_cost is None or self.unit_cost < 0:
            raise ValidationError({"unit_cost": "Unit cost must be non-negative."})
        if not self.product.is_active:
            raise ValidationError("Product is not active.")
        if self.purchase_order.status != PurchaseOrder.Status.DRAFT:
            raise ValidationError("Can only modify lines on a draft purchase order.")

    def __str__(self) -> str:
        return f"{self.product.sku} x {self.quantity} @ {self.unit_cost}"


class SalesOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PLACED = "PLACED", "Placed"
        PAID = "PAID", "Paid"
        SHIPPED = "SHIPPED", "Shipped"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="sales_orders")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=64, unique=True)
    placed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def clean(self) -> None:
        if not self.warehouse.is_active:
            raise ValidationError("Warehouse is not active.")

    def __str__(self) -> str:
        return f"SO {self.reference} ({self.status})"

    def total_amount(self) -> Decimal:
        total = Decimal("0.00")
        for line in self.lines.select_related("product").all():
            total += (line.unit_price or Decimal("0.00")) * line.quantity
        return total

    @transaction.atomic
    def place(self) -> None:
        so = SalesOrder.objects.select_for_update().get(pk=self.pk)
        if so.status != SalesOrder.Status.DRAFT:
            raise ValidationError("Only draft sales orders can be placed.")
        lines = list(so.lines.select_related("product").all())
        if not lines:
            raise ValidationError("Sales order must have at least one line.")
        for line in lines:
            inv, _ = Inventory.objects.select_for_update().get_or_create(
                product=line.product, warehouse=so.warehouse, defaults={"quantity_on_hand": 0, "quantity_reserved": 0}
            )
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
            if inv.quantity_available < line.quantity:
                raise ValidationError(f"Insufficient inventory for SKU {line.product.sku}.")
            Inventory.objects.filter(pk=inv.pk).update(quantity_reserved=F("quantity_reserved") + line.quantity)
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
            InventoryMovement.objects.create(
                inventory=inv,
                movement_type=InventoryMovement.MovementType.RESERVATION,
                quantity_delta_on_hand=0,
                quantity_delta_reserved=int(line.quantity),
                reference=so.reference,
                note="Reserved for sales order",
            )
        so.status = SalesOrder.Status.PLACED
        so.placed_at = timezone.now()
        so.save(update_fields=["status", "placed_at", "updated_at"])
        self.refresh_from_db()

    @transaction.atomic
    def mark_paid(self) -> None:
        so = SalesOrder.objects.select_for_update().get(pk=self.pk)
        if so.status != SalesOrder.Status.PLACED:
            raise ValidationError("Only placed sales orders can be marked paid.")
        so.status = SalesOrder.Status.PAID
        so.paid_at = timezone.now()
        so.save(update_fields=["status", "paid_at", "updated_at"])
        self.refresh_from_db()

    @transaction.atomic
    def ship(self) -> None:
        so = SalesOrder.objects.select_for_update().get(pk=self.pk)
        if so.status != SalesOrder.Status.PAID:
            raise ValidationError("Only paid sales orders can be shipped.")
        lines = list(so.lines.select_related("product").all())
        if not lines:
            raise ValidationError("Sales order must have at least one line.")
        for line in lines:
            inv = Inventory.objects.select_for_update().get(product=line.product, warehouse=so.warehouse)
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
            if inv.quantity_reserved < line.quantity:
                raise ValidationError(f"Reserved inventory insufficient for SKU {line.product.sku}.")
            Inventory.objects.filter(pk=inv.pk).update(
                quantity_reserved=F("quantity_reserved") - line.quantity,
                quantity_on_hand=F("quantity_on_hand") - line.quantity,
            )
            inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
            InventoryMovement.objects.create(
                inventory=inv,
                movement_type=InventoryMovement.MovementType.SALES_SHIPMENT,
                quantity_delta_on_hand=-int(line.quantity),
                quantity_delta_reserved=-int(line.quantity),
                reference=so.reference,
                note="Shipped sales order",
            )
        so.status = SalesOrder.Status.SHIPPED
        so.shipped_at = timezone.now()
        so.save(update_fields=["status", "shipped_at", "updated_at"])
        self.refresh_from_db()

    @transaction.atomic
    def cancel(self) -> None:
        so = SalesOrder.objects.select_for_update().get(pk=self.pk)
        if so.status in (SalesOrder.Status.SHIPPED, SalesOrder.Status.CANCELLED):
            raise ValidationError("Cannot cancel a shipped or already cancelled sales order.")
        lines = list(so.lines.select_related("product").all())
        if so.status in (SalesOrder.Status.PLACED, SalesOrder.Status.PAID):
            for line in lines:
                inv = Inventory.objects.select_for_update().get(product=line.product, warehouse=so.warehouse)
                inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
                if inv.quantity_reserved < line.quantity:
                    raise ValidationError(f"Reserved inventory insufficient to release for SKU {line.product.sku}.")
                Inventory.objects.filter(pk=inv.pk).update(quantity_reserved=F("quantity_reserved") - line.quantity)
                inv.refresh_from_db(fields=["quantity_on_hand", "quantity_reserved"])
                InventoryMovement.objects.create(
                    inventory=inv,
                    movement_type=InventoryMovement.MovementType.RELEASE,
                    quantity_delta_on_hand=0,
                    quantity_delta_reserved=-int(line.quantity),
                    reference=so.reference,
                    note="Released reservation due to cancellation",
                )
        so.status = SalesOrder.Status.CANCELLED
        so.save(update_fields=["status", "updated_at"])
        self.refresh_from_db()


class SalesOrderLine(TimeStampedModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales_order_lines")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [("sales_order", "product")]
        indexes = [models.Index(fields=["sales_order", "product"])]

    def clean(self) -> None:
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be positive."})
        if self.unit_price is None or self.unit_price < 0:
            raise ValidationError({"unit_price": "Unit price must be non-negative."})
        if not self.product.is_active:
            raise ValidationError("Product is not active.")
        if self.sales_order.status != SalesOrder.Status.DRAFT:
            raise ValidationError("Can only modify lines on a draft sales order.")

    def __str__(self) -> str:
        return f"{self.product.sku} x {self.quantity} @ {self.unit_price}"


class AuthService:
    @staticmethod
    def signup(username: str, email: str, password: str, **extra_fields: Any) -> User:
        if not username:
            raise ValidationError("Username is required.")
        if not email:
            raise ValidationError("Email is required.")
        if not password:
            raise ValidationError("Password is required.")
        user_model = get_user_model()
        if user_model.objects.filter(Q(username=username) | Q(email=email)).exists():
            raise ValidationError("User with given username or email already exists.")
        user = user_model.objects.create_user(username=username, email=email, password=password, **extra_fields)
        return user

    @staticmethod
    def login(request: Any, username: str, password: str) -> User:
        if not username or not password:
            raise ValidationError("Username and password are required.")
        user = authenticate(request, username=username, password=password)
        if user is None:
            raise ValidationError("Invalid credentials.")
        return user

    @staticmethod
    def logout(request: Any) -> None:
        from django.contrib.auth import logout as dj_logout

        dj_logout(request)


class ProductService:
    @staticmethod
    def list_active(category: Optional[Category] = None) -> models.QuerySet[Product]:
        qs = Product.objects.filter(is_active=True, category__is_active=True)
        if category is not None:
            qs = qs.filter(category=category)
        return qs

    @staticmethod
    def search(query: str) -> models.QuerySet[Product]:
        q = (query or "").strip()
        if not q:
            return Product.objects.none()
        return Product.objects.filter(is_active=True).filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))

    @staticmethod
    def get_detail(slug: str) -> Product:
        try:
            return Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist as e:
            raise ValidationError("Product not found.") from e


class CartService:
    @staticmethod
    def get_or_create_cart(user: User) -> Cart:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    @staticmethod
    def add_to_cart(user: User, product: Product, quantity: int = 1) -> CartItem:
        cart = CartService.get_or_create_cart(user)
        return cart.add_item(product=product, quantity=quantity)

    @staticmethod
    def update_quantity(user: User, product: Product, quantity: int) -> Optional[CartItem]:
        cart = CartService.get_or_create_cart(user)
        return cart.set_item_quantity(product=product, quantity=quantity)

    @staticmethod
    def clear_cart(user: User) -> None:
        cart = CartService.get_or_create_cart(user)
        cart.clear()


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_sales_order_from_cart(user: User, warehouse: Warehouse, reference: str) -> SalesOrder:
        if not warehouse.is_active:
            raise ValidationError("Warehouse is not active.")
        cart = CartService.get_or_create_cart(user)
        items = list(cart.items.select_related("product").all())
        if not items:
            raise ValidationError("Cart is empty.")
        if SalesOrder.objects.filter(reference=reference).exists():
            raise ValidationError("Sales order reference already exists.")
        so = SalesOrder.objects.create(user=user, warehouse=warehouse, reference=reference, status=SalesOrder.Status.DRAFT)
        for item in items:
            if not item.product.is_active:
                raise ValidationError("Cart contains inactive product.")
            SalesOrderLine.objects.create(
                sales_order=so,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
        cart.clear()
        return so

    @staticmethod
    def place_sales_order(sales_order: SalesOrder) -> None:
        sales_order.place()

    @staticmethod
    def pay_sales_order(sales_order: SalesOrder) -> None:
        sales_order.mark_paid()

    @staticmethod
    def ship_sales_order(sales_order: SalesOrder) -> None:
        sales_order.ship()

    @staticmethod
    def cancel_sales_order(sales_order: SalesOrder) -> None:
        sales_order.cancel()

    @staticmethod
    @transaction.atomic
    def create_purchase_order(supplier: Supplier, warehouse: Warehouse, reference: str, lines: List[Tuple[Product, int, Decimal]]) -> PurchaseOrder:
        if PurchaseOrder.objects.filter(reference=reference).exists():
            raise ValidationError("Purchase order reference already exists.")
        po = PurchaseOrder.objects.create(supplier=supplier, warehouse=warehouse, reference=reference, status=PurchaseOrder.Status.DRAFT)
        for product, qty, unit_cost in lines:
            pol = PurchaseOrderLine(purchase_order=po, product=product, quantity=qty, unit_cost=unit_cost)
            pol.full_clean()
            pol.save()
        return po

    @staticmethod
    def submit_purchase_order(purchase_order: PurchaseOrder) -> None:
        purchase_order.submit()

    @staticmethod
    def receive_purchase_order(purchase_order: PurchaseOrder) -> None:
        purchase_order.receive()

    @staticmethod
    def cancel_purchase_order(purchase_order: PurchaseOrder) -> None:
        purchase_order.cancel()