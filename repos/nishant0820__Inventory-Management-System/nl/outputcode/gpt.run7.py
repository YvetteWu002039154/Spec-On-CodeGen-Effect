import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Dict

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


DB_FILE = "inventory_management.db"


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
                emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                gender TEXT NOT NULL,
                dob TEXT NOT NULL,
                doj TEXT NOT NULL,
                address TEXT NOT NULL,
                salary REAL NOT NULL CHECK (salary >= 0)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                sup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                company TEXT NOT NULL,
                address TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                prod_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                supplier_id INTEGER NOT NULL,
                price REAL NOT NULL CHECK (price >= 0),
                qty INTEGER NOT NULL CHECK (qty >= 0),
                status TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(cat_id) ON DELETE RESTRICT,
                FOREIGN KEY(supplier_id) REFERENCES suppliers(sup_id) ON DELETE RESTRICT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills (
                invoice_no TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                bill_date TEXT NOT NULL,
                total REAL NOT NULL CHECK (total >= 0),
                tax REAL NOT NULL CHECK (tax >= 0),
                net_total REAL NOT NULL CHECK (net_total >= 0),
                content TEXT NOT NULL
            )
            """
        )

        self.conn.commit()

    def execute(self, sql: str, params: Tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql: str, params: Tuple = ()) -> List[Tuple]:
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
    name: str
    email: str
    phone: str
    gender: str
    dob: str
    doj: str
    address: str
    salary: float


@dataclass(frozen=True)
class Supplier:
    name: str
    email: str
    phone: str
    company: str
    address: str


@dataclass(frozen=True)
class Category:
    name: str
    description: str


@dataclass(frozen=True)
class Product:
    name: str
    category_id: int
    supplier_id: int
    price: float
    qty: int
    status: str


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, emp: Employee) -> int:
        self._validate(emp)
        cur = self.db.execute(
            """
            INSERT INTO employees (name, email, phone, gender, dob, doj, address, salary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (emp.name, emp.email, emp.phone, emp.gender, emp.dob, emp.doj, emp.address, float(emp.salary)),
        )
        return int(cur.lastrowid)

    def update(self, emp_id: int, emp: Employee) -> None:
        self._validate(emp)
        self.db.execute(
            """
            UPDATE employees
            SET name=?, email=?, phone=?, gender=?, dob=?, doj=?, address=?, salary=?
            WHERE emp_id=?
            """,
            (emp.name, emp.email, emp.phone, emp.gender, emp.dob, emp.doj, emp.address, float(emp.salary), emp_id),
        )

    def delete(self, emp_id: int) -> None:
        self.db.execute("DELETE FROM employees WHERE emp_id=?", (emp_id,))

    def get(self, emp_id: int) -> Optional[Tuple]:
        rows = self.db.query("SELECT * FROM employees WHERE emp_id=?", (emp_id,))
        return rows[0] if rows else None

    def list_all(self) -> List[Tuple]:
        return self.db.query("SELECT * FROM employees ORDER BY emp_id DESC")

    def search(self, field: str, value: str) -> List[Tuple]:
        allowed = {"emp_id", "name", "email", "phone", "gender"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        if field == "emp_id":
            try:
                emp_id = int(value)
            except Exception:
                return []
            return self.db.query("SELECT * FROM employees WHERE emp_id=?", (emp_id,))
        return self.db.query(f"SELECT * FROM employees WHERE {field} LIKE ? ORDER BY emp_id DESC", (f"%{value}%",))

    def _validate(self, emp: Employee) -> None:
        if not emp.name.strip():
            raise ValueError("Employee name is required")
        if not emp.email.strip():
            raise ValueError("Employee email is required")
        if not emp.phone.strip():
            raise ValueError("Employee phone is required")
        if not emp.gender.strip():
            raise ValueError("Employee gender is required")
        if not emp.dob.strip():
            raise ValueError("Employee DOB is required")
        if not emp.doj.strip():
            raise ValueError("Employee DOJ is required")
        if not emp.address.strip():
            raise ValueError("Employee address is required")
        if float(emp.salary) < 0:
            raise ValueError("Salary must be non-negative")


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, sup: Supplier) -> int:
        self._validate(sup)
        cur = self.db.execute(
            """
            INSERT INTO suppliers (name, email, phone, company, address)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sup.name, sup.email, sup.phone, sup.company, sup.address),
        )
        return int(cur.lastrowid)

    def update(self, sup_id: int, sup: Supplier) -> None:
        self._validate(sup)
        self.db.execute(
            """
            UPDATE suppliers
            SET name=?, email=?, phone=?, company=?, address=?
            WHERE sup_id=?
            """,
            (sup.name, sup.email, sup.phone, sup.company, sup.address, sup_id),
        )

    def delete(self, sup_id: int) -> None:
        self.db.execute("DELETE FROM suppliers WHERE sup_id=?", (sup_id,))

    def get(self, sup_id: int) -> Optional[Tuple]:
        rows = self.db.query("SELECT * FROM suppliers WHERE sup_id=?", (sup_id,))
        return rows[0] if rows else None

    def list_all(self) -> List[Tuple]:
        return self.db.query("SELECT * FROM suppliers ORDER BY sup_id DESC")

    def search(self, field: str, value: str) -> List[Tuple]:
        allowed = {"sup_id", "name", "email", "phone", "company"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        if field == "sup_id":
            try:
                sup_id = int(value)
            except Exception:
                return []
            return self.db.query("SELECT * FROM suppliers WHERE sup_id=?", (sup_id,))
        return self.db.query(f"SELECT * FROM suppliers WHERE {field} LIKE ? ORDER BY sup_id DESC", (f"%{value}%",))

    def _validate(self, sup: Supplier) -> None:
        if not sup.name.strip():
            raise ValueError("Supplier name is required")
        if not sup.email.strip():
            raise ValueError("Supplier email is required")
        if not sup.phone.strip():
            raise ValueError("Supplier phone is required")
        if not sup.company.strip():
            raise ValueError("Supplier company is required")
        if not sup.address.strip():
            raise ValueError("Supplier address is required")


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, cat: Category) -> int:
        self._validate(cat)
        cur = self.db.execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (cat.name, cat.description),
        )
        return int(cur.lastrowid)

    def update(self, cat_id: int, cat: Category) -> None:
        self._validate(cat)
        self.db.execute(
            "UPDATE categories SET name=?, description=? WHERE cat_id=?",
            (cat.name, cat.description, cat_id),
        )

    def delete(self, cat_id: int) -> None:
        self.db.execute("DELETE FROM categories WHERE cat_id=?", (cat_id,))

    def get(self, cat_id: int) -> Optional[Tuple]:
        rows = self.db.query("SELECT * FROM categories WHERE cat_id=?", (cat_id,))
        return rows[0] if rows else None

    def list_all(self) -> List[Tuple]:
        return self.db.query("SELECT * FROM categories ORDER BY cat_id DESC")

    def search(self, field: str, value: str) -> List[Tuple]:
        allowed = {"cat_id", "name"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        if field == "cat_id":
            try:
                cat_id = int(value)
            except Exception:
                return []
            return self.db.query("SELECT * FROM categories WHERE cat_id=?", (cat_id,))
        return self.db.query("SELECT * FROM categories WHERE name LIKE ? ORDER BY cat_id DESC", (f"%{value}%",))

    def _validate(self, cat: Category) -> None:
        if not cat.name.strip():
            raise ValueError("Category name is required")
        if not cat.description.strip():
            raise ValueError("Category description is required")


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, prod: Product) -> int:
        self._validate(prod)
        cur = self.db.execute(
            """
            INSERT INTO products (name, category_id, supplier_id, price, qty, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (prod.name, int(prod.category_id), int(prod.supplier_id), float(prod.price), int(prod.qty), prod.status),
        )
        return int(cur.lastrowid)

    def update(self, prod_id: int, prod: Product) -> None:
        self._validate(prod)
        self.db.execute(
            """
            UPDATE products
            SET name=?, category_id=?, supplier_id=?, price=?, qty=?, status=?
            WHERE prod_id=?
            """,
            (prod.name, int(prod.category_id), int(prod.supplier_id), float(prod.price), int(prod.qty), prod.status, prod_id),
        )

    def delete(self, prod_id: int) -> None:
        self.db.execute("DELETE FROM products WHERE prod_id=?", (prod_id,))

    def get(self, prod_id: int) -> Optional[Tuple]:
        rows = self.db.query("SELECT * FROM products WHERE prod_id=?", (prod_id,))
        return rows[0] if rows else None

    def list_all(self) -> List[Tuple]:
        return self.db.query(
            """
            SELECT p.prod_id, p.name, c.name, s.name, p.price, p.qty, p.status, p.category_id, p.supplier_id
            FROM products p
            JOIN categories c ON c.cat_id = p.category_id
            JOIN suppliers s ON s.sup_id = p.supplier_id
            ORDER BY p.prod_id DESC
            """
        )

    def search(self, field: str, value: str) -> List[Tuple]:
        allowed = {"prod_id", "name", "status"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        if field == "prod_id":
            try:
                prod_id = int(value)
            except Exception:
                return []
            return self.db.query(
                """
                SELECT p.prod_id, p.name, c.name, s.name, p.price, p.qty, p.status, p.category_id, p.supplier_id
                FROM products p
                JOIN categories c ON c.cat_id = p.category_id
                JOIN suppliers s ON s.sup_id = p.supplier_id
                WHERE p.prod_id=?
                """,
                (prod_id,),
            )
        return self.db.query(
            f"""
            SELECT p.prod_id, p.name, c.name, s.name, p.price, p.qty, p.status, p.category_id, p.supplier_id
            FROM products p
            JOIN categories c ON c.cat_id = p.category_id
            JOIN suppliers s ON s.sup_id = p.supplier_id
            WHERE p.{field} LIKE ?
            ORDER BY p.prod_id DESC
            """,
            (f"%{value}%",),
        )

    def adjust_stock(self, prod_id: int, delta_qty: int) -> None:
        if delta_qty == 0:
            return
        row = self.db.query("SELECT qty FROM products WHERE prod_id=?", (prod_id,))
        if not row:
            raise ValueError("Product not found")
        current = int(row[0][0])
        new_qty = current + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self.db.execute("UPDATE products SET qty=? WHERE prod_id=?", (new_qty, prod_id))

    def _validate(self, prod: Product) -> None:
        if not prod.name.strip():
            raise ValueError("Product name is required")
        if int(prod.category_id) <= 0:
            raise ValueError("Category is required")
        if int(prod.supplier_id) <= 0:
            raise ValueError("Supplier is required")
        if float(prod.price) < 0:
            raise ValueError("Price must be non-negative")
        if int(prod.qty) < 0:
            raise ValueError("Quantity must be non-negative")
        if prod.status.strip() not in {"Active", "Inactive"}:
            raise ValueError("Status must be Active or Inactive")


class BillRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, invoice_no: str, customer_name: str, customer_phone: str, bill_date: str, total: float, tax: float, net_total: float, content: str) -> None:
        if not invoice_no.strip():
            raise ValueError("Invoice number is required")
        if not customer_name.strip():
            raise ValueError("Customer name is required")
        if not customer_phone.strip():
            raise ValueError("Customer phone is required")
        if not bill_date.strip():
            raise ValueError("Bill date is required")
        if float(total) < 0 or float(tax) < 0 or float(net_total) < 0:
            raise ValueError("Totals must be non-negative")
        if not content.strip():
            raise ValueError("Bill content is required")

        self.db.execute(
            """
            INSERT OR REPLACE INTO bills (invoice_no, customer_name, customer_phone, bill_date, total, tax, net_total, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (invoice_no, customer_name, customer_phone, bill_date, float(total), float(tax), float(net_total), content),
        )

    def get(self, invoice_no: str) -> Optional[Tuple]:
        rows = self.db.query("SELECT * FROM bills WHERE invoice_no=?", (invoice_no,))
        return rows[0] if rows else None

    def list_all(self) -> List[Tuple]:
        return self.db.query("SELECT invoice_no, customer_name, customer_phone, bill_date, net_total FROM bills ORDER BY bill_date DESC")

    def search(self, invoice_no: str) -> Optional[str]:
        row = self.get(invoice_no)
        if not row:
            return None
        return str(row[7])


class BaseManagerWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("1100x600")
        self.minsize(1000, 550)
        self.transient(master)
        self.grab_set()

    def show_error(self, msg: str) -> None:
        messagebox.showerror("Error", msg, parent=self)

    def show_info(self, msg: str) -> None:
        messagebox.showinfo("Info", msg, parent=self)

    def ask_yes_no(self, msg: str) -> bool:
        return messagebox.askyesno("Confirm", msg, parent=self)


class EmployeeManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: EmployeeRepository) -> None:
        super().__init__(master, "Employee Management")
        self.repo = repo
        self.selected_id: Optional[int] = None

        form = ttk.LabelFrame(self, text="Employee Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_gender = tk.StringVar(value="Male")
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_address = tk.StringVar()

        fields = [
            ("Name", self.var_name),
            ("Email", self.var_email),
            ("Phone", self.var_phone),
            ("Gender", self.var_gender),
            ("DOB (YYYY-MM-DD)", self.var_dob),
            ("DOJ (YYYY-MM-DD)", self.var_doj),
            ("Salary", self.var_salary),
            ("Address", self.var_address),
        ]

        for i, (lbl, var) in enumerate(fields):
            ttk.Label(form, text=lbl).grid(row=i // 4, column=(i % 4) * 2, padx=6, pady=6, sticky="w")
            if lbl == "Gender":
                cb = ttk.Combobox(form, textvariable=var, values=["Male", "Female", "Other"], state="readonly", width=18)
                cb.grid(row=i // 4, column=(i % 4) * 2 + 1, padx=6, pady=6, sticky="w")
            else:
                ttk.Entry(form, textvariable=var, width=22).grid(row=i // 4, column=(i % 4) * 2 + 1, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self.on_save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self.on_update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self.on_delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["emp_id", "name", "email", "phone", "gender"], state="readonly", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self.on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self.refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("emp_id", "name", "email", "phone", "gender", "dob", "doj", "address", "salary")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120 if c not in {"address"} else 220, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.refresh()

    def _parse_employee(self) -> Employee:
        salary = float(self.var_salary.get().strip() or "0")
        return Employee(
            name=self.var_name.get().strip(),
            email=self.var_email.get().strip(),
            phone=self.var_phone.get().strip(),
            gender=self.var_gender.get().strip(),
            dob=self.var_dob.get().strip(),
            doj=self.var_doj.get().strip(),
            address=self.var_address.get().strip(),
            salary=salary,
        )

    def on_save(self) -> None:
        try:
            emp = self._parse_employee()
            self.repo.add(emp)
            self.show_info("Employee saved")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_update(self) -> None:
        if self.selected_id is None:
            self.show_error("Select an employee to update")
            return
        try:
            emp = self._parse_employee()
            self.repo.update(self.selected_id, emp)
            self.show_info("Employee updated")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_delete(self) -> None:
        if self.selected_id is None:
            self.show_error("Select an employee to delete")
            return
        if not self.ask_yes_no("Delete selected employee?"):
            return
        try:
            self.repo.delete(self.selected_id)
            self.show_info("Employee deleted")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_clear(self) -> None:
        self.selected_id = None
        self.var_name.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_gender.set("Male")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_salary.set("")
        self.var_address.set("")

    def on_search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_text.get().strip())
            self._load(rows)
        except Exception as e:
            self.show_error(str(e))

    def on_select(self, _evt: object = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get("values", [])
        if not vals:
            return
        self.selected_id = int(vals[0])
        self.var_name.set(str(vals[1]))
        self.var_email.set(str(vals[2]))
        self.var_phone.set(str(vals[3]))
        self.var_gender.set(str(vals[4]))
        self.var_dob.set(str(vals[5]))
        self.var_doj.set(str(vals[6]))
        self.var_address.set(str(vals[7]))
        self.var_salary.set(str(vals[8]))

    def refresh(self) -> None:
        self._load(self.repo.list_all())

    def _load(self, rows: List[Tuple]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", tk.END, values=r)


class SupplierManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Supplier Management")
        self.repo = repo
        self.selected_id: Optional[int] = None

        form = ttk.LabelFrame(self, text="Supplier Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_company = tk.StringVar()
        self.var_address = tk.StringVar()

        fields = [
            ("Name", self.var_name),
            ("Email", self.var_email),
            ("Phone", self.var_phone),
            ("Company", self.var_company),
            ("Address", self.var_address),
        ]

        for i, (lbl, var) in enumerate(fields):
            ttk.Label(form, text=lbl).grid(row=i // 3, column=(i % 3) * 2, padx=6, pady=6, sticky="w")
            ttk.Entry(form, textvariable=var, width=30).grid(row=i // 3, column=(i % 3) * 2 + 1, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self.on_save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self.on_update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self.on_delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["sup_id", "name", "email", "phone", "company"], state="readonly", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self.on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self.refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("sup_id", "name", "email", "phone", "company", "address")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c != "address" else 260, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.refresh()

    def _parse_supplier(self) -> Supplier:
        return Supplier(
            name=self.var_name.get().strip(),
            email=self.var_email.get().strip(),
            phone=self.var_phone.get().strip(),
            company=self.var_company.get().strip(),
            address=self.var_address.get().strip(),
        )

    def on_save(self) -> None:
        try:
            sup = self._parse_supplier()
            self.repo.add(sup)
            self.show_info("Supplier saved")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_update(self) -> None:
        if self.selected_id is None:
            self.show_error("Select a supplier to update")
            return
        try:
            sup = self._parse_supplier()
            self.repo.update(self.selected_id, sup)
            self.show_info("Supplier updated")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_delete(self) -> None:
        if self.selected_id is None:
            self.show_error("Select a supplier to delete")
            return
        if not self.ask_yes_no("Delete selected supplier?"):
            return
        try:
            self.repo.delete(self.selected_id)
            self.show_info("Supplier deleted")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_clear(self) -> None:
        self.selected_id = None
        self.var_name.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_company.set("")
        self.var_address.set("")

    def on_search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_text.get().strip())
            self._load(rows)
        except Exception as e:
            self.show_error(str(e))

    def on_select(self, _evt: object = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get("values", [])
        if not vals:
            return
        self.selected_id = int(vals[0])
        self.var_name.set(str(vals[1]))
        self.var_email.set(str(vals[2]))
        self.var_phone.set(str(vals[3]))
        self.var_company.set(str(vals[4]))
        self.var_address.set(str(vals[5]))

    def refresh(self) -> None:
        self._load(self.repo.list_all())

    def _load(self, rows: List[Tuple]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", tk.END, values=r)


class CategoryManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Category Management")
        self.repo = repo
        self.selected_id: Optional[int] = None

        form = ttk.LabelFrame(self, text="Category Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_desc = tk.StringVar()

        ttk.Label(form, text="Name").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Description").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_desc, width=50).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self.on_save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self.on_update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self.on_delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["cat_id", "name"], state="readonly", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self.on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self.refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("cat_id", "name", "description")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=220 if c != "description" else 600, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.refresh()

    def _parse_category(self) -> Category:
        return Category(name=self.var_name.get().strip(), description=self.var_desc.get().strip())

    def on_save(self) -> None:
        try:
            cat = self._parse_category()
            self.repo.add(cat)
            self.show_info("Category saved")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_update(self) -> None:
        if self.selected_id is None:
            self.show_error("Select a category to update")
            return
        try:
            cat = self._parse_category()
            self.repo.update(self.selected_id, cat)
            self.show_info("Category updated")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_delete(self) -> None:
        if self.selected_id is None:
            self.show_error("Select a category to delete")
            return
        if not self.ask_yes_no("Delete selected category?"):
            return
        try:
            self.repo.delete(self.selected_id)
            self.show_info("Category deleted")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_clear(self) -> None:
        self.selected_id = None
        self.var_name.set("")
        self.var_desc.set("")

    def on_search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_text.get().strip())
            self._load(rows)
        except Exception as e:
            self.show_error(str(e))

    def on_select(self, _evt: object = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get("values", [])
        if not vals:
            return
        self.selected_id = int(vals[0])
        self.var_name.set(str(vals[1]))
        self.var_desc.set(str(vals[2]))

    def refresh(self) -> None:
        self._load(self.repo.list_all())

    def _load(self, rows: List[Tuple]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", tk.END, values=r)


class ProductManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, cat_repo: CategoryRepository, sup_repo: SupplierRepository) -> None:
        super().__init__(master, "Product Management")
        self.repo = repo
        self.cat_repo = cat_repo
        self.sup_repo = sup_repo
        self.selected_id: Optional[int] = None

        form = ttk.LabelFrame(self, text="Product Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar(value="Active")

        ttk.Label(form, text="Name").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=28).grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Category").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.cb_category = ttk.Combobox(form, textvariable=self.var_category, state="readonly", width=26)
        self.cb_category.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Supplier").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.cb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, state="readonly", width=26)
        self.cb_supplier.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Price").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_price, width=28).grid(row=1, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Quantity").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_qty, width=28).grid(row=2, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Status").grid(row=2, column=2, padx=6, pady=6, sticky="w")
        ttk.Combobox(form, textvariable=self.var_status, values=["Active", "Inactive"], state="readonly", width=26).grid(row=2, column=3, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self.on_save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self.on_update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self.on_delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Reload Lists", command=self.reload_lists).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_text = tk.StringVar()

        ttk.Label(search, text="By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["prod_id", "name", "status"], state="readonly", width=12).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_text, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self.on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self.refresh).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("prod_id", "name", "category", "supplier", "price", "qty", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140 if c not in {"name"} else 220, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self._cat_map: Dict[str, int] = {}
        self._sup_map: Dict[str, int] = {}
        self.reload_lists()
        self.refresh()

    def reload_lists(self) -> None:
        cats = self.cat_repo.list_all()
        sups = self.sup_repo.list_all()

        self._cat_map = {f"{c[0]} - {c[1]}": int(c[0]) for c in cats}
        self._sup_map = {f"{s[0]} - {s[1]}": int(s[0]) for s in sups}

        cat_keys = list(self._cat_map.keys())
        sup_keys = list(self._sup_map.keys())

        self.cb_category["values"] = cat_keys
        self.cb_supplier["values"] = sup_keys

        if cat_keys and not self.var_category.get():
            self.var_category.set(cat_keys[0])
        if sup_keys and not self.var_supplier.get():
            self.var_supplier.set(sup_keys[0])

    def _parse_product(self) -> Product:
        cat_key = self.var_category.get().strip()
        sup_key = self.var_supplier.get().strip()
        if cat_key not in self._cat_map:
            raise ValueError("Select a valid category")
        if sup_key not in self._sup_map:
            raise ValueError("Select a valid supplier")
        price = float(self.var_price.get().strip() or "0")
        qty = int(float(self.var_qty.get().strip() or "0"))
        return Product(
            name=self.var_name.get().strip(),
            category_id=self._cat_map[cat_key],
            supplier_id=self._sup_map[sup_key],
            price=price,
            qty=qty,
            status=self.var_status.get().strip(),
        )

    def on_save(self) -> None:
        try:
            prod = self._parse_product()
            self.repo.add(prod)
            self.show_info("Product saved")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_update(self) -> None:
        if self.selected_id is None:
            self.show_error("Select a product to update")
            return
        try:
            prod = self._parse_product()
            self.repo.update(self.selected_id, prod)
            self.show_info("Product updated")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_delete(self) -> None:
        if self.selected_id is None:
            self.show_error("Select a product to delete")
            return
        if not self.ask_yes_no("Delete selected product?"):
            return
        try:
            self.repo.delete(self.selected_id)
            self.show_info("Product deleted")
            self.on_clear()
            self.refresh()
        except Exception as e:
            self.show_error(str(e))

    def on_clear(self) -> None:
        self.selected_id = None
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("Active")

    def on_search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_text.get().strip())
            self._load(rows)
        except Exception as e:
            self.show_error(str(e))

    def on_select(self, _evt: object = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get("values", [])
        if not vals:
            return
        prod_id = int(vals[0])
        row = self.repo.get(prod_id)
        if not row:
            return
        self.selected_id = prod_id
        self.var_name.set(str(row[1]))
        cat_id = int(row[2])
        sup_id = int(row[3])
        self.var_price.set(str(row[4]))
        self.var_qty.set(str(row[5]))
        self.var_status.set(str(row[6]))

        cat_key = None
        for k, v in self._cat_map.items():
            if v == cat_id:
                cat_key = k
                break
        sup_key = None
        for k, v in self._sup_map.items():
            if v == sup_id:
                sup_key = k
                break
        if cat_key:
            self.var_category.set(cat_key)
        if sup_key:
            self.var_supplier.set(sup_key)

    def refresh(self) -> None:
        self._load(self.repo.list_all())

    def _load(self, rows: List[Tuple]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", tk.END, values=(r[0], r[1], r[2], r[3], r[4], r[5], r[6]))


class BillViewerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: BillRepository) -> None:
        super().__init__(master, "Bill Viewer")
        self.repo = repo

        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_invoice = tk.StringVar()
        ttk.Label(top, text="Invoice No").pack(side=tk.LEFT, padx=5)
        ttk.Entry(top, textvariable=self.var_invoice, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Search", command=self.on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Browse Saved Bills", command=self.on_browse).pack(side=tk.LEFT, padx=5)

        body = ttk.Frame(self)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text = tk.Text(body, wrap="none")
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.text.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=sb_y.set)

        sb_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text.xview)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.text.configure(xscrollcommand=sb_x.set)

        self._load_list_panel()

    def _load_list_panel(self) -> None:
        panel = ttk.LabelFrame(self, text="Saved Bills")
        panel.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        cols = ("invoice_no", "customer_name", "customer_phone", "bill_date", "net_total")
        self.tree = ttk.Treeview(panel, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=180, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True)

        sb = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_pick)
        self.refresh_list()

    def refresh_list(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self.repo.list_all():
            self.tree.insert("", tk.END, values=r)

    def on_pick(self, _evt: object = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0]).get("values", [])
        if not vals:
            return
        inv = str(vals[0])
        self.var_invoice.set(inv)
        self.on_search()

    def on_search(self) -> None:
        inv = self.var_invoice.get().strip()
        if not inv:
            self.show_error("Enter invoice number")
            return
        content = self.repo.search(inv)
        if content is None:
            self.show_error("Invoice not found")
            return
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, content)

    def on_browse(self) -> None:
        inv = self.var_invoice.get().strip()
        if inv:
            self.on_search()
        else:
            self.refresh_list()
            self.show_info("Select an invoice from the list below")


class BillingWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, prod_repo: ProductRepository, bill_repo: BillRepository) -> None:
        super().__init__(master, "Billing")
        self.prod_repo = prod_repo
        self.bill_repo = bill_repo

        self.cart: List[Dict[str, object]] = []

        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_invoice = tk.StringVar(value=self._generate_invoice_no())
        self.var_cust_name = tk.StringVar()
        self.var_cust_phone = tk.StringVar()
        self.var_tax_rate = tk.StringVar(value="0")

        ttk.Label(header, text="Invoice No").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(header, textvariable=self.var_invoice, width=20).grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(header, text="Customer Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(header, textvariable=self.var_cust_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(header, text="Customer Phone").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(header, textvariable=self.var_cust_phone, width=20).grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(header, text="Tax %").grid(row=0, column=6, padx=6, pady=6, sticky="w")
        ttk.Entry(header, textvariable=self.var_tax_rate, width=8).grid(row=0, column=7, padx=6, pady=6, sticky="w")

        body = ttk.Frame(self)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.LabelFrame(body, text="Products")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        right = ttk.LabelFrame(body, text="Cart")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.var_prod_search = tk.StringVar()
        self.var_prod_search_by = tk.StringVar(value="name")

        search_bar = ttk.Frame(left)
        search_bar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        ttk.Label(search_bar, text="Search By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_bar, textvariable=self.var_prod_search_by, values=["prod_id", "name", "status"], state="readonly", width=10).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search_bar, textvariable=self.var_prod_search, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_bar, text="Search", command=self.on_prod_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_bar, text="Show All", command=self.refresh_products).pack(side=tk.LEFT, padx=5)

        prod_cols = ("prod_id", "name", "category", "supplier", "price", "qty", "status")
        self.prod_tree = ttk.Treeview(left, columns=prod_cols, show="headings", height=14)
        for c in prod_cols:
            self.prod_tree.heading(c, text=c)
            self.prod_tree.column(c, width=120 if c != "name" else 200, anchor="w")
        self.prod_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        prod_sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.prod_tree.yview)
        self.prod_tree.configure(yscrollcommand=prod_sb.set)
        prod_sb.place(relx=1.0, rely=0.12, relheight=0.86, anchor="ne")

        add_bar = ttk.Frame(left)
        add_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=6)

        self.var_add_qty = tk.StringVar(value="1")
        ttk.Label(add_bar, text="Qty").pack(side=tk.LEFT, padx=5)
        ttk.Entry(add_bar, textvariable=self.var_add_qty, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_bar, text="Add to Cart", command=self.on_add_to_cart).pack(side=tk.LEFT, padx=5)

        cart_cols = ("prod_id", "name", "price", "qty", "amount")
        self.cart_tree = ttk.Treeview(right, columns=cart_cols, show="headings", height=14)
        for c in cart_cols:
            self.cart_tree.heading(c, text=c)
            self.cart_tree.column(c, width=120 if c != "name" else 220, anchor="w")
        self.cart_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        cart_sb = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_sb.set)
        cart_sb.place(relx=1.0, rely=0.12, relheight=0.86, anchor="ne")

        cart_btns = ttk.Frame(right)
        cart_btns.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=6)

        ttk.Button(cart_btns, text="Remove Selected", command=self.on_remove_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btns, text="Clear Cart", command=self.on_clear_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btns, text="Generate Bill", command=self.on_generate_bill).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btns, text="Save Bill", command=self.on_save_bill).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btns, text="Print Preview", command=self.on_preview).pack(side=tk.LEFT, padx=5)

        totals = ttk.LabelFrame(self, text="Totals")
        totals.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.var_total = tk.StringVar(value="0.00")
        self.var_tax = tk.StringVar(value="0.00")
        self.var_net = tk.StringVar(value="0.00")

        ttk.Label(totals, text="Total").pack(side=tk.LEFT, padx=10)
        ttk.Label(totals, textvariable=self.var_total, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(totals, text="Tax").pack(side=tk.LEFT, padx=10)
        ttk.Label(totals, textvariable=self.var_tax, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(totals, text="Net Total").pack(side=tk.LEFT, padx=10)
        ttk.Label(totals, textvariable=self.var_net, width=12).pack(side=tk.LEFT, padx=5)

        self.bill_text = tk.Text(self, height=12, wrap="none")
        self.bill_text.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        self.refresh_products()
        self._recalc_totals()

    def _generate_invoice_no(self) -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def refresh_products(self) -> None:
        rows = self.prod_repo.list_all()
        self._load_products(rows)

    def _load_products(self, rows: List[Tuple]) -> None:
        for i in self.prod_tree.get_children():
            self.prod_tree.delete(i)
        for r in rows:
            self.prod_tree.insert("", tk.END, values=(r[0], r[1], r[2], r[3], f"{float(r[4]):.2f}", r[5], r[6]))

    def on_prod_search(self) -> None:
        try:
            rows = self.prod_repo.search(self.var_prod_search_by.get(), self.var_prod_search.get().strip())
            self._load_products(rows)
        except Exception as e:
            self.show_error(str(e))

    def on_add_to_cart(self) -> None:
        sel = self.prod_tree.selection()
        if not sel:
            self.show_error("Select a product to add")
            return
        vals = self.prod_tree.item(sel[0]).get("values", [])
        if not vals:
            return
        prod_id = int(vals[0])
        name = str(vals[1])
        price = float(vals[4])
        available = int(vals[5])
        try:
            qty = int(float(self.var_add_qty.get().strip() or "0"))
        except Exception:
            self.show_error("Invalid quantity")
            return
        if qty <= 0:
            self.show_error("Quantity must be positive")
            return
        if qty > available:
            self.show_error("Insufficient stock")
            return

        for item in self.cart:
            if int(item["prod_id"]) == prod_id:
                new_qty = int(item["qty"]) + qty
                if new_qty > available:
                    self.show_error("Insufficient stock")
                    return
                item["qty"] = new_qty
                item["amount"] = float(item["qty"]) * float(item["price"])
                self._refresh_cart()
                self._recalc_totals()
                return

        self.cart.append({"prod_id": prod_id, "name": name, "price": price, "qty": qty, "amount": price * qty})
        self._refresh_cart()
        self._recalc_totals()

    def _refresh_cart(self) -> None:
        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
        for item in self.cart:
            self.cart_tree.insert(
                "",
                tk.END,
                values=(
                    int(item["prod_id"]),
                    str(item["name"]),
                    f"{float(item['price']):.2f}",
                    int(item["qty"]),
                    f"{float(item['amount']):.2f}",
                ),
            )

    def on_remove_cart(self) -> None:
        sel = self.cart_tree.selection()
        if not sel:
            self.show_error("Select a cart item to remove")
            return
        vals = self.cart_tree.item(sel[0]).get("values", [])
        if not vals:
            return
        prod_id = int(vals[0])
        self.cart = [i for i in self.cart if int(i["prod_id"]) != prod_id]
        self._refresh_cart()
        self._recalc_totals()

    def on_clear_cart(self) -> None:
        self.cart = []
        self._refresh_cart()
        self._recalc_totals()
        self.bill_text.delete("1.0", tk.END)

    def _recalc_totals(self) -> None:
        total = sum(float(i["amount"]) for i in self.cart)
        try:
            tax_rate = float(self.var_tax_rate.get().strip() or "0")
        except Exception:
            tax_rate = 0.0
        if tax_rate < 0:
            tax_rate = 0.0
        tax = total * (tax_rate / 100.0)
        net = total + tax
        self.var_total.set(f"{total:.2f}")
        self.var_tax.set(f"{tax:.2f}")
        self.var_net.set(f"{net:.2f}")

    def on_generate_bill(self) -> None:
        if not self.cart:
            self.show_error("Cart is empty")
            return
        if not self.var_cust_name.get().strip():
            self.show_error("Customer name is required")
            return
        if not self.var_cust_phone.get().strip():
            self.show_error("Customer phone is required")
            return

        self._recalc_totals()
        invoice = self.var_invoice.get().strip()
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL")
        lines.append(f"Invoice No: {invoice}")
        lines.append(f"Date: {bill_date}")
        lines.append(f"Customer: {self.var_cust_name.get().strip()}")
        lines.append(f"Phone: {self.var_cust_phone.get().strip()}")
        lines.append("-" * 70)
        lines.append(f"{'ID':<6}{'Product':<30}{'Price':>10}{'Qty':>8}{'Amount':>12}")
        lines.append("-" * 70)
        for item in self.cart:
            lines.append(
                f"{int(item['prod_id']):<6}{str(item['name'])[:29]:<30}{float(item['price']):>10.2f}{int(item['qty']):>8}{float(item['amount']):>12.2f}"
            )
        lines.append("-" * 70)
        lines.append(f"{'Total':>56}{float(self.var_total.get()):>14.2f}")
        lines.append(f"{'Tax':>56}{float(self.var_tax.get()):>14.2f}")
        lines.append(f"{'Net Total':>56}{float(self.var_net.get()):>14.2f}")
        lines.append("-" * 70)

        content = "\n".join(lines)
        self.bill_text.delete("1.0", tk.END)
        self.bill_text.insert(tk.END, content)

    def on_save_bill(self) -> None:
        content = self.bill_text.get("1.0", tk.END).strip()
        if not content:
            self.show_error("Generate bill before saving")
            return
        if not self.cart:
            self.show_error("Cart is empty")
            return

        invoice = self.var_invoice.get().strip()
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._recalc_totals()

        try:
            for item in self.cart:
                self.prod_repo.adjust_stock(int(item["prod_id"]), -int(item["qty"]))
            self.bill_repo.save(
                invoice_no=invoice,
                customer_name=self.var_cust_name.get().strip(),
                customer_phone=self.var_cust_phone.get().strip(),
                bill_date=bill_date,
                total=float(self.var_total.get()),
                tax=float(self.var_tax.get()),
                net_total=float(self.var_net.get()),
                content=content,
            )
            self.show_info("Bill saved")
            self.refresh_products()
            self.var_invoice.set(self._generate_invoice_no())
            self.cart = []
            self._refresh_cart()
            self._recalc_totals()
        except Exception as e:
            self.show_error(str(e))

    def on_preview(self) -> None:
        content = self.bill_text.get("1.0", tk.END).strip()
        if not content:
            self.show_error("No bill to preview")
            return
        win = tk.Toplevel(self)
        win.title("Print Preview")
        win.geometry("800x600")
        txt = tk.Text(win, wrap="none")
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=txt.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.configure(yscrollcommand=sb.set)
        txt.insert(tk.END, content)
        txt.configure(state="disabled")


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1200x700")
        self.minsize(1100, 650)

        self.db = Database(DB_FILE)
        self.emp_repo = EmployeeRepository(self.db)
        self.sup_repo = SupplierRepository(self.db)
        self.cat_repo = CategoryRepository(self.db)
        self.prod_repo = ProductRepository(self.db)
        self.bill_repo = BillRepository(self.db)

        self._img_ref: Optional[object] = None

        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X)

        self.lbl_title = ttk.Label(top, text="Inventory Management System", font=("Arial", 20, "bold"))
        self.lbl_title.pack(side=tk.LEFT, padx=15, pady=15)

        self.lbl_time = ttk.Label(top, text="", font=("Arial", 12))
        self.lbl_time.pack(side=tk.RIGHT, padx=15)

        mid = ttk.Frame(self)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(mid)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        right = ttk.Frame(mid)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        btn_style = {"width": 22}
        ttk.Button(left, text="Employees", command=self.open_employees, **btn_style).pack(pady=6)
        ttk.Button(left, text="Suppliers", command=self.open_suppliers, **btn_style).pack(pady=6)
        ttk.Button(left, text="Categories", command=self.open_categories, **btn_style).pack(pady=6)
        ttk.Button(left, text="Products", command=self.open_products, **btn_style).pack(pady=6)
        ttk.Button(left, text="Billing", command=self.open_billing, **btn_style).pack(pady=6)
        ttk.Button(left, text="Bills (Search/View)", command=self.open_bills, **btn_style).pack(pady=6)
        ttk.Button(left, text="Load Image", command=self.load_image, **btn_style).pack(pady=6)
        ttk.Button(left, text="Exit", command=self.on_exit, **btn_style).pack(pady=6)

        stats = ttk.LabelFrame(right, text="Dashboard")
        stats.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_emp_count = tk.StringVar(value="0")
        self.var_sup_count = tk.StringVar(value="0")
        self.var_cat_count = tk.StringVar(value="0")
        self.var_prod_count = tk.StringVar(value="0")
        self.var_bill_count = tk.StringVar(value="0")

        self._stat_label(stats, "Employees", self.var_emp_count, 0)
        self._stat_label(stats, "Suppliers", self.var_sup_count, 1)
        self._stat_label(stats, "Categories", self.var_cat_count, 2)
        self._stat_label(stats, "Products", self.var_prod_count, 3)
        self._stat_label(stats, "Bills", self.var_bill_count, 4)

        self.image_panel = ttk.LabelFrame(right, text="Image")
        self.image_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.image_label = ttk.Label(self.image_panel, text="No image loaded")
        self.image_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_status = ttk.Label(bottom, text="Ready", anchor="w")
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)

        self._tick_time()
        self.refresh_counts()

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _stat_label(self, parent: ttk.LabelFrame, name: str, var: tk.StringVar, idx: int) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=idx, padx=10, pady=10, sticky="w")
        ttk.Label(frame, text=name, font=("Arial", 12, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=var, font=("Arial", 16)).pack(anchor="w")

    def _tick_time(self) -> None:
        self.lbl_time.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self._tick_time)

    def refresh_counts(self) -> None:
        try:
            emp = self.db.query("SELECT COUNT(*) FROM employees")[0][0]
            sup = self.db.query("SELECT COUNT(*) FROM suppliers")[0][0]
            cat = self.db.query("SELECT COUNT(*) FROM categories")[0][0]
            prod = self.db.query("SELECT COUNT(*) FROM products")[0][0]
            bills = self.db.query("SELECT COUNT(*) FROM bills")[0][0]
            self.var_emp_count.set(str(emp))
            self.var_sup_count.set(str(sup))
            self.var_cat_count.set(str(cat))
            self.var_prod_count.set(str(prod))
            self.var_bill_count.set(str(bills))
            self.lbl_status.configure(text="Counts refreshed")
        except Exception as e:
            self.lbl_status.configure(text=str(e))
        self.after(5000, self.refresh_counts)

    def open_employees(self) -> None:
        EmployeeManagerWindow(self, self.emp_repo)

    def open_suppliers(self) -> None:
        SupplierManagerWindow(self, self.sup_repo)

    def open_categories(self) -> None:
        CategoryManagerWindow(self, self.cat_repo)

    def open_products(self) -> None:
        ProductManagerWindow(self, self.prod_repo, self.cat_repo, self.sup_repo)

    def open_billing(self) -> None:
        BillingWindow(self, self.prod_repo, self.bill_repo)

    def open_bills(self) -> None:
        BillViewerWindow(self, self.bill_repo)

    def load_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            initialdir=os.getcwd(),
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")],
        )
        if not path:
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Error", "PIL (Pillow) is not available", parent=self)
            return
        try:
            img = Image.open(path)
            panel_w = max(300, self.image_panel.winfo_width() - 40)
            panel_h = max(300, self.image_panel.winfo_height() - 60)
            img.thumbnail((panel_w, panel_h))
            tk_img = ImageTk.PhotoImage(img)
            self._img_ref = tk_img
            self.image_label.configure(image=tk_img, text="")
            self.lbl_status.configure(text=f"Loaded image: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

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