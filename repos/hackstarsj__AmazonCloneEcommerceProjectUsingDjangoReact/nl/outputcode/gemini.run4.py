import uuid
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field

class AmazonException(Exception):
    pass

class AuthenticationError(AmazonException):
    pass

class NotFoundError(AmazonException):
    pass

class InsufficientStockError(AmazonException):
    pass

@dataclass
class User:
    username: str
    password: str
    email: str
    is_admin: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Category:
    name: str
    parent_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

@dataclass
class Product:
    name: str
    description: str
    price: float
    category_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

@dataclass
class Supplier:
    name: str
    contact_email: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

@dataclass
class Warehouse:
    name: str
    location: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

@dataclass
class InventoryRecord:
    product_id: str
    warehouse_id: str
    quantity: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

@dataclass
class CartItem:
    product_id: str
    quantity: int

@dataclass
class Cart:
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)

@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: float

@dataclass
class SalesOrder:
    user_id: str
    items: List[OrderItem]
    total_amount: float
    status: str = "PENDING"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class PurchaseOrder:
    supplier_id: str
    warehouse_id: str
    items: List[OrderItem]
    total_amount: float
    status: str = "PENDING"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)

class Database:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.categories: Dict[str, Category] = {}
        self.products: Dict[str, Product] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.warehouses: Dict[str, Warehouse] = {}
        self.inventory: List[InventoryRecord] = []
        self.carts: Dict[str, Cart] = {}
        self.sales_orders: Dict[str, SalesOrder] = {}
        self.purchase_orders: Dict[str, PurchaseOrder] = {}
        self.logged_in_users: set = set()

class AuthManager:
    def __init__(self, db: Database):
        self.db = db

    def sign_up(self, username: str, password: str, email: str, is_admin: bool = False) -> User:
        for user in self.db.users.values():
            if user.username == username:
                raise AuthenticationError("Username already exists.")
            if user.email == email:
                raise AuthenticationError("Email already registered.")
        
        new_user = User(username=username, password=password, email=email, is_admin=is_admin)
        self.db.users[new_user.id] = new_user
        self.db.carts[new_user.id] = Cart(user_id=new_user.id)
        return new_user

    def login(self, username: str, password: str) -> User:
        for user in self.db.users.values():
            if user.username == username and user.password == password:
                self.db.logged_in_users.add(user.id)
                return user
        raise AuthenticationError("Invalid username or password.")

    def logout(self, user_id: str) -> None:
        if user_id in self.db.logged_in_users:
            self.db.logged_in_users.remove(user_id)

    def get_user(self, user_id: str) -> User:
        if user_id not in self.db.users:
            raise NotFoundError("User not found.")
        return self.db.users[user_id]

class CatalogManager:
    def __init__(self, db: Database):
        self.db = db

    def create_category(self, name: str, parent_id: Optional[str] = None) -> Category:
        if parent_id and parent_id not in self.db.categories:
            raise NotFoundError("Parent category not found.")
        category = Category(name=name, parent_id=parent_id)
        self.db.categories[category.id] = category
        return category

    def create_product(self, name: str, description: str, price: float, category_id: str) -> Product:
        if category_id not in self.db.categories:
            raise NotFoundError("Category not found.")
        product = Product(name=name, description=description, price=price, category_id=category_id)
        self.db.products[product.id] = product
        return product

    def get_product(self, product_id: str) -> Product:
        if product_id not in self.db.products:
            raise NotFoundError("Product not found.")
        return self.db.products[product_id]

    def search_products(self, query: str) -> List[Product]:
        query = query.lower()
        return [
            p for p in self.db.products.values()
            if query in p.name.lower() or query in p.description.lower()
        ]

class InventoryManager:
    def __init__(self, db: Database):
        self.db = db

    def add_warehouse(self, name: str, location: str) -> Warehouse:
        warehouse = Warehouse(name=name, location=location)
        self.db.warehouses[warehouse.id] = warehouse
        return warehouse

    def add_supplier(self, name: str, contact_email: str) -> Supplier:
        supplier = Supplier(name=name, contact_email=contact_email)
        self.db.suppliers[supplier.id] = supplier
        return supplier

    def get_stock_level(self, product_id: str) -> int:
        return sum(record.quantity for record in self.db.inventory if record.product_id == product_id)

    def add_stock(self, product_id: str, warehouse_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        for record in self.db.inventory:
            if record.product_id == product_id and record.warehouse_id == warehouse_id:
                record.quantity += quantity
                return
        
        new_record = InventoryRecord(product_id=product_id, warehouse_id=warehouse_id, quantity=quantity)
        self.db.inventory.append(new_record)

    def remove_stock(self, product_id: str, quantity: int) -> None:
        if self.get_stock_level(product_id) < quantity:
            raise InsufficientStockError(f"Not enough stock for product {product_id}.")
        
        remaining_to_remove = quantity
        for record in self.db.inventory:
            if record.product_id == product_id and record.quantity > 0:
                if record.quantity >= remaining_to_remove:
                    record.quantity -= remaining_to_remove
                    remaining_to_remove = 0
                    break
                else:
                    remaining_to_remove -= record.quantity
                    record.quantity = 0

class CartManager:
    def __init__(self, db: Database, catalog: CatalogManager):
        self.db = db
        self.catalog = catalog

    def add_to_cart(self, user_id: str, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        self.catalog.get_product(product_id)
        cart = self.db.carts.get(user_id)
        if not cart:
            raise NotFoundError("Cart not found for user.")

        if product_id in cart.items:
            cart.items[product_id].quantity += quantity
        else:
            cart.items[product_id] = CartItem(product_id=product_id, quantity=quantity)

    def remove_from_cart(self, user_id: str, product_id: str) -> None:
        cart = self.db.carts.get(user_id)
        if cart and product_id in cart.items:
            del cart.items[product_id]

    def view_cart(self, user_id: str) -> Cart:
        cart = self.db.carts.get(user_id)
        if not cart:
            raise NotFoundError("Cart not found.")
        return cart

    def clear_cart(self, user_id: str) -> None:
        cart = self.db.carts.get(user_id)
        if cart:
            cart.items.clear()

class OrderManager:
    def __init__(self, db: Database, catalog: CatalogManager, inventory: InventoryManager, cart: CartManager):
        self.db = db
        self.catalog = catalog
        self.inventory = inventory
        self.cart = cart

    def checkout(self, user_id: str) -> SalesOrder:
        cart = self.cart.view_cart(user_id)
        if not cart.items:
            raise ValueError("Cart is empty.")

        for item in cart.items.values():
            if self.inventory.get_stock_level(item.product_id) < item.quantity:
                raise InsufficientStockError(f"Insufficient stock for product {item.product_id}")

        order_items = []
        total_amount = 0.0

        for item in cart.items.values():
            product = self.catalog.get_product(item.product_id)
            self.inventory.remove_stock(item.product_id, item.quantity)
            
            order_item = OrderItem(product_id=product.id, quantity=item.quantity, unit_price=product.price)
            order_items.append(order_item)
            total_amount += product.price * item.quantity

        sales_order = SalesOrder(user_id=user_id, items=order_items, total_amount=total_amount)
        self.db.sales_orders[sales_order.id] = sales_order
        self.cart.clear_cart(user_id)
        
        return sales_order

    def create_purchase_order(self, supplier_id: str, warehouse_id: str, items_data: List[Dict[str, float]]) -> PurchaseOrder:
        if supplier_id not in self.db.suppliers:
            raise NotFoundError("Supplier not found.")
        if warehouse_id not in self.db.warehouses:
            raise NotFoundError("Warehouse not found.")

        order_items = []
        total_amount = 0.0

        for data in items_data:
            product_id = data['product_id']
            quantity = int(data['quantity'])
            unit_price = float(data['unit_price'])
            
            self.catalog.get_product(product_id)
            order_items.append(OrderItem(product_id=product_id, quantity=quantity, unit_price=unit_price))
            total_amount += quantity * unit_price

        po = PurchaseOrder(
            supplier_id=supplier_id, 
            warehouse_id=warehouse_id, 
            items=order_items, 
            total_amount=total_amount
        )
        self.db.purchase_orders[po.id] = po
        return po

    def receive_purchase_order(self, po_id: str) -> None:
        po = self.db.purchase_orders.get(po_id)
        if not po:
            raise NotFoundError("Purchase order not found.")
        if po.status == "RECEIVED":
            raise ValueError("Purchase order already received.")

        for item in po.items:
            self.inventory.add_stock(item.product_id, po.warehouse_id, item.quantity)
        
        po.status = "RECEIVED"

class UserManagementService:
    def __init__(self, db: Database):
        self.db = db

    def list_all_users(self, admin_user_id: str) -> List[User]:
        admin = self.db.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise AuthenticationError("Unauthorized. Admin access required.")
        return list(self.db.users.values())

    def delete_user(self, admin_user_id: str, target_user_id: str) -> None:
        admin = self.db.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise AuthenticationError("Unauthorized. Admin access required.")
        if target_user_id in self.db.users:
            del self.db.users[target_user_id]
            if target_user_id in self.db.carts:
                del self.db.carts[target_user_id]

class AmazonCloneSystem:
    def __init__(self):
        self.db = Database()
        self.auth = AuthManager(self.db)
        self.catalog = CatalogManager(self.db)
        self.inventory = InventoryManager(self.db)
        self.cart = CartManager(self.db, self.catalog)
        self.orders = OrderManager(self.db, self.catalog, self.inventory, self.cart)
        self.user_management = UserManagementService(self.db)

if __name__ == "__main__":
    amazon = AmazonCloneSystem()
    
    admin = amazon.auth.sign_up("admin", "adminpass", "admin@amazon.com", is_admin=True)
    customer = amazon.auth.sign_up("john_doe", "password123", "john@example.com")
    
    amazon.auth.login("john_doe", "password123")
    
    electronics = amazon.catalog.create_category("Electronics")
    laptops = amazon.catalog.create_category("Laptops", parent_id=electronics.id)
    
    macbook = amazon.catalog.create_product("MacBook Pro", "Apple Laptop", 1999.99, laptops.id)
    
    supplier = amazon.inventory.add_supplier("Apple Inc", "sales@apple.com")
    warehouse = amazon.inventory.add_warehouse("NY Central", "New York, NY")
    
    po = amazon.orders.create_purchase_order(
        supplier.id, 
        warehouse.id, 
        [{"product_id": macbook.id, "quantity": 50, "unit_price": 1500.00}]
    )
    amazon.orders.receive_purchase_order(po.id)
    
    amazon.cart.add_to_cart(customer.id, macbook.id, 2)
    
    sales_order = amazon.orders.checkout(customer.id)
    
    amazon.auth.logout(customer.id)