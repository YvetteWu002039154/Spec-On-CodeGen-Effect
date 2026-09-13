from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        STAFF = "staff", "Staff"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    def clean(self) -> None:
        super().clean()
        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role == self.Role.STAFF:
            self.is_staff = True
            self.is_superuser = False
        else:
            self.is_staff = False
            self.is_superuser = False


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["parent", "is_active"])]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError("Category cannot be its own parent.")


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="products")
    sku = models.CharField(max_length=80, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.price is None or self.price < 0:
            raise ValidationError("Price must be non-negative.")


class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventories")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventories")
    quantity_on_hand = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)

    class Meta:
        unique_together = [("product", "warehouse")]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
            models.Index(fields=["warehouse"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} @ {self.warehouse.code}"

    @property
    def available(self) -> int:
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    def clean(self) -> None:
        super().clean()
        if self.quantity_on_hand < 0:
            raise ValidationError("quantity_on_hand cannot be negative.")
        if self.quantity_reserved < 0:
            raise ValidationError("quantity_reserved cannot be negative.")
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValidationError("quantity_reserved cannot exceed quantity_on_hand.")

    @classmethod
    def total_available_for_product(cls, product: Product) -> int:
        agg = cls.objects.filter(product=product).aggregate(
            total=Sum(F("quantity_on_hand") - F("quantity_reserved"))
        )
        return int(agg["total"] or 0)


class InventoryTransaction(models.Model):
    class Type(models.TextChoices):
        PURCHASE_RECEIPT = "purchase_receipt", "Purchase Receipt"
        SALES_SHIPMENT = "sales_shipment", "Sales Shipment"
        RESERVATION = "reservation", "Reservation"
        RELEASE = "release", "Release"
        ADJUSTMENT = "adjustment", "Adjustment"

    created_at = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=30, choices=Type.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventory_transactions")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_transactions")
    quantity = models.IntegerField()
    reference = models.CharField(max_length=120, blank=True)

    def clean(self) -> None:
        super().clean()
        if self.quantity == 0:
            raise ValidationError("Transaction quantity cannot be zero.")


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Cart({self.user_id})"

    def clean(self) -> None:
        super().clean()
        if not self.user_id:
            raise ValidationError("Cart must have a user.")

    @transaction.atomic
    def add_item(self, product: Product, quantity: int = 1) -> "CartItem":
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=self, product=product, defaults={"quantity": 0}
        )
        new_qty = item.quantity + quantity
        if new_qty <= 0:
            item.delete()
            raise ValidationError("Resulting quantity must be positive.")
        item.quantity = new_qty
        item.full_clean()
        item.save()
        return item

    @transaction.atomic
    def set_item_quantity(self, product: Product, quantity: int) -> None:
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative.")
        try:
            item = CartItem.objects.select_for_update().get(cart=self, product=product)
        except CartItem.DoesNotExist:
            if quantity == 0:
                return
            item = CartItem(cart=self, product=product, quantity=quantity)
            item.full_clean()
            item.save()
            return
        if quantity == 0:
            item.delete()
            return
        item.quantity = quantity
        item.full_clean()
        item.save()

    def clear(self) -> None:
        self.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = [("cart", "product")]
        indexes = [models.Index(fields=["cart"]), models.Index(fields=["product"])]

    def __str__(self) -> str:
        return f"{self.product.sku} x {self.quantity}"

    def clean(self) -> None:
        super().clean()
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_purchase_orders")
    created_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["supplier"])]

    def __str__(self) -> str:
        return f"PO#{self.id or 'new'}"

    def clean(self) -> None:
        super().clean()
        if self.status == self.Status.SUBMITTED and not self.submitted_at:
            self.submitted_at = timezone.now()
        if self.status == self.Status.RECEIVED and not self.received_at:
            self.received_at = timezone.now()

    @transaction.atomic
    def submit(self) -> None:
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only draft purchase orders can be submitted.")
        if not self.lines.exists():
            raise ValidationError("Purchase order must have at least one line.")
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "submitted_at"])

    @transaction.atomic
    def receive(self) -> None:
        if self.status != self.Status.SUBMITTED:
            raise ValidationError("Only submitted purchase orders can be received.")
        if not self.lines.exists():
            raise ValidationError("Purchase order must have at least one line.")
        for line in self.lines.select_related("product").select_for_update():
            if line.quantity <= 0:
                raise ValidationError("Purchase order line quantity must be positive.")
            inv, _ = Inventory.objects.select_for_update().get_or_create(
                product=line.product, warehouse=self.warehouse, defaults={"quantity_on_hand": 0, "quantity_reserved": 0}
            )
            inv.quantity_on_hand = F("quantity_on_hand") + line.quantity
            inv.save(update_fields=["quantity_on_hand"])
            InventoryTransaction.objects.create(
                type=InventoryTransaction.Type.PURCHASE_RECEIPT,
                product=line.product,
                warehouse=self.warehouse,
                quantity=line.quantity,
                reference=f"PO:{self.id}",
            )
        self.status = self.Status.RECEIVED
        self.received_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "received_at"])

    @transaction.atomic
    def cancel(self) -> None:
        if self.status in (self.Status.RECEIVED, self.Status.CANCELLED):
            raise ValidationError("Cannot cancel a received or already cancelled purchase order.")
        self.status = self.Status.CANCELLED
        self.full_clean()
        self.save(update_fields=["status"])


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_order_lines")
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [("purchase_order", "product")]
        indexes = [models.Index(fields=["purchase_order"]), models.Index(fields=["product"])]

    def clean(self) -> None:
        super().clean()
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if self.unit_cost is None or self.unit_cost < 0:
            raise ValidationError("Unit cost must be non-negative.")


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLACED = "placed", "Placed"
        PAID = "paid", "Paid"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    placed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"]), models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"SO#{self.id or 'new'}"

    def clean(self) -> None:
        super().clean()
        if self.status == self.Status.PLACED and not self.placed_at:
            self.placed_at = timezone.now()
        if self.status == self.Status.PAID and not self.paid_at:
            self.paid_at = timezone.now()
        if self.status == self.Status.FULFILLED and not self.fulfilled_at:
            self.fulfilled_at = timezone.now()
        if self.status == self.Status.CANCELLED and not self.cancelled_at:
            self.cancelled_at = timezone.now()

    @transaction.atomic
    def place_from_cart(self, cart: Cart) -> None:
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only draft sales orders can be placed.")
        if cart.user_id != self.user_id:
            raise ValidationError("Cart user does not match sales order user.")
        items = list(cart.items.select_related("product"))
        if not items:
            raise ValidationError("Cart is empty.")
        self.save()
        self.lines.all().delete()
        for item in items:
            SalesOrderLine.objects.create(
                sales_order=self,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
        self.status = self.Status.PLACED
        self.placed_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "placed_at"])
        cart.clear()

    @transaction.atomic
    def mark_paid(self) -> None:
        if self.status != self.Status.PLACED:
            raise ValidationError("Only placed orders can be marked paid.")
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "paid_at"])

    @transaction.atomic
    def fulfill(self, warehouse: Warehouse) -> None:
        if self.status != self.Status.PAID:
            raise ValidationError("Only paid orders can be fulfilled.")
        lines = list(self.lines.select_related("product").select_for_update())
        if not lines:
            raise ValidationError("Sales order must have at least one line.")

        for line in lines:
            inv = Inventory.objects.select_for_update().filter(product=line.product, warehouse=warehouse).first()
            if not inv or inv.available < line.quantity:
                raise ValidationError("Insufficient inventory to fulfill the order.")

        for line in lines:
            inv = Inventory.objects.select_for_update().get(product=line.product, warehouse=warehouse)
            inv.quantity_on_hand = F("quantity_on_hand") - line.quantity
            inv.save(update_fields=["quantity_on_hand"])
            InventoryTransaction.objects.create(
                type=InventoryTransaction.Type.SALES_SHIPMENT,
                product=line.product,
                warehouse=warehouse,
                quantity=-int(line.quantity),
                reference=f"SO:{self.id}",
            )

        self.status = self.Status.FULFILLED
        self.fulfilled_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "fulfilled_at"])

    @transaction.atomic
    def cancel(self) -> None:
        if self.status in (self.Status.FULFILLED, self.Status.CANCELLED):
            raise ValidationError("Cannot cancel a fulfilled or already cancelled order.")
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "cancelled_at"])


class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales_order_lines")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [("sales_order", "product")]
        indexes = [models.Index(fields=["sales_order"]), models.Index(fields=["product"])]

    def clean(self) -> None:
        super().clean()
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if self.unit_price is None or self.unit_price < 0:
            raise ValidationError("Unit price must be non-negative.")


class ProductQueryService:
    @staticmethod
    def search(query: str | None = None, category: Category | None = None, active_only: bool = True) -> models.QuerySet[Product]:
        qs = Product.objects.all()
        if active_only:
            qs = qs.filter(is_active=True, category__is_active=True)
        if category is not None:
            qs = qs.filter(category=category)
        if query:
            q = query.strip()
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(sku__icontains=q))
        return qs.distinct()


class UserManagementService:
    @staticmethod
    def set_role(user: User, role: str) -> None:
        if role not in User.Role.values:
            raise ValidationError("Invalid role.")
        user.role = role
        user.full_clean()
        user.save(update_fields=["role", "is_staff", "is_superuser"])