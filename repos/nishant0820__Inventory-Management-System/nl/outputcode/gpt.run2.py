import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


DB_FILE = "inventory.db"


class Database:
    def __init__(self, db_path: str = DB_FILE) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self.conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sup_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category_id INTEGER,
                supplier_id INTEGER,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL,
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                created_at TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                sku TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
            )
            """
        )

        self.conn.commit()

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


@dataclass(frozen=True)
class Employee:
    emp_id: str
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""


@dataclass(frozen=True)
class Supplier:
    sup_id: str
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""


@dataclass(frozen=True)
class Category:
    name: str
    description: str = ""


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category_id: Optional[int]
    supplier_id: Optional[int]
    price: float
    quantity: int
    image_path: str = ""


@dataclass(frozen=True)
class InvoiceItem:
    product_id: Optional[int]
    sku: str
    name: str
    price: float
    quantity: int

    @property
    def line_total(self) -> float:
        return float(self.price) * int(self.quantity)


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, employee: Employee) -> None:
        if not employee.emp_id.strip() or not employee.name.strip():
            raise ValueError("Employee ID and Name are required.")
        now = datetime.now().isoformat(timespec="seconds")
        self.db.execute(
            "INSERT INTO employees(emp_id, name, email, phone, address, created_at) VALUES(?,?,?,?,?,?)",
            (employee.emp_id.strip(), employee.name.strip(), employee.email.strip(), employee.phone.strip(), employee.address.strip(), now),
        )

    def update(self, employee: Employee) -> None:
        if not employee.emp_id.strip() or not employee.name.strip():
            raise ValueError("Employee ID and Name are required.")
        cur = self.db.execute(
            "UPDATE employees SET name=?, email=?, phone=?, address=? WHERE emp_id=?",
            (employee.name.strip(), employee.email.strip(), employee.phone.strip(), employee.address.strip(), employee.emp_id.strip()),
        )
        if cur.rowcount == 0:
            raise ValueError("Employee not found.")

    def delete(self, emp_id: str) -> None:
        cur = self.db.execute("DELETE FROM employees WHERE emp_id=?", (emp_id.strip(),))
        if cur.rowcount == 0:
            raise ValueError("Employee not found.")

    def list_all(self) -> List[Dict[str, Any]]:
        rows = self.db.query("SELECT emp_id, name, email, phone, address, created_at FROM employees ORDER BY id DESC")
        return [dict(r) for r in rows]

    def get(self, emp_id: str) -> Optional[Dict[str, Any]]:
        rows = self.db.query("SELECT emp_id, name, email, phone, address, created_at FROM employees WHERE emp_id=?", (emp_id.strip(),))
        return dict(rows[0]) if rows else None


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, supplier: Supplier) -> None:
        if not supplier.sup_id.strip() or not supplier.name.strip():
            raise ValueError("Supplier ID and Name are required.")
        now = datetime.now().isoformat(timespec="seconds")
        self.db.execute(
            "INSERT INTO suppliers(sup_id, name, email, phone, address, created_at) VALUES(?,?,?,?,?,?)",
            (supplier.sup_id.strip(), supplier.name.strip(), supplier.email.strip(), supplier.phone.strip(), supplier.address.strip(), now),
        )

    def update(self, supplier: Supplier) -> None:
        if not supplier.sup_id.strip() or not supplier.name.strip():
            raise ValueError("Supplier ID and Name are required.")
        cur = self.db.execute(
            "UPDATE suppliers SET name=?, email=?, phone=?, address=? WHERE sup_id=?",
            (supplier.name.strip(), supplier.email.strip(), supplier.phone.strip(), supplier.address.strip(), supplier.sup_id.strip()),
        )
        if cur.rowcount == 0:
            raise ValueError("Supplier not found.")

    def delete(self, sup_id: str) -> None:
        cur = self.db.execute("DELETE FROM suppliers WHERE sup_id=?", (sup_id.strip(),))
        if cur.rowcount == 0:
            raise ValueError("Supplier not found.")

    def list_all(self) -> List[Dict[str, Any]]:
        rows = self.db.query("SELECT id, sup_id, name, email, phone, address, created_at FROM suppliers ORDER BY id DESC")
        return [dict(r) for r in rows]

    def get_by_id(self, supplier_id: int) -> Optional[Dict[str, Any]]:
        rows = self.db.query("SELECT id, sup_id, name FROM suppliers WHERE id=?", (supplier_id,))
        return dict(rows[0]) if rows else None

    def get_by_sup_id(self, sup_id: str) -> Optional[Dict[str, Any]]:
        rows = self.db.query("SELECT id, sup_id, name, email, phone, address, created_at FROM suppliers WHERE sup_id=?", (sup_id.strip(),))
        return dict(rows[0]) if rows else None


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, category: Category) -> None:
        if not category.name.strip():
            raise ValueError("Category name is required.")
        now = datetime.now().isoformat(timespec="seconds")
        self.db.execute(
            "INSERT INTO categories(name, description, created_at) VALUES(?,?,?)",
            (category.name.strip(), category.description.strip(), now),
        )

    def update(self, category: Category) -> None:
        if not category.name.strip():
            raise ValueError("Category name is required.")
        cur = self.db.execute(
            "UPDATE categories SET description=? WHERE name=?",
            (category.description.strip(), category.name.strip()),
        )
        if cur.rowcount == 0:
            raise ValueError("Category not found.")

    def delete(self, name: str) -> None:
        cur = self.db.execute("DELETE FROM categories WHERE name=?", (name.strip(),))
        if cur.rowcount == 0:
            raise ValueError("Category not found.")

    def list_all(self) -> List[Dict[str, Any]]:
        rows = self.db.query("SELECT id, name, description, created_at FROM categories ORDER BY id DESC")
        return [dict(r) for r in rows]

    def get_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        rows = self.db.query("SELECT id, name FROM categories WHERE id=?", (category_id,))
        return dict(rows[0]) if rows else None

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        rows = self.db.query("SELECT id, name, description, created_at FROM categories WHERE name=?", (name.strip(),))
        return dict(rows[0]) if rows else None


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, product: Product) -> None:
        if not product.sku.strip() or not product.name.strip():
            raise ValueError("SKU and Name are required.")
        if product.price < 0:
            raise ValueError("Price must be non-negative.")
        if product.quantity < 0:
            raise ValueError("Quantity must be non-negative.")
        now = datetime.now().isoformat(timespec="seconds")
        self.db.execute(
            """
            INSERT INTO products(sku, name, category_id, supplier_id, price, quantity, image_path, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                product.sku.strip(),
                product.name.strip(),
                product.category_id,
                product.supplier_id,
                float(product.price),
                int(product.quantity),
                product.image_path.strip(),
                now,
            ),
        )

    def update(self, product: Product) -> None:
        if not product.sku.strip() or not product.name.strip():
            raise ValueError("SKU and Name are required.")
        if product.price < 0:
            raise ValueError("Price must be non-negative.")
        if product.quantity < 0:
            raise ValueError("Quantity must be non-negative.")
        cur = self.db.execute(
            """
            UPDATE products
            SET name=?, category_id=?, supplier_id=?, price=?, quantity=?, image_path=?
            WHERE sku=?
            """,
            (
                product.name.strip(),
                product.category_id,
                product.supplier_id,
                float(product.price),
                int(product.quantity),
                product.image_path.strip(),
                product.sku.strip(),
            ),
        )
        if cur.rowcount == 0:
            raise ValueError("Product not found.")

    def delete(self, sku: str) -> None:
        cur = self.db.execute("DELETE FROM products WHERE sku=?", (sku.strip(),))
        if cur.rowcount == 0:
            raise ValueError("Product not found.")

    def list_all(self) -> List[Dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT p.id, p.sku, p.name, p.category_id, p.supplier_id, p.price, p.quantity, p.image_path, p.created_at,
                   c.name AS category_name,
                   s.name AS supplier_name
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            ORDER BY p.id DESC
            """
        )
        return [dict(r) for r in rows]

    def get_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT p.id, p.sku, p.name, p.category_id, p.supplier_id, p.price, p.quantity, p.image_path, p.created_at
            FROM products p
            WHERE p.sku=?
            """,
            (sku.strip(),),
        )
        return dict(rows[0]) if rows else None

    def adjust_stock(self, product_id: int, delta: int) -> None:
        rows = self.db.query("SELECT quantity FROM products WHERE id=?", (product_id,))
        if not rows:
            raise ValueError("Product not found.")
        current = int(rows[0]["quantity"])
        new_qty = current + int(delta)
        if new_qty < 0:
            raise ValueError("Insufficient stock.")
        self.db.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, product_id))


class InvoiceRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_invoice(
        self,
        invoice_no: str,
        customer_name: str,
        customer_phone: str,
        items: List[InvoiceItem],
        tax_rate: float,
        product_repo: ProductRepository,
    ) -> None:
        inv_no = invoice_no.strip()
        if not inv_no:
            raise ValueError("Invoice number is required.")
        if not items:
            raise ValueError("At least one item is required.")
        if tax_rate < 0:
            raise ValueError("Tax rate must be non-negative.")

        subtotal = sum(i.line_total for i in items)
        tax = subtotal * float(tax_rate)
        total = subtotal + tax
        now = datetime.now().isoformat(timespec="seconds")

        try:
            self.db.conn.execute("BEGIN")
            cur = self.db.conn.cursor()
            cur.execute(
                "INSERT INTO invoices(invoice_no, customer_name, customer_phone, created_at, subtotal, tax, total) VALUES(?,?,?,?,?,?,?)",
                (inv_no, customer_name.strip(), customer_phone.strip(), now, float(subtotal), float(tax), float(total)),
            )
            invoice_id = int(cur.lastrowid)

            for it in items:
                if it.quantity <= 0:
                    raise ValueError("Item quantity must be positive.")
                if it.price < 0:
                    raise ValueError("Item price must be non-negative.")
                if it.product_id is not None:
                    product_repo.adjust_stock(it.product_id, -int(it.quantity))
                cur.execute(
                    """
                    INSERT INTO invoice_items(invoice_id, product_id, sku, name, price, quantity, line_total)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (invoice_id, it.product_id, it.sku.strip(), it.name.strip(), float(it.price), int(it.quantity), float(it.line_total)),
                )

            self.db.conn.commit()
        except Exception:
            self.db.conn.rollback()
            raise

    def list_invoices(self) -> List[Dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, invoice_no, customer_name, customer_phone, created_at, subtotal, tax, total FROM invoices ORDER BY id DESC"
        )
        return [dict(r) for r in rows]

    def get_invoice(self, invoice_no: str) -> Optional[Dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, invoice_no, customer_name, customer_phone, created_at, subtotal, tax, total FROM invoices WHERE invoice_no=?",
            (invoice_no.strip(),),
        )
        return dict(rows[0]) if rows else None

    def get_invoice_items(self, invoice_no: str) -> List[Dict[str, Any]]:
        inv = self.get_invoice(invoice_no)
        if not inv:
            return []
        rows = self.db.query(
            """
            SELECT sku, name, price, quantity, line_total
            FROM invoice_items
            WHERE invoice_id=?
            ORDER BY id ASC
            """,
            (int(inv["id"]),),
        )
        return [dict(r) for r in rows]


class BaseWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        self.grab_release()
        self.destroy()


class EmployeeWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: EmployeeRepository) -> None:
        super().__init__(master, "Employees")
        self.repo = repo

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_address = tk.StringVar()

        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        self._add_labeled_entry(form, "Employee ID", self.var_emp_id, 0)
        self._add_labeled_entry(form, "Name", self.var_name, 1)
        self._add_labeled_entry(form, "Email", self.var_email, 2)
        self._add_labeled_entry(form, "Phone", self.var_phone, 3)
        self._add_labeled_entry(form, "Address", self.var_address, 4)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Add", command=self.add_employee).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update_employee).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete_employee).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self, columns=("emp_id", "name", "email", "phone", "address", "created_at"), show="headings")
        for col, w in [("emp_id", 120), ("name", 160), ("email", 180), ("phone", 120), ("address", 220), ("created_at", 160)]:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh()

    def _add_labeled_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=3)
        parent.grid_columnconfigure(1, weight=1)

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.repo.list_all():
            self.tree.insert("", "end", values=(r["emp_id"], r["name"], r["email"], r["phone"], r["address"], r["created_at"]))

    def on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_emp_id.set(vals[0])
        self.var_name.set(vals[1])
        self.var_email.set(vals[2])
        self.var_phone.set(vals[3])
        self.var_address.set(vals[4])

    def clear_form(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_address.set("")

    def add_employee(self) -> None:
        try:
            self.repo.add(
                Employee(
                    emp_id=self.var_emp_id.get(),
                    name=self.var_name.get(),
                    email=self.var_email.get(),
                    phone=self.var_phone.get(),
                    address=self.var_address.get(),
                )
            )
            self.refresh()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def update_employee(self) -> None:
        try:
            self.repo.update(
                Employee(
                    emp_id=self.var_emp_id.get(),
                    name=self.var_name.get(),
                    email=self.var_email.get(),
                    phone=self.var_phone.get(),
                    address=self.var_address.get(),
                )
            )
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_employee(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            messagebox.showerror("Error", "Employee ID is required to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm", f"Delete employee {emp_id}?", parent=self):
            return
        try:
            self.repo.delete(emp_id)
            self.refresh()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class SupplierWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Suppliers")
        self.repo = repo

        self.var_sup_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_address = tk.StringVar()

        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        self._add_labeled_entry(form, "Supplier ID", self.var_sup_id, 0)
        self._add_labeled_entry(form, "Name", self.var_name, 1)
        self._add_labeled_entry(form, "Email", self.var_email, 2)
        self._add_labeled_entry(form, "Phone", self.var_phone, 3)
        self._add_labeled_entry(form, "Address", self.var_address, 4)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Add", command=self.add_supplier).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update_supplier).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete_supplier).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self, columns=("sup_id", "name", "email", "phone", "address", "created_at"), show="headings")
        for col, w in [("sup_id", 120), ("name", 160), ("email", 180), ("phone", 120), ("address", 220), ("created_at", 160)]:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh()

    def _add_labeled_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=3)
        parent.grid_columnconfigure(1, weight=1)

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.repo.list_all():
            self.tree.insert("", "end", values=(r["sup_id"], r["name"], r["email"], r["phone"], r["address"], r["created_at"]))

    def on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_sup_id.set(vals[0])
        self.var_name.set(vals[1])
        self.var_email.set(vals[2])
        self.var_phone.set(vals[3])
        self.var_address.set(vals[4])

    def clear_form(self) -> None:
        self.var_sup_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_address.set("")

    def add_supplier(self) -> None:
        try:
            self.repo.add(
                Supplier(
                    sup_id=self.var_sup_id.get(),
                    name=self.var_name.get(),
                    email=self.var_email.get(),
                    phone=self.var_phone.get(),
                    address=self.var_address.get(),
                )
            )
            self.refresh()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def update_supplier(self) -> None:
        try:
            self.repo.update(
                Supplier(
                    sup_id=self.var_sup_id.get(),
                    name=self.var_name.get(),
                    email=self.var_email.get(),
                    phone=self.var_phone.get(),
                    address=self.var_address.get(),
                )
            )
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_supplier(self) -> None:
        sup_id = self.var_sup_id.get().strip()
        if not sup_id:
            messagebox.showerror("Error", "Supplier ID is required to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm", f"Delete supplier {sup_id}?", parent=self):
            return
        try:
            self.repo.delete(sup_id)
            self.refresh()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class CategoryWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Categories")
        self.repo = repo

        self.var_name = tk.StringVar()
        self.var_desc = tk.StringVar()

        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.var_name).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.var_desc).grid(row=1, column=1, sticky="ew", pady=3)
        form.grid_columnconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Add", command=self.add_category).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update_category).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete_category).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self, columns=("name", "description", "created_at"), show="headings")
        for col, w in [("name", 200), ("description", 320), ("created_at", 180)]:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh()

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.repo.list_all():
            self.tree.insert("", "end", values=(r["name"], r["description"], r["created_at"]))

    def on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_name.set(vals[0])
        self.var_desc.set(vals[1])

    def clear_form(self) -> None:
        self.var_name.set("")
        self.var_desc.set("")

    def add_category(self) -> None:
        try:
            self.repo.add(Category(name=self.var_name.get(), description=self.var_desc.get()))
            self.refresh()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category name already exists.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def update_category(self) -> None:
        try:
            self.repo.update(Category(name=self.var_name.get(), description=self.var_desc.get()))
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_category(self) -> None:
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Category name is required to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm", f"Delete category '{name}'?", parent=self):
            return
        try:
            self.repo.delete(name)
            self.refresh()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class ProductWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, cat_repo: CategoryRepository, sup_repo: SupplierRepository) -> None:
        super().__init__(master, "Products")
        self.repo = repo
        self.cat_repo = cat_repo
        self.sup_repo = sup_repo

        self.var_sku = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_quantity = tk.StringVar()
        self.var_image_path = tk.StringVar()

        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        self._add_labeled_entry(form, "SKU", self.var_sku, 0)
        self._add_labeled_entry(form, "Name", self.var_name, 1)

        ttk.Label(form, text="Category").grid(row=2, column=0, sticky="w", pady=3)
        self.cmb_category = ttk.Combobox(form, textvariable=self.var_category, state="readonly")
        self.cmb_category.grid(row=2, column=1, sticky="ew", pady=3)

        ttk.Label(form, text="Supplier").grid(row=3, column=0, sticky="w", pady=3)
        self.cmb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, state="readonly")
        self.cmb_supplier.grid(row=3, column=1, sticky="ew", pady=3)

        self._add_labeled_entry(form, "Price", self.var_price, 4)
        self._add_labeled_entry(form, "Quantity", self.var_quantity, 5)

        ttk.Label(form, text="Image").grid(row=6, column=0, sticky="w", pady=3)
        img_row = ttk.Frame(form)
        img_row.grid(row=6, column=1, sticky="ew", pady=3)
        ttk.Entry(img_row, textvariable=self.var_image_path).pack(side="left", fill="x", expand=True)
        ttk.Button(img_row, text="Browse", command=self.browse_image).pack(side="left", padx=5)

        form.grid_columnconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Add", command=self.add_product).pack(side="left")
        ttk.Button(btns, text="Update", command=self.update_product).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete_product).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=5)
        ttk.Button(btns, text="Refresh Lists", command=self.refresh_lists).pack(side="right")

        self.tree = ttk.Treeview(
            self,
            columns=("sku", "name", "category", "supplier", "price", "quantity", "image_path", "created_at"),
            show="headings",
        )
        cols = [
            ("sku", 120),
            ("name", 180),
            ("category", 140),
            ("supplier", 140),
            ("price", 90),
            ("quantity", 90),
            ("image_path", 220),
            ("created_at", 160),
        ]
        for col, w in cols:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh_lists()
        self.refresh()

    def _add_labeled_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=3)

    def refresh_lists(self) -> None:
        categories = self.cat_repo.list_all()
        suppliers = self.sup_repo.list_all()
        self._category_map = {c["name"]: int(c["id"]) for c in categories}
        self._supplier_map = {s["name"]: int(s["id"]) for s in suppliers}
        self.cmb_category["values"] = [""] + list(self._category_map.keys())
        self.cmb_supplier["values"] = [""] + list(self._supplier_map.keys())

    def browse_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")],
        )
        if path:
            self.var_image_path.set(path)

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.repo.list_all():
            self.tree.insert(
                "",
                "end",
                values=(
                    r["sku"],
                    r["name"],
                    r.get("category_name") or "",
                    r.get("supplier_name") or "",
                    f'{float(r["price"]):.2f}',
                    str(int(r["quantity"])),
                    r.get("image_path") or "",
                    r["created_at"],
                ),
            )

    def on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_sku.set(vals[0])
        self.var_name.set(vals[1])
        self.var_category.set(vals[2])
        self.var_supplier.set(vals[3])
        self.var_price.set(vals[4])
        self.var_quantity.set(vals[5])
        self.var_image_path.set(vals[6])

    def clear_form(self) -> None:
        self.var_sku.set("")
        self.var_name.set("")
        self.var_category.set("")
        self.var_supplier.set("")
        self.var_price.set("")
        self.var_quantity.set("")
        self.var_image_path.set("")

    def _parse_price_qty(self) -> Tuple[float, int]:
        try:
            price = float(self.var_price.get().strip() or "0")
        except Exception:
            raise ValueError("Invalid price.")
        try:
            qty = int(float(self.var_quantity.get().strip() or "0"))
        except Exception:
            raise ValueError("Invalid quantity.")
        return price, qty

    def add_product(self) -> None:
        try:
            price, qty = self._parse_price_qty()
            cat_id = self._category_map.get(self.var_category.get().strip()) if self.var_category.get().strip() else None
            sup_id = self._supplier_map.get(self.var_supplier.get().strip()) if self.var_supplier.get().strip() else None
            self.repo.add(
                Product(
                    sku=self.var_sku.get(),
                    name=self.var_name.get(),
                    category_id=cat_id,
                    supplier_id=sup_id,
                    price=price,
                    quantity=qty,
                    image_path=self.var_image_path.get(),
                )
            )
            self.refresh()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "SKU already exists.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def update_product(self) -> None:
        try:
            price, qty = self._parse_price_qty()
            cat_id = self._category_map.get(self.var_category.get().strip()) if self.var_category.get().strip() else None
            sup_id = self._supplier_map.get(self.var_supplier.get().strip()) if self.var_supplier.get().strip() else None
            self.repo.update(
                Product(
                    sku=self.var_sku.get(),
                    name=self.var_name.get(),
                    category_id=cat_id,
                    supplier_id=sup_id,
                    price=price,
                    quantity=qty,
                    image_path=self.var_image_path.get(),
                )
            )
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def delete_product(self) -> None:
        sku = self.var_sku.get().strip()
        if not sku:
            messagebox.showerror("Error", "SKU is required to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm", f"Delete product {sku}?", parent=self):
            return
        try:
            self.repo.delete(sku)
            self.refresh()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class BillingWindow(BaseWindow):
    def __init__(self, master: tk.Tk, product_repo: ProductRepository, invoice_repo: InvoiceRepository) -> None:
        super().__init__(master, "Billing")
        self.product_repo = product_repo
        self.invoice_repo = invoice_repo

        self.var_invoice_no = tk.StringVar()
        self.var_customer_name = tk.StringVar()
        self.var_customer_phone = tk.StringVar()
        self.var_tax_rate = tk.StringVar(value="0.00")

        self.var_sku = tk.StringVar()
        self.var_qty = tk.StringVar(value="1")

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        self._add_labeled_entry(top, "Invoice No", self.var_invoice_no, 0, 0)
        self._add_labeled_entry(top, "Customer Name", self.var_customer_name, 0, 2)
        self._add_labeled_entry(top, "Customer Phone", self.var_customer_phone, 1, 2)
        self._add_labeled_entry(top, "Tax Rate (e.g. 0.05)", self.var_tax_rate, 1, 0)

        items_frame = ttk.LabelFrame(self, text="Add Item")
        items_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(items_frame, text="Product SKU").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(items_frame, textvariable=self.var_sku).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(items_frame, text="Quantity").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(items_frame, textvariable=self.var_qty, width=10).grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Button(items_frame, text="Add to Cart", command=self.add_to_cart).grid(row=0, column=4, sticky="e", padx=8, pady=6)
        items_frame.grid_columnconfigure(1, weight=1)

        self.cart = ttk.Treeview(self, columns=("sku", "name", "price", "quantity", "line_total"), show="headings")
        for col, w in [("sku", 120), ("name", 220), ("price", 90), ("quantity", 90), ("line_total", 110)]:
            self.cart.heading(col, text=col.replace("_", " ").title())
            self.cart.column(col, width=w, anchor="w")
        self.cart.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Remove Selected", command=self.remove_selected).pack(side="left")
        ttk.Button(bottom, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=5)
        ttk.Button(bottom, text="Generate Bill", command=self.generate_bill).pack(side="right")

        self.lbl_totals = ttk.Label(self, text="Subtotal: 0.00   Tax: 0.00   Total: 0.00")
        self.lbl_totals.pack(fill="x", padx=10, pady=(0, 10))

        self._cart_items: List[InvoiceItem] = []
        self._update_totals()

    def _add_labeled_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int, col: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=8, pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=8, pady=4)
        parent.grid_columnconfigure(col + 1, weight=1)

    def _update_totals(self) -> None:
        subtotal = sum(i.line_total for i in self._cart_items)
        try:
            tax_rate = float(self.var_tax_rate.get().strip() or "0")
        except Exception:
            tax_rate = 0.0
        tax = subtotal * tax_rate
        total = subtotal + tax
        self.lbl_totals.config(text=f"Subtotal: {subtotal:.2f}   Tax: {tax:.2f}   Total: {total:.2f}")

    def add_to_cart(self) -> None:
        sku = self.var_sku.get().strip()
        if not sku:
            messagebox.showerror("Error", "SKU is required.", parent=self)
            return
        try:
            qty = int(float(self.var_qty.get().strip() or "0"))
        except Exception:
            messagebox.showerror("Error", "Invalid quantity.", parent=self)
            return
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive.", parent=self)
            return

        prod = self.product_repo.get_by_sku(sku)
        if not prod:
            messagebox.showerror("Error", "Product not found.", parent=self)
            return
        if int(prod["quantity"]) < qty:
            messagebox.showerror("Error", "Insufficient stock.", parent=self)
            return

        item = InvoiceItem(
            product_id=int(prod["id"]),
            sku=str(prod["sku"]),
            name=str(prod["name"]),
            price=float(prod["price"]),
            quantity=qty,
        )
        self._cart_items.append(item)
        self.cart.insert("", "end", values=(item.sku, item.name, f"{item.price:.2f}", str(item.quantity), f"{item.line_total:.2f}"))
        self.var_sku.set("")
        self.var_qty.set("1")
        self._update_totals()

    def remove_selected(self) -> None:
        sel = self.cart.selection()
        if not sel:
            return
        idxs = []
        for s in sel:
            idx = self.cart.index(s)
            idxs.append(idx)
        for s in sel:
            self.cart.delete(s)
        for idx in sorted(idxs, reverse=True):
            if 0 <= idx < len(self._cart_items):
                self._cart_items.pop(idx)
        self._update_totals()

    def clear_cart(self) -> None:
        for i in self.cart.get_children():
            self.cart.delete(i)
        self._cart_items.clear()
        self._update_totals()

    def generate_bill(self) -> None:
        inv_no = self.var_invoice_no.get().strip()
        if not inv_no:
            messagebox.showerror("Error", "Invoice number is required.", parent=self)
            return
        try:
            tax_rate = float(self.var_tax_rate.get().strip() or "0")
        except Exception:
            messagebox.showerror("Error", "Invalid tax rate.", parent=self)
            return

        try:
            self.invoice_repo.create_invoice(
                invoice_no=inv_no,
                customer_name=self.var_customer_name.get(),
                customer_phone=self.var_customer_phone.get(),
                items=list(self._cart_items),
                tax_rate=tax_rate,
                product_repo=self.product_repo,
            )
            messagebox.showinfo("Success", "Bill generated and saved.", parent=self)
            self.clear_cart()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class BillsWindow(BaseWindow):
    def __init__(self, master: tk.Tk, invoice_repo: InvoiceRepository) -> None:
        super().__init__(master, "Bills (Invoices)")
        self.invoice_repo = invoice_repo

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        self.var_search = tk.StringVar()
        ttk.Label(top, text="Invoice No").pack(side="left")
        ttk.Entry(top, textvariable=self.var_search).pack(side="left", padx=5)
        ttk.Button(top, text="Search", command=self.search).pack(side="left", padx=5)
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="left")

        self.tree = ttk.Treeview(
            self,
            columns=("invoice_no", "customer_name", "customer_phone", "created_at", "subtotal", "tax", "total"),
            show="headings",
        )
        cols = [
            ("invoice_no", 140),
            ("customer_name", 180),
            ("customer_phone", 140),
            ("created_at", 170),
            ("subtotal", 90),
            ("tax", 90),
            ("total", 90),
        ]
        for col, w in cols:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", self.open_details)

        self.refresh()

    def refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.invoice_repo.list_invoices():
            self.tree.insert(
                "",
                "end",
                values=(
                    r["invoice_no"],
                    r["customer_name"],
                    r["customer_phone"],
                    r["created_at"],
                    f'{float(r["subtotal"]):.2f}',
                    f'{float(r["tax"]):.2f}',
                    f'{float(r["total"]):.2f}',
                ),
            )

    def search(self) -> None:
        inv_no = self.var_search.get().strip()
        if not inv_no:
            self.refresh()
            return
        inv = self.invoice_repo.get_invoice(inv_no)
        for i in self.tree.get_children():
            self.tree.delete(i)
        if inv:
            self.tree.insert(
                "",
                "end",
                values=(
                    inv["invoice_no"],
                    inv["customer_name"],
                    inv["customer_phone"],
                    inv["created_at"],
                    f'{float(inv["subtotal"]):.2f}',
                    f'{float(inv["tax"]):.2f}',
                    f'{float(inv["total"]):.2f}',
                ),
            )

    def open_details(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        inv_no = self.tree.item(sel[0], "values")[0]
        InvoiceDetailsWindow(self, self.invoice_repo, str(inv_no))


class InvoiceDetailsWindow(BaseWindow):
    def __init__(self, master: tk.Tk, invoice_repo: InvoiceRepository, invoice_no: str) -> None:
        super().__init__(master, f"Invoice Details - {invoice_no}")
        self.invoice_repo = invoice_repo
        self.invoice_no = invoice_no

        inv = self.invoice_repo.get_invoice(invoice_no)
        if not inv:
            messagebox.showerror("Error", "Invoice not found.", parent=self)
            self._on_close()
            return

        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)

        ttk.Label(header, text=f"Invoice No: {inv['invoice_no']}").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(header, text=f"Date/Time: {inv['created_at']}").grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(header, text=f"Customer: {inv['customer_name']}").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(header, text=f"Phone: {inv['customer_phone']}").grid(row=1, column=1, sticky="w", padx=5, pady=2)

        self.tree = ttk.Treeview(self, columns=("sku", "name", "price", "quantity", "line_total"), show="headings")
        for col, w in [("sku", 120), ("name", 240), ("price", 90), ("quantity", 90), ("line_total", 110)]:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for it in self.invoice_repo.get_invoice_items(invoice_no):
            self.tree.insert(
                "",
                "end",
                values=(it["sku"], it["name"], f'{float(it["price"]):.2f}', str(int(it["quantity"])), f'{float(it["line_total"]):.2f}'),
            )

        totals = ttk.Frame(self)
        totals.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(totals, text=f"Subtotal: {float(inv['subtotal']):.2f}").pack(side="left", padx=5)
        ttk.Label(totals, text=f"Tax: {float(inv['tax']):.2f}").pack(side="left", padx=5)
        ttk.Label(totals, text=f"Total: {float(inv['total']):.2f}").pack(side="left", padx=5)


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(900, 550)

        self.db = Database(DB_FILE)
        self.emp_repo = EmployeeRepository(self.db)
        self.sup_repo = SupplierRepository(self.db)
        self.cat_repo = CategoryRepository(self.db)
        self.prod_repo = ProductRepository(self.db)
        self.inv_repo = InvoiceRepository(self.db)

        self._img_ref: Optional[Any] = None

        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)

        self.lbl_title = ttk.Label(header, text="Inventory Management System", font=("TkDefaultFont", 16, "bold"))
        self.lbl_title.pack(side="left")

        self.lbl_time = ttk.Label(header, text="")
        self.lbl_time.pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(body)
        left.pack(side="left", fill="y")

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        ttk.Button(left, text="Employees", width=22, command=self.open_employees).pack(pady=5, fill="x")
        ttk.Button(left, text="Suppliers", width=22, command=self.open_suppliers).pack(pady=5, fill="x")
        ttk.Button(left, text="Categories", width=22, command=self.open_categories).pack(pady=5, fill="x")
        ttk.Button(left, text="Products", width=22, command=self.open_products).pack(pady=5, fill="x")
        ttk.Button(left, text="Billing", width=22, command=self.open_billing).pack(pady=5, fill="x")
        ttk.Button(left, text="Bills (Search)", width=22, command=self.open_bills).pack(pady=5, fill="x")
        ttk.Button(left, text="Load Image", width=22, command=self.load_image).pack(pady=20, fill="x")
        ttk.Button(left, text="Exit", width=22, command=self.on_exit).pack(pady=5, fill="x")

        self.stats = ttk.LabelFrame(right, text="Dashboard")
        self.stats.pack(fill="both", expand=True)

        self.lbl_counts = ttk.Label(self.stats, text="", font=("TkDefaultFont", 12))
        self.lbl_counts.pack(anchor="w", padx=10, pady=10)

        self.img_label = ttk.Label(self.stats)
        self.img_label.pack(padx=10, pady=10, anchor="center")

        self.files_frame = ttk.LabelFrame(self.stats, text="Files (Current Directory)")
        self.files_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.files_list = tk.Listbox(self.files_frame, height=8)
        self.files_list.pack(fill="both", expand=True, padx=8, pady=8)

        self._tick()
        self.refresh_dashboard()
        self.refresh_files()

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _tick(self) -> None:
        self.lbl_time.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self._tick)

    def refresh_dashboard(self) -> None:
        emp_count = len(self.emp_repo.list_all())
        sup_count = len(self.sup_repo.list_all())
        cat_count = len(self.cat_repo.list_all())
        prod_count = len(self.prod_repo.list_all())
        inv_count = len(self.inv_repo.list_invoices())
        self.lbl_counts.config(
            text=f"Employees: {emp_count}\nSuppliers: {sup_count}\nCategories: {cat_count}\nProducts: {prod_count}\nBills: {inv_count}"
        )

    def refresh_files(self) -> None:
        self.files_list.delete(0, tk.END)
        try:
            for name in sorted(os.listdir(".")):
                self.files_list.insert(tk.END, name)
        except Exception:
            pass

    def load_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")],
        )
        if not path:
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Error", "PIL (Pillow) is not available.", parent=self)
            return
        try:
            img = Image.open(path)
            img.thumbnail((520, 320))
            self._img_ref = ImageTk.PhotoImage(img)
            self.img_label.config(image=self._img_ref)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def open_employees(self) -> None:
        EmployeeWindow(self, self.emp_repo)

    def open_suppliers(self) -> None:
        SupplierWindow(self, self.sup_repo)

    def open_categories(self) -> None:
        CategoryWindow(self, self.cat_repo)

    def open_products(self) -> None:
        ProductWindow(self, self.prod_repo, self.cat_repo, self.sup_repo)

    def open_billing(self) -> None:
        BillingWindow(self, self.prod_repo, self.inv_repo)

    def open_bills(self) -> None:
        BillsWindow(self, self.inv_repo)

    def on_exit(self) -> None:
        try:
            self.db.close()
        finally:
            self.destroy()


def main() -> None:
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()