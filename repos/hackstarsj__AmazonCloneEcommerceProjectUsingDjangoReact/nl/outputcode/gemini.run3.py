import uuid
from typing import List, Dict, Optional
from datetime import datetime

class AuthenticationError(Exception):
    pass

class AuthorizationError(Exception):
    pass

class OutOfStockError(Exception):
    pass

class ItemNotFoundError(Exception):
    pass

class User:
    def __init__(self, username: str, password_hash: str, email: str, is_admin: bool = False):
        self.user_id: str = str(uuid.uuid4())
        self.username: str = username
        self.password_hash: str = password_hash
        self.email: str = email
        self.is_admin: bool = is_admin
        self.is_logged_in: bool = False

    def verify_password(self, password: str) -> bool:
        return self.password_hash == self._hash_password(password)

    @staticmethod
    def _hash_password(password: str) -> str:
        return password[::-1] 

class Category:
    def __init__(self, name: str, parent: Optional['Category'] = None):
        self.category_id: str = str(uuid.uuid4())
        self.name: str = name
        self.parent: Optional['Category'] = parent
        self.subcategories: List['Category'] = []
        if parent:
            parent.subcategories.append(self)

    def get_full_path(self) -> str:
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

class Product:
    def __init__(self, name: str, description: str, price: float, category: Category):
        self.product_id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.price: float = price
        self.category: Category = category

class Supplier:
    def __init__(self, name: str, contact_info: str):
        self.supplier_id: str = str(uuid.uuid4())
        self.name: str = name
        self.contact_info: str = contact_info

class Warehouse:
    def __init__(self, name: str, location: str):
        self.warehouse_id: str = str(uuid.uuid4())
        self.name: str = name
        self.location: str = location

class InventoryManager:
    def __init__(self):
        self.stocks: Dict[str, Dict[str, int]] = {}

    def add_stock(self, warehouse_id: str, product_id: str, quantity: int) -> None:
        if warehouse_id not in self.stocks:
            self.stocks[warehouse_id] = {}
        current_stock = self.stocks[warehouse_id].get(product_id, 0)
        self.stocks[warehouse_id][product_id] = current_stock + quantity

    def get_total_stock(self, product_id: str) -> int:
        return sum(warehouse_stock.get(product_id, 0) for warehouse_stock in self.stocks.values())

    def remove_stock_global(self, product_id: str, quantity: int, available_warehouses: List[str]) -> None:
        if self.get_total_stock(product_id) < quantity:
            raise OutOfStockError(f"Insufficient stock for product ID: {product_id}")
        
        remaining_to_deduct = quantity
        for w_id in available_warehouses:
            if remaining_to_deduct <= 0:
                break
            stock_here = self.stocks.get(w_id, {}).get(product_id, 0)
            if stock_here > 0:
                deduct = min(stock_here, remaining_to_deduct)
                self.stocks[w_id][product_id] -= deduct
                remaining_to_deduct -= deduct

class CartItem:
    def __init__(self, product: Product, quantity: int):
        self.product: Product = product
        self.quantity: int = quantity

class Cart:
    def __init__(self, user: User):
        self.user: User = user
        self.items: Dict[str, CartItem] = {}

    def add_item(self, product: Product, quantity: int) -> None:
        if product.product_id in self.items:
            self.items[product.product_id].quantity += quantity
        else:
            self.items[product.product_id] = CartItem(product, quantity)

    def remove_item(self, product_id: str, quantity: int) -> None:
        if product_id in self.items:
            self.items[product_id].quantity -= quantity
            if self.items[product_id].quantity <= 0:
                del self.items[product_id]

    def clear(self) -> None:
        self.items.clear()

    def get_total(self) -> float:
        return sum(item.product.price * item.quantity for item in self.items.values())

class SalesOrder:
    def __init__(self, user: User, items: List[CartItem], total_amount: float):
        self.order_id: str = str(uuid.uuid4())
        self.user: User = user
        self.items: List[CartItem] = items
        self.total_amount: float = total_amount
        self.status: str = "PENDING"
        self.created_at: datetime = datetime.now()

class PurchaseOrder:
    def __init__(self, supplier: Supplier, warehouse: Warehouse):
        self.po_id: str = str(uuid.uuid4())
        self.supplier: Supplier = supplier
        self.warehouse: Warehouse = warehouse
        self.items: Dict[Product, int] = {}
        self.status: str = "DRAFT"
        self.created_at: datetime = datetime.now()

    def add_item(self, product: Product, quantity: int) -> None:
        if self.status != "DRAFT":
            raise ValueError("Cannot add items to a non-draft purchase order.")
        self.items[product] = self.items.get(product, 0) + quantity

    def receive(self, inventory_manager: InventoryManager) -> None:
        if self.status == "RECEIVED":
            raise ValueError("Purchase order already received.")
        for product, quantity in self.items.items():
            inventory_manager.add_stock(self.warehouse.warehouse_id, product.product_id, quantity)
        self.status = "RECEIVED"

class AmazonClone:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.categories: Dict[str, Category] = {}
        self.products: Dict[str, Product] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.warehouses: Dict[str, Warehouse] = {}
        self.inventory: InventoryManager = InventoryManager()
        self.carts: Dict[str, Cart] = {}
        self.sales_orders: Dict[str, SalesOrder] = {}
        self.purchase_orders: Dict[str, PurchaseOrder] = {}

    def sign_up(self, username: str, password: str, email: str, is_admin: bool = False) -> User:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username already exists.")
        password_hash = User._hash_password(password)
        new_user = User(username, password_hash, email, is_admin)
        self.users[new_user.user_id] = new_user
        self.carts[new_user.user_id] = Cart(new_user)
        return new_user

    def login(self, username: str, password: str) -> User:
        for user in self.users.values():
            if user.username == username:
                if user.verify_password(password):
                    user.is_logged_in = True
                    return user
                else:
                    raise AuthenticationError("Invalid password.")
        raise AuthenticationError("User not found.")

    def logout(self, user_id: str) -> None:
        if user_id in self.users:
            self.users[user_id].is_logged_in = False

    def _require_admin(self, user_id: str) -> None:
        user = self.users.get(user_id)
        if not user or not user.is_logged_in or not user.is_admin:
            raise AuthorizationError("Admin privileges required.")

    def create_category(self, admin_id: str, name: str, parent_id: Optional[str] = None) -> Category:
        self._require_admin(admin_id)
        parent = self.categories.get(parent_id) if parent_id else None
        category = Category(name, parent)
        self.categories[category.category_id] = category
        return category

    def create_product(self, admin_id: str, name: str, description: str, price: float, category_id: str) -> Product:
        self._require_admin(admin_id)
        category = self.categories.get(category_id)
        if not category:
            raise ItemNotFoundError("Category not found.")
        product = Product(name, description, price, category)
        self.products[product.product_id] = product
        return product

    def search_products(self, keyword: str) -> List[Product]:
        keyword = keyword.lower()
        return [
            p for p in self.products.values()
            if keyword in p.name.lower() or keyword in p.description.lower()
        ]

    def get_product_detail(self, product_id: str) -> Product:
        if product_id not in self.products:
            raise ItemNotFoundError("Product not found.")
        return self.products[product_id]

    def add_to_cart(self, user_id: str, product_id: str, quantity: int) -> None:
        user = self.users.get(user_id)
        if not user or not user.is_logged_in:
            raise AuthenticationError("User must be logged in.")
        product = self.get_product_detail(product_id)
        self.carts[user_id].add_item(product, quantity)

    def view_cart(self, user_id: str) -> Cart:
        return self.carts.get(user_id)

    def checkout(self, user_id: str) -> SalesOrder:
        user = self.users.get(user_id)
        if not user or not user.is_logged_in:
            raise AuthenticationError("User must be logged in.")
        
        cart = self.carts.get(user_id)
        if not cart or not cart.items:
            raise ValueError("Cart is empty.")

        for item in cart.items.values():
            if self.inventory.get_total_stock(item.product.product_id) < item.quantity:
                raise OutOfStockError(f"Product {item.product.name} is out of stock.")

        warehouse_ids = list(self.warehouses.keys())
        for item in cart.items.values():
            self.inventory.remove_stock_global(item.product.product_id, item.quantity, warehouse_ids)

        order_items = list(cart.items.values())
        total_amount = cart.get_total()
        sales_order = SalesOrder(user, order_items, total_amount)
        self.sales_orders[sales_order.order_id] = sales_order
        
        cart.clear()
        return sales_order

    def create_supplier(self, admin_id: str, name: str, contact_info: str) -> Supplier:
        self._require_admin(admin_id)
        supplier = Supplier(name, contact_info)
        self.suppliers[supplier.supplier_id] = supplier
        return supplier

    def create_warehouse(self, admin_id: str, name: str, location: str) -> Warehouse:
        self._require_admin(admin_id)
        warehouse = Warehouse(name, location)
        self.warehouses[warehouse.warehouse_id] = warehouse
        return warehouse

    def create_purchase_order(self, admin_id: str, supplier_id: str, warehouse_id: str) -> PurchaseOrder:
        self._require_admin(admin_id)
        supplier = self.suppliers.get(supplier_id)
        warehouse = self.warehouses.get(warehouse_id)
        if not supplier or not warehouse:
            raise ItemNotFoundError("Supplier or Warehouse not found.")
        
        po = PurchaseOrder(supplier, warehouse)
        self.purchase_orders[po.po_id] = po
        return po

    def add_item_to_po(self, admin_id: str, po_id: str, product_id: str, quantity: int) -> None:
        self._require_admin(admin_id)
        po = self.purchase_orders.get(po_id)
        product = self.products.get(product_id)
        if not po or not product:
            raise ItemNotFoundError("Purchase Order or Product not found.")
        po.add_item(product, quantity)

    def receive_purchase_order(self, admin_id: str, po_id: str) -> None:
        self._require_admin(admin_id)
        po = self.purchase_orders.get(po_id)
        if not po:
            raise ItemNotFoundError("Purchase Order not found.")
        po.receive(self.inventory)

if __name__ == "__main__":
    system = AmazonClone()

    admin = system.sign_up("admin", "adminpass", "admin@amazon.com", is_admin=True)
    system.login("admin", "adminpass")

    customer = system.sign_up("john_doe", "password123", "john@example.com")
    system.login("john_doe", "password123")

    electronics = system.create_category(admin.user_id, "Electronics")
    laptops = system.create_category(admin.user_id, "Laptops", electronics.category_id)

    laptop_prod = system.create_product(admin.user_id, "MacBook Pro", "Apple Laptop M2", 1999.99, laptops.category_id)
    mouse_prod = system.create_product(admin.user_id, "Logitech Mouse", "Wireless mouse", 49.99, electronics.category_id)

    supplier = system.create_supplier(admin.user_id, "TechDistributors", "contact@techdist.com")
    warehouse = system.create_warehouse(admin.user_id, "NY Central", "New York, NY")

    po = system.create_purchase_order(admin.user_id, supplier.supplier_id, warehouse.warehouse_id)
    system.add_item_to_po(admin.user_id, po.po_id, laptop_prod.product_id, 50)
    system.add_item_to_po(admin.user_id, po.po_id, mouse_prod.product_id, 200)
    system.receive_purchase_order(admin.user_id, po.po_id)

    search_results = system.search_products("macbook")
    
    system.add_to_cart(customer.user_id, laptop_prod.product_id, 1)
    system.add_to_cart(customer.user_id, mouse_prod.product_id, 2)

    sales_order = system.checkout(customer.user_id)
    
    system.logout(customer.user_id)
    system.logout(admin.user_id)