import django
from django.conf import settings
from decimal import Decimal
from typing import Optional

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        USE_TZ=True,
    )
    django.setup()

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email: str, password: Optional[str] = None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: Optional[str] = None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_customer', False)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    is_admin = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)
    is_supplier = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        app_label = 'contenttypes'

class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        app_label = 'contenttypes'

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()

    class Meta:
        app_label = 'contenttypes'

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    class Meta:
        app_label = 'contenttypes'

class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='products')

    class Meta:
        app_label = 'contenttypes'

    @classmethod
    def search(cls, query: str):
        return cls.objects.filter(models.Q(title__icontains=query) | models.Q(description__icontains=query))

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_records')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_records')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'contenttypes'
        unique_together = ('product', 'warehouse')

    @classmethod
    def get_total_stock(cls, product: Product) -> int:
        return cls.objects.filter(product=product).aggregate(total=models.Sum('quantity'))['total'] or 0

    @classmethod
    def add_stock(cls, product: Product, warehouse: Warehouse, quantity: int):
        inventory, created = cls.objects.get_or_create(product=product, warehouse=warehouse)
        inventory.quantity += quantity
        inventory.save()
        return inventory

    @classmethod
    def remove_stock(cls, product: Product, quantity: int):
        records = cls.objects.filter(product=product, quantity__gt=0).order_by('-quantity')
        remaining_to_remove = quantity
        
        total_stock = cls.get_total_stock(product)
        if total_stock < quantity:
            raise ValueError("Insufficient stock")

        for record in records:
            if remaining_to_remove == 0:
                break
            if record.quantity >= remaining_to_remove:
                record.quantity -= remaining_to_remove
                record.save()
                remaining_to_remove = 0
            else:
                remaining_to_remove -= record.quantity
                record.quantity = 0
                record.save()

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')

    class Meta:
        app_label = 'contenttypes'

    def add_item(self, product: Product, quantity: int = 1):
        item, created = CartItem.objects.get_or_create(cart=self, product=product)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

    def remove_item(self, product: Product):
        CartItem.objects.filter(cart=self, product=product).delete()

    def clear(self):
        self.items.all().delete()

    def get_total(self) -> Decimal:
        return sum((item.product.price * item.quantity for item in self.items.all()), Decimal('0.00'))

    def checkout(self):
        items = self.items.all()
        if not items:
            raise ValueError("Cart is empty")

        for item in items:
            if Inventory.get_total_stock(item.product) < item.quantity:
                raise ValueError(f"Insufficient stock for {item.product.title}")

        order = SalesOrder.objects.create(customer=self.user, total_amount=self.get_total())
        
        for item in items:
            SalesOrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price
            )
            Inventory.remove_stock(item.product, item.quantity)

        self.clear()
        return order

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        app_label = 'contenttypes'

class SalesOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled')
    ]
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'contenttypes'

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        app_label = 'contenttypes'

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled')
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'contenttypes'

    def receive_order(self):
        if self.status == 'RECEIVED':
            raise ValueError("Order already received")
        
        for item in self.items.all():
            Inventory.add_stock(item.product, self.warehouse, item.quantity)
        
        self.status = 'RECEIVED'
        self.save()

class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        app_label = 'contenttypes'

class AuthService:
    @staticmethod
    def sign_up(email: str, password: str, is_customer: bool = True, is_supplier: bool = False, is_admin: bool = False) -> User:
        if User.objects.filter(email=email).exists():
            raise ValueError("User already exists")
        user = User.objects.create_user(
            email=email, 
            password=password, 
            is_customer=is_customer, 
            is_supplier=is_supplier, 
            is_admin=is_admin
        )
        if is_customer:
            Cart.objects.create(user=user)
        return user

    @staticmethod
    def login(email: str, password: str) -> Optional[User]:
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        return None

    @staticmethod
    def logout(user_token_or_session: str):
        pass

if __name__ == '__main__':
    from django.db import connection
    
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(User)
        schema_editor.create_model(Category)
        schema_editor.create_model(Supplier)
        schema_editor.create_model(Warehouse)
        schema_editor.create_model(Product)
        schema_editor.create_model(Inventory)
        schema_editor.create_model(Cart)
        schema_editor.create_model(CartItem)
        schema_editor.create_model(SalesOrder)
        schema_editor.create_model(SalesOrderItem)
        schema_editor.create_model(PurchaseOrder)
        schema_editor.create_model(PurchaseOrderItem)

    admin = AuthService.sign_up("admin@amazon.com", "adminpass", is_admin=True)
    customer = AuthService.sign_up("customer@amazon.com", "custpass")
    
    electronics = Category.objects.create(name="Electronics")
    laptops = Category.objects.create(name="Laptops", parent=electronics)
    
    supplier = Supplier.objects.create(name="Tech Supplier Inc", email="supplier@tech.com")
    warehouse = Warehouse.objects.create(name="Main Warehouse", location="Seattle, WA")
    
    laptop = Product.objects.create(
        title="Pro Laptop",
        description="High performance laptop",
        price=Decimal('1200.00'),
        category=laptops,
        supplier=supplier
    )
    
    po = PurchaseOrder.objects.create(supplier=supplier, warehouse=warehouse)
    PurchaseOrderItem.objects.create(order=po, product=laptop, quantity=100, cost_price=Decimal('900.00'))
    po.receive_order()
    
    cart = customer.cart
    cart.add_item(laptop, quantity=2)
    sales_order = cart.checkout()
    
    assert Inventory.get_total_stock(laptop) == 98
    assert sales_order.total_amount == Decimal('2400.00')
    assert SalesOrder.objects.count() == 1
    assert len(Product.search("Pro")) == 1
    
    print("Amazon Clone System successfully initialized and tested.")