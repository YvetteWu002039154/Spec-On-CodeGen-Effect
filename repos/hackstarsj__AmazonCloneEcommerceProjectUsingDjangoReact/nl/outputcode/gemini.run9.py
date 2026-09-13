import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any

class Role(Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PurchaseOrderStatus(Enum):
    ISSUED = "ISSUED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"

class User:
    def __init__(self, username: str, password_hash: str, email: str, role: Role = Role.CUSTOMER):
        self.id: str = str(uuid.uuid4())
        self.username: str = username
        self._password_hash: str = password_hash
        self.email: str = email
        self.role: Role = role
        self.is_active: bool = True
        self.is_logged_in: bool = False

    def verify_password(self, password: str) -> bool:
        return self._password_hash == self._hash_password(password)

    @staticmethod
    def _hash_password(password: str) -> str:
        return f"hashed_{password}"

    def login(self, password: str) -> bool:
        if self.verify_password(password) and self.is_active:
            self.is_logged_in = True
            return True
        return False

    def logout(self) -> None:
        self.is_logged_in = False

class Category:
    def __init__(self, name: str, parent: Optional['Category'] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.parent: Optional['Category'] = parent
        self.subcategories: List['Category'] = []
        if parent:
            parent.add_subcategory(self)

    def add_subcategory(self, category: 'Category') -> None:
        if category not in self.subcategories:
            self.subcategories.append(category)

    def get_full_path(self) -> str:
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

class Supplier:
    def __init__(self, name: str, contact_email: str, phone: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.contact_email: str = contact_email
        self.phone: str = phone

class Product:
    def __init__(self, name: str, description: str, price: float, category: Category, supplier: Supplier):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.price: float = price
        self.category: Category = category
        self.supplier: Supplier = supplier

class Warehouse:
    def __init__(self, name: str, location: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.location: str = location

class InventoryItem:
    def __init__(self, product: Product, warehouse: Warehouse, quantity: int = 0):
        self.id: str = str(uuid.uuid4())
        self.product: Product = product
        self.warehouse: Warehouse = warehouse
        self.quantity: int = quantity

class CartItem:
    def __init__(self, product: Product, quantity: int):
        self.product: Product = product
        self.quantity: int = quantity

class ShoppingCart:
    def __init__(self, user: User):
        self.user: User = user
        self.items: Dict[str, CartItem] = {}

    def add_item(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if product.id in self.items:
            self.items[product.id].quantity += quantity
        else:
            self.items[product.id] = CartItem(product, quantity)

    def remove_item(self, product_id: str) -> None:
        if product_id in self.items:
            del self.items[product_id]

    def update_quantity(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            self.remove_item(product_id)
        elif product_id in self.items:
            self.items[product_id].quantity = quantity

    def get_total(self) -> float:
        return sum(item.product.price * item.quantity for item in self.items.values())

    def clear(self) -> None:
        self.items.clear()

class SalesOrder:
    def __init__(self, user: User, items: List[CartItem], total_amount: float):
        self.id: str = str(uuid.uuid4())
        self.user: User = user
        self.items: List[CartItem] = items
        self.total_amount: float = total_amount
        self.status: OrderStatus = OrderStatus.PENDING
        self.created_at: datetime = datetime.now()

class PurchaseOrder:
    def __init__(self, supplier: Supplier, product: Product, warehouse: Warehouse, quantity: int):
        self.id: str = str(uuid.uuid4())
        self.supplier: Supplier = supplier
        self.product: Product = product
        self.warehouse: Warehouse = warehouse
        self.quantity: int = quantity
        self.status: PurchaseOrderStatus = PurchaseOrderStatus.ISSUED
        self.created_at: datetime = datetime.now()

class InventoryManager:
    def __init__(self):
        self.inventory: List[InventoryItem] = []

    def add_stock(self, product: Product, warehouse: Warehouse, quantity: int) -> None:
        for item in self.inventory:
            if item.product.id == product.id and item.warehouse.id == warehouse.id:
                item.quantity += quantity
                return
        self.inventory.append(InventoryItem(product, warehouse, quantity))

    def get_total_stock(self, product_id: str) -> int:
        return sum(item.quantity for item in self.inventory if item.product.id == product_id)

    def reserve_stock(self, product_id: str, quantity: int) -> bool:
        if self.get_total_stock(product_id) < quantity:
            return False
        
        remaining_to_reserve = quantity
        for item in self.inventory:
            if item.product.id == product_id:
                if item.quantity >= remaining_to_reserve:
                    item.quantity -= remaining_to_reserve
                    return True
                else:
                    remaining_to_reserve -= item.quantity
                    item.quantity = 0
        return False

class AmazonCloneSystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.categories: Dict[str, Category] = {}
        self.products: Dict[str, Product] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.warehouses: Dict[str, Warehouse] = {}
        self.carts: Dict[str, ShoppingCart] = {}
        self.sales_orders: Dict[str, SalesOrder] = {}
        self.purchase_orders: Dict[str, PurchaseOrder] = {}
        self.inventory_manager: InventoryManager = InventoryManager()
        self.current_user: Optional[User] = None

    def register_user(self, username: str, password: str, email: str, role: Role = Role.CUSTOMER) -> User:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username already exists.")
        user = User(username, User._hash_password(password), email, role)
        self.users[user.id] = user
        self.carts[user.id] = ShoppingCart(user)
        return user

    def login(self, username: str, password: str) -> bool:
        for user in self.users.values():
            if user.username == username:
                if user.login(password):
                    self.current_user = user
                    return True
        return False

    def logout(self) -> None:
        if self.current_user:
            self.current_user.logout()
            self.current_user = None

    def add_category(self, name: str, parent_id: Optional[str] = None) -> Category:
        self._require_admin()
        parent = self.categories.get(parent_id) if parent_id else None
        category = Category(name, parent)
        self.categories[category.id] = category
        return category

    def add_supplier(self, name: str, email: str, phone: str) -> Supplier:
        self._require_admin()
        supplier = Supplier(name, email, phone)
        self.suppliers[supplier.id] = supplier
        return supplier

    def add_warehouse(self, name: str, location: str) -> Warehouse:
        self._require_admin()
        warehouse = Warehouse(name, location)
        self.warehouses[warehouse.id] = warehouse
        return warehouse

    def add_product(self, name: str, description: str, price: float, category_id: str, supplier_id: str) -> Product:
        self._require_admin()
        if category_id not in self.categories:
            raise ValueError("Category not found.")
        if supplier_id not in self.suppliers:
            raise ValueError("Supplier not found.")
        
        product = Product(
            name=name,
            description=description,
            price=price,
            category=self.categories[category_id],
            supplier=self.suppliers[supplier_id]
        )
        self.products[product.id] = product
        return product

    def search_products(self, keyword: str) -> List[Product]:
        keyword = keyword.lower()
        return [
            p for p in self.products.values()
            if keyword in p.name.lower() or keyword in p.description.lower()
        ]

    def get_product_detail(self, product_id: str) -> Dict[str, Any]:
        if product_id not in self.products:
            raise ValueError("Product not found.")
        product = self.products[product_id]
        stock = self.inventory_manager.get_total_stock(product_id)
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "category": product.category.get_full_path(),
            "supplier": product.supplier.name,
            "stock_available": stock
        }

    def add_to_cart(self, product_id: str, quantity: int) -> None:
        self._require_login()
        if product_id not in self.products:
            raise ValueError("Product not found.")
        product = self.products[product_id]
        self.carts[self.current_user.id].add_item(product, quantity)

    def view_cart(self) -> Dict[str, Any]:
        self._require_login()
        cart = self.carts[self.current_user.id]
        return {
            "items": [{"product": item.product.name, "quantity": item.quantity, "subtotal": item.product.price * item.quantity} for item in cart.items.values()],
            "total": cart.get_total()
        }

    def checkout(self) -> SalesOrder:
        self._require_login()
        cart = self.carts[self.current_user.id]
        if not cart.items:
            raise ValueError("Cart is empty.")

        for item in cart.items.values():
            if self.inventory_manager.get_total_stock(item.product.id) < item.quantity:
                raise ValueError(f"Insufficient stock for product: {item.product.name}")

        for item in cart.items.values():
            self.inventory_manager.reserve_stock(item.product.id, item.quantity)

        order = SalesOrder(self.current_user, list(cart.items.values()), cart.get_total())
        self.sales_orders[order.id] = order
        cart.clear()
        return order

    def create_purchase_order(self, supplier_id: str, product_id: str, warehouse_id: str, quantity: int) -> PurchaseOrder:
        self._require_admin()
        if supplier_id not in self.suppliers or product_id not in self.products or warehouse_id not in self.warehouses:
            raise ValueError("Invalid supplier, product, or warehouse ID.")
        
        po = PurchaseOrder(
            supplier=self.suppliers[supplier_id],
            product=self.products[product_id],
            warehouse=self.warehouses[warehouse_id],
            quantity=quantity
        )
        self.purchase_orders[po.id] = po
        return po

    def receive_purchase_order(self, po_id: str) -> None:
        self._require_admin()
        if po_id not in self.purchase_orders:
            raise ValueError("Purchase order not found.")
        
        po = self.purchase_orders[po_id]
        if po.status != PurchaseOrderStatus.ISSUED:
            raise ValueError("Purchase order already processed.")
        
        self.inventory_manager.add_stock(po.product, po.warehouse, po.quantity)
        po.status = PurchaseOrderStatus.RECEIVED

    def update_sales_order_status(self, order_id: str, status: OrderStatus) -> None:
        self._require_admin()
        if order_id not in self.sales_orders:
            raise ValueError("Sales order not found.")
        self.sales_orders[order_id].status = status

    def _require_login(self) -> None:
        if not self.current_user or not self.current_user.is_logged_in:
            raise PermissionError("User must be logged in to perform this action.")

    def _require_admin(self) -> None:
        self._require_login()
        if self.current_user.role != Role.ADMIN:
            raise PermissionError("Admin privileges required.")