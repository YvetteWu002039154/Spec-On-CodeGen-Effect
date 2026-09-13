import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Any, Dict

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


DB_FILE = "inventory.db"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class Database:
    def __init__(self, path: str = DB_FILE) -> None:
        self._path = path
        self._conn = sqlite3.connect(self._path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                gender TEXT NOT NULL,
                dob TEXT,
                doj TEXT,
                address TEXT,
                salary REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT NOT NULL,
                company TEXT,
                address TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                supplier_id INTEGER,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT,
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_no TEXT PRIMARY KEY,
                customer_name TEXT,
                customer_phone TEXT,
                created_at TEXT NOT NULL,
                subtotal REAL NOT NULL,
                discount REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                notes TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(invoice_no) REFERENCES invoices(invoice_no) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
            )
            """
        )

        self._conn.commit()

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()
        return cur

    def query(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


@dataclass(frozen=True)
class Employee:
    id: int
    name: str
    email: str
    phone: str
    gender: str
    dob: Optional[str]
    doj: Optional[str]
    address: Optional[str]
    salary: float
    created_at: str


@dataclass(frozen=True)
class Supplier:
    id: int
    name: str
    email: Optional[str]
    phone: str
    company: Optional[str]
    address: Optional[str]
    created_at: str


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    description: Optional[str]
    created_at: str


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category_id: int
    supplier_id: Optional[int]
    price: float
    qty: int
    image_path: Optional[str]
    created_at: str


@dataclass(frozen=True)
class InvoiceItem:
    product_id: Optional[int]
    product_name: str
    price: float
    qty: int

    @property
    def line_total(self) -> float:
        return float(self.price) * int(self.qty)


@dataclass(frozen=True)
class Invoice:
    invoice_no: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    created_at: str
    subtotal: float
    discount: float
    tax: float
    total: float
    notes: Optional[str]


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(
        self,
        name: str,
        email: str,
        phone: str,
        gender: str,
        dob: Optional[str],
        doj: Optional[str],
        address: Optional[str],
        salary: float,
    ) -> int:
        name = name.strip()
        email = email.strip()
        phone = phone.strip()
        gender = gender.strip()
        if not name:
            raise ValueError("Employee name is required")
        if not email:
            raise ValueError("Employee email is required")
        if not phone:
            raise ValueError("Employee phone is required")
        if not gender:
            raise ValueError("Employee gender is required")
        if salary is None:
            salary = 0.0
        salary_f = float(salary)
        if salary_f < 0:
            raise ValueError("Salary cannot be negative")

        cur = self._db.execute(
            """
            INSERT INTO employees (name, email, phone, gender, dob, doj, address, salary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, email, phone, gender, dob, doj, address, salary_f, now_str()),
        )
        return int(cur.lastrowid)

    def update(
        self,
        emp_id: int,
        name: str,
        email: str,
        phone: str,
        gender: str,
        dob: Optional[str],
        doj: Optional[str],
        address: Optional[str],
        salary: float,
    ) -> None:
        name = name.strip()
        email = email.strip()
        phone = phone.strip()
        gender = gender.strip()
        if not name:
            raise ValueError("Employee name is required")
        if not email:
            raise ValueError("Employee email is required")
        if not phone:
            raise ValueError("Employee phone is required")
        if not gender:
            raise ValueError("Employee gender is required")
        salary_f = float(salary)
        if salary_f < 0:
            raise ValueError("Salary cannot be negative")

        self._db.execute(
            """
            UPDATE employees
            SET name=?, email=?, phone=?, gender=?, dob=?, doj=?, address=?, salary=?
            WHERE id=?
            """,
            (name, email, phone, gender, dob, doj, address, salary_f, int(emp_id)),
        )

    def delete(self, emp_id: int) -> None:
        self._db.execute("DELETE FROM employees WHERE id=?", (int(emp_id),))

    def get(self, emp_id: int) -> Optional[Employee]:
        rows = self._db.query("SELECT * FROM employees WHERE id=?", (int(emp_id),))
        if not rows:
            return None
        r = rows[0]
        return Employee(
            id=int(r["id"]),
            name=str(r["name"]),
            email=str(r["email"]),
            phone=str(r["phone"]),
            gender=str(r["gender"]),
            dob=r["dob"],
            doj=r["doj"],
            address=r["address"],
            salary=float(r["salary"]),
            created_at=str(r["created_at"]),
        )

    def list(self, search: str = "") -> List[Employee]:
        search = search.strip()
        if search:
            rows = self._db.query(
                """
                SELECT * FROM employees
                WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query("SELECT * FROM employees ORDER BY id DESC")
        out: List[Employee] = []
        for r in rows:
            out.append(
                Employee(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    email=str(r["email"]),
                    phone=str(r["phone"]),
                    gender=str(r["gender"]),
                    dob=r["dob"],
                    doj=r["doj"],
                    address=r["address"],
                    salary=float(r["salary"]),
                    created_at=str(r["created_at"]),
                )
            )
        return out

    def count(self) -> int:
        rows = self._db.query("SELECT COUNT(*) AS c FROM employees")
        return int(rows[0]["c"]) if rows else 0


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(
        self,
        name: str,
        email: Optional[str],
        phone: str,
        company: Optional[str],
        address: Optional[str],
    ) -> int:
        name = name.strip()
        phone = phone.strip()
        email = email.strip() if email else None
        company = company.strip() if company else None
        address = address.strip() if address else None
        if not name:
            raise ValueError("Supplier name is required")
        if not phone:
            raise ValueError("Supplier phone is required")

        cur = self._db.execute(
            """
            INSERT INTO suppliers (name, email, phone, company, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, email, phone, company, address, now_str()),
        )
        return int(cur.lastrowid)

    def update(
        self,
        supplier_id: int,
        name: str,
        email: Optional[str],
        phone: str,
        company: Optional[str],
        address: Optional[str],
    ) -> None:
        name = name.strip()
        phone = phone.strip()
        email = email.strip() if email else None
        company = company.strip() if company else None
        address = address.strip() if address else None
        if not name:
            raise ValueError("Supplier name is required")
        if not phone:
            raise ValueError("Supplier phone is required")

        self._db.execute(
            """
            UPDATE suppliers
            SET name=?, email=?, phone=?, company=?, address=?
            WHERE id=?
            """,
            (name, email, phone, company, address, int(supplier_id)),
        )

    def delete(self, supplier_id: int) -> None:
        self._db.execute("DELETE FROM suppliers WHERE id=?", (int(supplier_id),))

    def get(self, supplier_id: int) -> Optional[Supplier]:
        rows = self._db.query("SELECT * FROM suppliers WHERE id=?", (int(supplier_id),))
        if not rows:
            return None
        r = rows[0]
        return Supplier(
            id=int(r["id"]),
            name=str(r["name"]),
            email=r["email"],
            phone=str(r["phone"]),
            company=r["company"],
            address=r["address"],
            created_at=str(r["created_at"]),
        )

    def list(self, search: str = "") -> List[Supplier]:
        search = search.strip()
        if search:
            rows = self._db.query(
                """
                SELECT * FROM suppliers
                WHERE name LIKE ? OR phone LIKE ? OR company LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query("SELECT * FROM suppliers ORDER BY id DESC")
        out: List[Supplier] = []
        for r in rows:
            out.append(
                Supplier(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    email=r["email"],
                    phone=str(r["phone"]),
                    company=r["company"],
                    address=r["address"],
                    created_at=str(r["created_at"]),
                )
            )
        return out

    def count(self) -> int:
        rows = self._db.query("SELECT COUNT(*) AS c FROM suppliers")
        return int(rows[0]["c"]) if rows else 0


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str, description: Optional[str]) -> int:
        name = name.strip()
        description = description.strip() if description else None
        if not name:
            raise ValueError("Category name is required")
        cur = self._db.execute(
            """
            INSERT INTO categories (name, description, created_at)
            VALUES (?, ?, ?)
            """,
            (name, description, now_str()),
        )
        return int(cur.lastrowid)

    def update(self, category_id: int, name: str, description: Optional[str]) -> None:
        name = name.strip()
        description = description.strip() if description else None
        if not name:
            raise ValueError("Category name is required")
        self._db.execute(
            """
            UPDATE categories
            SET name=?, description=?
            WHERE id=?
            """,
            (name, description, int(category_id)),
        )

    def delete(self, category_id: int) -> None:
        self._db.execute("DELETE FROM categories WHERE id=?", (int(category_id),))

    def get(self, category_id: int) -> Optional[Category]:
        rows = self._db.query("SELECT * FROM categories WHERE id=?", (int(category_id),))
        if not rows:
            return None
        r = rows[0]
        return Category(
            id=int(r["id"]),
            name=str(r["name"]),
            description=r["description"],
            created_at=str(r["created_at"]),
        )

    def list(self, search: str = "") -> List[Category]:
        search = search.strip()
        if search:
            rows = self._db.query(
                """
                SELECT * FROM categories
                WHERE name LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search}%",),
            )
        else:
            rows = self._db.query("SELECT * FROM categories ORDER BY id DESC")
        out: List[Category] = []
        for r in rows:
            out.append(
                Category(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    description=r["description"],
                    created_at=str(r["created_at"]),
                )
            )
        return out

    def count(self) -> int:
        rows = self._db.query("SELECT COUNT(*) AS c FROM categories")
        return int(rows[0]["c"]) if rows else 0


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(
        self,
        name: str,
        category_id: int,
        supplier_id: Optional[int],
        price: float,
        qty: int,
        image_path: Optional[str],
    ) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Product name is required")
        category_id_i = int(category_id)
        supplier_id_i = int(supplier_id) if supplier_id not in (None, "", 0) else None
        price_f = float(price)
        qty_i = int(qty)
        if price_f < 0:
            raise ValueError("Price cannot be negative")
        if qty_i < 0:
            raise ValueError("Quantity cannot be negative")
        image_path_s = image_path.strip() if image_path else None
        if image_path_s and not os.path.exists(image_path_s):
            raise ValueError("Image path does not exist")

        cur = self._db.execute(
            """
            INSERT INTO products (name, category_id, supplier_id, price, qty, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category_id_i, supplier_id_i, price_f, qty_i, image_path_s, now_str()),
        )
        return int(cur.lastrowid)

    def update(
        self,
        product_id: int,
        name: str,
        category_id: int,
        supplier_id: Optional[int],
        price: float,
        qty: int,
        image_path: Optional[str],
    ) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Product name is required")
        category_id_i = int(category_id)
        supplier_id_i = int(supplier_id) if supplier_id not in (None, "", 0) else None
        price_f = float(price)
        qty_i = int(qty)
        if price_f < 0:
            raise ValueError("Price cannot be negative")
        if qty_i < 0:
            raise ValueError("Quantity cannot be negative")
        image_path_s = image_path.strip() if image_path else None
        if image_path_s and not os.path.exists(image_path_s):
            raise ValueError("Image path does not exist")

        self._db.execute(
            """
            UPDATE products
            SET name=?, category_id=?, supplier_id=?, price=?, qty=?, image_path=?
            WHERE id=?
            """,
            (name, category_id_i, supplier_id_i, price_f, qty_i, image_path_s, int(product_id)),
        )

    def delete(self, product_id: int) -> None:
        self._db.execute("DELETE FROM products WHERE id=?", (int(product_id),))

    def get(self, product_id: int) -> Optional[Product]:
        rows = self._db.query("SELECT * FROM products WHERE id=?", (int(product_id),))
        if not rows:
            return None
        r = rows[0]
        return Product(
            id=int(r["id"]),
            name=str(r["name"]),
            category_id=int(r["category_id"]),
            supplier_id=int(r["supplier_id"]) if r["supplier_id"] is not None else None,
            price=float(r["price"]),
            qty=int(r["qty"]),
            image_path=r["image_path"],
            created_at=str(r["created_at"]),
        )

    def list(self, search: str = "") -> List[Product]:
        search = search.strip()
        if search:
            rows = self._db.query(
                """
                SELECT * FROM products
                WHERE name LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search}%",),
            )
        else:
            rows = self._db.query("SELECT * FROM products ORDER BY id DESC")
        out: List[Product] = []
        for r in rows:
            out.append(
                Product(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    category_id=int(r["category_id"]),
                    supplier_id=int(r["supplier_id"]) if r["supplier_id"] is not None else None,
                    price=float(r["price"]),
                    qty=int(r["qty"]),
                    image_path=r["image_path"],
                    created_at=str(r["created_at"]),
                )
            )
        return out

    def count(self) -> int:
        rows = self._db.query("SELECT COUNT(*) AS c FROM products")
        return int(rows[0]["c"]) if rows else 0

    def adjust_stock(self, product_id: int, delta_qty: int) -> None:
        p = self.get(product_id)
        if p is None:
            raise ValueError("Product not found")
        new_qty = int(p.qty) + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self._db.execute("UPDATE products SET qty=? WHERE id=?", (new_qty, int(product_id)))

    def list_with_joins(self, search: str = "") -> List[Dict[str, Any]]:
        search = search.strip()
        if search:
            rows = self._db.query(
                """
                SELECT p.*, c.name AS category_name, s.name AS supplier_name
                FROM products p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN suppliers s ON s.id = p.supplier_id
                WHERE p.name LIKE ? OR c.name LIKE ? OR COALESCE(s.name,'') LIKE ?
                ORDER BY p.id DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query(
                """
                SELECT p.*, c.name AS category_name, s.name AS supplier_name
                FROM products p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN suppliers s ON s.id = p.supplier_id
                ORDER BY p.id DESC
                """
            )
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append({k: r[k] for k in r.keys()})
        return out


class BillingService:
    def __init__(self, db: Database, products: ProductRepository) -> None:
        self._db = db
        self._products = products

    def generate_invoice_no(self) -> str:
        base = datetime.now().strftime("%Y%m%d")
        rows = self._db.query(
            "SELECT invoice_no FROM invoices WHERE invoice_no LIKE ? ORDER BY invoice_no DESC LIMIT 1",
            (f"INV-{base}-%",),
        )
        if not rows:
            seq = 1
        else:
            last = str(rows[0]["invoice_no"])
            try:
                seq = int(last.split("-")[-1]) + 1
            except Exception:
                seq = 1
        return f"INV-{base}-{seq:04d}"

    def create_invoice(
        self,
        customer_name: Optional[str],
        customer_phone: Optional[str],
        items: List[InvoiceItem],
        discount: float = 0.0,
        tax: float = 0.0,
        notes: Optional[str] = None,
        invoice_no: Optional[str] = None,
    ) -> str:
        if not items:
            raise ValueError("At least one item is required")
        discount_f = float(discount or 0.0)
        tax_f = float(tax or 0.0)
        if discount_f < 0:
            raise ValueError("Discount cannot be negative")
        if tax_f < 0:
            raise ValueError("Tax cannot be negative")

        subtotal = sum(i.line_total for i in items)
        total = subtotal - discount_f + tax_f
        if total < 0:
            raise ValueError("Total cannot be negative")

        inv_no = invoice_no.strip() if invoice_no else self.generate_invoice_no()

        for it in items:
            if it.qty <= 0:
                raise ValueError("Item quantity must be positive")
            if it.price < 0:
                raise ValueError("Item price cannot be negative")
            if it.product_id is not None:
                p = self._products.get(int(it.product_id))
                if p is None:
                    raise ValueError("Product not found for an item")
                if p.qty < it.qty:
                    raise ValueError(f"Insufficient stock for {p.name}")

        self._db.execute(
            """
            INSERT INTO invoices (invoice_no, customer_name, customer_phone, created_at, subtotal, discount, tax, total, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inv_no,
                customer_name.strip() if customer_name else None,
                customer_phone.strip() if customer_phone else None,
                now_str(),
                float(subtotal),
                discount_f,
                tax_f,
                float(total),
                notes.strip() if notes else None,
            ),
        )

        for it in items:
            self._db.execute(
                """
                INSERT INTO invoice_items (invoice_no, product_id, product_name, price, qty, line_total)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (inv_no, int(it.product_id) if it.product_id is not None else None, it.product_name, float(it.price), int(it.qty), float(it.line_total)),
            )
            if it.product_id is not None:
                self._products.adjust_stock(int(it.product_id), -int(it.qty))

        return inv_no

    def get_invoice(self, invoice_no: str) -> Tuple[Optional[Invoice], List[sqlite3.Row]]:
        invoice_no = invoice_no.strip()
        rows = self._db.query("SELECT * FROM invoices WHERE invoice_no=?", (invoice_no,))
        if not rows:
            return None, []
        r = rows[0]
        inv = Invoice(
            invoice_no=str(r["invoice_no"]),
            customer_name=r["customer_name"],
            customer_phone=r["customer_phone"],
            created_at=str(r["created_at"]),
            subtotal=float(r["subtotal"]),
            discount=float(r["discount"]),
            tax=float(r["tax"]),
            total=float(r["total"]),
            notes=r["notes"],
        )
        items = self._db.query("SELECT * FROM invoice_items WHERE invoice_no=? ORDER BY id ASC", (invoice_no,))
        return inv, items

    def list_invoices(self, search: str = "") -> List[sqlite3.Row]:
        search = search.strip()
        if search:
            return self._db.query(
                """
                SELECT * FROM invoices
                WHERE invoice_no LIKE ? OR COALESCE(customer_name,'') LIKE ? OR COALESCE(customer_phone,'') LIKE ?
                ORDER BY created_at DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        return self._db.query("SELECT * FROM invoices ORDER BY created_at DESC")

    def count(self) -> int:
        rows = self._db.query("SELECT COUNT(*) AS c FROM invoices")
        return int(rows[0]["c"]) if rows else 0


class BaseManagerFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master)
        self._app = app

    def show_error(self, err: Exception) -> None:
        messagebox.showerror("Error", str(err))

    def show_info(self, msg: str) -> None:
        messagebox.showinfo("Info", msg)


class EmployeeFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self._repo = app.employees

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(9, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.search_var, width=30)
        ent.grid(row=0, column=1, sticky="w", padx=(5, 10))
        ttk.Button(top, text="Go", command=self.refresh).grid(row=0, column=2, sticky="w")
        ttk.Button(top, text="Clear", command=self._clear_search).grid(row=0, column=3, sticky="w", padx=(5, 0))

        form = ttk.LabelFrame(self, text="Employee Details")
        form.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        for i in range(8):
            form.columnconfigure(i, weight=1)

        self.emp_id_var = tk.StringVar(value="")
        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.gender_var = tk.StringVar()
        self.dob_var = tk.StringVar()
        self.doj_var = tk.StringVar()
        self.salary_var = tk.StringVar(value="0")
        self.address_var = tk.StringVar()

        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.emp_id_var, width=10, state="readonly").grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Email").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.email_var).grid(row=0, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Phone").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.phone_var).grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Gender").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.gender_cb = ttk.Combobox(form, textvariable=self.gender_var, values=["Male", "Female", "Other"], state="readonly")
        self.gender_cb.grid(row=1, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="DOB (YYYY-MM-DD)").grid(row=1, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.dob_var).grid(row=1, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="DOJ (YYYY-MM-DD)").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.doj_var).grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Salary").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.salary_var).grid(row=2, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Address").grid(row=2, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.address_var).grid(row=2, column=5, sticky="ew", padx=5, pady=5)

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=6, sticky="ew", padx=5, pady=8)
        ttk.Button(btns, text="Add", command=self.add).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete).pack(side="left")
        ttk.Button(btns, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)

        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("id", "name", "email", "phone", "gender", "dob", "doj", "salary", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=120, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("salary", width=90, anchor="e")
        self.tree.column("created_at", width=160, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.refresh()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for e in self._repo.list(self.search_var.get()):
            self.tree.insert(
                "",
                "end",
                values=(e.id, e.name, e.email, e.phone, e.gender, e.dob or "", e.doj or "", f"{e.salary:.2f}", e.created_at),
            )
        self._app.refresh_dashboard_counts()

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.emp_id_var.set(str(vals[0]))
        self.name_var.set(str(vals[1]))
        self.email_var.set(str(vals[2]))
        self.phone_var.set(str(vals[3]))
        self.gender_var.set(str(vals[4]))
        self.dob_var.set(str(vals[5]))
        self.doj_var.set(str(vals[6]))
        self.salary_var.set(str(vals[7]))
        self.address_var.set("")

        emp = self._repo.get(int(vals[0]))
        if emp and emp.address:
            self.address_var.set(emp.address)

    def clear_form(self) -> None:
        self.emp_id_var.set("")
        self.name_var.set("")
        self.email_var.set("")
        self.phone_var.set("")
        self.gender_var.set("")
        self.dob_var.set("")
        self.doj_var.set("")
        self.salary_var.set("0")
        self.address_var.set("")

    def add(self) -> None:
        try:
            self._repo.add(
                name=self.name_var.get(),
                email=self.email_var.get(),
                phone=self.phone_var.get(),
                gender=self.gender_var.get(),
                dob=self.dob_var.get().strip() or None,
                doj=self.doj_var.get().strip() or None,
                address=self.address_var.get().strip() or None,
                salary=float(self.salary_var.get() or 0),
            )
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)

    def update(self) -> None:
        try:
            if not self.emp_id_var.get().strip():
                raise ValueError("Select an employee to update")
            self._repo.update(
                emp_id=int(self.emp_id_var.get()),
                name=self.name_var.get(),
                email=self.email_var.get(),
                phone=self.phone_var.get(),
                gender=self.gender_var.get(),
                dob=self.dob_var.get().strip() or None,
                doj=self.doj_var.get().strip() or None,
                address=self.address_var.get().strip() or None,
                salary=float(self.salary_var.get() or 0),
            )
            self.refresh()
        except Exception as e:
            self.show_error(e)

    def delete(self) -> None:
        try:
            if not self.emp_id_var.get().strip():
                raise ValueError("Select an employee to delete")
            if not messagebox.askyesno("Confirm", "Delete selected employee?"):
                return
            self._repo.delete(int(self.emp_id_var.get()))
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)


class SupplierFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self._repo = app.suppliers

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(9, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.search_var, width=30).grid(row=0, column=1, sticky="w", padx=(5, 10))
        ttk.Button(top, text="Go", command=self.refresh).grid(row=0, column=2, sticky="w")
        ttk.Button(top, text="Clear", command=self._clear_search).grid(row=0, column=3, sticky="w", padx=(5, 0))

        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("id", "name", "phone", "email", "company", "address", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=140, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("created_at", width=160, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ttk.LabelFrame(self, text="Supplier Details")
        form.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        for i in range(6):
            form.columnconfigure(i, weight=1)

        self.supplier_id_var = tk.StringVar(value="")
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.company_var = tk.StringVar()
        self.address_var = tk.StringVar()

        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.supplier_id_var, width=10, state="readonly").grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Phone").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.phone_var).grid(row=0, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Email").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.email_var).grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Company").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.company_var).grid(row=1, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Address").grid(row=1, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.address_var).grid(row=1, column=5, sticky="ew", padx=5, pady=5)

        btns = ttk.Frame(form)
        btns.grid(row=2, column=0, columnspan=6, sticky="ew", padx=5, pady=8)
        ttk.Button(btns, text="Add", command=self.add).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete).pack(side="left")
        ttk.Button(btns, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)

        self.refresh()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in self._repo.list(self.search_var.get()):
            self.tree.insert("", "end", values=(s.id, s.name, s.phone, s.email or "", s.company or "", s.address or "", s.created_at))
        self._app.refresh_dashboard_counts()

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.supplier_id_var.set(str(vals[0]))
        self.name_var.set(str(vals[1]))
        self.phone_var.set(str(vals[2]))
        self.email_var.set(str(vals[3]))
        self.company_var.set(str(vals[4]))
        self.address_var.set(str(vals[5]))

    def clear_form(self) -> None:
        self.supplier_id_var.set("")
        self.name_var.set("")
        self.phone_var.set("")
        self.email_var.set("")
        self.company_var.set("")
        self.address_var.set("")

    def add(self) -> None:
        try:
            self._repo.add(
                name=self.name_var.get(),
                email=self.email_var.get().strip() or None,
                phone=self.phone_var.get(),
                company=self.company_var.get().strip() or None,
                address=self.address_var.get().strip() or None,
            )
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)

    def update(self) -> None:
        try:
            if not self.supplier_id_var.get().strip():
                raise ValueError("Select a supplier to update")
            self._repo.update(
                supplier_id=int(self.supplier_id_var.get()),
                name=self.name_var.get(),
                email=self.email_var.get().strip() or None,
                phone=self.phone_var.get(),
                company=self.company_var.get().strip() or None,
                address=self.address_var.get().strip() or None,
            )
            self.refresh()
        except Exception as e:
            self.show_error(e)

    def delete(self) -> None:
        try:
            if not self.supplier_id_var.get().strip():
                raise ValueError("Select a supplier to delete")
            if not messagebox.askyesno("Confirm", "Delete selected supplier?"):
                return
            self._repo.delete(int(self.supplier_id_var.get()))
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)


class CategoryFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self._repo = app.categories

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(9, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.search_var, width=30).grid(row=0, column=1, sticky="w", padx=(5, 10))
        ttk.Button(top, text="Go", command=self.refresh).grid(row=0, column=2, sticky="w")
        ttk.Button(top, text="Clear", command=self._clear_search).grid(row=0, column=3, sticky="w", padx=(5, 0))

        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("id", "name", "description", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=200, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("created_at", width=160, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ttk.LabelFrame(self, text="Category Details")
        form.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        for i in range(4):
            form.columnconfigure(i, weight=1)

        self.category_id_var = tk.StringVar(value="")
        self.name_var = tk.StringVar()
        self.desc_var = tk.StringVar()

        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.category_id_var, width=10, state="readonly").grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.desc_var).grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=5)

        btns = ttk.Frame(form)
        btns.grid(row=2, column=0, columnspan=4, sticky="ew", padx=5, pady=8)
        ttk.Button(btns, text="Add", command=self.add).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete).pack(side="left")
        ttk.Button(btns, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)

        self.refresh()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for c in self._repo.list(self.search_var.get()):
            self.tree.insert("", "end", values=(c.id, c.name, c.description or "", c.created_at))
        self._app.refresh_dashboard_counts()

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.category_id_var.set(str(vals[0]))
        self.name_var.set(str(vals[1]))
        self.desc_var.set(str(vals[2]))

    def clear_form(self) -> None:
        self.category_id_var.set("")
        self.name_var.set("")
        self.desc_var.set("")

    def add(self) -> None:
        try:
            self._repo.add(self.name_var.get(), self.desc_var.get().strip() or None)
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)

    def update(self) -> None:
        try:
            if not self.category_id_var.get().strip():
                raise ValueError("Select a category to update")
            self._repo.update(int(self.category_id_var.get()), self.name_var.get(), self.desc_var.get().strip() or None)
            self.refresh()
        except Exception as e:
            self.show_error(e)

    def delete(self) -> None:
        try:
            if not self.category_id_var.get().strip():
                raise ValueError("Select a category to delete")
            if not messagebox.askyesno("Confirm", "Delete selected category?"):
                return
            self._repo.delete(int(self.category_id_var.get()))
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)


class ProductFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self._repo = app.products
        self._cat_repo = app.categories
        self._sup_repo = app.suppliers

        self._image_preview_ref = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(9, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.search_var, width=30).grid(row=0, column=1, sticky="w", padx=(5, 10))
        ttk.Button(top, text="Go", command=self.refresh).grid(row=0, column=2, sticky="w")
        ttk.Button(top, text="Clear", command=self._clear_search).grid(row=0, column=3, sticky="w", padx=(5, 0))

        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("id", "name", "category", "supplier", "price", "qty", "image_path", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=140, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("price", width=90, anchor="e")
        self.tree.column("qty", width=70, anchor="e")
        self.tree.column("created_at", width=160, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ttk.LabelFrame(self, text="Product Details")
        form.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        for i in range(8):
            form.columnconfigure(i, weight=1)

        self.product_id_var = tk.StringVar(value="")
        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.price_var = tk.StringVar(value="0")
        self.qty_var = tk.StringVar(value="0")
        self.image_path_var = tk.StringVar(value="")

        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.product_id_var, width=10, state="readonly").grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Category").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.category_cb = ttk.Combobox(form, textvariable=self.category_var, state="readonly")
        self.category_cb.grid(row=0, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Supplier").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.supplier_cb = ttk.Combobox(form, textvariable=self.supplier_var, state="readonly")
        self.supplier_cb.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Price").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.price_var).grid(row=1, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Qty").grid(row=1, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(form, textvariable=self.qty_var).grid(row=1, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(form, text="Image").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        img_row = ttk.Frame(form)
        img_row.grid(row=2, column=1, columnspan=5, sticky="ew", padx=5, pady=5)
        img_row.columnconfigure(0, weight=1)
        ttk.Entry(img_row, textvariable=self.image_path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(img_row, text="Browse", command=self.browse_image).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(img_row, text="Preview", command=self.preview_image).grid(row=0, column=2, padx=(5, 0))

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=6, sticky="ew", padx=5, pady=8)
        ttk.Button(btns, text="Add", command=self.add).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete).pack(side="left")
        ttk.Button(btns, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)
        ttk.Button(btns, text="Refresh Lists", command=self._refresh_dropdowns).pack(side="left", padx=5)

        self._refresh_dropdowns()
        self.refresh()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.refresh()

    def _refresh_dropdowns(self) -> None:
        cats = self._cat_repo.list()
        sups = self._sup_repo.list()
        self._cat_map = {c.name: c.id for c in cats}
        self._sup_map = {s.name: s.id for s in sups}
        self.category_cb["values"] = list(self._cat_map.keys())
        self.supplier_cb["values"] = [""] + list(self._sup_map.keys())

    def refresh(self) -> None:
        self._refresh_dropdowns()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self._repo.list_with_joins(self.search_var.get()):
            self.tree.insert(
                "",
                "end",
                values=(
                    int(r["id"]),
                    str(r["name"]),
                    str(r["category_name"]),
                    str(r["supplier_name"] or ""),
                    f"{float(r['price']):.2f}",
                    int(r["qty"]),
                    str(r["image_path"] or ""),
                    str(r["created_at"]),
                ),
            )
        self._app.refresh_dashboard_counts()

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.product_id_var.set(str(vals[0]))
        self.name_var.set(str(vals[1]))
        self.category_var.set(str(vals[2]))
        self.supplier_var.set(str(vals[3]))
        self.price_var.set(str(vals[4]))
        self.qty_var.set(str(vals[5]))
        self.image_path_var.set(str(vals[6]))

    def clear_form(self) -> None:
        self.product_id_var.set("")
        self.name_var.set("")
        self.category_var.set("")
        self.supplier_var.set("")
        self.price_var.set("0")
        self.qty_var.set("0")
        self.image_path_var.set("")

    def browse_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")],
        )
        if path:
            self.image_path_var.set(path)

    def preview_image(self) -> None:
        path = self.image_path_var.get().strip()
        if not path:
            messagebox.showinfo("Preview", "No image selected")
            return
        if not os.path.exists(path):
            messagebox.showerror("Preview", "Image path does not exist")
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Preview", "PIL is not available")
            return
        try:
            win = tk.Toplevel(self)
            win.title("Image Preview")
            img = Image.open(path)
            img.thumbnail((400, 400))
            photo = ImageTk.PhotoImage(img)
            self._image_preview_ref = photo
            lbl = ttk.Label(win, image=photo)
            lbl.pack(padx=10, pady=10)
        except Exception as e:
            self.show_error(e)

    def add(self) -> None:
        try:
            if not self.category_var.get().strip():
                raise ValueError("Select a category")
            cat_id = self._cat_map.get(self.category_var.get().strip())
            if cat_id is None:
                raise ValueError("Invalid category")
            sup_name = self.supplier_var.get().strip()
            sup_id = self._sup_map.get(sup_name) if sup_name else None

            self._repo.add(
                name=self.name_var.get(),
                category_id=int(cat_id),
                supplier_id=int(sup_id) if sup_id is not None else None,
                price=float(self.price_var.get() or 0),
                qty=int(float(self.qty_var.get() or 0)),
                image_path=self.image_path_var.get().strip() or None,
            )
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)

    def update(self) -> None:
        try:
            if not self.product_id_var.get().strip():
                raise ValueError("Select a product to update")
            if not self.category_var.get().strip():
                raise ValueError("Select a category")
            cat_id = self._cat_map.get(self.category_var.get().strip())
            if cat_id is None:
                raise ValueError("Invalid category")
            sup_name = self.supplier_var.get().strip()
            sup_id = self._sup_map.get(sup_name) if sup_name else None

            self._repo.update(
                product_id=int(self.product_id_var.get()),
                name=self.name_var.get(),
                category_id=int(cat_id),
                supplier_id=int(sup_id) if sup_id is not None else None,
                price=float(self.price_var.get() or 0),
                qty=int(float(self.qty_var.get() or 0)),
                image_path=self.image_path_var.get().strip() or None,
            )
            self.refresh()
        except Exception as e:
            self.show_error(e)

    def delete(self) -> None:
        try:
            if not self.product_id_var.get().strip():
                raise ValueError("Select a product to delete")
            if not messagebox.askyesno("Confirm", "Delete selected product?"):
                return
            self._repo.delete(int(self.product_id_var.get()))
            self.refresh()
            self.clear_form()
        except Exception as e:
            self.show_error(e)


class BillingFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self._products = app.products
        self._billing = app.billing

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.LabelFrame(self, text="Billing")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for i in range(8):
            top.columnconfigure(i, weight=1)

        self.invoice_no_var = tk.StringVar(value="")
        self.customer_name_var = tk.StringVar()
        self.customer_phone_var = tk.StringVar()
        self.discount_var = tk.StringVar(value="0")
        self.tax_var = tk.StringVar(value="0")
        self.notes_var = tk.StringVar()

        ttk.Label(top, text="Invoice No").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        inv_row = ttk.Frame(top)
        inv_row.grid(row=0, column=1, columnspan=3, sticky="ew", padx=5, pady=5)
        inv_row.columnconfigure(0, weight=1)
        ttk.Entry(inv_row, textvariable=self.invoice_no_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(inv_row, text="Auto", command=self._set_auto_invoice).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(inv_row, text="Fetch", command=self.fetch_invoice).grid(row=0, column=2, padx=(5, 0))

        ttk.Label(top, text="Customer Name").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(top, textvariable=self.customer_name_var).grid(row=0, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(top, text="Customer Phone").grid(row=0, column=6, sticky="w", padx=5, pady=5)
        ttk.Entry(top, textvariable=self.customer_phone_var).grid(row=0, column=7, sticky="ew", padx=5, pady=5)

        add_item = ttk.LabelFrame(self, text="Add Item")
        add_item.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        add_item.columnconfigure(1, weight=1)
        add_item.columnconfigure(3, weight=1)
        add_item.columnconfigure(5, weight=1)
        add_item.rowconfigure(2, weight=1)

        self.product_search_var = tk.StringVar()
        ttk.Label(add_item, text="Search Product").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(add_item, textvariable=self.product_search_var).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(add_item, text="Find", command=self.refresh_products).grid(row=0, column=2, sticky="w", padx=5, pady=5)

        self.selected_product_var = tk.StringVar()
        ttk.Label(add_item, text="Product").grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.product_cb = ttk.Combobox(add_item, textvariable=self.selected_product_var, state="readonly")
        self.product_cb.grid(row=0, column=4, sticky="ew", padx=5, pady=5)

        self.item_qty_var = tk.StringVar(value="1")
        ttk.Label(add_item, text="Qty").grid(row=0, column=5, sticky="w", padx=5, pady=5)
        ttk.Entry(add_item, textvariable=self.item_qty_var, width=10).grid(row=0, column=6, sticky="w", padx=5, pady=5)

        ttk.Button(add_item, text="Add to Cart", command=self.add_to_cart).grid(row=0, column=7, sticky="w", padx=5, pady=5)

        cart_frame = ttk.Frame(add_item)
        cart_frame.grid(row=2, column=0, columnspan=8, sticky="nsew", padx=5, pady=5)
        cart_frame.rowconfigure(0, weight=1)
        cart_frame.columnconfigure(0, weight=1)

        cart_cols = ("product_id", "product_name", "price", "qty", "line_total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cart_cols, show="headings", selectmode="browse")
        for c in cart_cols:
            self.cart_tree.heading(c, text=c.upper())
            self.cart_tree.column(c, width=140, anchor="w")
        self.cart_tree.column("product_id", width=90, anchor="center")
        self.cart_tree.column("price", width=90, anchor="e")
        self.cart_tree.column("qty", width=70, anchor="e")
        self.cart_tree.column("line_total", width=110, anchor="e")

        vsb = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        hsb = ttk.Scrollbar(cart_frame, orient="horizontal", command=self.cart_tree.xview)
        self.cart_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        actions = ttk.Frame(add_item)
        actions.grid(row=3, column=0, columnspan=8, sticky="ew", padx=5, pady=5)
        ttk.Button(actions, text="Remove Selected", command=self.remove_selected).pack(side="left")
        ttk.Button(actions, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=5)

        totals = ttk.LabelFrame(self, text="Totals")
        totals.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        for i in range(8):
            totals.columnconfigure(i, weight=1)

        self.subtotal_var = tk.StringVar(value="0.00")
        self.total_var = tk.StringVar(value="0.00")

        ttk.Label(totals, text="Subtotal").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(totals, textvariable=self.subtotal_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(totals, text="Discount").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(totals, textvariable=self.discount_var).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        ttk.Label(totals, text="Tax").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(totals, textvariable=self.tax_var).grid(row=0, column=5, sticky="ew", padx=5, pady=5)

        ttk.Label(totals, text="Total").grid(row=0, column=6, sticky="w", padx=5, pady=5)
        ttk.Entry(totals, textvariable=self.total_var, state="readonly").grid(row=0, column=7, sticky="ew", padx=5, pady=5)

        ttk.Label(totals, text="Notes").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(totals, textvariable=self.notes_var).grid(row=1, column=1, columnspan=7, sticky="ew", padx=5, pady=5)

        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Save Invoice", command=self.save_invoice).pack(side="left")
        ttk.Button(bottom, text="New Invoice", command=self.new_invoice).pack(side="left", padx=5)
        ttk.Button(bottom, text="Print View", command=self.print_view).pack(side="left", padx=5)

        self._product_map: Dict[str, int] = {}
        self._set_auto_invoice()
        self.refresh_products()
        self._recalc_totals()

    def _set_auto_invoice(self) -> None:
        self.invoice_no_var.set(self._billing.generate_invoice_no())

    def refresh_products(self) -> None:
        search = self.product_search_var.get().strip()
        rows = self._products.list_with_joins(search)
        self._product_map = {}
        display: List[str] = []
        for r in rows:
            pid = int(r["id"])
            name = str(r["name"])
            qty = int(r["qty"])
            price = float(r["price"])
            label = f"{name} (ID:{pid}, Stock:{qty}, Price:{price:.2f})"
            self._product_map[label] = pid
            display.append(label)
        self.product_cb["values"] = display
        if display and not self.selected_product_var.get():
            self.selected_product_var.set(display[0])

    def _cart_items(self) -> List[InvoiceItem]:
        items: List[InvoiceItem] = []
        for iid in self.cart_tree.get_children():
            vals = self.cart_tree.item(iid, "values")
            pid_s = str(vals[0]).strip()
            pid = int(pid_s) if pid_s else None
            items.append(
                InvoiceItem(
                    product_id=pid,
                    product_name=str(vals[1]),
                    price=float(vals[2]),
                    qty=int(vals[3]),
                )
            )
        return items

    def _recalc_totals(self) -> None:
        items = self._cart_items()
        subtotal = sum(i.line_total for i in items)
        self.subtotal_var.set(f"{subtotal:.2f}")
        try:
            discount = float(self.discount_var.get() or 0)
        except Exception:
            discount = 0.0
        try:
            tax = float(self.tax_var.get() or 0)
        except Exception:
            tax = 0.0
        total = subtotal - discount + tax
        self.total_var.set(f"{total:.2f}")

    def add_to_cart(self) -> None:
        try:
            label = self.selected_product_var.get().strip()
            if not label:
                raise ValueError("Select a product")
            pid = self._product_map.get(label)
            if pid is None:
                raise ValueError("Invalid product selection")
            p = self._products.get(pid)
            if p is None:
                raise ValueError("Product not found")
            qty = int(float(self.item_qty_var.get() or 0))
            if qty <= 0:
                raise ValueError("Quantity must be positive")
            if p.qty < qty:
                raise ValueError("Insufficient stock")

            for iid in self.cart_tree.get_children():
                vals = self.cart_tree.item(iid, "values")
                if int(vals[0]) == pid:
                    new_qty = int(vals[3]) + qty
                    if p.qty < new_qty:
                        raise ValueError("Insufficient stock")
                    price = float(vals[2])
                    self.cart_tree.item(iid, values=(pid, p.name, f"{price:.2f}", new_qty, f"{price * new_qty:.2f}"))
                    self._recalc_totals()
                    return

            self.cart_tree.insert("", "end", values=(pid, p.name, f"{p.price:.2f}", qty, f"{p.price * qty:.2f}"))
            self._recalc_totals()
        except Exception as e:
            self.show_error(e)

    def remove_selected(self) -> None:
        sel = self.cart_tree.selection()
        if not sel:
            return
        self.cart_tree.delete(sel[0])
        self._recalc_totals()

    def clear_cart(self) -> None:
        for iid in self.cart_tree.get_children():
            self.cart_tree.delete(iid)
        self._recalc_totals()

    def new_invoice(self) -> None:
        self._set_auto_invoice()
        self.customer_name_var.set("")
        self.customer_phone_var.set("")
        self.discount_var.set("0")
        self.tax_var.set("0")
        self.notes_var.set("")
        self.clear_cart()

    def save_invoice(self) -> None:
        try:
            inv_no = self.invoice_no_var.get().strip() or None
            items = self._cart_items()
            discount = float(self.discount_var.get() or 0)
            tax = float(self.tax_var.get() or 0)
            saved_no = self._billing.create_invoice(
                customer_name=self.customer_name_var.get().strip() or None,
                customer_phone=self.customer_phone_var.get().strip() or None,
                items=items,
                discount=discount,
                tax=tax,
                notes=self.notes_var.get().strip() or None,
                invoice_no=inv_no,
            )
            self.show_info(f"Invoice saved: {saved_no}")
            self._app.refresh_dashboard_counts()
            self.refresh_products()
            self.new_invoice()
        except Exception as e:
            self.show_error(e)

    def fetch_invoice(self) -> None:
        try:
            inv_no = self.invoice_no_var.get().strip()
            if not inv_no:
                raise ValueError("Enter invoice number")
            inv, items = self._billing.get_invoice(inv_no)
            if inv is None:
                raise ValueError("Invoice not found")
            self.customer_name_var.set(inv.customer_name or "")
            self.customer_phone_var.set(inv.customer_phone or "")
            self.discount_var.set(f"{inv.discount:.2f}")
            self.tax_var.set(f"{inv.tax:.2f}")
            self.notes_var.set(inv.notes or "")

            self.clear_cart()
            for it in items:
                self.cart_tree.insert(
                    "",
                    "end",
                    values=(
                        it["product_id"] if it["product_id"] is not None else "",
                        it["product_name"],
                        f"{float(it['price']):.2f}",
                        int(it["qty"]),
                        f"{float(it['line_total']):.2f}",
                    ),
                )
            self._recalc_totals()
        except Exception as e:
            self.show_error(e)

    def print_view(self) -> None:
        try:
            inv_no = self.invoice_no_var.get().strip()
            if not inv_no:
                inv_no = "(unsaved)"
            win = tk.Toplevel(self)
            win.title(f"Invoice {inv_no}")
            win.geometry("700x500")
            txt = tk.Text(win, wrap="word")
            txt.pack(fill="both", expand=True)

            txt.insert("end", f"Invoice No: {inv_no}\n")
            txt.insert("end", f"Date/Time: {now_str()}\n")
            txt.insert("end", f"Customer: {self.customer_name_var.get().strip()}\n")
            txt.insert("end", f"Phone: {self.customer_phone_var.get().strip()}\n")
            txt.insert("end", "\nItems:\n")
            txt.insert("end", "-" * 70 + "\n")
            txt.insert("end", f"{'Product':30} {'Price':>10} {'Qty':>6} {'Total':>12}\n")
            txt.insert("end", "-" * 70 + "\n")
            for it in self._cart_items():
                txt.insert("end", f"{it.product_name[:30]:30} {it.price:>10.2f} {it.qty:>6d} {it.line_total:>12.2f}\n")
            txt.insert("end", "-" * 70 + "\n")
            txt.insert("end", f"Subtotal: {float(self.subtotal_var.get() or 0):.2f}\n")
            txt.insert("end", f"Discount: {float(self.discount_var.get() or 0):.2f}\n")
            txt.insert("end", f"Tax: {float(self.tax_var.get() or 0):.2f}\n")
            txt.insert("end", f"Total: {float(self.total_var.get() or 0):.2f}\n")
            notes = self.notes_var.get().strip()
            if notes:
                txt.insert("end", f"\nNotes:\n{notes}\n")
            txt.configure(state="disabled")
        except Exception as e:
            self.show_error(e)


class BillsFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self._billing = app.billing

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text="Search Invoice").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.search_var, width=30).grid(row=0, column=1, sticky="w", padx=(5, 10))
        ttk.Button(top, text="Go", command=self.refresh).grid(row=0, column=2, sticky="w")
        ttk.Button(top, text="Clear", command=self._clear_search).grid(row=0, column=3, sticky="w")

        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("invoice_no", "customer_name", "customer_phone", "created_at", "subtotal", "discount", "tax", "total")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=140, anchor="w")
        self.tree.column("invoice_no", width=140, anchor="w")
        self.tree.column("created_at", width=160, anchor="w")
        self.tree.column("subtotal", width=90, anchor="e")
        self.tree.column("discount", width=90, anchor="e")
        self.tree.column("tax", width=90, anchor="e")
        self.tree.column("total", width=90, anchor="e")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._open_invoice)

        bottom = ttk.Frame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(bottom, text="View Selected", command=self.view_selected).pack(side="left")

        self.refresh()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self._billing.list_invoices(self.search_var.get()):
            self.tree.insert(
                "",
                "end",
                values=(
                    r["invoice_no"],
                    r["customer_name"] or "",
                    r["customer_phone"] or "",
                    r["created_at"],
                    f"{float(r['subtotal']):.2f}",
                    f"{float(r['discount']):.2f}",
                    f"{float(r['tax']):.2f}",
                    f"{float(r['total']):.2f}",
                ),
            )
        self._app.refresh_dashboard_counts()

    def _selected_invoice_no(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return str(vals[0]) if vals else None

    def view_selected(self) -> None:
        inv_no = self._selected_invoice_no()
        if not inv_no:
            return
        self._show_invoice(inv_no)

    def _open_invoice(self, _evt: object) -> None:
        inv_no = self._selected_invoice_no()
        if not inv_no:
            return
        self._show_invoice(inv_no)

    def _show_invoice(self, invoice_no: str) -> None:
        try:
            inv, items = self._billing.get_invoice(invoice_no)
            if inv is None:
                raise ValueError("Invoice not found")
            win = tk.Toplevel(self)
            win.title(f"Invoice {invoice_no}")
            win.geometry("750x550")

            txt = tk.Text(win, wrap="word")
            txt.pack(fill="both", expand=True, padx=10, pady=10)

            txt.insert("end", f"Invoice No: {inv.invoice_no}\n")
            txt.insert("end", f"Created At: {inv.created_at}\n")
            txt.insert("end", f"Customer: {inv.customer_name or ''}\n")
            txt.insert("end", f"Phone: {inv.customer_phone or ''}\n")
            if inv.notes:
                txt.insert("end", f"Notes: {inv.notes}\n")
            txt.insert("end", "\nItems:\n")
            txt.insert("end", "-" * 70 + "\n")
            txt.insert("end", f"{'Product':30} {'Price':>10} {'Qty':>6} {'Total':>12}\n")
            txt.insert("end", "-" * 70 + "\n")
            for it in items:
                txt.insert(
                    "end",
                    f"{str(it['product_name'])[:30]:30} {float(it['price']):>10.2f} {int(it['qty']):>6d} {float(it['line_total']):>12.2f}\n",
                )
            txt.insert("end", "-" * 70 + "\n")
            txt.insert("end", f"Subtotal: {inv.subtotal:.2f}\n")
            txt.insert("end", f"Discount: {inv.discount:.2f}\n")
            txt.insert("end", f"Tax: {inv.tax:.2f}\n")
            txt.insert("end", f"Total: {inv.total:.2f}\n")
            txt.configure(state="disabled")
        except Exception as e:
            self.show_error(e)


class DashboardFrame(BaseManagerFrame):
    def __init__(self, master: tk.Misc, app: "InventoryApp") -> None:
        super().__init__(master, app)
        self.columnconfigure(0, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header.columnconfigure(1, weight=1)

        self.title_lbl = ttk.Label(header, text="Inventory Management System", font=("Arial", 18, "bold"))
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.time_var = tk.StringVar(value=now_str())
        self.time_lbl = ttk.Label(header, textvariable=self.time_var, font=("Arial", 11))
        self.time_lbl.grid(row=0, column=1, sticky="e")

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        for i in range(4):
            body.columnconfigure(i, weight=1)

        self.emp_count_var = tk.StringVar(value="0")
        self.sup_count_var = tk.StringVar(value="0")
        self.cat_count_var = tk.StringVar(value="0")
        self.prod_count_var = tk.StringVar(value="0")
        self.bill_count_var = tk.StringVar(value="0")

        self._make_card(body, 0, "Employees", self.emp_count_var, lambda: app.show_frame("employees"))
        self._make_card(body, 1, "Suppliers", self.sup_count_var, lambda: app.show_frame("suppliers"))
        self._make_card(body, 2, "Categories", self.cat_count_var, lambda: app.show_frame("categories"))
        self._make_card(body, 3, "Products", self.prod_count_var, lambda: app.show_frame("products"))

        body2 = ttk.Frame(self)
        body2.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        body2.columnconfigure(0, weight=1)
        body2.columnconfigure(1, weight=1)

        self._make_card(body2, 0, "Bills", self.bill_count_var, lambda: app.show_frame("bills"))
        billing_card = ttk.LabelFrame(body2, text="Billing")
        billing_card.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=0)
        ttk.Button(billing_card, text="Open Billing", command=lambda: app.show_frame("billing")).pack(fill="x", padx=10, pady=10)

        img_frame = ttk.LabelFrame(self, text="Image")
        img_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        img_frame.columnconfigure(0, weight=1)
        self._img_label = ttk.Label(img_frame, text="(No image loaded)")
        self._img_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        ttk.Button(img_frame, text="Load Image", command=self.load_image).grid(row=0, column=1, sticky="e", padx=10, pady=10)

        self._img_ref = None
        self._tick()

    def _make_card(self, parent: ttk.Frame, col: int, title: str, var: tk.StringVar, cmd) -> None:
        card = ttk.LabelFrame(parent, text=title)
        card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 10, 0), pady=0)
        lbl = ttk.Label(card, textvariable=var, font=("Arial", 20, "bold"))
        lbl.pack(padx=10, pady=(10, 0), anchor="w")
        ttk.Button(card, text=f"Manage {title}", command=cmd).pack(fill="x", padx=10, pady=10)

    def _tick(self) -> None:
        self.time_var.set(now_str())
        self.after(1000, self._tick)

    def load_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")],
        )
        if not path:
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Image", "PIL is not available")
            return
        try:
            img = Image.open(path)
            img.thumbnail((300, 200))
            photo = ImageTk.PhotoImage(img)
            self._img_ref = photo
            self._img_label.configure(image=photo, text="")
        except Exception as e:
            messagebox.showerror("Image", str(e))


class InventoryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x700")
        self.minsize(1000, 650)

        self.db = Database(DB_FILE)
        self.employees = EmployeeRepository(self.db)
        self.suppliers = SupplierRepository(self.db)
        self.categories = CategoryRepository(self.db)
        self.products = ProductRepository(self.db)
        self.billing = BillingService(self.db, self.products)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, padding=10)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="Menu", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(sidebar, text="Dashboard", command=lambda: self.show_frame("dashboard")).grid(row=1, column=0, sticky="ew", pady=3)
        ttk.Button(sidebar, text="Employees", command=lambda: self.show_frame("employees")).grid(row=2, column=0, sticky="ew", pady=3)
        ttk.Button(sidebar, text="Suppliers", command=lambda: self.show_frame("suppliers")).grid(row=3, column=0, sticky="ew", pady=3)
        ttk.Button(sidebar, text="Categories", command=lambda: self.show_frame("categories")).grid(row=4, column=0, sticky="ew", pady=3)
        ttk.Button(sidebar, text="Products", command=lambda: self.show_frame("products")).grid(row=5, column=0, sticky="ew", pady=3)
        ttk.Button(sidebar, text="Billing", command=lambda: self.show_frame("billing")).grid(row=6, column=0, sticky="ew", pady=3)
        ttk.Button(sidebar, text="Bills", command=lambda: self.show_frame("bills")).grid(row=7, column=0, sticky="ew", pady=3)

        ttk.Separator(sidebar, orient="horizontal").grid(row=8, column=0, sticky="ew", pady=10)
        ttk.Button(sidebar, text="Exit", command=self._on_close).grid(row=9, column=0, sticky="ew", pady=3)

        container = ttk.Frame(self)
        container.grid(row=0, column=1, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self._frames: Dict[str, ttk.Frame] = {}
        self._frames["dashboard"] = DashboardFrame(container, self)
        self._frames["employees"] = EmployeeFrame(container, self)
        self._frames["suppliers"] = SupplierFrame(container, self)
        self._frames["categories"] = CategoryFrame(container, self)
        self._frames["products"] = ProductFrame(container, self)
        self._frames["billing"] = BillingFrame(container, self)
        self._frames["bills"] = BillsFrame(container, self)

        for f in self._frames.values():
            f.grid(row=0, column=0, sticky="nsew")

        self.show_frame("dashboard")
        self.refresh_dashboard_counts()

    def show_frame(self, name: str) -> None:
        frame = self._frames.get(name)
        if frame is None:
            return
        frame.tkraise()
        if hasattr(frame, "refresh") and callable(getattr(frame, "refresh")):
            try:
                getattr(frame, "refresh")()
            except Exception:
                pass

    def refresh_dashboard_counts(self) -> None:
        dash = self._frames.get("dashboard")
        if not isinstance(dash, DashboardFrame):
            return
        dash.emp_count_var.set(str(self.employees.count()))
        dash.sup_count_var.set(str(self.suppliers.count()))
        dash.cat_count_var.set(str(self.categories.count()))
        dash.prod_count_var.set(str(self.products.count()))
        dash.bill_count_var.set(str(self.billing.count()))

    def _on_close(self) -> None:
        try:
            self.db.close()
        finally:
            self.destroy()


def main() -> None:
    app = InventoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()