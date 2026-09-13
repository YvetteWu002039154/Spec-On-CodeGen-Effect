import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

class UnauthorizedError(Exception):
    pass

class OutOfStockError(Exception):
    pass

class EntityNotFoundError(Exception):
    pass

class Category:
    def __init__(self, name: str, parent: Optional['Category'] = None):
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._parent: Optional['Category'] = parent
        self._subcategories: List['Category'] = []
        if parent:
            parent.add_subcategory(self)

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent(self) -> Optional['Category']:
        return self._parent

    def add_subcategory(self, category: 'Category') -> None:
        if category not in self._subcategories:
            self._subcategories.append(category)

    def get_all_subcategories(self) -> List['Category']:
        return self._subcategories.copy()

class Supplier:
    def __init__(self, name: str, contact_info: str):
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._contact_info: str = contact_info

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

class Warehouse:
    def __init__(self, name: str, location: str):
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._location: str = location

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

class Product:
    def __init__(self, name: str, description: str, price: float, category: Category, supplier: Supplier):
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._description: str = description
        self._price: float = price
        self._category: Category = category
        self._supplier: Supplier = supplier

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def price(self) -> float:
        return self._price

    @property
    def category(self) -> Category:
        return self._category

    @property
    def supplier(self) -> Supplier:
        return self._supplier

class InventoryManager:
    def __init__(self):
        self._stock: Dict[str, Dict[str, int]] = {}

    def add_stock(self, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if product.id not in self._stock:
            self._stock[product.id] = {}
        if warehouse.id not in self._stock[product.id]:
            self._stock[product.id][warehouse.id] = 0
        self._stock[product.id][warehouse.id] += quantity

    def get_total_stock(self, product: Product) -> int:
        if product.id not in self._stock:
            return 0
        return sum(self._stock[product.id].values())

    def remove_stock(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        total_stock = self.get_total_stock(product)
        if total_stock < quantity:
            raise OutOfStockError(f"Insufficient stock for product {product.name}")
        
        remaining_to_remove = quantity
        for w_id, qty in self._stock[product.id].items():
            if remaining_to_remove == 0:
                break
            if qty >= remaining_to_remove:
                self._stock[product.id][w_id] -= remaining_to_remove
                remaining_to_remove = 0
            else:
                remaining_to_remove -= qty
                self._stock[product.id][w_id] = 0

class CartItem:
    def __init__(self, product: Product, quantity: int):
        self._product: Product = product
        self._quantity: int = quantity

    @property
    def product(self) -> Product:
        return self._product

    @property
    def quantity(self) -> int:
        return self._quantity

    def add_quantity(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self._quantity += amount

class Cart:
    def __init__(self):
        self._items: Dict[str, CartItem] = {}

    def add_item(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if product.id in self._items:
            self._items[product.id].add_quantity(quantity)
        else:
            self._items[product.id] = CartItem(product, quantity)

    def remove_item(self, product: Product) -> None:
        if product.id in self._items:
            del self._items[product.id]

    def clear(self) -> None:
        self._items.clear()

    def get_items(self) -> List[CartItem]:
        return list(self._items.values())

    def get_total(self) -> float:
        return sum(item.product.price * item.quantity for item in self._items.values())

class User:
    def __init__(self, username: str, password: str, email: str, is_admin: bool = False):
        self._id: str = str(uuid.uuid4())
        self._username: str = username
        self._password: str = password 
        self._email: str = email
        self._is_admin: bool = is_admin
        self._is_logged_in: bool = False
        self._cart: Cart = Cart()

    @property
    def id(self) -> str:
        return self._id

    @property
    def username(self) -> str:
        return self._username

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @property
    def cart(self) -> Cart:
        return self._cart

    def verify_password(self, password: str) -> bool:
        return self._password == password

    def login(self, password: str) -> bool:
        if self.verify_password(password):
            self._is_logged_in = True
            return True
        return False

    def logout(self) -> None:
        self._is_logged_in = False

class SalesOrder:
    def __init__(self, user: User, items: List[CartItem], total_amount: float):
        self._id: str = str(uuid.uuid4())
        self._user: User = user
        self._items: List[CartItem] = items
        self._total_amount: float = total_amount
        self._status: str = "PENDING"
        self._created_at: datetime = datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def status(self) -> str:
        return self._status

    def process(self) -> None:
        if self._status != "PENDING":
            raise ValueError("Order is already processed or shipped")
        self._status = "PROCESSED"

    def ship(self) -> None:
        if self._status != "PROCESSED":
            raise ValueError("Order must be processed before shipping")
        self._status = "SHIPPED"

class PurchaseOrder:
    def __init__(self, supplier: Supplier, product: Product, quantity: int, warehouse: Warehouse):
        self._id: str = str(uuid.uuid4())
        self._supplier: Supplier = supplier
        self._product: Product = product
        self._quantity: int = quantity
        self._warehouse: Warehouse = warehouse
        self._status: str = "PENDING"
        self._created_at: datetime = datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def product(self) -> Product:
        return self._product

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def warehouse(self) -> Warehouse:
        return self._warehouse

    @property
    def status(self) -> str:
        return self._status

    def receive(self) -> None:
        if self._status == "RECEIVED":
            raise ValueError("Purchase order already received")
        self._status = "RECEIVED"

class AmazonCloneSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._products: Dict[str, Product] = {}
        self._categories: Dict[str, Category] = {}
        self._suppliers: Dict[str, Supplier] = {}
        self._warehouses: Dict[str, Warehouse] = {}
        self._inventory_manager: InventoryManager = InventoryManager()
        self._sales_orders: Dict[str, SalesOrder] = {}
        self._purchase_orders: Dict[str, PurchaseOrder] = {}
        self._current_user: Optional[User] = None

    def _require_admin(self) -> None:
        if not self._current_user or not self._current_user.is_admin:
            raise UnauthorizedError("Admin privileges required")

    def _require_auth(self) -> None:
        if not self._current_user or not self._current_user.is_logged_in:
            raise UnauthorizedError("User must be logged in")

    def sign_up(self, username: str, password: str, email: str, is_admin: bool = False) -> User:
        if username in self._users:
            raise ValueError("Username already exists")
        user = User(username, password, email, is_admin)
        self._users[username] = user
        return user

    def login(self, username: str, password: str) -> bool:
        user = self._users.get(username)
        if user and user.login(password):
            self._current_user = user
            return True
        return False

    def logout(self) -> None:
        if self._current_user:
            self._current_user.logout()
            self._current_user = None

    def create_category(self, name: str, parent_id: Optional[str] = None) -> Category:
        self._require_admin()
        parent = self._categories.get(parent_id) if parent_id else None
        category = Category(name, parent)
        self._categories[category.id] = category
        return category

    def create_supplier(self, name: str, contact_info: str) -> Supplier:
        self._require_admin()
        supplier = Supplier(name, contact_info)
        self._suppliers[supplier.id] = supplier
        return supplier

    def create_warehouse(self, name: str, location: str) -> Warehouse:
        self._require_admin()
        warehouse = Warehouse(name, location)
        self._warehouses[warehouse.id] = warehouse
        return warehouse

    def create_product(self, name: str, description: str, price: float, category_id: str, supplier_id: str) -> Product:
        self._require_admin()
        category = self._categories.get(category_id)
        supplier = self._suppliers.get(supplier_id)
        if not category or not supplier:
            raise EntityNotFoundError("Category or Supplier not found")
        
        product = Product(name, description, price, category, supplier)
        self._products[product.id] = product
        return product

    def search_products(self, keyword: str) -> List[Product]:
        keyword = keyword.lower()
        return [p for p in self._products.values() if keyword in p.name.lower() or keyword in p.description.lower()]

    def get_product_detail(self, product_id: str) -> Dict[str, Any]:
        product = self._products.get(product_id)
        if not product:
            raise EntityNotFoundError("Product not found")
        stock = self._inventory_manager.get_total_stock(product)
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "category": product.category.name,
            "supplier": product.supplier.name,
            "stock_available": stock
        }

    def add_to_cart(self, product_id: str, quantity: int) -> None:
        self._require_auth()
        product = self._products.get(product_id)
        if not product:
            raise EntityNotFoundError("Product not found")
        
        available_stock = self._inventory_manager.get_total_stock(product)
        if available_stock < quantity:
            raise OutOfStockError("Not enough stock available")
            
        self._current_user.cart.add_item(product, quantity)

    def view_cart(self) -> Dict[str, Any]:
        self._require_auth()
        cart = self._current_user.cart
        items = [{"product": item.product.name, "quantity": item.quantity, "subtotal": item.product.price * item.quantity} for item in cart.get_items()]
        return {
            "items": items,
            "total": cart.get_total()
        }

    def checkout(self) -> SalesOrder:
        self._require_auth()
        cart = self._current_user.cart
        items = cart.get_items()
        
        if not items:
            raise ValueError("Cart is empty")

        for item in items:
            if self._inventory_manager.get_total_stock(item.product) < item.quantity:
                raise OutOfStockError(f"Product {item.product.name} is out of stock for the requested quantity")

        for item in items:
            self._inventory_manager.remove_stock(item.product, item.quantity)

        order = SalesOrder(self._current_user, items.copy(), cart.get_total())
        self._sales_orders[order.id] = order
        cart.clear()
        return order

    def create_purchase_order(self, supplier_id: str, product_id: str, quantity: int, warehouse_id: str) -> PurchaseOrder:
        self._require_admin()
        supplier = self._suppliers.get(supplier_id)
        product = self._products.get(product_id)
        warehouse = self._warehouses.get(warehouse_id)
        
        if not all([supplier, product, warehouse]):
            raise EntityNotFoundError("Supplier, Product, or Warehouse not found")

        po = PurchaseOrder(supplier, product, quantity, warehouse)
        self._purchase_orders[po.id] = po
        return po

    def receive_purchase_order(self, po_id: str) -> None:
        self._require_admin()
        po = self._purchase_orders.get(po_id)
        if not po:
            raise EntityNotFoundError("Purchase Order not found")
        
        po.receive()
        self._inventory_manager.add_stock(po.product, po.warehouse, po.quantity)