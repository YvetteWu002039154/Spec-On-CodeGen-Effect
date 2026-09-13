import uuid
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime

class Role(Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"

class OrderStatus(Enum):
    PENDING = "PENDING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class OrderType(Enum):
    SALES = "SALES"
    PURCHASE = "PURCHASE"

class UnauthorizedError(Exception):
    pass

class InsufficientStockError(Exception):
    pass

class ValidationError(Exception):
    pass

class User:
    def __init__(self, username: str, password: str, email: str, role: Role = Role.CUSTOMER):
        self._id: str = str(uuid.uuid4())
        self._username: str = username
        self._password: str = password
        self._email: str = email
        self._role: Role = role

    @property
    def id(self) -> str:
        return self._id

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> Role:
        return self._role

    def check_password(self, password: str) -> bool:
        return self._password == password

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
        self._subcategories.append(category)

    def get_all_subcategories(self) -> List['Category']:
        return self._subcategories

class Product:
    def __init__(self, name: str, description: str, price: float, category: Category):
        if price < 0:
            raise ValidationError("Price cannot be negative.")
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._description: str = description
        self._price: float = price
        self._category: Category = category

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

class CartItem:
    def __init__(self, product: Product, quantity: int):
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        self._product: Product = product
        self._quantity: int = quantity

    @property
    def product(self) -> Product:
        return self._product

    @property
    def quantity(self) -> int:
        return self._quantity

    def add_quantity(self, amount: int) -> None:
        if self._quantity + amount <= 0:
            raise ValidationError("Resulting quantity must be greater than zero.")
        self._quantity += amount

class ShoppingCart:
    def __init__(self, user: User):
        self._user: User = user
        self._items: Dict[str, CartItem] = {}

    @property
    def items(self) -> List[CartItem]:
        return list(self._items.values())

    def add_item(self, product: Product, quantity: int) -> None:
        if product.id in self._items:
            self._items[product.id].add_quantity(quantity)
        else:
            self._items[product.id] = CartItem(product, quantity)

    def remove_item(self, product_id: str) -> None:
        if product_id in self._items:
            del self._items[product_id]

    def clear(self) -> None:
        self._items.clear()

    def get_total(self) -> float:
        return sum(item.product.price * item.quantity for item in self._items.values())

class OrderItem:
    def __init__(self, product: Product, quantity: int, price: float):
        self._product: Product = product
        self._quantity: int = quantity
        self._price: float = price

    @property
    def product(self) -> Product:
        return self._product

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def price(self) -> float:
        return self._price

class Order:
    def __init__(self, order_type: OrderType, party_id: str, items: List[OrderItem]):
        self._id: str = str(uuid.uuid4())
        self._order_type: OrderType = order_type
        self._party_id: str = party_id 
        self._items: List[OrderItem] = items
        self._status: OrderStatus = OrderStatus.PENDING
        self._created_at: datetime = datetime.now()
        self._total_amount: float = sum(item.price * item.quantity for item in items)

    @property
    def id(self) -> str:
        return self._id

    @property
    def order_type(self) -> OrderType:
        return self._order_type

    @property
    def party_id(self) -> str:
        return self._party_id

    @property
    def items(self) -> List[OrderItem]:
        return self._items

    @property
    def status(self) -> OrderStatus:
        return self._status

    @property
    def total_amount(self) -> float:
        return self._total_amount

    def update_status(self, new_status: OrderStatus) -> None:
        self._status = new_status

class AmazonCloneSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._categories: Dict[str, Category] = {}
        self._products: Dict[str, Product] = {}
        self._suppliers: Dict[str, Supplier] = {}
        self._warehouses: Dict[str, Warehouse] = {}
        self._inventory: Dict[str, Dict[str, int]] = {} 
        self._carts: Dict[str, ShoppingCart] = {}
        self._orders: Dict[str, Order] = {}
        self._current_user: Optional[User] = None

    def _require_auth(self) -> User:
        if not self._current_user:
            raise UnauthorizedError("User must be logged in.")
        return self._current_user

    def _require_admin(self) -> User:
        user = self._require_auth()
        if user.role != Role.ADMIN:
            raise UnauthorizedError("Admin privileges required.")
        return user

    def sign_up(self, username: str, password: str, email: str, role: Role = Role.CUSTOMER) -> User:
        for user in self._users.values():
            if user.username == username:
                raise ValidationError("Username already exists.")
        new_user = User(username, password, email, role)
        self._users[new_user.id] = new_user
        self._carts[new_user.id] = ShoppingCart(new_user)
        return new_user

    def login(self, username: str, password: str) -> User:
        for user in self._users.values():
            if user.username == username and user.check_password(password):
                self._current_user = user
                return user
        raise UnauthorizedError("Invalid credentials.")

    def logout(self) -> None:
        self._current_user = None

    def get_all_users(self) -> List[User]:
        self._require_admin()
        return list(self._users.values())

    def create_category(self, name: str, parent_id: Optional[str] = None) -> Category:
        self._require_admin()
        parent = self._categories.get(parent_id) if parent_id else None
        category = Category(name, parent)
        self._categories[category.id] = category
        return category

    def add_product(self, name: str, description: str, price: float, category_id: str) -> Product:
        self._require_admin()
        if category_id not in self._categories:
            raise ValidationError("Category not found.")
        product = Product(name, description, price, self._categories[category_id])
        self._products[product.id] = product
        self._inventory[product.id] = {}
        return product

    def search_products(self, query: str) -> List[Product]:
        query = query.lower()
        return [p for p in self._products.values() if query in p.name.lower() or query in p.description.lower()]

    def get_product_detail(self, product_id: str) -> Product:
        if product_id not in self._products:
            raise ValidationError("Product not found.")
        return self._products[product_id]

    def add_supplier(self, name: str, contact_info: str) -> Supplier:
        self._require_admin()
        supplier = Supplier(name, contact_info)
        self._suppliers[supplier.id] = supplier
        return supplier

    def add_warehouse(self, name: str, location: str) -> Warehouse:
        self._require_admin()
        warehouse = Warehouse(name, location)
        self._warehouses[warehouse.id] = warehouse
        return warehouse

    def get_total_stock(self, product_id: str) -> int:
        if product_id not in self._inventory:
            return 0
        return sum(self._inventory[product_id].values())

    def add_to_cart(self, product_id: str, quantity: int) -> None:
        user = self._require_auth()
        if product_id not in self._products:
            raise ValidationError("Product not found.")
        product = self._products[product_id]
        self._carts[user.id].add_item(product, quantity)

    def view_cart(self) -> ShoppingCart:
        user = self._require_auth()
        return self._carts[user.id]

    def checkout(self) -> Order:
        user = self._require_auth()
        cart = self._carts[user.id]
        if not cart.items:
            raise ValidationError("Cart is empty.")

        for item in cart.items:
            if self.get_total_stock(item.product.id) < item.quantity:
                raise InsufficientStockError(f"Not enough stock for {item.product.name}")

        for item in cart.items:
            remaining_to_deduct = item.quantity
            for warehouse_id, stock in self._inventory[item.product.id].items():
                if remaining_to_deduct == 0:
                    break
                if stock > 0:
                    deduct = min(stock, remaining_to_deduct)
                    self._inventory[item.product.id][warehouse_id] -= deduct
                    remaining_to_deduct -= deduct

        order_items = [OrderItem(item.product, item.quantity, item.product.price) for item in cart.items]
        sales_order = Order(OrderType.SALES, user.id, order_items)
        self._orders[sales_order.id] = sales_order
        cart.clear()
        return sales_order

    def create_purchase_order(self, supplier_id: str, product_quantities: Dict[str, int]) -> Order:
        self._require_admin()
        if supplier_id not in self._suppliers:
            raise ValidationError("Supplier not found.")
        
        order_items = []
        for product_id, quantity in product_quantities.items():
            if product_id not in self._products:
                raise ValidationError(f"Product {product_id} not found.")
            product = self._products[product_id]
            order_items.append(OrderItem(product, quantity, product.price))
            
        purchase_order = Order(OrderType.PURCHASE, supplier_id, order_items)
        self._orders[purchase_order.id] = purchase_order
        return purchase_order

    def receive_purchase_order(self, order_id: str, warehouse_id: str) -> None:
        self._require_admin()
        if order_id not in self._orders:
            raise ValidationError("Order not found.")
        if warehouse_id not in self._warehouses:
            raise ValidationError("Warehouse not found.")
            
        order = self._orders[order_id]
        if order.order_type != OrderType.PURCHASE:
            raise ValidationError("Only purchase orders can be received into inventory.")
        if order.status == OrderStatus.DELIVERED:
            raise ValidationError("Order already received.")

        for item in order.items:
            product_id = item.product.id
            if warehouse_id not in self._inventory[product_id]:
                self._inventory[product_id][warehouse_id] = 0
            self._inventory[product_id][warehouse_id] += item.quantity
            
        order.update_status(OrderStatus.DELIVERED)

    def update_sales_order_status(self, order_id: str, status: OrderStatus) -> None:
        self._require_admin()
        if order_id not in self._orders:
            raise ValidationError("Order not found.")
        order = self._orders[order_id]
        if order.order_type != OrderType.SALES:
            raise ValidationError("Can only update sales orders through this method.")
        order.update_status(status)

    def get_user_orders(self) -> List[Order]:
        user = self._require_auth()
        return [order for order in self._orders.values() if order.party_id == user.id and order.order_type == OrderType.SALES]

if __name__ == "__main__":
    system = AmazonCloneSystem()
    
    admin = system.sign_up("admin", "adminpass", "admin@amazon.com", Role.ADMIN)
    customer = system.sign_up("john_doe", "password123", "john@example.com", Role.CUSTOMER)
    
    system.login("admin", "adminpass")
    
    electronics = system.create_category("Electronics")
    laptops = system.create_category("Laptops", electronics.id)
    
    laptop = system.add_product("Gaming Laptop", "High performance gaming laptop", 1500.00, laptops.id)
    mouse = system.add_product("Wireless Mouse", "Ergonomic wireless mouse", 25.00, electronics.id)
    
    supplier = system.add_supplier("TechDistributors Inc.", "contact@techdist.com")
    warehouse = system.add_warehouse("Central Warehouse", "New York, NY")
    
    po = system.create_purchase_order(supplier.id, {laptop.id: 10, mouse.id: 50})
    system.receive_purchase_order(po.id, warehouse.id)
    
    system.logout()
    
    system.login("john_doe", "password123")
    
    search_results = system.search_products("laptop")
    
    system.add_to_cart(laptop.id, 1)
    system.add_to_cart(mouse.id, 2)
    
    sales_order = system.checkout()
    
    system.logout()
    
    system.login("admin", "adminpass")
    system.update_sales_order_status(sales_order.id, OrderStatus.SHIPPED)