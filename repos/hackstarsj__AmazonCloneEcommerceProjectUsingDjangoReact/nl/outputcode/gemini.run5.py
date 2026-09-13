import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class AuthenticationError(Exception):
    pass

class UnauthorizedError(Exception):
    pass

class OutOfStockError(Exception):
    pass

class ItemNotFoundError(Exception):
    pass

class User:
    def __init__(self, user_id: str, username: str, password_hash: str, email: str, is_admin: bool = False):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.is_admin = is_admin
        self.is_logged_in = False

    def verify_password(self, password: str) -> bool:
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

class Category:
    def __init__(self, category_id: str, name: str, parent: Optional['Category'] = None):
        self.category_id = category_id
        self.name = name
        self.parent = parent
        self.subcategories: List['Category'] = []
        if parent:
            parent.subcategories.append(self)

    def get_full_path(self) -> str:
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

class Product:
    def __init__(self, product_id: str, name: str, description: str, price: float, category: Category):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.category = category

class Supplier:
    def __init__(self, supplier_id: str, name: str, contact_email: str):
        self.supplier_id = supplier_id
        self.name = name
        self.contact_email = contact_email

class Warehouse:
    def __init__(self, warehouse_id: str, location: str, capacity: int):
        self.warehouse_id = warehouse_id
        self.location = location
        self.capacity = capacity

class ShoppingCart:
    def __init__(self, user: User):
        self.user = user
        self.items: Dict[Product, int] = {}

    def add_item(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if product in self.items:
            self.items[product] += quantity
        else:
            self.items[product] = quantity

    def remove_item(self, product: Product, quantity: Optional[int] = None) -> None:
        if product not in self.items:
            raise ItemNotFoundError("Product not in cart")
        
        if quantity is None or self.items[product] <= quantity:
            del self.items[product]
        else:
            self.items[product] -= quantity

    def get_total(self) -> float:
        return sum(product.price * qty for product, qty in self.items.items())

    def clear(self) -> None:
        self.items.clear()

class SalesOrder:
    def __init__(self, order_id: str, user: User, items: Dict[Product, int]):
        self.order_id = order_id
        self.user = user
        self.items = items.copy()
        self.total_amount = sum(p.price * q for p, q in self.items.items())
        self.status = "PENDING"
        self.created_at = datetime.now()

    def update_status(self, new_status: str) -> None:
        self.status = new_status

class PurchaseOrder:
    def __init__(self, po_id: str, supplier: Supplier, items: Dict[Product, int]):
        self.po_id = po_id
        self.supplier = supplier
        self.items = items.copy()
        self.total_amount = sum(p.price * q for p, q in self.items.items())
        self.status = "PENDING"
        self.created_at = datetime.now()

    def mark_received(self) -> None:
        self.status = "RECEIVED"

class UserManager:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.current_user: Optional[User] = None
        self._user_counter = 1

    def sign_up(self, username: str, password: str, email: str, is_admin: bool = False) -> User:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username already exists")
        
        user_id = f"U{self._user_counter:04d}"
        self._user_counter += 1
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        new_user = User(user_id, username, password_hash, email, is_admin)
        self.users[user_id] = new_user
        return new_user

    def login(self, username: str, password: str) -> User:
        for user in self.users.values():
            if user.username == username:
                if user.verify_password(password):
                    user.is_logged_in = True
                    self.current_user = user
                    return user
                else:
                    raise AuthenticationError("Invalid password")
        raise AuthenticationError("User not found")

    def logout(self) -> None:
        if self.current_user:
            self.current_user.is_logged_in = False
            self.current_user = None

    def get_current_user(self) -> Optional[User]:
        return self.current_user

class ProductManager:
    def __init__(self):
        self.products: Dict[str, Product] = {}
        self.categories: Dict[str, Category] = {}
        self._product_counter = 1
        self._category_counter = 1

    def create_category(self, name: str, parent_id: Optional[str] = None) -> Category:
        cat_id = f"C{self._category_counter:04d}"
        self._category_counter += 1
        parent = self.categories.get(parent_id) if parent_id else None
        category = Category(cat_id, name, parent)
        self.categories[cat_id] = category
        return category

    def add_product(self, name: str, description: str, price: float, category_id: str) -> Product:
        if category_id not in self.categories:
            raise ItemNotFoundError("Category not found")
        
        prod_id = f"P{self._product_counter:04d}"
        self._product_counter += 1
        product = Product(prod_id, name, description, price, self.categories[category_id])
        self.products[prod_id] = product
        return product

    def search_products(self, query: str) -> List[Product]:
        query = query.lower()
        return [
            p for p in self.products.values()
            if query in p.name.lower() or query in p.description.lower() or query in p.category.name.lower()
        ]

    def get_product_detail(self, product_id: str) -> Product:
        if product_id not in self.products:
            raise ItemNotFoundError("Product not found")
        return self.products[product_id]

class InventoryManager:
    def __init__(self):
        self.warehouses: Dict[str, Warehouse] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.stock: Dict[str, Dict[str, int]] = {} 
        self._warehouse_counter = 1
        self._supplier_counter = 1

    def add_warehouse(self, location: str, capacity: int) -> Warehouse:
        w_id = f"W{self._warehouse_counter:04d}"
        self._warehouse_counter += 1
        warehouse = Warehouse(w_id, location, capacity)
        self.warehouses[w_id] = warehouse
        return warehouse

    def add_supplier(self, name: str, contact_email: str) -> Supplier:
        s_id = f"S{self._supplier_counter:04d}"
        self._supplier_counter += 1
        supplier = Supplier(s_id, name, contact_email)
        self.suppliers[s_id] = supplier
        return supplier

    def add_stock(self, product_id: str, warehouse_id: str, quantity: int) -> None:
        if warehouse_id not in self.warehouses:
            raise ItemNotFoundError("Warehouse not found")
        
        if product_id not in self.stock:
            self.stock[product_id] = {}
            
        current_stock = self.stock[product_id].get(warehouse_id, 0)
        self.stock[product_id][warehouse_id] = current_stock + quantity

    def remove_stock(self, product_id: str, quantity: int) -> None:
        total_available = self.get_total_stock(product_id)
        if total_available < quantity:
            raise OutOfStockError(f"Insufficient stock for product {product_id}")

        remaining_to_remove = quantity
        if product_id in self.stock:
            for w_id in list(self.stock[product_id].keys()):
                w_stock = self.stock[product_id][w_id]
                if w_stock >= remaining_to_remove:
                    self.stock[product_id][w_id] -= remaining_to_remove
                    remaining_to_remove = 0
                    break
                else:
                    remaining_to_remove -= w_stock
                    self.stock[product_id][w_id] = 0

    def get_total_stock(self, product_id: str) -> int:
        if product_id not in self.stock:
            return 0
        return sum(self.stock[product_id].values())

class OrderManager:
    def __init__(self, inventory_manager: InventoryManager):
        self.inventory_manager = inventory_manager
        self.sales_orders: Dict[str, SalesOrder] = {}
        self.purchase_orders: Dict[str, PurchaseOrder] = {}
        self._so_counter = 1
        self._po_counter = 1

    def create_sales_order(self, user: User, cart: ShoppingCart) -> SalesOrder:
        if not cart.items:
            raise ValueError("Cart is empty")

        for product, quantity in cart.items.items():
            if self.inventory_manager.get_total_stock(product.product_id) < quantity:
                raise OutOfStockError(f"Product {product.name} is out of stock")

        for product, quantity in cart.items.items():
            self.inventory_manager.remove_stock(product.product_id, quantity)

        so_id = f"SO{self._so_counter:04d}"
        self._so_counter += 1
        order = SalesOrder(so_id, user, cart.items)
        self.sales_orders[so_id] = order
        cart.clear()
        return order

    def create_purchase_order(self, supplier: Supplier, items: Dict[Product, int]) -> PurchaseOrder:
        po_id = f"PO{self._po_counter:04d}"
        self._po_counter += 1
        po = PurchaseOrder(po_id, supplier, items)
        self.purchase_orders[po_id] = po
        return po

    def receive_purchase_order(self, po_id: str, warehouse_id: str) -> None:
        if po_id not in self.purchase_orders:
            raise ItemNotFoundError("Purchase order not found")
        
        po = self.purchase_orders[po_id]
        if po.status == "RECEIVED":
            raise ValueError("Purchase order already received")

        for product, quantity in po.items.items():
            self.inventory_manager.add_stock(product.product_id, warehouse_id, quantity)
        
        po.mark_received()

class AmazonClone:
    def __init__(self):
        self.user_manager = UserManager()
        self.product_manager = ProductManager()
        self.inventory_manager = InventoryManager()
        self.order_manager = OrderManager(self.inventory_manager)
        self.carts: Dict[str, ShoppingCart] = {}

    def _require_admin(self) -> None:
        user = self.user_manager.get_current_user()
        if not user or not user.is_admin:
            raise UnauthorizedError("Admin privileges required")

    def _require_login(self) -> User:
        user = self.user_manager.get_current_user()
        if not user:
            raise UnauthorizedError("Must be logged in")
        return user

    def get_cart(self) -> ShoppingCart:
        user = self._require_login()
        if user.user_id not in self.carts:
            self.carts[user.user_id] = ShoppingCart(user)
        return self.carts[user.user_id]

    def setup_catalog(self) -> None:
        self._require_admin()
        electronics = self.product_manager.create_category("Electronics")
        laptops = self.product_manager.create_category("Laptops", electronics.category_id)
        
        self.product_manager.add_product("MacBook Pro", "Apple Laptop", 1999.99, laptops.category_id)
        self.product_manager.add_product("Dell XPS", "Windows Laptop", 1499.99, laptops.category_id)

        w1 = self.inventory_manager.add_warehouse("New York", 1000)
        s1 = self.inventory_manager.add_supplier("TechDistributor Inc", "supply@tech.com")
        
        return w1, s1

if __name__ == "__main__":
    system = AmazonClone()

    admin = system.user_manager.sign_up("admin", "adminpass", "admin@amazon.com", is_admin=True)
    customer = system.user_manager.sign_up("john_doe", "password123", "john@example.com", is_admin=False)

    system.user_manager.login("admin", "adminpass")
    warehouse, supplier = system.setup_catalog()
    
    macbook = system.product_manager.search_products("MacBook")[0]
    dell = system.product_manager.search_products("Dell")[0]

    po_items = {macbook: 50, dell: 30}
    po = system.order_manager.create_purchase_order(supplier, po_items)
    system.order_manager.receive_purchase_order(po.po_id, warehouse.warehouse_id)
    
    system.user_manager.logout()

    system.user_manager.login("john_doe", "password123")
    
    search_results = system.product_manager.search_products("Laptop")
    
    cart = system.get_cart()
    cart.add_item(search_results[0], 2) 
    cart.add_item(search_results[1], 1) 
    
    sales_order = system.order_manager.create_sales_order(system.user_manager.get_current_user(), cart)
    
    system.user_manager.logout()