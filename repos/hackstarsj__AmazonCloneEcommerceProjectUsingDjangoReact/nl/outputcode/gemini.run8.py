from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class User:
    def __init__(self, user_id: int, username: str, email: str, password: str, is_admin: bool = False):
        self.user_id = user_id
        self.username = username
        self.email = email
        self._password = password
        self.is_admin = is_admin
        self.is_logged_in = False

    def login(self, password: str) -> bool:
        if self._password == password:
            self.is_logged_in = True
            return True
        return False

    def logout(self) -> None:
        self.is_logged_in = False

class Category:
    def __init__(self, category_id: int, name: str, parent: Optional['Category'] = None):
        self.category_id = category_id
        self.name = name
        self.parent = parent
        self.subcategories: List['Category'] = []
        if parent:
            parent.subcategories.append(self)

class Product:
    def __init__(self, product_id: int, name: str, description: str, price: float, category: Category):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.category = category

class Warehouse:
    def __init__(self, warehouse_id: int, name: str, location: str):
        self.warehouse_id = warehouse_id
        self.name = name
        self.location = location

class Supplier:
    def __init__(self, supplier_id: int, name: str, contact_info: str):
        self.supplier_id = supplier_id
        self.name = name
        self.contact_info = contact_info

class Inventory:
    def __init__(self):
        self.stock: Dict[int, Dict[int, int]] = {}

    def add_stock(self, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if product.product_id not in self.stock:
            self.stock[product.product_id] = {}
        if warehouse.warehouse_id not in self.stock[product.product_id]:
            self.stock[product.product_id][warehouse.warehouse_id] = 0
        self.stock[product.product_id][warehouse.warehouse_id] += quantity

    def remove_stock(self, product: Product, warehouse: Warehouse, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        current_stock = self.stock.get(product.product_id, {}).get(warehouse.warehouse_id, 0)
        if current_stock < quantity:
            raise ValueError("Insufficient stock in the specified warehouse")
        self.stock[product.product_id][warehouse.warehouse_id] -= quantity

    def get_total_stock(self, product: Product) -> int:
        return sum(self.stock.get(product.product_id, {}).values())

class CartItem:
    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = quantity

class ShoppingCart:
    def __init__(self, user: User):
        self.user = user
        self.items: Dict[int, CartItem] = {}

    def add_item(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if product.product_id in self.items:
            self.items[product.product_id].quantity += quantity
        else:
            self.items[product.product_id] = CartItem(product, quantity)

    def remove_item(self, product: Product, quantity: int) -> None:
        if product.product_id in self.items:
            if self.items[product.product_id].quantity <= quantity:
                del self.items[product.product_id]
            else:
                self.items[product.product_id].quantity -= quantity

    def get_total(self) -> float:
        return sum(item.product.price * item.quantity for item in self.items.values())

    def clear(self) -> None:
        self.items.clear()

class OrderStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class SalesOrder:
    def __init__(self, order_id: int, user: User, items: List[CartItem], shipping_address: str):
        self.order_id = order_id
        self.user = user
        self.items = items
        self.total_amount = sum(item.product.price * item.quantity for item in items)
        self.shipping_address = shipping_address
        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()

    def update_status(self, new_status: OrderStatus) -> None:
        self.status = new_status

class PurchaseOrderStatus(Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    RECEIVED = "RECEIVED"

class PurchaseOrder:
    def __init__(self, po_id: int, supplier: Supplier, product: Product, quantity: int, warehouse: Warehouse):
        self.po_id = po_id
        self.supplier = supplier
        self.product = product
        self.quantity = quantity
        self.warehouse = warehouse
        self.status = PurchaseOrderStatus.REQUESTED
        self.created_at = datetime.now()

    def receive_inventory(self, inventory: Inventory) -> None:
        if self.status == PurchaseOrderStatus.RECEIVED:
            raise ValueError("Purchase order already received")
        inventory.add_stock(self.product, self.warehouse, self.quantity)
        self.status = PurchaseOrderStatus.RECEIVED

class AmazonCloneSystem:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.products: Dict[int, Product] = {}
        self.categories: Dict[int, Category] = {}
        self.warehouses: Dict[int, Warehouse] = {}
        self.suppliers: Dict[int, Supplier] = {}
        self.inventory = Inventory()
        self.sales_orders: Dict[int, SalesOrder] = {}
        self.purchase_orders: Dict[int, PurchaseOrder] = {}
        self.carts: Dict[int, ShoppingCart] = {}
        
        self._next_user_id = 1
        self._next_product_id = 1
        self._next_category_id = 1
        self._next_warehouse_id = 1
        self._next_supplier_id = 1
        self._next_so_id = 1
        self._next_po_id = 1

    def sign_up(self, username: str, email: str, password: str, is_admin: bool = False) -> User:
        for user in self.users.values():
            if user.email == email:
                raise ValueError("Email already registered")
        user = User(self._next_user_id, username, email, password, is_admin)
        self.users[self._next_user_id] = user
        self.carts[self._next_user_id] = ShoppingCart(user)
        self._next_user_id += 1
        return user

    def login(self, email: str, password: str) -> Optional[User]:
        for user in self.users.values():
            if user.email == email:
                if user.login(password):
                    return user
        return None

    def logout(self, user_id: int) -> None:
        if user_id in self.users:
            self.users[user_id].logout()

    def create_category(self, name: str, parent_id: Optional[int] = None) -> Category:
        parent = self.categories.get(parent_id) if parent_id else None
        category = Category(self._next_category_id, name, parent)
        self.categories[self._next_category_id] = category
        self._next_category_id += 1
        return category

    def add_product(self, name: str, description: str, price: float, category_id: int, admin_user: User) -> Product:
        if not admin_user.is_admin or not admin_user.is_logged_in:
            raise PermissionError("Only logged-in admins can add products")
        if category_id not in self.categories:
            raise ValueError("Invalid category ID")
        category = self.categories[category_id]
        product = Product(self._next_product_id, name, description, price, category)
        self.products[self._next_product_id] = product
        self._next_product_id += 1
        return product

    def search_products(self, keyword: str) -> List[Product]:
        keyword = keyword.lower()
        return [p for p in self.products.values() if keyword in p.name.lower() or keyword in p.description.lower()]

    def get_product_detail(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def add_warehouse(self, name: str, location: str, admin_user: User) -> Warehouse:
        if not admin_user.is_admin or not admin_user.is_logged_in:
            raise PermissionError("Only logged-in admins can add warehouses")
        warehouse = Warehouse(self._next_warehouse_id, name, location)
        self.warehouses[self._next_warehouse_id] = warehouse
        self._next_warehouse_id += 1
        return warehouse

    def add_supplier(self, name: str, contact_info: str, admin_user: User) -> Supplier:
        if not admin_user.is_admin or not admin_user.is_logged_in:
            raise PermissionError("Only logged-in admins can add suppliers")
        supplier = Supplier(self._next_supplier_id, name, contact_info)
        self.suppliers[self._next_supplier_id] = supplier
        self._next_supplier_id += 1
        return supplier

    def create_purchase_order(self, supplier_id: int, product_id: int, quantity: int, warehouse_id: int, admin_user: User) -> PurchaseOrder:
        if not admin_user.is_admin or not admin_user.is_logged_in:
            raise PermissionError("Only logged-in admins can create purchase orders")
        supplier = self.suppliers[supplier_id]
        product = self.products[product_id]
        warehouse = self.warehouses[warehouse_id]
        po = PurchaseOrder(self._next_po_id, supplier, product, quantity, warehouse)
        self.purchase_orders[self._next_po_id] = po
        self._next_po_id += 1
        return po

    def receive_purchase_order(self, po_id: int, admin_user: User) -> None:
        if not admin_user.is_admin or not admin_user.is_logged_in:
            raise PermissionError("Only logged-in admins can receive purchase orders")
        po = self.purchase_orders[po_id]
        po.receive_inventory(self.inventory)

    def add_to_cart(self, user_id: int, product_id: int, quantity: int) -> None:
        user = self.users[user_id]
        if not user.is_logged_in:
            raise PermissionError("User must be logged in to add to cart")
        product = self.products[product_id]
        self.carts[user_id].add_item(product, quantity)

    def view_cart(self, user_id: int) -> ShoppingCart:
        user = self.users[user_id]
        if not user.is_logged_in:
            raise PermissionError("User must be logged in to view cart")
        return self.carts[user_id]

    def place_sales_order(self, user_id: int, shipping_address: str) -> SalesOrder:
        user = self.users[user_id]
        if not user.is_logged_in:
            raise PermissionError("User must be logged in to place an order")
        
        cart = self.carts[user_id]
        if not cart.items:
            raise ValueError("Cart is empty")

        for item in cart.items.values():
            if self.inventory.get_total_stock(item.product) < item.quantity:
                raise ValueError(f"Insufficient stock for product: {item.product.name}")

        for item in cart.items.values():
            remaining_to_deduct = item.quantity
            product_stock = self.inventory.stock.get(item.product.product_id, {})
            for w_id, qty in list(product_stock.items()):
                if remaining_to_deduct == 0:
                    break
                if qty > 0:
                    deduct = min(qty, remaining_to_deduct)
                    warehouse = self.warehouses[w_id]
                    self.inventory.remove_stock(item.product, warehouse, deduct)
                    remaining_to_deduct -= deduct

        order_items = list(cart.items.values())
        order = SalesOrder(self._next_so_id, user, order_items, shipping_address)
        self.sales_orders[self._next_so_id] = order
        self._next_so_id += 1
        cart.clear()
        return order

    def update_sales_order_status(self, order_id: int, status: OrderStatus, admin_user: User) -> None:
        if not admin_user.is_admin or not admin_user.is_logged_in:
            raise PermissionError("Only logged-in admins can update order status")
        order = self.sales_orders[order_id]
        order.update_status(status)