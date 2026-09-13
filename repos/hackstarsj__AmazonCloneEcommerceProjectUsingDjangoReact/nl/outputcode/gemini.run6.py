import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

class Role(Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class POStatus(Enum):
    ISSUED = "ISSUED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"

class AuthException(Exception):
    pass

class InventoryException(Exception):
    pass

class NotFoundException(Exception):
    pass

@dataclass
class User:
    id: str
    username: str
    password: str
    email: str
    role: Role
    is_logged_in: bool = False

@dataclass
class Category:
    id: str
    name: str
    parent_id: Optional[str] = None

@dataclass
class Product:
    id: str
    name: str
    description: str
    price: float
    category_id: str

@dataclass
class Supplier:
    id: str
    name: str
    contact_email: str

@dataclass
class Warehouse:
    id: str
    name: str
    location: str

@dataclass
class InventoryItem:
    warehouse_id: str
    product_id: str
    quantity: int

@dataclass
class CartItem:
    product_id: str
    quantity: int

@dataclass
class Cart:
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)

@dataclass
class SalesOrderItem:
    product_id: str
    quantity: int
    price: float

@dataclass
class SalesOrder:
    id: str
    user_id: str
    items: List[SalesOrderItem]
    total_amount: float
    status: OrderStatus
    created_at: datetime

@dataclass
class PurchaseOrder:
    id: str
    supplier_id: str
    warehouse_id: str
    product_id: str
    quantity: int
    status: POStatus
    created_at: datetime

class Database:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.categories: Dict[str, Category] = {}
        self.products: Dict[str, Product] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.warehouses: Dict[str, Warehouse] = {}
        self.inventory: Dict[tuple, InventoryItem] = {} 
        self.carts: Dict[str, Cart] = {}
        self.sales_orders: Dict[str, SalesOrder] = {}
        self.purchase_orders: Dict[str, PurchaseOrder] = {}

class UserService:
    def __init__(self, db: Database):
        self.db = db

    def sign_up(self, username: str, password: str, email: str, role: Role = Role.CUSTOMER) -> User:
        for user in self.db.users.values():
            if user.username == username:
                raise AuthException("Username already exists")
            if user.email == email:
                raise AuthException("Email already exists")
        
        user_id = str(uuid.uuid4())
        new_user = User(id=user_id, username=username, password=password, email=email, role=role)
        self.db.users[user_id] = new_user
        self.db.carts[user_id] = Cart(user_id=user_id)
        return new_user

    def login(self, username: str, password: str) -> User:
        for user in self.db.users.values():
            if user.username == username and user.password == password:
                user.is_logged_in = True
                return user
        raise AuthException("Invalid credentials")

    def logout(self, user_id: str):
        user = self.db.users.get(user_id)
        if user:
            user.is_logged_in = False

    def get_all_users(self, admin_id: str) -> List[User]:
        admin = self.db.users.get(admin_id)
        if not admin or admin.role != Role.ADMIN:
            raise AuthException("Unauthorized: Admin access required")
        return list(self.db.users.values())

    def update_user_role(self, admin_id: str, target_user_id: str, new_role: Role):
        admin = self.db.users.get(admin_id)
        if not admin or admin.role != Role.ADMIN:
            raise AuthException("Unauthorized: Admin access required")
        target_user = self.db.users.get(target_user_id)
        if not target_user:
            raise NotFoundException("User not found")
        target_user.role = new_role

class CatalogService:
    def __init__(self, db: Database):
        self.db = db

    def create_category(self, name: str, parent_id: Optional[str] = None) -> Category:
        if parent_id and parent_id not in self.db.categories:
            raise NotFoundException("Parent category not found")
        cat_id = str(uuid.uuid4())
        category = Category(id=cat_id, name=name, parent_id=parent_id)
        self.db.categories[cat_id] = category
        return category

    def create_product(self, name: str, description: str, price: float, category_id: str) -> Product:
        if category_id not in self.db.categories:
            raise NotFoundException("Category not found")
        prod_id = str(uuid.uuid4())
        product = Product(id=prod_id, name=name, description=description, price=price, category_id=category_id)
        self.db.products[prod_id] = product
        return product

    def list_products(self) -> List[Product]:
        return list(self.db.products.values())

    def search_products(self, query: str) -> List[Product]:
        query = query.lower()
        return [p for p in self.db.products.values() if query in p.name.lower() or query in p.description.lower()]

    def get_product_detail(self, product_id: str) -> Product:
        product = self.db.products.get(product_id)
        if not product:
            raise NotFoundException("Product not found")
        return product

    def _get_subcategory_ids(self, category_id: str) -> List[str]:
        sub_ids = []
        for cat in self.db.categories.values():
            if cat.parent_id == category_id:
                sub_ids.append(cat.id)
                sub_ids.extend(self._get_subcategory_ids(cat.id))
        return sub_ids

    def get_products_by_category(self, category_id: str) -> List[Product]:
        if category_id not in self.db.categories:
            raise NotFoundException("Category not found")
        valid_category_ids = [category_id] + self._get_subcategory_ids(category_id)
        return [p for p in self.db.products.values() if p.category_id in valid_category_ids]

class InventoryService:
    def __init__(self, db: Database):
        self.db = db

    def add_supplier(self, name: str, contact_email: str) -> Supplier:
        sup_id = str(uuid.uuid4())
        supplier = Supplier(id=sup_id, name=name, contact_email=contact_email)
        self.db.suppliers[sup_id] = supplier
        return supplier

    def add_warehouse(self, name: str, location: str) -> Warehouse:
        wh_id = str(uuid.uuid4())
        warehouse = Warehouse(id=wh_id, name=name, location=location)
        self.db.warehouses[wh_id] = warehouse
        return warehouse

    def get_stock(self, product_id: str) -> int:
        return sum(item.quantity for key, item in self.db.inventory.items() if key[1] == product_id)

    def add_stock(self, warehouse_id: str, product_id: str, quantity: int):
        if warehouse_id not in self.db.warehouses:
            raise NotFoundException("Warehouse not found")
        if product_id not in self.db.products:
            raise NotFoundException("Product not found")
        
        key = (warehouse_id, product_id)
        if key in self.db.inventory:
            self.db.inventory[key].quantity += quantity
        else:
            self.db.inventory[key] = InventoryItem(warehouse_id=warehouse_id, product_id=product_id, quantity=quantity)

    def remove_stock(self, product_id: str, quantity: int):
        total_stock = self.get_stock(product_id)
        if total_stock < quantity:
            raise InventoryException(f"Insufficient stock for product {product_id}")

        remaining = quantity
        for key, item in self.db.inventory.items():
            if item.product_id == product_id and item.quantity > 0:
                if item.quantity >= remaining:
                    item.quantity -= remaining
                    remaining = 0
                    break
                else:
                    remaining -= item.quantity
                    item.quantity = 0

        if remaining > 0:
            raise InventoryException("Failed to remove stock completely due to concurrency or data inconsistency")

class OrderService:
    def __init__(self, db: Database, inventory_service: InventoryService):
        self.db = db
        self.inventory_service = inventory_service

    def create_purchase_order(self, admin_id: str, supplier_id: str, warehouse_id: str, product_id: str, quantity: int) -> PurchaseOrder:
        admin = self.db.users.get(admin_id)
        if not admin or admin.role != Role.ADMIN:
            raise AuthException("Only admins can create purchase orders")
        if supplier_id not in self.db.suppliers:
            raise NotFoundException("Supplier not found")
        if warehouse_id not in self.db.warehouses:
            raise NotFoundException("Warehouse not found")
        if product_id not in self.db.products:
            raise NotFoundException("Product not found")

        po_id = str(uuid.uuid4())
        po = PurchaseOrder(
            id=po_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity=quantity,
            status=POStatus.ISSUED,
            created_at=datetime.now()
        )
        self.db.purchase_orders[po_id] = po
        return po

    def receive_purchase_order(self, admin_id: str, po_id: str):
        admin = self.db.users.get(admin_id)
        if not admin or admin.role != Role.ADMIN:
            raise AuthException("Only admins can receive purchase orders")

        po = self.db.purchase_orders.get(po_id)
        if not po:
            raise NotFoundException("Purchase order not found")
        if po.status != POStatus.ISSUED:
            raise ValueError("Purchase order already processed or cancelled")

        po.status = POStatus.RECEIVED
        self.inventory_service.add_stock(po.warehouse_id, po.product_id, po.quantity)

    def create_sales_order(self, user_id: str, items: List[SalesOrderItem], total_amount: float) -> SalesOrder:
        order_id = str(uuid.uuid4())
        order = SalesOrder(
            id=order_id,
            user_id=user_id,
            items=items,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            created_at=datetime.now()
        )
        self.db.sales_orders[order_id] = order
        return order

    def update_sales_order_status(self, admin_id: str, order_id: str, status: OrderStatus):
        admin = self.db.users.get(admin_id)
        if not admin or admin.role != Role.ADMIN:
            raise AuthException("Only admins can update order status")
        order = self.db.sales_orders.get(order_id)
        if not order:
            raise NotFoundException("Sales order not found")
        order.status = status

    def get_user_orders(self, user_id: str) -> List[SalesOrder]:
        return [order for order in self.db.sales_orders.values() if order.user_id == user_id]

class CartService:
    def __init__(self, db: Database, catalog_service: CatalogService, inventory_service: InventoryService, order_service: OrderService):
        self.db = db
        self.catalog_service = catalog_service
        self.inventory_service = inventory_service
        self.order_service = order_service

    def add_to_cart(self, user_id: str, product_id: str, quantity: int):
        cart = self.db.carts.get(user_id)
        if not cart:
            raise NotFoundException("Cart not found")
        product = self.catalog_service.get_product_detail(product_id)
        
        if product_id in cart.items:
            cart.items[product_id].quantity += quantity
        else:
            cart.items[product_id] = CartItem(product_id=product_id, quantity=quantity)

    def remove_from_cart(self, user_id: str, product_id: str):
        cart = self.db.carts.get(user_id)
        if not cart:
            raise NotFoundException("Cart not found")
        if product_id in cart.items:
            del cart.items[product_id]

    def view_cart(self, user_id: str) -> Dict[str, Any]:
        cart = self.db.carts.get(user_id)
        if not cart:
            raise NotFoundException("Cart not found")
        
        total = 0.0
        items_detail = []
        for item in cart.items.values():
            product = self.catalog_service.get_product_detail(item.product_id)
            subtotal = product.price * item.quantity
            total += subtotal
            items_detail.append({
                "product_name": product.name,
                "quantity": item.quantity,
                "price": product.price,
                "subtotal": subtotal
            })
        
        return {
            "items": items_detail,
            "total_amount": total
        }

    def checkout(self, user_id: str) -> SalesOrder:
        cart = self.db.carts.get(user_id)
        if not cart or not cart.items:
            raise ValueError("Cart is empty")

        total_amount = 0.0
        sales_items = []

        for product_id, cart_item in cart.items.items():
            product = self.catalog_service.get_product_detail(product_id)
            if self.inventory_service.get_stock(product_id) < cart_item.quantity:
                raise InventoryException(f"Insufficient stock for {product.name}")
            
            price = product.price
            total_amount += price * cart_item.quantity
            sales_items.append(SalesOrderItem(product_id=product_id, quantity=cart_item.quantity, price=price))

        for item in sales_items:
            self.inventory_service.remove_stock(item.product_id, item.quantity)

        order = self.order_service.create_sales_order(user_id, sales_items, total_amount)
        cart.items.clear()
        return order

class AmazonCloneSystem:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService(self.db)
        self.catalog_service = CatalogService(self.db)
        self.inventory_service = InventoryService(self.db)
        self.order_service = OrderService(self.db, self.inventory_service)
        self.cart_service = CartService(self.db, self.catalog_service, self.inventory_service, self.order_service)

if __name__ == "__main__":
    system = AmazonCloneSystem()

    admin = system.user_service.sign_up("admin", "adminpass", "admin@amazon.com", Role.ADMIN)
    system.user_service.login("admin", "adminpass")

    electronics = system.catalog_service.create_category("Electronics")
    laptops = system.catalog_service.create_category("Laptops", parent_id=electronics.id)

    macbook = system.catalog_service.create_product("MacBook Pro", "Apple M2 Laptop", 1999.99, laptops.id)
    mouse = system.catalog_service.create_product("Logitech Mouse", "Wireless Mouse", 49.99, electronics.id)

    supplier = system.inventory_service.add_supplier("Apple Inc", "supply@apple.com")
    warehouse = system.inventory_service.add_warehouse("NY Central", "New York, NY")

    po = system.order_service.create_purchase_order(admin.id, supplier.id, warehouse.id, macbook.id, 50)
    system.order_service.receive_purchase_order(admin.id, po.id)
    
    po2 = system.order_service.create_purchase_order(admin.id, supplier.id, warehouse.id, mouse.id, 100)
    system.order_service.receive_purchase_order(admin.id, po2.id)

    customer = system.user_service.sign_up("john_doe", "password123", "john@example.com", Role.CUSTOMER)
    system.user_service.login("john_doe", "password123")

    search_results = system.catalog_service.search_products("macbook")
    
    system.cart_service.add_to_cart(customer.id, macbook.id, 1)
    system.cart_service.add_to_cart(customer.id, mouse.id, 2)
    
    cart_view = system.cart_service.view_cart(customer.id)
    
    sales_order = system.cart_service.checkout(customer.id)
    
    system.order_service.update_sales_order_status(admin.id, sales_order.id, OrderStatus.SHIPPED)
    
    system.user_service.logout(customer.id)
    system.user_service.logout(admin.id)