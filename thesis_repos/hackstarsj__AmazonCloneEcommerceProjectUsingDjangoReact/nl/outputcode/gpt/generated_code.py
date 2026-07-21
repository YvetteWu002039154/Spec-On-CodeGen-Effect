from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from django.utils.text import slugify


MONEY_PLACES = Decimal("0.01")


def to_money(value) -> Decimal:
    return Decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    is_customer = models.BooleanField(default=True)
    is_supplier = models.BooleanField(default=False)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.username


class Category(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def clean(self) -> None:
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError("Category cannot be its own parent.")

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            index = 1
            while Category.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base}-{index}"
                index += 1
            self.slug = slug
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supplier_profile",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Warehouse(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))], default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            index = 1
            while Product.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base}-{index}"
                index += 1
            self.slug = slug
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def total_stock(self) -> int:
        total = self.inventory_items.aggregate(total=Sum("quantity"))["total"]
        return int(total or 0)

    def __str__(self) -> str:
        return self.name


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "id"]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            result = super().save(*args, **kwargs)
            if self.is_primary:
                ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(is_primary=False)
            return result

    def __str__(self) -> str:
        return f"{self.product.name} image"


class Inventory(TimeStampedModel):
    product = models.ForeignKey(Product, related_name="inventory_items", on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, related_name="inventory_items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "warehouse")
        ordering = ["product__name", "warehouse__name"]

    def clean(self) -> None:
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative.")
        if self.reorder_level < 0:
            raise ValidationError("Reorder level cannot be negative.")

    def adjust(self, delta: int) -> None:
        new_quantity = self.quantity + delta
        if new_quantity < 0:
            raise ValidationError("Insufficient inventory.")
        self.quantity = new_quantity
        self.save(update_fields=["quantity", "updated_at"])

    @property
    def needs_reorder(self) -> bool:
        return self.quantity <= self.reorder_level

    def __str__(self) -> str:
        return f"{self.product} @ {self.warehouse}: {self.quantity}"


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="cart", on_delete=models.CASCADE)

    def add_product(self, product: Product, quantity: int = 1) -> "CartItem":
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={"quantity": quantity, "unit_price": product.price},
        )
        if not created:
            item.quantity += quantity
            item.unit_price = product.price
            item.save()
        return item

    def remove_product(self, product: Product) -> None:
        CartItem.objects.filter(cart=self, product=product).delete()

    def clear(self) -> None:
        self.items.all().delete()

    @property
    def subtotal(self) -> Decimal:
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("unit_price"), output_field=models.DecimalField(max_digits=14, decimal_places=2))
        )["total"]
        return to_money(total or Decimal("0.00"))

    def __str__(self) -> str:
        return f"Cart({self.user})"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="cart_items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        unique_together = ("cart", "product")

    def save(self, *args, **kwargs):
        self.unit_price = to_money(self.unit_price)
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def total_price(self) -> Decimal:
        return to_money(self.quantity * self.unit_price)

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"


class Order(TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    placed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def recalculate_total(self) -> Decimal:
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("unit_price"), output_field=models.DecimalField(max_digits=14, decimal_places=2))
        )["total"]
        self.total_amount = to_money(total or Decimal("0.00"))
        self.save(update_fields=["total_amount", "updated_at"])
        return self.total_amount

    @classmethod
    def create_from_cart(cls, user: User, shipping_address: str, billing_address: str = "") -> "Order":
        if not hasattr(user, "cart"):
            raise ValidationError("Cart does not exist.")
        cart = user.cart
        if not cart.items.exists():
            raise ValidationError("Cart is empty.")
        with transaction.atomic():
            order = cls.objects.create(
                user=user,
                shipping_address=shipping_address,
                billing_address=billing_address or shipping_address,
                status=cls.STATUS_PENDING,
            )
            for item in cart.items.select_related("product"):
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
            order.recalculate_total()
            cart.clear()
            return order

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.user}"


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    def save(self, *args, **kwargs):
        self.unit_price = to_money(self.unit_price)
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def total_price(self) -> Decimal:
        return to_money(self.quantity * self.unit_price)

    def __str__(self) -> str:
        return f"OrderItem({self.product}, {self.quantity})"


class PurchaseOrder(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_ORDERED = "ordered"
    STATUS_RECEIVED = "received"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_RECEIVED, "Received"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    supplier = models.ForeignKey(Supplier, related_name="purchase_orders", on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, related_name="purchase_orders", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    expected_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def recalculate_total(self) -> Decimal:
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("unit_cost"), output_field=models.DecimalField(max_digits=14, decimal_places=2))
        )["total"]
        self.total_amount = to_money(total or Decimal("0.00"))
        self.save(update_fields=["total_amount", "updated_at"])
        return self.total_amount

    def receive(self) -> None:
        if self.status == self.STATUS_RECEIVED:
            raise ValidationError("Purchase order already received.")
        if self.status == self.STATUS_CANCELLED:
            raise ValidationError("Cancelled purchase order cannot be received.")
        with transaction.atomic():
            for item in self.items.select_related("product"):
                inventory, _ = Inventory.objects.get_or_create(
                    product=item.product,
                    warehouse=self.warehouse,
                    defaults={"quantity": 0, "reorder_level": 0},
                )
                inventory.quantity += item.quantity
                inventory.save(update_fields=["quantity", "updated_at"])
            self.status = self.STATUS_RECEIVED
            self.received_at = timezone.now()
            self.save(update_fields=["status", "received_at", "updated_at"])

    def __str__(self) -> str:
        return f"PO #{self.pk}"


class PurchaseOrderItem(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="purchase_order_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    def save(self, *args, **kwargs):
        self.unit_cost = to_money(self.unit_cost)
        self.full_clean()
        result = super().save(*args, **kwargs)
        self.purchase_order.recalculate_total()
        return result

    def delete(self, *args, **kwargs):
        po = self.purchase_order
        result = super().delete(*args, **kwargs)
        po.recalculate_total()
        return result

    @property
    def total_cost(self) -> Decimal:
        return to_money(self.quantity * self.unit_cost)

    def __str__(self) -> str:
        return f"POItem({self.product}, {self.quantity})"


class SalesOrder(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FULFILLED = "fulfilled"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_FULFILLED, "Fulfilled"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sales_orders", on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, related_name="sales_orders", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]

    def recalculate_total(self) -> Decimal:
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("unit_price"), output_field=models.DecimalField(max_digits=14, decimal_places=2))
        )["total"]
        self.total_amount = to_money(total or Decimal("0.00"))
        self.save(update_fields=["total_amount", "updated_at"])
        return self.total_amount

    def fulfill(self) -> None:
        if self.status == self.STATUS_FULFILLED:
            raise ValidationError("Sales order already fulfilled.")
        if self.status == self.STATUS_CANCELLED:
            raise ValidationError("Cancelled sales order cannot be fulfilled.")
        with transaction.atomic():
            for item in self.items.select_related("product"):
                inventory = Inventory.objects.select_for_update().filter(
                    product=item.product,
                    warehouse=self.warehouse,
                ).first()
                if not inventory or inventory.quantity < item.quantity:
                    raise ValidationError(f"Insufficient inventory for {item.product.name}.")
                inventory.quantity -= item.quantity
                inventory.save(update_fields=["quantity", "updated_at"])
            self.status = self.STATUS_FULFILLED
            self.save(update_fields=["status", "updated_at"])

    def __str__(self) -> str:
        return f"SO #{self.pk}"


class SalesOrderItem(TimeStampedModel):
    sales_order = models.ForeignKey(SalesOrder, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="sales_order_items", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    def save(self, *args, **kwargs):
        self.unit_price = to_money(self.unit_price)
        self.full_clean()
        result = super().save(*args, **kwargs)
        self.sales_order.recalculate_total()
        return result

    def delete(self, *args, **kwargs):
        so = self.sales_order
        result = super().delete(*args, **kwargs)
        so.recalculate_total()
        return result

    @property
    def total_price(self) -> Decimal:
        return to_money(self.quantity * self.unit_price)

    def __str__(self) -> str:
        return f"SOItem({self.product}, {self.quantity})"


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def search(self, query: Optional[str]):
        if not query:
            return self
        return self.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
        ).distinct()


class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def search(self, query: Optional[str]):
        return self.get_queryset().search(query)


Product.add_to_class("objects", ProductManager())