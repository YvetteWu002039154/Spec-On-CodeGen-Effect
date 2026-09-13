import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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
                address TEXT NOT NULL,
                role TEXT NOT NULL,
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
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                company TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
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
                supplier_id INTEGER NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT,
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills (
                invoice_no TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                total REAL NOT NULL,
                tax REAL NOT NULL,
                grand_total REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(invoice_no) REFERENCES bills(invoice_no) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE RESTRICT
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

    def query_one(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()

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
    address: str
    role: str
    salary: float
    created_at: str


@dataclass(frozen=True)
class Supplier:
    id: int
    name: str
    email: str
    phone: str
    address: str
    company: str
    created_at: str


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    description: str
    created_at: str


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category_id: int
    supplier_id: int
    price: float
    qty: int
    status: str
    created_at: str


@dataclass(frozen=True)
class Bill:
    invoice_no: str
    customer_name: str
    customer_phone: str
    total: float
    tax: float
    grand_total: float
    created_at: str


@dataclass(frozen=True)
class BillItem:
    id: int
    invoice_no: str
    product_id: int
    product_name: str
    price: float
    qty: int
    line_total: float


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str, email: str, phone: str, address: str, role: str, salary: float) -> int:
        self._validate(name, email, phone, address, role, salary)
        cur = self._db.execute(
            """
            INSERT INTO employees(name,email,phone,address,role,salary,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (name.strip(), email.strip(), phone.strip(), address.strip(), role.strip(), float(salary), now_str()),
        )
        return int(cur.lastrowid)

    def update(self, emp_id: int, name: str, email: str, phone: str, address: str, role: str, salary: float) -> None:
        self._validate(name, email, phone, address, role, salary)
        self._db.execute(
            """
            UPDATE employees
            SET name=?, email=?, phone=?, address=?, role=?, salary=?
            WHERE id=?
            """,
            (name.strip(), email.strip(), phone.strip(), address.strip(), role.strip(), float(salary), int(emp_id)),
        )

    def delete(self, emp_id: int) -> None:
        self._db.execute("DELETE FROM employees WHERE id=?", (int(emp_id),))

    def list_all(self) -> List[Employee]:
        rows = self._db.query("SELECT * FROM employees ORDER BY id DESC")
        return [Employee(**dict(r)) for r in rows]

    def search(self, field: str, value: str) -> List[Employee]:
        if field not in {"name", "email", "phone", "role"}:
            field = "name"
        rows = self._db.query(f"SELECT * FROM employees WHERE {field} LIKE ? ORDER BY id DESC", (f"%{value}%",))
        return [Employee(**dict(r)) for r in rows]

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS c FROM employees")
        return int(row["c"]) if row else 0

    def _validate(self, name: str, email: str, phone: str, address: str, role: str, salary: float) -> None:
        if not name.strip():
            raise ValueError("Employee name is required")
        if not email.strip():
            raise ValueError("Employee email is required")
        if not phone.strip():
            raise ValueError("Employee phone is required")
        if not address.strip():
            raise ValueError("Employee address is required")
        if not role.strip():
            raise ValueError("Employee role is required")
        if float(salary) < 0:
            raise ValueError("Salary cannot be negative")


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str, email: str, phone: str, address: str, company: str) -> int:
        self._validate(name, email, phone, address, company)
        cur = self._db.execute(
            """
            INSERT INTO suppliers(name,email,phone,address,company,created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (name.strip(), email.strip(), phone.strip(), address.strip(), company.strip(), now_str()),
        )
        return int(cur.lastrowid)

    def update(self, supplier_id: int, name: str, email: str, phone: str, address: str, company: str) -> None:
        self._validate(name, email, phone, address, company)
        self._db.execute(
            """
            UPDATE suppliers
            SET name=?, email=?, phone=?, address=?, company=?
            WHERE id=?
            """,
            (name.strip(), email.strip(), phone.strip(), address.strip(), company.strip(), int(supplier_id)),
        )

    def delete(self, supplier_id: int) -> None:
        self._db.execute("DELETE FROM suppliers WHERE id=?", (int(supplier_id),))

    def list_all(self) -> List[Supplier]:
        rows = self._db.query("SELECT * FROM suppliers ORDER BY id DESC")
        return [Supplier(**dict(r)) for r in rows]

    def search(self, field: str, value: str) -> List[Supplier]:
        if field not in {"name", "email", "phone", "company"}:
            field = "name"
        rows = self._db.query(f"SELECT * FROM suppliers WHERE {field} LIKE ? ORDER BY id DESC", (f"%{value}%",))
        return [Supplier(**dict(r)) for r in rows]

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS c FROM suppliers")
        return int(row["c"]) if row else 0

    def _validate(self, name: str, email: str, phone: str, address: str, company: str) -> None:
        if not name.strip():
            raise ValueError("Supplier name is required")
        if not email.strip():
            raise ValueError("Supplier email is required")
        if not phone.strip():
            raise ValueError("Supplier phone is required")
        if not address.strip():
            raise ValueError("Supplier address is required")
        if not company.strip():
            raise ValueError("Supplier company is required")


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str, description: str) -> int:
        self._validate(name, description)
        cur = self._db.execute(
            """
            INSERT INTO categories(name,description,created_at)
            VALUES(?,?,?)
            """,
            (name.strip(), description.strip(), now_str()),
        )
        return int(cur.lastrowid)

    def update(self, category_id: int, name: str, description: str) -> None:
        self._validate(name, description)
        self._db.execute(
            """
            UPDATE categories
            SET name=?, description=?
            WHERE id=?
            """,
            (name.strip(), description.strip(), int(category_id)),
        )

    def delete(self, category_id: int) -> None:
        self._db.execute("DELETE FROM categories WHERE id=?", (int(category_id),))

    def list_all(self) -> List[Category]:
        rows = self._db.query("SELECT * FROM categories ORDER BY id DESC")
        return [Category(**dict(r)) for r in rows]

    def search(self, value: str) -> List[Category]:
        rows = self._db.query("SELECT * FROM categories WHERE name LIKE ? ORDER BY id DESC", (f"%{value}%",))
        return [Category(**dict(r)) for r in rows]

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS c FROM categories")
        return int(row["c"]) if row else 0

    def _validate(self, name: str, description: str) -> None:
        if not name.strip():
            raise ValueError("Category name is required")
        if not description.strip():
            raise ValueError("Category description is required")


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str, category_id: int, supplier_id: int, price: float, qty: int, status: str) -> int:
        self._validate(name, category_id, supplier_id, price, qty, status)
        cur = self._db.execute(
            """
            INSERT INTO products(name,category_id,supplier_id,price,qty,status,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (name.strip(), int(category_id), int(supplier_id), float(price), int(qty), status.strip(), now_str()),
        )
        return int(cur.lastrowid)

    def update(self, product_id: int, name: str, category_id: int, supplier_id: int, price: float, qty: int, status: str) -> None:
        self._validate(name, category_id, supplier_id, price, qty, status)
        self._db.execute(
            """
            UPDATE products
            SET name=?, category_id=?, supplier_id=?, price=?, qty=?, status=?
            WHERE id=?
            """,
            (name.strip(), int(category_id), int(supplier_id), float(price), int(qty), status.strip(), int(product_id)),
        )

    def delete(self, product_id: int) -> None:
        self._db.execute("DELETE FROM products WHERE id=?", (int(product_id),))

    def list_all(self) -> List[Product]:
        rows = self._db.query("SELECT * FROM products ORDER BY id DESC")
        return [Product(**dict(r)) for r in rows]

    def search(self, field: str, value: str) -> List[Product]:
        if field not in {"name", "status"}:
            field = "name"
        rows = self._db.query(f"SELECT * FROM products WHERE {field} LIKE ? ORDER BY id DESC", (f"%{value}%",))
        return [Product(**dict(r)) for r in rows]

    def get(self, product_id: int) -> Optional[Product]:
        row = self._db.query_one("SELECT * FROM products WHERE id=?", (int(product_id),))
        return Product(**dict(row)) if row else None

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS c FROM products")
        return int(row["c"]) if row else 0

    def adjust_stock(self, product_id: int, delta_qty: int) -> None:
        prod = self.get(product_id)
        if not prod:
            raise ValueError("Product not found")
        new_qty = int(prod.qty) + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self._db.execute("UPDATE products SET qty=? WHERE id=?", (new_qty, int(product_id)))

    def _validate(self, name: str, category_id: int, supplier_id: int, price: float, qty: int, status: str) -> None:
        if not name.strip():
            raise ValueError("Product name is required")
        if int(category_id) <= 0:
            raise ValueError("Category is required")
        if int(supplier_id) <= 0:
            raise ValueError("Supplier is required")
        if float(price) < 0:
            raise ValueError("Price cannot be negative")
        if int(qty) < 0:
            raise ValueError("Quantity cannot be negative")
        if status.strip() not in {"Active", "Inactive"}:
            raise ValueError("Status must be Active or Inactive")


class BillingRepository:
    def __init__(self, db: Database, products: ProductRepository) -> None:
        self._db = db
        self._products = products

    def create_bill(
        self,
        invoice_no: str,
        customer_name: str,
        customer_phone: str,
        items: List[Tuple[int, int]],
        tax_rate: float,
    ) -> Bill:
        invoice_no = invoice_no.strip()
        customer_name = customer_name.strip()
        customer_phone = customer_phone.strip()

        if not invoice_no:
            raise ValueError("Invoice number is required")
        if not customer_name:
            raise ValueError("Customer name is required")
        if not customer_phone:
            raise ValueError("Customer phone is required")
        if not items:
            raise ValueError("At least one item is required")
        if float(tax_rate) < 0:
            raise ValueError("Tax rate cannot be negative")

        existing = self._db.query_one("SELECT invoice_no FROM bills WHERE invoice_no=?", (invoice_no,))
        if existing:
            raise ValueError("Invoice number already exists")

        computed_items: List[Tuple[int, str, float, int, float]] = []
        total = 0.0

        for product_id, qty in items:
            qty_i = int(qty)
            if qty_i <= 0:
                raise ValueError("Item quantity must be positive")
            prod = self._products.get(int(product_id))
            if not prod:
                raise ValueError("Product not found")
            if prod.status != "Active":
                raise ValueError("Cannot bill inactive product")
            if prod.qty < qty_i:
                raise ValueError("Insufficient stock for product")
            line_total = float(prod.price) * qty_i
            total += line_total
            computed_items.append((prod.id, prod.name, float(prod.price), qty_i, line_total))

        tax = total * (float(tax_rate) / 100.0)
        grand_total = total + tax

        self._db.execute(
            """
            INSERT INTO bills(invoice_no,customer_name,customer_phone,total,tax,grand_total,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (invoice_no, customer_name, customer_phone, float(total), float(tax), float(grand_total), now_str()),
        )

        for pid, pname, price, qty_i, line_total in computed_items:
            self._db.execute(
                """
                INSERT INTO bill_items(invoice_no,product_id,product_name,price,qty,line_total)
                VALUES(?,?,?,?,?,?)
                """,
                (invoice_no, int(pid), pname, float(price), int(qty_i), float(line_total)),
            )
            self._products.adjust_stock(int(pid), -int(qty_i))

        row = self._db.query_one("SELECT * FROM bills WHERE invoice_no=?", (invoice_no,))
        return Bill(**dict(row)) if row else Bill(invoice_no, customer_name, customer_phone, total, tax, grand_total, now_str())

    def get_bill(self, invoice_no: str) -> Optional[Bill]:
        row = self._db.query_one("SELECT * FROM bills WHERE invoice_no=?", (invoice_no.strip(),))
        return Bill(**dict(row)) if row else None

    def get_bill_items(self, invoice_no: str) -> List[BillItem]:
        rows = self._db.query("SELECT * FROM bill_items WHERE invoice_no=? ORDER BY id ASC", (invoice_no.strip(),))
        return [BillItem(**dict(r)) for r in rows]

    def list_bills(self) -> List[Bill]:
        rows = self._db.query("SELECT * FROM bills ORDER BY created_at DESC")
        return [Bill(**dict(r)) for r in rows]

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS c FROM bills")
        return int(row["c"]) if row else 0


class ImageManager:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def load(self, path: str, size: Optional[Tuple[int, int]] = None) -> Optional[Any]:
        if not Image or not ImageTk:
            return None
        path = os.path.abspath(path)
        key = f"{path}|{size}"
        if key in self._cache:
            return self._cache[key]
        if not os.path.exists(path):
            return None
        img = Image.open(path)
        if size:
            img = img.resize(size)
        tk_img = ImageTk.PhotoImage(img)
        self._cache[key] = tk_img
        return tk_img


class BaseWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("1000x600")
        self.minsize(900, 550)
        self.transient(master)
        self.grab_set()

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class EmployeeWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: EmployeeRepository) -> None:
        super().__init__(master, "Employees")
        self._repo = repo
        self._selected_id: Optional[int] = None

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(frm, text="Employee Details", padding=10)
        form.pack(side=tk.TOP, fill=tk.X)

        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_role = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_address = tk.StringVar()

        r = 0
        ttk.Label(form, text="Name").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Email").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.var_email, width=30).grid(row=r, column=3, sticky="w", padx=5)

        r += 1
        ttk.Label(form, text="Phone").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_phone, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Role").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.var_role, width=30).grid(row=r, column=3, sticky="w", padx=5)

        r += 1
        ttk.Label(form, text="Salary").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_salary, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Address").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.var_address, width=30).grid(row=r, column=3, sticky="w", padx=5)

        btns = ttk.Frame(form)
        btns.grid(row=0, column=4, rowspan=3, sticky="ns", padx=10)
        ttk.Button(btns, text="Add", command=self._add).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Update", command=self._update).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Delete", command=self._delete).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Clear", command=self._clear).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Close", command=self.close).pack(fill=tk.X, pady=2)

        search = ttk.LabelFrame(frm, text="Search", padding=10)
        search.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["name", "email", "phone", "role"], width=12, state="readonly").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(frm)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "name", "email", "phone", "address", "role", "salary", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=120 if c != "address" else 200, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("salary", width=90, anchor="e")
        self.tree.column("created_at", width=150, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        self.var_name.set(values[1])
        self.var_email.set(values[2])
        self.var_phone.set(values[3])
        self.var_address.set(values[4])
        self.var_role.set(values[5])
        self.var_salary.set(values[6])

    def _clear(self) -> None:
        self._selected_id = None
        self.var_name.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_address.set("")
        self.var_role.set("")
        self.var_salary.set("")

    def _add(self) -> None:
        try:
            self._repo.add(
                self.var_name.get(),
                self.var_email.get(),
                self.var_phone.get(),
                self.var_address.get(),
                self.var_role.get(),
                safe_float(self.var_salary.get(), 0.0),
            )
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _update(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select an employee to update", parent=self)
            return
        try:
            self._repo.update(
                self._selected_id,
                self.var_name.get(),
                self.var_email.get(),
                self.var_phone.get(),
                self.var_address.get(),
                self.var_role.get(),
                safe_float(self.var_salary.get(), 0.0),
            )
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _delete(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select an employee to delete", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Delete selected employee?", parent=self):
            return
        try:
            self._repo.delete(self._selected_id)
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _search(self) -> None:
        try:
            rows = self._repo.search(self.var_search_by.get(), self.var_search_text.get())
            self._populate(rows)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _refresh(self) -> None:
        self._populate(self._repo.list_all())

    def _populate(self, employees: List[Employee]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for e in employees:
            self.tree.insert("", tk.END, values=(e.id, e.name, e.email, e.phone, e.address, e.role, f"{e.salary:.2f}", e.created_at))


class SupplierWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Suppliers")
        self._repo = repo
        self._selected_id: Optional[int] = None
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(frm, text="Supplier Details", padding=10)
        form.pack(side=tk.TOP, fill=tk.X)

        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_company = tk.StringVar()
        self.var_address = tk.StringVar()

        r = 0
        ttk.Label(form, text="Name").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Email").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.var_email, width=30).grid(row=r, column=3, sticky="w", padx=5)

        r += 1
        ttk.Label(form, text="Phone").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_phone, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Company").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.var_company, width=30).grid(row=r, column=3, sticky="w", padx=5)

        r += 1
        ttk.Label(form, text="Address").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_address, width=70).grid(row=r, column=1, columnspan=3, sticky="w", padx=5)

        btns = ttk.Frame(form)
        btns.grid(row=0, column=4, rowspan=3, sticky="ns", padx=10)
        ttk.Button(btns, text="Add", command=self._add).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Update", command=self._update).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Delete", command=self._delete).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Clear", command=self._clear).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Close", command=self.close).pack(fill=tk.X, pady=2)

        search = ttk.LabelFrame(frm, text="Search", padding=10)
        search.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["name", "email", "phone", "company"], width=12, state="readonly").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(frm)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "name", "email", "phone", "address", "company", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=140 if c != "address" else 220, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("created_at", width=150, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        self.var_name.set(values[1])
        self.var_email.set(values[2])
        self.var_phone.set(values[3])
        self.var_address.set(values[4])
        self.var_company.set(values[5])

    def _clear(self) -> None:
        self._selected_id = None
        self.var_name.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_address.set("")
        self.var_company.set("")

    def _add(self) -> None:
        try:
            self._repo.add(
                self.var_name.get(),
                self.var_email.get(),
                self.var_phone.get(),
                self.var_address.get(),
                self.var_company.get(),
            )
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _update(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a supplier to update", parent=self)
            return
        try:
            self._repo.update(
                self._selected_id,
                self.var_name.get(),
                self.var_email.get(),
                self.var_phone.get(),
                self.var_address.get(),
                self.var_company.get(),
            )
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _delete(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a supplier to delete", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Delete selected supplier?", parent=self):
            return
        try:
            self._repo.delete(self._selected_id)
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _search(self) -> None:
        try:
            rows = self._repo.search(self.var_search_by.get(), self.var_search_text.get())
            self._populate(rows)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _refresh(self) -> None:
        self._populate(self._repo.list_all())

    def _populate(self, suppliers: List[Supplier]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in suppliers:
            self.tree.insert("", tk.END, values=(s.id, s.name, s.email, s.phone, s.address, s.company, s.created_at))


class CategoryWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Categories")
        self._repo = repo
        self._selected_id: Optional[int] = None
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(frm, text="Category Details", padding=10)
        form.pack(side=tk.TOP, fill=tk.X)

        self.var_name = tk.StringVar()
        self.var_desc = tk.StringVar()

        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=40).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_desc, width=70).grid(row=1, column=1, sticky="w", padx=5)

        btns = ttk.Frame(form)
        btns.grid(row=0, column=2, rowspan=2, sticky="ns", padx=10)
        ttk.Button(btns, text="Add", command=self._add).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Update", command=self._update).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Delete", command=self._delete).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Clear", command=self._clear).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Close", command=self.close).pack(fill=tk.X, pady=2)

        search = ttk.LabelFrame(frm, text="Search", padding=10)
        search.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.var_search_text = tk.StringVar()
        ttk.Label(search, text="Name").pack(side=tk.LEFT)
        ttk.Entry(search, textvariable=self.var_search_text, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(frm)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "name", "description", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=200 if c == "description" else 150, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("created_at", width=150, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        self.var_name.set(values[1])
        self.var_desc.set(values[2])

    def _clear(self) -> None:
        self._selected_id = None
        self.var_name.set("")
        self.var_desc.set("")

    def _add(self) -> None:
        try:
            self._repo.add(self.var_name.get(), self.var_desc.get())
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _update(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a category to update", parent=self)
            return
        try:
            self._repo.update(self._selected_id, self.var_name.get(), self.var_desc.get())
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _delete(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a category to delete", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Delete selected category?", parent=self):
            return
        try:
            self._repo.delete(self._selected_id)
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _search(self) -> None:
        try:
            rows = self._repo.search(self.var_search_text.get())
            self._populate(rows)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _refresh(self) -> None:
        self._populate(self._repo.list_all())

    def _populate(self, categories: List[Category]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for c in categories:
            self.tree.insert("", tk.END, values=(c.id, c.name, c.description, c.created_at))


class ProductWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, categories: CategoryRepository, suppliers: SupplierRepository) -> None:
        super().__init__(master, "Products")
        self._repo = repo
        self._categories = categories
        self._suppliers = suppliers
        self._selected_id: Optional[int] = None
        self._build_ui()
        self._load_dropdowns()
        self._refresh()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(frm, text="Product Details", padding=10)
        form.pack(side=tk.TOP, fill=tk.X)

        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar(value="Active")

        r = 0
        ttk.Label(form, text="Name").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Category").grid(row=r, column=2, sticky="w")
        self.cmb_category = ttk.Combobox(form, textvariable=self.var_category, width=28, state="readonly")
        self.cmb_category.grid(row=r, column=3, sticky="w", padx=5)

        r += 1
        ttk.Label(form, text="Supplier").grid(row=r, column=0, sticky="w")
        self.cmb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, width=28, state="readonly")
        self.cmb_supplier.grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Price").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.var_price, width=30).grid(row=r, column=3, sticky="w", padx=5)

        r += 1
        ttk.Label(form, text="Quantity").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_qty, width=30).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Status").grid(row=r, column=2, sticky="w")
        ttk.Combobox(form, textvariable=self.var_status, values=["Active", "Inactive"], width=28, state="readonly").grid(row=r, column=3, sticky="w", padx=5)

        btns = ttk.Frame(form)
        btns.grid(row=0, column=4, rowspan=3, sticky="ns", padx=10)
        ttk.Button(btns, text="Add", command=self._add).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Update", command=self._update).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Delete", command=self._delete).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Clear", command=self._clear).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Reload Lists", command=self._load_dropdowns).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Close", command=self.close).pack(fill=tk.X, pady=2)

        search = ttk.LabelFrame(frm, text="Search", padding=10)
        search.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["name", "status"], width=12, state="readonly").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(frm)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "name", "category_id", "supplier_id", "price", "qty", "status", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=120, anchor="w")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("price", width=90, anchor="e")
        self.tree.column("qty", width=80, anchor="e")
        self.tree.column("created_at", width=150, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _load_dropdowns(self) -> None:
        cats = self._categories.list_all()
        sups = self._suppliers.list_all()
        self._cat_map: Dict[str, int] = {f"{c.id} - {c.name}": c.id for c in cats}
        self._sup_map: Dict[str, int] = {f"{s.id} - {s.name}": s.id for s in sups}
        self.cmb_category["values"] = list(self._cat_map.keys())
        self.cmb_supplier["values"] = list(self._sup_map.keys())
        if self.cmb_category["values"] and not self.var_category.get():
            self.var_category.set(self.cmb_category["values"][0])
        if self.cmb_supplier["values"] and not self.var_supplier.get():
            self.var_supplier.set(self.cmb_supplier["values"][0])

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        self.var_name.set(values[1])
        cat_id = int(values[2])
        sup_id = int(values[3])
        self.var_price.set(values[4])
        self.var_qty.set(values[5])
        self.var_status.set(values[6])

        cat_key = next((k for k, v in self._cat_map.items() if v == cat_id), "")
        sup_key = next((k for k, v in self._sup_map.items() if v == sup_id), "")
        if cat_key:
            self.var_category.set(cat_key)
        if sup_key:
            self.var_supplier.set(sup_key)

    def _clear(self) -> None:
        self._selected_id = None
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("Active")

    def _add(self) -> None:
        try:
            cat_id = self._cat_map.get(self.var_category.get(), 0)
            sup_id = self._sup_map.get(self.var_supplier.get(), 0)
            self._repo.add(
                self.var_name.get(),
                cat_id,
                sup_id,
                safe_float(self.var_price.get(), 0.0),
                safe_int(self.var_qty.get(), 0),
                self.var_status.get(),
            )
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _update(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a product to update", parent=self)
            return
        try:
            cat_id = self._cat_map.get(self.var_category.get(), 0)
            sup_id = self._sup_map.get(self.var_supplier.get(), 0)
            self._repo.update(
                self._selected_id,
                self.var_name.get(),
                cat_id,
                sup_id,
                safe_float(self.var_price.get(), 0.0),
                safe_int(self.var_qty.get(), 0),
                self.var_status.get(),
            )
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _delete(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a product to delete", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Delete selected product?", parent=self):
            return
        try:
            self._repo.delete(self._selected_id)
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _search(self) -> None:
        try:
            rows = self._repo.search(self.var_search_by.get(), self.var_search_text.get())
            self._populate(rows)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _refresh(self) -> None:
        self._populate(self._repo.list_all())

    def _populate(self, products: List[Product]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in products:
            self.tree.insert(
                "",
                tk.END,
                values=(p.id, p.name, p.category_id, p.supplier_id, f"{p.price:.2f}", p.qty, p.status, p.created_at),
            )


class BillViewerWindow(BaseWindow):
    def __init__(self, master: tk.Tk, billing: BillingRepository) -> None:
        super().__init__(master, "Bills")
        self._billing = billing
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        top = ttk.LabelFrame(frm, text="Find Bill by Invoice No", padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        self.var_invoice = tk.StringVar()
        ttk.Label(top, text="Invoice No").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.var_invoice, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Fetch", command=self._fetch).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Show All", command=self._refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Close", command=self.close).pack(side=tk.RIGHT)

        mid = ttk.Frame(frm)
        mid.pack(fill=tk.BOTH, expand=True, pady=10)

        left = ttk.LabelFrame(mid, text="Bills", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cols = ("invoice_no", "customer_name", "customer_phone", "total", "tax", "grand_total", "created_at")
        self.tree = ttk.Treeview(left, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=140, anchor="w")
        self.tree.column("total", width=90, anchor="e")
        self.tree.column("tax", width=90, anchor="e")
        self.tree.column("grand_total", width=110, anchor="e")
        self.tree.column("created_at", width=150, anchor="w")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        right = ttk.LabelFrame(mid, text="Bill Items", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        cols2 = ("product_id", "product_name", "price", "qty", "line_total")
        self.tree_items = ttk.Treeview(right, columns=cols2, show="headings")
        for c in cols2:
            self.tree_items.heading(c, text=c.replace("_", " ").title())
            self.tree_items.column(c, width=140, anchor="w")
        self.tree_items.column("price", width=90, anchor="e")
        self.tree_items.column("qty", width=70, anchor="e")
        self.tree_items.column("line_total", width=110, anchor="e")

        vsb2 = ttk.Scrollbar(right, orient="vertical", command=self.tree_items.yview)
        hsb2 = ttk.Scrollbar(right, orient="horizontal", command=self.tree_items.xview)
        self.tree_items.configure(yscroll=vsb2.set, xscroll=hsb2.set)

        self.tree_items.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)
        hsb2.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_bill_select)

    def _on_bill_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        invoice_no = self.tree.item(sel[0], "values")[0]
        self._show_items(invoice_no)

    def _show_items(self, invoice_no: str) -> None:
        for i in self.tree_items.get_children():
            self.tree_items.delete(i)
        items = self._billing.get_bill_items(invoice_no)
        for it in items:
            self.tree_items.insert("", tk.END, values=(it.product_id, it.product_name, f"{it.price:.2f}", it.qty, f"{it.line_total:.2f}"))

    def _fetch(self) -> None:
        inv = self.var_invoice.get().strip()
        if not inv:
            messagebox.showwarning("Invoice", "Enter invoice number", parent=self)
            return
        bill = self._billing.get_bill(inv)
        if not bill:
            messagebox.showinfo("Not Found", "No bill found for invoice number", parent=self)
            return
        self._populate([bill])
        self._show_items(inv)

    def _refresh(self) -> None:
        self._populate(self._billing.list_bills())
        for i in self.tree_items.get_children():
            self.tree_items.delete(i)

    def _populate(self, bills: List[Bill]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for b in bills:
            self.tree.insert(
                "",
                tk.END,
                values=(b.invoice_no, b.customer_name, b.customer_phone, f"{b.total:.2f}", f"{b.tax:.2f}", f"{b.grand_total:.2f}", b.created_at),
            )


class BillingWindow(BaseWindow):
    def __init__(self, master: tk.Tk, products: ProductRepository, billing: BillingRepository) -> None:
        super().__init__(master, "Billing")
        self._products = products
        self._billing = billing
        self._cart: List[Tuple[int, str, float, int, float]] = []
        self._build_ui()
        self._refresh_products()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        top = ttk.LabelFrame(frm, text="Customer & Invoice", padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        self.var_invoice = tk.StringVar()
        self.var_customer = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_tax = tk.StringVar(value="0")

        ttk.Label(top, text="Invoice No").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.var_invoice, width=20).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(top, text="Customer Name").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.var_customer, width=25).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Label(top, text="Customer Phone").grid(row=0, column=4, sticky="w")
        ttk.Entry(top, textvariable=self.var_phone, width=20).grid(row=0, column=5, sticky="w", padx=5)
        ttk.Label(top, text="Tax %").grid(row=0, column=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_tax, width=8).grid(row=0, column=7, sticky="w", padx=5)

        mid = ttk.Frame(frm)
        mid.pack(fill=tk.BOTH, expand=True, pady=10)

        left = ttk.LabelFrame(mid, text="Products", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.var_prod_search = tk.StringVar()
        ttk.Label(left, text="Search Name").pack(side=tk.TOP, anchor="w")
        srow = ttk.Frame(left)
        srow.pack(side=tk.TOP, fill=tk.X, pady=5)
        ttk.Entry(srow, textvariable=self.var_prod_search).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(srow, text="Search", command=self._search_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(srow, text="Show All", command=self._refresh_products).pack(side=tk.LEFT)

        cols = ("id", "name", "price", "qty", "status")
        self.tree_prod = ttk.Treeview(left, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree_prod.heading(c, text=c.title())
            self.tree_prod.column(c, width=120, anchor="w")
        self.tree_prod.column("id", width=60, anchor="center")
        self.tree_prod.column("price", width=90, anchor="e")
        self.tree_prod.column("qty", width=70, anchor="e")
        self.tree_prod.column("status", width=90, anchor="w")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree_prod.yview)
        self.tree_prod.configure(yscroll=vsb.set)
        self.tree_prod.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        addfrm = ttk.Frame(left)
        addfrm.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        self.var_add_qty = tk.StringVar(value="1")
        ttk.Label(addfrm, text="Qty").pack(side=tk.LEFT)
        ttk.Entry(addfrm, textvariable=self.var_add_qty, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(addfrm, text="Add to Cart", command=self._add_to_cart).pack(side=tk.LEFT, padx=5)

        right = ttk.LabelFrame(mid, text="Cart", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        cols2 = ("product_id", "product_name", "price", "qty", "line_total")
        self.tree_cart = ttk.Treeview(right, columns=cols2, show="headings", height=12)
        for c in cols2:
            self.tree_cart.heading(c, text=c.replace("_", " ").title())
            self.tree_cart.column(c, width=140, anchor="w")
        self.tree_cart.column("price", width=90, anchor="e")
        self.tree_cart.column("qty", width=70, anchor="e")
        self.tree_cart.column("line_total", width=110, anchor="e")

        vsb2 = ttk.Scrollbar(right, orient="vertical", command=self.tree_cart.yview)
        self.tree_cart.configure(yscroll=vsb2.set)
        self.tree_cart.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)

        cartbtns = ttk.Frame(right)
        cartbtns.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        ttk.Button(cartbtns, text="Remove Selected", command=self._remove_selected).pack(side=tk.LEFT)
        ttk.Button(cartbtns, text="Clear Cart", command=self._clear_cart).pack(side=tk.LEFT, padx=5)

        bottom = ttk.LabelFrame(frm, text="Totals & Actions", padding=10)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        self.var_total = tk.StringVar(value="0.00")
        self.var_tax_amt = tk.StringVar(value="0.00")
        self.var_grand = tk.StringVar(value="0.00")

        ttk.Label(bottom, text="Total").grid(row=0, column=0, sticky="w")
        ttk.Label(bottom, textvariable=self.var_total, width=12).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(bottom, text="Tax").grid(row=0, column=2, sticky="w")
        ttk.Label(bottom, textvariable=self.var_tax_amt, width=12).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Label(bottom, text="Grand Total").grid(row=0, column=4, sticky="w")
        ttk.Label(bottom, textvariable=self.var_grand, width=12).grid(row=0, column=5, sticky="w", padx=5)

        ttk.Button(bottom, text="Generate Bill", command=self._generate_bill).grid(row=0, column=6, padx=10)
        ttk.Button(bottom, text="Close", command=self.close).grid(row=0, column=7, padx=5)

        self.var_tax.trace_add("write", lambda *_: self._recalc_totals())

    def _refresh_products(self) -> None:
        prods = [p for p in self._products.list_all() if p.status == "Active"]
        self._populate_products(prods)

    def _search_products(self) -> None:
        txt = self.var_prod_search.get().strip()
        if not txt:
            self._refresh_products()
            return
        prods = [p for p in self._products.search("name", txt) if p.status == "Active"]
        self._populate_products(prods)

    def _populate_products(self, products: List[Product]) -> None:
        for i in self.tree_prod.get_children():
            self.tree_prod.delete(i)
        for p in products:
            self.tree_prod.insert("", tk.END, values=(p.id, p.name, f"{p.price:.2f}", p.qty, p.status))

    def _add_to_cart(self) -> None:
        sel = self.tree_prod.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a product to add", parent=self)
            return
        values = self.tree_prod.item(sel[0], "values")
        pid = int(values[0])
        pname = str(values[1])
        price = safe_float(str(values[2]), 0.0)
        stock = safe_int(str(values[3]), 0)
        qty = safe_int(self.var_add_qty.get(), 1)
        if qty <= 0:
            messagebox.showerror("Qty", "Quantity must be positive", parent=self)
            return
        if qty > stock:
            messagebox.showerror("Stock", "Insufficient stock", parent=self)
            return

        for idx, (cpid, _, cprice, cqty, _) in enumerate(self._cart):
            if cpid == pid:
                new_qty = cqty + qty
                if new_qty > stock:
                    messagebox.showerror("Stock", "Insufficient stock", parent=self)
                    return
                line_total = cprice * new_qty
                self._cart[idx] = (cpid, pname, cprice, new_qty, line_total)
                self._populate_cart()
                self._recalc_totals()
                return

        line_total = price * qty
        self._cart.append((pid, pname, price, qty, line_total))
        self._populate_cart()
        self._recalc_totals()

    def _populate_cart(self) -> None:
        for i in self.tree_cart.get_children():
            self.tree_cart.delete(i)
        for pid, pname, price, qty, lt in self._cart:
            self.tree_cart.insert("", tk.END, values=(pid, pname, f"{price:.2f}", qty, f"{lt:.2f}"))

    def _remove_selected(self) -> None:
        sel = self.tree_cart.selection()
        if not sel:
            return
        values = self.tree_cart.item(sel[0], "values")
        pid = int(values[0])
        self._cart = [c for c in self._cart if c[0] != pid]
        self._populate_cart()
        self._recalc_totals()

    def _clear_cart(self) -> None:
        self._cart = []
        self._populate_cart()
        self._recalc_totals()

    def _recalc_totals(self) -> None:
        total = sum(lt for *_rest, lt in self._cart)
        tax_rate = safe_float(self.var_tax.get(), 0.0)
        if tax_rate < 0:
            tax_rate = 0.0
        tax_amt = total * (tax_rate / 100.0)
        grand = total + tax_amt
        self.var_total.set(f"{total:.2f}")
        self.var_tax_amt.set(f"{tax_amt:.2f}")
        self.var_grand.set(f"{grand:.2f}")

    def _generate_bill(self) -> None:
        try:
            items = [(pid, qty) for pid, _n, _p, qty, _lt in self._cart]
            bill = self._billing.create_bill(
                self.var_invoice.get(),
                self.var_customer.get(),
                self.var_phone.get(),
                items,
                safe_float(self.var_tax.get(), 0.0),
            )
            messagebox.showinfo("Bill Generated", f"Bill saved.\nInvoice: {bill.invoice_no}\nGrand Total: {bill.grand_total:.2f}", parent=self)
            self._clear_cart()
            self._refresh_products()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._db = Database(DB_FILE)
        self._employees = EmployeeRepository(self._db)
        self._suppliers = SupplierRepository(self._db)
        self._categories = CategoryRepository(self._db)
        self._products = ProductRepository(self._db)
        self._billing = BillingRepository(self._db, self._products)
        self._images = ImageManager()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._tick()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(side=tk.TOP, fill=tk.X)

        self.lbl_title = ttk.Label(header, text="Inventory Management System", font=("Arial", 20, "bold"))
        self.lbl_title.pack(side=tk.LEFT)

        self.lbl_time = ttk.Label(header, text="", font=("Arial", 11))
        self.lbl_time.pack(side=tk.RIGHT)

        body = ttk.Frame(root)
        body.pack(fill=tk.BOTH, expand=True, pady=10)

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y)

        btn_style = {"width": 22}
        ttk.Button(left, text="Employees", command=self._open_employees, **btn_style).pack(pady=5, fill=tk.X)
        ttk.Button(left, text="Suppliers", command=self._open_suppliers, **btn_style).pack(pady=5, fill=tk.X)
        ttk.Button(left, text="Categories", command=self._open_categories, **btn_style).pack(pady=5, fill=tk.X)
        ttk.Button(left, text="Products", command=self._open_products, **btn_style).pack(pady=5, fill=tk.X)
        ttk.Button(left, text="Billing", command=self._open_billing, **btn_style).pack(pady=5, fill=tk.X)
        ttk.Button(left, text="Bills (View)", command=self._open_bills, **btn_style).pack(pady=5, fill=tk.X)

        ttk.Separator(left, orient="horizontal").pack(fill=tk.X, pady=10)
        ttk.Button(left, text="Load Logo Image", command=self._load_logo, **btn_style).pack(pady=5, fill=tk.X)
        ttk.Button(left, text="Exit", command=self._on_close, **btn_style).pack(pady=5, fill=tk.X)

        right = ttk.Frame(body)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        self.logo_label = ttk.Label(right, text="No image loaded", anchor="center")
        self.logo_label.pack(side=tk.TOP, fill=tk.X, pady=5)

        stats = ttk.LabelFrame(right, text="Dashboard", padding=10)
        stats.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.var_emp = tk.StringVar(value="0")
        self.var_sup = tk.StringVar(value="0")
        self.var_cat = tk.StringVar(value="0")
        self.var_prod = tk.StringVar(value="0")
        self.var_bill = tk.StringVar(value="0")

        self._stat_row(stats, 0, "Employees", self.var_emp)
        self._stat_row(stats, 1, "Suppliers", self.var_sup)
        self._stat_row(stats, 2, "Categories", self.var_cat)
        self._stat_row(stats, 3, "Products", self.var_prod)
        self._stat_row(stats, 4, "Bills", self.var_bill)

        info = ttk.LabelFrame(right, text="Info", padding=10)
        info.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.txt_info = tk.Text(info, height=10, wrap="word")
        self.txt_info.pack(fill=tk.BOTH, expand=True)
        self.txt_info.insert(
            "1.0",
            "This Inventory Management System provides:\n"
            "- Employee data management\n"
            "- Supplier data management\n"
            "- Product and category management\n"
            "- Billing and bill storage by invoice number\n"
            "- Dashboard with time and counts\n",
        )
        self.txt_info.configure(state="disabled")

        self._logo_img: Optional[Any] = None

    def _stat_row(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=label, font=("Arial", 11, "bold")).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Label(parent, textvariable=var, font=("Arial", 11)).grid(row=row, column=1, sticky="e", pady=3)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)

    def _tick(self) -> None:
        self.lbl_time.configure(text=f"{today_str()}  {datetime.now().strftime('%H:%M:%S')}")
        self._refresh_counts()
        self.after(1000, self._tick)

    def _refresh_counts(self) -> None:
        try:
            self.var_emp.set(str(self._employees.count()))
            self.var_sup.set(str(self._suppliers.count()))
            self.var_cat.set(str(self._categories.count()))
            self.var_prod.set(str(self._products.count()))
            self.var_bill.set(str(self._billing.count()))
        except Exception:
            pass

    def _open_employees(self) -> None:
        EmployeeWindow(self, self._employees)

    def _open_suppliers(self) -> None:
        SupplierWindow(self, self._suppliers)

    def _open_categories(self) -> None:
        CategoryWindow(self, self._categories)

    def _open_products(self) -> None:
        ProductWindow(self, self._products, self._categories, self._suppliers)

    def _open_billing(self) -> None:
        BillingWindow(self, self._products, self._billing)

    def _open_bills(self) -> None:
        BillViewerWindow(self, self._billing)

    def _load_logo(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")],
        )
        if not path:
            return
        if not Image or not ImageTk:
            messagebox.showerror("PIL Missing", "Pillow (PIL) is required to load images.", parent=self)
            return
        img = self._images.load(path, size=(700, 220))
        if not img:
            messagebox.showerror("Error", "Unable to load image.", parent=self)
            return
        self._logo_img = img
        self.logo_label.configure(image=self._logo_img, text="")

    def _on_close(self) -> None:
        try:
            self._db.close()
        finally:
            self.destroy()


def main() -> None:
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()