import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

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
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                gender TEXT,
                contact TEXT,
                dob TEXT,
                doj TEXT,
                password TEXT,
                usertype TEXT,
                address TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                contact TEXT,
                description TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pid TEXT UNIQUE NOT NULL,
                category_id INTEGER,
                supplier_invoice_no TEXT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                status TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL,
                FOREIGN KEY(supplier_invoice_no) REFERENCES suppliers(invoice_no) ON DELETE SET NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                customer_contact TEXT,
                created_at TEXT NOT NULL,
                total REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bill_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_invoice_no TEXT NOT NULL,
                product_pid TEXT,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(bill_invoice_no) REFERENCES bills(invoice_no) ON DELETE CASCADE
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
    emp_id: str
    name: str
    email: str = ""
    gender: str = ""
    contact: str = ""
    dob: str = ""
    doj: str = ""
    password: str = ""
    usertype: str = ""
    address: str = ""


@dataclass(frozen=True)
class Supplier:
    invoice_no: str
    name: str
    contact: str = ""
    description: str = ""


@dataclass(frozen=True)
class Category:
    name: str


@dataclass(frozen=True)
class Product:
    pid: str
    category_name: str = ""
    supplier_invoice_no: str = ""
    name: str = ""
    price: float = 0.0
    qty: int = 0
    status: str = ""


@dataclass(frozen=True)
class BillItem:
    product_pid: str
    product_name: str
    price: float
    qty: int

    @property
    def line_total(self) -> float:
        return float(self.price) * int(self.qty)


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, e: Employee) -> None:
        if not e.emp_id.strip() or not e.name.strip():
            raise ValueError("Employee ID and Name are required.")
        self.db.execute(
            """
            INSERT INTO employees(emp_id,name,email,gender,contact,dob,doj,password,usertype,address)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.password, e.usertype, e.address),
        )

    def update(self, e: Employee) -> None:
        if not e.emp_id.strip():
            raise ValueError("Employee ID is required.")
        self.db.execute(
            """
            UPDATE employees
            SET name=?, email=?, gender=?, contact=?, dob=?, doj=?, password=?, usertype=?, address=?
            WHERE emp_id=?
            """,
            (e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.password, e.usertype, e.address, e.emp_id),
        )

    def delete(self, emp_id: str) -> None:
        self.db.execute("DELETE FROM employees WHERE emp_id=?", (emp_id,))

    def get(self, emp_id: str) -> Optional[Employee]:
        rows = self.db.query(
            """
            SELECT emp_id,name,email,gender,contact,dob,doj,password,usertype,address
            FROM employees WHERE emp_id=?
            """,
            (emp_id,),
        )
        if not rows:
            return None
        r = rows[0]
        return Employee(*r)

    def list_all(self) -> List[Employee]:
        rows = self.db.query(
            """
            SELECT emp_id,name,email,gender,contact,dob,doj,password,usertype,address
            FROM employees ORDER BY id DESC
            """
        )
        return [Employee(*r) for r in rows]

    def search(self, field: str, value: str) -> List[Employee]:
        allowed = {"emp_id", "name", "contact", "email", "usertype"}
        if field not in allowed:
            raise ValueError("Invalid search field.")
        rows = self.db.query(
            f"""
            SELECT emp_id,name,email,gender,contact,dob,doj,password,usertype,address
            FROM employees
            WHERE {field} LIKE ?
            ORDER BY id DESC
            """,
            (f"%{value}%",),
        )
        return [Employee(*r) for r in rows]


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, s: Supplier) -> None:
        if not s.invoice_no.strip() or not s.name.strip():
            raise ValueError("Supplier Invoice No and Name are required.")
        self.db.execute(
            "INSERT INTO suppliers(invoice_no,name,contact,description) VALUES(?,?,?,?)",
            (s.invoice_no, s.name, s.contact, s.description),
        )

    def update(self, s: Supplier) -> None:
        if not s.invoice_no.strip():
            raise ValueError("Supplier Invoice No is required.")
        self.db.execute(
            "UPDATE suppliers SET name=?, contact=?, description=? WHERE invoice_no=?",
            (s.name, s.contact, s.description, s.invoice_no),
        )

    def delete(self, invoice_no: str) -> None:
        self.db.execute("DELETE FROM suppliers WHERE invoice_no=?", (invoice_no,))

    def get(self, invoice_no: str) -> Optional[Supplier]:
        rows = self.db.query("SELECT invoice_no,name,contact,description FROM suppliers WHERE invoice_no=?", (invoice_no,))
        if not rows:
            return None
        return Supplier(*rows[0])

    def list_all(self) -> List[Supplier]:
        rows = self.db.query("SELECT invoice_no,name,contact,description FROM suppliers ORDER BY id DESC")
        return [Supplier(*r) for r in rows]

    def search(self, field: str, value: str) -> List[Supplier]:
        allowed = {"invoice_no", "name", "contact"}
        if field not in allowed:
            raise ValueError("Invalid search field.")
        rows = self.db.query(
            f"SELECT invoice_no,name,contact,description FROM suppliers WHERE {field} LIKE ? ORDER BY id DESC",
            (f"%{value}%",),
        )
        return [Supplier(*r) for r in rows]


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, c: Category) -> None:
        if not c.name.strip():
            raise ValueError("Category name is required.")
        self.db.execute("INSERT INTO categories(name) VALUES(?)", (c.name.strip(),))

    def delete(self, name: str) -> None:
        self.db.execute("DELETE FROM categories WHERE name=?", (name,))

    def list_all(self) -> List[Category]:
        rows = self.db.query("SELECT name FROM categories ORDER BY name ASC")
        return [Category(r[0]) for r in rows]

    def get_id_by_name(self, name: str) -> Optional[int]:
        rows = self.db.query("SELECT id FROM categories WHERE name=?", (name,))
        return int(rows[0][0]) if rows else None


class ProductRepository:
    def __init__(self, db: Database, categories: CategoryRepository) -> None:
        self.db = db
        self.categories = categories

    def add(self, p: Product) -> None:
        if not p.pid.strip() or not p.name.strip():
            raise ValueError("Product ID and Name are required.")
        if p.price < 0:
            raise ValueError("Price must be non-negative.")
        if p.qty < 0:
            raise ValueError("Quantity must be non-negative.")
        cat_id = None
        if p.category_name.strip():
            cat_id = self.categories.get_id_by_name(p.category_name.strip())
            if cat_id is None:
                raise ValueError("Category does not exist.")
        supplier_invoice = p.supplier_invoice_no.strip() or None
        self.db.execute(
            """
            INSERT INTO products(pid,category_id,supplier_invoice_no,name,price,qty,status)
            VALUES(?,?,?,?,?,?,?)
            """,
            (p.pid, cat_id, supplier_invoice, p.name, float(p.price), int(p.qty), p.status),
        )

    def update(self, p: Product) -> None:
        if not p.pid.strip():
            raise ValueError("Product ID is required.")
        if p.price < 0:
            raise ValueError("Price must be non-negative.")
        if p.qty < 0:
            raise ValueError("Quantity must be non-negative.")
        cat_id = None
        if p.category_name.strip():
            cat_id = self.categories.get_id_by_name(p.category_name.strip())
            if cat_id is None:
                raise ValueError("Category does not exist.")
        supplier_invoice = p.supplier_invoice_no.strip() or None
        self.db.execute(
            """
            UPDATE products
            SET category_id=?, supplier_invoice_no=?, name=?, price=?, qty=?, status=?
            WHERE pid=?
            """,
            (cat_id, supplier_invoice, p.name, float(p.price), int(p.qty), p.status, p.pid),
        )

    def delete(self, pid: str) -> None:
        self.db.execute("DELETE FROM products WHERE pid=?", (pid,))

    def get(self, pid: str) -> Optional[Product]:
        rows = self.db.query(
            """
            SELECT p.pid, COALESCE(c.name,''), COALESCE(p.supplier_invoice_no,''), p.name, p.price, p.qty, COALESCE(p.status,'')
            FROM products p
            LEFT JOIN categories c ON c.id=p.category_id
            WHERE p.pid=?
            """,
            (pid,),
        )
        if not rows:
            return None
        r = rows[0]
        return Product(pid=r[0], category_name=r[1], supplier_invoice_no=r[2], name=r[3], price=float(r[4]), qty=int(r[5]), status=r[6])

    def list_all(self) -> List[Product]:
        rows = self.db.query(
            """
            SELECT p.pid, COALESCE(c.name,''), COALESCE(p.supplier_invoice_no,''), p.name, p.price, p.qty, COALESCE(p.status,'')
            FROM products p
            LEFT JOIN categories c ON c.id=p.category_id
            ORDER BY p.id DESC
            """
        )
        return [
            Product(pid=r[0], category_name=r[1], supplier_invoice_no=r[2], name=r[3], price=float(r[4]), qty=int(r[5]), status=r[6])
            for r in rows
        ]

    def search(self, field: str, value: str) -> List[Product]:
        allowed = {"pid", "name", "status", "supplier_invoice_no"}
        if field not in allowed:
            raise ValueError("Invalid search field.")
        rows = self.db.query(
            f"""
            SELECT p.pid, COALESCE(c.name,''), COALESCE(p.supplier_invoice_no,''), p.name, p.price, p.qty, COALESCE(p.status,'')
            FROM products p
            LEFT JOIN categories c ON c.id=p.category_id
            WHERE p.{field} LIKE ?
            ORDER BY p.id DESC
            """,
            (f"%{value}%",),
        )
        return [
            Product(pid=r[0], category_name=r[1], supplier_invoice_no=r[2], name=r[3], price=float(r[4]), qty=int(r[5]), status=r[6])
            for r in rows
        ]

    def adjust_stock(self, pid: str, delta_qty: int) -> None:
        prod = self.get(pid)
        if prod is None:
            raise ValueError("Product not found.")
        new_qty = int(prod.qty) + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock.")
        self.db.execute("UPDATE products SET qty=? WHERE pid=?", (new_qty, pid))


class BillingService:
    def __init__(self, db: Database, products: ProductRepository) -> None:
        self.db = db
        self.products = products

    def create_bill(self, invoice_no: str, customer_name: str, customer_contact: str, items: List[BillItem]) -> None:
        if not invoice_no.strip():
            raise ValueError("Invoice number is required.")
        if not items:
            raise ValueError("At least one item is required.")
        for it in items:
            if it.qty <= 0:
                raise ValueError("Item quantity must be positive.")
            if it.price < 0:
                raise ValueError("Item price must be non-negative.")
        total = float(sum(i.line_total for i in items))
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur = self.db.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO bills(invoice_no,customer_name,customer_contact,created_at,total) VALUES(?,?,?,?,?)",
                (invoice_no, customer_name, customer_contact, created_at, total),
            )
            for it in items:
                if it.product_pid.strip():
                    self.products.adjust_stock(it.product_pid, -int(it.qty))
                cur.execute(
                    """
                    INSERT INTO bill_items(bill_invoice_no,product_pid,product_name,price,qty,line_total)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (invoice_no, it.product_pid, it.product_name, float(it.price), int(it.qty), float(it.line_total)),
                )
            self.db.conn.commit()
        except Exception:
            self.db.conn.rollback()
            raise

    def get_bill(self, invoice_no: str) -> Tuple[Optional[Tuple], List[Tuple]]:
        bill_rows = self.db.query(
            "SELECT invoice_no,customer_name,customer_contact,created_at,total FROM bills WHERE invoice_no=?",
            (invoice_no,),
        )
        bill = bill_rows[0] if bill_rows else None
        items = self.db.query(
            "SELECT product_pid,product_name,price,qty,line_total FROM bill_items WHERE bill_invoice_no=? ORDER BY id ASC",
            (invoice_no,),
        )
        return bill, items

    def list_bills(self) -> List[Tuple]:
        return self.db.query("SELECT invoice_no,customer_name,customer_contact,created_at,total FROM bills ORDER BY id DESC")


class BaseManagerWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("1000x600")
        self.minsize(900, 550)
        self.transient(master)
        self.grab_set()

    def _center(self) -> None:
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


class EmployeeManager(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: EmployeeRepository) -> None:
        super().__init__(master, "Employee Management")
        self.repo = repo

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_password = tk.StringVar()
        self.var_usertype = tk.StringVar()
        self.var_address = tk.StringVar()

        self.var_search_by = tk.StringVar(value="emp_id")
        self.var_search_txt = tk.StringVar()

        self._build()
        self._refresh_table()
        self._center()

    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Employee Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        def add_row(r: int, c: int, text: str, var: tk.StringVar, width: int = 22) -> None:
            ttk.Label(form, text=text).grid(row=r, column=c, padx=6, pady=6, sticky="w")
            ttk.Entry(form, textvariable=var, width=width).grid(row=r, column=c + 1, padx=6, pady=6, sticky="w")

        add_row(0, 0, "Employee ID", self.var_emp_id)
        add_row(0, 2, "Name", self.var_name)
        add_row(0, 4, "Email", self.var_email)

        add_row(1, 0, "Gender", self.var_gender)
        add_row(1, 2, "Contact", self.var_contact)
        add_row(1, 4, "DOB (YYYY-MM-DD)", self.var_dob)

        add_row(2, 0, "DOJ (YYYY-MM-DD)", self.var_doj)
        add_row(2, 2, "Password", self.var_password)
        add_row(2, 4, "User Type", self.var_usertype)

        ttk.Label(form, text="Address").grid(row=3, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_address, width=80).grid(row=3, column=1, columnspan=5, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self._update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(search, text="Search By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["emp_id", "name", "contact", "email", "usertype"], state="readonly", width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Entry(search, textvariable=self.var_search_txt, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh_table).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "usertype", "address")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=120, anchor="w")
        self.tree.column("address", width=220)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _validate_date(self, s: str) -> None:
        if not s.strip():
            return
        datetime.strptime(s.strip(), "%Y-%m-%d")

    def _get_form_employee(self) -> Employee:
        self._validate_date(self.var_dob.get())
        self._validate_date(self.var_doj.get())
        return Employee(
            emp_id=self.var_emp_id.get().strip(),
            name=self.var_name.get().strip(),
            email=self.var_email.get().strip(),
            gender=self.var_gender.get().strip(),
            contact=self.var_contact.get().strip(),
            dob=self.var_dob.get().strip(),
            doj=self.var_doj.get().strip(),
            password=self.var_password.get(),
            usertype=self.var_usertype.get().strip(),
            address=self.var_address.get().strip(),
        )

    def _save(self) -> None:
        try:
            self.repo.add(self._get_form_employee())
            messagebox.showinfo("Success", "Employee saved.")
            self._refresh_table()
            self._clear()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _update(self) -> None:
        try:
            self.repo.update(self._get_form_employee())
            messagebox.showinfo("Success", "Employee updated.")
            self._refresh_table()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            messagebox.showerror("Error", "Employee ID is required.")
            return
        if not messagebox.askyesno("Confirm", "Delete this employee?"):
            return
        try:
            self.repo.delete(emp_id)
            messagebox.showinfo("Success", "Employee deleted.")
            self._refresh_table()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear(self) -> None:
        for v in (
            self.var_emp_id,
            self.var_name,
            self.var_email,
            self.var_gender,
            self.var_contact,
            self.var_dob,
            self.var_doj,
            self.var_password,
            self.var_usertype,
            self.var_address,
        ):
            v.set("")

    def _refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for e in self.repo.list_all():
            self.tree.insert("", tk.END, values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.usertype, e.address))

    def _search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_txt.get().strip())
            self.tree.delete(*self.tree.get_children())
            for e in rows:
                self.tree.insert("", tk.END, values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.usertype, e.address))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_emp_id.set(vals[0])
        self.var_name.set(vals[1])
        self.var_email.set(vals[2])
        self.var_gender.set(vals[3])
        self.var_contact.set(vals[4])
        self.var_dob.set(vals[5])
        self.var_doj.set(vals[6])
        self.var_usertype.set(vals[7])
        self.var_address.set(vals[8])


class SupplierManager(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Supplier Management")
        self.repo = repo

        self.var_invoice_no = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_description = tk.StringVar()

        self.var_search_by = tk.StringVar(value="invoice_no")
        self.var_search_txt = tk.StringVar()

        self._build()
        self._refresh_table()
        self._center()

    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Supplier Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(form, text="Invoice No").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_invoice_no, width=25).grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Contact").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_contact, width=25).grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Description").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_description, width=25).grid(row=1, column=3, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self._update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(search, text="Search By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["invoice_no", "name", "contact"], state="readonly", width=15).pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_search_txt, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh_table).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("invoice_no", "name", "contact", "description")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=200, anchor="w")
        self.tree.column("description", width=350)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _get_form_supplier(self) -> Supplier:
        return Supplier(
            invoice_no=self.var_invoice_no.get().strip(),
            name=self.var_name.get().strip(),
            contact=self.var_contact.get().strip(),
            description=self.var_description.get().strip(),
        )

    def _save(self) -> None:
        try:
            self.repo.add(self._get_form_supplier())
            messagebox.showinfo("Success", "Supplier saved.")
            self._refresh_table()
            self._clear()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier Invoice No already exists.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _update(self) -> None:
        try:
            self.repo.update(self._get_form_supplier())
            messagebox.showinfo("Success", "Supplier updated.")
            self._refresh_table()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete(self) -> None:
        inv = self.var_invoice_no.get().strip()
        if not inv:
            messagebox.showerror("Error", "Invoice No is required.")
            return
        if not messagebox.askyesno("Confirm", "Delete this supplier?"):
            return
        try:
            self.repo.delete(inv)
            messagebox.showinfo("Success", "Supplier deleted.")
            self._refresh_table()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear(self) -> None:
        for v in (self.var_invoice_no, self.var_name, self.var_contact, self.var_description):
            v.set("")

    def _refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for s in self.repo.list_all():
            self.tree.insert("", tk.END, values=(s.invoice_no, s.name, s.contact, s.description))

    def _search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_txt.get().strip())
            self.tree.delete(*self.tree.get_children())
            for s in rows:
                self.tree.insert("", tk.END, values=(s.invoice_no, s.name, s.contact, s.description))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_invoice_no.set(vals[0])
        self.var_name.set(vals[1])
        self.var_contact.set(vals[2])
        self.var_description.set(vals[3])


class CategoryManager(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Category Management")
        self.repo = repo
        self.var_name = tk.StringVar()
        self._build()
        self._refresh()
        self._center()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="Category Name").pack(side=tk.LEFT, padx=5)
        ttk.Entry(top, textvariable=self.var_name, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Add", command=self._add).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5)

        frame = ttk.Frame(self)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.listbox = tk.Listbox(frame)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", self._on_select)

    def _refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for c in self.repo.list_all():
            self.listbox.insert(tk.END, c.name)

    def _add(self) -> None:
        try:
            self.repo.add(Category(self.var_name.get().strip()))
            messagebox.showinfo("Success", "Category added.")
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete(self) -> None:
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Category name is required.")
            return
        if not messagebox.askyesno("Confirm", "Delete this category?"):
            return
        try:
            self.repo.delete(name)
            messagebox.showinfo("Success", "Category deleted.")
            self._refresh()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear(self) -> None:
        self.var_name.set("")

    def _on_select(self, _evt: object) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        self.var_name.set(self.listbox.get(sel[0]))


class ProductManager(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, cat_repo: CategoryRepository, sup_repo: SupplierRepository) -> None:
        super().__init__(master, "Product Management")
        self.repo = repo
        self.cat_repo = cat_repo
        self.sup_repo = sup_repo

        self.var_pid = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()

        self.var_search_by = tk.StringVar(value="pid")
        self.var_search_txt = tk.StringVar()

        self._build()
        self._reload_dropdowns()
        self._refresh_table()
        self._center()

    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Product Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(form, text="Product ID").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_pid, width=25).grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Category").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.cmb_category = ttk.Combobox(form, textvariable=self.var_category, state="readonly", width=23)
        self.cmb_category.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Supplier Invoice").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        self.cmb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, state="readonly", width=23)
        self.cmb_supplier.grid(row=1, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Price").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_price, width=25).grid(row=2, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Quantity").grid(row=2, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_qty, width=25).grid(row=2, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Status").grid(row=3, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_status, width=25).grid(row=3, column=1, padx=6, pady=6, sticky="w")

        ttk.Button(form, text="Reload Lists", command=self._reload_dropdowns).grid(row=3, column=3, padx=6, pady=6, sticky="e")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10)

        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self._update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(search, text="Search By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search, textvariable=self.var_search_by, values=["pid", "name", "status", "supplier_invoice_no"], state="readonly", width=18).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Entry(search, textvariable=self.var_search_txt, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Search", command=self._search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh_table).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("pid", "category", "supplier_invoice", "name", "price", "qty", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=130, anchor="w")
        self.tree.column("name", width=220)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _reload_dropdowns(self) -> None:
        cats = [c.name for c in self.cat_repo.list_all()]
        sups = [s.invoice_no for s in self.sup_repo.list_all()]
        self.cmb_category["values"] = [""] + cats
        self.cmb_supplier["values"] = [""] + sups
        if self.var_category.get() not in self.cmb_category["values"]:
            self.var_category.set("")
        if self.var_supplier.get() not in self.cmb_supplier["values"]:
            self.var_supplier.set("")

    def _get_form_product(self) -> Product:
        pid = self.var_pid.get().strip()
        name = self.var_name.get().strip()
        category = self.var_category.get().strip()
        supplier = self.var_supplier.get().strip()
        status = self.var_status.get().strip()
        try:
            price = float(self.var_price.get().strip() or "0")
        except ValueError:
            raise ValueError("Invalid price.")
        try:
            qty = int(self.var_qty.get().strip() or "0")
        except ValueError:
            raise ValueError("Invalid quantity.")
        return Product(pid=pid, category_name=category, supplier_invoice_no=supplier, name=name, price=price, qty=qty, status=status)

    def _save(self) -> None:
        try:
            self.repo.add(self._get_form_product())
            messagebox.showinfo("Success", "Product saved.")
            self._refresh_table()
            self._clear()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product ID already exists.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _update(self) -> None:
        try:
            self.repo.update(self._get_form_product())
            messagebox.showinfo("Success", "Product updated.")
            self._refresh_table()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            messagebox.showerror("Error", "Product ID is required.")
            return
        if not messagebox.askyesno("Confirm", "Delete this product?"):
            return
        try:
            self.repo.delete(pid)
            messagebox.showinfo("Success", "Product deleted.")
            self._refresh_table()
            self._clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear(self) -> None:
        for v in (self.var_pid, self.var_category, self.var_supplier, self.var_name, self.var_price, self.var_qty, self.var_status):
            v.set("")

    def _refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for p in self.repo.list_all():
            self.tree.insert("", tk.END, values=(p.pid, p.category_name, p.supplier_invoice_no, p.name, f"{p.price:.2f}", p.qty, p.status))

    def _search(self) -> None:
        try:
            rows = self.repo.search(self.var_search_by.get(), self.var_search_txt.get().strip())
            self.tree.delete(*self.tree.get_children())
            for p in rows:
                self.tree.insert("", tk.END, values=(p.pid, p.category_name, p.supplier_invoice_no, p.name, f"{p.price:.2f}", p.qty, p.status))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_pid.set(vals[0])
        self.var_category.set(vals[1])
        self.var_supplier.set(vals[2])
        self.var_name.set(vals[3])
        self.var_price.set(str(vals[4]))
        self.var_qty.set(str(vals[5]))
        self.var_status.set(vals[6])


class BillingWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, billing: BillingService, products: ProductRepository) -> None:
        super().__init__(master, "Billing")
        self.billing = billing
        self.products = products

        self.var_invoice_no = tk.StringVar()
        self.var_customer_name = tk.StringVar()
        self.var_customer_contact = tk.StringVar()

        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar(value="1")

        self.var_bill_search = tk.StringVar()

        self._build()
        self._refresh_products()
        self._refresh_bills()
        self._center()

    def _build(self) -> None:
        top = ttk.LabelFrame(self, text="Bill Header")
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="Invoice No").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_invoice_no, width=25).grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(top, text="Customer Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_customer_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(top, text="Customer Contact").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_customer_contact, width=25).grid(row=0, column=5, padx=6, pady=6, sticky="w")

        mid = ttk.LabelFrame(self, text="Add Item")
        mid.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(mid, text="Product ID").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.cmb_pid = ttk.Combobox(mid, textvariable=self.var_pid, state="readonly", width=23)
        self.cmb_pid.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        self.cmb_pid.bind("<<ComboboxSelected>>", self._on_pid_selected)

        ttk.Label(mid, text="Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(mid, textvariable=self.var_pname, width=25, state="readonly").grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(mid, text="Price").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(mid, textvariable=self.var_price, width=15, state="readonly").grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(mid, text="Qty").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(mid, textvariable=self.var_qty, width=25).grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Button(mid, text="Add to Cart", command=self._add_to_cart).grid(row=1, column=3, padx=6, pady=6, sticky="w")
        ttk.Button(mid, text="Remove Selected", command=self._remove_selected).grid(row=1, column=4, padx=6, pady=6, sticky="w")
        ttk.Button(mid, text="Clear Cart", command=self._clear_cart).grid(row=1, column=5, padx=6, pady=6, sticky="w")

        body = ttk.Frame(self)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.LabelFrame(body, text="Cart")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        cart_cols = ("pid", "name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(left, columns=cart_cols, show="headings", height=12)
        for c in cart_cols:
            self.cart_tree.heading(c, text=c.upper())
            self.cart_tree.column(c, width=120, anchor="w")
        self.cart_tree.column("name", width=220)
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cart_sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_sb.set)
        cart_sb.pack(side=tk.RIGHT, fill=tk.Y)

        right = ttk.LabelFrame(body, text="Bills")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search = ttk.Frame(right)
        search.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)
        ttk.Label(search, text="Invoice No").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search, textvariable=self.var_bill_search, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Find", command=self._find_bill).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Show All", command=self._refresh_bills).pack(side=tk.LEFT, padx=5)
        ttk.Button(search, text="Open Bill File", command=self._open_bill_file).pack(side=tk.LEFT, padx=5)

        bill_cols = ("invoice_no", "customer_name", "customer_contact", "created_at", "total")
        self.bill_tree = ttk.Treeview(right, columns=bill_cols, show="headings", height=12)
        for c in bill_cols:
            self.bill_tree.heading(c, text=c.upper())
            self.bill_tree.column(c, width=140, anchor="w")
        self.bill_tree.column("created_at", width=170)
        self.bill_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        bill_sb = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.bill_tree.yview)
        self.bill_tree.configure(yscrollcommand=bill_sb.set)
        bill_sb.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.lbl_total = ttk.Label(bottom, text="Total: 0.00")
        self.lbl_total.pack(side=tk.LEFT, padx=5)

        ttk.Button(bottom, text="Generate Bill", command=self._generate_bill).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom, text="Save Bill to File", command=self._save_bill_to_file).pack(side=tk.RIGHT, padx=5)

    def _refresh_products(self) -> None:
        prods = self.products.list_all()
        self._pid_map = {p.pid: p for p in prods}
        self.cmb_pid["values"] = [""] + [p.pid for p in prods]
        if self.var_pid.get() not in self.cmb_pid["values"]:
            self.var_pid.set("")
            self.var_pname.set("")
            self.var_price.set("")

    def _on_pid_selected(self, _evt: object) -> None:
        pid = self.var_pid.get().strip()
        p = self._pid_map.get(pid)
        if not p:
            self.var_pname.set("")
            self.var_price.set("")
            return
        self.var_pname.set(p.name)
        self.var_price.set(f"{p.price:.2f}")

    def _add_to_cart(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            messagebox.showerror("Error", "Select a product.")
            return
        p = self.products.get(pid)
        if p is None:
            messagebox.showerror("Error", "Product not found.")
            return
        try:
            qty = int(self.var_qty.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity.")
            return
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive.")
            return
        if qty > p.qty:
            messagebox.showerror("Error", "Insufficient stock.")
            return

        for iid in self.cart_tree.get_children():
            vals = self.cart_tree.item(iid, "values")
            if vals and vals[0] == pid:
                new_qty = int(vals[3]) + qty
                if new_qty > p.qty:
                    messagebox.showerror("Error", "Insufficient stock.")
                    return
                price = float(vals[2])
                total = price * new_qty
                self.cart_tree.item(iid, values=(pid, p.name, f"{price:.2f}", new_qty, f"{total:.2f}"))
                self._update_total()
                return

        total = float(p.price) * qty
        self.cart_tree.insert("", tk.END, values=(pid, p.name, f"{p.price:.2f}", qty, f"{total:.2f}"))
        self._update_total()

    def _remove_selected(self) -> None:
        sel = self.cart_tree.selection()
        if not sel:
            return
        for iid in sel:
            self.cart_tree.delete(iid)
        self._update_total()

    def _clear_cart(self) -> None:
        self.cart_tree.delete(*self.cart_tree.get_children())
        self._update_total()

    def _update_total(self) -> None:
        total = 0.0
        for iid in self.cart_tree.get_children():
            vals = self.cart_tree.item(iid, "values")
            if vals:
                total += float(vals[4])
        self.lbl_total.config(text=f"Total: {total:.2f}")

    def _cart_items(self) -> List[BillItem]:
        items: List[BillItem] = []
        for iid in self.cart_tree.get_children():
            pid, name, price, qty, _total = self.cart_tree.item(iid, "values")
            items.append(BillItem(product_pid=str(pid), product_name=str(name), price=float(price), qty=int(qty)))
        return items

    def _generate_bill(self) -> None:
        invoice_no = self.var_invoice_no.get().strip()
        customer_name = self.var_customer_name.get().strip()
        customer_contact = self.var_customer_contact.get().strip()
        items = self._cart_items()
        try:
            self.billing.create_bill(invoice_no, customer_name, customer_contact, items)
            messagebox.showinfo("Success", "Bill generated.")
            self._refresh_products()
            self._refresh_bills()
            self._clear_cart()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _refresh_bills(self) -> None:
        self.bill_tree.delete(*self.bill_tree.get_children())
        for b in self.billing.list_bills():
            inv, cname, ccontact, created_at, total = b
            self.bill_tree.insert("", tk.END, values=(inv, cname, ccontact, created_at, f"{float(total):.2f}"))

    def _find_bill(self) -> None:
        inv = self.var_bill_search.get().strip()
        if not inv:
            self._refresh_bills()
            return
        bill, _items = self.billing.get_bill(inv)
        self.bill_tree.delete(*self.bill_tree.get_children())
        if bill:
            inv, cname, ccontact, created_at, total = bill
            self.bill_tree.insert("", tk.END, values=(inv, cname, ccontact, created_at, f"{float(total):.2f}"))
        else:
            messagebox.showinfo("Not found", "No bill found for that invoice number.")

    def _bill_text(self, invoice_no: str) -> str:
        bill, items = self.billing.get_bill(invoice_no)
        if not bill:
            raise ValueError("Bill not found.")
        inv, cname, ccontact, created_at, total = bill
        lines = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL")
        lines.append(f"Invoice No: {inv}")
        lines.append(f"Date/Time: {created_at}")
        lines.append(f"Customer: {cname}")
        lines.append(f"Contact: {ccontact}")
        lines.append("-" * 60)
        lines.append(f"{'PID':<12}{'NAME':<26}{'PRICE':>8}{'QTY':>6}{'TOTAL':>8}")
        lines.append("-" * 60)
        for pid, pname, price, qty, line_total in items:
            lines.append(f"{str(pid)[:12]:<12}{str(pname)[:26]:<26}{float(price):>8.2f}{int(qty):>6}{float(line_total):>8.2f}")
        lines.append("-" * 60)
        lines.append(f"{'GRAND TOTAL':>52}{float(total):>8.2f}")
        lines.append("-" * 60)
        return "\n".join(lines)

    def _save_bill_to_file(self) -> None:
        inv = self.var_invoice_no.get().strip()
        if not inv:
            sel = self.bill_tree.selection()
            if sel:
                inv = str(self.bill_tree.item(sel[0], "values")[0])
        if not inv:
            messagebox.showerror("Error", "Provide or select an invoice number.")
            return
        try:
            text = self._bill_text(inv)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        bills_dir = "bills"
        os.makedirs(bills_dir, exist_ok=True)
        path = os.path.join(bills_dir, f"{inv}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Saved", f"Bill saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_bill_file(self) -> None:
        bills_dir = "bills"
        os.makedirs(bills_dir, exist_ok=True)
        path = filedialog.askopenfilename(initialdir=bills_dir, title="Open Bill", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not path:
            return
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                import subprocess

                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, path])
        except Exception:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                w = tk.Toplevel(self)
                w.title(os.path.basename(path))
                txt = tk.Text(w, wrap="word")
                txt.insert("1.0", content)
                txt.configure(state="disabled")
                txt.pack(fill=tk.BOTH, expand=True)
            except Exception as e:
                messagebox.showerror("Error", str(e))


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self.db = Database(DB_FILE)
        self.emp_repo = EmployeeRepository(self.db)
        self.sup_repo = SupplierRepository(self.db)
        self.cat_repo = CategoryRepository(self.db)
        self.prod_repo = ProductRepository(self.db, self.cat_repo)
        self.billing = BillingService(self.db, self.prod_repo)

        self._img_ref = None

        self._build()
        self._tick()
        self._refresh_counts()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X)

        title = ttk.Label(header, text="Inventory Management System", font=("Arial", 20, "bold"))
        title.pack(side=tk.LEFT, padx=12, pady=12)

        self.lbl_time = ttk.Label(header, text="", font=("Arial", 11))
        self.lbl_time.pack(side=tk.RIGHT, padx=12)

        main = ttk.Frame(self)
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Button(left, text="Employees", width=22, command=self._open_employees).pack(pady=6)
        ttk.Button(left, text="Suppliers", width=22, command=self._open_suppliers).pack(pady=6)
        ttk.Button(left, text="Categories", width=22, command=self._open_categories).pack(pady=6)
        ttk.Button(left, text="Products", width=22, command=self._open_products).pack(pady=6)
        ttk.Button(left, text="Billing", width=22, command=self._open_billing).pack(pady=6)
        ttk.Button(left, text="Refresh Dashboard", width=22, command=self._refresh_counts).pack(pady=6)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cards = ttk.Frame(right)
        cards.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        self.lbl_emp = ttk.Label(cards, text="Employees: 0", font=("Arial", 12, "bold"))
        self.lbl_emp.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.lbl_sup = ttk.Label(cards, text="Suppliers: 0", font=("Arial", 12, "bold"))
        self.lbl_sup.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.lbl_cat = ttk.Label(cards, text="Categories: 0", font=("Arial", 12, "bold"))
        self.lbl_cat.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.lbl_prod = ttk.Label(cards, text="Products: 0", font=("Arial", 12, "bold"))
        self.lbl_prod.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.lbl_bills = ttk.Label(cards, text="Bills: 0", font=("Arial", 12, "bold"))
        self.lbl_bills.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        preview = ttk.LabelFrame(right, text="Image Preview (PIL)")
        preview.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        topbar = ttk.Frame(preview)
        topbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        ttk.Button(topbar, text="Load Image", command=self._load_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(topbar, text="Clear Image", command=self._clear_image).pack(side=tk.LEFT, padx=5)

        self.img_label = ttk.Label(preview, text="No image loaded")
        self.img_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        footer = ttk.Frame(self)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer, text="Database: sqlite3 | Files: os | Date/Time: datetime | GUI: tkinter").pack(side=tk.LEFT, padx=10, pady=8)

    def _tick(self) -> None:
        self.lbl_time.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self._tick)

    def _refresh_counts(self) -> None:
        try:
            emp = self.db.query("SELECT COUNT(*) FROM employees")[0][0]
            sup = self.db.query("SELECT COUNT(*) FROM suppliers")[0][0]
            cat = self.db.query("SELECT COUNT(*) FROM categories")[0][0]
            prod = self.db.query("SELECT COUNT(*) FROM products")[0][0]
            bills = self.db.query("SELECT COUNT(*) FROM bills")[0][0]
            self.lbl_emp.config(text=f"Employees: {emp}")
            self.lbl_sup.config(text=f"Suppliers: {sup}")
            self.lbl_cat.config(text=f"Categories: {cat}")
            self.lbl_prod.config(text=f"Products: {prod}")
            self.lbl_bills.config(text=f"Bills: {bills}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_employees(self) -> None:
        EmployeeManager(self, self.emp_repo)

    def _open_suppliers(self) -> None:
        SupplierManager(self, self.sup_repo)

    def _open_categories(self) -> None:
        CategoryManager(self, self.cat_repo)

    def _open_products(self) -> None:
        ProductManager(self, self.prod_repo, self.cat_repo, self.sup_repo)

    def _open_billing(self) -> None:
        BillingWindow(self, self.billing, self.prod_repo)

    def _load_image(self) -> None:
        path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")])
        if not path:
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Error", "PIL (Pillow) is not available.")
            return
        try:
            img = Image.open(path)
            w = max(1, self.img_label.winfo_width())
            h = max(1, self.img_label.winfo_height())
            img.thumbnail((w - 20, h - 20))
            self._img_ref = ImageTk.PhotoImage(img)
            self.img_label.config(image=self._img_ref, text="")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear_image(self) -> None:
        self._img_ref = None
        self.img_label.config(image="", text="No image loaded")

    def _on_close(self) -> None:
        try:
            self.db.close()
        finally:
            self.destroy()


def main() -> None:
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()